# JD Generator Web App

This repository contains the project brief, backlog, and database schema for a web application that generates job descriptions from NCS, ESCO, O*NET, DigComp, and optionally SFIA.

## Included Files
- `README.md`: repository overview
- `docs/project-brief.md`: product and architecture brief for Lovable build kickoff
- `docs/lovable-build-prompt.md`: copy-paste prompt for Lovable
- `docs/conversation-summary.md`: condensed summary of the design decisions made so far
- `docs/jd_generator_v1_backlog.md`: implementation backlog
- `docs/jd_generator_v1_schema.sql`: PostgreSQL schema draft

## Product Scope
- Source ingestion: NCS, ESCO, O*NET in v1
- DigComp in v1.1
- SFIA as feature-flagged module after license confirmation
- Core modules: source hub, mapping engine, JD generator, dashboard

## Recommended Stack
- Frontend: Next.js
- Backend: FastAPI
- Database: PostgreSQL + pgvector
- Queue/cache: Redis
- Hosting/build: Lovable + Supabase or separate API deployment

## Notes
- KPI generation should be rules-based, not copied from source systems.
- Every JD sentence should keep evidence links.
- Raw source data and generated JD content must be stored separately.
