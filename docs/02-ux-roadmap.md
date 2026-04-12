# Smart BI — User Experience

This document defines personas, information architecture, primary journeys, UX milestones, and interaction principles for the MVP. Delivery sequencing aligns with [Technical Roadmap](./03-technical-roadmap.md).

**Status legend:** **[Done]** = implemented in `apps/web` to UX intent · **[Partial]** = placeholder / thin shell · **[To do]** = not built

## Personas
- **Admin**: configures datasource and semantic layer; governs AI routing for tasks.
- **Business user**: asks questions, inspects evidence (SQL + data), and manages dashboards with AI assistance.

## Information architecture

Top-level areas (role-aware navigation):

| Area | Audience | Purpose | UX build |
|------|----------|---------|----------|
| Sign-in / session | All | Access the product | **[Partial]** — `/login` + `localStorage` session; **dev** token from API; not production auth |
| Admin — Connections | Admin | Create, test, introspect datasources | **[Partial]** — full form (name, **source type** Oracle/PostgreSQL/MySQL, host, port, service or database, credentials), list, **Test** and **Introspect** actions |
| Admin — Semantic | Admin | Tables, relationships, dictionary, metrics | **[Partial]** — tabbed editors with list + add + inline edit per segment (no version UI) |
| Admin — AI routing | Admin | Task profiles (provider, model, limits) | **[Partial]** — catalog-driven pickers + save per task (`sql_gen`, `answer_gen`, `dashboard_gen`, `extract_classify`) |
| Ask Data (chat) | User | Questions, answers, SQL, tables | **[Partial]** — composer + messages; **answer card** (answer, confidence, warnings, collapsible SQL, table, model line); optional **connection** selector for live preview |
| Dashboards | User | List, open, create from chat, AI edit with versions | **[Partial]** — list, create modal, detail; AI edit returns preview payload (simplified backend) |

## Screen inventory (MVP)

- **[Partial] Auth** (`/login`): username/password → stores session; role badge from dev API (`admin*` → admin). Sign out clears session.
- **[Partial] Admin** (`/admin`): tabbed **Admin console** — **Connections** (new connection form, table of connections, test/introspect), **Semantic layer** (four segments), **AI routing** (per-task profile forms + catalog).
- **[Partial] Ask Data** (`/ask`): question field, **Ask** button, optional connection picker when connections exist; assistant **answer card** per UX principles.
- **[Partial] Dashboards** (`/dashboards`, `/dashboards/[id]`): list + new dashboard; detail client with AI edit flow per API capabilities.

**Implementation note:** UI is **Next.js App Router** with client components in `.js` files; API base from `NEXT_PUBLIC_API_URL` or same-origin **`/api-proxy`** rewrite to FastAPI (`apps/web/lib/api.js`, `next.config.js`).

## Core User Journeys
1. Admin connects Oracle and validates connectivity.
2. Admin reviews discovered schema and writes business metadata.
3. User asks a question and inspects answer, SQL, and result table.
4. User creates dashboard from chat output and saves it.
5. User edits existing dashboard via AI prompt with preview.

## UX Milestones

### Milestone A - Foundation UX
- **[Partial]** Authentication screens (`/login`)
- **[Partial]** Role-aware navigation (`TopNav`: Ask Data, Dashboards, Admin for admin role)
- **[Partial]** Empty states in semantic segments and connections list

### Milestone B - Admin Console UX
- **[Partial]** Connection form with **Test** / **Introspect** feedback (errors from API surfaced)
- **[Partial]** Schema outcome shown after introspect (table/column list from API) — **no** dedicated schema browser with search/filters yet
- **[Partial]** Semantic editor for tables, relationships, dictionary, and metrics

### Milestone C - Ask Data UX
- **[Partial]** Chat with **in-session** message history (not persisted server-side)
- **[Partial]** Structured answer card (answer, SQL in `<details>`, table, confidence, warnings, `meta` models line)
- **[To do]** Persisted chat sessions; streaming answers

### Milestone D - Dashboard UX
- **[Partial]** Prompt-to-dashboard flow (create from UI)
- **[Partial]** Dashboard list/detail; create returns to list
- **[Partial]** AI edit with API **preview** field — **no** rich diff / rollback UI yet

## Interaction patterns
- **Evidence first**: surface SQL and raw rows alongside narrative so users can validate the answer.
- **Progressive disclosure**: SQL collapsed by default for business users; easy expand for analysts.
- **Destructive or structural changes**: dashboard AI edits require preview; saving creates an explicit new version.
- **Admin feedback**: inline validation on connection and semantic forms; clear errors from test and introspect endpoints.

## UX Principles
- Always show SQL used for the answer.
- Always separate generated insight from raw data.
- Minimize clicks to save dashboard from chat.
- Keep terminology business-friendly with dictionary aliases.

## Accessibility and quality bar
- Keyboard-accessible primary flows (login, ask question, expand SQL).
- Sufficient contrast for data tables and status badges (confidence, warnings).
- Loading and empty states for long introspection or slow LLM responses.

## Edge Cases
- Empty result set
- Long-running query
- Invalid semantic metric formula
- AI confidence below threshold
- Provider/model timeout
