import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NutritionFinalResult } from "@/components/nutrition-final-result";
import { NutritionProgramShell, useNutritionProgramShell } from "@/components/nutrition-program-shell";
import { NutritionProgramDayPage } from "@/components/nutrition-program-day-page";
import { HistoryVisualCard } from "@/components/nutrition-program-ui";
import { ProgramCountdown } from "@/components/program-countdown";

const authState = { status: "authenticated" as "authenticated" | "unauthenticated", user: { id: "u1", email: "care@example.com", created_at: "2026-09-23T00:00:00Z" } };
vi.mock("@/components/auth-provider", () => ({ useAuth: () => ({ ...authState, refreshAuth: vi.fn(), logout: vi.fn() }) }));

const { routerPush, routerReplace, routerRefresh, cancelProgram, resumeProgram, getProgram } = vi.hoisted(() => ({
  routerPush: vi.fn(),
  routerReplace: vi.fn(),
  routerRefresh: vi.fn(),
  cancelProgram: vi.fn(),
  resumeProgram: vi.fn(),
  getProgram: vi.fn(),
}));

vi.mock("@/lib/nutrition-program", async () => {
  const actual = await vi.importActual<typeof import("@/lib/nutrition-program")>("@/lib/nutrition-program");
  return { ...actual, cancelNutritionProgram: cancelProgram, resumeNutritionProgram: resumeProgram, getNutritionProgram: getProgram };
});

vi.mock("next/navigation", () => ({
  usePathname: () => "/nutrition/program/p1/progress",
  useRouter: () => ({
    push: routerPush,
    replace: routerReplace,
    refresh: routerRefresh,
  }),
}));

const goal = { id: "g1", goal_key: "meal_routine", title: "Rutinitas makan", description: "Rutinitas makan teratur", baseline: 0, target: 10, actual: 4, unit: "successful target days", measurement_method: "daily metric", duration_days: 14, priority: 1, status: "PARTIALLY_MET", progress_percentage: 40, remaining_gap: 6 };
const days = [
  { id: "d1", day_number: 1, focus: "Baseline", status: "COMPLETED" as const, unlock_at: "2026-09-23T00:00:00Z", remaining_seconds: 0, recommended_action: "", meal_guidance: "", action_details: {}, meal_guidance_details: {}, reference_notes: [], checklist: [], checklist_state: [], food_group_state: [], completed: true, completed_at: "2026-09-23T00:10:00Z", locked: false, missed: false },
  { id: "d2", day_number: 2, focus: "Responsive feeding", status: "AVAILABLE" as const, unlock_at: "2026-09-23T00:01:00Z", remaining_seconds: 0, recommended_action: "", meal_guidance: "", action_details: {}, meal_guidance_details: {}, reference_notes: [], checklist: [], checklist_state: [], food_group_state: [], completed: false, completed_at: null, locked: false, missed: false },
  { id: "d3", day_number: 3, focus: "Variasi", status: "LOCKED" as const, unlock_at: "2026-09-23T00:02:00Z", remaining_seconds: 59, recommended_action: "", meal_guidance: "", action_details: {}, meal_guidance_details: {}, reference_notes: [], checklist: [], checklist_state: [], food_group_state: [], completed: false, completed_at: null, locked: true, missed: false },
];
const program = { id: "p1", stage: "toddler", title: "Toddler Guided Program", status: "ACTIVE", duration_days: 14, cycle_number: 1, parent_program_id: null, created_at: "2026-09-23T00:00:00Z", started_at: "2026-09-23T00:00:00Z", ends_at: "2026-10-06T00:00:00Z", completed_at: null, cancelled_at: null, current_day: 2, days_completed: 1, completed_tasks: 3, total_tasks: 42, progress_percent: 7.14, time_elapsed_days: 2, missed_days: 0, inactive_days: 0, last_activity_at: "2026-09-23T00:00:00Z", goal, cumulative_goal: null, profile: { stage: "toddler" }, assessment_snapshot: {}, recommendation: {} as never, goals: [goal], days, extension_history: [] };

