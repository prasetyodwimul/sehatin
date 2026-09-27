# SEHATIN Demo Guide — Guided Nutrition Sprint

## Startup

Backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
alembic upgrade head
python -m uvicorn app.main:app --reload --port 8000
```

Frontend:

```powershell
cd frontend
npm run dev
```

## Scenario 1 — Public Nutrition without login

1. Home → Nutrition → MPASI/Toddler/Lansia.
2. Fill age, sex, weight, length/height plus relevant eating context.
3. Show real-time `VALID` / `WARNING` / `INVALID` validation from backend.
4. Submit and open dedicated result page.
5. Explain estimated needs, recommendations, menu, safety, and evidence.
6. Emphasize: no account was required.

## Scenario 2 — Save & Start Guided Program

1. From Nutrition result click **Save & Start Guided Program**.
2. Show the Authentication Gate only at this point.
3. Explain privacy notice: data becomes persistent only after this explicit choice.
4. Login or Create Account.
5. Create Guided Program.
6. Show Today's Guidance, checklist, meal note, and current progress.
7. Complete checklist and save.
8. Show progress changing from real completed activity.
9. Open Program Progress/Evaluation and explain it is adherence/activity, not health diagnosis.
10. Complete the final day and show `COMPLETED`, then open Profile → Program History.

## Security talking point

- Password is stored as `scrypt` hash, never plaintext.
- Raw session token is not stored in browser JS storage; it is an HttpOnly cookie.
- User A cannot access User B program; ownership is checked on every protected request.

## Validation talking point

- Child input is evaluated with age + sex + weight + length/height.
- WHO 2006 reference data is used as a screening reference.
- The app says “outside the reference used by the system”, not “abnormal” or a diagnosis.
- Lansia BMI is context only.

## Scenario 3 — Blood Connect

Blood remains public and simulated. Show facility, quantity, status, source and `SIMULATED DEMO DATA` label.

## Scenario 4 — Health Checker

Health Checker remains public. Show one of each verdict type and explain Trust Score vs Evidence Confidence.

## Honest limitations

- Guided Nutrition is educational behavior guidance, not clinical care.
- WHO growth integration is a screening reference layer, not a diagnostic growth-chart service.
- No password reset/email verification in this sprint.
- Blood is simulated.
- Health Checker evidence retrieval is curated/demo rather than a live systematic review engine.

## Adaptive Nutrition competition journey

Recommended local demo: set `NUTRITION_DAY_INTERVAL_SECONDS=60`, restart backend, create a new MPASI/Toddler program, complete Day 1 quick log, show the stored adaptive reason and tomorrow preview, wait for backend unlock, continue through an adaptive branch, then demonstrate Block Review / Final Program Result using a completed fixture or accelerated cycle.

Blood inventory in demo mode must remain clearly marked as simulated/demonstration data rather than official live availability.
