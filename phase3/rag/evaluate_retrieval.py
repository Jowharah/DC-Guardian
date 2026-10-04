"""Evaluate DC-GUARDIAN RAG retrieval against frozen v2 cases."""

from __future__ import annotations

import json
import math
import statistics
import sys
import time
from pathlib import Path

RAG_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(RAG_ROOT))

from retrieve import retrieve_knowledge  # noqa: E402


CASES_FILE = RAG_ROOT / "evaluation" / "retrieval_cases.json"
REPORT_FILE = RAG_ROOT / "evaluation" / "retrieval_evaluation_report.json"
K_VALUES = (1, 3, 5)


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def unique_documents(results: list[dict], k: int) -> list[str]:
    """Return first-seen unique document IDs from the top-k chunks."""
    seen = set()
    documents = []
    for result in results[:k]:
        document_id = result["document_id"]
        if document_id not in seen:
            seen.add(document_id)
            documents.append(document_id)
    return documents


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ranking",
        choices=["raw", "diverse"],
        default="diverse",
    )
    args = parser.parse_args()

    spec = load_json(CASES_FILE)
    cases = spec["cases"]

    metric_rows = []
    latencies_ms = []
    provenance_ok = 0
    filter_ok = 0
    negative_ok = 0
    negative_total = 0

    for case in cases:
        started = time.perf_counter()
        results = retrieve_knowledge(
            case["query"],
            domains=case.get("domains"),
            top_k=max(K_VALUES),
            ranking=args.ranking,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        latencies_ms.append(latency_ms)

        expected = set(case.get("expected_document_ids", []))
        excluded = set(case.get("excluded_document_ids", []))
        excluded_domains = set(case.get("excluded_domains", []))

        row = {
            "case_id": case["case_id"],
            "case_type": case["case_type"],
            "query": case["query"],
            "domains": case.get("domains"),
            "expected_document_ids": sorted(expected),
            "latency_ms": latency_ms,
            "retrieved": [
                {
                    "rank": item["rank"],
                    "document_id": item["document_id"],
                    "chunk_id": item["chunk_id"],
                    "score": item["score"],
                }
                for item in results
            ],
        }

        for k in K_VALUES:
            docs = unique_documents(results, k)
            retrieved_set = set(docs)
            relevant = len(expected.intersection(retrieved_set))
            row[f"hit@{k}"] = int(bool(relevant)) if expected else None
            row[f"recall@{k}"] = (
                relevant / len(expected) if expected else None
            )
            row[f"precision@{k}"] = (
                relevant / len(docs) if docs else 0.0
            ) if expected else None

        first_relevant_rank = next(
            (
                item["rank"]
                for item in results
                if item["document_id"] in expected
            ),
            None,
        )
        row["reciprocal_rank"] = (
            1.0 / first_relevant_rank
            if first_relevant_rank is not None
            else (None if not expected else 0.0)
        )

        row["provenance_correct"] = all(
            item.get("chunk_id")
            and item.get("document_id")
            and item.get("source_sha256")
            and item.get("index_id")
            and item.get("embedding_model")
            for item in results
        )
        provenance_ok += int(row["provenance_correct"])

        domain_correct = True
        if case.get("domains"):
            requested = set(case["domains"])
            # Filtering is inclusive: a multi-domain source is eligible when
            # at least one applicable domain matches the requested set.
            domain_correct = all(
                requested.intersection(set(item["applicable_domains"]))
                for item in results
            )
        if excluded_domains:
            # excluded_domains describes domains that must not be retrieved as
            # the source's PRIMARY domain. A valid multi-domain source should
            # not fail merely because an excluded label is also applicable.
            domain_correct = domain_correct and all(
                item["primary_domain"] not in excluded_domains
                for item in results
            )
        row["filter_correct"] = domain_correct
        filter_ok += int(domain_correct)

        row["excluded_document_correct"] = all(
            item["document_id"] not in excluded
            for item in results
        )

        is_negative = case["case_type"].startswith("negative")
        if is_negative:
            negative_total += 1
            if expected:
                negative_case_ok = (
                    row["excluded_document_correct"]
                    and bool(expected.intersection(unique_documents(results, 5)))
                )
            else:
                # No approved source is expected. Because semantic retrieval
                # always returns nearest neighbors, this baseline records the
                # case as unsupported until an abstention/threshold policy is
                # explicitly designed and evaluated.
                negative_case_ok = len(results) == 0
            row["negative_case_correct"] = negative_case_ok
            negative_ok += int(negative_case_ok)
        else:
            row["negative_case_correct"] = None

        metric_rows.append(row)

        docs5 = unique_documents(results, 5)
        print(
            f"{case['case_id']} | {case['case_type']:<24} "
            f"| top_docs={docs5} | {latency_ms:.1f} ms"
        )

    aggregate = {
        "evaluation_version": spec["evaluation_version"],
        "ranking_policy": args.ranking,
        "case_count": len(cases),
        "k_values": list(K_VALUES),
        "metrics": {},
        "mrr": statistics.mean(
            row["reciprocal_rank"]
            for row in metric_rows
            if row["reciprocal_rank"] is not None
        ),
        "filter_correctness": filter_ok / len(cases),
        "provenance_correctness": provenance_ok / len(cases),
        "negative_case_correctness": (
            negative_ok / negative_total if negative_total else None
        ),
        "negative_case_count": negative_total,
        "latency_ms": {
            "mean": statistics.mean(latencies_ms),
            "median": statistics.median(latencies_ms),
            "p95": percentile(latencies_ms, 0.95),
            "max": max(latencies_ms),
        },
    }

    positive_rows = [
        row for row in metric_rows
        if row["expected_document_ids"]
    ]
    for k in K_VALUES:
        aggregate["metrics"][f"hit_rate@{k}"] = statistics.mean(
            row[f"hit@{k}"] for row in positive_rows
        )
        aggregate["metrics"][f"recall@{k}"] = statistics.mean(
            row[f"recall@{k}"] for row in positive_rows
        )
        aggregate["metrics"][f"precision@{k}"] = statistics.mean(
            row[f"precision@{k}"] for row in positive_rows
        )

    report = {
        "aggregate": aggregate,
        "cases": metric_rows,
        "notes": [
            "Document-level metrics deduplicate repeated chunks by document_id.",
            "The frozen expected-document labels are not modified by retrieval output.",
            "The no-approved-source case is expected to expose the need for an explicit abstention policy in a nearest-neighbor retriever.",
        ],
    }
    with REPORT_FILE.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")

    print()
    print("=" * 60)
    print(
        "DC-GUARDIAN RAG RETRIEVAL BASELINE "
        f"({args.ranking.upper()} RANKING)"
    )
    print("=" * 60)
    for name, value in aggregate["metrics"].items():
        print(f"{name:16} {value:.4f}")
    print(f"{'MRR':16} {aggregate['mrr']:.4f}")
    print(f"{'Filter correct':16} {aggregate['filter_correctness']:.4f}")
    print(f"{'Provenance':16} {aggregate['provenance_correctness']:.4f}")
    if aggregate["negative_case_correctness"] is not None:
        print(
            f"{'Negative cases':16} "
            f"{aggregate['negative_case_correctness']:.4f}"
        )
    print(
        f"{'Latency mean':16} "
        f"{aggregate['latency_ms']['mean']:.1f} ms"
    )
    print(
        f"{'Latency p95':16} "
        f"{aggregate['latency_ms']['p95']:.1f} ms"
    )
    print(f"Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()
