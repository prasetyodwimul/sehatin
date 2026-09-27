export type NutritionStage = "mpasi" | "toddler" | "elderly";
export type NutritionSex = "female" | "male";
export type NutritionFoodGroup = "grains" | "legumes" | "dairy" | "animal_source" | "eggs" | "vitamin_a_produce" | "other_produce" | "breastmilk";
export type ElderlyCondition = "diabetes" | "hypertension" | "high_cholesterol" | "heart_disease" | "kidney_disease" | "other";

export const ELDERLY_CONDITION_OPTIONS: Array<{ value: ElderlyCondition; label: string }> = [
  { value: "diabetes", label: "Diabetes" },
  { value: "hypertension", label: "Hipertensi" },
  { value: "high_cholesterol", label: "Kolesterol Tinggi" },
  { value: "heart_disease", label: "Penyakit Jantung" },
  { value: "kidney_disease", label: "Penyakit Ginjal" },
  { value: "other", label: "Lainnya" },
];

export function elderlyConditionLabel(value: ElderlyCondition, otherCondition?: string) {
  if (value === "other" && otherCondition?.trim()) return otherCondition.trim();
  return ELDERLY_CONDITION_OPTIONS.find((item) => item.value === value)?.label ?? value;
}

export type NutritionAssessmentPayload = {
  stage: NutritionStage;
  date_of_birth?: string;
  assessment_date?: string;
  age_months?: number;
  age_years?: number;
  sex: NutritionSex;
  weight_kg: number;
  height_cm: number;
  feeding_mode?: "breastmilk" | "formula" | "mixed" | "other";
  mpasi_history?: "not_started" | "started";
  texture_level?: "smooth_mashed" | "mashed_lumpy" | "finger_food" | "family_soft";
  appetite?: "low" | "typical" | "high";
  meal_frequency?: number;
  activity_level?: "low" | "moderate" | "high";
  chewing_difficulty?: boolean;
  swallowing_difficulty?: boolean;
  hydration_pattern?: "regular" | "sometimes_low" | "often_low" | "unknown";
  eating_independence?: "independent" | "needs_reminder" | "needs_setup" | "needs_assistance" | "unknown";
  caregiver_support?: "none" | "sometimes" | "daily" | "unknown";
  animal_source_food_days?: number;
  fruit_vegetable_days?: number;
  recent_food_group_count?: number;
  recent_food_groups?: NutritionFoodGroup[];
  responsive_feeding?: "usually" | "sometimes" | "rarely";
  meal_routine?: "regular" | "mixed" | "irregular";
  sweet_beverage_days?: number;
  sweetened_beverage_exposure?: boolean;
  pressure_to_eat?: boolean;
  screen_during_meals?: boolean;
  self_feeding_opportunity?: boolean;
  mealtime_duration_minutes?: number;
  food_preferences?: string[];
  primary_concern?:
    | "low_animal_source_food_exposure"
    | "low_food_diversity"
    | "feeding_routine_issue"
    | "texture_issue"
    | "food_refusal"
    | "responsive_feeding_issue"
    | "limited_variety"
    | "low_vegetable_exposure"
    | "sweetened_beverage_exposure"
    | "low_self_feeding"
    | "pressure_feeding"
    | "irregular_meal_routine";
  snack_frequency?: number;
  feeding_method?: "caregiver_assisted" | "mixed" | "self_feeding";
  food_refusal?: boolean;
  food_rejection?: "none" | "occasional" | "frequent";
  food_rejection_details?: string[];
  feeding_difficulty?: "none" | "some" | "significant";
  feeding_difficulty_details?: string[];
  texture_refusal?: boolean;
  repeated_exposure_days?: number;
  water_primary_beverage?: boolean;
  meal_environment?: "calm" | "mixed" | "distracted";
  safety_hygiene_ok?: boolean;
  barriers?: string[];
  allergies?: string[];
  dietary_restrictions?: string[];
  medical_context?: string;
  has_condition?: boolean;
  conditions?: ElderlyCondition[];
  other_condition?: string;
  notes?: string;
};

export type NutritionValidationIssue = {
  level: "VALID" | "WARNING" | "INVALID";
  code: string;
  message: string;
};

export type NutritionValidation = {
  status: "VALID" | "WARNING" | "INVALID";
  can_process: boolean;
  message: string;
  issues: NutritionValidationIssue[];
  indicators: Array<Record<string, unknown>>;
  references: Array<Record<string, unknown>>;
};

export type NutritionEvidenceRule = {
  source_name?: string;
  source_type?: string;
  source_url?: string;
  evidence_level?: string;
  last_reviewed?: string;
  rule_kind?: string;
  [key: string]: unknown;
};

