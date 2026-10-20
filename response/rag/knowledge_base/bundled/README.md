# Bundled approved sources

These files are exact copies of the 13 approved RAG source snapshots recorded in
`response/rag/manifests/source_lock.json`. They were fetched on 2026-10-04 from the
URLs listed there, and every file matches its locked SHA-256.

**Why they are bundled:** a fresh installation must rebuild exactly the corpus the
retrieval evaluation used. Live downloads cannot guarantee that:
- CISA refuses automated downloads (HTTP 403);
- the U.S. DOE web page changes byte-for-byte between visits.

`setup.ps1` copies these files into `knowledge_base/originals/`. `fetch_sources.py`
then verifies each one against the lock instead of downloading it.

**Terms:** all 13 are publications of U.S. federal agencies (NIST, CISA and the
Interagency Security Committee, OSHA, U.S. DOE FEMP). As works of the U.S.
Government they are not subject to copyright in the United States (17 U.S.C. § 105).
They are redistributed unchanged, with their source URLs, for research use.

Do not edit these files: `.gitattributes` stores them byte-for-byte (`-text`).
To change the corpus, update the manifest and lock through the RAG pipeline first.
