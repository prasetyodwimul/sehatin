# Security & Privacy

## Public-first boundary

Public Homepage/Nutrition/Blood/Health Checker do not require authentication. Authentication exists only for persistent Guided Nutrition.

## Authentication controls

- password rules enforced by Pydantic;
- password hashed with `hashlib.scrypt`, random salt, and environment `AUTH_PEPPER`;
- no plaintext password storage/logging;
- opaque random session token;
- only HMAC/SHA-256 token hash stored in `auth_sessions`;
- raw token stored only in HttpOnly cookie;
- `SameSite=Lax`;
- production must use `AUTH_COOKIE_SECURE=true` behind HTTPS;
- session expiry configured by `AUTH_SESSION_MINUTES`;
- logout revokes session;
- login/register rate limit stricter than normal API limit.

## Authorization

Every protected Nutrition Program request checks ownership. Foreign program IDs return `404` to avoid revealing resource existence.

## Persistence consent

Health/Nutrition data is not attached to an account until user explicitly chooses **Save & Start Guided Program** and confirms save consent.

Public Health Checker claims remain request-based and are not automatically converted into user history.

## API protections

- CORS allow-list with credentials only for configured frontend origins
- request-size limit including streamed bodies
- global rate limiting
- Pydantic validation
- SQLAlchemy bound queries/ORM
- safe error envelope
- no stack traces to clients
- request ID
- API `Cache-Control: no-store`
- `X-Content-Type-Options`, `X-Frame-Options`, Referrer Policy, Permissions Policy
- HSTS in production

## Frontend protections

- API base URL comes from `NEXT_PUBLIC_API_URL`
- no secret or session token in localStorage/sessionStorage
- React renders user strings as escaped text; no `dangerouslySetInnerHTML`
- CSP configured in Next.js

## Environment secrets

`AUTH_PEPPER` must be long/random and environment-managed in production. `.env` and `.env.local` are ignored by repository.

## Current limitations

- in-memory rate limiter is suitable for single-instance MVP, not distributed production;
- no password reset/email verification flow yet;
- no multi-device session management UI yet;
- Guided Program is educational, not clinical monitoring.

## Nutrition ownership and final-result access

Saved programs, daily logs, progress, history, block review, extension and Final Program Result remain authenticated/private. Program lookup is ownership-scoped server-side before the service is called. Public assessment/result/guidance flows remain available without persistent account data.

## Stage 1 hardening (2026-09-23)

### External URL fetching

User-supplied Health Checker URLs are validated before each HTTP hop. Every DNS answer must be publicly routable. The article fetcher then connects to one of those validated literal IP addresses instead of resolving the hostname again. The actual connected peer IP is compared with the pinned address before any response is trusted. HTTPS still uses the original hostname for SNI and certificate hostname verification; TLS verification is not disabled. Redirects are handled manually and the same validation/pinning process is repeated for every hop.

This intentionally bypasses ambient HTTP proxy resolution for user-supplied article fetches. Deployments that require an outbound proxy should add a security-reviewed proxy integration rather than re-enabling hostname re-resolution in the application fetch path.

### Anonymous Nutrition persistence

`PERSISTENCE_ENABLED` no longer implicitly authorizes storage of personal Nutrition assessment fields from unauthenticated users. Public Nutrition assessment/result remains available, but guest personal-data persistence additionally requires `PERSIST_ANONYMOUS_NUTRITION_PERSONAL_DATA=true`, which defaults to `false`.

Authenticated Guided Nutrition Program saves continue through the ownership-scoped Nutrition Program service and are not controlled by the anonymous persistence flag. Existing stored rows are not deleted automatically; retention/cleanup requires a separate approved policy.

### Production auth cookie configuration

Application startup/config validation rejects `ENVIRONMENT=production` when `AUTH_COOKIE_SECURE=false`. Development may still use an insecure cookie for local HTTP. `HttpOnly` and `SameSite=Lax` behavior is unchanged.
