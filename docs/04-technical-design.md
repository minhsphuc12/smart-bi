# Smart BI Technical Design

## As-built vs this document

**Status legend:** **[Done]** = matches design direction in code · **[Partial]** = stub or simplified · **[To do]** = not implemented as described

| Topic | Status | Notes |
|-------|--------|--------|
| Monorepo layout (`apps/web`, `apps/api`, `packages/shared`) | **[Done]** | Web uses Next.js App Router (`.js` client components). |
| Docker Compose Postgres + Redis | **[Done]** | Containers available; **API domain data not stored in Postgres yet**. |
| Admin persistence (connections, semantic, AI routing) | **[Partial]** | **JSON files** under `apps/api/data/` with atomic writes; env overrides (see below). |
| Router modules listed below | **[Partial]** | Endpoints implemented; dashboards **persist** via `dashboard_store` with in-process cache + lock. |
| Auth (JWT + RBAC enforcement on routes) | **[To do]** | `POST /auth/login` returns dev token + role heuristic; **no** verification middleware on routers. |
| Multi-engine connectivity | **[Partial]** | `app/services/db_engine.py`: **Oracle**, **PostgreSQL**, **MySQL** URLs, ping, introspection, `preview_select` (read-only `LIMIT`). Used by admin test/introspect and chat when `connection_id` set. |
| NL2SQL + SQL safety (AST, allowlist) | **[Partial]** | With `connection_id`: **`nl2sql_pipeline`** calls LLM `sql_gen`, then **`sql_policy`** (`sqlglot`) for read-only SELECT + table allowlist + row cap; **no** heuristic **`preview_for_question`** fallback — failures return **HTTP 400**. |
| AI router real providers | **[Partial]** | **`llm_client`** + **`httpx`**: OpenAI-compatible chat, Anthropic Messages, Gemini `generateContent` when env API keys set; missing keys → **`run_task`** returns **`live: false`** + **`error`** (no simulated output). |
| Dashboard persistence | **[Partial]** | **File-backed JSON** via `dashboard_store` → `apps/api/data/dashboards.json` (`SMART_BI_DASHBOARDS_FILE`); in-memory copy under `app/routers/dashboards.py` lock. **`dashboard_gen`** requires **`llm_client`**; optional **`connection_id`** runs introspection when the cache is empty so the LLM gets physical schema and emits widget **`sql`** (`dashboard_ai.py`). Bad keys or unusable JSON → **HTTP 400**. **Manual edits:** **`PATCH` / `DELETE /dashboards/{id}`**; **`POST` / `PATCH` / `DELETE /dashboards/{id}/widgets/{index}`** with `normalize_spec` validation; each change appends a **version** row (same history as AI edits). |

### File-backed admin data (as-built)

| Concern | Default path | Override env var |
|---------|----------------|------------------|
| Datasource connections | `apps/api/data/connections.json` | `SMART_BI_CONNECTIONS_FILE` |
| Semantic bundle (tables, relationships, dictionary, metrics) — Admin UI CRUD only | `apps/api/data/semantic.json` | `SMART_BI_SEMANTIC_FILE` |
| LLM semantic context (Ask + dashboards): raw YAML files | `<repo>/mart/` (recursive `*.yml` / `*.yaml`) | `SMART_BI_SEMANTIC_MART_DIR` |
| AI routing profiles per task | `apps/api/data/ai_routing.json` | `SMART_BI_AI_ROUTING_FILE` |
| Dashboards + version history | `apps/api/data/dashboards.json` | `SMART_BI_DASHBOARDS_FILE` |

Passwords for connections are stored **in plaintext inside the JSON file** (development convenience only — see [Security Design](./05-security-design.md)).

## Repository layout

| Path | Responsibility |
|------|----------------|
| `apps/web` | Next.js frontend (admin + user workspaces) |
| `apps/api` | FastAPI application (`app.main`), routers under `app/routers/` |
| `packages/shared` | Shared contracts (schemas, DTOs) |
| `docker-compose.yml` | Local Postgres 16 + Redis 7 |

## High-Level Architecture
- `apps/web`: Next.js frontend for admin and users (JavaScript client modules).
- `apps/api`: FastAPI backend for auth, semantic layer, chat, dashboards.
- `packages/shared`: shared schemas and DTO contracts.
- **Postgres** (Compose): available for future app metadata; **not** the active store for connections/semantic/routing today.
- **Business databases**: Oracle, PostgreSQL, or MySQL via SQLAlchemy (`oracledb` / `psycopg` / `pymysql` drivers as configured in requirements).
- **Redis** (Compose): available for future cache/session/job state.

