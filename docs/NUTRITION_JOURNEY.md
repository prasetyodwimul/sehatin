# Nutrition Journey — Goals, History, Evaluation, Extension

## Architecture

SEHATIN Nutrition remains public-first. Assessment, validation, result, recommendation, example menu, guidance, safety notes, evidence, and suggested goals are public. Persistence requires authentication only when the user chooses to save/start a Guided Nutrition Program.

A saved program snapshots the assessment and recommendation used at creation time. PostgreSQL is then the source of truth for goals, program days, checklist state, meal notes, progress, evaluation, history, and extension cycles.

## Goal model

Each program stores measurable behavioral goals. Goals track baseline, target, actual value, unit, measurement method, duration, priority, status, progress percentage, and remaining gap. They intentionally measure adherence to nutrition guidance rather than clinical outcomes.

Primary goal status is derived from saved activity: `NOT_STARTED`, `IN_PROGRESS`, `MET`, `PARTIALLY_MET`, or `NOT_MET`. A calendar-ended program can be evaluated even when the user did not complete every day.

## Concrete daily guidance

Every saved program day contains:

- a daily focus;
- actionable `WHAT TO DO` metadata (why, action, when, how, done-when criterion, related goal);
- concrete meal guidance (occasion, example, food groups, preparation, substitutions/restriction note, safety notes);
- a short checklist tied to that guidance;
- references inherited from the recommendation snapshot.

Meal examples are filtered against allergy/dietary restriction strings stored from the assessment. If no compatible example remains, the UI falls back to a non-specific food-group instruction instead of presenting a conflicting menu.

## History

Authenticated users have `/nutrition/history` and `/nutrition/history/[programId]`. History detail acts as a journey archive: original assessment snapshot, recommendation snapshot, goals, daily guidance, saved progress, evaluation, and extension cycle chain.

Ownership is verified in the backend. A program belonging to another user returns 404.

## Evaluation and adaptive extension

Evaluation compares baseline, target, and actual tracked activity. It does not claim that health improved or that a condition was diagnosed/treated.

When the primary goal is `PARTIALLY_MET` or `NOT_MET`, the backend may recommend an extension. The user must explicitly confirm. The extension creates a new program cycle linked to the original root program, carries forward snapshots/restrictions, uses the remaining behavioral gap, and generates adjusted guidance. Progress is not presented as a medical metric and extension is capped at three total cycles to avoid infinite blind duplication.

## UX/state consistency revision (20260918)

The guided journey now exposes one backend-owned day schedule instead of deriving unlocks from browser dates. Day `N` unlocks at `started_at + (N - 1) × 24 hours`; the API returns `status`, `unlock_at`, `remaining_seconds`, and `completed_at`. This avoids a Day 1 completion near midnight accidentally exposing Day 2 only a few minutes later.

Day status is one of `LOCKED`, `AVAILABLE`, `IN_PROGRESS`, `COMPLETED`, or `MISSED`. Locked-day responses intentionally redact the actual action, checklist, meal guidance, and references until the unlock timestamp. Missed days remain incomplete; they are not silently converted to completed days.

Program progress and goal achievement remain distinct:

- `program progress = completed program days / duration days × 100`
- `goal achievement = actual goal measure / target goal measure × 100`

The program overview is now an overview rather than an inline checklist editor. Each day opens `/nutrition/program/{programId}/day/{dayNumber}`, where the user can review WHY, WHAT TO DO, meal guidance, checklist, goal connection, references, and persistent save state. Save state is `IDLE`, `DIRTY`, `SAVING`, `SAVED`, or `SAVE_ERROR`; after a successful backend commit the CTA becomes `✓ Progress Saved` and the last-saved timestamp remains visible.

Active plans can be cancelled after confirmation. Cancellation preserves existing progress/history, stores `cancelled_at`, changes status to `CANCELLED`, blocks future writes/extensions, and never deletes the journey. History filters include `ALL`, `ACTIVE`, `COMPLETED`, `EXTENDED`, and `CANCELLED`.

Authentication UI has three real states only: loading, unauthenticated, and authenticated. An unauthenticated navbar shows a neutral Account/Login trigger (no fake avatar or “Guest”), with direct Sign in/Create account routes. Authenticated users see their real account identity. The context Save & Start gate still requires explicit persistence consent; its continue button remains disabled until consent is checked, and the create-program backend continues to enforce `consent_to_save`.

## UX consistency follow-up

Program navigation now separates overview, current day, progress anchor, and program-specific history. Day timeline states have distinct visual treatment for TODAY, COMPLETED, MISSED, and LOCKED. Missed-day checklists are explicitly expired/read-only.

Cancellation offers three explicit choices: keep the plan, cancel while preserving history, or cancel and permanently delete. A previously cancelled plan can also be deleted later from history. Permanent deletion is backend-gated to `CANCELLED` programs only.
