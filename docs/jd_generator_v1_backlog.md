# JD Generator v1 Backlog

## Assumptions
- Core v1 sources: NCS, ESCO, O*NET
- DigComp is enabled in v1.1
- SFIA is feature-flagged until license is confirmed
- Stack: Next.js + FastAPI + PostgreSQL + pgvector + Redis

## P0 Epics and Tickets

### EPIC 0. Platform Foundation
**JD-001** Monorepo / service skeleton
- Output: web, api, worker, shared schema packages
- Done when: local dev, env separation, lint/test scripts all work

**JD-002** Authentication and RBAC
- Output: tenant membership, role-based route guard, API permission middleware
- Done when: admin / HR architect / reviewer / viewer permission matrix passes tests

**JD-003** Background job framework
- Output: job queue, retry policy, dead-letter handling
- Done when: source sync and export jobs can run async with observability

**JD-004** Audit and activity logging baseline
- Output: request ID, actor logging, change event hooks
- Done when: JD approval/rejection actions are fully traceable

### EPIC 1. Source Hub
**JD-101** Source registry + sync run management
- Output: source config UI, sync run status API
- Done when: admin can start full/incremental sync and inspect results

**JD-102** NCS connector
- Output: NCS fetcher, parser, raw payload persistence
- Done when: role/classification/capability data lands in source_items with dedup

**JD-103** ESCO connector
- Output: occupation/skill fetcher, relation import
- Done when: ESCO role and skill entities are searchable in raw store

**JD-104** O*NET connector
- Output: tasks/skills/knowledge/technology ingestion
- Done when: approved O*NET endpoints populate raw store with source version metadata

**JD-105** Source normalization text pipeline
- Output: text cleaner, locale normalization, content hashing
- Done when: all source items have normalized_text and stable content_hash

**JD-106** Embedding and retrieval index pipeline
- Output: embedding worker, vector/text index refresh
- Done when: source items and canonical roles are retrievable by hybrid search

### EPIC 2. Canonical Job Graph
**JD-201** Canonical schema implementation
- Output: canonical role/task/skill/knowledge/tool tables
- Done when: migrations run and integrity tests pass

**JD-202** Raw-to-canonical normalizer
- Output: mapping rules from each source to internal entities
- Done when: at least 50 seed roles normalize without duplicate explosion

**JD-203** Crosswalk builder
- Output: source-to-canonical link creation logic
- Done when: one canonical role can aggregate multiple source evidences

**JD-204** KO/EN alias dictionary
- Output: synonym dictionary for role titles and common skill labels
- Done when: Korean job titles retrieve English-source candidates reliably

### EPIC 3. Company Role Intake
**JD-301** Org unit CRUD
- Output: org tree UI and API
- Done when: business units and nested teams can be managed per tenant

**JD-302** Company role CRUD
- Output: job family, title, domain, status management
- Done when: a company role can be created and archived without deleting history

**JD-303** Role intake form + snapshoting
- Output: mission, deliverables, recurring tasks, tools, stakeholders, seniority form
- Done when: each save creates a recoverable snapshot

**JD-304** Duplicate role detection
- Output: near-duplicate warning based on title and embedding similarity
- Done when: users see duplicate warnings before new role creation completes

### EPIC 4. Matching Engine
**JD-401** Candidate retrieval service
- Output: BM25 + vector hybrid retrieval against canonical roles
- Done when: top 10 candidate roles are returned under 2 seconds on seed data

**JD-402** Scoring engine
- Output: title/task/skill/knowledge/level/context weighted scoring
- Done when: score breakdown is returned as JSON for each candidate

**JD-403** Match review UI
- Output: side-by-side candidate comparison with evidence tabs
- Done when: reviewer can approve, reject, or mark primary mapping

**JD-404** Feedback learning loop
- Output: event capture and weight calibration hooks
- Done when: approved/rejected decisions are stored for future ranking improvement

### EPIC 5. JD Generator
**JD-501** Evidence bundle builder
- Output: approved mapping + source evidence + company input bundle
- Done when: each JD section request has traceable evidence payload

**JD-502** Section composer
- Output: generator for summary, mission, responsibilities, qualifications, collaboration, career path
- Done when: generated draft conforms to JSON schema and section structure

**JD-503** KPI recommender
- Output: responsibility-to-metric rule engine and template lookup
- Done when: each generated KPI includes metric type, formula, data source, review cycle

**JD-504** Guardrail validator
- Output: evidence coverage check, prohibited phrasing check, duplicate line check
- Done when: evidence-less responsibility lines are blocked from approval submission

**JD-505** JD editor with evidence drawer
- Output: edit panel, section lock, evidence side drawer
- Done when: reviewer can edit text while preserving source trace visibility

### EPIC 6. Workflow / Dashboard / Export
**JD-601** Review queue
- Output: pending/rework/approved queue screen
- Done when: reviewer workload and item status are filterable by org and owner

**JD-602** Approval workflow
- Output: submit, request changes, approve, reject actions
- Done when: approval_logs capture every state transition

**JD-603** Dashboard summary widgets
- Output: org coverage, pending counts, duplicate warnings, sync freshness
- Done when: dashboard reflects approved data in near-real time

**JD-604** Export service
- Output: DOCX/PDF export worker and template
- Done when: approved JD can be exported with sections, KPIs, and evidence appendix toggle

## P1 Tickets
**JD-701** DigComp loader and AI-literacy layer
- Done when: non-engineering roles can receive digital/AI common competency sections

**JD-702** Template profiles
- Done when: one JD can be generated in org-design / hiring / evaluation modes

**JD-703** Prompt and schema versioning
- Done when: generator changes are reproducible by version

**JD-704** Analytics: role overlap and source coverage
- Done when: admins can find under-evidenced or overlapping roles

**JD-705** Notification hooks
- Done when: reviewers receive in-app/email notifications for assigned review requests

## P2 Tickets
**JD-801** SFIA feature flag module
- Done when: system can turn level guidance on/off by tenant setting

**JD-802** Career path visualizer
- Done when: adjacent roles and progression paths can be rendered from approved mappings

**JD-803** Bulk role import
- Done when: CSV import creates company roles and intake drafts safely

## Suggested Sprint Order
### Sprint 1
JD-001 ~ JD-105, JD-201, JD-301, JD-302

### Sprint 2
JD-106, JD-202, JD-203, JD-204, JD-303, JD-401

### Sprint 3
JD-402, JD-403, JD-404, JD-501, JD-502, JD-504

### Sprint 4
JD-503, JD-505, JD-601, JD-602, JD-603, JD-604

## Release Gate Checklist
- All approved JD sections must have evidence coverage
- Match scoring must expose explainable breakdown
- Audit log must exist for review and approval actions
- Export must work from approved versions only
- Seed data must cover at least AI / data / platform / product / governance families
