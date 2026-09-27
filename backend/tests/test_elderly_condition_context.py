from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.main import app
from app.models import Base, NutritionProgramDayModel, NutritionProgramModel
from app.services.auth_service import create_session, create_user


@pytest.fixture()
def elderly_db(tmp_path):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'elderly-condition.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    try:
        yield factory
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def _elderly(**overrides) -> dict:
    payload = {
        "stage": "elderly",
        "age_years": 70,
        "sex": "female",
        "weight_kg": 55.0,
        "height_cm": 155.0,
        "meal_frequency": 3,
        "activity_level": "moderate",
    }
    payload.update(overrides)
    return payload


def _login(client: TestClient, factory, email: str) -> None:
    with factory() as db:
        user = create_user(db, email=email, password="SehatinPass123")
        token, _ = create_session(db, user)
        db.commit()
    client.cookies.set("sehatin_session", token)


def test_elderly_without_condition_keeps_existing_general_flow(elderly_db):
    client = TestClient(app)
    response = client.post("/api/nutrition/recommendation", json=_elderly(has_condition=False))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["health_context"]["has_condition"] is False
    assert body["health_context"]["condition_labels"] == []
    assert body["personalization_status"] == "personalized_education"
    assert not any("Kondisi kesehatan yang dilaporkan" in item for item in body["input_summary"])


def test_elderly_condition_validation_requires_selection_and_other_name(elderly_db):
    client = TestClient(app)
    no_selection = client.post("/api/nutrition/recommendation", json=_elderly(has_condition=True, conditions=[]))
    assert no_selection.status_code == 422

    other_missing = client.post(
        "/api/nutrition/recommendation",
        json=_elderly(has_condition=True, conditions=["other"]),
    )
    assert other_missing.status_code == 422


