# DC-GUARDIAN RAG Knowledge Base

This directory holds local source snapshots used by the Response RAG retrieval
pipeline.

## Source policy

The authoritative catalog is:

```text
response/rag/manifests/knowledge_manifest.json
```

Only sources marked both `APPROVED` and `ACTIVE` are eligible for the
active retrieval index.

Third-party source snapshots are downloaded into `originals/` and are not
committed to Git by default. The downloader records the resolved URL, content
type, byte size, SHA-256 digest, and fetch timestamp in
`manifests/source_lock.json`.

## Fetch approved sources

From the repository root:

```powershell
python response\rag\fetch_sources.py
```

A subsequent run verifies and reuses locked local copies. It does not silently
replace a changed source.

To intentionally refresh sources after reviewing upstream changes:

```powershell
python response\rag\fetch_sources.py --refresh
```

Review the resulting lock-file diff and retrieval impact before accepting a
new source snapshot.

## Separation of artifacts

```text
knowledge_manifest.json   approved/candidate source catalog
source_lock.json          exact locally fetched source snapshot metadata
knowledge_base/originals  downloaded third-party originals (local only)
future parsed/chunks      generated derivatives
future vector_store       generated local retrieval index
```

Downloaded content is treated as data only. The fetcher never executes or
deserializes source content.

