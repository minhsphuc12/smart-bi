# Smart BI MVP Acceptance Scenarios

**Verification status (against production MVP intent):** **[Pass — partial]** = API/demo only with stubs · **[To do]** = full scenario not yet verifiable end-to-end

| Story | Status |
|-------|--------|
| 1 Admin Connect Oracle | **[Pass — partial]** — endpoints return success/stub metadata; **not** real Oracle |
| 2 Admin Semantic | **[Pass — partial]** — CRUD in memory; **not** durable semantic layer |
| 3 User Ask Data | **[Pass — partial]** — response shape matches; SQL/rows **hardcoded** |
| 4 Dashboard from chat | **[Pass — partial]** — in-memory create/list; **not** wired to real chat output |
| 5 AI dashboard edit | **[Pass — partial]** — simplified version bump; **not** full preview/diff/rollback UX |

## Story 1: Admin Connect Oracle
### Given
- Admin is authenticated.
### When
- Admin creates Oracle connection and runs test.
### Then
- API returns successful test result.
- Admin can trigger schema introspection and get table metadata.

## Story 2: Admin Manage Semantic Knowledge
### Given
- Oracle metadata exists.
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