def test_diabetes_and_hypertension_are_both_used_as_context(elderly_db):
    client = TestClient(app)
    response = client.post(
        "/api/nutrition/recommendation",
        json=_elderly(has_condition=True, conditions=["diabetes", "hypertension"]),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    context = body["health_context"]
    assert context["condition_labels"] == ["Diabetes", "Hipertensi"]
    assert any("Keteraturan waktu makan" == item for item in context["nutrition_focus"])
    assert any("garam" in item.lower() or "natrium" in item.lower() for item in context["nutrition_focus"])
    assert body["personalization_status"] == "personalized_education"
    assert "Diabetes, Hipertensi" in body["summary"]
    assert any("Kondisi kesehatan yang dilaporkan: Diabetes, Hipertensi" == item for item in body["input_summary"])
    goal = body["suggested_goals"][0]
    assert goal["title"] == "Pertahankan pola makan seimbang yang konsisten"
    assert "Diabetes" in goal["description"] and "Hipertensi" in goal["description"]
    assert goal["baseline_label"] == "3 kali makan utama/hari pada assessment"
    assert "14 hari" in goal["target_label"]
    assert "log harian" in goal["measurement_method"].lower()


def test_other_condition_is_preserved_without_diagnosis_inference(elderly_db):
    client = TestClient(app)
    response = client.post(
        "/api/nutrition/recommendation",
        json=_elderly(has_condition=True, conditions=["diabetes", "other"], other_condition="Osteoporosis"),
    )
    assert response.status_code == 200, response.text
    context = response.json()["health_context"]
    assert context["conditions"] == ["diabetes", "other"]
    assert context["other_condition"] == "Osteoporosis"
    assert context["condition_labels"] == ["Diabetes", "Osteoporosis"]
    assert context["needs_clinical_consultation"] is True
    assert "dilaporkan user" in context["source_note"]


def test_kidney_context_does_not_create_automatic_renal_restrictions(elderly_db):
    client = TestClient(app)
    response = client.post(
        "/api/nutrition/recommendation",
        json=_elderly(has_condition=True, conditions=["kidney_disease"]),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "protein_berdasarkan_berat" not in body["estimated_needs"]
    assert body["health_context"]["needs_clinical_consultation"] is True
    assert not any("batasi kalium" in item.lower() or "batasi fosfor" in item.lower() or "batasi protein" in item.lower() for item in body["recommendations"])
    assert any("tidak menetapkan pembatasan spesifik otomatis" in item.lower() for item in body["recommendations"])


def test_guided_program_carries_condition_context_into_day_without_auto_pause(elderly_db):
    client = TestClient(app)
    _login(client, elderly_db, "elderly-context@example.com")
    assessment = _elderly(has_condition=True, conditions=["diabetes", "hypertension"])
    created = client.post(
        "/api/nutrition/program",
        json={"assessment": assessment, "consent_to_save": True, "duration_days": 14},
    )
    assert created.status_code == 201, created.text
    program_id = created.json()["id"]

    detail = client.get(f"/api/nutrition/program/{program_id}")
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["status"] == "ACTIVE"
    assert body["assessment_snapshot"]["conditions"] == ["diabetes", "hypertension"]
    assert body["days"][0]["status"] in {"AVAILABLE", "IN_PROGRESS"}
    assert body["days"][1]["status"] == "LOCKED"
    day1 = body["days"][0]
    assert day1["action_details"]["health_context"]["has_condition"] is True
    assert any("karbohidrat" in item.lower() or "garam" in item.lower() for item in day1["checklist"])


def test_chronic_condition_context_survives_pause_and_resume(elderly_db):
    client = TestClient(app)
    _login(client, elderly_db, "elderly-pause-context@example.com")
    assessment = _elderly(has_condition=True, conditions=["diabetes"])
    created = client.post(
        "/api/nutrition/program",
        json={"assessment": assessment, "consent_to_save": True, "duration_days": 14},
    )
    assert created.status_code == 201, created.text
    program_id = created.json()["id"]
    day = client.get(f"/api/nutrition/program/{program_id}/days/1").json()["day"]
    checks = [True] + [False] * max(0, len(day["checklist"]) - 1)

    paused = client.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={"day_number": 1, "checklist_state": checks, "health_condition": "unwell", "has_complaint": None},
    )
    assert paused.status_code == 200, paused.text
    assert paused.json()["program_status"] == "PAUSED"

    during_pause = client.get(f"/api/nutrition/program/{program_id}").json()
    assert during_pause["assessment_snapshot"]["conditions"] == ["diabetes"]
    assert during_pause["current_day"] == 1
    assert during_pause["days"][1]["status"] == "LOCKED"

    resumed = client.post(
        f"/api/nutrition/program/{program_id}/resume",
        json={"confirm": True, "recovery_status": "improved"},
    )
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["status"] == "ACTIVE"
    after = client.get(f"/api/nutrition/program/{program_id}").json()
    assert after["assessment_snapshot"]["conditions"] == ["diabetes"]
    assert after["current_day"] == 1
    assert after["days"][0]["checklist_state"] == checks


def test_elderly_expanded_daily_conditions_separate_observation_from_pause(elderly_db):
    client = TestClient(app)
    _login(client, elderly_db, "elderly-expanded-condition@example.com")
    created = client.post(
        "/api/nutrition/program",
        json={"assessment": _elderly(has_condition=True, conditions=["diabetes"]), "consent_to_save": True, "duration_days": 14},
    )
    assert created.status_code == 201, created.text
    program_id = created.json()["id"]
    day = client.get(f"/api/nutrition/program/{program_id}/days/1").json()["day"]
    checks = [False] * len(day["checklist"])

    observed = client.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={
            "day_number": 1,
            "checklist_state": checks,
            "health_condition": "reduced_appetite",
            "appetite_status": "reduced",
            "eating_difficulty": "some",
            "routine_adherence": "partial",
            "has_complaint": False,
        },
    )
    assert observed.status_code == 200, observed.text
    assert observed.json()["program_status"] == "ACTIVE"


