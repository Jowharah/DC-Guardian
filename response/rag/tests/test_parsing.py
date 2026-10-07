"""
Contract checks for Response RAG parsed RAG source records.

Run after parse_sources.py from the repository root:
    python response/rag/tests/test_parsing.py
"""

from __future__ import annotations

import json
from pathlib import Path


RAG_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_FILE = RAG_ROOT / "manifests" / "knowledge_manifest.json"
LOCK_FILE = RAG_ROOT / "manifests" / "source_lock.json"
PARSED_DIR = RAG_ROOT / "knowledge_base" / "parsed"

REQUIRED_FIELDS = {
    "record_id",
    "document_id",
    "title",
    "primary_domain",
    "applicable_domains",
    "authority_type",
    "source_type",
    "publisher",
    "version",
    "source_url",
    "source_sha256",
    "record_type",
    "page",
    "section",
    "text",
}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    manifest = load_json(MANIFEST_FILE)
    lock = load_json(LOCK_FILE)

    active_ids = {
        item["document_id"]
        for item in manifest["sources"]
        if item.get("approval_status") == "APPROVED"
        and item.get("retrieval_status") == "ACTIVE"
    }
    locked_ids = {
        item["document_id"]
        for item in lock["sources"]
    }

    if active_ids != locked_ids:
        raise AssertionError(
            "APPROVED + ACTIVE manifest sources must exactly match "
            "the locked corpus before parsing validation."
        )

    for document_id in sorted(locked_ids):
        path = PARSED_DIR / f"{document_id}.jsonl"
        if not path.is_file():
            raise AssertionError(
                f"Missing parsed output: {path}"
            )

        records = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    records.append(json.loads(line))

        if not records:
            raise AssertionError(
                f"No parsed records for {document_id}"
            )

        ids = set()
        total_chars = 0

        for record in records:
            missing = REQUIRED_FIELDS - record.keys()
            if missing:
                raise AssertionError(
                    f"{document_id} missing fields: {sorted(missing)}"
                )
            if record["document_id"] != document_id:
                raise AssertionError(
                    f"Wrong document_id in {document_id}"
                )
            if not record["text"].strip():
                raise AssertionError(
                    f"Empty parsed text in {record['record_id']}"
                )
            if record["record_id"] in ids:
                raise AssertionError(
                    f"Duplicate record_id: {record['record_id']}"
                )
            ids.add(record["record_id"])
            total_chars += len(record["text"])

        if total_chars < 200:
            raise AssertionError(
                f"Suspiciously little parsed text for {document_id}: "
                f"{total_chars} characters"
            )

        print(
            f"PASS: {document_id} "
            f"({len(records)} records, {total_chars} chars)"
        )

    print()
    print("=" * 60)
    print(
        f"DC-GUARDIAN RAG PARSING CONTRACT PASSED: "
        f"{len(locked_ids)}/{len(active_ids)}"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()

