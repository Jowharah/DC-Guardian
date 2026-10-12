# DC-GUARDIAN — Production deployment design, threat model and security review scope

**Status:** design, 2026-10-12. Nothing in this document is implemented unless marked **(in place)**. DC-GUARDIAN today is a research prototype running on one Windows PC for one operator, on synthetic and controlled data. This document states what must change before it handles real data or more than one user, and what an independent security review should examine.

## 1. Where the prototype stands

| Area | Today | Why it is not production-ready |
|---|---|---|
| Authentication | One local account (HTTP Basic, from `.env`) **(in place)** | Single shared identity; no MFA, sessions, lockout or password policy; Basic credentials sent on every request |
| Authorization | Roles × permissions × zones, deny by default; access matrix tests all 99 operations **(in place)** | Roles come from one `.env` line, not from an identity provider; no per-user zone management |
| Transport | `127.0.0.1` only; Vite proxy in development **(in place)** | No TLS; must never be exposed beyond localhost as is |
| HTTP hardening | None | No security headers (CSP, frame, HSTS), no rate limiting, no request size limits beyond upload checks |
| Data stores | SQLite file, local image folders, Neo4j with password auth | No encryption at rest; single file; no concurrent multi-user writes |
| Secrets | `.env` (never committed), user environment variables **(in place)** | No secret store or rotation |
| External AI | OpenAI Responses API, opt-in, `store=False`, outbound minimization and pseudonyms, call audit **(in place)** | Needs a data-processing agreement, data-residency decision and provider risk assessment for real Evidence |
| Audit | Four hash chains, external checkpoints, backups with restore check **(in place)** | Chains live in the same database; checkpoints and backups depend on an operator routine |
| Monitoring | Rotating log files (`logs/`) **(in place)** | No central logging, alerting or uptime checks |
| Supply chain | pip-audit, npm audit, Bandit in CI; protected `main` **(in place)** | No SBOM, no signed releases, no container scanning |

## 2. Target deployment

```
 Operators ──HTTPS──▶ Reverse proxy (TLS 1.2+, security headers, rate limits, request limits)
                           │
                           ├──▶ Static dashboard (built React app)
                           └──▶ FastAPI backend (several workers, no public port)
                                    │
                    ┌───────────────┼──────────────────────┬─────────────────┐
              PostgreSQL       Object storage           Neo4j               OpenAI (optional,
         (Evidence, verdicts,  (images, encrypted,   (auth + TLS,           via egress proxy,
          Decisions, audit)     signed URLs)          private network)       allow-listed)
                    │
          Append-only audit export → WORM storage / SIEM (checkpoint every hour)
```

**Decisions to make (with the recommended choice):**

1. **Identity:** OIDC single sign-on (e.g. Microsoft Entra ID, the operator's existing directory) with MFA. Roles and zones come from directory groups mapped to `ROLE_PERMISSIONS`. Keep HTTP Basic only for the local research setup.
2. **Database:** move from SQLite to PostgreSQL for concurrent users and backups. The audit chains keep the same hash scheme; add database-level append-only permissions on the audit tables (no UPDATE or DELETE grants).
3. **Images:** object storage with server-side encryption and short-lived signed URLs, in place of the local folders. Face images and enrollment embeddings need the strictest retention.
4. **OpenAI:** decide whether real Evidence may leave the organisation at all. If yes: a data-processing agreement, a region choice, keeping the pseudonyms and minimization, and an egress allow-list. If no: keep the Investigator and specialists disabled, or move them to a self-hosted model.
5. **Hosting:** containers on the organisation's infrastructure, with the backend, Neo4j and the database on a private network and only the reverse proxy reachable.

## 3. Threat model (STRIDE)

Assets: Evidence (including face images and identities), verdicts and Decisions, audit records, credentials and API keys, the integrity of severity.

| Threat | Example | Existing control | Gap / to do |
|---|---|---|---|
| **Spoofing** | Stolen shared password used from another machine | Localhost only; constant-time credential compare | SSO with MFA; per-user identities; session expiry |
| **Tampering** | Editing a verdict, Decision or audit record in the database | Hash chains, external checkpoints, backups with chain verification; verdicts never overwrite detector output | Append-only DB permissions; audit export to WORM storage; signed checkpoints by default (`DCG_CHECKPOINT_KEY`) |
| **Tampering** | Severity changed by an LLM or a human typing a level | Severity only from deterministic rules (v1/v2); specialists and the Investigator never assign it; tests enforce it | Keep as an acceptance rule for every new feature |
| **Repudiation** | "I did not resolve that investigation" | Reviewer identity and time in every audit chain | Per-user identities (today one shared account makes this weak) |
| **Information disclosure** | Face images or identities reaching a user without permission | Domain + zone permissions on every endpoint; access matrix test | Encryption at rest; signed image URLs; retention and deletion policy |
| **Information disclosure** | Evidence sent to OpenAI | Opt-in, consent per call, allowlists, minimization, pseudonyms, `store=False`, call audit | Data-processing agreement; residency; or disable for real data |
| **Information disclosure** | Prompt injection in Evidence or knowledge text making the model leak or misstate | Context treated as untrusted data; prompt-injection contract tests; claim checks on answers | Red-team evaluation with crafted Evidence |
| **Denial of service** | Large uploads or many specialist calls (cost and availability) | Upload size limits on SSH logs; specialists are administrator-only | Rate limits per user; OpenAI spend limits; request size limits at the proxy |
| **Elevation of privilege** | A viewer reaching detail or write endpoints | Deny-by-default policy; 401/403 matrix for every operation and role | Directory-group mapping review; periodic access recertification |
| **Elevation of privilege** | A dependency vulnerability | pip-audit, npm audit, Bandit in CI; protected `main` | SBOM; container image scanning; scheduled dependency updates |

## 4. Independent security review — scope

The review should be done by someone outside the project team. Material for the reviewer:

- **Architecture and data flow:** this document; `docs/AI_INVESTIGATOR.md` (what leaves to OpenAI); `docs/VALIDATION_AND_OPERATIONS.md`.
- **Code focus:**
  - `presentation/backend/app/authentication.py` and `authorization.py`;
  - every router (the access matrix in `tests/test_access_matrix.py` lists them);
  - upload handlers (SSH logs, images, SMART and sensor files);
  - `investigator_*` (outbound payloads);
  - the audit modules (`review_integrity.py`, `audit_checkpoint.py`, `backup.py`).
- **Tests to run:** the authenticated and unauthenticated access matrix; upload fuzzing (file type, size, malformed CSV and logs); prompt-injection attempts through Evidence fields and knowledge text; audit tampering (edit, delete tail, replace database) against checkpoints; a dependency and container scan.
- **Out of scope until deployment exists:** network penetration test of the hosting environment (repeat once deployed).
- **Exit criteria:** no open high or critical findings; medium findings with an owner and a date; results recorded in `docs/WORK_LOG.md`.

## 5. Order of work before real data

1. Decide the four questions in section 2 (identity, database, images, OpenAI).
2. Add HTTP hardening that works even locally: security headers, request size limits, rate limits on specialist and Investigator endpoints.
3. Implement OIDC behind the existing `current_principal` interface. Authorization code stays unchanged, and the access matrix keeps testing it.
4. Move storage to PostgreSQL and object storage; keep the hash-chain format; add append-only permissions and the audit export.
5. Containerise; deploy behind the reverse proxy on a private network; central logging and alerts.
6. Independent security review (section 4), fix findings, then a pilot with real data.