def test_elderly_daily_input_generates_adaptive_next_day_plan(elderly_db):
    client = TestClient(app)
    _login(client, elderly_db, "elderly-daily-adaptive@example.com")
    created = client.post(
        "/api/nutrition/program",
        json={"assessment": _elderly(has_condition=True, conditions=["diabetes", "hypertension"]), "consent_to_save": True, "duration_days": 14},
    )
    assert created.status_code == 201, created.text
    program_id = created.json()["id"]
    day = client.get(f"/api/nutrition/program/{program_id}/days/1").json()["day"]

    saved = client.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={
            "day_number": 1,
            "checklist_state": [True] * len(day["checklist"]),
            "has_complaint": False,
            "health_condition": "well",
            "appetite_status": "good",
            "eating_difficulty": "none",
            "routine_adherence": "yes",
        },
    )
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["day_completed"] is True
    assert body["adaptation"]["decision"] == "CONTINUE"
    assert body["next_day_plan"]["day_number"] == 2
    assert body["next_day_plan"]["strategy"] == "CONTINUE"
    assert body["daily_summary"]["adaptation_decision"] == "CONTINUE"

    detail = client.get(f"/api/nutrition/program/{program_id}").json()
    assert detail["adaptive_mode"] is True
    with elderly_db() as db:
        day2 = db.query(NutritionProgramDayModel).filter(
            NutritionProgramDayModel.program_id == program_id,
            NutritionProgramDayModel.day_number == 2,
        ).one()
        assert day2.action_details["adaptive_mode"] is True
        assert day2.action_details["generated_from_day"] == 1
        assert day2.action_details["health_context"]["condition_labels"] == ["Diabetes", "Hipertensi"]


def test_elderly_adaptive_decision_eases_when_daily_pattern_is_hard():
    from app.nutrition.adaptive_program import decide_elderly_adaptation

    result = decide_elderly_adaptation(
        safety={"blocked": False},
        indicators={
            "history_days_available": 2,
            "recent_adherence_average": 45.0,
            "appetite_average": 0.25,
            "routine_average": 0.5,
            "difficulty_average": 0.75,
        },
        current_log={"appetite_status": "poor", "eating_difficulty": "difficult", "routine_adherence": "partial"},
        recent_logs=[{"appetite_status": "poor", "eating_difficulty": "difficult", "routine_adherence": "partial"}],
        day_number=3,
    )
    assert result["decision"] == "EASE"
    assert result["explanation"]["what_next"]


def test_elderly_adaptive_decision_can_advance_after_stable_daily_pattern():
    from app.nutrition.adaptive_program import decide_elderly_adaptation

    result = decide_elderly_adaptation(
        safety={"blocked": False},
        indicators={
            "history_days_available": 3,
            "recent_adherence_average": 90.0,
            "appetite_average": 1.0,
            "routine_average": 1.0,
            "difficulty_average": 0.0,
        },
        current_log={"appetite_status": "good", "eating_difficulty": "none", "routine_adherence": "yes"},
        recent_logs=[
            {"appetite_status": "good", "eating_difficulty": "none", "routine_adherence": "yes"},
            {"appetite_status": "good", "eating_difficulty": "none", "routine_adherence": "yes"},
        ],
        day_number=4,
        previous_decision="CONTINUE",
    )
    assert result["decision"] == "ADVANCE"
    assert "satu" in result["user_facing_reason"].lower()


