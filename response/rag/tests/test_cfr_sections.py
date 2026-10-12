"""CFR section trimming: an OSHA document keeps only its own section (pytest or `python <file>`)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from response.rag.preprocess_sources import cfr_section, trim_to_cfr_section  # noqa: E402

SIGN = "�"  # the section sign as the PDF text layer delivers it


def page(number, text):
    return {"page": number, "text": text}


def test_section_number_comes_from_the_document_id():
    assert cfr_section("OSHA-1910-135") == "135"
    assert cfr_section("OSHA-1910-38") == "38"
    assert cfr_section("NIST-SP-800-53R5-PE") is None


def test_single_page_keeps_only_its_own_section():
    text = (f"450 29 CFR Ch. XVII {SIGN} 1910.135\n4. Keep track of your respirator.\n"
            f"{SIGN} 1910.135 Head protection.\n(a) The employer shall ensure each employee wears a protective helmet.\n"
            f"{SIGN} 1910.136 Foot protection.\n(a) Protective footwear.")
    (record, before, after), = trim_to_cfr_section([page(1, text)], "135")
    assert record["text"].startswith(f"{SIGN} 1910.135 Head protection.")
    assert "respirator" not in record["text"] and "Foot protection" not in record["text"]
    assert before > 0 and after > 0


def test_multi_page_section_drops_pages_before_and_after():
    pages = [page(1, f"tail of 1910.131\n{SIGN} 1910.132 General requirements.\n(a) Application."),
             page(2, f"{SIGN} 1910.133\n(2) Each affected employee shall demonstrate training. "
                     f"See {SIGN} 1910.134 and 1910.137.\n{SIGN} 1910.133 Eye and face protection."),
             page(3, "unrelated later page")]
    kept = trim_to_cfr_section(pages, "132")
    assert [r["page"] for r, _, _ in kept] == [1, 2]
    assert kept[0][0]["text"].startswith(f"{SIGN} 1910.132 General requirements.")
    # A running header ("1910.133" + line break) and a cross-reference do not end the section.
    assert "Each affected employee shall demonstrate training" in kept[1][0]["text"]
    assert "Eye and face protection" not in kept[1][0]["text"]


def test_missing_heading_keeps_the_document_whole():
    pages = [page(1, "no section heading here"), page(2, "more text")]
    assert [(r["text"], b, a) for r, b, a in trim_to_cfr_section(pages, "135")] == [
        ("no section heading here", 0, 0), ("more text", 0, 0)]


def main():
    test_section_number_comes_from_the_document_id()
    test_single_page_keeps_only_its_own_section()
    test_multi_page_section_drops_pages_before_and_after()
    test_missing_heading_keeps_the_document_whole()
    print("=" * 60)
    print("DC-GUARDIAN RAG CFR SECTION CONTRACT PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
