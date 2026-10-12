# Industrial deployment considerations

*Draft report section (2026-10-12). Figures refer to the DC-GUARDIAN repository at the date above; supporting material is in `docs/PRODUCTION_READINESS.md`, `docs/VALIDATION_AND_OPERATIONS.md` and `docs/AI_INVESTIGATOR.md`.*

## Purpose and scope

DC-GUARDIAN is an industrial prototype: it runs as a single-operator system on one workstation, against controlled and synthetic data. The prototype implements the controls that an operational monitoring system needs to be trustworthy (access control, auditability, privacy protection, human oversight and verification). It does not implement the infrastructure for multi-user production use. This section separates what is in place, and how it was verified, from what a production deployment would add.

## Controls implemented in the prototype

| Area | Implemented control | Verification |
|---|---|---|
| Human oversight | No autonomous action anywhere. Severity comes only from deterministic rules (DCG-DECISION-v1/v2), never from a language model. Operators record verdicts beside frozen detector output, never in place of it. | Contract tests on the Decision rules; the Investigator refuses action requests in every recorded live test |
| Authorisation | Deny-by-default role × zone policy across five domains | Automated access matrix: all 99 API operations × every role (401 without credentials, 403 exactly where a permission is missing) |
| Audit integrity | Four hash chains (group reviews, Evidence verdicts, Investigator calls, investigation lifecycle). External checkpoints detect deleted records and a replaced database. | Tamper, tail-deletion and replacement tests; checkpoint verification on operational data |
| Data protection | Opt-in external model calls with per-call consent. Outbound minimisation strips biometric fields. Usernames, IP addresses and person IDs leave only as keyed pseudonyms. Provider-side storage is disabled. | Payload inspection tests; live calls recorded in the call audit |
| Model output assurance | Grounding check on cited knowledge. Numeric and identity field checks. A post-generation judge flags unsupported presence, causation and PPE-absence claims. | Judge measured on 40 blind-labelled live answers: 4 of 5 overclaims caught, 1 false alarm in 35 |
| Resilience | Backups (consistent online copy, images, graph export, hash manifest) with a restore check; documented recovery steps | Backup and restore-check tests; verified backup of operational data |
| Software assurance | Continuous integration on every change: dependency audit, static security analysis, 14 test suites across every layer, browser and accessibility tests. Merges to the main branch require passing checks. | CI results per pull request |

## Requirements for production deployment

| Requirement | Prototype | Production |
|---|---|---|
| Authentication | One local account (HTTP Basic) on localhost | Organisational single sign-on (OIDC) with multi-factor authentication and per-user identities |
| Authorisation administration | Role and zones from local configuration | Roles and zones from directory groups, with periodic access recertification |
| Data store | SQLite file | PostgreSQL with append-only permissions on audit tables |
| Image storage | Local folder | Encrypted object storage, short-lived signed links, a retention period for face images |
| Audit retention | Local chains, operator-held checkpoints | Write-once (WORM) audit export and scheduled checkpoints |
| External AI processing | Opt-in, pseudonymised, rate-limited | A data-processing agreement and data-residency decision, or a self-hosted model |
| Hosting and transport | Single workstation, no TLS | Containers on a private network behind a TLS reverse proxy; central logging and alerting |
| Assurance | Internal tests and a STRIDE threat model | Independent security review and penetration test before handling real data |

## Threat model summary

A STRIDE analysis (`docs/PRODUCTION_READINESS.md`, section 3) maps each threat to existing controls and remaining gaps. The main gaps are:
- **Shared identity:** weak non-repudiation while there is one shared account.
- **No encryption at rest:** stored Evidence and images are not encrypted.
- **External processing:** governance of real Evidence sent to an external language model.

Each gap maps to one of the production requirements above.

## Limitations

- **Data:** the Evidence components were evaluated on public or controlled datasets, and the data-centre topology is synthetic, so detector performance and correlation behaviour on a real site are not established.
- **Labels:** the reasoning evaluations (correlation, group severity, Investigator overclaims) use labels written by the project team; an independent labelling round is pending.
- **Users:** the system has not been operated by multiple users or by operators outside the project team.
