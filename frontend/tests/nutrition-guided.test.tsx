import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import HomePage from "@/app/page";
import { AuthGate } from "@/components/auth-gate";
import { AuthProvider } from "@/components/auth-provider";
import { Navbar } from "@/components/layout";
import { NutritionAssessment } from "@/components/nutrition-assessment";
import { NutritionHistory } from "@/components/nutrition-history";
import { NutritionFinalResult } from "@/components/nutrition-final-result";
import { NutritionProgramDayDetail } from "@/components/nutrition-program-day-detail";
import { NutritionProgramDailyWorkspace } from "@/components/nutrition-program-daily-workspace";
import { NutritionProgramShell } from "@/components/nutrition-program-shell";
import { NutritionProgramDetail } from "@/components/nutrition-program-detail";
import { resolveNutritionResultCta } from "@/components/nutrition-result";
import { apiFetch, ApiError } from "@/lib/api";
import { getCurrentUser } from "@/lib/auth";
import { type NutritionAssessmentPayload, type NutritionResult as NutritionResultData } from "@/lib/nutrition";

const push = vi.fn();
const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace }),
  usePathname: () => "/nutrition/program",
}));
vi.mock("@/components/program-countdown", () => ({
  ProgramCountdown: ({ seconds, className = "" }: { seconds: number; className?: string }) => (
    <span className={className}>{Math.max(0, Math.ceil(seconds / 60))}m</span>
  ),
}));
vi.mock("@/lib/api", () => ({
  API_BASE: "http://localhost:8000",
  SESSION_EXPIRED_EVENT: "sehatin:session-expired",
  ApiError: class ApiError extends Error {
    status: number; code?: string;
    constructor(message: string, status = 0, code?: string) { super(message); this.status = status; this.code = code; }
  },
  apiFetch: vi.fn(),
}));
const mocked = vi.mocked(apiFetch);

const user = { id: "u1", email: "care@example.com", created_at: "2026-09-16T00:00:00Z" };
const goal = {
  id: "g1", goal_key: "daily_consistency", title: "Rutinitas makan", description: "Jalankan panduan secara konsisten.",
  baseline: 0, target: 10, actual: 0, unit: "completed days", measurement_method: "daily checklist completion",
  duration_days: 14, priority: 1, status: "NOT_STARTED", progress_percentage: 0, remaining_gap: 10,
};
const summary = {
  id: "p1", stage: "toddler", title: "Healthy Eating Habit Plan", status: "ACTIVE", duration_days: 14, cycle_number: 1,
  parent_program_id: null, created_at: "2026-09-16T08:00:00Z", started_at: "2026-09-16T08:00:00Z", ends_at: "2026-09-29T08:00:00Z",
  completed_at: null, cancelled_at: null, current_day: 1, days_completed: 0, completed_tasks: 0, total_tasks: 42,
  progress_percent: 0, time_elapsed_days: 1, missed_days: 0, inactive_days: 0, last_activity_at: "2026-09-16T08:00:00Z", goal, cumulative_goal: null,
};

const toddlerAssessment: NutritionAssessmentPayload = { stage: "toddler", age_months: 36, sex: "female", weight_kg: 14, height_cm: 95 };
const toddlerResult: NutritionResultData = {
  stage: "toddler", category: "Toddler", age_band: "3 years", personalization_status: "personalized_education",
  validation: { status: "VALID", can_process: true, message: "Data dapat diproses", issues: [], indicators: [], references: [] },
  input_summary: ["Usia 36 bulan", "Berat 14 kg"], summary: "Panduan edukatif untuk pola makan balita.",
  estimated_needs: { energy: "Estimasi edukatif" }, meal_pattern: { routine: "3 meals + planned snacks" }, priority_nutrients: ["Protein"],
  food_groups: ["Protein", "Sayur dan buah"], recommendations: ["Jaga ritme makan yang konsisten."], sample_menu: ["Nasi, telur, sayur, buah"],
  guidance: ["Tawarkan makanan tanpa memaksa."], safety_notes: ["Sesuaikan tekstur dan awasi saat makan."], disclaimer: "Informasi umum, bukan diagnosis.",
  references: ["WHO guidance"], suggested_goals: [{ goal_key: "daily_consistency", title: "Rutinitas makan", description: "Jalankan panduan secara konsisten.", baseline: 0, target: 10, unit: "completed days", measurement_method: "daily checklist completion", duration: 14, priority: 1, status: "NOT_STARTED" }],
};

const baselineTasks = [
  { key: "meal_routine_d1", id: "meal_routine_d1", metric: "meal_routine", metric_id: "meal_routine", input_type: "count" as const, target_value: 3, unit: "makan utama", target_label: "3 waktu makan utama terjadwal hari ini.", action_text: "Catat berapa waktu makan utama yang benar-benar berlangsung hari ini.", result_prompt: "Berapa waktu makan utama yang benar-benar berlangsung?", mode: "baseline_observation", evidence_rule: { source_name: "NICE", source_url: "https://example.test/nice", rule_kind: "product_operationalization" } },
  { key: "vegetable_fruit_exposure_d1", id: "vegetable_fruit_exposure_d1", metric: "vegetable_fruit_exposure", metric_id: "vegetable_fruit_exposure", input_type: "count" as const, target_value: 1, unit: "kesempatan", target_label: "Minimal 1 kesempatan mencoba sayur atau buah hari ini.", action_text: "Catat berapa kesempatan sayur atau buah benar-benar ditawarkan hari ini.", result_prompt: "Berapa kesempatan sayur/buah benar-benar ditawarkan?", mode: "baseline_observation" },
  { key: "food_response_d1", id: "food_response_d1", metric: "food_response", metric_id: "food_response", input_type: "choice" as const, target_value: "accepted", unit: "respons", target_label: "Catat respons terhadap satu paparan makanan fokus.", action_text: "Catat respons anak pada satu paparan makanan fokus hari ini.", result_prompt: "Bagaimana respons anak pada paparan makanan fokus hari ini?", mode: "baseline_observation", options: [{ value: "accepted", label: "Diterima" }, { value: "partial", label: "Sebagian" }, { value: "refused", label: "Ditolak" }], adherence_map: { accepted: 100, partial: 50, refused: 0 } },
];

