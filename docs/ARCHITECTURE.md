# SEHATIN Current Architecture

## Product boundary

SEHATIN is **public-first**. Public health journeys do not require authentication. Controlled authentication exists only for saved Guided Nutrition persistence.

```text
Browser (Next.js)
        │
        │ NEXT_PUBLIC_API_URL + HttpOnly session cookie when needed
        ▼
FastAPI
        │
        ├── Public Nutrition
        │      ├── Anthropometric Validation
        │      ├── Rule/Evidence Nutrition Engine
        │      └── Public Result
        │
        ├── Controlled Auth
        │      ├── Register / Login / Logout
        │      └── Opaque server-side sessions
        │
        ├── Guided Nutrition
        │      ├── Saved Profile / Recommendation
        │      ├── Program Days
        │      ├── Daily Checklist / Meal Logs
        │      ├── Progress / Evaluation
        │      └── Ownership Authorization
        │
        ├── Blood Provider Layer
        │      ├── Demo Provider
        │      ├── Database Provider
        │      └── Auto/Fallback Provider
        │
        └── Health Checker
               ├── Evidence Provider
               └── Trust Engine

PostgreSQL ← SQLAlchemy ← Alembic
```

## Nutrition state model

Before Save:

```text
Assessment → API → Result → browser sessionStorage
```

No persistent personal profile is created.

After explicit Save choice:

```text
Result → Auth Gate → Consent → Saved Nutrition Profile
→ Saved Recommendation → Guided Program
```

## Authentication boundary

No public `/login` or `/register` page is used as an entry barrier. Authentication is embedded only in Save/Continue flows.

Raw session token is stored in an HttpOnly cookie. Database stores only its hash and session metadata.

## Anthropometric validation

MPASI/Toddler uses sex-specific WHO Child Growth Standards 2006 reference data for input screening. It is not a diagnostic growth assessment.

Lansia validation uses technical ranges and height/weight/BMI context to detect implausible input. It does not classify health status.

## Ownership

Every program access uses both authentication and ownership verification. A valid user cannot access another user's program by guessing `program_id`.

## Fail-soft behavior

Public demo services can boot without PostgreSQL. Authentication and Guided Nutrition persistence require the database to be available and migrated.

## Blood and Health Checker

They remain public/request-based. Guided Nutrition accounts do not turn Blood searches or Health Checker claims into user history.

## Adaptive Nutrition completion

For MPASI/Toddler the backend owns the adaptive loop: daily log → safety guard → indicator calculator → rule-versioned decision → next-plan generator → second safety guard. React renders server results and temporary drafts; it does not calculate medical/adaptation thresholds.

Final Program Result is an aggregate read model backed by existing Nutrition program/day/log/evaluation/config JSON structures. No new database migration is required for this completion sprint.