def test_swallowing_difficulty_can_start_general_guided_program_without_reassessment_loop(elderly_db):
    client = TestClient(app)
    _login(client, elderly_db, "elderly-swallow-guided@example.com")
    assessment = _elderly(
        swallowing_difficulty=True,
        has_condition=True,
        conditions=["diabetes"],
    )

    recommendation = client.post("/api/nutrition/recommendation", json=assessment)
    assert recommendation.status_code == 200, recommendation.text
    assert recommendation.json()["personalization_status"] == "limited_for_safety"

    created = client.post(
        "/api/nutrition/program",
        json={"assessment": assessment, "consent_to_save": True, "duration_days": 14},
    )
    assert created.status_code == 201, created.text
    program_id = created.json()["id"]

    detail = client.get(f"/api/nutrition/program/{program_id}")
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["status"] == "ACTIVE"
    assert body["assessment_snapshot"]["swallowing_difficulty"] is True

    day1 = body["days"][0]
    combined = " ".join([
        str(day1.get("recommended_action") or ""),
        str(day1.get("meal_guidance") or ""),
        " ".join(day1.get("checklist") or []),
    ]).lower()
    assert "pilih tekstur yang mudah dikunyah" not in combined
    assert "diketahui aman" in combined
    assert "sumber energi" in combined or "protein" in combined
    assert "tidak ada contoh menu" not in combined
    assert recommendation.json()["sample_menu"]
    assert any("diketahui aman" in item.lower() for item in recommendation.json()["sample_menu"])
    assert any("IDDSI" in ref for ref in recommendation.json()["references"])

    with elderly_db() as db:
        program = db.get(NutritionProgramModel, program_id)
        assert program is not None
        assert program.program_config["guided_safety_mode"] == "swallowing_general_only"


def test_other_medical_safety_context_still_blocks_guided_program(elderly_db):
    client = TestClient(app)
    _login(client, elderly_db, "elderly-medical-block@example.com")
    assessment = _elderly(
        swallowing_difficulty=True,
        medical_context="kondisi medis yang memerlukan diet terapi",
    )
    created = client.post(
        "/api/nutrition/program",
        json={"assessment": assessment, "consent_to_save": True, "duration_days": 14},
    )
    assert created.status_code == 409, created.text


def test_elderly_task_set_changes_with_adaptive_strategy():
    from app.services.nutrition_program_service import _elderly_daily_tasks

    recommendation = {
        "health_context": {
            "has_condition": True,
            "daily_actions": [
                "Jaga keteraturan pola makan yang realistis.",
                "Perhatikan kualitas pilihan karbohidrat tanpa membuat diet medis khusus.",
            ],
        }
    }
    profile = {"meal_frequency": 3}

    continue_tasks = _elderly_daily_tasks(profile, recommendation, 2, primary_action="Pertahankan pola", strategy="CONTINUE")
    ease_tasks = _elderly_daily_tasks(profile, recommendation, 3, primary_action="Pertahankan pola", strategy="EASE")
    advance_tasks = _elderly_daily_tasks(profile, recommendation, 4, primary_action="Pertahankan pola", strategy="ADVANCE")

    assert len(continue_tasks) == 3
    assert {task["input_type"] for task in continue_tasks} >= {"choice", "simple_experience"}
    assert len(ease_tasks) == 2
    assert any("satu langkah utama" in task["target_label"].lower() for task in ease_tasks)
    assert len(advance_tasks) == 5
    assert any(task["metric"] == "elderly_small_step" for task in advance_tasks)
    assert [task["action_text"] for task in continue_tasks] != [task["action_text"] for task in ease_tasks]


