# Database

Canonical database: **PostgreSQL + SQLAlchemy + Psycopg 3 + Alembic**.

## Public-system tables

```text
nutrition_requests
nutrition_recommendations
blood_facilities
blood_inventory
blood_requests
health_claims
evidence_sources
evidence_documents
claim_evidence
system_logs
```

Blood and Health Checker public records are not required to be user-owned.

## Controlled persistence tables

```text
users
auth_sessions
nutrition_profiles
nutrition_programs
nutrition_program_days
nutrition_meal_logs
nutrition_evaluations
```

### users
Contains only account identity/security fields such as `id`, `email`, `password_hash`, `created_at`. Health data is not stored directly in this table.

### auth_sessions
Stores only hash of opaque session token plus user ownership, expiry and revocation timestamps. Raw token remains in HttpOnly cookie.

### nutrition_profiles
Saved only after explicit user consent. Contains the Nutrition assessment data required to continue Guided Program.

### nutrition_recommendations
Public request recommendations can remain anonymous. Saved Guided Program recommendations may optionally reference `user_id` + `profile_id`.

### nutrition_programs
Owned by one user. Every protected API verifies `program.user_id == authenticated_user.id`.

### nutrition_program_days / meal_logs / evaluations
Store actual program activity. Progress is derived from real checklist completion, not fabricated percentages.

## Migrations

```text
20260915_0001_core_schema.py
20260916_0002_guided_nutrition_auth.py
20260917_0003_program_progress_fix.py
20260917_0004_nutrition_goals_history_extension.py
20260917_0005_program_time_activity.py
20260918_0006_program_cancel_state.py
```

`0002` is additive: it preserves existing core tables, adds controlled auth/program tables, adds `height_cm` to Nutrition request storage, and adds optional saved-owner/profile references to recommendations.

`0003` is also additive and upgrade-safe: it adds nullable `nutrition_programs.completed_at` and normalizes existing program status strings to uppercase (`ACTIVE` / `COMPLETED`). Sequential locking and progress remain derived from persisted program-day checklist state rather than adding duplicated progress columns.

Run:

```powershell
alembic upgrade head
```

The migration chain supports a blank database, upgrade from `0001`, and upgrade from an existing `0002` Guided Nutrition database without rewriting earlier migrations.

## Revision 20260917_0004 — goal/history/extension layer

Additive migration `20260917_0004_nutrition_goals_history_extension.py` adds:

- `nutrition_program_goals` for measurable behavioral goals;
- `nutrition_program_extensions` for confirmed extension relationships and remaining-gap snapshots;
- `nutrition_programs.parent_program_id`, `cycle_number`, `assessment_snapshot`, `recommendation_snapshot`, and `program_config`;
- `nutrition_program_days.action_details` and `meal_guidance_details`.

No previous migration is edited. Existing program rows remain valid; missing snapshots are reconstructed from existing profile/recommendation records when read.


## Revision 20260917_0005 — calendar/inactivity state

Additive migration `20260917_0005_program_time_activity.py` adds nullable `nutrition_programs.last_activity_at`. It supports backend-owned inactivity detection without storing browser-only state. `current_day`, `missed_days`, program progress, goal progress, and cumulative extension progress are derived from persisted program/day/goal records rather than duplicated percentage columns.

## Revision 20260918_0006 — cancellation state

Additive migration `20260918_0006_program_cancel_state.py` adds nullable `nutrition_programs.cancelled_at`.

Cancellation is soft state, not deletion: existing goals, day activity, meal logs, evaluation, recommendation snapshot, and assessment snapshot remain available in Nutrition History. Day availability, missed-day counts, countdowns, current day, program progress, and goal progress continue to be derived by the backend rather than duplicated as database percentage/status columns.

## Final Nutrition result storage

No migration is introduced by the final completion sprint. Final result is derived from existing `nutrition_programs`, `nutrition_program_goals`, `nutrition_program_days`, `nutrition_meal_logs`, `nutrition_evaluations`, `nutrition_program_extensions` and JSON program/day metadata. Historical adaptive decisions retain their stored rule-version identifier rather than being recalculated against a newer rule.
