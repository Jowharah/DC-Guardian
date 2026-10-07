"""Structured local retrieval API for DC-GUARDIAN Response RAG."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from response.rag.config import (
    ABSTENTION_THRESHOLD,
    LOCAL_EMBEDDING_MODEL,
    LOCAL_EMBEDDING_REVISION,
)


RAG_ROOT = Path(__file__).resolve().parent
INDEX_DIR = RAG_ROOT / "vector_store" / "local_v1"
VECTORS_FILE = INDEX_DIR / "vectors.npy"
METADATA_FILE = INDEX_DIR / "chunks.jsonl"
BUILD_FILE = INDEX_DIR / "index_build.json"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_metadata() -> list[dict]:
    with METADATA_FILE.open("r", encoding="utf-8") as handle:
        return [
            json.loads(line)
            for line in handle
            if line.strip()
        ]


def retrieve_knowledge(
    query: str,
    *,
    domains: list[str] | None = None,
    top_k: int = 5,
    ranking: str = "controlled",
    abstain: bool = False,
) -> list[dict]:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string.")
    if not isinstance(top_k, int) or top_k < 1 or top_k > 50:
        raise ValueError("top_k must be an integer from 1 to 50.")
    if ranking not in {"raw", "diverse", "controlled"}:
        raise ValueError(
            "ranking must be 'raw', 'diverse', or 'controlled'."
        )

    requested_domains = None
    if domains is not None:
        if not isinstance(domains, list) or not domains:
            raise ValueError("domains must be a non-empty list when supplied.")
        requested_domains = {str(x).upper() for x in domains}

    build = _load_json(BUILD_FILE)
    metadata = _load_metadata()
    vectors = np.load(VECTORS_FILE, allow_pickle=False)

    if len(metadata) != vectors.shape[0]:
        raise RuntimeError("Index metadata/vector row mismatch.")

    eligible = []
    for index, item in enumerate(metadata):
        if requested_domains is not None:
            applicable = {x.upper() for x in item["applicable_domains"]}
            if not applicable.intersection(requested_domains):
                continue
        eligible.append(index)

    if not eligible:
        return []

    # Retrieval is intentionally offline after the model has been
    # downloaded during index construction. This avoids network dependence
    # and prevents Hugging Face certificate/availability issues at runtime.
    model = SentenceTransformer(
        LOCAL_EMBEDDING_MODEL,
        revision=LOCAL_EMBEDDING_REVISION,
        local_files_only=True,
    )
    query_vector = model.encode(
        [query.strip()],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )[0].astype(np.float32)

    eligible_array = np.asarray(eligible, dtype=np.int64)
    scores = vectors[eligible_array] @ query_vector
    raw_order = list(np.argsort(-scores))

    if ranking == "raw":
        order = raw_order[:top_k]
    elif ranking == "diverse":
        # Diversity policy v2: take the strongest chunk from each document
        # first, then fill remaining slots by raw similarity. This changes
        # ranking only; embeddings, scores, chunks, and filtering are unchanged.
        first_per_document = []
        deferred = []
        seen_documents = set()
        for position in raw_order:
            row_index = int(eligible_array[position])
            document_id = metadata[row_index]["document_id"]
            if document_id not in seen_documents:
                first_per_document.append(position)
                seen_documents.add(document_id)
            else:
                deferred.append(position)

        order = first_per_document[:top_k]
        if len(order) < top_k:
            order.extend(deferred[: top_k - len(order)])
    else:
        # Controlled diversity v3. Preserve raw relevance ordering but cap
        # duplicate chunks from one document. This is a policy parameter,
        # not a similarity-score threshold and does not alter embeddings.
        MAX_CHUNKS_PER_DOCUMENT = 2
        order = []
        per_document = {}
        deferred = []
        for position in raw_order:
            row_index = int(eligible_array[position])
            document_id = metadata[row_index]["document_id"]
            count = per_document.get(document_id, 0)
            if count < MAX_CHUNKS_PER_DOCUMENT:
                order.append(position)
                per_document[document_id] = count + 1
            else:
                deferred.append(position)
            if len(order) >= top_k:
                break

        if len(order) < top_k:
            for position in deferred:
                order.append(position)
                if len(order) >= top_k:
                    break

    if abstain:
        best_score = float(scores[raw_order[0]]) if raw_order else 0.0
        if best_score < ABSTENTION_THRESHOLD:
            return []

    results = []
    for rank, position in enumerate(order, start=1):
        row_index = int(eligible_array[position])
        item = metadata[row_index]
        results.append({
            "rank": rank,
            "score": float(scores[position]),
            "chunk_id": item["chunk_id"],
            "document_id": item["document_id"],
            "title": item["title"],
            "primary_domain": item["primary_domain"],
            "applicable_domains": item["applicable_domains"],
            "authority_type": item["authority_type"],
            "publisher": item["publisher"],
            "version": item.get("version"),
            "pages": item["pages"],
            "text": item["text"],
            "source_url": item.get("source_url"),
            "source_sha256": item["source_sha256"],
            "index_id": build["index_id"],
            "embedding_model": build["embedding_model"],
            "ranking_policy": ranking,
        })

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--domain", action="append", dest="domains")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--abstain",
        action="store_true",
        help="Return no evidence when calibrated support threshold is not met.",
    )
    parser.add_argument(
        "--ranking",
        choices=["raw", "diverse", "controlled"],
        default="controlled",
    )
    args = parser.parse_args()

    print(json.dumps(
        retrieve_knowledge(
            args.query,
            domains=args.domains,
            top_k=args.top_k,
            ranking=args.ranking,
            abstain=args.abstain,
        ),
        indent=2,
        ensure_ascii=False,
    ))

