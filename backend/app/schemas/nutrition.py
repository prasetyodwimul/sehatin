from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Stage = Literal["mpasi", "toddler", "elderly"]
Sex = Literal["female", "male"]
FeedingMode = Literal["breastmilk", "formula", "mixed", "other"]
TextureLevel = Literal["smooth_mashed", "mashed_lumpy", "finger_food", "family_soft"]
AppetiteLevel = Literal["low", "typical", "high"]
ActivityLevel = Literal["low", "moderate", "high"]
HydrationPattern = Literal["regular", "sometimes_low", "often_low", "unknown"]
EatingIndependence = Literal["independent", "needs_reminder", "needs_setup", "needs_assistance", "unknown"]
CaregiverSupport = Literal["none", "sometimes", "daily", "unknown"]
ElderlyCondition = Literal["diabetes", "hypertension", "high_cholesterol", "heart_disease", "kidney_disease", "other"]
ValidationStatus = Literal["VALID", "WARNING", "INVALID"]
ResponsiveFeedingLevel = Literal["usually", "sometimes", "rarely"]
MealRoutineLevel = Literal["regular", "mixed", "irregular"]
PrimaryConcern = Literal[
    "low_animal_source_food_exposure",
    "low_food_diversity",
    "feeding_routine_issue",
    "texture_issue",
    "food_refusal",
    "responsive_feeding_issue",
    "limited_variety",
    "low_vegetable_exposure",
    "sweetened_beverage_exposure",
    "low_self_feeding",
    "pressure_feeding",
    "irregular_meal_routine",
]
FeedingMethod = Literal["caregiver_assisted", "mixed", "self_feeding"]
MealEnvironment = Literal["calm", "mixed", "distracted"]
MpasiHistory = Literal["not_started", "started"]
FeedingDifficulty = Literal["none", "some", "significant"]
FoodRejection = Literal["none", "occasional", "frequent"]
FoodGroup = Literal["grains", "legumes", "dairy", "animal_source", "eggs", "vitamin_a_produce", "other_produce", "breastmilk"]


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.strip().split())
    if "\x00" in cleaned:
        raise ValueError("Input mengandung karakter yang tidak diizinkan")
    return cleaned or None


def _calculate_age_months(date_of_birth: date, assessment_date: date) -> int:
    if date_of_birth > assessment_date:
        raise ValueError("Tanggal lahir tidak boleh setelah tanggal assessment")
    months = (assessment_date.year - date_of_birth.year) * 12 + assessment_date.month - date_of_birth.month
    if assessment_date.day < date_of_birth.day:
        months -= 1
    return max(0, months)


class NutritionAnthropometricValidationRequest(BaseModel):
    stage: Stage
    date_of_birth: date | None = None
    assessment_date: date | None = None
    age_months: int | None = Field(default=None, ge=0, le=120)
    age_years: int | None = Field(default=None, ge=0, le=120)
    sex: Sex
    weight_kg: float = Field(gt=0, le=300)
    height_cm: float = Field(gt=0, le=250)

    @model_validator(mode="after")
    def validate_age(self):
        if self.stage in {"mpasi", "toddler"} and self.date_of_birth is not None:
            assessment_date = self.assessment_date or date.today()
            self.assessment_date = assessment_date
            self.age_months = _calculate_age_months(self.date_of_birth, assessment_date)
        if self.stage in {"mpasi", "toddler"} and self.age_months is None:
            raise ValueError("Tanggal lahir wajib diisi untuk assessment anak; age_months legacy tetap didukung oleh API.")
        if self.stage == "elderly" and self.age_years is None:
            raise ValueError("Usia dalam tahun wajib diisi untuk lansia")
        return self


class ValidationIssueResponse(BaseModel):
    level: ValidationStatus
    code: str
    message: str


class NutritionValidationResponse(BaseModel):
    status: ValidationStatus
    can_process: bool
    message: str
    issues: list[ValidationIssueResponse] = Field(default_factory=list)
    indicators: list[dict] = Field(default_factory=list)
    references: list[dict] = Field(default_factory=list)


