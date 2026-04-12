# Smart BI MVP Vision and Scope

## Implementation status (product doc)

This file states **intent and scope**, not build progress. For engineering phase status see [Technical Roadmap](./03-technical-roadmap.md). For UX build status see [User Experience](./02-ux-roadmap.md).

| Area | Status |
|------|--------|
| Vision, problem, MVP goals, out of scope | **[Done]** — documented baseline |
| Success metrics | **[To do]** — targets to measure in UAT / post-MVP instrumentation |

## Vision
Build a Smart BI platform where business users can ask questions in natural language, get reliable answers with traceable SQL, and create or edit dashboards through AI assistance.

## Problem Statement
- BI tools are often difficult for non-technical users.
- SQL and data model knowledge are bottlenecks.
- Dashboard creation is slow and usually depends on analysts.

## MVP Goals
- Allow admins to connect a **business database** (first target **Oracle**; the current build also supports **PostgreSQL** and **MySQL** connection profiles for the same admin and preview flows) and define semantic business knowledge.
- Allow end users to ask business questions and receive:
  - natural-language answer
  - data table
  - executable SQL
- Allow end users to create and edit dashboards via chat.
- Support multiple LLM providers and models by task.

## Out of Scope (MVP)
- Multi-tenant billing.
- Fine-grained row-level security from external IAM.
- Advanced data transformation pipelines.
- Mobile app.

## Success Metrics
- Time-to-first-answer after connection setup: under 10 minutes.
- SQL traceability: 100% of AI responses include viewable SQL.
- Dashboard creation success rate from chat prompt: at least 80% in UAT scenarios.
- Admin semantic update propagation latency: under 1 minute.

## Stakeholders
- Product owner
- Data admin
- BI end users
- Platform engineering
- Security and compliance reviewers
