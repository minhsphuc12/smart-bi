# Smart BI MVP Acceptance Scenarios

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
