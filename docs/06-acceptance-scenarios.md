# Smart BI MVP Acceptance Scenarios

**Verification status (against production MVP intent):** **[Pass — partial]** = API/demo only with stubs · **[To do]** = full scenario not yet verifiable end-to-end

| Story | Status |
|-------|--------|
| 1 Admin Connect datasource | **[Pass — partial]** — **real** `POST …/test` and `POST …/introspect` against a reachable **Oracle, PostgreSQL, or MySQL** instance; results persisted in **process + JSON** (not enterprise metadata DB) |
| 2 Admin Semantic | **[Pass — partial]** — CRUD **durable** via `semantic.json`; **no** versioning |
| 3 User Ask Data | **[Pass — partial]** — without `connection_id`: demo SQL/rows; **with** `connection_id`: **live read-only preview** (heuristic table, max 50 rows); narrative still **simulated** |
| 4 Dashboard from chat | **[Pass — partial]** — in-memory create/list/detail in API; UI can create from prompts; **lost on API restart** |
| 5 AI dashboard edit | **[Pass — partial]** — version list grows on edit; preview in API response; **no** full diff/rollback UX |

## Story 1: Admin Connect datasource (Oracle primary)
### Given
- Admin is authenticated (dev session).
### When
- Admin creates a connection (`source_type` **oracle**, **postgresql**, or **mysql**) and runs **Test**, then **Introspect**.
### Then
- API returns successful test when the database is reachable.
- Introspection returns `{ tables: [{ name, columns }] }` and populates server-side cache used by Ask Data.

## Story 2: Admin Manage Semantic Knowledge
### Given
- Datasource metadata exists (from introspection or external knowledge).
### When
- Admin creates or updates table descriptions, relationships, dictionary terms, and metrics.
### Then
- Semantic endpoints persist and return updated items.

## Story 3: User Ask Business Question
### Given
- Semantic data and AI routing profiles are configured.
### When
- User asks a business question in chat.
### Then
- Response includes answer text, SQL, columns, rows, confidence, warnings.

## Story 4: User Create Dashboard with Chat
### Given
- User receives a valid answer from Ask Data flow.
### When
- User creates dashboard from prompt.
### Then
- Dashboard is saved and appears in dashboard list/detail.

## Story 5: User Edit Dashboard with AI
### Given
- Existing dashboard is available.
### When
- User sends AI edit prompt.
### Then
- Updated spec is previewed and persisted as a new version.
- Version history endpoint returns both initial and edited versions.
