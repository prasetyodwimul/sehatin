import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { NutritionProgramDailyWorkspace } from "@/components/nutrition-program-daily-workspace";
import { NutritionProgramDayPage } from "@/components/nutrition-program-day-page";
import type { ProgramDay, ProgramDetail, ProgramTask } from "@/lib/nutrition-program";

const { shellStateRef, routerPush, routerReplace, routerRefresh } = vi.hoisted(() => ({
  shellStateRef: { current: {} as Record<string, unknown> },
  routerPush: vi.fn(),
  routerReplace: vi.fn(),
  routerRefresh: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: routerPush, replace: routerReplace, refresh: routerRefresh }),
  usePathname: () => "/nutrition/program/p1/day/2",
}));

vi.mock("@/components/nutrition-program-shell", () => ({
  useNutritionProgramShell: () => shellStateRef.current,
}));

const tasks: ProgramTask[] = [
  { key: "a", metric: "meal_routine", input_type: "count", target_value: 3, unit: "kali", target_label: "3 waktu makan", action_text: "Catat waktu makan", result_prompt: "Berapa kali?", why: "Mengukur rutinitas makan aktual." },
  { key: "b", metric: "responsive_feeding", input_type: "boolean", target_value: true, target_label: "Tanpa memaksa", action_text: "Ikuti tanda lapar/kenyang", result_prompt: "Dilakukan?", why: "Mendukung responsive feeding." },
  { key: "c", metric: "self_feeding", input_type: "count", target_value: 1, unit: "kesempatan", target_label: "1 kesempatan", action_text: "Beri kesempatan makan mandiri", result_prompt: "Berapa kesempatan?", why: "Mendukung latihan makan mandiri." },
];

function makeDay(id: string, dayNumber: number, checklistState: boolean[], status: ProgramDay["status"]): ProgramDay {
  return {
    id,
    day_number: dayNumber,
    focus: dayNumber === 1 ? "Baseline" : `Fokus Hari ${dayNumber}`,
    status,
    unlock_at: "2026-09-24T00:00:00Z",
    remaining_seconds: 0,
    recommended_action: "Panduan hari ini",
    meal_guidance: "Menu hari ini",
    action_details: { tasks },
    meal_guidance_details: { food_groups: ["protein", "vegetable"] },
    reference_notes: [],
    checklist: tasks.map((task) => task.action_text ?? task.target_label),
    checklist_state: checklistState,
    food_group_state: [],
    has_complaint: false,
    complaint_note: null,
    completed: status === "COMPLETED",
    completed_at: status === "COMPLETED" ? "2026-09-24T00:10:00Z" : null,
    locked: false,
    missed: false,
  };
}

const day1 = makeDay("d1", 1, [true, true, true], "COMPLETED");
const day2 = makeDay("d2", 2, [false, false, false], "AVAILABLE");
const day3 = makeDay("d3", 3, [false, false, false], "AVAILABLE");

const program = {
  id: "p1",
  stage: "toddler",
  title: "Healthy Eating Habit Plan",
  status: "ACTIVE",
  duration_days: 14,
  cycle_number: 1,
  created_at: "2026-09-24T00:00:00Z",
  started_at: "2026-09-24T00:00:00Z",
  ends_at: "2026-10-07T00:00:00Z",
  current_day: 2,
  days_completed: 1,
  completed_tasks: 3,
  total_tasks: 9,
  progress_percent: 7.14,
  time_elapsed_days: 2,
  missed_days: 0,
  inactive_days: 0,
  profile: {},
  assessment_snapshot: {},
  recommendation: { food_groups: [] },
  goals: [],
  days: [day1, day2, day3],
  extension_history: [],
} as unknown as ProgramDetail;

describe("nutrition day state isolation", () => {
  it("does not carry Day 1 completed action state into Day 2 when the day prop changes", () => {
    const onRefresh = vi.fn();
    const { rerender } = render(<NutritionProgramDailyWorkspace program={program} day={day1} onProgramRefresh={onRefresh} />);

    rerender(<NutritionProgramDailyWorkspace program={program} day={day2} onProgramRefresh={onRefresh} />);

    expect(screen.getByText("0 dari 3 tindakan dilakukan")).toBeInTheDocument();
    expect(screen.getAllByText("Belum dilakukan")).toHaveLength(3);
    expect(screen.queryByText("3 dari 3 tindakan dilakukan")).not.toBeInTheDocument();
  });

  it.each([2, 3])("renders Day %s from the structured task schema instead of the legacy generic checklist", (dayNumber) => {
    shellStateRef.current = {
      program: { ...program, current_day: dayNumber },
      readOnly: false,
      refreshProgram: vi.fn(),
      syncProgram: vi.fn(),
    };

    render(<NutritionProgramDayPage dayNumber={dayNumber} />);

    expect(screen.getByRole("heading", { name: /To Do hari ini/i })).toBeInTheDocument();
    expect(screen.getAllByText("3 waktu makan").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Tanpa memaksa").length).toBeGreaterThan(0);
    expect(screen.getAllByText("1 kesempatan").length).toBeGreaterThan(0);
    expect(screen.getByText("Berapa kali?")).toBeInTheDocument();
    expect(screen.queryByText(/Today'?s Checklist/i)).not.toBeInTheDocument();
  });

  it("keeps result input state scoped to the selected persisted day id", () => {
    const onRefresh = vi.fn();
    const { rerender } = render(<NutritionProgramDailyWorkspace program={program} day={day2} onProgramRefresh={onRefresh} />);
    const input = screen.getByLabelText(/Hasil aktual Catat waktu makan/i);
    fireEvent.change(input, { target: { value: "2" } });
    expect(input).toHaveValue(2);

    rerender(<NutritionProgramDailyWorkspace program={program} day={day3} onProgramRefresh={onRefresh} />);
    expect(screen.getByLabelText(/Hasil aktual Catat waktu makan/i)).toHaveValue(null);
  });

  it("keeps responsive-feeding semantics while hiding per-question percentages", () => {
    render(<NutritionProgramDailyWorkspace program={program} day={day2} onProgramRefresh={vi.fn()} />);
    const group = screen.getByRole("group", { name: "Dilakukan?" });
    const article = group.closest("article");
    expect(article).not.toBeNull();

    fireEvent.click(within(group).getByRole("button", { name: "Ya" }));
    expect(within(article as HTMLElement).getByText(/^Target tercapai$/i)).toBeInTheDocument();
    expect(within(article as HTMLElement).queryByText(/100%/i)).not.toBeInTheDocument();

    fireEvent.click(within(group).getByRole("button", { name: "Tidak" }));
    expect(within(article as HTMLElement).getByText(/^Target belum tercapai$/i)).toBeInTheDocument();
    expect(within(article as HTMLElement).queryByText(/0%/i)).not.toBeInTheDocument();
  });
});
