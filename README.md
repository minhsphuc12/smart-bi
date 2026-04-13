# Smart BI MVP

Monorepo for Smart BI MVP:
- `apps/web`: Next.js frontend
- `apps/api`: FastAPI backend
- `packages/shared`: shared contracts

## Quick Start

### 1) Infrastructure
```bash
docker compose up -d
```

### 2) API
Use **Python 3.12 or 3.13** (Pydantic wheels may not be available for 3.14 yet).

```bash
cd apps/api
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional: edit .env for LLM keys and path overrides
uvicorn app.main:app --reload --port 8000
```

On startup the API loads environment files (without clobbering variables already set in the shell):

1. **`<repo>/.env`** — optional shared defaults for the whole monorepo  
2. **`apps/api/.env`** — optional overrides for the API (wins over repo for duplicate keys)

Use **`apps/api/.env.example`** as a template. **Never commit** `.env` (it stays gitignored).

### LLM API keys (server-side only)

Ask Data **requires** a **`connection_id`** (an Admin datasource) and **provider API keys** for both **`sql_gen`** and **`answer_gen`** (profiles from **Admin → AI routing**). The API calls vendors over HTTPS; if keys are missing or the LLM fails, **`POST /chat/questions`** returns **HTTP 400** with a clear `detail` message (the Ask UI shows it).

**Dashboards** use the **`dashboard_gen`** profile the same way: **HTTPS** to the vendor, optional **`connection_id`** on create/edit (the API **introspects** when needed so widgets can include **`sql`**). Missing keys, vendor errors, or unusable JSON return **HTTP 400** instead of stub layouts. Responses include **`meta.dashboard_gen`** (`live`, `error`, provider/model). Dashboards and version history are written to **`apps/api/data/dashboards.json`** by default (override with **`SMART_BI_DASHBOARDS_FILE`**), same atomic-write pattern as other admin JSON stores.

| Provider | Env vars (first match wins) | Optional base URL |
|----------|------------------------------|-------------------|
| **openai** | `SMART_BI_OPENAI_API_KEY`, `OPENAI_API_KEY` | `SMART_BI_OPENAI_BASE_URL` or `OPENAI_API_BASE` (default `https://api.openai.com/v1`) |
| **anthropic** | `SMART_BI_ANTHROPIC_API_KEY`, `ANTHROPIC_API_KEY` | — |
| **google** (Gemini) | `SMART_BI_GOOGLE_API_KEY`, `GOOGLE_API_KEY`, `GEMINI_API_KEY` | — |

Set keys in **`apps/api/.env`**, the repo-root `.env`, your shell, or your deployment secret store — **never commit** real tokens. Semantic layer content is loaded from `semantic.json` (or `SMART_BI_SEMANTIC_FILE`) and sent in the SQL prompt together with introspected physical schema.

### API tests

From `apps/api` with the virtual environment activated:

```bash
cd apps/api
source .venv/bin/activate
pip install -r requirements.txt
pytest tests/test_api.py -v
```

Pytest writes a JSON report to `apps/api/test-record.json` (via `pytest-json-report` in `apps/api/pytest.ini`). That file is gitignored; remove `--json-report` and related flags from `addopts` if you do not want a local report.

### 3) Web
```bash
cd apps/web
npm install
npm run dev
```

From repo root you can run **`npm run lint:web`** (ESLint via Next), **`npm run build:web`** (`next build` after removing `apps/web/.next` to avoid stale or racing `.next` artifacts), and **`npm run test:e2e`** (Playwright; starts API + web per `playwright.config`). Prefer running these **one after another**, not in parallel, if you ever invoke `next build` / `next dev` manually at the same time.

Next.js automatically loads **`apps/web/.env.local`** (gitignored). Use `NEXT_PUBLIC_API_URL` when the browser should call the API on a non-default host/port (otherwise the app uses same-origin `/api-proxy`).

## Documentation

| Document | Description |
|----------|-------------|
| [docs/01-product-vision-and-scope.md](docs/01-product-vision-and-scope.md) | Vision, MVP scope, success metrics |
| [docs/02-ux-roadmap.md](docs/02-ux-roadmap.md) | **User experience** — IA, journeys, milestones |
| [docs/solution-architecture.md](docs/solution-architecture.md) | **Solution architecture** — capabilities, context, containers |
| [docs/03-technical-roadmap.md](docs/03-technical-roadmap.md) | **Roadmap** — phases, dependencies, post-MVP |
| [docs/04-technical-design.md](docs/04-technical-design.md) | **Technical design** — components, data model, APIs |
| [docs/05-security-design.md](docs/05-security-design.md) | Security controls and threat model |
| [docs/06-acceptance-scenarios.md](docs/06-acceptance-scenarios.md) | User story acceptance tests |

## Changelog

All notable changes to this project are documented in this section. Versions follow API `version` in `apps/api/app/main.py` where applicable.

### [Unreleased]

- API + web: **remove simulated LLM and heuristic fallbacks** for Ask Data, `run_task`, and dashboard generation — missing provider keys, unusable model JSON, SQL policy violations, or execution errors return **HTTP 400** with a `detail` string; Ask and Dashboards UIs surface that message.
- Web: add **ESLint** (`eslint`, `eslint-config-next`, `apps/web/.eslintrc.json`); fix admin tab buttons with **`role="tab"`** for a11y; root scripts **`npm run lint:web`** and **`npm run build:web`** (cleans `apps/web/.next` before `next build` to avoid corrupt parallel builds).
- API: load optional **`.env`** files via `python-dotenv` (`repo/.env` then `apps/api/.env`); add `apps/api/.env.example`.
- Ask Data: **`connection_id` required** (no bundled demo DB); NL2SQL with **LLM** + **semantic layer** + live schema; **sqlglot** policy (read-only SELECT, table allowlist, row cap); **no** heuristic preview when keys or SQL path fail — **HTTP 400** with `detail`; Ask UI picks a configured datasource by default.
- Dashboards: **`dashboard_gen`** wired to **`llm_client`** with strict JSON widget contract (including per-widget **`sql`** when a datasource is selected); **no** heuristic widget layout on parse failure — **HTTP 400**; **`POST /dashboards/{id}/run-queries`** executes widget SQL with the same read-only policy as Ask Data; web draws SVG charts / KPI / table from results; **file persistence** (`dashboard_store`, `SMART_BI_DASHBOARDS_FILE`).

### [0.1.0] — 2026-04-11

- Initial monorepo: Next.js web app, FastAPI API (`0.1.0`), shared package.
- Local stack: Docker Compose for Postgres 16 and Redis 7.
- API surface: auth, admin (Oracle connections, semantic layer, AI routing), chat, dashboards; `GET /health`.
- Documentation set under `docs/` (vision, UX, solution architecture, technical roadmap/design, security, acceptance scenarios).
- API tests via `pytest` with optional JSON report to `apps/api/test-record.json` (gitignored).

## Notes
- Oracle is the first datasource.
- AI task routing supports different providers/models per task profile.