def test_elderly_completed_block_can_extend_when_daily_adherence_is_still_low(elderly_db):
    from app.models.base import utcnow

    client = TestClient(app)
    _login(client, elderly_db, "elderly-extension-adherence@example.com")
    created = client.post(
        "/api/nutrition/program",
        json={"assessment": _elderly(has_condition=True, conditions=["diabetes"]), "consent_to_save": True, "duration_days": 14},
    )
    assert created.status_code == 201, created.text
    program_id = created.json()["id"]

    with elderly_db() as db:
        program = db.get(NutritionProgramModel, program_id)
        days = db.query(NutritionProgramDayModel).filter(
            NutritionProgramDayModel.program_id == program_id
        ).order_by(NutritionProgramDayModel.day_number).all()
        now = utcnow()
        for day in days:
            tasks = list((day.action_details or {}).get("tasks") or [])
            details = dict(day.action_details or {})
            metric_results = []
            task_results = {}
            for task in tasks:
                task_id = str(task.get("key") or task.get("id"))
                input_type = str(task.get("input_type") or "boolean")
                if input_type == "count":
                    actual = 1
                    adherence = 35.0
                elif input_type in {"choice", "rating", "observation"}:
                    actual = "partial" if any(option.get("value") == "partial" for option in task.get("options", [])) else (task.get("options") or [{"value": "some"}])[-1]["value"]
                    adherence = 40.0 if task.get("adherence_map") else None
                elif input_type == "simple_experience":
                    actual = "manageable"
                    adherence = None
                else:
                    actual = False
                    adherence = 0.0
                task_results[task_id] = actual
                metric_results.append({
                    "task_id": task_id,
                    "metric_id": str(task.get("metric_id") or task.get("metric") or "unknown"),
                    "target": task.get("target_value"),
                    "actual_result": actual,
                    "unit": task.get("unit"),
                    "input_type": input_type,
                    "status": "PARTIAL" if adherence is not None and adherence < 100 else "COMPLETED",
                    "adherence": adherence,
                    "completed_at": None,
                    "action_completed": True,
                    "evidence_rule_id": None,
                })
            details["task_results"] = task_results
            details["metric_results"] = metric_results
            details["daily_log"] = {
                "health_condition": "well",
                "appetite_status": "good",
                "hydration_status": "poor",
                "eating_difficulty": "none",
                "eating_support": "independent",
                "eating_barrier": "none",
            }
            details["last_saved_at"] = now.isoformat()
            day.action_details = details
            day.checklist_state = [True] * len(day.checklist or [])
            day.has_complaint = False
            day.completed = True
            day.completed_at = now
        program.status = "COMPLETED"
        program.completed_at = now
        db.commit()

    result = client.get(f"/api/nutrition/program/{program_id}/result")
    assert result.status_code == 200, result.text
    assert result.json()["next_step"]["can_extend"] is True

    info = client.get(f"/api/nutrition/program/{program_id}/extension-recommendation")
    assert info.status_code == 200, info.text
    assert info.json()["recommended_days"] in {7, 14}
    assert info.json()["remaining_gap"] > 0
    assert info.json()["guidance_adjustments"]["recommended_goal_key"] == "elderly_hydration_routine"
    assert "minum" in info.json()["guidance_adjustments"]["focus"].lower()

    final_result = client.get(f"/api/nutrition/program/{program_id}/result").json()
    assert final_result["next_step"]["suggested_goal_key"] == "elderly_hydration_routine"
    assert "minum" in final_result["next_step"]["suggested_focus"].lower()

    extended = client.post(f"/api/nutrition/program/{program_id}/extend", json={"confirm": True})
    assert extended.status_code == 201, extended.text
    assert extended.json()["stage"] == "elderly"
    assert extended.json()["cycle_number"] == 2
    assert extended.json()["goal"]["goal_key"] == "elderly_hydration_routine"


