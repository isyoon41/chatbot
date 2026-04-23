# Project Brief — JD Generator Web App

## Goal
Build a web app that creates evidence-based job descriptions by combining Korean NCS data with ESCO, O*NET, DigComp, and optionally SFIA.

## Workflow
1. Collect source data from NCS API and four additional sources.
2. Match a company role to external standard roles, tasks, and skills.
3. Generate a JD draft including responsibilities, qualifications, and KPI suggestions.
4. Manage, review, approve, version, and export JDs from a dashboard.

## v1 Scope
- NCS + ESCO + O*NET connectors
- Company role intake form
- Matching engine with explainable scoring
- JD draft generator
- KPI suggestion engine
- Review / approval workflow
- Dashboard with evidence drawer and exports

## v1.1
- DigComp common digital and AI literacy layer

## v1.2
- SFIA-based leveling after license confirmation

## Key Design Principles
- Evidence-first generation
- Human approval before publishing
- Version-controlled JD objects
- Separate raw-source store from generated content
- Explainable role matching

## Core Entities
- tenant
- org_unit
- company_role
- role_input_snapshot
- source_item
- canonical_role
- canonical_skill
- canonical_task
- mapping_candidate
- jd_version
- jd_section
- jd_evidence
- kpi_template
- kpi_instance
- approval_log

## Matching Logic
Use hybrid retrieval and weighted scoring.

Suggested initial score:
- 25% title similarity
- 30% task overlap
- 20% skill overlap
- 10% knowledge overlap
- 10% level fit
- 5% org context fit

## Dashboard Must-Haves
- Role library by organization
- Approval queue
- Evidence drawer
- Version comparison
- Source sync status
- Duplicate role warnings
- Export to DOCX/PDF

## Constraints
- SFIA usage depends on commercial licensing.
- O*NET source handling should preserve attribution and keep raw source exposure limited.
- KPI values must be internally generated from role responsibilities and measurable objects.
