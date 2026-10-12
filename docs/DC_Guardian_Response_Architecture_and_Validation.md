# DC-GUARDIAN — Response Architecture and Validation

**Status:** IN DEVELOPMENT  
**Architecture:** Evidence â†’ Reasoning â†’ Response

## 1. Layered Architecture

DC-GUARDIAN is organized around Evidence, Reasoning, Response, Decision, and Presentation layers.

| Phase | Name | Core question | Responsibility |
|---|---|---|---|
| Evidence layer | **Evidence** | What happened? | Detect domain events and normalize evidence. |
| Reasoning layer | **Reasoning** | What does the evidence mean together? | Deterministically correlate events using common schemas, topology, and explicit rules. |
| Response layer | **Response** | What approved knowledge applies, what can be concluded, and what should be considered next? | Retrieve governed knowledge, perform grounded AI reasoning, and support deterministic response decisions. |

Reasoning and Response both involve reasoning, but they have different roles. Reasoning-layer correlation is deterministic and rule/topology based. Grounded Reasoning uses an LLM to interpret supplied incident evidence together with retrieved approved knowledge. The LLM does not replace Reasoning-layer correlation or final deterministic decision/escalation rules.

## 2. Response layer Decomposition

### 3.1 Knowledge & Retrieval â€” VERIFIED

Response RAG provides the governed knowledge layer used by later reasoning.

Pipeline:

```text
Approved source manifest
        â†“
Locked source snapshots + SHA-256
        â†“
Parsing
        â†“
Conservative preprocessing
        â†“
Deterministic chunking
        â†“
Local embeddings
        â†“
Domain eligibility/filtering
        â†“
Controlled Top-3 retrieval
        â†“
Grounded evidence with provenance
```

Verified foundation:

- 13 approved and active knowledge sources.
- 13/13 source snapshots locked and SHA-256 verified.
- 13/13 parsing contract passed.
- 13/13 preprocessing/provenance contract passed.
- 13/13 chunking contract passed.
- 255 active retrieval chunks (260 before 2026-10-12, when OSHA documents were trimmed to their own CFR section; see 3.1.2).
- Local embedding model: `sentence-transformers/all-MiniLM-L6-v2`.
- Embedding dimension: 384.
- Retrieval operates locally/offline after model acquisition.
- Selected ranking policy: **CONTROLLED**.
- Default evidence depth: **Top-3**.
- Knowledge eligibility: deterministic.
- Generated vector index and local knowledge artifacts are reproducible from governed inputs.

### 3.1.1 Corpus Governance

The locked source corpus and active retrieval corpus are distinct concepts. Original approved sources remain intact. Retrieval scope can deliberately select relevant material without modifying the authoritative source snapshot.

Each retrieval result retains provenance including document ID, chunk ID, publisher/authority metadata, page information where available, source URL, and source SHA-256.

Downloaded third-party source files, parsed text, clean text, chunks, vectors, and generated diagnostic reports remain local/rebuildable artifacts rather than being treated as source code.

### 3.1.2 Retrieval Experiments

The same frozen retrieval evaluation cases were used to compare ranking policies.

| Experiment | Ranking policy | Recall@3 | Precision@3 | Recall@5 | Precision@5 | MRR | Result |
|---|---|---:|---:|---:|---:|---:|---|
| v1 | Raw cosine ranking | 84.31% | 74.51% | 90.20% | 73.53% | 0.8725 | Strong precision; lower multi-source recall. |
| v2 | Maximum document diversity | 90.20% | 47.06% | 97.06% | 39.41% | 0.8725 | Recall improved but irrelevant diversity reduced precision. |
| v3 | Controlled diversity | **90.20%** | **65.69%** | 92.16% | 46.57% | **0.8725** | **Selected ranking policy.** |
| v4 | Controlled + cosine abstention | 49.02% | 31.37% | 50.98% | 23.04% | 0.4608 | Rejected as default due to poor generalization and false abstention. |

For the selected controlled-ranking baseline:

- Hit Rate@3: **100%**
- Recall@3: **90.20%**
- Precision@3: **65.69%**
- MRR: **0.8725**
- Domain-filter correctness: **100%**
- Provenance correctness: **100%**

Top-3 is the current evidence-depth candidate because Top-5 provided only a modest recall gain while introducing substantially more retrieval noise.

The table above is the original evaluation (corpus of 260 chunks), kept as the record of how the ranking policy was selected.

#### Re-evaluation after the CFR section fix (2026-10-12)

The official OSHA PDFs are whole printed CFR pages, so each OSHA document also held parts of its neighbouring sections. For example, 1910.135 began with respirator text from 1910.134, and 1910.137 repeated 1910.135/136. Preprocessing now keeps each OSHA document's own section; no source was added or reworded (see `docs/WORK_LOG.md`). This leaves 255 chunks. The same 18 frozen cases were re-run for all four experiments, without retuning either the cases or the abstention threshold:

