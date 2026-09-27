from app.nutrition.program_evidence import (
    RULE_VERSION,
    adaptation_for_days,
    adherence_for_task,
    behavioral_status,
    build_personalized_tasks,
    mpasi_band,
    mpasi_meal_target,
    preferred_mpasi_metric,
    preferred_toddler_metric,
    target_for_metric,
    task_result_status,
)
from app.schemas.nutrition import NutritionRequest


def test_age_bands_and_meal_targets_are_explicit():
    assert mpasi_band(6) == "6–8"
    assert mpasi_band(9) == "9–11"
    assert mpasi_band(23) == "12–23"
    assert mpasi_meal_target(8, "breastmilk") == 2
    assert mpasi_meal_target(12, "breastmilk") == 3
    assert mpasi_meal_target(8, "mixed") == 2
    assert mpasi_meal_target(12, "mixed") == 3
    assert mpasi_meal_target(8, "formula") == 3
    assert mpasi_meal_target(12, "formula") == 4
    assert NutritionRequest(stage="toddler", age_months=24, sex="female", weight_kg=12, height_cm=88)
    assert NutritionRequest(stage="toddler", age_months=59, sex="female", weight_kg=18, height_cm=105)


def test_personalized_metric_selection_uses_profile_gaps():
    mpasi = {
        "age_months": 8,
        "feeding_mode": "breastmilk",
        "meal_frequency": 1,
        "animal_source_food_days": 7,
        "fruit_vegetable_days": 7,
        "recent_food_group_count": 5,
        "responsive_feeding": "usually",
    }
    assert preferred_mpasi_metric(mpasi) == "meal_frequency"

    toddler = {
        "meal_routine": "regular",
        "sweet_beverage_days": 4,
        "fruit_vegetable_days": 7,
        "animal_source_food_days": 7,
        "self_feeding_opportunity": True,
        "pressure_to_eat": False,
    }
    assert preferred_toddler_metric(toddler) == "sweet_beverage"


def test_personalized_tasks_are_measurable_and_three_items():
    profile = {
        "age_months": 8,
        "feeding_mode": "breastmilk",
        "meal_frequency": 1,
        "animal_source_food_days": 2,
        "fruit_vegetable_days": 3,
        "recent_food_group_count": 3,
        "responsive_feeding": "sometimes",
    }
    tasks = build_personalized_tasks("mpasi", profile, 1)
    assert len(tasks) == 3
    assert all(task["target_label"] for task in tasks)
    assert all(task["input_type"] in {"count", "boolean", "choice", "rating", "observation"} for task in tasks)
    assert tasks[0]["metric"] == "meal_frequency"
    assert tasks[0]["target_value"] == 2
    assert "WHO Guideline" in tasks[0]["evidence"][0]
    assert "https://www.who.int/" in tasks[0]["evidence"][0]

    toddler_task = target_for_metric("toddler", "vegetable_fruit_exposure", {})
    assert toddler_task["input_type"] == "count"
    assert toddler_task["target_value"] == 1


def test_adaptation_waits_for_three_saved_days_and_uses_product_heuristics():
    profile = {"age_months": 8, "feeding_mode": "breastmilk"}
    wait = adaptation_for_days(
        "mpasi",
        [{"tasks": [], "task_adherence": {}}] * 2,
        profile,
        "meal_frequency",
    )
    assert wait["decision"] == "WAIT"

    reinforce = adaptation_for_days(
        "mpasi",
        [{"tasks": [{"metric": "meal_frequency", "key": f"meal_frequency_d{i}"}], "task_adherence": {f"meal_frequency_d{i}": 25}} for i in range(1, 4)],
        profile,
        "meal_frequency",
    )
    assert reinforce["decision"] == "REINFORCE"
    assert reinforce["rule_version"] == RULE_VERSION

    advance = adaptation_for_days(
        "mpasi",
        [{"tasks": [{"metric": "meal_frequency", "key": f"meal_frequency_d{i}"}], "task_adherence": {f"meal_frequency_d{i}": 100}} for i in range(1, 4)],
        profile,
        "meal_frequency",
    )
    assert advance["decision"] == "ADVANCE"
    assert advance["next_primary_metric"] == "animal_source_food"
    assert "clinical" not in advance["reason"].lower()


