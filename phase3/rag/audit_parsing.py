"""
Audit parsed RAG source quality before chunking/embedding.

Produces a JSON report and exits non-zero only for hard failures. Soft
quality warnings are reported for human review.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


RAG_ROOT = Path(__file__).resolve().parent
LOCK_FILE = RAG_ROOT / "manifests" / "source_lock.json"
PARSED_DIR = RAG_ROOT / "knowledge_base" / "parsed"
REPORT_FILE = RAG_ROOT / "evaluation" / "parsing_quality_report.json"

MIN_RECORD_CHARS = 80
LONG_RECORD_CHARS = 12000
MAX_EMPTY_RATIO = 0.05


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records


def normalized_lines(text: str) -> list[str]:
    lines = []
    for line in text.splitlines():
        value = re.sub(r"\s+", " ", line).strip()
        if len(value) >= 8:
            lines.append(value)
    return lines


def audit_document(document_id: str) -> dict:
    path = PARSED_DIR / f"{document_id}.jsonl"
    if not path.is_file():
        return {
            "document_id": document_id,
            "status": "FAIL",
            "errors": ["Missing parsed JSONL output."],
            "warnings": [],
        }

    records = load_jsonl(path)
    errors = []
    warnings = []

    if not records:
        errors.append("No parsed records.")
        return {
            "document_id": document_id,
            "status": "FAIL",
            "errors": errors,
            "warnings": warnings,
        }

    lengths = [len(item.get("text", "")) for item in records]
    total_chars = sum(lengths)
    short_records = sum(length < MIN_RECORD_CHARS for length in lengths)
    long_records = sum(length > LONG_RECORD_CHARS for length in lengths)

    all_text = "\n".join(item["text"] for item in records)
    replacement_chars = all_text.count("\ufffd")
    null_chars = all_text.count("\x00")
    hyphen_linebreaks = len(re.findall(r"[A-Za-z]-\n[A-Za-z]", all_text))

    line_counter = Counter()
    for record in records:
        line_counter.update(set(normalized_lines(record["text"])))

    repeated_lines = [
        {"text": line, "record_count": count}
        for line, count in line_counter.most_common(20)
        if count >= max(3, int(len(records) * 0.20))
    ]

    duplicate_texts = (
        len(records)
        - len({item["text"] for item in records})
    )

    if short_records / len(records) > MAX_EMPTY_RATIO:
        warnings.append(
            f"{short_records}/{len(records)} records contain fewer than "
            f"{MIN_RECORD_CHARS} characters."
        )
    if long_records:
        warnings.append(
            f"{long_records} records exceed {LONG_RECORD_CHARS} characters."
        )
    if repeated_lines:
        warnings.append(
            "Potential repeated header/footer lines detected."
        )
    if duplicate_texts:
        warnings.append(
            f"{duplicate_texts} exact duplicate text records detected."
        )
    if replacement_chars:
        warnings.append(
            f"{replacement_chars} Unicode replacement characters detected."
        )
    if null_chars:
        errors.append(
            f"{null_chars} NUL characters remain after parsing."
        )
    if hyphen_linebreaks:
        warnings.append(
            f"{hyphen_linebreaks} possible line-break hyphenations detected."
        )

    sample_indexes = sorted(
        set([0, len(records) // 2, len(records) - 1])
    )
    samples = [
        {
            "record_id": records[index]["record_id"],
            "page": records[index].get("page"),
            "preview": re.sub(
                r"\s+", " ", records[index]["text"]
            )[:500],
        }
        for index in sample_indexes
    ]

    return {
        "document_id": document_id,
        "status": "FAIL" if errors else (
            "REVIEW" if warnings else "PASS"
        ),
        "record_count": len(records),
        "total_characters": total_chars,
        "min_record_characters": min(lengths),
        "median_record_characters": sorted(lengths)[len(lengths) // 2],
        "max_record_characters": max(lengths),
        "short_record_count": short_records,
        "long_record_count": long_records,
        "exact_duplicate_record_count": duplicate_texts,
        "replacement_character_count": replacement_chars,
        "possible_hyphen_linebreak_count": hyphen_linebreaks,
        "repeated_line_candidates": repeated_lines,
        "warnings": warnings,
        "errors": errors,
        "samples": samples,
    }


def main() -> None:
    lock = load_json(LOCK_FILE)
    document_ids = sorted(
        item["document_id"]
        for item in lock["sources"]
    )

    reports = [
        audit_document(document_id)
        for document_id in document_ids
    ]

    summary = {
        "documents": len(reports),
        "pass": sum(item["status"] == "PASS" for item in reports),
        "review": sum(item["status"] == "REVIEW" for item in reports),
        "fail": sum(item["status"] == "FAIL" for item in reports),
    }

    output = {
        "report_version": "1.0",
        "purpose": (
            "Pre-chunking extraction-quality audit. REVIEW is not a "
            "failure; it identifies documents requiring inspection."
        ),
        "summary": summary,
        "documents": reports,
    }

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_FILE.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    for item in reports:
        print(
            f"{item['status']:6} {item['document_id']}"
            + (
                f" | records={item.get('record_count')} "
                f"chars={item.get('total_characters')}"
                if "record_count" in item else ""
            )
        )
        for warning in item.get("warnings", []):
            print(f"       WARN: {warning}")
        for error in item.get("errors", []):
            print(f"       ERROR: {error}")

    print()
    print("=" * 60)
    print("RAG PARSING QUALITY AUDIT")
    print("=" * 60)
    print(f"Documents: {summary['documents']}")
    print(f"PASS:      {summary['pass']}")
    print(f"REVIEW:    {summary['review']}")
    print(f"FAIL:      {summary['fail']}")
    print(f"Report:    {REPORT_FILE}")

    if summary["fail"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
