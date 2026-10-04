"""Build deterministic, provenance-preserving RAG chunks."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from phase3.rag.config import (
    MAX_CHUNK_WORDS,
    MIN_CHUNK_WORDS,
    OVERLAP_WORDS,
    RETRIEVAL_SCOPE,
    TARGET_CHUNK_WORDS,
)


RAG_ROOT = Path(__file__).resolve().parent
CLEAN_DIR = RAG_ROOT / "knowledge_base" / "clean"
CHUNK_DIR = RAG_ROOT / "knowledge_base" / "chunks"
LOCK_FILE = RAG_ROOT / "manifests" / "source_lock.json"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(x) for x in handle if x.strip()]


def paragraphs(text: str) -> list[str]:
    parts = re.split(r"\n\s*\n|(?<=\.)\n(?=[A-Z0-9])", text)
    return [re.sub(r"\s+", " ", p).strip() for p in parts if p.strip()]


def scope_records(document_id: str, records: list[dict]) -> tuple[list[dict], str]:
    scope = RETRIEVAL_SCOPE.get(document_id)
    if not scope:
        return records, "FULL_DOCUMENT"

    if scope["mode"] != "control_ranges":
        raise ValueError(f"Unsupported retrieval scope mode: {scope['mode']}")

    controls = scope["controls"]
    selected = []

    # Preserve page provenance while extracting only the requested control
    # text. A control may span pages; extraction stops at the next PE control
    # heading so unrelated intervening controls are not indexed.
    full_text_parts = []
    offsets = []
    cursor = 0
    for record in records:
        text = record["text"]
        full_text_parts.append(text)
        offsets.append((cursor, cursor + len(text), record))
        cursor += len(text) + 2
    full_text = "\n\n".join(full_text_parts)

    heading = re.compile(r"(?m)^\s*PE-(\d+)\s+[A-Z]")
    headings = list(heading.finditer(full_text))

    for control in controls:
        number = int(control.split("-")[1])
        start_match = next(
            (match for match in headings if int(match.group(1)) == number),
            None,
        )
        if start_match is None:
            raise RuntimeError(
                f"Could not locate complete control text for {document_id}: {control}"
            )

        next_match = next(
            (match for match in headings if match.start() > start_match.start()),
            None,
        )
        end_pos = next_match.start() if next_match else len(full_text)
        control_text = full_text[start_match.start():end_pos].strip()

        pages = []
        record_ids = []
        first_meta = None
        for begin, end, record in offsets:
            if end <= start_match.start() or begin >= end_pos:
                continue
            if first_meta is None:
                first_meta = record
            if record.get("page") is not None:
                pages.append(record["page"])
            record_ids.append(record["record_id"])

        if first_meta is None or not control_text:
            raise RuntimeError(f"Empty scoped control: {control}")

        synthetic = dict(first_meta)
        synthetic["record_id"] = f"{document_id}:scope:{control}"
        synthetic["text"] = control_text
        synthetic["page"] = min(pages) if pages else None
        synthetic["scope_pages"] = sorted(set(pages))
        synthetic["scope_source_record_ids"] = list(dict.fromkeys(record_ids))
        selected.append(synthetic)

    return selected, "EXACT_CONTROL_TEXT"


def split_long_paragraph(text: str, limit: int) -> list[str]:
    words = text.split()
    return [
        " ".join(words[i:i + limit])
        for i in range(0, len(words), limit)
    ]


def make_chunks(document_id: str, records: list[dict], scope_mode: str) -> list[dict]:
    units = []
    for record in records:
        for para in paragraphs(record["text"]):
            pieces = split_long_paragraph(para, MAX_CHUNK_WORDS)
            for piece in pieces:
                units.append({
                    "text": piece,
                    "page": record.get("page"),
                    "record_id": record["record_id"],
                    "scope_pages": record.get("scope_pages"),
                    "scope_source_record_ids": record.get("scope_source_record_ids"),
                    "meta": record,
                })

    chunks = []
    current = []
    current_words = 0

    def flush() -> None:
        nonlocal current, current_words
        if not current:
            return
        text = "\n\n".join(item["text"] for item in current).strip()
        if not text:
            current = []
            current_words = 0
            return

        meta = current[0]["meta"]
        pages = sorted({
            page
            for item in current
            for page in (
                item["scope_pages"]
                if item.get("scope_pages")
                else ([item["page"]] if item["page"] is not None else [])
            )
        })
        source_records = list(dict.fromkeys(
            source_id
            for item in current
            for source_id in (
                item["scope_source_record_ids"]
                if item.get("scope_source_record_ids")
                else [item["record_id"]]
            )
        ))
        index = len(chunks)
        digest = hashlib.sha256(
            (document_id + "\n" + text).encode("utf-8")
        ).hexdigest()[:16]

        chunks.append({
            "chunk_id": f"{document_id}:chunk:{index:05d}:{digest}",
            "chunk_index": index,
            "document_id": document_id,
            "title": meta["title"],
            "primary_domain": meta["primary_domain"],
            "applicable_domains": meta["applicable_domains"],
            "authority_type": meta["authority_type"],
            "source_type": meta["source_type"],
            "publisher": meta["publisher"],
            "version": meta.get("version"),
            "publication_date": meta.get("publication_date"),
            "source_url": meta.get("source_url"),
            "source_sha256": meta["source_sha256"],
            "pages": pages,
            "source_record_ids": source_records,
            "retrieval_scope": scope_mode,
            "word_count": len(text.split()),
            "text": text,
        })

        overlap = []
        overlap_words = 0
        for item in reversed(current):
            item_words = len(item["text"].split())
            if overlap and overlap_words + item_words > OVERLAP_WORDS:
                break
            if item_words > OVERLAP_WORDS:
                break
            overlap.insert(0, item)
            overlap_words += item_words
            if overlap_words >= OVERLAP_WORDS:
                break
        current = overlap
        current_words = overlap_words

    for unit in units:
        words = len(unit["text"].split())
        if current and current_words + words > TARGET_CHUNK_WORDS:
            flush()
        current.append(unit)
        current_words += words
        if current_words >= MAX_CHUNK_WORDS:
            flush()

    flush()

    # Merge a tiny final chunk into the preceding chunk when possible.
    if len(chunks) >= 2 and chunks[-1]["word_count"] < MIN_CHUNK_WORDS:
        tail = chunks.pop()
        prev = chunks[-1]
        combined = prev["text"] + "\n\n" + tail["text"]
        if len(combined.split()) <= MAX_CHUNK_WORDS:
            prev["text"] = combined
            prev["word_count"] = len(combined.split())
            prev["pages"] = sorted(set(prev["pages"] + tail["pages"]))
            prev["source_record_ids"] = list(dict.fromkeys(
                prev["source_record_ids"] + tail["source_record_ids"]
            ))
        else:
            chunks.append(tail)

    return chunks


def main() -> None:
    lock = load_json(LOCK_FILE)
    ids = sorted(item["document_id"] for item in lock["sources"])
    CHUNK_DIR.mkdir(parents=True, exist_ok=True)

    total = 0
    failures = 0
    for document_id in ids:
        try:
            records = load_jsonl(CLEAN_DIR / f"{document_id}.jsonl")
            selected, scope_mode = scope_records(document_id, records)
            chunks = make_chunks(document_id, selected, scope_mode)
            if not chunks:
                raise RuntimeError("No chunks generated.")

            output = CHUNK_DIR / f"{document_id}.jsonl"
            with output.open("w", encoding="utf-8") as handle:
                for chunk in chunks:
                    handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")

            total += len(chunks)
            counts = [c["word_count"] for c in chunks]
            print(
                f"PASS: {document_id} | chunks={len(chunks)} "
                f"min={min(counts)} max={max(counts)} "
                f"scope={scope_mode}"
            )
        except Exception as error:
            failures += 1
            print(f"FAIL: {document_id}: {error}")

    print()
    print(f"Documents:    {len(ids)}")
    print(f"Total chunks: {total}")
    print(f"Failures:     {failures}")
    print(f"Output:       {CHUNK_DIR}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
