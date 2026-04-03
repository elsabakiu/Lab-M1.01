# GDPR Documentation — InfraInspect AI Inspection Assistant

**Prepared by:** Elsa Bakiu | **Client:** HydroMapper / InfraCloud | **Version:** 1.4 | **Date:** April 2026 | **Status:** Draft for review

**Confirmed assumption:** HydroMapper's direct contractual relationship is with independent Bauwerksprüfung engineering consultancies. The consultancy is the **controller** for inspection data. WSV / WSA is the consultancy's end client and receives final inspection outputs — it is not a party to the data processing chain between HydroMapper and the consultancy.

---

## Table of Contents

1. Fact Pattern
2. GDPR Audit
   - Section A: Data Map
   - Section B: Risk and Rights
   - Section C: Law Stacking
3. Client Recommendation Memo

---

## 1. Fact Pattern

### Client

HydroMapper GmbH — infrastructure SaaS, 51–200 employees, Germany. InfraInspect is an AI-assisted inspection module for the InfraCloud platform, sold to Bauwerksprüfung engineering consultancies that conduct structural inspections of German federal waterway infrastructure (locks, weirs, canal bridges, culverts) under VV-WSV 2101 on behalf of WSV. The consultancy determines the purposes and means of inspection data processing — it is the controller. HydroMapper provides the platform as a processor.

### Personal data processed

