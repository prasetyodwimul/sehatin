# Guided Nutrition Program

## Public flow

```text
Nutrition → Assessment → Server Validation → Recommendation → Result
```

No account is required. Authentication appears only when the user chooses persistent Guided Nutrition.

## Optional persistence flow

```text
Result → Save & Start Guided Program
→ Save notice/consent
→ Login or Register when needed
→ Program created
→ Calendar day → Daily Guidance → Checklist → Save Progress
→ Program Progress + Goal Achievement
→ Evaluation
→ Goal Met OR Adaptive Extension
```

## Authentication UI state

The root `AuthProvider` uses `GET /api/auth/me` and exposes only `loading`, `authenticated`, and `unauthenticated`. Logged-out means `user = null`; SEHATIN does not create a fake Guest account/avatar. The public navbar stays clean. Login/register is contextual to protected actions such as Save & Start Guided Program, Continue Program, Profile, and History.

## Validation

Child input combines age, sex, weight, and length/height. WHO Child Growth Standards 2006 metadata is versioned in backend. Validation returns `VALID`, `WARNING`, or `INVALID` without diagnostic labels.

## Privacy

Only Guided Nutrition data intentionally saved by the authenticated user becomes persistent/account-owned. Public Blood/Health Checker activity is not converted into account history.

## Program progress vs goal achievement

These are deliberately different metrics:

```text
program_progress = completed_program_days / duration_days × 100
goal_progress    = actual_goal_measurement / target × 100
```

Both are capped at 100%, but never share a denominator. A 14-day program with 10 completed days is 71.4% complete; a goal with actual 8 and target 10 is 80% achieved.

Program progress means actual completed program days. It never means “health improved”, “recovered”, or medical success.

## Calendar day, missed days, and inactivity

The backend owns `current_day` from `started_at` and current UTC date. It is not derived from completed task count. Prior calendar days that were not completed become `missed` and cannot be backfilled. Missed days do not increase `days_completed` or program progress.

`last_activity_at` records the latest successful save. `inactive_days` is calculated backend-side and is used only for supportive return messaging such as “Welcome back”; it does not penalize or alter progress.

The planned final calendar date remains writable for the whole day. Completing and saving the final day closes the program even if earlier days were missed. If the user never returns on the final day, the program auto-finalizes on the following calendar date so evaluation can compare actual activity against the target.

## Persistence

PostgreSQL is the source of truth after Save. `GET /api/nutrition/program`, detail, progress, evaluation, history, and extension endpoints rehydrate the journey after navigation, refresh, logout, and login. Checklist edits are local drafts until Save Progress succeeds.

Only the current calendar day is writable. Future days return `PROGRAM_DAY_LOCKED`; prior missed days return `PROGRAM_DAY_CLOSED`. A successful daily-log response is authoritative for completed days, missed days, current day, program progress, goal progress, cumulative extension goal, program status, and timestamps.

## Evaluation and extension

Program completion and goal achievement are separate. A program may be `COMPLETED` while the primary goal is `MET`, `PARTIALLY_MET`, or `NOT_MET`.

Adaptive extension is available only after evaluation when the goal is `PARTIALLY_MET` or `NOT_MET`. The UI shows target, actual, remaining gap, recommended duration, and reasoning before requiring explicit confirmation. Goal `MET` never shows an extension recommendation.

An extension is a new program cycle linked to the original journey. It tracks its own remaining target while `cumulative_goal` preserves the original target and sums actual goal achievement across cycles. Extension does not rewrite or reset Cycle 1 history.