const availableDay = {
  id: "d1", day_number: 1, focus: "Ritme makan", status: "AVAILABLE" as const, unlock_at: "2026-09-16T08:00:00Z", remaining_seconds: 0,
  recommended_action: "Catat pola makan hari ini sebagai baseline.", meal_guidance: "Sediakan makan utama seimbang.",
  action_details: { why: "Mendukung konsistensi.", action: "Catat pola makan.", when: "Hari ini", how: "Isi hasil aktual.", completion_criteria: "Action dan hasil tersimpan.", tasks: baselineTasks, task_results: {} },
  meal_guidance_details: { occasion: "Main meal", example: "Nasi, telur, sayur", food_groups: ["Protein"], preparation: "Sajikan sesuai toleransi.", substitutions: "Gunakan bahan setara." },
  reference_notes: ["WHO guidance"], checklist: baselineTasks.map((task) => task.action_text), checklist_state: [false, false, false],
  food_group_state: [false, false, false, false, false], has_complaint: null, complaint_note: null,
  completed: false, completed_at: null, locked: false, missed: false, meal_label: null, meal_notes: null,
};
const lockedDay = {
  id: "d2", day_number: 2, focus: "Variasi pangan", status: "LOCKED" as const, unlock_at: "2026-09-17T08:00:00Z", remaining_seconds: 3600,
  recommended_action: "", meal_guidance: "", action_details: {}, meal_guidance_details: {}, reference_notes: [], checklist: [], checklist_state: [],
  food_group_state: [], has_complaint: null, complaint_note: null,
  completed: false, completed_at: null, locked: true, missed: false, meal_label: null, meal_notes: null,
};
const programDetail = { ...summary, profile: { stage: "toddler" }, assessment_snapshot: toddlerAssessment, recommendation: toddlerResult, goals: [goal], days: [availableDay, lockedDay], extension_history: [summary] };
const availableDayDetail = { program_id: "p1", program_title: summary.title, program_status: "ACTIVE", duration_days: 14, current_day: 1, progress_percent: 0, missed_days: 0, inactive_days: 0, last_activity_at: summary.last_activity_at, goal, cumulative_goal: null, day: availableDay };
const lockedDayDetail = { ...availableDayDetail, progress_percent: 7.14, day: lockedDay };

async function flushAction(action: () => void) {
  await act(async () => {
    action();
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
  });
}

function withProvider(node: React.ReactNode, initialUser: typeof user | null = user) { return render(<AuthProvider initialUser={initialUser} autoRefresh={false}>{node}</AuthProvider>); }

beforeEach(() => { mocked.mockReset(); push.mockReset(); replace.mockReset(); sessionStorage.clear(); });
afterEach(() => { cleanup(); vi.useRealTimers(); });