| Experiment | Ranking policy | Hit@1 | Recall@3 | Precision@3 | Recall@5 | Precision@5 | MRR | No-source case |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| v1 | Raw cosine ranking | 94.12% | 90.20% | 83.33% | 96.08% | 75.49% | 0.9706 | 1/2 |
| v2 | Maximum document diversity | 94.12% | 96.08% | 50.98% | 98.04% | 39.41% | 0.9706 | 0/2 |
| v3 | **Controlled diversity (selected)** | **94.12%** | **96.08%** | **71.57%** | 96.08% | 47.55% | **0.9706** | 0/2 |
| v4 | Controlled + cosine abstention | 58.82% | 60.78% | 39.22% | 60.78% | 25.98% | 0.6176 | 1/2 |

- **Selected policy:** controlled diversity stays the selected policy. Against the original evaluation, Recall@3 rose from 90.20% to 96.08%, Precision@3 from 65.69% to 71.57%, and MRR from 0.8725 to 0.9706. Hit Rate@3 is 100% (every case with an expected source finds one in the top 3), and domain-filter and provenance correctness stay at 100%.
- **Where the gain comes from:** mainly the PPE and electrical-PPE cases (RAG-EVAL-004, -008, -013), which now rank OSHA 1910.132/135/137 first.
- **Remaining weak cases:** RAG-EVAL-006 (heat plus drive risk, three expected documents: Recall@3 0.33), and RAG-EVAL-017 (the right source is ranked second).
- **No-source case:** RAG-EVAL-016 has no approved source and is still answered by nearest-neighbour retrieval under controlled ranking. Deterministic knowledge eligibility (3.1.3), not cosine abstention, handles it.
- **Abstention:** recalibrated on the rebuilt index with its development cases. The threshold is unchanged (0.5922) and still separates those cases perfectly, but on the frozen set it still costs a third of the valid retrievals. It stays experimental and is not the default.
- **Caveats:** 18 cases written by the project author; the OSHA fix was prompted by a live PPE-specialist failure, not by these cases, but three of them test exactly the documents it changed. The reports are local, rebuildable artifacts (`response/rag/evaluation/retrieval_evaluation_report.json`, one run per configuration).

### 3.1.3 Abstention and Knowledge Eligibility

A development-only calibration experiment produced a cosine threshold of 0.5922 with perfect separation on its calibration cases. When applied unchanged to the frozen retrieval evaluation, however, valid retrieval performance degraded substantially. Therefore cosine-score abstention is retained only as an experimental mechanism and is **not the production default**.

DC-GUARDIAN instead includes deterministic knowledge eligibility. Before semantic retrieval is relied upon for a required authority/source scope, the manifest can establish whether approved active knowledge of that type exists.

Example:

```text
Request requires DC-GUARDIAN internal project policy
        â†“
Manifest eligibility check
        â†“
Required approved/active project policy unavailable
        â†“
INSUFFICIENT_APPROVED_KNOWLEDGE
```

This prevents a semantically similar external standard from being incorrectly presented as DC-GUARDIAN internal policy.

### 3.1.4 Integrated Verification

The integrated verifier `response/rag/verify_response_rag.py` currently verifies:

- Source corpus integrity.
- Parsing contract.
- Preprocessing contract.
- Chunking contract.
- Local retrieval contract.
- Knowledge eligibility contract.
- Chunk/index count consistency.

Verified result:

```text
RAG sources:            13
RAG chunks:             255
Embedding model:        sentence-transformers/all-MiniLM-L6-v2
Selected ranking:       CONTROLLED
Default evidence depth: TOP-3
Knowledge eligibility:  DETERMINISTIC
Cosine abstention:      EXPERIMENTAL / NOT DEFAULT

DC-GUARDIAN RESPONSE RAG RAG FOUNDATION PASSED
```

## 3. Grounded Reasoning Grounded AI Reasoning â€” IN DEVELOPMENT

Grounded Reasoning converts Evidence and Reasoning context plus approved retrieved knowledge into a structured grounded assessment.

Current flow:

```text
Reasoning-layer correlation / incident evidence
        +
Deterministic knowledge eligibility
        â†“
Local RAG â€” Controlled Top-3
        â†“
Grounded reasoning provider
        â†“
OpenAI Responses API
        â†“
Strict structured assessment
        â†“
Deterministic schema/citation validation
        â†“
Future deterministic decision rules
```

### 3.2.1 Provider Boundary

The reasoning layer uses a provider-independent interface. The first provider implementation uses the OpenAI Responses API. The provider can later be replaced or benchmarked without changing the RAG or reasoning contract.

The full local corpus, vector index, raw biometric imagery, raw logs, Neo4j database, and model artifacts do not need to be sent to the LLM. The intended API boundary contains only the normalized incident/correlation context required for the reasoning task and selected approved retrieved evidence.

### 3.2.2 Grounded Assessment Contract

The current structured output contains:

- `assessment`
- `supported_findings[]`
- `recommended_considerations[]`
- `evidence_sufficient`
- `citations[]`
- `limitations[]`

The deterministic validator rejects citations to chunks/documents that were not supplied by the RAG layer. A sufficient-evidence assessment must cite retrieved evidence.

