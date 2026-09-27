import { apiFetch } from "@/lib/api";
import type { NutritionAssessmentPayload, NutritionResult } from "@/lib/nutrition";

export type ProgramGoal = {
  id?: string | null;
  goal_key: string;
  title: string;
  description: string;
  baseline: number;
  target: number;
  actual: number;
  unit: string;
  measurement_method: string;
  duration_days: number;
  priority: number;
  status: string;
  progress_percentage: number;
  remaining_gap: number;
};

export type CumulativeGoal = {
  title: string;
  target: number;
  actual: number;
  unit: string;
  progress_percentage: number;
  remaining_gap: number;
  status: string;
  cycles_included: number;
};

export type ProgramSummary = {
  id: string;
  stage: string;
  title: string;
  status: string;
  duration_days: number;
  cycle_number: number;
  parent_program_id?: string | null;
  created_at: string;
  started_at: string;
  ends_at: string;
  completed_at?: string | null;
  cancelled_at?: string | null;
  current_day: number;
  days_completed: number;
  completed_tasks: number;
  total_tasks: number;
  progress_percent: number;
  time_elapsed_days: number;
  missed_days: number;
  inactive_days: number;
  last_activity_at?: string | null;
  goal?: ProgramGoal | null;
  cumulative_goal?: CumulativeGoal | null;
  adaptive_mode?: boolean;
  latest_decision?: AdaptationDecision | null;
  post_block_choice?: {
    preference?: "same_goal" | "smaller_goal" | "different_goal";
    difficulty?: string | null;
    goal_key?: string | null;
    saved_at?: string | null;
  } | null;
};

export type ProgramDayStatus = "LOCKED" | "AVAILABLE" | "IN_PROGRESS" | "COMPLETED" | "MISSED";

export type ProgramTask = {
  key: string;
  id?: string;
  metric: string;
  metric_id?: string;
  input_type: "count" | "boolean" | "choice" | "rating" | "observation" | "simple_experience";
  target_value?: number | string | boolean | null;
  unit?: string;
  target_label: string;
  action?: string;
  action_text?: string;
  result_prompt?: string;
  when?: string;
  why?: string;
  mode?: string;
  evidence?: string[];
  evidence_rule?: {
    rule_id?: string;
    category?: string;
    age_range?: string;
    metric?: string;
    threshold_or_target?: unknown;
    target_unit?: string;
    description?: string;
    source_name?: string;
    source_type?: string;
    source_url?: string;
    evidence_level?: string;
    last_reviewed?: string;
    notes?: string;
    rule_kind?: string;
  } | null;
  success_criteria?: string;
  priority?: number;
  day_applicability?: string;
  result?: unknown;
  current_result?: unknown;
  status?: string;
  evidence_rule_id?: string | null;
  baseline?: unknown;
  target_origin?: "EVIDENCE_RULE" | "PRODUCT_OPERATIONALIZATION" | string;
  stage4_target?: unknown;
  stage4_target_unit?: string | null;
  personalization_trace?: {
    baseline?: unknown;
    gap_id?: string | null;
    gap_metric?: string | null;
    target_id?: string | null;
    evidence_rule_id?: string | null;
  };
  stage5_engine_version?: string;
  options?: Array<{ value: string; label: string }>;
  adherence_map?: Record<string, number>;
};

export type DailyMetricResult = {
  task_id: string;
  metric_id: string;
  target?: unknown;
  actual_result?: unknown;
  unit?: string | null;
  input_type: string;
  status: "NOT_STARTED" | "PARTIAL" | "COMPLETED" | "MISSED" | string;
  adherence?: number | null;
  completed_at?: string | null;
  action_completed: boolean;
  evidence_rule_id?: string | null;
  stage6_engine_version?: string | null;
};

export type ProgramDay = {
  id: string;
  day_number: number;
  focus: string;
  status: ProgramDayStatus;
  unlock_at: string;
  close_at?: string;
  remaining_seconds: number;
  close_remaining_seconds?: number;
  recommended_action: string;
  meal_guidance: string;
  action_details: Record<string, unknown> & {
    tasks?: ProgramTask[];
    task_results?: Record<string, unknown>;
    last_saved_task_adherence?: Record<string, number>;
    metric_results?: DailyMetricResult[];
    last_saved_at?: string;
    daily_log?: DailyQuickLog;
    indicators?: IndicatorSnapshot;
    safety?: SafetySnapshot;
    adaptation?: AdaptationDecision;
    daily_summary?: DailySummary;
    why_this_plan?: string;
    decision?: AdaptationDecision;
    planned?: boolean;
    generated_from_day?: number | null;
  };
  meal_guidance_details: Record<string, unknown>;
  reference_notes: string[];
  checklist: string[];
  checklist_state: boolean[];
  food_group_state: boolean[];
  has_complaint?: boolean | null;
  complaint_note?: string | null;
  task_results?: Record<string, unknown>;
  metric_results?: DailyMetricResult[];
  completed: boolean;
  completed_at?: string | null;
  locked: boolean;
  missed: boolean;
  meal_label?: string | null;
  meal_notes?: string | null;
};

