"""
DC-GUARDIAN Phase 3.1 approved-source fetcher.

Downloads only APPROVED + ACTIVE external knowledge sources from the
knowledge manifest into a local originals directory. Downloaded third-party
source files are intentionally not committed to Git.

Security/reproducibility controls:
- HTTPS only
- explicit authoritative-host allowlist
- redirect destination re-validation
- bounded download size
- atomic writes
- SHA-256 lock metadata
- no execution/deserialization of downloaded content
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen


RAG_ROOT = Path(__file__).resolve().parent
MANIFEST_FILE = RAG_ROOT / "manifests" / "knowledge_manifest.json"
ORIGINALS_DIR = RAG_ROOT / "knowledge_base" / "originals"
LOCK_FILE = RAG_ROOT / "manifests" / "source_lock.json"

ALLOWED_HOSTS = {
    "csrc.nist.gov",
    "www.cisa.gov",
    "www.energy.gov",
    "www.osha.gov",
}

MAX_SOURCE_BYTES = 30 * 1024 * 1024
CHUNK_BYTES = 1024 * 1024
USER_AGENT = "DC-GUARDIAN-RAG/1.0 (+research-prototype)"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"Only HTTPS sources are allowed: {url}")
    if parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError(
            f"Source host is not approved: {parsed.hostname}"
        )


def safe_filename(document_id: str, content_type: str, final_url: str) -> str:
    suffix = Path(urlparse(final_url).path).suffix.lower()
    if suffix not in {".pdf", ".html", ".htm", ".txt"}:
        suffix = ".pdf" if "application/pdf" in content_type.lower() else ".html"
    return f"{document_id}{suffix}"


def download_source(url: str, destination: Path) -> dict:
    validate_url(url)
    request = Request(url, headers={"User-Agent": USER_AGENT})

    with urlopen(request, timeout=60) as response:
        final_url = response.geturl()
        validate_url(final_url)

        content_type = response.headers.get(
            "Content-Type", "application/octet-stream"
        ).split(";", 1)[0].strip()

        declared_length = response.headers.get("Content-Length")
        if declared_length and int(declared_length) > MAX_SOURCE_BYTES:
            raise ValueError(
                f"Source exceeds {MAX_SOURCE_BYTES} bytes: {final_url}"
            )

        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(
            prefix=destination.name + ".",
            suffix=".tmp",
            dir=destination.parent,
        )

        total = 0
        try:
            with os.fdopen(fd, "wb") as output:
                while True:
                    chunk = response.read(CHUNK_BYTES)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_SOURCE_BYTES:
                        raise ValueError(
                            f"Source exceeded {MAX_SOURCE_BYTES} bytes while downloading."
                        )
                    output.write(chunk)
            os.replace(temp_name, destination)
        except Exception:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
            raise

    return {
        "final_url": final_url,
        "content_type": content_type,
        "size_bytes": total,
        "sha256": sha256_file(destination),
    }


def load_manifest() -> dict:
    with MANIFEST_FILE.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_lock() -> dict:
    if not LOCK_FILE.is_file():
        return {
            "lock_version": "1.0",
            "generated_utc": None,
            "sources": [],
        }
    with LOCK_FILE.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Re-download sources even when a locked local copy exists.",
    )
    args = parser.parse_args()

    manifest = load_manifest()
    lock = load_lock()
    locked_by_id = {
        item["document_id"]: item
        for item in lock.get("sources", [])
    }

    eligible = [
        source
        for source in manifest["sources"]
        if source.get("approval_status") == "APPROVED"
        and source.get("retrieval_status") == "ACTIVE"
        and source.get("source_type") == "EXTERNAL_AUTHORITATIVE"
    ]

    failures = []
    updated = []

    for source in eligible:
        document_id = source["document_id"]
        url = source.get("url")

        if not url:
            failures.append((document_id, "Missing source URL"))
            continue

        try:
            validate_url(url)
            existing = locked_by_id.get(document_id)

            if existing and not args.refresh:
                path = RAG_ROOT / existing["local_file"]
                if path.is_file():
                    actual = sha256_file(path)
                    if actual == existing["sha256"]:
                        print(f"SKIP: {document_id} (locked copy verified)")
                        updated.append(existing)
                        continue
                    raise RuntimeError(
                        "Local source exists but does not match its locked SHA-256. "
                        "Use --refresh only after reviewing the source change."
                    )

            # First request determines a safe extension. Download initially to
            # a neutral file, then rename according to returned content type.
            neutral = ORIGINALS_DIR / f"{document_id}.download"
            result = download_source(url, neutral)
            filename = safe_filename(
                document_id,
                result["content_type"],
                result["final_url"],
            )
            destination = ORIGINALS_DIR / filename
            if destination != neutral:
                os.replace(neutral, destination)

            record = {
                "document_id": document_id,
                "local_file": str(
                    destination.relative_to(RAG_ROOT)
                ).replace("\\", "/"),
                "requested_url": url,
                "final_url": result["final_url"],
                "content_type": result["content_type"],
                "size_bytes": result["size_bytes"],
                "sha256": result["sha256"],
                "fetched_utc": datetime.now(timezone.utc).isoformat(),
            }
            updated.append(record)
            print(
                f"PASS: {document_id} "
                f"({result['size_bytes']} bytes, {result['sha256'][:12]}...)"
            )
        except Exception as error:
            failures.append((document_id, str(error)))
            print(f"FAIL: {document_id}: {error}")

    lock["generated_utc"] = datetime.now(timezone.utc).isoformat()
    lock["sources"] = sorted(
        updated,
        key=lambda item: item["document_id"],
    )
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_FILE.open("w", encoding="utf-8") as handle:
        json.dump(lock, handle, indent=2)
        handle.write("\n")

    print()
    print(f"Eligible sources: {len(eligible)}")
    print(f"Locked sources:   {len(updated)}")
    print(f"Failures:         {len(failures)}")
    print(f"Lock file:        {LOCK_FILE}")

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
