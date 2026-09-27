# SEHATIN API

Base URL is configured by deployment. Frontend uses `NEXT_PUBLIC_API_URL`.

## Public endpoints

### GET `/health`
Health/readiness response. No login.

### POST `/api/nutrition/validate`
Server-side anthropometric validation for MPASI/Toddler/Lansia.

Returns:

```json
{
  "status": "VALID | WARNING | INVALID",
  "can_process": true,
  "message": "...",
  "issues": [],
  "indicators": [],
  "references": []
}
```

`WARNING` may be processed. `INVALID` blocks recommendation.

### POST `/api/nutrition/recommendation`
Public Nutrition recommendation. No login. Response includes validation + educational recommendation. This endpoint does not create a Guided Program.

### Blood

```text
GET /api/blood/facilities
GET /api/blood/inventory
GET /api/blood/facilities/{facility_id}
```

Current competition inventory is simulated/demo.

### POST `/api/health-checker/analyze`
Public claim analysis with structured evidence/verdict. No personal account required.

## Controlled authentication

Authentication is used only for persistent Guided Nutrition.

### POST `/api/auth/register`

```json
{
  "email": "user@example.com",
  "password": "StrongPass123"
}
```

On success the server sets an opaque `sehatin_session` HttpOnly cookie.

### POST `/api/auth/login`
Same request shape. Invalid credentials return a generic email/password error.

### GET `/api/auth/me`
Requires valid session cookie.

### POST `/api/auth/logout`
Revokes server-side session and clears cookie.

## Protected Guided Nutrition endpoints

All endpoints below require session cookie and verify program ownership.

### POST `/api/nutrition/program`

```json
{
  "assessment": { "stage": "toddler", "...": "..." },
  "consent_to_save": true,
  "duration_days": 14
}
```

Creates saved profile/recommendation/program only after explicit consent. Assessments that are safety-limited cannot start a program.

### GET `/api/nutrition/program`
Lists programs owned by current authenticated user.

### GET `/api/nutrition/program/{program_id}`
Returns profile snapshot, saved recommendation, and program days. Foreign-owned id returns `404`.

### POST `/api/nutrition/program/{program_id}/daily-log`
Persists checklist state and optional meal note for the **current calendar day**. Future days return `409 PROGRAM_DAY_LOCKED`; prior missed days return `409 PROGRAM_DAY_CLOSED`. A successful response is authoritative and includes `saved`, `saved_at`, current day, completed/missed days, task counts, program progress, goal progress, cumulative goal state, inactivity, and program status.

### GET `/api/nutrition/program/{program_id}/progress`
Returns centralized backend metrics. `program_progress = completed_days / duration_days × 100`. Goal progress is separately calculated as `actual / target × 100`. The response also includes `current_day`, `missed_days`, `inactive_days`, `last_activity_at`, goal state, and cumulative extension-goal state.

### GET `/api/nutrition/program/{program_id}/evaluation`
Compares goal baseline/target/actual after or during the program. Program completion does not imply goal success. The educational evaluation can return goal `MET`, `PARTIALLY_MET`, or `NOT_MET`; it does not diagnose health status.

## Error format

```json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "Human-readable message"
  }
}
```

No stack trace is returned to clients.

## Nutrition journey additions

Authenticated endpoints:

- `GET /api/nutrition/history` — all saved program cycles for current user.
- `GET /api/nutrition/history/{program_id}` — immutable-style journey detail using saved snapshots.
- `GET /api/nutrition/program/{program_id}/extension-recommendation` — remaining goal gap and recommended extension duration after a completed/expired program.
- `POST /api/nutrition/program/{program_id}/extend` — creates a confirmed adaptive extension cycle (`{"confirm": true}`).

Program detail now includes `goals`, `assessment_snapshot`, actionable day metadata, concrete meal-guidance metadata, references, and `extension_history`. Daily-log responses remain authoritative and now also return current goal state.

## Nutrition UX/state consistency endpoints (20260918)

All endpoints below are protected and verify `program.user_id == authenticated_user.id`.

- `GET /api/nutrition/program/{program_id}/days/{day_number}` — returns one day with backend-authoritative `status`, `unlock_at`, `remaining_seconds`, and `completed_at`. Locked guidance is redacted until its schedule opens.
- `POST /api/nutrition/program/{program_id}/cancel` with `{"confirm": true}` — changes an active plan to `CANCELLED`, stores `cancelled_at`, and preserves all history/progress.

The existing `POST /api/nutrition/program/{program_id}/daily-log` now accepts writes only for an `AVAILABLE` or `IN_PROGRESS` current schedule window. A locked day returns `PROGRAM_DAY_LOCKED`, a missed/closed day returns `PROGRAM_DAY_CLOSED`, a cancelled plan returns `PROGRAM_CANCELLED`, and a completed/finalized day cannot be rewritten.

`GET /api/nutrition/program/{program_id}` and history responses expose the same centralized state used by day detail, including current day, completed days, missed days, program progress, goal progress, inactivity, cancellation, and day availability. Frontend components should not reimplement these calculations.

## Cancelled-program deletion

`DELETE /api/nutrition/program/{program_id}` permanently deletes a program only when it is already `CANCELLED`. Ownership is verified first. Active/completed/foreign programs cannot be deleted through this endpoint. Program-owned days, goals, logs, evaluations, and extension-link records follow database foreign-key cascade behavior; shared profile/recommendation source rows are not deleted by this program-only operation.

## Realtime day availability UI

Day availability remains backend-authoritative. The frontend countdown is presentation only and triggers a fresh no-cache API read immediately after the scheduled boundary. Overview/day-detail screens also schedule a boundary refresh so a day moves from `LOCKED` to today's available state without requiring a manual page reload.

## Final Nutrition result

`GET /api/nutrition/program/{program_id}/result` is authenticated and ownership-scoped. It is available only for a completed/extended block and returns program completion, goal achievement, real program numbers, persisted adaptation history, trends, safety notes, next-step capability and extension-chain summaries.

Existing endpoints remain authoritative for daily logs, progress, block review, rule inspection, extension, pause/resume/skip and cancellation. No duplicate parallel Nutrition API was introduced.