export type ProgramDetail = ProgramSummary & {
  profile: Record<string, unknown>;
  assessment_snapshot: Record<string, unknown>;
  recommendation: NutritionResult;
  goals: ProgramGoal[];
  days: ProgramDay[];
  extension_history: ProgramSummary[];
  rule_version?: Record<string, unknown> | null;
};

export type ProgramDayDetail = {
  program_id: string;
  program_title: string;
  program_status: string;
  duration_days: number;
  current_day: number;
  progress_percent: number;
  missed_days: number;
  inactive_days: number;
  last_activity_at?: string | null;
  goal?: ProgramGoal | null;
  cumulative_goal?: CumulativeGoal | null;
  day: ProgramDay;
};

export type ProgramProgress = {
  program_id: string;
  days_completed: number;
  total_days: number;
  completed_tasks: number;
  total_tasks: number;
  progress_percent: number;
  current_day: number;
  time_elapsed_days: number;
  missed_days: number;
  inactive_days: number;
  last_activity_at?: string | null;
  program_status: string;
  completed_at?: string | null;
  goals: ProgramGoal[];
  cumulative_goal?: CumulativeGoal | null;
  goal_progress_percent?: number;
};

export type DailyQuickLog = {
  portion?: "finished" | "partial" | "little" | "none" | null;
  acceptance?: "liked" | "neutral" | "refused" | null;
  texture?: string | null;
  new_food?: boolean | null;
  reaction?: "none" | "detected" | null;
  reaction_notes?: string | null;
  child_condition?: "healthy" | "fussy" | "sick" | "fever" | "diarrhea" | "severe_teething" | null;
  health_condition?: "well" | "unwell" | "reduced_appetite" | "nausea" | "vomiting" | "fever" | "diarrhea" | "constipation" | "fatigue" | "dizziness" | "pain_discomfort" | "difficulty_eating_drinking" | "other_concern" | null;
  appetite_status?: "good" | "reduced" | "poor" | null;
  eating_difficulty?: "none" | "some" | "difficult" | null;
  routine_adherence?: "yes" | "partial" | "no" | null;
  caregiver_adherence?: "yes" | "partial" | "no" | null;
  hydration_status?: "good" | "reduced" | "poor" | null;
  eating_support?: "independent" | "reminder" | "assisted" | null;
  eating_barrier?: "none" | "low_appetite" | "early_satiety" | "chewing" | "swallowing" | "preparation" | "availability" | "support" | "other" | null;
  parent_difficulty?: "easy" | "somewhat_difficult" | "difficult" | null;
  available_ingredients?: string[];
  budget_context?: string | null;
  notes?: string | null;
};

export type IndicatorSnapshot = {
  acceptance_score?: number | null;
  portion_score?: number | null;
  trend_window_days?: number;
  acceptance_trend?: number | null;
  trend_direction?: string;
  goal_progress_score?: number | null;
  goal_metric?: string | null;
  burden_index?: number | null;
  safety_index?: number;
  history_days_available?: number;
  history_window_days?: number;
  current_adherence?: number | null;
  recent_adherence_average?: number | null;
  adherence_trend_direction?: string;
  goal_metric_trend?: string;
  portion_trend?: number | null;
  portion_trend_direction?: string;
  burden_average?: number | null;
  hydration_average?: number | null;
  hydration_trend_direction?: string;
  support_need_average?: number | null;
  barrier_count?: number;
  latest_barrier?: string | null;
  data_sufficiency?: string;
};

