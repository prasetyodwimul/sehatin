# Nutrition Adaptive Program — MPASI & Toddler

## Scope

Adaptive rules apply to MPASI and Toddler/Anak. Lansia retains the existing guided-program path unless a separate rule set is defined.

## Authoritative flow

Assessment → safety/validation → phase → one primary goal → block → Day 1 plan → daily log → safety guard → indicators → adaptive decision → next-day plan → safety guard → daily summary → progress → block review → Final Program Result → complete / extend / reframe / refer.

A 14-day block is a guidance cycle, not a goal deadline. Program completion and goal achievement are calculated and displayed independently.

## Plan generation

At program creation the backend stores a detailed Day 1 plus a 14-day schedule shell. For MPASI/Toddler, detailed Day 2+ content is generated only after prior daily data is evaluated. Locked days do not expose future detailed guidance.

## Daily log

The quick log accepts relevant values such as portion, acceptance, texture, new-food attempt, reaction, child condition, caregiver adherence, caregiver difficulty, ingredients/context and notes. The backend is the source of truth for persisted logs.

## Safety

Safety validation is executed before adaptive decision-making and again after next-plan generation. A severe condition blocks automatic adaptation. Safety state is stored with the decision history. The product does not diagnose or prioritize a behavioral goal above safety.

## Indicators

The backend computes descriptive indicators for food acceptance, portion completion, recent trend, goal progress, caregiver burden and safety. Parent-facing UI uses natural language rather than requiring SPH/SPoH/SKG terminology.

## Adaptation engine

Supported decisions are CONTINUE, EASE, REPEAT, ADVANCE, PAUSE, REFER and BLOCK_REVIEW. Each stored decision contains an internal reason, a user-facing reason, indicator snapshot, rule version and next-plan strategy.

Core decisions are rule-based; no ML is used. Thresholds that do not have clinical validation in the repository remain configurable and are labeled `NEEDS_CLINICAL_VALIDATION`.

## Goal vs program progress

Program progress = completed days / block days. Missed days are not counted as completed.

Goal achievement = successful observations for the selected goal / goal target. Completing a block does not manufacture goal success.

## Final Program Result

Authenticated completed blocks expose `/nutrition/program/[programId]/result`. The page aggregates only persisted data: goal, baseline, target, actual, completed/missed/logged days, metric results, adaptive decisions, safety events, trends and extension chain.

The page shows Program Completion and Goal Achievement separately, then summarizes accomplishments, challenges, adaptation history, trends, safety notes and next step. It does not infer a medical diagnosis.

## Extension and reframe

When a completed MPASI/Toddler block is not fully achieved, the existing extension service can create a linked seven-day cycle after explicit caregiver choice. The original block remains unchanged in history. Caregiver choices include continuing the same goal, making it smaller, or changing the goal. SEHATIN does not provide an in-app professional consultation workflow.

## History and auditability

History retains cycle number, goal, program progress, goal progress, metric history, decision history, rule version and extension relationship. Stored automatic decisions preserve the chain Daily Log → Indicators → RuleVersion → Decision/Reason → Plan → Safety Validation.

## Development time acceleration

`NUTRITION_DAY_SCHEDULE=midnight` is the default daily schedule: each MPASI, Toddler, and Lansia progress window closes at 00:00 in `NUTRITION_TIMEZONE` (default `Asia/Jakarta`), and the next day opens at that midnight boundary. `NUTRITION_DAY_INTERVAL_SECONDS` remains available only when `NUTRITION_DAY_SCHEDULE=interval` for accelerated local testing. The backend remains the source of unlock/lock timestamps and remaining time.