function PauseProgramTrigger() {
  const { setProgram } = useNutritionProgramShell();
  return <button type="button" onClick={() => setProgram((current) => current ? { ...current, status: "PAUSED" } : current)}>Trigger pause</button>;
}

function SafetyProgramTrigger() {
  const { setProgram } = useNutritionProgramShell();
  return <button type="button" onClick={() => setProgram((current) => current ? { ...current, status: "SAFETY_HOLD" } : current)}>Trigger safety hold</button>;
}

beforeEach(() => {
  authState.status = "authenticated";
  authState.user = { id: "u1", email: "care@example.com", created_at: "2026-09-23T00:00:00Z" };
  routerPush.mockClear();
  routerReplace.mockClear();
  routerRefresh.mockClear();
  cancelProgram.mockReset();
  cancelProgram.mockResolvedValue({ status: "CANCELLED" });
  resumeProgram.mockReset();
  getProgram.mockReset();
  resumeProgram.mockResolvedValue({ ...program, status: "ACTIVE" });
  getProgram.mockResolvedValue(program);
  sessionStorage.clear();
});
afterEach(() => { vi.useRealTimers(); });

describe("Nutrition Program final shell", () => {
  it("keeps program navigation visible with progress active and server countdown context", () => {
    render(<NutritionProgramShell programId="p1" active="progress" initialProgram={program as never}><div>Progress content</div></NutritionProgramShell>);
    expect(screen.getByText("Progress content")).toBeInTheDocument();
    const progressLinks = screen.getAllByRole("link", { name: "Progres" });
    expect(progressLinks.some((item) => item.getAttribute("aria-current") === "page")).toBe(true);
    expect(screen.getByText(/Panduan berikutnya/i)).toBeInTheDocument();
    expect(screen.getAllByText(/\d+m \d+s/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Hari 3/i).length).toBeGreaterThan(0);
  });


  it("uses the user program name as the primary heading and category as secondary context", () => {
    const named = { ...program, title: "Rutinitas Makan Raka" };
    render(<NutritionProgramShell programId="p1" active="today" initialProgram={named as never}><div>Today content</div></NutritionProgramShell>);
    expect(screen.getByRole("heading", { level: 1, name: "Rutinitas Makan Raka" })).toBeInTheDocument();
    expect(screen.getByText(/Program Toddler · 14 hari/i)).toBeInTheDocument();
    expect(screen.queryByText(/Toddler Guided Program · Cycle/i)).not.toBeInTheDocument();
  });

  it("keeps elderly chronic-condition context visible without changing program state", () => {
    const elderly = { ...program, stage: "elderly", title: "Program Lansia", assessment_snapshot: { has_condition: true, conditions: ["diabetes", "other"], other_condition: "Osteoporosis" } };
    render(<NutritionProgramShell programId="p1" active="today" initialProgram={elderly as never}><div>Elderly content</div></NutritionProgramShell>);
    expect(screen.getByText(/Konteks kesehatan/i)).toBeInTheDocument();
    expect(screen.getByText("Diabetes")).toBeInTheDocument();
    expect(screen.getByText("Osteoporosis")).toBeInTheDocument();
    expect(screen.getByText("ACTIVE")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /Program sedang dijeda/i })).not.toBeInTheDocument();
  });

  it("uses a local horizontal day timeline and keeps locked days in the workspace", () => {
    render(<NutritionProgramShell programId="p1" active="today" initialProgram={program as never}><h2>Guidance hari ini</h2></NutritionProgramShell>);

    expect(screen.getByRole("link", { name: /^Hari Ini$/i })).toHaveAttribute("href", "/nutrition/program/p1");
    expect(screen.getByRole("link", { name: /Hari ini, Hari 2/i })).toHaveAttribute("href", "/nutrition/program/p1");
    expect(screen.getByTestId("day-timeline-scroll")).toHaveClass("overflow-x-auto");
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);

    const lockedDayLink = screen.getByRole("link", { name: /Lihat Hari 3, terkunci/i });
    expect(lockedDayLink).toHaveAttribute("href", "/nutrition/program/p1/day/3");
    fireEvent.click(lockedDayLink);
    expect(screen.getByText(/Hari 3 belum terbuka/i)).toBeInTheDocument();
  });


  it("never renders editable controls for a future day even if its legacy locked boolean is stale", () => {
    const futureAvailable = { ...days[2], status: "AVAILABLE" as const, locked: false, checklist: ["Future action"], checklist_state: [false] };
    const guarded = { ...program, days: [days[0], days[1], futureAvailable], current_day: 2 };
    render(<NutritionProgramShell programId="p1" active="today" initialProgram={guarded as never}><NutritionProgramDayPage dayNumber={3} /></NutritionProgramShell>);

    expect(screen.getByRole("heading", { name: /Belum tersedia/i })).toBeInTheDocument();
    expect(screen.getAllByText(/Hari 3/i).length).toBeGreaterThan(0);
    expect(screen.queryByText("Future action")).not.toBeInTheDocument();
    expect(screen.queryByRole("spinbutton")).not.toBeInTheDocument();
  });


  it("shows a one-time notifier when an active program transitions to paused", () => {
    render(<NutritionProgramShell programId="p1" active="today" initialProgram={program as never}><PauseProgramTrigger /></NutritionProgramShell>);

    expect(screen.queryByRole("heading", { name: /Program dijeda sementara/i })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Trigger pause/i }));

    expect(screen.getByRole("heading", { name: /Program dijeda sementara/i })).toBeInTheDocument();
    expect(screen.getByText(/Progress yang sudah dicatat tetap tersimpan/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /^Program sedang dijeda$/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Mengerti/i }));
    expect(screen.queryByRole("heading", { name: /Program dijeda sementara/i })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /^Program sedang dijeda$/i })).toBeInTheDocument();
  });

  it("keeps a paused current day visible and resumes only after the recovery choice", async () => {
    const pausedDays = [days[0], { ...days[1], status: "IN_PROGRESS" as const, checklist: ["A", "B"], checklist_state: [true, false] }, days[2]];
    const pausedProgram = { ...program, status: "PAUSED", current_day: 2, days: pausedDays };
    const activeProgram = { ...pausedProgram, status: "ACTIVE" };
    resumeProgram.mockResolvedValueOnce({ ...pausedProgram, status: "PAUSED" });
    getProgram.mockResolvedValueOnce(pausedProgram);

    render(<NutritionProgramShell programId="p1" active="today" initialProgram={pausedProgram as never}><div>Paused content</div></NutritionProgramShell>);

    expect(screen.getByRole("heading", { name: /Program sedang dijeda/i })).toBeInTheDocument();
    expect(screen.getByText(/Progress yang sudah dilakukan tetap tersimpan/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Lanjutkan Program/i }));
    expect(screen.getByRole("heading", { name: /Bagaimana kondisi sekarang/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Masih kurang sehat/i }));
    await waitFor(() => expect(resumeProgram).toHaveBeenCalledWith("p1", "still_unwell"));
    expect(await screen.findByText(/Program tetap dijeda/i)).toBeInTheDocument();

    resumeProgram.mockResolvedValueOnce({ ...activeProgram, status: "ACTIVE" });
    getProgram.mockResolvedValueOnce(activeProgram);
    fireEvent.click(screen.getByRole("button", { name: /Lanjutkan Program/i }));
    fireEvent.click(screen.getByRole("button", { name: /Sudah membaik/i }));
    await waitFor(() => expect(resumeProgram).toHaveBeenCalledWith("p1", "improved"));
    await waitFor(() => expect(routerPush).toHaveBeenCalledWith("/nutrition/program/p1/day/2"));
  });

  it("shows an urgent hospital notifier when an active program transitions into SAFETY_HOLD", () => {
    render(<NutritionProgramShell programId="p1" active="today" initialProgram={program as never}><SafetyProgramTrigger /></NutritionProgramShell>);
    fireEvent.click(screen.getByRole("button", { name: /Trigger safety hold/i }));
    const dialog = screen.getByRole("dialog", { name: /Segera bawa anak ke IGD atau rumah sakit/i });
    expect(dialog).toHaveTextContent(/input yang baru disimpan memenuhi aturan tanda bahaya/i);
    fireEvent.click(within(dialog).getByRole("button", { name: /Mengerti/i }));
    expect(screen.getByRole("heading", { name: /Segera bawa anak ke IGD atau rumah sakit/i })).toBeInTheDocument();
  });

  it("shows an emergency-only safety hold with reassessment as the single next step", async () => {
    const held = { ...program, status: "SAFETY_HOLD" };
    sessionStorage.setItem("sehatin:nutrition-result:toddler", "stale-result");

    render(<NutritionProgramShell programId="p1" active="progress" initialProgram={held as never}><div>Held content</div></NutritionProgramShell>);

    expect(screen.getByRole("heading", { name: /Segera bawa anak ke IGD atau rumah sakit/i })).toBeInTheDocument();
    expect(screen.getByText(/Program dihentikan dan tidak akan melanjutkan adaptasi otomatis/i)).toBeInTheDocument();
    expect(screen.getByText(/asesmen SEHATIN dari awal/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Perkecil goal/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Ubah goal/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: /Goal pengganti/i })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Ulangi asesmen/i }));

    await waitFor(() => expect(cancelProgram).toHaveBeenCalledWith("p1"));
    await waitFor(() => expect(routerPush).toHaveBeenCalledWith("/nutrition/toddler"));
    expect(sessionStorage.getItem("sehatin:nutrition-result:toddler")).toBeNull();
  });

  it("fires countdown expiry once and never displays negative time", () => {
    vi.useFakeTimers();
    const expired = vi.fn();
    render(<ProgramCountdown seconds={1} onExpire={expired} />);
    act(() => { vi.advanceTimersByTime(1500); });
    expect(expired).toHaveBeenCalledTimes(1);
    expect(screen.getByText("0m 0s")).toBeInTheDocument();
  });

  it("redirects final result to the public homepage after logout without exposing a private snapshot", () => {
    authState.status = "unauthenticated";
    authState.user = null as never;

    const result = {
      program: {
        ...program,
        status: "COMPLETED",
        completed_at: "2026-10-06T00:00:00Z",
        days_completed: 14,
        progress_percent: 100,
      },
      cycle: 1,
      duration_days: 14,
      goal: { ...goal, actual: 7, progress_percentage: 70 },
      baseline: 0,
      target: 10,
      actual: 7,
      goal_status: "PARTIALLY_MET",
      goal_achievement_percent: 70,
      program_completion_percent: 100,
      program_numbers: {
        completed_days: 14,
        missed_days: 0,
        logged_days: 13,
      },
      what_accomplished: ["Rutinitas membaik"],
      what_changed: "Plan menyesuaikan daily log.",
      what_worked_well: ["Responsif"],
      challenges: ["Perlu waktu"],
      adaptation_history: [
        {
          day: 2,
          decision: "CONTINUE",
          user_facing_reason: "Stabil",
        },
      ],
      trends: {},
      safety_notes: [],
      next_step: {
        decision: "EXTEND",
        can_extend: true,
        can_reframe: false,
        message: "Lanjutkan 7 hari.",
      },
      extension_history: [],
      generated_at: "2026-10-06T00:00:00Z",
    };

    render(
      <NutritionFinalResult
        programId="p1"
        initialResult={result as never}
      />,
    );

    expect(routerReplace).toHaveBeenCalledWith("/");
    expect(screen.queryByText("Toddler Guided Program")).not.toBeInTheDocument();
  });

  it("makes the whole history card a keyboard-accessible destination", () => {
    const completed = { ...program, status: "COMPLETED", completed_at: "2026-10-06T00:00:00Z" };
    render(<HistoryVisualCard program={completed as never} />);
    expect(screen.getByRole("link", { name: /Toddler Guided Program, cycle 1, buka Final Program Result/i })).toHaveAttribute("href", "/nutrition/program/p1/result");
  });
});

