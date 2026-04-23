# Conversation Summary

## Objective
Create a web app that can generate and manage job descriptions for modern AI, data, and platform roles by combining Korean and international standard sources.

## Selected Source Strategy
Core five-source strategy:
- NCS
- ESCO
- O*NET
- DigComp 3.0
- SFIA

Operational decision:
- v1 uses NCS + ESCO + O*NET
- DigComp is added in v1.1
- SFIA is held behind feature flag until licensing is confirmed

## Why This Structure
- NCS gives Korean job-family and capability alignment.
- ESCO gives international occupation-skill graph.
- O*NET gives detailed tasks, knowledge, skills, and technology signals.
- DigComp supports common digital and AI literacy across non-engineering roles.
- SFIA supports levels and responsibility bands, but licensing must be checked.

## Product Definition
This is not a plain JD writer.
It is a standard-data integration and evidence-based JD operating system.

## Required Modules
- Source Hub
- Canonical job graph
- Matching engine
- JD generator
- KPI rules layer
- Review and approval workflow
- Dashboard and export

## Key Product Rules
- Every JD sentence should have evidence.
- Raw source data and generated text must be separated.
- Matching should be based on title + tasks + skills + knowledge + org context.
- KPI suggestions must be internally generated.

## Recommended Build Direction
Use Lovable to bootstrap the web app UI and data workflows, with the provided backlog and schema as implementation anchors.
