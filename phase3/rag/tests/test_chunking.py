"""Contract checks for DC-GUARDIAN RAG chunks."""

from __future__ import annotations

import json
from pathlib import Path
import sys

RAG_ROOT = Path(__file__).resolve().parents[1]
LOCK_FILE = RAG_ROOT / "manifests" / "source_lock.json"
CHUNK_DIR = RAG_ROOT / "knowledge_base" / "chunks"
sys.path.insert(0, str(RAG_ROOT))
from config import MAX_CHUNK_WORDS  # noqa: E402

REQUIRED = {
    "chunk_id","chunk_index","document_id","title","primary_domain",
    "applicable_domains","authority_type","source_type","publisher","version",
    "source_sha256","pages","source_record_ids","retrieval_scope",
    "word_count","text",
}


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main():
    lock=load_json(LOCK_FILE)
    ids=sorted(x["document_id"] for x in lock["sources"])
    all_ids=set()
    for document_id in ids:
        path=CHUNK_DIR/f"{document_id}.jsonl"
        if not path.is_file():
            raise AssertionError(f"Missing chunks: {document_id}")
        rows=[json.loads(x) for x in path.open(encoding="utf-8") if x.strip()]
        if not rows:
            raise AssertionError(f"No chunks: {document_id}")
        for i,row in enumerate(rows):
            missing=REQUIRED-row.keys()
            if missing:
                raise AssertionError(f"{document_id} missing {sorted(missing)}")
            if row["document_id"] != document_id:
                raise AssertionError("Document identity changed.")
            if row["chunk_index"] != i:
                raise AssertionError(f"Non-deterministic chunk index: {document_id}")
            if row["chunk_id"] in all_ids:
                raise AssertionError(f"Duplicate chunk ID: {row['chunk_id']}")
            all_ids.add(row["chunk_id"])
            if not row["text"].strip() or row["word_count"] != len(row["text"].split()):
                raise AssertionError(f"Invalid chunk text/count: {row['chunk_id']}")
            if not row["source_sha256"]:
                raise AssertionError(f"Missing source hash: {row['chunk_id']}")
            if row["word_count"] > MAX_CHUNK_WORDS:
                raise AssertionError(
                    f"Chunk exceeds configured maximum: {row['chunk_id']} "
                    f"({row['word_count']} > {MAX_CHUNK_WORDS})"
                )
        if document_id == "NIST-SP-800-53R5-PE":
            combined = "\n".join(row["text"].upper() for row in rows)
            for control in ("PE-2", "PE-3", "PE-6"):
                if control not in combined:
                    raise AssertionError(
                        f"NIST retrieval scope missing {control}."
                    )
            if any(row["retrieval_scope"] != "EXPLICIT_CONTROL_RANGES" for row in rows):
                raise AssertionError("NIST chunks do not record control-range scope.")

        print(f"PASS: {document_id} ({len(rows)} chunks)")

    print()
    print("="*60)
    print(f"DC-GUARDIAN RAG CHUNKING CONTRACT PASSED: {len(ids)}/{len(ids)}")
    print("="*60)


if __name__=="__main__":
    main()