class NutritionRequest(BaseModel):
    stage: Stage
    date_of_birth: date | None = None
    assessment_date: date | None = None
    age_months: int | None = Field(default=None, ge=0, le=120)
    age_years: int | None = Field(default=None, ge=0, le=120)
    sex: Sex
    weight_kg: float = Field(gt=0, le=300)
    height_cm: float = Field(gt=0, le=250)

    feeding_mode: FeedingMode | None = None
    mpasi_history: MpasiHistory | None = None
    texture_level: TextureLevel | None = None
    appetite: AppetiteLevel = "typical"
    meal_frequency: int | None = Field(default=None, ge=1, le=10)
    activity_level: ActivityLevel = "moderate"
    chewing_difficulty: bool = False
    swallowing_difficulty: bool = False
    hydration_pattern: HydrationPattern | None = None
    eating_independence: EatingIndependence | None = None
    caregiver_support: CaregiverSupport | None = None

    # Stage 3 child profile fields. They remain in the existing request JSON so
    # no database migration or duplicate persistence endpoint is required.
    animal_source_food_days: int | None = Field(default=None, ge=0, le=7)
    fruit_vegetable_days: int | None = Field(default=None, ge=0, le=7)
    recent_food_group_count: int | None = Field(default=None, ge=0, le=8)
    recent_food_groups: list[FoodGroup] = Field(default_factory=list, max_length=8)
    responsive_feeding: ResponsiveFeedingLevel | None = None
    meal_routine: MealRoutineLevel | None = None
    sweet_beverage_days: int | None = Field(default=None, ge=0, le=7)
    sweetened_beverage_exposure: bool | None = None
    pressure_to_eat: bool = False
    screen_during_meals: bool = False
    self_feeding_opportunity: bool = False
    mealtime_duration_minutes: int | None = Field(default=None, ge=1, le=180)
    food_preferences: list[str] = Field(default_factory=list, max_length=10)

    # Behavioral context only; none of these fields imply a diagnosis.
    primary_concern: PrimaryConcern | None = None
    snack_frequency: int | None = Field(default=None, ge=0, le=10)
    feeding_method: FeedingMethod | None = None
    food_refusal: bool = False  # legacy compatibility
    food_rejection: FoodRejection | None = None
    food_rejection_details: list[str] = Field(default_factory=list, max_length=10)
    feeding_difficulty: FeedingDifficulty | None = None
    feeding_difficulty_details: list[str] = Field(default_factory=list, max_length=10)
    texture_refusal: bool = False
    repeated_exposure_days: int | None = Field(default=None, ge=0, le=7)
    water_primary_beverage: bool | None = None
    meal_environment: MealEnvironment | None = None
    safety_hygiene_ok: bool | None = None
    barriers: list[str] = Field(default_factory=list, max_length=10)

    allergies: list[str] = Field(default_factory=list, max_length=10)
    dietary_restrictions: list[str] = Field(default_factory=list, max_length=10)
    medical_context: str | None = Field(default=None, max_length=200)
    has_condition: bool = False
    conditions: list[ElderlyCondition] = Field(default_factory=list, max_length=6)
    other_condition: str | None = Field(default=None, max_length=80)
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("medical_context", "notes", "other_condition")
    @classmethod
    def clean_free_text(cls, value: str | None):
        return _clean_text(value)

    @field_validator(
        "allergies",
        "dietary_restrictions",
        "food_preferences",
        "food_rejection_details",
        "feeding_difficulty_details",
        "barriers",
    )
    @classmethod
    def clean_list_values(cls, values: list[str]):
        cleaned: list[str] = []
        for value in values:
            item = _clean_text(value)
            if item and len(item) <= 80:
                cleaned.append(item)
            elif item:
                raise ValueError("Setiap item teks maksimal 80 karakter")
        return cleaned

    @model_validator(mode="after")
    def validate_stage_specific_input(self):
        if self.stage in {"mpasi", "toddler"} and self.date_of_birth is not None:
            assessment_date = self.assessment_date or date.today()
            self.assessment_date = assessment_date
            self.age_months = _calculate_age_months(self.date_of_birth, assessment_date)

        if self.stage in {"mpasi", "toddler"} and self.age_months is None:
            raise ValueError("Tanggal lahir wajib diisi untuk assessment anak; age_months legacy tetap didukung oleh API.")
        if self.stage == "mpasi":
            if not 6 <= int(self.age_months or 0) <= 23:
                raise ValueError("MPASI hanya ditujukan untuk usia 6–23 bulan")
            if self.feeding_mode is None:
                raise ValueError("Pola pemberian susu wajib dipilih untuk MPASI")
        if self.stage == "toddler" and not 24 <= int(self.age_months or 0) <= 59:
            raise ValueError("Toddler ditujukan untuk usia 24–59 bulan")
        if self.stage == "elderly" and (self.age_years is None or self.age_years < 60):
            raise ValueError("Panduan lansia ditujukan untuk usia 60+ tahun")
        if self.stage != "elderly" and (self.has_condition or self.conditions or self.other_condition):
            raise ValueError("Konteks penyakit terstruktur hanya tersedia pada modul lansia")
        if self.stage != "elderly" and (self.hydration_pattern or self.eating_independence or self.caregiver_support):
            raise ValueError("Konteks fungsi makan/hidrasi hanya tersedia pada modul lansia")
        if self.stage == "elderly":
            # Chronic/known-condition context is separate from today's health state.
            # It must never imply a diagnosis or trigger PAUSED/LOCKED by itself.
            self.conditions = list(dict.fromkeys(self.conditions))
            if not self.has_condition:
                self.conditions = []
                self.other_condition = None
            else:
                if not self.conditions:
                    raise ValueError("Pilih minimal satu penyakit atau kondisi yang sudah diketahui")
                if "other" in self.conditions and not self.other_condition:
                    raise ValueError("Nama penyakit atau kondisi wajib diisi ketika memilih Lainnya")
                if "other" not in self.conditions:
                    self.other_condition = None
        if self.swallowing_difficulty and self.stage != "elderly":
            raise ValueError("Input gangguan menelan hanya tersedia pada modul lansia")
        if self.recent_food_groups and self.recent_food_group_count is None:
            self.recent_food_group_count = len(self.recent_food_groups)
        if self.food_rejection == "none":
            self.food_rejection_details = []
            self.food_refusal = False
        elif self.food_rejection in {"occasional", "frequent"}:
            # Keep the existing downstream program contract in sync while Stage 3
            # stores the richer enum as the source of truth.
            self.food_refusal = True
        if self.feeding_difficulty == "none":
            self.feeding_difficulty_details = []
        if self.sweetened_beverage_exposure is False:
            self.sweet_beverage_days = 0
        if self.primary_concern:
            mpasi_concerns = {
                "low_animal_source_food_exposure",
                "low_food_diversity",
                "feeding_routine_issue",
                "texture_issue",
                "food_refusal",
                "responsive_feeding_issue",
            }
            toddler_concerns = {
                "limited_variety",
                "low_vegetable_exposure",
                "sweetened_beverage_exposure",
                "low_self_feeding",
                "pressure_feeding",
                "irregular_meal_routine",
                "food_refusal",
            }
            if self.stage == "mpasi" and self.primary_concern not in mpasi_concerns:
                raise ValueError("Primary concern tidak sesuai dengan modul MPASI")
            if self.stage == "toddler" and self.primary_concern not in toddler_concerns:
                raise ValueError("Primary concern tidak sesuai dengan modul toddler")
            if self.stage == "elderly":
                raise ValueError("Primary concern ini hanya tersedia pada modul MPASI/toddler")
        return self


class NutritionResponse(BaseModel):
    stage: Stage
    category: str
    age_band: str
    personalization_status: Literal["personalized_education", "limited_for_safety"]
    validation: NutritionValidationResponse
    input_summary: list[str]
    summary: str
    estimated_needs: dict[str, str]
    meal_pattern: dict[str, str]
    priority_nutrients: list[str]
    food_groups: list[str]
    recommendations: list[str]
    sample_menu: list[str]
    guidance: list[str]
    safety_notes: list[str]
    disclaimer: str
    references: list[str] = Field(default_factory=list)
    suggested_goals: list[dict] = Field(default_factory=list)
    baseline: dict = Field(default_factory=dict)
    detected_gaps: list[dict] = Field(default_factory=list)
    primary_gap: dict | None = None
    primary_target: dict | None = None
    support_targets: list[dict] = Field(default_factory=list)
    evidence_rule_evaluation: dict = Field(default_factory=dict)
    health_context: dict = Field(default_factory=dict)
    elderly_context: dict = Field(default_factory=dict)