Solution-level diagrams and capability mapping: [Solution Architecture](./solution-architecture.md).

## Service Components (FastAPI)
- Auth service (JWT + RBAC).
- Connection service (Oracle config and validation).
- Schema service (introspection and metadata sync).
- Semantic service (table, relation, dictionary, metric CRUD + versioning).
- AI router service (multi-provider, task-based model profiles).
- Query service (NL2SQL + safety checks + execution).
- Dashboard service (create, edit, versioning).

## API modules (implementation)

Routers registered in `apps/api/app/main.py`:

| Router module | Prefix (typical) | Concern |
|---------------|------------------|---------|
| `auth` | `/auth` | Login / JWT |
| `admin_connections` | `/admin/connections` | Oracle profiles, test, introspect |
| `admin_semantic` | `/admin/semantic` | Tables, relationships, dictionary, metrics (JSON); read-only mart browse: **`GET /admin/semantic/mart/files`**, **`GET /admin/semantic/mart/content?path=`** (relative POSIX path under mart root) |
| `admin_ai_routing` | `/admin/ai-routing` | Catalog (`GET …/catalog`), profiles CRUD, `POST …/validate` |
| `chat` | `/chat` | Ask data (`POST /chat/questions`) — **`connection_id` required**: **NL2SQL** (mart YAML in system prompt + schema in user message → LLM SQL → policy → execute → LLM answer); missing keys / policy / execution errors → **HTTP 400** |
| `dashboards` | `/dashboards` | CRUD, AI edit, versions |

Health: `GET /health`.

## Ask Data sequence

**Target (full NL2SQL):**

```mermaid
sequenceDiagram
  participant U as User
  participant W as Web
  participant A as API
  participant R as AI Router
  participant O as Oracle

  U->>W: Submit question
  W->>A: POST /chat/questions
  A->>R: sql_gen task
  R-->>A: SQL / model meta
  Note over A: SQL validation and allowlist
  A->>O: Execute read-only query
  O-->>A: Rows
  A->>R: answer_gen task (grounded on results)
  R-->>A: Narrative
  A-->>W: answer, sql, columns, rows, confidence, warnings
  W-->>U: Answer card
```

**As-built today:** `connection_id` is **required** (no demo placeholder path). **`nl2sql_pipeline`** loads **concatenated mart YAML** (`semantic_store.load_mart_yaml_bundle_text`) into the **`sql_gen` system prompt**, passes cached/introspected **physical schema** and the user question in the user message, calls **`run_task("sql_gen", …)`**, validates via **`sql_policy.prepare_readonly_select`** (`sqlglot`, allowlisted physical tables, CTE names exempt from physical match, row cap), executes read-only via SQLAlchemy `text()`, then calls **`run_task("answer_gen", …)`** with question + SQL + JSON sample rows for the user-facing answer. Missing API keys, invalid SQL, execution errors, or empty model output raise **`ValueError`** → **HTTP 400** with `detail` for the web client. Successful responses set **`evidence.query_kind`** to **`llm_sql`** and **`meta.sql_live` / `meta.answer_live`** to **true**. **`dashboard_gen`** includes the same mart YAML block in its system prompt (`dashboard_ai.py`).

## AI Task Profiles
- `sql_gen`: SQL generation and SQL repair.
- `answer_gen`: user-facing narrative answer.
- `dashboard_gen`: dashboard spec generation and patching.
- `extract_classify`: entity extraction and intent classification.

Each profile includes:
- provider
- model
- temperature
- max_tokens
- timeout_ms
- cost_limit
- fallback_profile

## Data Model (Core)
- `users`
- `roles`
- `datasource_connections`
- `schemas`
- `tables`
- `columns`
- `relationships`
- `dictionary_terms`
- `metrics`
- `semantic_versions`
- `ai_routing_profiles`
- `chat_sessions`
- `chat_messages`
- `query_runs`
- `dashboards`
- `dashboard_versions`

## API Contracts (Core)
- Admin:
  - `GET`/`POST` `/admin/connections`; `PUT` `/admin/connections/{id}`
  - `POST` `/admin/connections/{id}/test` — real DB ping
  - `POST` `/admin/connections/{id}/introspect` — real metadata query; caches result server-side for chat
  - `GET`/`POST`/`PUT` `/admin/semantic/tables|relationships|dictionary|metrics`
  - `GET` `/admin/ai-routing/catalog` — allowlisted providers and models (`app/ai_routing_catalog.py`)
  - `GET`/`POST`/`PUT` `/admin/ai-routing/profiles`; `POST` `/admin/ai-routing/validate`
