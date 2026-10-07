"""Build the DC-GUARDIAN Phase 3.1 local embedding index."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from response.rag.config import (
    LOCAL_EMBEDDING_BATCH_SIZE,
    LOCAL_EMBEDDING_MODEL,
    LOCAL_EMBEDDING_REVISION,
)


RAG_ROOT = Path(__file__).resolve().parent
CHUNK_DIR = RAG_ROOT / "knowledge_base" / "chunks"
LOCK_FILE = RAG_ROOT / "manifests" / "source_lock.json"
INDEX_DIR = RAG_ROOT / "vector_store" / "local_v1"
VECTORS_FILE = INDEX_DIR / "vectors.npy"
METADATA_FILE = INDEX_DIR / "chunks.jsonl"
BUILD_FILE = INDEX_DIR / "index_build.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_chunks() -> list[dict]:
    rows = []
    for path in sorted(CHUNK_DIR.glob("*.jsonl")):
        with path.open("r", encoding="utf-8") as handle:
            rows.extend(
                json.loads(line)
                for line in handle
                if line.strip()
            )
    if not rows:
        raise RuntimeError("No frozen RAG chunks found.")
    return rows


def main() -> None:
    chunks = load_chunks()
    texts = [item["text"] for item in chunks]

    model = SentenceTransformer(
        LOCAL_EMBEDDING_MODEL,
        revision=LOCAL_EMBEDDING_REVISION,
    )
    vectors = model.encode(
        texts,
        batch_size=LOCAL_EMBEDDING_BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype(np.float32)

    if vectors.shape[0] != len(chunks):
        raise RuntimeError("Embedding row count does not match chunk count.")

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    np.save(VECTORS_FILE, vectors)

    with METADATA_FILE.open("w", encoding="utf-8") as handle:
        for item in chunks:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")

    lock_hash = sha256_file(LOCK_FILE)
    metadata_hash = sha256_file(METADATA_FILE)
    vectors_hash = sha256_file(VECTORS_FILE)

    build = {
        "index_schema_version": "1.0",
        "index_id": (
            f"local-v1-{metadata_hash[:12]}-{vectors_hash[:12]}"
        ),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "embedding_provider": "LOCAL_SENTENCE_TRANSFORMERS",
        "embedding_model": LOCAL_EMBEDDING_MODEL,
        "embedding_revision_requested": LOCAL_EMBEDDING_REVISION,
        "embedding_dimension": int(vectors.shape[1]),
        "normalized_embeddings": True,
        "similarity": "cosine_via_dot_product",
        "chunking_version": "v1",
        "source_count": len({x["document_id"] for x in chunks}),
        "chunk_count": len(chunks),
        "source_lock_sha256": lock_hash,
        "chunk_metadata_sha256": metadata_hash,
        "vectors_sha256": vectors_hash,
    }

    with BUILD_FILE.open("w", encoding="utf-8") as handle:
        json.dump(build, handle, indent=2)
        handle.write("\n")

    print("=" * 60)
    print("DC-GUARDIAN LOCAL RAG INDEX BUILT")
    print("=" * 60)
    print(f"Index ID:   {build['index_id']}")
    print(f"Sources:    {build['source_count']}")
    print(f"Chunks:     {build['chunk_count']}")
    print(f"Dimension:  {build['embedding_dimension']}")
    print(f"Model:      {build['embedding_model']}")
    print(f"Index path: {INDEX_DIR}")


if __name__ == "__main__":
    main()

