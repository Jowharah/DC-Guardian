"""Contract test for the local DC-GUARDIAN retrieval API."""

from __future__ import annotations

import sys
from pathlib import Path

RAG_ROOT = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from phase3.rag.retrieve import retrieve_knowledge  # noqa: E402


REQUIRED = {
    "rank","score","chunk_id","document_id","title","primary_domain",
    "applicable_domains","authority_type","publisher","version","pages",
    "text","source_url","source_sha256","index_id","embedding_model",
    "ranking_policy",
}


def main() -> None:
    # The retrieval path must work from the already cached embedding model;
    # it must not require Hugging Face network access after index creation.
    rows = retrieve_knowledge(
        "physical access authorization and monitoring",
        domains=["PHYSICAL_SECURITY"],
        top_k=3,
    )
    if len(rows) != 3:
        raise AssertionError("top_k contract failed.")

    for expected_rank, row in enumerate(rows, start=1):
        missing = REQUIRED - row.keys()
        if missing:
            raise AssertionError(f"Missing result fields: {sorted(missing)}")
        if row["rank"] != expected_rank:
            raise AssertionError("Rank contract failed.")
        if "PHYSICAL_SECURITY" not in row["applicable_domains"]:
            raise AssertionError("Domain filter contract failed.")
        if not row["source_sha256"] or not row["index_id"]:
            raise AssertionError("Provenance contract failed.")

    if any(row["ranking_policy"] != "controlled" for row in rows):
        raise AssertionError("Default controlled-ranking contract failed.")

    if retrieve_knowledge(
        "head protection",
        domains=["NOT_A_REAL_DOMAIN"],
        top_k=5,
    ):
        raise AssertionError("Unknown-domain filter should return no results.")

    print("=" * 60)
    print("DC-GUARDIAN LOCAL RETRIEVAL CONTRACT PASSED")
    print("=" * 60)
    for row in rows:
        print(
            f"{row['rank']}. {row['document_id']} "
            f"score={row['score']:.4f} pages={row['pages']}"
        )


if __name__ == "__main__":
    main()
