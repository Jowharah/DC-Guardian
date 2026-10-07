"""Security contract for DC-GUARDIAN Response RAG source fetching."""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from response.rag.fetch_sources import (
    ValidatingRedirectHandler,
    validate_document_id,
    validate_url,
)


def expect_rejected(fn, value, label):
    try:
        fn(value)
    except ValueError:
        print(f"PASS: rejected {label}")
        return
    raise AssertionError(f"Security boundary accepted {label}: {value!r}")


def main():
    validate_url("https://csrc.nist.gov/test")
    validate_url("https://www.cisa.gov/test")
    print("PASS: approved HTTPS hosts accepted.")

    for url, label in [
        ("http://csrc.nist.gov/test", "non-HTTPS URL"),
        ("file:///etc/passwd", "file URL"),
        ("https://localhost/test", "localhost"),
        ("https://127.0.0.1/test", "loopback IP"),
        ("https://example.com/test", "unapproved host"),
        (
            "https://user:password@csrc.nist.gov/test",
            "embedded credentials",
        ),
        ("https://csrc.nist.gov:8443/test", "nonstandard HTTPS port"),
    ]:
        expect_rejected(validate_url, url, label)

    for document_id in [
        "../escape",
        "..\\escape",
        "folder/file",
        "folder\\file",
        "",
    ]:
        expect_rejected(
            validate_document_id,
            document_id,
            f"document_id {document_id!r}",
        )

    validate_document_id("NIST-SP-800-53R5-PE")
    print("PASS: approved document_id accepted.")

    handler = ValidatingRedirectHandler()
    expect_rejected(
        lambda url: handler.redirect_request(
            None, None, 302, "Found", {}, url
        ),
        "https://127.0.0.1/internal",
        "unsafe redirect target before follow",
    )

    print("=" * 60)
    print("DC-GUARDIAN RAG SOURCE FETCH SECURITY CONTRACT PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