| Category | Description | Sensitivity |
|---|---|---|
| Inspector identity | Name, surname, work email, hashed password, user ID | Standard |
| Authentication data | JWT tokens, login events, access logs | Standard |
| Operational audit data | Timestamps, review decisions, `inspector_accepted`, `corrected_fields` diff — constitutes a behavioural record capable of performance profiling | Standard–Elevated |
| Voice / audio recordings | Field recordings of inspector speech | Elevated — biometric-adjacent |
| ASR transcripts | German-language text from Whisper; stored in plaintext in `extraction_log.transcript` | Elevated |
| Evidence file metadata | `evidence` table stores `original_name` (inspector's original filename — may contain identifiers such as date, site, or inspector name) and `uploaded_by` (user_id) — directly links each audio recording or photo to the uploading inspector | Standard–Elevated |
| Free-text damage fields | `description`, `note`, `damage_repair_note`, `optional_remark`, `text_field` — uncontrolled at source; may incidentally contain names, health references, third-party data | Elevated |
| Historical damage record in VALIDATE prompt | For VALIDATE_DAMAGE extractions, the assembled GPT-4o prompt includes the full existing damage record as JSON — including all free-text fields listed above. Any incidental PII previously entered in those fields is transmitted to OpenAI on every re-inspection call. | Elevated |
| Photographic evidence | Structural photos; may incidentally contain persons, plates, location markers | Elevated where third-party identifiers present |
| Geolocation data | `latitude`, `longitude`, `height` per damage record — combined with inspector identity and timestamps forms an activity profile | Standard |
| AI extraction metadata | Confidence scores, intent classification, field-level diffs | Standard |
| LangSmith trace data | Full LangGraph state at every node: assembled prompt (system instructions + schema + existing record JSON + full transcript), raw LLM response, validated fields, proposed record, latency/retry logs | Elevated — contains full transcript and all intermediate outputs |
| Error / incident telemetry | Sentry receives error messages, stack traces, and request metadata at 20% trace sampling rate. May contain PII appearing in stack frames or request paths. | Standard–Elevated |
| Inferred performance indicators | Correction rates, acceptance patterns — derivable from `inspector_accepted` / `corrected_fields` | Elevated — employee profiling of consultancy staff |

**Volume:** ~36 damages per inspection report (BAW 2001); thousands of audio files and transcripts annually across the consultancy's WSV inspection portfolio.

### Data subjects

- **Field inspectors employed by the Bauwerksprüfung consultancy (primary)** — engineers and technicians conducting Bauwerksprüfungen; employees of the consultancy, not WSV civil servants
- **Internal reviewers and team leads** — office-based consultancy staff validating AI output before submission
- **HydroMapper admin users** — platform administrators and project managers
- **Incidental third parties** — individuals who may appear in photos or be referenced in free-text notes

### Where located

Germany and other EU/EEA member states. Consultancy employees are private-sector workers governed by German employment law.

### Vendor stack

| Vendor | Role | EEA? |
|---|---|---|
| OpenAI | LLM inference (GPT-4o) + ASR (Whisper) — receives full assembled prompt including transcript, schema, existing record (inc. free-text fields for VALIDATE flows) | ❌ US — transfer required |
| LangSmith | Pipeline tracing — full pipeline state at every node; eu.langsmith.com | ✅ EU data residency confirmed |
| NeonDB | PostgreSQL at rest — EU region to be explicitly configured | Depends on config |
| Sentry | Error tracking and performance monitoring — receives stack traces, error messages, request metadata at 20% trace sampling rate | ❌ US — transfer required |
| Hosting (TBC) | Web server, API | TBC |

### What the AI does

Audio → Whisper transcript → assembled prompt (system instructions + schema + existing record + transcript) → GPT-4o extracts intent + structured fields with confidence scores → domain validation → proposed record written to `extraction_log` → **human reviewer** inspects side-by-side diff → explicit submit required before any DB write.

For **VALIDATE_DAMAGE** flows, the assembled prompt includes the full existing damage record as JSON — including all free-text fields (`description`, `note`, `damage_repair_note`, `optional_remark`, `text_field`). Any incidental PII in those fields is transmitted to OpenAI on every re-inspection call.

**No autonomous decisions.** Human submission is mandatory for every record.

### Authentication

JWT-based authentication is implemented in the API layer. Keycloak SSO integration is planned, enabling consultancy identity providers to manage access. The POC workflow service is currently unauthenticated — resolved before production. Self-registration is currently open; production will enforce email verification and domain or invitation-based restriction aligned with the consultancy's employee identity management.

---

## 2. GDPR Audit

### Section A — Data Map

#### Purposes, lawful bases, and retention

| Purpose | Lawful basis | Retention |
|---|---|---|
| Authentication and access control | Art. 6(1)(b) — contract (platform service agreement between consultancy and HydroMapper) | Account lifetime + 30 days post-termination |
| Inspection workflow — creating, validating, storing damage records | Art. 6(1)(b) — contract (consultancy's service agreement with WSV requires structured inspection documentation under VV-WSV 2101) | Aligned with WSV documentation requirements — inspection records archived for the structure's operational lifetime |
| AI extraction from audio/transcripts | Art. 6(1)(f) — legitimate interests — see LIA below | Audio: deleted post-review or within 90 days (`DATA_RETENTION_DAYS=90`). Transcript: retained with damage record. |
| Audit logging / QA | Art. 6(1)(f) — legitimate interests | 12 months rolling |
| Extraction log for model evaluation | **TBD — legal review required** before any reuse for prompt improvement or fine-tuning | Anonymise or delete after eval cycle (suggested: 90 days) |
| Error telemetry (Sentry) | Art. 6(1)(f) — legitimate interests | Sentry default retention (90 days) — review against GDPR requirements before production |
| Security / incident response | Art. 6(1)(f) / legal obligation | 12 months |

#### Legitimate Interests Assessment — AI extraction

**Purpose:** Operational efficiency of Bauwerksprüfung inspections — reducing manual transcription burden on field engineers, ensuring consistent structured data capture across large portfolios, enabling quality-controlled AI-assisted damage classification. Legitimate interest of both HydroMapper (platform operator) and the consultancy (controller delivering contracted inspection services to WSV).

**Necessity:**

| Alternative | Why insufficient |
|---|---|
| Manual structured entry only | Increases field time; inspectors work with both hands occupied at inspection sites |
| On-device LLM | Not feasible at current scale; significant infrastructure investment required |
| Human transcription post-hoc | Transcription delay incompatible with real-time review workflow; audio still processed |
| Form-only inspection | Established field practice relies on spoken documentation; not within HydroMapper's control to change |

Processing is necessary — no less intrusive method achieves equivalent data quality at operational scale.

**Balancing:**

*Reducing impact:* Inspectors are professional engineers acting in an employment context (reduced privacy expectation relative to private citizens). AI-assisted tooling is a reasonable expectation in modern professional inspection practice. Mandatory human review gate — no AI output has direct effect without explicit submission. Audio deleted within 90 days post-session. Full extraction log auditability. EU-hosted LangSmith tracing. Confidence scores disclosed to reviewer in the UI.

*Increasing impact:* Voice is biometric-adjacent and transmitted to OpenAI outside the EEA — the most significant balancing factor. For VALIDATE_DAMAGE flows, the assembled prompt also includes the full existing damage record JSON — including free-text fields that may contain incidental PII — transmitted to OpenAI on every re-inspection call. Transcripts retained in plaintext without pseudonymisation. `inspector_accepted`/`corrected_fields` creates a permanent behavioural record of each session that could be repurposed for performance management.

**Net assessment:** Defensible where: (a) audio deletion is enforced before production; (b) OpenAI DPA + SCCs + EU-region endpoint are in place; (c) inspectors are informed at point of use; (d) `inspector_accepted`/`corrected_fields` is access-controlled and excluded from performance management workflows without separate legal assessment. The LIA weakens materially if any condition is unmet.

#### Controller / processor roles

| Entity | Role | Notes |
|---|---|---|
| Bauwerksprüfung consultancy | **Controller** | Determines purposes and means of inspection data processing; employs the inspectors; contractually responsible to WSV for inspection outputs |
| WSV / WSA | **Recipient** — not in the processing chain | Receives final inspection reports as the consultancy's end client; separate controller for its own obligations |
| HydroMapper | **Processor** for consultancy inspection data; **Controller** for platform operations and product development | Dual role depending on data category; DPA with each consultancy required |
| Elsa Bakiu | **Sub-processor** during development and POC | Access rights to be clarified before production |
| OpenAI | **Sub-processor** — receives raw audio (Whisper) and full assembled prompt including transcript, schema, and existing damage record JSON (GPT-4o, incl. free-text fields on VALIDATE flows) | DPA + SCCs + TIA required; EU-region endpoint to be enforced |
| LangSmith | **Sub-processor** — receives full pipeline state at every node | DPA required (Art. 28); no international transfer; implement trace payload filtering |
| NeonDB | **Sub-processor** — all data at rest | DPA required; EU region to be explicitly configured |
| Sentry | **Sub-processor** — error tracking; receives stack traces, error messages, request metadata | DPA + SCCs required; US-based — international transfer |

#### International transfers

| Transfer | Mechanism | Action |
|---|---|---|
| OpenAI (USA) | SCCs + TIA | Execute DPA; enforce EU-region endpoint; complete TIA for FISA/EO 14086 risk |
| LangSmith | None — EU hosted | Execute Art. 28 DPA; enforce EU region; implement transcript filtering in trace config |
| NeonDB | Depends on region | Confirm EU region (e.g. AWS eu-central-1); document in sub-processor agreement |
| Sentry (USA) | SCCs | Execute DPA + SCCs; review what PII appears in stack traces and request paths at 20% sampling rate |

---

### Section B — Risk and Rights

#### Special-category data (Art. 9)

Not by design. Three incidental risks: (1) voice recordings are biometric-adjacent; (2) free-text fields and transcripts may incidentally contain Art. 9 data (health conditions, union membership) — including via VALIDATE_DAMAGE prompts that include historical free-text damage fields; (3) photos may capture faces or third-party identifiers. Mitigation: audio deletion post-session; inspector guidance not to include personal or sensitive information in free-text fields beyond what the WSV damage schema requires.

#### Automated decision-making (Art. 22)

Not in current design — human submission is mandatory.

**Current capability risk:** The `extraction_log` table already captures `inspector_accepted` and `corrected_fields` per session. The platform statistics endpoint aggregates this data. The technical infrastructure for per-inspector performance profiling **exists in the deployed schema today**, regardless of intent. Before production: implement RBAC to ensure this data is inaccessible to consultancy management, HR systems, or performance review workflows without separate legal authorisation by the consultancy as controller.

Art. 22 escalates further if the consultancy or WSV configures downstream workflows to auto-trigger consequential actions (maintenance contracts, enforcement decisions, liability determinations) based on AI-proposed records without genuine human review.

#### DPIA required?

**Yes — legally required before production rollout.** At minimum five EDPB criteria apply:

| Criterion | Applies? |
|---|---|
| Evaluation / scoring | ✅ Inspector correction rate data — already technically possible in current schema |
| Automated decision-making | Partially |
| Systematic monitoring | ✅ Continuous logging of inspector actions and field decisions |
| Sensitive data | ✅ Voice / incidental Art. 9 data; historical free-text transmitted to OpenAI on VALIDATE flows |
| Large scale | ✅ Likely across consultancy's WSV portfolio |
| Matching / combining datasets | ✅ Transcripts + damage records + coordinates + inspector identity |
| Innovative technology | ✅ Voice AI + LLM in regulated infrastructure inspection |
| Prevents exercise of rights | Partially — `extraction_log.user_id` is present but **nullable** in current implementation; sessions where `user_id` is NULL cannot be reliably attributed for rights fulfilment without indirect joins |
| Vulnerable subjects | ❌ Professional engineers in employment context |

**Primary DPIA focal point:** AI extraction from audio and assembled prompts (including historical free-text damage fields in VALIDATE flows) transmitted to OpenAI outside the EEA.

The DPIA is the consultancy's obligation as controller. HydroMapper must provide a processor-side technical documentation package (data flows, retention periods, sub-processor list, security measures) to support the consultancy's DPIA. A consultancy that cannot complete its DPIA because HydroMapper has not provided this information is HydroMapper's problem at the sales stage.

#### Data subject friction points

1. **Art. 15 — access:** Inspector requests all data held about them (audio, transcripts, extraction logs, LangSmith traces). Rights requests route to the **consultancy** as controller. HydroMapper must respond to the consultancy's instructions to locate and extract data. Note: `extraction_log.user_id` is present but **nullable** — for sessions where `user_id` is NULL, complete fulfilment requires indirect join through the damage record. Structural gap to be resolved before production by enforcing non-null `user_id` on all production sessions.

2. **Art. 17 — erasure:** Inspector leaving the consultancy requests deletion. Transcripts embedded in inspection records create tension with the consultancy's contractual retention obligations to WSV. Audio deletion is enforced within 90 days (`DATA_RETENTION_DAYS=90`). Same nullable `user_id` gap applies for locating all records attributable to a specific inspector.

3. **Art. 21 — objection to profiling:** If correction rate data reaches any performance management process at the consultancy, engineers have the right to object. RBAC controls and clear internal governance at the consultancy are the primary mitigations.

4. **Art. 13/14 — transparency:** The consultancy, as controller, bears the transparency obligation to its employees. HydroMapper must surface accurate information in the product. Before the first audio recording of any session, inspectors must be informed: (a) audio is processed by OpenAI outside the EEA; (b) pipeline traces including transcript content go to LangSmith (EU-hosted); (c) error telemetry goes to Sentry (US-hosted); (d) transcripts are retained for auditability; (e) audio is deleted within 90 days; (f) for VALIDATE re-inspections, the existing damage record including any free-text fields is included in the AI prompt. A short dismissable dialog is sufficient.

---

### Section C — Law Stacking

#### EU AI Act

**Likely Limited Risk; arguable High Risk pathway.** High Risk argument: Annex III(2) — safety components in critical infrastructure. German federal waterways qualify; Class 4 damage decisions affect structural safety. Counter-argument: mandatory human-in-the-loop limits effective risk level — the AI documents, the engineer decides. More defensible classification: **Limited Risk** with transparency obligations. Already substantially satisfied by intent badges, per-field confidence scores, and side-by-side review UI. See the separate EU AI Act compliance package for the full classification analysis.

#### ePrivacy

Applies to the web application. Confirm no third-party analytics cookies or session tracking SDKs before production.

#### Data Act

Low current applicability. Flag if IoT sensors or AR hardware are introduced in later iterations.

#### BetrVG §87(1) No. 6 — Works council co-determination

**Applies to the consultancy. Legal opinion required before production deployment.**

BetrVG §87(1) No. 6 grants works councils mandatory co-determination rights over technical systems **capable of** monitoring employee behaviour or performance — the trigger is capability, not intent.

InfraInspect satisfies this trigger: `extraction_log` permanently records `inspector_accepted` and `corrected_fields` per session, and the statistics endpoint aggregates this data across sessions. The system is technically capable of per-inspector correction rate reporting.

Because the inspectors are **employees of the Bauwerksprüfung consultancy**, the co-determination obligation sits with the consultancy, not with HydroMapper. If the consultancy has a Betriebsrat, a works council agreement (Betriebsvereinbarung) is required before deploying InfraInspect to its employees. This cannot be waived by individual consent or by contract with HydroMapper.

HydroMapper should:
- Build a works council engagement step into the customer implementation process
- Include a contract clause requiring the consultancy to confirm works council compliance (or confirm no Betriebsrat exists) before go-live
- Provide the consultancy with sufficient technical documentation of InfraInspect's monitoring capabilities to support the works council assessment

---

## 3. Client Recommendation Memo

**To:** HydroMapper product and legal team | **From:** Elsa Bakiu | **Date:** April 2026

**Bottom line: Proceed, but with conditions before any production rollout.**

The product design is sound — mandatory human review, audio deletion, confidence transparency, and structured extraction logging reflect genuine data protection thinking built in from the start. With the controller confirmed as the Bauwerksprüfung consultancy, the governance structure is clear: HydroMapper is unambiguously a processor, the DPA counterparty is the consultancy, and data subject rights route to the consultancy as controller.

### Three pre-production actions

**1. Execute vendor DPAs and transfer documentation — immediately**

- **OpenAI (urgent):** DPA + SCCs + TIA. Enforce EU-region API endpoint. The full assembled prompt including the inspector's transcript flows to US servers — this is the primary transfer risk. For VALIDATE_DAMAGE flows, this also includes historical free-text damage record fields that may contain incidental PII.
- **Sentry (new sub-processor):** DPA + SCCs. Sentry is a US-based error tracking service receiving stack traces and request metadata at 20% trace sampling. Review whether PII appears in those traces before production; consider EU-hosted alternative if transfer risk is unacceptable.
- **LangSmith:** DPA under Art. 28 (no transfer needed — EU hosted). Implement trace payload filtering to pseudonymise or exclude transcript content from stored traces. LangSmith receives the full pipeline state, not just surface telemetry.
- **NeonDB:** DPA + confirmed EU region configuration.
- **HydroMapper ↔ consultancy:** Prepare a standard Art. 28-compliant processor agreement template covering the mandatory clauses, sub-processor list, and data subject rights assistance obligations.

**2. Complete DPIA support package for consultancy customers**

The DPIA is the consultancy's obligation as controller, but HydroMapper must provide the technical documentation to support it: data flow diagrams, retention schedules, sub-processor list with transfer mechanisms, and a description of the AI pipeline's processing activities — including the fact that VALIDATE_DAMAGE prompts transmit historical damage record free-text fields to OpenAI. A consultancy that cannot complete its DPIA because HydroMapper has not provided the necessary information is HydroMapper's problem at the sales stage.

**3. Add transparency disclosure to the UI before any live use**

Before the first audio recording in any session, inspectors must be informed that: (a) audio is processed by OpenAI outside the EEA; (b) pipeline traces including transcript content go to LangSmith (EU-hosted); (c) error telemetry goes to Sentry (US-hosted); (d) transcripts are retained for auditability; (e) audio is deleted within 90 days; (f) for VALIDATE re-inspections, the existing damage record including free-text fields is included in the AI prompt. A short dismissable dialog is sufficient.

### Residual risks

**BetrVG.** Any consultancy customer with a Betriebsrat must obtain a works council agreement before deploying InfraInspect to its employees. Build this into the sales and implementation process. A contract clause making go-live conditional on the customer confirming works council compliance protects HydroMapper from being named in the resulting dispute.

**Inspector performance profiling via current schema.** The `extraction_log` table already enables per-inspector correction rate analysis. RBAC must prevent consultancy management from accessing this data without a separately assessed legal basis. Recommend restricting access to platform administrators only in the default configuration.

**OpenAI US jurisdiction risk is structural.** SCCs reduce exposure but cannot prevent US government data requests under FISA. Disclose this to each consultancy customer so they can include it in their DPIA. LangSmith's EU endpoint mitigates this for trace data; OpenAI remains the outstanding exposure.

**Meaningful human review may erode in practice.** Monitor `inspector_accepted` rates. If acceptance consistently approaches 100%, investigate whether genuine review is occurring. Commercial time pressure on field engineers is real, and rubber-stamp review creates Art. 22 exposure for the consultancy as controller.

**Incidental sensitive data.** Voice recordings and free-text fields may incidentally contain Art. 9 data — including via historical damage records transmitted to OpenAI on VALIDATE flows. Document as accepted residual risk in the DPIA support package. Provide inspectors with clear guidance on what not to include in recordings and free-text fields beyond what the WSV damage schema requires.

---

*Advisory note — does not constitute legal advice. Legal counsel must be engaged before production deployment.*