export type NutritionGap = {
  id: string;
  metric: string;
  label: string;
  baseline: unknown;
  expected: string;
  priority_tier: number;
  severity: number;
  rationale: string;
  evidence?: NutritionEvidenceRule | null;
};

export type NutritionTargetCandidate = {
  id: string;
  metric: string;
  baseline: unknown;
  target: unknown;
  unit: string;
  priority: number;
  rationale: string;
  label: string;
  evidence?: NutritionEvidenceRule | null;
};

export type NutritionResult = {
  stage: NutritionStage;
  category: string;
  age_band: string;
  personalization_status: "personalized_education" | "limited_for_safety";
  validation: NutritionValidation;
  input_summary: string[];
  summary: string;
  estimated_needs: Record<string, string>;
  meal_pattern: Record<string, string>;
  priority_nutrients: string[];
  food_groups: string[];
  recommendations: string[];
  sample_menu: string[];
  guidance: string[];
  safety_notes: string[];
  disclaimer: string;
  references: string[];
  suggested_goals: Array<{
    goal_key: string;
    title: string;
    description: string;
    baseline: number;
    target: number;
    unit: string;
    measurement_method: string;
    duration: number;
    priority: number;
    status: string;
    baseline_label?: string;
    target_label?: string;
    selection_reason?: string;
  }>;
  baseline?: Record<string, unknown>;
  detected_gaps?: NutritionGap[];
  primary_gap?: NutritionGap | null;
  primary_target?: NutritionTargetCandidate | null;
  support_targets?: NutritionTargetCandidate[];
  elderly_context?: {
    hydration_pattern?: "regular" | "sometimes_low" | "often_low" | "unknown";
    hydration_label?: string;
    eating_independence?: "independent" | "needs_reminder" | "needs_setup" | "needs_assistance" | "unknown";
    eating_independence_label?: string;
    caregiver_support?: "none" | "sometimes" | "daily" | "unknown";
    caregiver_support_label?: string;
    focus?: string[];
    daily_actions?: string[];
    notes?: string[];
    context_kind?: string;
  };
  health_context?: {
    has_condition?: boolean;
    conditions?: ElderlyCondition[];
    condition_labels?: string[];
    other_condition?: string | null;
    nutrition_focus?: string[];
    recommendations?: string[];
    food_guidance?: string[];
    daily_actions?: string[];
    program_focus?: string[];
    needs_clinical_consultation?: boolean;
    consultation_note?: string | null;
    source_note?: string;
  };
  evidence_rule_evaluation?: {
    status: "MATCHED" | "NO_MATCHING_RULE" | string;
    message: string;
    evidence_available: boolean;
    matched_rules: Array<{
      rule_id: string;
      metric: string;
      condition: string;
      rationale: string;
      rule_kind: string;
      product_note?: string | null;
      evidence?: NutritionEvidenceRule;
      source?: NutritionEvidenceRule;
      [key: string]: unknown;
    }>;
    unmatched_metrics: string[];
    targets: Array<NutritionTargetCandidate & { evidence_rule_id?: string; rule_kind?: string }>;
    primary_target?: (NutritionTargetCandidate & { evidence_rule_id?: string; rule_kind?: string }) | null;
    support_targets?: Array<NutritionTargetCandidate & { evidence_rule_id?: string; rule_kind?: string }>;
    engine_version?: string;
  };
};

export type NutritionResultSession = {
  result: NutritionResult;
  assessment?: NutritionAssessmentPayload;
  created_at: string;
};

const STORAGE_PREFIX = "sehatin:nutrition-result:";

export function nutritionResultPath(stage: NutritionStage) {
  return `/nutrition/${stage}/result`;
}

export function nutritionAssessmentPath(stage: NutritionStage) {
  return `/nutrition/${stage}`;
}

export function clearNutritionSession(stage: NutritionStage) {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(`${STORAGE_PREFIX}${stage}`);
}

export function saveNutritionResult(result: NutritionResult, assessment?: NutritionAssessmentPayload) {
  if (typeof window === "undefined") return;
  const envelope: NutritionResultSession = {
    result,
    assessment,
    created_at: new Date().toISOString(),
  };
  sessionStorage.setItem(`${STORAGE_PREFIX}${result.stage}`, JSON.stringify(envelope));
}

export function loadNutritionSession(stage: NutritionStage): NutritionResultSession | null {
  if (typeof window === "undefined") return null;
  const raw = sessionStorage.getItem(`${STORAGE_PREFIX}${stage}`);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as NutritionResultSession | NutritionResult;
    if ("result" in parsed) {
      return parsed.result.stage === stage ? parsed : null;
    }
    return parsed.stage === stage
      ? { result: parsed, created_at: new Date().toISOString() }
      : null;
  } catch {
    return null;
  }
}

export function loadNutritionResult(stage: NutritionStage): NutritionResult | null {
  return loadNutritionSession(stage)?.result ?? null;
}
