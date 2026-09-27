# Concept Compliance — Guided Nutrition Sprint

## Product decision

SEHATIN remains **public-first**. Controlled authentication exists only for persistent Nutrition experiences.

| Requirement | Status | Notes |
|---|---|---|
| Public Homepage/Blood/Health Checker | ✅ | No login barrier |
| Public Nutrition assessment/result | ✅ | No login required |
| Save gate only after result | ✅ | Explicit user action |
| Register/Login/Logout | ✅ | Gate-based, no login landing page |
| Password hashing | ✅ | scrypt + salt + env pepper |
| Session security | ✅ | Opaque HttpOnly cookie + expiry/revoke |
| Program ownership | ✅ | Foreign program returns 404 |
| Explicit health-data save consent | ✅ | Required before program creation |
| MPASI/Toddler anthropometric validation | ✅ | WHO 2006 versioned reference subset |
| Lansia technical/body-size validation | ✅ | BMI context only, no diagnosis |
| Guided Program | ✅ | Daily guidance + checklist |
| Progress | ✅ | Derived from actual completed tasks |
| Evaluation | ✅ | Activity adherence only |
| Sequential Program Completion | ✅ | Future days locked; final day becomes COMPLETED |
| No medical diagnosis | ✅ | Educational wording + safety boundary |
| Blood/Health persistence linked to account | ❌ intentionally absent | Public request-based design preserved |

## Remaining limitations

- WHO child reference implementation is a screening subset/interpolation layer, not a clinical growth-chart engine and not a substitute for professional anthropometric assessment.
- Password reset, email verification, and session-device management are not in this sprint.
- Production requires HTTPS + secure cookie + strong environment secret.

## 2026 final completion delta

Implemented: dedicated data-backed Final Program Result; program/goal progress separation; history link to completed result; linked extension review; neutral logged-out Account UI; backend-owned unlock countdown; explicit saved/unsaved semantics; public-domain homepage visual sources; rule-versioned adaptive audit trail.

Not claimed as fully verified in the Linux packaging environment: Windows Vitest/build, interactive browser matrix, device-level responsive screenshots, network-performance profiling, and full manual multi-browser E2E. These remain release-gate checks on the target Windows environment.