def test_day_fourteen_evaluation_uses_behavioral_statuses():
    profile = {"age_months": 12, "feeding_mode": "breastmilk"}
    tasks = build_personalized_tasks("mpasi", profile, 14, primary_metric="animal_source_food")
    assert tasks[0]["input_type"] == "count"
    assert tasks[0]["target_value"] == 1
    decision = adaptation_for_days(
        "mpasi",
        [
            {"tasks": [tasks[:1][0]], "task_adherence": {tasks[0]["key"]: 100}},
            {"tasks": [tasks[:1][0]], "task_adherence": {tasks[0]["key"]: 100}},
            {"tasks": [tasks[:1][0]], "task_adherence": {tasks[0]["key"]: 100}},
        ],
        profile,
        "animal_source_food",
    )
    assert decision["decision"] == "ADVANCE"


def test_primary_concern_overrides_generic_gap_order_without_activating_every_issue():
    mpasi = {
        "age_months": 10,
        "feeding_mode": "mixed",
        "meal_frequency": 1,
        "animal_source_food_days": 0,
        "recent_food_group_count": 2,
        "primary_concern": "texture_issue",
    }
    assert preferred_mpasi_metric(mpasi) == "texture"
    baseline_tasks = build_personalized_tasks("mpasi", mpasi, 1)
    assert baseline_tasks[0]["metric"] == "meal_frequency"
    assert any(task["metric"] == "texture" for task in baseline_tasks)
    assert all(task["mode"] == "baseline_observation" for task in baseline_tasks)
    tasks = build_personalized_tasks("mpasi", mpasi, 2)
    assert tasks[0]["metric"] == "texture"
    assert 3 <= len(tasks) <= 5

    toddler = {
        "age_months": 36,
        "meal_routine": "irregular",
        "sweet_beverage_days": 5,
        "primary_concern": "low_self_feeding",
    }
    assert preferred_toddler_metric(toddler) == "self_feeding"
    baseline = build_personalized_tasks("toddler", toddler, 1)
    assert baseline[0]["metric"] == "meal_routine"
    assert any(task["metric"] == "self_feeding" for task in baseline)
    assert build_personalized_tasks("toddler", toddler, 2)[0]["metric"] == "self_feeding"


def test_task_model_exposes_structured_rule_metadata_and_result_prompt():
    profile = {
        "age_months": 8,
        "feeding_mode": "breastmilk",
        "primary_concern": "feeding_routine_issue",
    }
    task = build_personalized_tasks("mpasi", profile, 1)[0]
    assert task["id"] == task["key"]
    assert task["metric_id"] == "meal_frequency"
    assert task["action_text"]
    assert task["result_prompt"]
    assert task["priority"] == 1
    assert task["day_applicability"] == "day_1_baseline"
    rule = task["evidence_rule"]
    for key in (
        "rule_id",
        "category",
        "age_range",
        "metric",
        "threshold_or_target",
        "description",
        "source_name",
        "source_type",
        "source_url",
        "evidence_level",
        "last_reviewed",
        "notes",
        "rule_kind",
    ):
        assert key in rule
    assert rule["source_url"].startswith("https://")


def test_boolean_and_choice_results_are_metric_specific_not_checkbox_scores():
    no_sweetened = target_for_metric("toddler", "sweet_beverage", {})
    task = {
        "input_type": no_sweetened["input_type"],
        "target_value": no_sweetened["target_value"],
        "adherence_map": no_sweetened.get("adherence_map", {}),
    }
    # False means no sweetened beverage was offered, which is the target.
    assert adherence_for_task(task, False, checked=True) == 100
    assert adherence_for_task(task, True, checked=True) == 0

    choice = target_for_metric("toddler", "food_response", {})
    choice_task = {
        "input_type": choice["input_type"],
        "target_value": choice["target_value"],
        "adherence_map": choice["adherence_map"],
    }
    assert adherence_for_task(choice_task, "accepted", checked=True) == 100
    assert adherence_for_task(choice_task, "partial", checked=True) == 50
    assert adherence_for_task(choice_task, "refused", checked=True) == 0
    assert task_result_status(choice_task, "partial", checked=True) == "PARTIAL"


