import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { NutritionProgramDailyWorkspace } from "@/components/nutrition-program-daily-workspace";

vi.mock("@/components/auth-gate", () => ({ AuthGate: () => null }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/nutrition/program/p1/day/2",
}));

const tasks = [1, 2, 3].map((index) => ({
  key: `t${index}`, metric: "meal_routine", input_type: "boolean" as const, target_value: true,
  target_label: `Target ${index}`, action: `Action ${index}`, action_text: `Action ${index}`,
  result_prompt: `Result ${index}`, success_criteria: "Recorded",
}));

const baseDay = { focus: "Routine", status: "AVAILABLE" as const, unlock_at: "2026-09-24T00:00:00Z", remaining_seconds: 0, recommended_action: "Do it", meal_guidance: "Meal", meal_guidance_details: {}, reference_notes: [], checklist: tasks.map((task) => task.action_text), food_group_state: [], completed: false, completed_at: null, locked: false, missed: false, has_complaint: null, complaint_note: null, task_results: {} };
const program = { id: "p1", stage: "toddler", title: "Toddler Guided Program", status: "ACTIVE", duration_days: 14, cycle_number: 1, started_at: "2026-09-24T00:00:00Z", ends_at: "2026-10-07T00:00:00Z", completed_at: null, cancelled_at: null, created_at: "2026-09-24T00:00:00Z", updated_at: "2026-09-24T00:00:00Z", days_completed: 1, progress_percent: 7.14, current_day: 2, time_elapsed_days: 2, missed_days: 0, inactive_days: 0, last_activity_at: "2026-09-24T00:00:00Z", goal: null, goals: [], cumulative_goal: null, profile: {}, assessment_snapshot: {}, recommendation: { food_groups: [] }, days: [], extension_history: [], adaptive_mode: true, latest_decision: null, rule_version: null } as never;

describe("Stage 3-9 regressions", () => {
  it("does not leak completed Day 1 checkbox state into Day 2", () => {
    const day1 = { ...baseDay, id: "d1", day_number: 1, checklist_state: [true, true, true], action_details: { tasks } } as never;
    const day2 = { ...baseDay, id: "d2", day_number: 2, checklist_state: [false, false, false], action_details: { tasks } } as never;
    const view = render(<NutritionProgramDailyWorkspace program={program} day={day1} onProgramRefresh={vi.fn()} />);
    expect(screen.getByText(/3 dari 3 tindakan dilakukan/i)).toBeInTheDocument();
    view.rerender(<NutritionProgramDailyWorkspace program={program} day={day2} onProgramRefresh={vi.fn()} />);
    expect(screen.getByText(/0 dari 3 tindakan dilakukan/i)).toBeInTheDocument();
    expect(screen.getAllByText("Belum dilakukan")).toHaveLength(3);
  });
});
