# Smart BI — Solution Architecture

This document describes the solution from an architecture perspective: capabilities, major components, integrations, and how they satisfy MVP goals. Detailed API and data shapes live in [Technical Design](./04-technical-design.md).

**Implementation status:** Architecture below is **target**; the repo is **hybrid**. Admin **connections**, **semantic layer**, and **AI routing profiles** persist to **JSON files** under `apps/api/data/` (overridable via env — see [Technical Design](./04-technical-design.md)). **Ask Data** with `connection_id` runs **`nl2sql_pipeline`**: semantic + physical schema → LLM **`sql_gen`** (when API keys are set) → **`sqlglot`** read-only policy → execute → LLM **`answer_gen`**, with **heuristic fallback** if keys or SQL fail. **Dashboards** remain **in-process memory** (lost on restart). **Postgres/Redis** from Docker Compose are **not** wired as the app metadata store yet. **`run_task`** uses **real HTTPS** to vendors when env keys exist; otherwise it returns **simulated** stub text.

## 1. Purpose and scope

Smart BI MVP delivers:

- **Governed access to Oracle** via admin-managed connections and a curated semantic layer.
- **Natural-language analytics** with traceable SQL, tabular results, and narrative answers.
- **AI-assisted dashboards** with versioning and safe iteration.

Out of scope for this view matches [Product Vision and Scope](./01-product-vision-and-scope.md) (e.g. multi-tenant billing, mobile-native apps).

## 2. Capability map

| Capability | Primary consumers | Realized by | Build status |
|------------|-------------------|-------------|--------------|
| Identity & roles | All users | JWT auth, `admin` / `user` RBAC | **[Partial]** — dev login only; **no** enforced RBAC |
| Datasource lifecycle | Admin | Connection CRUD, test, introspection | **[Partial]** — **real** connectivity test + schema introspection via SQLAlchemy for **Oracle, PostgreSQL, and MySQL**; profiles persisted to JSON (not Postgres) |
| Semantic governance | Admin | Tables, relationships, dictionary, metrics + versioning | **[Partial]** — CRUD + **file-backed** JSON; **no** semantic versioning |
| Model governance | Admin | AI routing profiles per task | **[Partial]** — profiles **file-backed**; allowlisted providers/models via catalog; **real** HTTPS calls when per-provider **env API keys** are set |
| Ask data | Business user | NL2SQL pipeline, safety policy, execution, narrative | **[Partial]** — without `connection_id`: demo SQL/rows + demo narrative; **with** `connection_id`: **LLM NL2SQL** (semantic + physical schema → `sql_gen` → **sqlglot** policy → read-only execute → `answer_gen`) when keys exist; else **heuristic** preview fallback; `evidence.query_kind` distinguishes **`llm_sql`** vs **`llm_sql_heuristic_fallback`** |
| Dashboard lifecycle | Business user | Create, list, detail, AI edit, versions | **[Partial]** — **in-memory** only; simplified spec merge and version list |
| Observability | Platform | Request logging, AI task metadata (extend for full metrics) | **[Partial]** — HTTP logging only |

## 3. Context (system landscape)

External actors and systems the solution depends on.

```mermaid
flowchart TB
  subgraph org [Organization]
    Admin[Admin]
    User[Business User]
  end

  subgraph smartbi [Smart BI]
    FE[Web App - Next.js]
    API[API - FastAPI]
  end

  subgraph data [Data Plane]
    PG[(Postgres - metadata)]
    Ora[(Oracle - business data)]
    R[(Redis - cache or jobs)]
  end

  subgraph ai [AI Providers]
    LLM1[LLM Provider A]
    LLM2[LLM Provider B]
  end

  Admin --> FE
  User --> FE
  FE --> API
  API --> PG
  API --> Ora
  API --> R
  API --> LLM1
  API --> LLM2
```

## 4. Container view

Logical deployable units in the MVP codebase.

```mermaid
flowchart LR
  subgraph clients [Clients]
    Browser[Browser]
  end

  subgraph apps [Monorepo]
    Web[apps/web]
    Api[apps/api]
    Shared[packages/shared]
  end

  subgraph infra [Local / platform infra]
    Postgres[(Postgres 16)]
    Redis[(Redis 7)]
  end

  Browser --> Web
  Web --> Api
  Web -. contracts .-> Shared
  Api -. contracts .-> Shared
  Api --> Postgres
  Api --> Redis
  Api --> Oracle[(Oracle)]
```

- **Web** (`apps/web`, Next.js App Router, **JavaScript** client components): login, **Admin** console (connections, semantic tabs, AI routing), **Ask Data** (answer card with SQL/details/table), **Dashboards** list/detail; uses `/api-proxy` rewrites or `NEXT_PUBLIC_API_URL` for API access (see `lib/api.js`).
- **API**: Single service owning auth, metadata, semantic layer, chat orchestration, dashboard services, and AI routing.
- **Shared**: Optional shared types/contracts for alignment between web and API.

## 5. Integration principles

- **Oracle**: Only the API tier holds connection credentials; queries run server-side after SQL validation.
- **LLMs**: Invoked through a **task-based router** (`sql_gen`, `answer_gen`, `dashboard_gen`, `extract_classify`) so models can differ per task with fallback policy.
- **Postgres**: System of record for users, connections, semantic definitions, chat/dashboard artifacts, and AI routing configuration.
- **Redis**: Caching, session, or async job state as the implementation matures.

## 6. Cross-cutting concerns

| Concern | Approach |
|---------|----------|
| Security | See [Security Design](./05-security-design.md): JWT, RBAC, credential protection, SQL allowlist, audit hooks. |
| Reliability | Provider fallbacks for AI tasks; defensive validation before executing SQL. |
| Evolvability | Semantic and dashboard versioning; routing profiles configurable without redeploy (target state). |

## 7. Deployment topology (reference)

Typical production pattern:

- **Web** and **API** as separate processes (or containers) behind TLS-terminating ingress.
- **Postgres** and **Redis** as managed or self-hosted data stores.
- **Oracle** reachable only from API network zone (not from browser).

Local development uses Docker Compose for Postgres and Redis per repository `docker-compose.yml`.

## 8. Document map

| Document | Focus |
|----------|--------|
| [User Experience](./02-ux-roadmap.md) | Journeys, IA, UX milestones |
| [Technical Roadmap](./03-technical-roadmap.md) | Delivery phases |
| [Technical Design](./04-technical-design.md) | Components, data model, APIs |
| [Security Design](./05-security-design.md) | Threats and controls |
| [Acceptance Scenarios](./06-acceptance-scenarios.md) | Story-level verification |