def test_elderly_program_name_and_selected_goal_drive_first_day(elderly_db):
    client = TestClient(app)
    _login(client, elderly_db, "elderly-named-goal@example.com")
    created = client.post(
        "/api/nutrition/program",
        json={
            "assessment": _elderly(hydration_pattern="often_low"),
            "consent_to_save": True,
            "duration_days": 14,
            "goal_key": "elderly_hydration_routine",
            "display_name": "Program Minum Ibu",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["title"] == "Program Minum Ibu"
    assert body["goal"]["goal_key"] == "elderly_hydration_routine"
    detail = client.get(f"/api/nutrition/program/{body['id']}").json()
    first_tasks = detail["days"][0]["action_details"]["tasks"]
    assert first_tasks[0]["metric"] == "elderly_hydration_routine"
    assert "minum" in first_tasks[0]["action"].lower()


def test_elderly_repeated_daily_barrier_can_ease_next_plan():
    from app.nutrition.adaptive_program import calculate_elderly_indicators, decide_elderly_adaptation

    previous = {
        "health_condition": "well",
        "appetite_status": "good",
        "hydration_status": "good",
        "eating_difficulty": "none",
        "eating_support": "independent",
        "eating_barrier": "preparation",
    }
    current = dict(previous)
    indicators = calculate_elderly_indicators(
        current, [previous], goal_metric="elderly_balanced_meal_routine",
        task_adherence={"task-a": 100.0}, recent_adherence_history=[100.0],
    )
    assert indicators["barrier_count"] == 2
    decision = decide_elderly_adaptation(
        safety={"state": "ACTIVE", "reason": None}, indicators=indicators, current_log=current,
        recent_logs=[previous], day_number=4, previous_decision="CONTINUE", block_days=14,
    )
    assert decision["decision"] == "EASE"
    assert "sulit" in decision["user_facing_reason"].lower() or "hambatan" in decision["user_facing_reason"].lower()


def test_elderly_hard_day_rewrites_next_day_tasks_instead_of_repeating_generic_checklist(elderly_db):
    client = TestClient(app)
    _login(client, elderly_db, "elderly-ease-plan@example.com")
    created = client.post(
        "/api/nutrition/program",
        json={"assessment": _elderly(has_condition=True, conditions=["hypertension"]), "consent_to_save": True, "duration_days": 14},
    )
    assert created.status_code == 201, created.text
    program_id = created.json()["id"]
    day1 = client.get(f"/api/nutrition/program/{program_id}/days/1").json()["day"]
    tasks = day1["action_details"]["tasks"]
    assert len(tasks) == 3
    results = {}
    for task in tasks:
        if task["input_type"] == "count":
            results[task["key"]] = 0
        elif task["input_type"] == "simple_experience":
            results[task["key"]] = "difficult"
        elif task["input_type"] == "choice":
            results[task["key"]] = "not_done" if any(o["value"] == "not_done" for o in task.get("options", [])) else task["options"][-1]["value"]
        else:
            results[task["key"]] = False

    saved = client.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={
            "day_number": 1,
            "checklist_state": [True] * len(day1["checklist"]),
            "task_results": results,
            "has_complaint": False,
            "health_condition": "well",
            "appetite_status": "poor",
            "eating_difficulty": "difficult",
            "routine_adherence": "no",
        },
    )
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["adaptation"]["decision"] == "EASE"
    assert body["next_day_plan"]["strategy"] == "EASE"

    with elderly_db() as db:
        day2 = db.query(NutritionProgramDayModel).filter(
            NutritionProgramDayModel.program_id == program_id,
            NutritionProgramDayModel.day_number == 2,
        ).one()
        day2_tasks = list(day2.action_details.get("tasks") or [])
        assert len(day2_tasks) == 2
        assert day2.action_details["adaptation_context"]["strategy"] == "EASE"
        assert [task["action_text"] for task in day2_tasks] != [task["action_text"] for task in tasks]


def test_existing_unfinished_elderly_legacy_day_is_upgraded_without_resetting_completed_history(elderly_db):
    client = TestClient(app)
    _login(client, elderly_db, "elderly-legacy-upgrade@example.com")
    created = client.post(
        "/api/nutrition/program",
        json={"assessment": _elderly(has_condition=True, conditions=["diabetes"]), "consent_to_save": True, "duration_days": 14},
    )
    assert created.status_code == 201, created.text
    program_id = created.json()["id"]

    with elderly_db() as db:
        day1 = db.query(NutritionProgramDayModel).filter(
            NutritionProgramDayModel.program_id == program_id,
            NutritionProgramDayModel.day_number == 1,
        ).one()
        day1.action_details = {"tasks": [], "adaptive_mode": True, "planned": True, "adaptation_context": {"strategy": "CONTINUE"}}
        day1.checklist = [
            "Ikuti tindakan utama hari ini",
            "Terapkan panduan makan pada waktu makan yang sesuai",
            "Catat apakah panduan dapat diterapkan hari ini",
        ]
        day1.checklist_state = [False, False, False]
        db.commit()

    response = client.get(f"/api/nutrition/program/{program_id}/days/1")
    assert response.status_code == 200, response.text
    day = response.json()["day"]
    tasks = day["action_details"]["tasks"]
    assert len(tasks) == 3
    assert all(task["metric"] != "legacy" for task in tasks)
    assert {task["input_type"] for task in tasks} >= {"choice", "simple_experience"}
    assert day["checklist"] != [
        "Ikuti tindakan utama hari ini",
        "Terapkan panduan makan pada waktu makan yang sesuai",
        "Catat apakah panduan dapat diterapkan hari ini",
    ]



def test_elderly_lifestyle_context_is_preserved_without_medical_targeting(elderly_db):
    client = TestClient(app)
    response = client.post(
        "/api/nutrition/recommendation",
        json=_elderly(
            has_condition=True,
            conditions=["hypertension"],
            hydration_pattern="sometimes_low",
            eating_independence="needs_reminder",
            caregiver_support="sometimes",
        ),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    context = body["elderly_context"]
    assert context["hydration_pattern"] == "sometimes_low"
    assert context["eating_independence"] == "needs_reminder"
    assert context["caregiver_support"] == "sometimes"
    assert any("kebiasaan minum" in item.lower() for item in context["focus"])
    assert not any("liter" in item.lower() for item in context["focus"] + context["notes"])
    assert any("Kebiasaan minum:" in item for item in body["input_summary"])
    goal = body["suggested_goals"][0]
    assert goal["goal_key"] == "elderly_hydration_routine"
    assert goal["title"] == "Bangun kebiasaan minum yang lebih teratur"
    assert "Kadang minum lebih sedikit" in goal["baseline_label"]


def test_elderly_daily_hydration_and_support_are_saved_and_affect_adaptation(elderly_db):
    client = TestClient(app)
    _login(client, elderly_db, "elderly-hydration-adaptive@example.com")
    created = client.post(
        "/api/nutrition/program",
        json={"assessment": _elderly(hydration_pattern="often_low", eating_independence="needs_assistance", caregiver_support="daily"), "consent_to_save": True, "duration_days": 14},
    )
    assert created.status_code == 201, created.text
    program_id = created.json()["id"]
    day = client.get(f"/api/nutrition/program/{program_id}/days/1").json()["day"]
    tasks = day["action_details"]["tasks"]
    results = {}
    for task in tasks:
        if task["input_type"] == "count":
            results[task["key"]] = task.get("target_value") or 1
        elif task["input_type"] == "simple_experience":
            results[task["key"]] = "manageable"
        elif task["input_type"] == "choice":
            values = [option["value"] for option in task.get("options", [])]
            results[task["key"]] = values[0]
        else:
            results[task["key"]] = True

    saved = client.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={
            "day_number": 1,
            "checklist_state": [True] * len(day["checklist"]),
            "task_results": results,
            "has_complaint": False,
            "health_condition": "well",
            "appetite_status": "good",
            "hydration_status": "poor",
            "eating_difficulty": "none",
            "eating_support": "assisted",
            "routine_adherence": "yes",
        },
    )
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["indicators"]["hydration_average"] == 0.0
    assert body["indicators"]["support_need_average"] == 1.0
    assert body["adaptation"]["decision"] == "EASE"

    detail = client.get(f"/api/nutrition/program/{program_id}").json()
    stored = detail["days"][0]["action_details"]["daily_log"]
    assert stored["hydration_status"] == "poor"
    assert stored["eating_support"] == "assisted"