export type SafetyRedFlag = { code?: string; label?: string; matched_phrase?: string; source?: Record<string, unknown> };
export type SafetyResult = { level?: string; blocked?: boolean; decision?: string | null; emergency?: boolean; red_flags?: SafetyRedFlag[]; reason?: string; user_facing_reason?: string; recommended_action?: string };
export type SafetySnapshot = { before_adaptation?: SafetyResult; after_plan_generation?: SafetyResult };
export type AdaptationDecision = {
  decision?: string;
  reason_code?: string;
  reason?: string;
  reason_text?: string;
  user_facing_reason?: string;
  evidence_refs?: string[];
  indicator_snapshot?: IndicatorSnapshot;
  indicators_snapshot?: IndicatorSnapshot;
  rule_version?: { id?: string; version?: string; effective_date?: string | null; review_status?: string | null };
  rule_version_id?: string;
  next_plan_strategy?: string;
  explanation?: { what_changed?: string; why?: string; what_next?: string };
};
export type DailySummary = {
  what_went_well?: string;
  what_was_difficult?: string;
  today_progress?: number | null;
  adaptation_decision?: string;
  why_plan_changes?: string;
  what_changed?: string;
  what_next?: string;
  tomorrow_preview?: string;
};

export type DailyLogResponse = ProgramProgress & {
  saved: boolean;
  saved_at: string;
  day_number: number;
  day_completed: boolean;
  day_completed_at?: string | null;
  checklist_state: boolean[];
  food_group_state: boolean[];
  has_complaint?: boolean | null;
  complaint_note?: string | null;
  task_results?: Record<string, unknown>;
  metric_results?: DailyMetricResult[];
  indicators?: IndicatorSnapshot;
  safety?: SafetySnapshot;
  adaptation?: AdaptationDecision;
  daily_summary?: DailySummary;
  next_day_plan?: Record<string, unknown> | null;
};

export type ProgramEvaluation = {
  program_id: string;
  completion_rate: number;
  guidance_completion: number;
  meal_log_count: number;
  summary: string;
  details: Record<string, unknown> & {
    goals?: ProgramGoal[];
    goal_status?: string;
    what_went_well?: string;
    what_remains?: string;
    recommended_next_step?: string;
    can_extend?: boolean;
    behavior_metrics?: Record<string, { label?: string; assigned_days: number; met_days: number; partial_days?: number; missed_days?: number; adherence_percentage: number; status: string }>;
    daily_metric_history?: Array<{ day: number; metric: string; metric_label?: string; target: unknown; unit?: string; actual: unknown; adherence: number; status: string; action_completed: boolean }>;
    overall_behavioral_adherence?: number;
    overall_behavioral_status?: string;
    most_stable_metric?: string | null;
    least_consistent_metric?: string | null;
    next_focus?: string | null;
    evaluation_framework?: string;
    behavioral_status_heuristic?: string;
    adaptation_rule_version?: Record<string, unknown> | string;
    decision_history?: Array<{ day: number; indicators?: IndicatorSnapshot; decision?: AdaptationDecision; safety?: SafetySnapshot; next_plan?: Record<string, unknown> | null }>;
  };
};


export type ElderlyDailyContextSummary = {
  logged_days?: number;
  appetite?: Record<string, number>;
  hydration?: Record<string, number>;
  routine?: Record<string, number>;
  difficulty?: Record<string, number>;
  eating_support?: Record<string, number>;
  barriers?: Record<string, number>;
  latest?: {
    appetite_status?: DailyQuickLog["appetite_status"];
    hydration_status?: DailyQuickLog["hydration_status"];
    routine_adherence?: DailyQuickLog["routine_adherence"];
    eating_difficulty?: DailyQuickLog["eating_difficulty"];
    eating_support?: DailyQuickLog["eating_support"];
    eating_barrier?: DailyQuickLog["eating_barrier"];
    health_condition?: DailyQuickLog["health_condition"];
  };
};


export type FinalDailyProgressPoint = {
  day: number;
  adherence_percent?: number | null;
  task_count?: number;
  met_tasks?: number;
  status?: string;
  decision?: string | null;
};

export type FinalDailyProgressChange = {
  early_average?: number | null;
  recent_average?: number | null;
  delta_points?: number | null;
  direction?: "IMPROVING" | "STABLE" | "DECLINING" | "INSUFFICIENT_DATA" | string;
  scored_days?: number;
  strong_days?: number;
};

