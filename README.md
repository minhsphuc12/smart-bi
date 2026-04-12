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

Ask Data with a **`connection_id`** uses `sql_gen` and `answer_gen` profiles from **Admin → AI routing**. When the matching provider has an API key in the environment, the API calls the vendor over HTTPS; otherwise it falls back to **simulated** router text and a **heuristic** SQL preview.

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

- API: load optional **`.env`** files via `python-dotenv` (`repo/.env` then `apps/api/.env`); add `apps/api/.env.example`.
- Ask Data: NL2SQL with **LLM** + **semantic layer** + live schema when `connection_id` is set and provider API keys exist; **sqlglot** policy (read-only SELECT, table allowlist, row cap); heuristic preview fallback; Ask UI refresh (sidebar, chips, CSV export, copy answer, keyboard submit).

### [0.1.0] — 2026-04-11

- Initial monorepo: Next.js web app, FastAPI API (`0.1.0`), shared package.
- Local stack: Docker Compose for Postgres 16 and Redis 7.
- API surface: auth, admin (Oracle connections, semantic layer, AI routing), chat, dashboards; `GET /health`.
- Documentation set under `docs/` (vision, UX, solution architecture, technical roadmap/design, security, acceptance scenarios).
- API tests via `pytest` with optional JSON report to `apps/api/test-record.json` (gitignored).

## Notes
- Oracle is the first datasource.
- AI task routing supports different providers/models per task profile.
