"""
Conservatively preprocess parsed DC-GUARDIAN RAG records.

This stage removes repeated PDF header/footer lines, repairs clear
alphabetic line-break hyphenation, and preserves page/source provenance.
It does not chunk, summarize, translate, or semantically rewrite content.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


RAG_ROOT = Path(__file__).resolve().parent
PARSED_DIR = RAG_ROOT / "knowledge_base" / "parsed"
CLEAN_DIR = RAG_ROOT / "knowledge_base" / "clean"
LOCK_FILE = RAG_ROOT / "manifests" / "source_lock.json"

REPEAT_MIN_RECORDS = 3
REPEAT_RATIO = 0.20


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


def normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def repeated_line_set(records: list[dict]) -> set[str]:
    if len(records) < REPEAT_MIN_RECORDS:
        return set()

    counts = Counter()
    for record in records:
        unique = {
            normalize_line(line)
            for line in record["text"].splitlines()
            if len(normalize_line(line)) >= 8
        }
        counts.update(unique)

    threshold = max(
        REPEAT_MIN_RECORDS,
        int(len(records) * REPEAT_RATIO),
    )

    repeated = set()
    for line, count in counts.items():
        if count < threshold:
            continue

        # Conservative header/footer candidates: short repeated lines,
        # publication identifiers, or simple page-number phrases.
        if (
            len(line) <= 140
            or re.fullmatch(r"(?:page\s+)?\d+(?:\s+of\s+\d+)?", line, re.I)
        ):
            repeated.add(line)

    return repeated


def remove_repeated_lines(text: str, repeated: set[str]) -> tuple[str, int]:
    kept = []
    removed = 0
    for line in text.splitlines():
        normalized = normalize_line(line)
        if normalized and normalized in repeated:
            removed += 1
            continue
        kept.append(line)
    return "\n".join(kept), removed


def dehyphenate_linebreaks(text: str) -> tuple[str, int]:
    # Join only alphabetic word fragments split by a hyphen at a line break.
    # Existing same-line hyphenated terms remain untouched.
    pattern = re.compile(r"(?<=[A-Za-z])-[ \t]*\n[ \t]*(?=[A-Za-z])")
    return pattern.subn("", text)


def repair_known_encoding_artifacts(
    text: str,
    document_id: str,
) -> tuple[str, int]:
    """
    Repair only the reviewed DOE O&M extraction mojibake.

    The sequence below represents a separator/bullet boundary in this
    specific source. Preserve the boundary as a newline rather than
    deleting it.
    """
    if document_id != "DOE-FEMP-OM-BEST-PRACTICES":
        return text, 0

    # pypdf emits U+FFFD for the reviewed separator/bullet glyphs in
    # this specific DOE source.
    artifact = "\ufffd"
    count = text.count(artifact)
    return text.replace(artifact, "\n"), count


def normalize_whitespace(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def replacement_contexts(text: str, limit: int = 20) -> list[str]:
    contexts = []
    for match in re.finditer("\ufffd", text):
        start = max(0, match.start() - 60)
        end = min(len(text), match.end() + 60)
        contexts.append(
            re.sub(r"\s+", " ", text[start:end])
        )
        if len(contexts) >= limit:
            break
    return contexts


def main() -> None:
    lock = load_json(LOCK_FILE)
    document_ids = sorted(
        item["document_id"]
        for item in lock["sources"]
    )

    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    failures = 0

    for document_id in document_ids:
        source_path = PARSED_DIR / f"{document_id}.jsonl"
        try:
            records = load_jsonl(source_path)
            repeated = repeated_line_set(records)

            cleaned_records = []
            removed_total = 0
            dehyphenated_total = 0
            replacement_total = 0
            replacement_samples = []
            encoding_repairs_total = 0

            for record in records:
                text, removed = remove_repeated_lines(
                    record["text"], repeated
                )
                text, dehyphenated = dehyphenate_linebreaks(text)
                text, encoding_repairs = repair_known_encoding_artifacts(
                    text,
                    document_id,
                )
                text = normalize_whitespace(text)

                encoding_repairs_total += encoding_repairs
                replacement_total += text.count("\ufffd")
                if "\ufffd" in text and len(replacement_samples) < 20:
                    replacement_samples.extend(
                        replacement_contexts(
                            text,
                            20 - len(replacement_samples),
                        )
                    )

                output = dict(record)
                output["text"] = text
                output["preprocessing"] = {
                    "repeated_lines_removed": removed,
                    "linebreak_hyphens_joined": dehyphenated,
                    "known_encoding_artifacts_repaired": encoding_repairs,
                    "semantic_rewrite": False,
                }
                cleaned_records.append(output)
                removed_total += removed
                dehyphenated_total += dehyphenated

            output_path = CLEAN_DIR / f"{document_id}.jsonl"
            with output_path.open("w", encoding="utf-8") as handle:
                for record in cleaned_records:
                    handle.write(
                        json.dumps(record, ensure_ascii=False) + "\n"
                    )

            if replacement_samples:
                review_path = (
                    CLEAN_DIR
                    / f"{document_id}.replacement_review.json"
                )
                with review_path.open("w", encoding="utf-8") as handle:
                    json.dump(
                        {
                            "document_id": document_id,
                            "replacement_character_count": replacement_total,
                            "contexts": replacement_samples,
                            "action": (
                                "REVIEW_CONTEXTS_BEFORE_REPLACING_OR_REMOVING"
                            ),
                        },
                        handle,
                        indent=2,
                        ensure_ascii=False,
                    )
                    handle.write("\n")

            print(
                f"PASS: {document_id} | "
                f"records={len(cleaned_records)} "
                f"headers/footers_removed={removed_total} "
                f"dehyphenated={dehyphenated_total} "
                f"encoding_repairs={encoding_repairs_total} "
                f"replacement_chars={replacement_total}"
            )
        except Exception as error:
            failures += 1
            print(f"FAIL: {document_id}: {error}")

    print()
    print(f"Documents: {len(document_ids)}")
    print(f"Failures:  {failures}")
    print(f"Output:    {CLEAN_DIR}")

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
