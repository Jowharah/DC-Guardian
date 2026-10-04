"""
Parse locked DC-GUARDIAN RAG sources into page/document records.

Parsing is deterministic and does not chunk, embed, summarize, or rewrite
source content. Every record retains source provenance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup
from pypdf import PdfReader


RAG_ROOT = Path(__file__).resolve().parent
MANIFEST_FILE = RAG_ROOT / "manifests" / "knowledge_manifest.json"
LOCK_FILE = RAG_ROOT / "manifests" / "source_lock.json"
PARSED_DIR = RAG_ROOT / "knowledge_base" / "parsed"
CHUNK_BYTES = 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def base_metadata(source: dict, lock: dict) -> dict:
    return {
        "document_id": source["document_id"],
        "title": source["title"],
        "primary_domain": source["primary_domain"],
        "applicable_domains": source["applicable_domains"],
        "authority_type": source["authority_type"],
        "source_type": source["source_type"],
        "publisher": source["publisher"],
        "version": source.get("version"),
        "publication_date": source.get("publication_date"),
        "source_url": source.get("url"),
        "source_sha256": lock["sha256"],
    }


def parse_pdf(path: Path, metadata: dict) -> list[dict]:
    reader = PdfReader(str(path))
    records = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = clean_text(page.extract_text() or "")
        if not text:
            continue

        record = dict(metadata)
        record.update({
            "record_id": f"{metadata['document_id']}:page:{page_number}",
            "record_type": "PAGE",
            "page": page_number,
            "section": None,
            "text": text,
        })
        records.append(record)

    return records


def parse_html(path: Path, metadata: dict) -> list[dict]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(raw, "html.parser")

    for element in soup(["script", "style", "noscript"]):
        element.decompose()

    text = clean_text(soup.get_text("\n"))
    if not text:
        return []

    record = dict(metadata)
    record.update({
        "record_id": f"{metadata['document_id']}:document:1",
        "record_type": "DOCUMENT",
        "page": None,
        "section": None,
        "text": text,
    })
    return [record]


def parse_source(path: Path, metadata: dict) -> list[dict]:
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return parse_pdf(path, metadata)
    if suffix in {".html", ".htm"}:
        return parse_html(path, metadata)

    raise ValueError(f"Unsupported locked source format: {suffix}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--document-id",
        help="Parse only one locked document ID.",
    )
    args = parser.parse_args()

    manifest = load_json(MANIFEST_FILE)
    lock = load_json(LOCK_FILE)

    source_by_id = {
        item["document_id"]: item
        for item in manifest["sources"]
    }

    locked = lock["sources"]
    if args.document_id:
        locked = [
            item for item in locked
            if item["document_id"] == args.document_id
        ]
        if not locked:
            raise ValueError(
                f"Document is not locked: {args.document_id}"
            )

    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    failures = []
    parsed_count = 0

    for locked_source in locked:
        document_id = locked_source["document_id"]
        try:
            source = source_by_id[document_id]

            if not (
                source.get("approval_status") == "APPROVED"
                and source.get("retrieval_status") == "ACTIVE"
            ):
                raise ValueError(
                    "Locked source is not APPROVED + ACTIVE."
                )

            source_path = RAG_ROOT / locked_source["local_file"]
            if not source_path.is_file():
                raise FileNotFoundError(source_path)

            actual_sha = sha256_file(source_path)
            if actual_sha != locked_source["sha256"]:
                raise RuntimeError(
                    "Source SHA-256 does not match source_lock.json."
                )

            metadata = base_metadata(source, locked_source)
            records = parse_source(source_path, metadata)

            if not records:
                raise RuntimeError("Parser produced no text records.")

            output = PARSED_DIR / f"{document_id}.jsonl"
            with output.open("w", encoding="utf-8") as handle:
                for record in records:
                    handle.write(
                        json.dumps(record, ensure_ascii=False) + "\n"
                    )

            total_chars = sum(len(item["text"]) for item in records)
            parsed_count += 1
            print(
                f"PASS: {document_id} "
                f"({len(records)} records, {total_chars} chars)"
            )
        except Exception as error:
            failures.append((document_id, str(error)))
            print(f"FAIL: {document_id}: {error}")

    print()
    print(f"Locked sources: {len(locked)}")
    print(f"Parsed sources: {parsed_count}")
    print(f"Failures:       {len(failures)}")
    print(f"Output:         {PARSED_DIR}")

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
