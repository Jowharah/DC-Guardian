"""Integrated verification for DC-GUARDIAN Response RAG RAG foundation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAG_ROOT = ROOT / "response" / "rag"
LOCK_FILE = RAG_ROOT / "manifests" / "source_lock.json"
CHUNK_DIR = RAG_ROOT / "knowledge_base" / "chunks"
BUILD_FILE = RAG_ROOT / "vector_store" / "local_v1" / "index_build.json"

CHECKS = [
    ("Parsing contract", RAG_ROOT / "tests" / "test_parsing.py"),
    ("Preprocessing contract", RAG_ROOT / "tests" / "test_preprocessing.py"),
    ("Chunking contract", RAG_ROOT / "tests" / "test_chunking.py"),
    ("Local retrieval contract", RAG_ROOT / "tests" / "test_retrieval_contract.py"),
    ("Knowledge eligibility contract", RAG_ROOT / "tests" / "test_knowledge_eligibility.py"),
]


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def count_chunks() -> int:
    total = 0
    for path in CHUNK_DIR.glob("*.jsonl"):
        with path.open("r", encoding="utf-8") as handle:
            total += sum(1 for line in handle if line.strip())
    return total


def main() -> None:
    print("=" * 60)
    print("DC-GUARDIAN RESPONSE RAG VERIFICATION")
    print("=" * 60)

    failures = []

    lock = load_json(LOCK_FILE)
    build = load_json(BUILD_FILE)

    if len(lock.get("sources", [])) == 13:
        print("PASS: Source corpus integrity (13 locked sources).")
    else:
        failures.append("Source corpus integrity")
        print("FAIL: Source corpus integrity.")

    for label, script in CHECKS:
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if result.returncode == 0:
            print(f"PASS: {label}.")
        else:
            failures.append(label)
            print(f"FAIL: {label}.")
            print(result.stdout)

    chunks = count_chunks()
    if chunks != build.get("chunk_count"):
        failures.append("Chunk/index count consistency")
        print(
            "FAIL: Chunk/index count consistency "
            f"({chunks} local vs {build.get('chunk_count')} indexed)."
        )
    else:
        print(
            f"PASS: Chunk/index count consistency ({chunks} chunks)."
        )

    print()
    print(f"RAG sources:            {len(lock.get('sources', []))}")
    print(f"RAG chunks:             {chunks}")
    print(f"Embedding model:        {build.get('embedding_model')}")
    print("Selected ranking:       CONTROLLED")
    print("Default evidence depth: TOP-3")
    print("Knowledge eligibility:  DETERMINISTIC")
    print("Cosine abstention:      EXPERIMENTAL / NOT DEFAULT")

    print()
    print("=" * 60)
    if failures:
        print(
            "DC-GUARDIAN RESPONSE RAG RAG FOUNDATION FAILED: "
            + ", ".join(failures)
        )
        print("=" * 60)
        raise SystemExit(1)

    print("DC-GUARDIAN RESPONSE RAG FOUNDATION PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()