export type FinalProgramResult = {
  program: ProgramSummary;
  cycle: number;
  duration_days: number;
  goal?: ProgramGoal | null;
  baseline?: unknown;
  target?: unknown;
  actual?: unknown;
  goal_status: string;
  goal_achievement_percent: number;
  program_completion_percent: number;
  program_numbers: {
    duration_days?: number;
    completed_days?: number;
    missed_days?: number;
    logged_days?: number;
    adaptation_decisions?: number;
    [key: string]: unknown;
  };
  what_accomplished: string[];
  what_changed: string;
  what_worked_well: string[];
  challenges: string[];
  adaptation_history: Array<{
    day?: number;
    decision?: string;
    reason?: string | null;
    user_facing_reason?: string | null;
    rule_version_id?: string | null;
    trend_direction?: string | null;
    acceptance_trend?: number | null;
    next_plan?: Record<string, unknown> | null;
  }>;
  trends: {
    acceptance?: Array<{ day?: number; value?: number; direction?: string }>;
    goal_progress_percent?: number;
    behavioral_adherence_percent?: number;
    goal_metric?: string | null;
    daily_progress?: FinalDailyProgressPoint[];
    daily_progress_change?: FinalDailyProgressChange;
    elderly_daily_context?: ElderlyDailyContextSummary;
    [key: string]: unknown;
  };
  safety_notes: string[];
  next_step: {
    decision?: string;
    can_extend?: boolean;
    can_reframe?: boolean;
    options?: string[];
    message?: string;
    [key: string]: unknown;
  };
  extension_history: ProgramSummary[];
  generated_at: string;
};

export type ExtensionRecommendation = {
  program_id: string;
  goal_status: string;
  previous_actual: number;
  previous_target: number;
  remaining_gap: number;
  unit: string;
  recommended_days: number;
  cumulative_actual: number;
  cumulative_target: number;
  cumulative_progress: number;
  why: string;
  guidance_adjustments: Record<string, unknown>;
};

export function createNutritionProgram(assessment: NutritionAssessmentPayload, durationDays = 14, goalKey?: string, displayName?: string) {
  return apiFetch<ProgramSummary>("/api/nutrition/program", {
    method: "POST",
    body: JSON.stringify({ assessment, consent_to_save: true, duration_days: durationDays, goal_key: goalKey || undefined, display_name: displayName?.trim() || undefined }),
  });
}

export function listNutritionPrograms() { return apiFetch<ProgramSummary[]>("/api/nutrition/program"); }
export function listNutritionHistory() { return apiFetch<ProgramSummary[]>("/api/nutrition/history"); }
export function getNutritionProgram(id: string) { return apiFetch<ProgramDetail>(`/api/nutrition/program/${id}`); }
export function getNutritionHistoryDetail(id: string) { return apiFetch<ProgramDetail>(`/api/nutrition/history/${id}`); }
export function getNutritionProgramDay(id: string, dayNumber: number) { return apiFetch<ProgramDayDetail>(`/api/nutrition/program/${id}/days/${dayNumber}`); }
export type DailyLogInput = {
  checklistState: boolean[];
  foodGroupState?: boolean[];
  hasComplaint?: boolean | null;
  complaintNote?: string;
  mealLabel?: string;
  mealNotes?: string;
  taskResults?: Record<string, unknown>;
  quickLog?: DailyQuickLog;
};

