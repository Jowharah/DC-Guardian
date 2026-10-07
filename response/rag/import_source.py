"""
Import a manually downloaded approved RAG source into the controlled corpus.

Use this for authoritative publishers that block automated downloads.
The source must already be APPROVED + ACTIVE in knowledge_manifest.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path


RAG_ROOT = Path(__file__).resolve().parent
MANIFEST_FILE = RAG_ROOT / "manifests" / "knowledge_manifest.json"
LOCK_FILE = RAG_ROOT / "manifests" / "source_lock.json"
ORIGINALS_DIR = RAG_ROOT / "knowledge_base" / "originals"
MAX_SOURCE_BYTES = 30 * 1024 * 1024
CHUNK_BYTES = 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path, default: dict | None = None) -> dict:
    if not path.is_file():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_pdf(path: Path) -> int:
    if not path.is_file():
        raise FileNotFoundError(f"Source file not found: {path}")

    size = path.stat().st_size
    if size <= 0:
        raise ValueError("Source file is empty.")
    if size > MAX_SOURCE_BYTES:
        raise ValueError(
            f"Source exceeds {MAX_SOURCE_BYTES} bytes."
        )

    with path.open("rb") as handle:
        if handle.read(5) != b"%PDF-":
            raise ValueError(
                "Manual source must be a valid PDF file."
            )

    return size


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--document-id", required=True)
    parser.add_argument("--file", required=True)
    args = parser.parse_args()

    source_path = Path(args.file).expanduser().resolve()
    size = validate_pdf(source_path)

    manifest = load_json(MANIFEST_FILE)
    source = next(
        (
            item
            for item in manifest["sources"]
            if item["document_id"] == args.document_id
        ),
        None,
    )

    if source is None:
        raise ValueError(
            f"Unknown document_id: {args.document_id}"
        )

    if not (
        source.get("approval_status") == "APPROVED"
        and source.get("retrieval_status") == "ACTIVE"
        and source.get("source_type") == "EXTERNAL_AUTHORITATIVE"
    ):
        raise ValueError(
            "Manual import is allowed only for APPROVED + ACTIVE "
            "external authoritative sources."
        )

    ORIGINALS_DIR.mkdir(parents=True, exist_ok=True)
    destination = ORIGINALS_DIR / f"{args.document_id}.pdf"

    fd, temp_name = tempfile.mkstemp(
        prefix=destination.name + ".",
        suffix=".tmp",
        dir=ORIGINALS_DIR,
    )
    os.close(fd)

    try:
        shutil.copyfile(source_path, temp_name)
        os.replace(temp_name, destination)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise

    digest = sha256_file(destination)

    lock = load_json(
        LOCK_FILE,
        {
            "lock_version": "1.0",
            "generated_utc": None,
            "sources": [],
        },
    )

    record = {
        "document_id": args.document_id,
        "local_file": str(
            destination.relative_to(RAG_ROOT)
        ).replace("\\", "/"),
        "requested_url": source.get("download_url") or source.get("url"),
        "final_url": source.get("download_url") or source.get("url"),
        "content_type": "application/pdf",
        "size_bytes": size,
        "sha256": digest,
        "fetched_utc": datetime.now(timezone.utc).isoformat(),
        "acquisition_method": "MANUAL_OFFICIAL_DOWNLOAD",
    }

    existing = {
        item["document_id"]: item
        for item in lock.get("sources", [])
    }
    existing[args.document_id] = record

    lock["generated_utc"] = datetime.now(timezone.utc).isoformat()
    lock["sources"] = sorted(
        existing.values(),
        key=lambda item: item["document_id"],
    )

    with LOCK_FILE.open("w", encoding="utf-8") as handle:
        json.dump(lock, handle, indent=2)
        handle.write("\n")

    print(f"PASS: {args.document_id}")
    print(f"File:   {destination}")
    print(f"Size:   {size} bytes")
    print(f"SHA256: {digest}")
    print(f"Lock:   {LOCK_FILE}")


if __name__ == "__main__":
    main()