def test_adaptation_requires_three_saved_primary_observations_not_three_rows():
    profile = {"age_months": 8, "feeding_mode": "breastmilk"}
    rows = [
        {"tasks": [{"metric": "meal_frequency", "key": "m1"}], "task_adherence": {"m1": 100}},
        {"tasks": [{"metric": "animal_source_food", "key": "a2"}], "task_adherence": {"a2": 100}},
        {"tasks": [{"metric": "meal_frequency", "key": "m3"}], "task_adherence": {"m3": 100}},
    ]
    decision = adaptation_for_days("mpasi", rows, profile, "meal_frequency")
    assert decision["decision"] == "WAIT"
    assert decision["saved_primary_observations"] == 2


def test_day_fourteen_behavioral_status_is_product_heuristic_not_diagnosis():
    assert behavioral_status(80) == "TERCAPAI_KONSISTEN"
    assert behavioral_status(79.9) == "SEBAGIAN_TERCAPAI"
    assert behavioral_status(50) == "SEBAGIAN_TERCAPAI"
    assert behavioral_status(49.9) == "PERLU_DILANJUTKAN"


def test_child_tasks_never_use_generic_checklist_copy():
    generic = {
        "Ikuti tindakan utama hari ini",
        "Terapkan meal guidance pada waktu makan yang sesuai",
        "Catat apakah panduan dapat diterapkan hari ini",
    }
    mpasi = build_personalized_tasks("mpasi", {"age_months": 8, "feeding_mode": "breastmilk"}, 1)
    toddler = build_personalized_tasks("toddler", {"age_months": 36, "meal_routine": "irregular"}, 1)
    for task in [*mpasi, *toddler]:
        assert task["action_text"] not in generic
        assert task["target_label"] not in generic
    assert all(task["mode"] == "baseline_observation" for task in [*mpasi, *toddler])


def test_choice_like_observation_can_use_explicit_adherence_map():
    task = {"input_type": "observation", "adherence_map": {"accepted": 100, "partial": 50, "refused": 0}}
    assert adherence_for_task(task, "accepted", checked=True) == 100
    assert adherence_for_task(task, "partial", checked=True) == 50
    assert adherence_for_task(task, "refused", checked=True) == 0


def test_legacy_active_child_day_upgrades_to_personalized_todo_without_touching_completed_history():
    from app.models.nutrition_program import NutritionProgramDayModel, NutritionProgramModel
    from app.services.nutrition_program_service import _ensure_personalized_day_payload

    program = NutritionProgramModel(
        stage="toddler",
        assessment_snapshot={"age_months": 36, "meal_routine": "irregular", "primary_concern": "irregular_meal_routine"},
        recommendation_snapshot={"food_groups": ["Protein"], "sample_menu": ["Nasi, telur, sayur"]},
        program_config={"source_snapshot": ["WHO guidance"]},
    )
    active_day = NutritionProgramDayModel(
        day_number=1,
        focus="Generic",
        recommended_action="Ikuti tindakan utama hari ini",
        meal_guidance="Generic",
        action_details={},
        meal_guidance_details={},
        checklist=[
            "Ikuti tindakan utama hari ini",
            "Terapkan meal guidance pada waktu makan yang sesuai",
            "Catat apakah panduan dapat diterapkan hari ini",
        ],
        checklist_state=[False, False, False],
        reference_notes=[],
        completed=False,
    )
    assert _ensure_personalized_day_payload(program, active_day) is True
    assert (active_day.action_details or {}).get("tasks")
    assert "Ikuti tindakan utama hari ini" not in active_day.checklist
    assert all(task["mode"] == "baseline_observation" for task in active_day.action_details["tasks"])

    completed_day = NutritionProgramDayModel(
        day_number=1,
        focus="Historical",
        recommended_action="Ikuti tindakan utama hari ini",
        meal_guidance="Historical",
        action_details={},
        meal_guidance_details={},
        checklist=["Ikuti tindakan utama hari ini"],
        checklist_state=[True],
        reference_notes=[],
        completed=True,
    )
    assert _ensure_personalized_day_payload(program, completed_day) is False
    assert completed_day.checklist == ["Ikuti tindakan utama hari ini"]
