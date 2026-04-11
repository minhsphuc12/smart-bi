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
uvicorn app.main:app --reload --port 8000
```

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

## Notes
- Oracle is the first datasource.
- AI task routing supports different providers/models per task profile.
