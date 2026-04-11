# Smart BI Security Design

## Security Objectives
- Protect datasource credentials and user data.
- Prevent unsafe SQL execution.
- Maintain auditable AI-assisted actions.

## Identity and Access
- JWT authentication with short-lived access tokens.
- Role-based authorization:
  - `admin`: datasource and semantic management
  - `user`: ask data and dashboard operations

## Secret Management
- Never expose raw credentials to frontend.
- Encrypt Oracle passwords at rest using server-side key management.
- Keep provider API keys in secure runtime secrets.

## Data Protection
- TLS in transit.
- Encryption at rest for metadata database volumes.
- Mask sensitive fields in logs.

## Query Safety
- Validate generated SQL via parser and policy engine.
- Restrict to read-only operations.
- Enforce schema/table allowlist.
- Apply query timeout and row limit.

## AI Security Controls
- Prompt templates with explicit boundaries.
- Input sanitization before provider calls.
- Response validation before execution.
- Fallback policies do not bypass security checks.

## Audit and Monitoring
- Audit events:
  - login
  - datasource changes
  - semantic changes
  - AI routing profile changes
  - dashboard create/edit/rollback
- Capture request IDs and actor IDs.
- Emit metrics for failed auth, SQL rejections, and provider errors.

## Threat Model (MVP)
- Prompt injection attempt in user question.
- Credential leakage via misconfigured logs.
- Over-permissive SQL from AI generation.
- Unauthorized dashboard modifications.

## Security Test Plan
- Authorization tests for all admin endpoints.
- SQL policy tests with malicious payloads.
- Secret redaction tests in logs.
- Basic dependency and container scanning.