The system instructions explicitly prohibit the grounded reasoning component from:

- Inventing missing project policy, facts, identities, thresholds, procedures, or escalation rules.
- Treating external standards as DC-GUARDIAN internal policy.
- Assigning final severity.
- Executing operational actions.
- Unlocking doors or disabling systems.
- Claiming autonomous authority.

Final severity, escalation, and automated actions remain responsibilities of deterministic DC-GUARDIAN decision rules.

### 3.2.3 Local Reasoning Contract

The local Grounded Reasoning contract passed:

```text
PASS: Valid grounded assessment.
PASS: Hallucinated citation rejected.

DC-GUARDIAN GROUNDED REASONING GROUNDED REASONING CONTRACT PASSED
```

This contract uses fake providers and therefore does not require a paid external API call.

### 3.2.4 First End-to-End Grounded Reasoning Validation

A synthetic physical-access scenario was used for the first live end-to-end test:

```text
event_type           = PHYSICAL_ACCESS
subject_id           = TEST-EMPLOYEE
zone                 = ZONE-B
identity_status      = RECOGNIZED
authorization_status = UNAUTHORIZED
source               = SYNTHETIC_RESPONSE_TEST
```

The test successfully executed:

1. Deterministic Physical Security knowledge eligibility.
2. Local controlled Top-3 retrieval.
3. OpenAI grounded reasoning.
4. Strict structured output.
5. Deterministic citation validation.

The response correctly distinguished an observed unauthorized status from proof that physical entry was granted. It cited retrieved NIST evidence, did not invent final severity or autonomous action, and explicitly distinguished government guidance from DC-GUARDIAN internal policy.

The result also exposed a useful schema refinement: a single Boolean `evidence_sufficient` may be too coarse because evidence can support some findings while remaining insufficient for a complete operational conclusion. A future revision should evaluate a status such as:

- `SUPPORTED`
- `PARTIALLY_SUPPORTED`
- `INSUFFICIENT`

## 4. Planned Specialist Agents â€” Specialist Agent Routing

The target architecture includes specialist reasoning responsibilities, but DC-GUARDIAN will not invoke every specialist for every incident.

Initial target roles:

- Physical & Safety specialist.
- Cybersecurity specialist.
- Operations specialist (maintenance + environmental).
- Cross-domain synthesis.
- Supervisor/router.

Routing should use Reasoning-layer structured domain/correlation information wherever deterministic routing is possible rather than asking an LLM to rediscover known event domains.

RAG remains a shared capability rather than requiring a separate autonomous RAG agent.

## 5. Planned Cross-Domain Response â€” Cross-Domain Response

For genuinely cross-domain incidents, relevant specialists may reason over their own approved evidence and return structured findings. Cross-domain synthesis then combines those findings.

The LLM layer produces grounded interpretation and recommendations. Deterministic rules remain responsible for final severity, escalation, routing, ticket generation, or authorized automation.

## 6. Target End-to-End Architecture

```text
EVIDENCE
Domain detectors/models
        â†“
Structured events
        â†“
REASONING
Common Event Schema
Neo4j topology
Deterministic correlation
        â†“
Correlation / incident context
        â†“
RESPONSE
Knowledge eligibility
Local governed RAG
Grounded specialist reasoning
Cross-domain synthesis
        â†“
Deterministic decision / escalation rules
        â†“
Incident output / dashboard
```

## 7. Current Completion State

| Capability | Status |
|---|---|
| Response RAG governed corpus | VERIFIED |
| Response RAG parsing/preprocessing/chunking | VERIFIED |
| Response RAG local embedding index | VERIFIED |
| Response RAG retrieval evaluation | VERIFIED |
| Response RAG deterministic knowledge eligibility | VERIFIED |
| Response RAG integrated verification | PASSED |
| Grounded Reasoning provider-independent reasoning interface | IMPLEMENTED |
| Grounded Reasoning structured grounding contract | PASSED |
| Grounded Reasoning first live grounded reasoning call | PASSED |
| Grounded Reasoning reasoning evaluation suite | NEXT |
| Specialist Agents specialist routing | PLANNED |
| Cross-Domain Response cross-domain response | PLANNED |

## 8. Response layer Completion Criteria

Response layer should not be considered complete solely because an LLM can produce plausible text. Completion requires evidence that:

1. Knowledge sources remain governed, approved, traceable, and reproducible.
2. Retrieval quality is measured against frozen cases.
3. Grounded reasoning citations are restricted to supplied evidence.
4. Unsupported internal policy is not invented.
5. Reasoning quality is evaluated using synthetic/frozen cases and explicit required/forbidden behaviors.
6. Specialist routing is deterministic where domain information is already known.
7. Cross-domain synthesis operates on structured specialist findings.
8. Final severity/escalation and operational authority remain governed by explicit deterministic rules.
9. The end-to-end Response layer verification suite passes.
10. Documentation and reproducibility artifacts are synchronized with the verified implementation.

---

**Architecture summary:** **Evidence â†’ Reasoning â†’ Response**


