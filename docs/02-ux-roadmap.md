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
| Sign-in / session | All | Access the product | **[Partial]** — stub login UX if any; not production auth UI |
| Admin — Connections | Admin | Create, test, introspect Oracle | **[To do]** |
| Admin — Semantic | Admin | Tables, relationships, dictionary, metrics | **[To do]** |
| Admin — AI routing | Admin | Task profiles (provider, model, limits, fallback) | **[To do]** |
| Ask Data (chat) | User | Questions, answers, SQL, tables | **[To do]** |
| Dashboards | User | List, open, create from chat, AI edit with versions | **[To do]** |

## Screen inventory (MVP)

- **[To do] Auth**: login; session recovery or sign-out as needed.
- **[To do] Admin connection**: form (host, port, service/SID, credentials), test result, introspect action and job status.
- **[To do] Admin semantic**: editors for table descriptions, relationship overrides, business terms, metrics; version indicator where applicable.
- **[To do] Admin AI routing**: profile list/detail; validate configuration action.
- **[To do] Chat workspace**: thread or session list, composer, message list with **answer card** (summary, expandable SQL, table, confidence/warnings).
- **[To do] Dashboard**: gallery/list; detail view; create-from-prompt flow; AI edit with **preview** and version history / rollback.

**Note:** `apps/web` currently ships a **thin navigation shell** and placeholder pages; the screens above are **specification**, not yet product UI.

## Core User Journeys
1. Admin connects Oracle and validates connectivity.
2. Admin reviews discovered schema and writes business metadata.
3. User asks a question and inspects answer, SQL, and result table.
4. User creates dashboard from chat output and saves it.
5. User edits existing dashboard via AI prompt with preview.

## UX Milestones

### Milestone A - Foundation UX
- **[Partial]** Authentication screens
- **[Partial]** Role-aware navigation (basic shell only)
- **[To do]** Empty states and onboarding hints

### Milestone B - Admin Console UX
- **[To do]** Connection form with test feedback
- **[To do]** Schema browser with search and filters
- **[To do]** Semantic editor for tables, relationships, dictionary, and metrics

### Milestone C - Ask Data UX
- **[To do]** Chat with message history
- **[To do]** Structured answer card:
  - Answer summary
  - SQL panel
  - Data table
- **[To do]** Confidence and warning indicators

### Milestone D - Dashboard UX
- **[To do]** Prompt-to-dashboard flow
- **[To do]** Dashboard preview and save
- **[To do]** Dashboard list/detail
- **[To do]** AI edit prompt with diff preview and version rollback

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
