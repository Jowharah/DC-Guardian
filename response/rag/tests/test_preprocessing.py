"""
Contract checks for conservatively preprocessed RAG records.
"""

from __future__ import annotations

import json
from pathlib import Path


RAG_ROOT = Path(__file__).resolve().parents[1]
LOCK_FILE = RAG_ROOT / "manifests" / "source_lock.json"
PARSED_DIR = RAG_ROOT / "knowledge_base" / "parsed"
CLEAN_DIR = RAG_ROOT / "knowledge_base" / "clean"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [
            json.loads(line)
            for line in handle
            if line.strip()
        ]


def main() -> None:
    lock = load_json(LOCK_FILE)
    ids = sorted(item["document_id"] for item in lock["sources"])

    for document_id in ids:
        parsed = load_jsonl(
            PARSED_DIR / f"{document_id}.jsonl"
        )
        clean = load_jsonl(
            CLEAN_DIR / f"{document_id}.jsonl"
        )

        if len(parsed) != len(clean):
            raise AssertionError(
                f"Record count changed for {document_id}."
            )

        for before, after in zip(parsed, clean):
            for field in (
                "record_id",
                "document_id",
                "source_sha256",
                "title",
                "primary_domain",
                "applicable_domains",
                "authority_type",
                "publisher",
                "version",
                "page",
            ):
                if before.get(field) != after.get(field):
                    raise AssertionError(
                        f"Provenance field changed: "
                        f"{document_id} / {field}"
                    )

            if not after["text"].strip():
                raise AssertionError(
                    f"Preprocessing emptied {after['record_id']}."
                )

            processing = after.get("preprocessing")
            if not processing:
                raise AssertionError(
                    f"Missing preprocessing metadata: "
                    f"{after['record_id']}"
                )
            if processing.get("semantic_rewrite") is not False:
                raise AssertionError(
                    "Preprocessing must not claim semantic rewriting."
                )

        print(
            f"PASS: {document_id} "
            f"({len(clean)} records; provenance preserved)"
        )

    print()
    print("=" * 60)
    print(
        f"DC-GUARDIAN RAG PREPROCESSING CONTRACT PASSED: "
        f"{len(ids)}/{len(ids)}"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()