export function saveDailyLog(id: string, dayNumber: number, input: DailyLogInput) {
  return apiFetch<DailyLogResponse>(`/api/nutrition/program/${id}/daily-log`, {
    method: "POST",
    body: JSON.stringify({
      day_number: dayNumber,
      checklist_state: input.checklistState,
      food_group_state: input.foodGroupState ?? [],
      has_complaint: input.hasComplaint ?? null,
      complaint_note: input.complaintNote?.trim() || undefined,
      meal_label: input.mealLabel?.trim().slice(0, 100) || undefined,
      meal_notes: input.mealNotes || undefined,
      task_results: input.taskResults ?? {},
      portion: input.quickLog?.portion ?? undefined,
      acceptance: input.quickLog?.acceptance ?? undefined,
      texture: input.quickLog?.texture?.trim() || undefined,
      new_food: input.quickLog?.new_food ?? undefined,
      reaction: input.quickLog?.reaction ?? undefined,
      reaction_notes: input.quickLog?.reaction_notes?.trim() || undefined,
      child_condition: input.quickLog?.child_condition ?? undefined,
      health_condition: input.quickLog?.health_condition ?? undefined,
      appetite_status: input.quickLog?.appetite_status ?? undefined,
      eating_difficulty: input.quickLog?.eating_difficulty ?? undefined,
      routine_adherence: input.quickLog?.routine_adherence ?? undefined,
      caregiver_adherence: input.quickLog?.caregiver_adherence ?? undefined,
      hydration_status: input.quickLog?.hydration_status ?? undefined,
      eating_support: input.quickLog?.eating_support ?? undefined,
      eating_barrier: input.quickLog?.eating_barrier ?? undefined,
      parent_difficulty: input.quickLog?.parent_difficulty ?? undefined,
      available_ingredients: input.quickLog?.available_ingredients ?? [],
      budget_context: input.quickLog?.budget_context?.trim() || undefined,
      notes: input.quickLog?.notes?.trim() || undefined,
    }),
  });
}
export function getProgramProgress(id: string) { return apiFetch<ProgramProgress>(`/api/nutrition/program/${id}/progress`); }
export function cancelNutritionProgram(id: string) { return apiFetch<ProgramSummary>(`/api/nutrition/program/${id}/cancel`, { method: "POST", body: JSON.stringify({ confirm: true }) }); }
export function deleteCancelledNutritionProgram(id: string) { return apiFetch<void>(`/api/nutrition/program/${id}`, { method: "DELETE" }); }
export function getProgramEvaluation(id: string) { return apiFetch<ProgramEvaluation>(`/api/nutrition/program/${id}/evaluation`); }
export function getFinalProgramResult(id: string) { return apiFetch<FinalProgramResult>(`/api/nutrition/program/${id}/result`); }
export function getExtensionRecommendation(id: string) { return apiFetch<ExtensionRecommendation>(`/api/nutrition/program/${id}/extension-recommendation`); }
export type BlockReview = {
  program_id: string;
  block_number?: number;
  duration_days?: number;
  block_completed?: boolean;
  review_status?: string;
  program_progress?: { completed_days?: number; planned_days?: number; percent?: number };
  goal_progress?: { metric?: string | null; target?: unknown; actual?: unknown; unit?: string | null; percent?: number };
  goal?: Record<string, unknown> | null;
  baseline?: unknown;
  current?: unknown;
  metrics?: Array<{ metric: string; label?: string; target?: unknown; unit?: string | null; actual?: number; observed_days?: number; assigned_days?: number; adherence?: number; status?: string; trend?: Record<string, unknown> }>;
  adherence_summary?: Record<string, unknown>;
  trend: Record<string, unknown>;
  trends?: Record<string, Record<string, unknown>>;
  what_improved: string;
  what_remains: string;
  safety: Record<string, unknown>;
  safety_summary?: Record<string, unknown>;
  goal_status?: string;
  decision: string;
  next_focus?: string | null;
  options: string[];
  can_extend: boolean;
  can_reframe: boolean;
  rule_version?: string;
  generated_at?: string;
  evaluation_framework?: string;
};

export function getActiveNutritionRule() { return apiFetch<Record<string, unknown>>("/api/nutrition/rules/active"); }
export function getBlockReview(id: string) { return apiFetch<BlockReview>(`/api/nutrition/program/${id}/block-review`); }
export function pauseNutritionProgram(id: string) { return apiFetch<ProgramSummary>(`/api/nutrition/program/${id}/pause`, { method: "POST", body: JSON.stringify({ confirm: true }) }); }
export function resumeNutritionProgram(id: string, recoveryStatus?: "improved" | "still_unwell") {
  return apiFetch<ProgramSummary>(`/api/nutrition/program/${id}/resume`, {
    method: "POST",
    body: JSON.stringify({ confirm: true, recovery_status: recoveryStatus }),
  });
}
export function reviewNutritionSafetyHold(id: string) {
  return apiFetch<ProgramSummary>(`/api/nutrition/program/${id}/safety-review`, { method: "POST", body: JSON.stringify({ confirm: true, action: "restart_assessment" }) });
}
export function skipNutritionProgramDay(id: string) { return apiFetch<ProgramProgress>(`/api/nutrition/program/${id}/skip-day`, { method: "POST", body: JSON.stringify({ confirm: true }) }); }
export function extendNutritionProgram(id: string, options?: { preference?: "same_goal" | "smaller_goal" | "different_goal"; difficulty?: string; goalKey?: string }) {
  return apiFetch<ProgramSummary>(`/api/nutrition/program/${id}/extend`, { method: "POST", body: JSON.stringify({ confirm: true, preference: options?.preference ?? "same_goal", difficulty: options?.difficulty || undefined, goal_key: options?.goalKey || undefined }) });
}

const PROGRAM_ENTRY_PREFIX = "sehatin:nutrition-program-entry:";

export function markNutritionProgramEntry(programId: string) {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(`${PROGRAM_ENTRY_PREFIX}${programId}`, "1");
}

export function consumeNutritionProgramEntry(programId: string) {
  if (typeof window === "undefined") return false;
  const key = `${PROGRAM_ENTRY_PREFIX}${programId}`;
  const marked = sessionStorage.getItem(key) === "1";
  if (marked) sessionStorage.removeItem(key);
  return marked;
}

export function formatPercent(value: number) { return value.toFixed(2).replace(/\.?0+$/, ""); }