- User:
  - `POST` `/chat/questions` — body: `{ "question": string, "connection_id": number }` — response adds **`evidence`** (`query_kind`, `row_count`, `execution_ms`, …) and `meta.sql_task_note` / `meta.answer_task_note` (truncated model text on success).
  - `GET`/`POST` `/dashboards` — body `{ "title", "prompt", "connection_id?" }` — response includes **`meta.dashboard_gen`** (`live`, `provider`, `model`, `error` when applicable).
  - `GET` `/dashboards/{id}`; `POST` `/dashboards/{id}/ai-edit` — body `{ "prompt", "connection_id?" }` — returns `preview`, **`meta`**; `GET` `/dashboards/{id}/versions`
  - `POST` `/dashboards/{id}/run-queries` — body `{ "connection_id?" }` — executes each widget **`sql`** (read-only, **sqlglot** allowlist); uses body `connection_id` or **`dashboard.connection_id`**; response `{ "connection_id", "series": [{ "widget_index", "sql_executed", "columns", "rows", "error" }] }`.

Connection payloads support `source_type`: `oracle` | `postgresql` | `mysql` (see `ConnectionPayload` in `admin_connections.py`).

## SQL Safety Rules
- Read-only statements only.
- Allowlist schema and tables.
- Enforce row limit defaults.
- Deny dangerous functions or DDL/DML.
- Require parsed SQL AST validation before execution.

## Operational notes

- **Local API**: Python 3.12 or 3.13 recommended; run with `uvicorn app.main:app`.
- **Observability**: HTTP request logging middleware is attached in `main.py`; extend with structured metrics and AI token/cost counters per task profile for production.
- **Evolution**: Replace stubbed or simplified chat/dashboard paths with full NL2SQL + spec validation while keeping response contracts stable for the web client.

**[To do]** items aligned with roadmap: Postgres-backed metadata, credential encryption at rest, NL2SQL + **SQL policy engine** on any generated text, provider SDK integration, dashboards in **Postgres** (today: JSON file only), enforced JWT/RBAC, and semantic **versioning**.

**Implemented recently (summary):** SQLAlchemy-based engine layer for three DB kinds; file persistence for admin stores and **dashboards** (`dashboard_store`); admin AI catalog; **`llm_client`** (OpenAI / Anthropic / Google HTTP); Ask Data **`nl2sql_pipeline`** + **`sql_policy`** (`sqlglot`) with **HTTP 400** on failure (no heuristic fallback); Next.js flows for admin / ask / dashboards; Playwright smoke tests (`apps/web/e2e/app.spec.js`).

### LLM credentials (operations)

| Variable | Purpose |
|----------|---------|
| `SMART_BI_OPENAI_API_KEY` / `OPENAI_API_KEY` | OpenAI or OpenAI-compatible API |
| `SMART_BI_OPENAI_BASE_URL` / `OPENAI_API_BASE` | Optional chat-completions base (default OpenAI cloud) |
| `SMART_BI_ANTHROPIC_API_KEY` / `ANTHROPIC_API_KEY` | Anthropic Messages API |
| `SMART_BI_GOOGLE_API_KEY` / `GOOGLE_API_KEY` / `GEMINI_API_KEY` | Google Gemini `generateContent` |
| `SMART_BI_SEMANTIC_MART_DIR` | Optional absolute path to a folder of semantic YAML for LLM prompts (defaults to `<repo>/mart/`) |

Keys are read from the **process environment** after optional **`.env` files** are loaded at API startup: repository root `.env` then `apps/api/.env` (see `app/main.py`; `python-dotenv`). Do not store secrets in `apps/api/data/*.json`.

## Change Log

- 2026-04-14: Documented mart YAML for Ask Data and `dashboard_gen` system prompts; clarified `semantic.json` is admin CRUD only (`SMART_BI_SEMANTIC_MART_DIR`).
- 2026-04-14: Admin **mart YAML** read-only API and web tab (`/admin/semantic/mart/files`, `/admin/semantic/mart/content`).
- 2026-04-14: Web Admin semantic tab label is **Semantic Repo** (was “Mart YAML”); mart file preview uses explicit light text on the dark `<pre>` panel because `var(--text, …)` always resolved to the global dark body text color.
- 2026-04-14: API startup now loads **monorepo root** `.env` (not `apps/.env`); default **mart** directory is discovered by walking up from `semantic_store.py` until a `mart/` folder exists (still overridable with `SMART_BI_SEMANTIC_MART_DIR`).