describe("nutrition guided program UX/state", () => {
  it("shows a neutral account trigger while logged out without inventing a guest profile", async () => {
    mocked.mockRejectedValue(new ApiError("Login diperlukan", 401));
    await expect(getCurrentUser()).rejects.toMatchObject({ status: 401 });
    expect(mocked).toHaveBeenCalledWith("/api/auth/me");
    withProvider(<Navbar />, null);
    const accountTrigger = screen.getAllByRole("button", { name: /^Akun$/i })[0];
    expect(accountTrigger).toBeInTheDocument();
    fireEvent.click(accountTrigger);
    expect(screen.getByText("Akun SEHATIN")).toBeInTheDocument();
    expect(screen.queryByText(/Guest Profile/i)).not.toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /^Sign in$/i })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /^Create account$/i })).toBeInTheDocument();
  });

  it("shows a personal nutrition overview on the authenticated homepage", async () => {
    mocked.mockImplementation(async (path: string) => {
      if (path === "/api/auth/me") return user as never;
      if (path === "/api/nutrition/program") return [summary] as never;
      throw new Error(`Unexpected API call: ${path}`);
    });
    withProvider(<HomePage />);
    expect(await screen.findByRole("heading", { name: /Halo, Care\./i })).toBeInTheDocument();
    expect(await screen.findByText(/Program sedang berjalan/i)).toBeInTheDocument();
    expect(screen.getByText(/Program Toddler/i)).toBeInTheDocument();
    expect(screen.getByText(/Lanjutkan program/i)).toBeInTheDocument();
  });

  it("shows the real authenticated profile trigger only after /auth/me succeeds", async () => {
    mocked.mockImplementation(async (path: string) => {
      if (path === "/api/auth/me") return user as never;
      throw new Error(`Unexpected path ${path}`);
    });
    expect(await getCurrentUser()).toEqual(user);
    expect(mocked).toHaveBeenCalledWith("/api/auth/me");
    withProvider(<Navbar />, user);
    expect(screen.getAllByRole("button", { name: /Profile care@example.com/i })[0]).toBeInTheDocument();
    expect(screen.queryByText(/Guest/i)).not.toBeInTheDocument();
  });

  it("requires explicit save consent before contextual login/register can continue", async () => {
    mocked.mockRejectedValue(new ApiError("Login diperlukan", 401));
    const done = vi.fn();
    withProvider(<AuthGate open requireSaveConsent onClose={() => {}} onAuthenticated={done} />, null);
    const button = screen.getByRole("button", { name: /^(?:Login & Continue|Masuk & Lanjutkan)$/i });
    expect(button).toBeDisabled();
    expect(screen.getByText(/Centang konfirmasi untuk melanjutkan/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("checkbox"));
    expect(button).toBeEnabled();
    fireEvent.click(screen.getByRole("checkbox"));
    expect(button).toBeDisabled();
  });

  it("clears stale assessment validation immediately as required fields become valid", async () => {
    mocked.mockImplementation(async (path: string) => {
      if (path === "/api/nutrition/validate") return { status: "VALID", can_process: true, message: "Data dapat diproses", issues: [], indicators: [], references: [] } as never;
      throw new Error(`Unexpected path ${path}`);
    });
    render(<NutritionAssessment stage="toddler" />);
    fireEvent.change(screen.getByLabelText(/Tanggal lahir/i), { target: { value: "2023-09-24" } });
    fireEvent.click(screen.getByRole("button", { name: /Lanjut/i }));
    expect(screen.getByText("Periksa assessment")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/Jenis kelamin/i), { target: { value: "female" } });
    fireEvent.change(screen.getByLabelText(/Berat badan/i), { target: { value: "14" } });
    fireEvent.change(screen.getByLabelText(/Panjang\/Tinggi badan/i), { target: { value: "95" } });
    // fireEvent is wrapped in React act() by Testing Library, so the local
    // validation effect has already been flushed here. No polling/timer needed.
    expect(screen.queryByText("Periksa assessment")).not.toBeInTheDocument();
  });

  it("uses contextual result CTAs based on actual auth/program state", () => {
    const guest = resolveNutritionResultCta("unauthenticated", null, false);
    expect(guest).toMatchObject({
      loading: false,
      title: "Simpan & Mulai Guided Program",
      button: "Simpan & Mulai Guided Program",
    });

    const authenticated = resolveNutritionResultCta("authenticated", null, false);
    expect(authenticated).toMatchObject({
      loading: false,
      title: "Mulai Guided Program",
      button: "Mulai Guided Program",
    });

    const activeProgram = resolveNutritionResultCta("authenticated", summary, false);
    expect(activeProgram).toMatchObject({
      loading: false,
      title: "Program aktif sudah tersedia.",
      button: "Pilih program",
    });

    expect(resolveNutritionResultCta("authenticated", null, true).loading).toBe(true);
  });

  it("renders the program day workspace with horizontal day journey and current-day guidance", () => {
    withProvider(<NutritionProgramDetail programId="p1" initialProgram={programDetail} />);

    expect(screen.getByText("Program Toddler")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: summary.title })).toBeInTheDocument();
    expect(screen.getByText(/Hari 1 dari 14/i)).toBeInTheDocument();

    const journey = screen.getByRole("region", { name: /Perjalanan hari program/i });
    expect(journey).toBeInTheDocument();

    const dayOne = screen.getByRole("link", { name: /Hari 1: Hari ini/i });
    expect(dayOne).toHaveAttribute("href", "/nutrition/program/p1/day/1");

    const dayTwo = screen.getByRole("link", { name: /Hari 2: Terkunci/i });
    expect(dayTwo).toHaveAttribute("href", "#");
    expect(dayTwo).toHaveAttribute("aria-disabled", "true");

    expect(screen.getByRole("heading", { name: /To Do hari ini/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Hasil hari ini/i })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /Hari selesai/i })).not.toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: /0 dari 3 aktivitas selesai/i })).toBeInTheDocument();
    expect(screen.queryByText("Ikuti tindakan utama hari ini")).not.toBeInTheDocument();
    expect(screen.queryByText("Terapkan meal guidance pada waktu makan yang sesuai")).not.toBeInTheDocument();
  });

  it("keeps action completion separate from count, boolean, and choice results", () => {
    const measurableDay = {
      ...availableDay,
      checklist: ["Jaga tiga waktu makan", "Hindari minuman berpemanis", "Catat respons makanan"],
      checklist_state: [false, false, false],
      action_details: {
        ...availableDay.action_details,
        tasks: [
          { key: "meal_routine_d1", id: "meal_routine_d1", metric: "meal_routine", metric_id: "meal_routine", input_type: "count" as const, target_value: 3, unit: "makan utama", target_label: "3 waktu makan utama", action_text: "Jaga tiga waktu makan", result_prompt: "Berapa waktu makan utama yang berlangsung?", evidence_rule: { source_name: "NICE", source_url: "https://example.test/nice", rule_kind: "product_operationalization" } },
          { key: "sweet_beverage_d1", id: "sweet_beverage_d1", metric: "sweet_beverage", metric_id: "sweet_beverage", input_type: "boolean" as const, target_value: false, unit: "hari", target_label: "Tidak ada minuman berpemanis", action_text: "Hindari minuman berpemanis", result_prompt: "Apakah minuman berpemanis ditawarkan hari ini?" },
          { key: "food_response_d1", id: "food_response_d1", metric: "food_response", metric_id: "food_response", input_type: "choice" as const, target_value: "accepted", unit: "respons", target_label: "Catat respons", action_text: "Catat respons makanan", result_prompt: "Bagaimana respons anak?", options: [{ value: "accepted", label: "Diterima" }, { value: "partial", label: "Sebagian" }, { value: "refused", label: "Ditolak" }], adherence_map: { accepted: 100, partial: 50, refused: 0 } },
        ],
        task_results: {},
      },
    };
    const measurableProgram = { ...programDetail, days: [measurableDay, lockedDay] };
    withProvider(<NutritionProgramDetail programId="p1" initialProgram={measurableProgram} />);

    const countInput = screen.getByRole("spinbutton", { name: /Hasil aktual Jaga tiga waktu makan/i });
    expect(countInput).toHaveValue(null);
    fireEvent.click(screen.getByRole("button", { name: /Tandai tindakan: Jaga tiga waktu makan/i }));
    expect(countInput).toHaveValue(null);
    fireEvent.change(countInput, { target: { value: "2" } });
    expect(screen.getAllByText(/Sebagian tercapai/i).length).toBeGreaterThan(0);

    const booleanGroup = screen.getByRole("group", { name: /Apakah minuman berpemanis ditawarkan hari ini/i });
    fireEvent.click(within(booleanGroup).getByRole("button", { name: /^Tidak$/i }));
    expect(within(booleanGroup).getByRole("button", { name: /^Tidak$/i })).toHaveAttribute("aria-pressed", "true");

    const choiceGroup = screen.getByRole("group", { name: /Bagaimana respons anak/i });
    fireEvent.click(within(choiceGroup).getByRole("button", { name: /Sebagian/i }));
    expect(within(choiceGroup).getByRole("button", { name: /Sebagian/i })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("heading", { name: /Hasil hari ini/i })).toBeInTheDocument();
    expect(screen.queryByText(/2 \/ 3 makan utama/i)).not.toBeInTheDocument();
    expect(countInput).toHaveValue(2);
  });

  it("renders the adaptive quick daily log with fast caregiver inputs", () => {
    withProvider(<NutritionProgramDetail programId="p1" initialProgram={programDetail} />);
    expect(screen.getByRole("heading", { name: /Catat sesi hari ini/i })).toBeInTheDocument();
    const portion = screen.getByRole("group", { name: /^Porsi$/i });
    fireEvent.click(within(portion).getByRole("button", { name: /Sebagian/i }));
    expect(within(portion).getByRole("button", { name: /Sebagian/i })).toHaveAttribute("aria-pressed", "true");
    const acceptance = screen.getByRole("group", { name: /^Penerimaan$/i });
    fireEvent.click(within(acceptance).getByRole("button", { name: /^Suka$/i }));
    expect(within(acceptance).getByRole("button", { name: /^Suka$/i })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("group", { name: /Kondisi anak/i })).toBeInTheDocument();
    const reaction = screen.getByRole("group", { name: /Reaksi tidak biasa/i });
    expect(screen.queryByLabelText(/Jelaskan reaksi tidak biasa/i)).not.toBeInTheDocument();
    fireEvent.click(within(reaction).getByRole("button", { name: /^Ada$/i }));
    expect(screen.getByLabelText(/Jelaskan reaksi tidak biasa/i)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/Jelaskan reaksi tidak biasa/i), { target: { value: "muncul ruam ringan" } });
    expect(screen.getByDisplayValue("muncul ruam ringan")).toBeInTheDocument();
    fireEvent.click(within(reaction).getByRole("button", { name: /^Tidak ada$/i }));
    expect(screen.queryByLabelText(/Jelaskan reaksi tidak biasa/i)).not.toBeInTheDocument();
  });

  it("shows Stage 7 what changed, why, and what next without engine jargon", () => {
    const adaptiveDay = {
      ...availableDay,
      action_details: {
        ...availableDay.action_details,
        adaptation: {
          decision: "EASE",
          reason_code: "HIGH_BURDEN_LOW_ADHERENCE",
          user_facing_reason: "Beberapa sesi terakhir terasa lebih sulit. Rencana berikutnya dibuat lebih ringan tanpa mengganti goal utama.",
          explanation: {
            what_changed: "Kompleksitas rencana berikutnya diturunkan.",
            why: "Beberapa sesi terakhir terasa lebih sulit.",
            what_next: "Fokus pada langkah inti yang lebih ringan sambil mempertahankan goal utama.",
          },
          rule_version: { id: "nutrition_adaptive_rules_v2", version: "2.0.0" },
        },
        daily_summary: {
          what_went_well: "Daily log tersimpan.",
          what_was_difficult: "Beberapa langkah masih sulit dijalankan.",
          tomorrow_preview: "Fokus lebih ringan besok.",
        },
      },
    };
    const adaptiveProgram = { ...programDetail, days: [adaptiveDay, lockedDay] };
    withProvider(<NutritionProgramDetail programId="p1" initialProgram={adaptiveProgram} />);

    expect(screen.getByText("Apa berubah?")).toBeInTheDocument();
    expect(screen.getByText("Kenapa?")).toBeInTheDocument();
    expect(screen.getByText("Apa berikutnya?")).toBeInTheDocument();
    expect(screen.getByText(/Kompleksitas rencana berikutnya diturunkan/i)).toBeInTheDocument();
    expect(screen.getByText(/Fokus pada langkah inti yang lebih ringan/i)).toBeInTheDocument();
    expect(screen.queryByText(/reason_code/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/SPH|SPoH|SKG/i)).not.toBeInTheDocument();
  });

  it("shows an emergency hospital warning only after backend classifies reaction text as a red flag", async () => {
    mocked.mockImplementation(async (path: string, init?: RequestInit) => {
      if (path === "/api/nutrition/program/p1/daily-log" && init?.method === "POST") return {
        program_id: "p1", saved: true, saved_at: "2026-09-16T09:00:00Z", day_number: 1, day_completed: false, day_completed_at: null,
        checklist_state: [true, true, true], food_group_state: [], has_complaint: false, complaint_note: null, task_results: { meal_routine_d1: "3", vegetable_fruit_exposure_d1: "1", food_response_d1: "accepted" },
        days_completed: 0, total_days: 14, completed_tasks: 0, total_tasks: 42, progress_percent: 0, current_day: 1, time_elapsed_days: 1, missed_days: 0, inactive_days: 0, last_activity_at: "2026-09-16T09:00:00Z",
        program_status: "SAFETY_HOLD", completed_at: null, goals: [goal], cumulative_goal: null,
        safety: { before_adaptation: { level: "SEVERE", blocked: true, decision: "REFER", emergency: true, red_flags: [{ code: "BREATHING_DIFFICULTY", label: "Kesulitan bernapas / tanda gangguan jalan napas", matched_phrase: "sulit bernapas" }], recommended_action: "Hentikan program untuk saat ini dan segera bawa anak ke IGD/rumah sakit atau hubungi layanan darurat setempat." } },
        adaptation: { decision: "REFER" }, daily_summary: {}, next_day_plan: null,
      } as never;
      if (path === "/api/nutrition/program/p1") return { ...programDetail, status: "SAFETY_HOLD" } as never;
      throw new Error(`Unexpected path ${path}`);
    });

    withProvider(<NutritionProgramDayDetail programId="p1" dayNumber={1} initialDetail={availableDayDetail} initialProgram={programDetail} />);
    screen.getAllByRole("button", { name: /^Tandai tindakan:/i }).forEach((button) => fireEvent.click(button));
    const resultInputs = screen.getAllByRole("spinbutton");
    fireEvent.change(resultInputs[0], { target: { value: "3" } });
    fireEvent.change(resultInputs[1], { target: { value: "1" } });
    fireEvent.click(screen.getByRole("button", { name: /^Diterima$/i }));
    fireEvent.click(screen.getByRole("button", { name: /^Tidak ada keluhan$/i }));
    const reaction = screen.getByRole("group", { name: /Reaksi tidak biasa/i });
    fireEvent.click(within(reaction).getByRole("button", { name: /^Ada$/i }));
    fireEvent.change(screen.getByLabelText(/Jelaskan reaksi tidak biasa/i), { target: { value: "anak sulit bernapas setelah makan" } });

    await flushAction(() => fireEvent.click(screen.getByRole("button", { name: /Simpan catatan hari ini/i })));

    expect(await screen.findByRole("alert")).toHaveTextContent(/segera bawa anak ke IGD\/rumah sakit/i);
    expect(screen.getByText(/Kesulitan bernapas/i)).toBeInTheDocument();
  });

  it("keeps a locked day visual, readable, and free of future task details", () => {
    withProvider(<NutritionProgramDayDetail programId="p1" dayNumber={2} initialDetail={lockedDayDetail} initialProgram={programDetail} />);
    expect(screen.getByRole("heading", { name: /Belum tersedia/i })).toBeInTheDocument();
    expect(screen.getByText(/Tersedia dalam/i)).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /Kembali ke Program/i }).some((link) => link.getAttribute("href") === "/nutrition/program/p1")).toBe(true);
    expect(screen.queryByText("Bangun jadwal makan.")).not.toBeInTheDocument();
    expect(screen.queryByRole("spinbutton")).not.toBeInTheDocument();
  });

  it("shows DIRTY → SAVING/SAVED semantics and keeps the next day locked after completion", async () => {
    mocked.mockImplementation(async (path: string, init?: RequestInit) => {
      if (path === "/api/nutrition/program/p1/daily-log" && init?.method === "POST") return { program_id: "p1", saved: true, saved_at: "2026-09-16T09:00:00Z", day_number: 1, day_completed: true, day_completed_at: "2026-09-16T09:00:00Z", checklist_state: [true, true, true], food_group_state: [true, true, false, false, false], has_complaint: false, complaint_note: null, days_completed: 1, total_days: 14, completed_tasks: 3, total_tasks: 42, progress_percent: 7.14, current_day: 1, time_elapsed_days: 1, missed_days: 0, inactive_days: 0, last_activity_at: "2026-09-16T09:00:00Z", program_status: "ACTIVE", completed_at: null, goals: [{ ...goal, actual: 1, progress_percentage: 10, remaining_gap: 9, status: "IN_PROGRESS" }], cumulative_goal: null } as never;
      if (path === "/api/nutrition/program/p1/days/2") return { ...lockedDayDetail, last_activity_at: "2026-09-16T09:00:00Z" } as never;
      throw new Error(`Unexpected path ${path}`);
    });

    withProvider(<NutritionProgramDayDetail programId="p1" dayNumber={1} initialDetail={availableDayDetail} initialProgram={programDetail} />);
    expect(screen.getAllByText(/Day 1 of 14/i).length).toBeGreaterThan(0);
    const save = screen.getByRole("button", { name: /Simpan catatan hari ini/i });
    expect(save).toBeDisabled();
    screen.getAllByRole("button", { name: /^Tandai tindakan:/i }).forEach((button) => fireEvent.click(button));
    const resultInputs = screen.getAllByRole("spinbutton");
    fireEvent.change(resultInputs[0], { target: { value: "3" } });
    fireEvent.change(resultInputs[1], { target: { value: "1" } });
    fireEvent.click(screen.getByRole("button", { name: /^Diterima$/i }));
    fireEvent.click(screen.getByRole("button", { name: /^Tidak ada keluhan$/i }));
    fireEvent.click(screen.getByRole("button", { name: /^Protein/i }));
    expect(screen.getByText("Unsaved changes")).toBeInTheDocument();
    expect(save).toBeEnabled();

    await flushAction(() => fireEvent.click(save));

    const successDialog = await screen.findByRole("dialog", { name: /Hari 1 selesai/i });
    expect(within(successDialog).getByText(/Semua aktivitas dan catatan hari ini sudah tersimpan/i)).toBeInTheDocument();
    const stayButton = within(successDialog).getByRole("button", { name: /Tetap di Hari 1/i });
    const nextButton = within(successDialog).getByRole("button", { name: /Lihat Hari 2/i });
    expect(stayButton).toHaveFocus();
    expect(nextButton).toBeInTheDocument();
    fireEvent.click(stayButton);
    expect(screen.queryByRole("dialog", { name: /Hari 1 selesai/i })).not.toBeInTheDocument();
    expect(screen.getByRole("status", { name: /Memproses hasil Hari 1/i })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: /Hari ini sudah tersimpan/i }, { timeout: 2000 })).toBeInTheDocument();
    expect(screen.getByText(/Visual hasil To Do/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Simpan catatan hari ini/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("spinbutton")).not.toBeInTheDocument();
  });

  it("shows complaint notes only when the user reports a problem", () => {
    withProvider(<NutritionProgramDayDetail programId="p1" dayNumber={1} initialDetail={availableDayDetail} initialProgram={programDetail} />);
    expect(screen.getByText(/Apakah ada keluhan atau kendala hari ini/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/Ceritakan keluhan atau kendalanya/i)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /^Ada keluhan$/i }));
    expect(screen.getByLabelText(/Ceritakan keluhan atau kendalanya/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /^Tidak ada keluhan$/i }));
    expect(screen.queryByLabelText(/Ceritakan keluhan atau kendalanya/i)).not.toBeInTheDocument();
  });

  it("filters nutrition history by MPASI, Toddler, and Lansia category", () => {
    const mpasi = { ...summary, id: "p-mpasi", stage: "mpasi", title: "Program MPASI" };
    const toddler = { ...summary, id: "p-toddler", stage: "toddler", title: "Program Toddler" };
    const elderly = { ...summary, id: "p-elderly", stage: "elderly", title: "Program Lansia" };
    withProvider(<NutritionHistory initialPrograms={[mpasi, toddler, elderly] as never} />);

    expect(screen.getByText("Program MPASI")).toBeInTheDocument();
    expect(screen.getByText("Program Toddler")).toBeInTheDocument();
    expect(screen.getByText("Program Lansia")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /^Lansia$/i }));
    expect(screen.getByText("Program Lansia")).toBeInTheDocument();
    expect(screen.queryByText("Program MPASI")).not.toBeInTheDocument();
    expect(screen.queryByText("Program Toddler")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /^MPASI$/i }));
    expect(screen.getByText("Program MPASI")).toBeInTheDocument();
    expect(screen.queryByText("Program Lansia")).not.toBeInTheDocument();
  });

  it("cancels an active plan only after confirmation and preserves it as CANCELLED history", async () => {
    const cancelled = { ...summary, status: "CANCELLED", cancelled_at: "2026-09-18T10:00:00Z" };
    mocked.mockImplementation(async (path: string, init?: RequestInit) => {
      if (path === "/api/nutrition/program/p1/cancel" && init?.method === "POST") return cancelled as never;
      throw new Error(`Unexpected path ${path}`);
    });

    withProvider(<NutritionHistory initialPrograms={[summary]} />);
    expect(screen.getByText(summary.title)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /More actions for Healthy Eating Habit Plan/i }));
    fireEvent.click(screen.getByRole("menuitem", { name: /Cancel Plan/i }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText(/Cancel Only mempertahankan progress/i)).toBeInTheDocument();

    await flushAction(() => fireEvent.click(within(dialog).getByRole("button", { name: /Cancel Only/i })));

    expect(screen.getAllByText("CANCELLED").length).toBeGreaterThan(0);
  });

  it("shows missed checklist as expired read-only", () => {
    const missedDay = { ...availableDay, status: "MISSED" as const, missed: true, unlock_at: "2026-09-15T08:00:00Z" };
    const missedDetail = { ...availableDayDetail, current_day: 2, missed_days: 1, day: missedDay };
    const missedProgram = { ...programDetail, current_day: 2, missed_days: 1, days: [missedDay, { ...lockedDay, status: "AVAILABLE" as const, locked: false }] };

    withProvider(<NutritionProgramDayDetail programId="p1" dayNumber={1} initialDetail={missedDetail} initialProgram={missedProgram} />);
    expect(screen.getByRole("heading", { name: /Hari sudah terkunci/i })).toBeInTheDocument();
    expect(screen.getByText(/Progress harian ditutup tepat pukul 00\.00/i)).toBeInTheDocument();

    const disabledButtons = screen
      .getAllByRole("button")
      .filter((button) => button.hasAttribute("disabled"));

    expect(disabledButtons.length).toBeGreaterThan(0);

    screen
      .getAllByRole("button", { name: /^Tandai tindakan:/i })
      .forEach((button) => expect(button).toBeDisabled());
  });

  it("deletes a program from history only after it is already cancelled", async () => {
    const cancelled = { ...summary, status: "CANCELLED", cancelled_at: "2026-09-18T10:00:00Z" };
    mocked.mockImplementation(async (path: string, init?: RequestInit) => {
      if (path === "/api/nutrition/program/p1" && init?.method === "DELETE") return undefined as never;
      throw new Error(`Unexpected path ${path}`);
    });

    withProvider(<NutritionHistory initialPrograms={[cancelled]} />);
    expect(screen.getByText(summary.title)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /More actions for Healthy Eating Habit Plan/i }));
    fireEvent.click(screen.getByRole("menuitem", { name: /Delete Program/i }));
    const dialog = screen.getByRole("dialog");

    await flushAction(() => fireEvent.click(within(dialog).getByRole("button", { name: /^Delete Program$/i })));

    expect(screen.queryByText(summary.title)).not.toBeInTheDocument();
  });

  it("renders Final Program Result with program completion separate from goal achievement", () => {
    const finalResult = {
      program: { ...summary, status: "COMPLETED", completed_at: "2026-09-30T08:00:00Z", days_completed: 14, progress_percent: 100 },
      cycle: 1, duration_days: 14, goal: { ...goal, actual: 8, target: 10, status: "PARTIALLY_MET", progress_percentage: 80, remaining_gap: 2 },
      baseline: 0, target: 10, actual: 8, goal_status: "PARTIALLY_MET", goal_achievement_percent: 80, program_completion_percent: 100,
      program_numbers: { duration_days: 14, completed_days: 14, missed_days: 0, logged_days: 12, adaptation_decisions: 3 },
      what_accomplished: ["Rutinitas makan tercapai pada 8 hari."], what_changed: "Rencana berubah berdasarkan log yang tersimpan.",
      what_worked_well: ["Rutinitas makan paling konsisten."], challenges: ["Keragaman masih perlu waktu."],
      adaptation_history: [{ day: 2, decision: "CONTINUE", user_facing_reason: "Rencana dipertahankan.", rule_version_id: "nutrition-adaptive-v1" }],
      trends: {
        goal_progress_percent: 80,
        behavioral_adherence_percent: 72,
        daily_progress: [
          { day: 1, adherence_percent: 60, task_count: 3, met_tasks: 1, status: "COMPLETED" },
          { day: 2, adherence_percent: 70, task_count: 3, met_tasks: 2, status: "COMPLETED", decision: "CONTINUE" },
          { day: 13, adherence_percent: 85, task_count: 3, met_tasks: 2, status: "COMPLETED" },
          { day: 14, adherence_percent: 90, task_count: 3, met_tasks: 3, status: "COMPLETED" },
        ],
        daily_progress_change: { early_average: 65, recent_average: 87.5, delta_points: 22.5, direction: "IMPROVING", scored_days: 4, strong_days: 2 },
      }, safety_notes: [],
      next_step: { decision: "EXTEND", can_extend: true, can_reframe: false, options: ["same_goal"], message: "Lanjutkan goal dengan extension." },
      extension_history: [], generated_at: "2026-09-30T08:00:00Z",
    };
    withProvider(<NutritionFinalResult programId="p1" initialResult={finalResult} />);
    expect(screen.getByText(summary.title)).toBeInTheDocument();
    expect(screen.getByText(/14 \/ 14 hari/i)).toBeInTheDocument();
    expect(screen.getByText(/8 \/ 10/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Extend Guided Program/i })).toHaveAttribute("href", "/nutrition/program/p1/history#extension-review");
    expect(screen.getByRole("heading", { name: /Lihat hasil cycle dalam satu tampilan/i })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /Program selesai/i })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /Grafik pencapaian harian dari hari ke hari/i })).toBeInTheDocument();
    expect(screen.getByText(/\+23 poin/i)).toBeInTheDocument();
  });

  it("uses the Stage 9 root route as the Today workspace without the old overview sidebar", () => {
    withProvider(<NutritionProgramShell programId="p1" active="today" initialProgram={programDetail}><div>Konten workspace hari ini</div></NutritionProgramShell>);
    const todayLink = screen.getByRole("link", { name: /^Hari Ini$/i });
    expect(todayLink).toHaveAttribute("href", "/nutrition/program/p1");
    expect(todayLink).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: /^Progres$/i })).toHaveAttribute("href", "/nutrition/program/p1/progress");
    expect(screen.getByRole("link", { name: /^Riwayat$/i })).toHaveAttribute("href", "/nutrition/program/p1/history");
    expect(screen.queryByRole("link", { name: /^Ringkasan$/i })).not.toBeInTheDocument();
    expect(screen.getByText("Konten workspace hari ini")).toBeInTheDocument();
    expect(screen.getByTestId("day-timeline-scroll")).toHaveClass("overflow-x-auto");
  });

  it("renders the Stage 8 Day 14 block review inside the Stage 9 Today workspace", async () => {
    const day14 = {
      ...availableDay,
      id: "d14",
      day_number: 14,
      status: "COMPLETED" as const,
      completed: true,
      completed_at: "2026-09-29T09:00:00Z",
      action_details: { ...availableDay.action_details, task_results: { meal_routine_d1: 3, vegetable_fruit_exposure_d1: 1, food_response_d1: "accepted" } },
      checklist_state: [true, true, true],
      has_complaint: false,
    };
    const completedProgram = {
      ...programDetail,
      status: "COMPLETED",
      completed_at: "2026-09-29T09:00:00Z",
      current_day: 14,
      days_completed: 14,
      progress_percent: 100,
      days: [day14],
    };
    mocked.mockImplementation(async (path: string) => {
      if (path === "/api/nutrition/program/p1/block-review") return {
        program_id: "p1",
        duration_days: 14,
        block_completed: true,
        program_progress: { completed_days: 14, planned_days: 14, percent: 100 },
        goal_progress: { metric: "meal_routine", target: 10, actual: 8, unit: "successful target days", percent: 80 },
        trend: {},
        what_improved: "Rutinitas makan lebih konsisten.",
        what_remains: "Variasi makanan masih perlu dilanjutkan.",
        safety: {},
        goal_status: "PARTIALLY_MET",
        decision: "EXTEND",
        next_focus: "Pertahankan rutinitas makan dan lanjutkan variasi secara bertahap.",
        options: ["same_goal"],
        can_extend: true,
        can_reframe: false,
      } as never;
      throw new Error(`Unexpected path ${path}`);
    });

    withProvider(<NutritionProgramDailyWorkspace program={completedProgram as never} day={day14 as never} onProgramRefresh={vi.fn()} />);

    expect(await screen.findByRole("heading", { name: /Ringkasan 14 hari/i })).toBeInTheDocument();
    expect(screen.getByText(/14 \/ 14 hari/i)).toBeInTheDocument();
    expect(screen.getByText(/Rutinitas makan lebih konsisten/i)).toBeInTheDocument();
    expect(screen.getByText(/Pertahankan rutinitas makan dan lanjutkan variasi/i)).toBeInTheDocument();
  });

  it("redirects final result after logout and hides private actions", async () => {
    const finalResult = {
      program: { ...summary, status: "COMPLETED", completed_at: "2026-09-30T08:00:00Z", days_completed: 14, progress_percent: 100 },
      cycle: 1, duration_days: 14, goal: { ...goal, actual: 8, target: 10, status: "PARTIALLY_MET", progress_percentage: 80, remaining_gap: 2 },
      baseline: 0, target: 10, actual: 8, goal_status: "PARTIALLY_MET", goal_achievement_percent: 80, program_completion_percent: 100,
      program_numbers: { duration_days: 14, completed_days: 14, missed_days: 0, logged_days: 12, adaptation_decisions: 3 },
      what_accomplished: ["Rutinitas makan tercapai pada 8 hari."], what_changed: "Rencana berubah berdasarkan log yang tersimpan.",
      what_worked_well: ["Rutinitas makan paling konsisten."], challenges: ["Keragaman masih perlu waktu."],
      adaptation_history: [], trends: { goal_progress_percent: 80, behavioral_adherence_percent: 72 }, safety_notes: [],
      next_step: { decision: "EXTEND", can_extend: true, can_reframe: true, options: ["same_goal"], message: "Lanjutkan goal dengan extension." },
      extension_history: [], generated_at: "2026-09-30T08:00:00Z",
    };
    mocked.mockImplementation(async (path: string, init?: RequestInit) => {
      if (path === "/api/auth/logout" && init?.method === "POST") return undefined as never;
      throw new Error(`Unexpected path ${path}`);
    });
    withProvider(<><Navbar/><NutritionFinalResult programId="p1" initialResult={finalResult} /></>);
    fireEvent.click(screen.getAllByRole("button", { name: /Profile care@example.com/i })[0]);
    await flushAction(() => fireEvent.click(screen.getByRole("menuitem", { name: /^Logout$/i })));
    expect(screen.queryByRole("heading", { name: summary.title })).not.toBeInTheDocument();
    expect(screen.queryByText(/Anda telah keluar/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Extend Guided Program/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/Guest Account/i)).not.toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /^Akun$/i })[0]).toBeInTheDocument();
  });


  it("uses backend Stage 6 adherence after save instead of keeping only the client preview", async () => {
    mocked.mockImplementation(async (path: string, init?: RequestInit) => {
      if (path === "/api/nutrition/program/p1/daily-log" && init?.method === "POST") return {
        program_id: "p1", saved: true, saved_at: "2026-09-16T09:00:00Z", day_number: 1, day_completed: false, day_completed_at: null,
        checklist_state: [false, false, false], food_group_state: [], has_complaint: false, complaint_note: null,
        task_results: { meal_routine_d1: 2, vegetable_fruit_exposure_d1: 1, food_response_d1: "partial" },
        metric_results: [
          { task_id: "meal_routine_d1", metric_id: "meal_routine", target: 3, actual_result: 2, unit: "makan utama", input_type: "count", status: "PARTIAL", adherence: 66.67, completed_at: null, action_completed: false, evidence_rule_id: null, stage6_engine_version: "daily_result_adherence_v1" },
          { task_id: "vegetable_fruit_exposure_d1", metric_id: "vegetable_fruit_exposure", target: 1, actual_result: 1, unit: "kesempatan", input_type: "count", status: "COMPLETED", adherence: 100, completed_at: "2026-09-16T09:00:00Z", action_completed: false, evidence_rule_id: null, stage6_engine_version: "daily_result_adherence_v1" },
          { task_id: "food_response_d1", metric_id: "food_response", target: "accepted", actual_result: "partial", unit: "respons", input_type: "choice", status: "PARTIAL", adherence: 50, completed_at: null, action_completed: false, evidence_rule_id: null, stage6_engine_version: "daily_result_adherence_v1" },
        ],
        days_completed: 0, total_days: 14, completed_tasks: 0, total_tasks: 42, progress_percent: 0, current_day: 1, time_elapsed_days: 1, missed_days: 0, inactive_days: 0, last_activity_at: "2026-09-16T09:00:00Z",
        program_status: "ACTIVE", completed_at: null, goals: [goal], cumulative_goal: null,
        indicators: {}, safety: {}, adaptation: {}, daily_summary: {}, next_day_plan: null,
      } as never;
      if (path === "/api/nutrition/program/p1") return programDetail as never;
      throw new Error(`Unexpected path ${path}`);
    });

    withProvider(<NutritionProgramDayDetail programId="p1" dayNumber={1} initialDetail={availableDayDetail} initialProgram={programDetail} />);
    const inputs = screen.getAllByRole("spinbutton");
    fireEvent.change(inputs[0], { target: { value: "2" } });
    fireEvent.change(inputs[1], { target: { value: "1" } });
    const foodResponseGroup = screen.getByRole("group", { name: /Bagaimana respons anak pada paparan makanan fokus hari ini/i });
    fireEvent.click(within(foodResponseGroup).getByRole("button", { name: /^Sebagian$/i }));
    fireEvent.click(screen.getByRole("button", { name: /^Tidak ada keluhan$/i }));

    await flushAction(() => fireEvent.click(screen.getByRole("button", { name: /Simpan catatan hari ini/i })));

    expect(screen.queryByText(/66\.67%/)).not.toBeInTheDocument();
    expect(screen.queryByText(/^50%$/)).not.toBeInTheDocument();
    expect(screen.getAllByText(/Sebagian tercapai/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/2 makan utama/i).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("spinbutton")[0]).toHaveValue(2);
  });

  it("keeps Stage 6 local actual results when save returns 401", async () => {
    mocked.mockImplementation(async (path: string, init?: RequestInit) => {
      if (path === "/api/nutrition/program/p1/daily-log" && init?.method === "POST") {
        throw new ApiError("Sesi berakhir", 401);
      }
      throw new Error(`Unexpected path ${path}`);
    });

    withProvider(<NutritionProgramDayDetail programId="p1" dayNumber={1} initialDetail={availableDayDetail} initialProgram={programDetail} />);
    const inputs = screen.getAllByRole("spinbutton");
    fireEvent.change(inputs[0], { target: { value: "2" } });
    fireEvent.change(inputs[1], { target: { value: "1" } });
    const foodResponseGroup = screen.getByRole("group", { name: /Bagaimana respons anak pada paparan makanan fokus hari ini/i });
    fireEvent.click(within(foodResponseGroup).getByRole("button", { name: /^Sebagian$/i }));
    fireEvent.click(screen.getByRole("button", { name: /^Tidak ada keluhan$/i }));

    await flushAction(() => fireEvent.click(screen.getByRole("button", { name: /Simpan catatan hari ini/i })));

    expect(screen.getByText(/Sesi berakhir\. Masuk lagi untuk menyimpan/i)).toBeInTheDocument();
    expect(inputs[0]).toHaveValue(2);
    expect(inputs[1]).toHaveValue(1);
    expect(within(foodResponseGroup).getByRole("button", { name: /^Sebagian$/i })).toHaveAttribute("aria-pressed", "true");
  });

  it("protects Stage 6 save from a rapid double click", async () => {
    let dailySaveCalls = 0;
    mocked.mockImplementation(async (path: string, init?: RequestInit) => {
      if (path === "/api/nutrition/program/p1/daily-log" && init?.method === "POST") {
        dailySaveCalls += 1;
        await new Promise((resolve) => setTimeout(resolve, 5));
        return {
          program_id: "p1", saved: true, saved_at: "2026-09-16T09:00:00Z", day_number: 1, day_completed: false, day_completed_at: null,
          checklist_state: [false, false, false], food_group_state: [], has_complaint: false, complaint_note: null,
          task_results: { meal_routine_d1: 2, vegetable_fruit_exposure_d1: 1, food_response_d1: "accepted" }, metric_results: [],
          days_completed: 0, total_days: 14, completed_tasks: 0, total_tasks: 42, progress_percent: 0, current_day: 1, time_elapsed_days: 1, missed_days: 0, inactive_days: 0, last_activity_at: "2026-09-16T09:00:00Z",
          program_status: "ACTIVE", completed_at: null, goals: [goal], cumulative_goal: null, indicators: {}, safety: {}, adaptation: {}, daily_summary: {}, next_day_plan: null,
        } as never;
      }
      if (path === "/api/nutrition/program/p1") return programDetail as never;
      throw new Error(`Unexpected path ${path}`);
    });

    withProvider(<NutritionProgramDayDetail programId="p1" dayNumber={1} initialDetail={availableDayDetail} initialProgram={programDetail} />);
    const inputs = screen.getAllByRole("spinbutton");
    fireEvent.change(inputs[0], { target: { value: "2" } });
    fireEvent.change(inputs[1], { target: { value: "1" } });
    fireEvent.click(screen.getByRole("button", { name: /^Diterima$/i }));
    fireEvent.click(screen.getByRole("button", { name: /^Tidak ada keluhan$/i }));
    const save = screen.getByRole("button", { name: /Simpan catatan hari ini/i });

    await act(async () => {
      fireEvent.click(save);
      fireEvent.click(save);
      await new Promise((resolve) => setTimeout(resolve, 15));
    });

    expect(dailySaveCalls).toBe(1);
  });

});








