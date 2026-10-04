"""Build deterministic, provenance-preserving RAG chunks."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from config import (
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
    starts = {}
    for index, record in enumerate(records):
        upper = record["text"].upper()
        for control in controls:
            pattern = rf"(?m)^\s*{re.escape(control)}(?:\s|\.|:)"
            if control not in starts and re.search(pattern, upper):
                starts[control] = index

    missing = [control for control in controls if control not in starts]
    if missing:
        raise RuntimeError(
            f"Could not locate complete control ranges for {document_id}: {missing}"
        )

    selected_indexes = set()
    control_heading = re.compile(r"(?m)^\s*PE-(\d+)(?:\s|\.|:)")
    for control in controls:
        start_index = starts[control]
        target_number = int(control.split("-")[1])
        end_index = len(records)

        for index in range(start_index + 1, len(records)):
            matches = control_heading.findall(records[index]["text"].upper())
            if any(int(number) > target_number for number in matches):
                end_index = index
                break

        selected_indexes.update(range(start_index, end_index))

    selected = [
        record for index, record in enumerate(records)
        if index in selected_indexes
    ]
    if not selected:
        raise RuntimeError(
            f"Retrieval scope selected no records for {document_id}."
        )
    return selected, "EXPLICIT_CONTROL_RANGES"


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
            item["page"] for item in current
            if item["page"] is not None
        })
        source_records = list(dict.fromkeys(
            item["record_id"] for item in current
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
