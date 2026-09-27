import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "@/components/auth-provider";
import { NutritionAssessment } from "@/components/nutrition-assessment";
import { NutritionResult } from "@/components/nutrition-result";
import { apiFetch } from "@/lib/api";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/nutrition/elderly",
}));
vi.mock("@/lib/api", () => ({
  API_BASE: "http://localhost:8000",
  SESSION_EXPIRED_EVENT: "sehatin:session-expired",
  ApiError: class ApiError extends Error {},
  apiFetch: vi.fn(),
}));
const mockedApiFetch = vi.mocked(apiFetch);

const valid = { status: "VALID" as const, can_process: true, message: "Data dapat diproses", issues: [], indicators: [], references: [] };

function fillElderlyBasic() {
  fireEvent.change(screen.getByLabelText(/Jenis kelamin/i), { target: { value: "female" } });
  fireEvent.change(screen.getByLabelText(/Berat badan/i), { target: { value: "55" } });
  fireEvent.change(screen.getByLabelText(/Tinggi badan/i), { target: { value: "155" } });
}

async function goToElderlyConditions() {
  fillElderlyBasic();
  fireEvent.click(screen.getByRole("button", { name: /Lanjut/i }));
  await screen.findByRole("heading", { name: /^Kebiasaan Makan Lansia$/i });
  const chewingGroup = screen.getByRole("group", { name: /Kesulitan mengunyah makanan/i });
  const swallowingGroup = screen.getByRole("group", { name: /Kesulitan menelan makanan atau minuman/i });
  fireEvent.click(within(chewingGroup).getByRole("button", { name: /^Tidak ada$/i }));
  fireEvent.click(within(swallowingGroup).getByRole("button", { name: /^Tidak ada$/i }));
  fireEvent.click(screen.getByRole("button", { name: /Lanjut/i }));
  await screen.findByRole("heading", { name: /^Kondisi Kesehatan$/i });
}

beforeEach(() => {
  sessionStorage.clear();
  push.mockReset();
  mockedApiFetch.mockReset();
  mockedApiFetch.mockResolvedValue(valid as never);
});

describe("Elderly known-condition context", () => {
  it("uses an elderly-specific eating context and a dedicated health-condition step", async () => {
    render(<NutritionAssessment stage="elderly" />);
    fillElderlyBasic();
    fireEvent.click(screen.getByRole("button", { name: /Lanjut/i }));

    expect(await screen.findByRole("heading", { name: /^Kebiasaan Makan Lansia$/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/Nafsu makan belakangan ini/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Frekuensi makan utama per hari/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Aktivitas harian/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Kebiasaan minum cairan/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Kemandirian saat makan\/minum/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Dukungan caregiver/i)).toBeInTheDocument();
    expect(screen.queryByText(/Penyakit atau kondisi kesehatan yang sudah diketahui diisi pada langkah berikutnya/i)).not.toBeInTheDocument();
    const chewingGroup = screen.getByRole("group", { name: /Kesulitan mengunyah makanan/i });
    const swallowingGroup = screen.getByRole("group", { name: /Kesulitan menelan makanan atau minuman/i });
    expect(within(chewingGroup).getByRole("button", { name: /^Tidak ada$/i })).toHaveAttribute("aria-pressed", "false");
    expect(within(swallowingGroup).getByRole("button", { name: /^Tidak ada$/i })).toHaveAttribute("aria-pressed", "false");
    expect(screen.queryByText(/Responsive feeding/i)).not.toBeInTheDocument();

    fireEvent.click(within(chewingGroup).getByRole("button", { name: /^Tidak ada$/i }));
    fireEvent.click(within(swallowingGroup).getByRole("button", { name: /^Tidak ada$/i }));
    fireEvent.click(screen.getByRole("button", { name: /Lanjut/i }));
    expect(await screen.findByRole("heading", { name: /^Kondisi Kesehatan$/i })).toBeInTheDocument();
    expect(screen.getByText(/Apakah lansia memiliki penyakit atau kondisi kesehatan yang sudah diketahui/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /^Ada$/i }));
    expect(screen.getByRole("checkbox", { name: /^Diabetes$/i })).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /^Hipertensi$/i })).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /^Lainnya$/i })).toBeInTheDocument();
  });

  it("uses multi-select, validates Other, and persists disease draft across remount", async () => {
    const view = render(<NutritionAssessment stage="elderly" />);
    await goToElderlyConditions();

    fireEvent.click(screen.getByRole("button", { name: /^Ada$/i }));
    fireEvent.click(screen.getByRole("checkbox", { name: /^Diabetes$/i }));
    fireEvent.click(screen.getByRole("checkbox", { name: /^Hipertensi$/i }));
    fireEvent.click(screen.getByRole("checkbox", { name: /^Lainnya$/i }));
    expect(screen.getByLabelText(/Nama penyakit atau kondisi/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Lanjut/i }));
    expect(screen.getByText(/Nama kondisi wajib diisi/i)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/Nama penyakit atau kondisi/i), { target: { value: "Osteoporosis" } });
    await waitFor(() => expect(sessionStorage.getItem("sehatin:nutrition-assessment-draft:elderly")).toContain("Osteoporosis"));

    fireEvent.click(screen.getByRole("button", { name: /Kembali/i }));
    fireEvent.click(screen.getByRole("button", { name: /Lanjut/i }));
    expect(screen.getByRole("checkbox", { name: /^Diabetes$/i })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: /^Hipertensi$/i })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: /^Lainnya$/i })).toBeChecked();
    expect(screen.getByLabelText(/Nama penyakit atau kondisi/i)).toHaveValue("Osteoporosis");

    view.unmount();
    render(<NutritionAssessment stage="elderly" />);
    await goToElderlyConditions();
    expect(screen.getByRole("button", { name: /^Ada$/i })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("checkbox", { name: /^Diabetes$/i })).toBeChecked();
    expect(screen.getByLabelText(/Nama penyakit atau kondisi/i)).toHaveValue("Osteoporosis");
  });

  it("sends structured conditions in the elderly recommendation payload", async () => {
    mockedApiFetch.mockImplementation(async (path: string) => {
      if (path === "/api/nutrition/validate") return valid as never;
      if (path === "/api/nutrition/recommendation") return {
        stage: "elderly", category: "Nutrisi lansia 60+ tahun", age_band: "Lansia 65–80 tahun", personalization_status: "personalized_education", validation: valid,
        input_summary: [], summary: "Panduan edukatif", estimated_needs: {}, meal_pattern: {}, priority_nutrients: [], food_groups: [], recommendations: [], sample_menu: [], guidance: [], safety_notes: [], disclaimer: "Bukan diagnosis", references: [], suggested_goals: [], baseline: {}, detected_gaps: [], primary_gap: null, primary_target: null, support_targets: [], health_context: { has_condition: true, conditions: ["diabetes", "other"], condition_labels: ["Diabetes", "Osteoporosis"] },
      } as never;
      throw new Error(`Unexpected path ${path}`);
    });

    render(<NutritionAssessment stage="elderly" />);
    fillElderlyBasic();
    fireEvent.click(screen.getByRole("button", { name: /Lanjut/i }));
    await screen.findByRole("heading", { name: /^Kebiasaan Makan Lansia$/i });
    fireEvent.change(screen.getByLabelText(/Kebiasaan minum cairan/i), { target: { value: "sometimes_low" } });
    fireEvent.change(screen.getByLabelText(/Kemandirian saat makan\/minum/i), { target: { value: "needs_reminder" } });
    fireEvent.change(screen.getByLabelText(/Dukungan caregiver/i), { target: { value: "daily" } });
    const chewingGroup = screen.getByRole("group", { name: /Kesulitan mengunyah makanan/i });
    const swallowingGroup = screen.getByRole("group", { name: /Kesulitan menelan makanan atau minuman/i });
    fireEvent.click(within(chewingGroup).getByRole("button", { name: /^Tidak ada$/i }));
    fireEvent.click(within(swallowingGroup).getByRole("button", { name: /^Tidak ada$/i }));
    fireEvent.click(screen.getByRole("button", { name: /Lanjut/i }));
    await screen.findByRole("heading", { name: /^Kondisi Kesehatan$/i });
    fireEvent.click(screen.getByRole("button", { name: /^Ada$/i }));
    fireEvent.click(screen.getByRole("checkbox", { name: /^Diabetes$/i }));
    fireEvent.click(screen.getByRole("checkbox", { name: /^Lainnya$/i }));
    fireEvent.change(screen.getByLabelText(/Nama penyakit atau kondisi/i), { target: { value: "Osteoporosis" } });
    fireEvent.click(screen.getByRole("button", { name: /Lanjut/i }));
    expect(await screen.findByRole("heading", { name: /^Preferensi & Pantangan$/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Lanjut/i }));
    expect(await screen.findByText(/Review before analysis/i)).toBeInTheDocument();
    expect(screen.getByText(/Diabetes, Osteoporosis/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Analyze My Nutrition/i }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/nutrition/elderly/result"));
    const recommendationCall = mockedApiFetch.mock.calls.find(([path]) => path === "/api/nutrition/recommendation");
    expect(recommendationCall).toBeTruthy();
    const body = JSON.parse(String(recommendationCall?.[1]?.body));
    expect(body.has_condition).toBe(true);
    expect(body.conditions).toEqual(["diabetes", "other"]);
    expect(body.other_condition).toBe("Osteoporosis");
    expect(body.hydration_pattern).toBe("sometimes_low");
    expect(body.eating_independence).toBe("needs_reminder");
    expect(body.caregiver_support).toBe("daily");
  });

  it("renders reported conditions and nutrition focus on the elderly result", async () => {
    sessionStorage.setItem("sehatin:nutrition-result:elderly", JSON.stringify({
      created_at: new Date().toISOString(),
      assessment: { stage: "elderly", age_years: 70, sex: "female", weight_kg: 55, height_cm: 155, has_condition: true, conditions: ["diabetes", "other"], other_condition: "Osteoporosis" },
      result: {
        stage: "elderly", category: "Nutrisi lansia 60+ tahun", age_band: "Lansia 65–80 tahun", personalization_status: "personalized_education", validation: valid,
        input_summary: ["Kondisi kesehatan yang dilaporkan: Diabetes, Osteoporosis"], summary: "Disesuaikan dengan kondisi yang dilaporkan.", estimated_needs: {}, meal_pattern: {}, priority_nutrients: ["Protein"], food_groups: ["Sayur dan buah"], recommendations: ["Pertahankan pola makan seimbang."], sample_menu: ["Nasi, ikan, sayur."], guidance: [], safety_notes: [], disclaimer: "Bukan diagnosis", references: [], suggested_goals: [], baseline: {}, detected_gaps: [], primary_gap: null, primary_target: null, support_targets: [],
        health_context: { has_condition: true, conditions: ["diabetes", "other"], condition_labels: ["Diabetes", "Osteoporosis"], nutrition_focus: ["Keteraturan waktu makan", "Pola makan seimbang dan cukup"], program_focus: ["Keteraturan waktu makan"], needs_clinical_consultation: true, consultation_note: "Gunakan arahan tenaga kesehatan.", source_note: "Kondisi kesehatan berasal dari informasi yang dilaporkan user; SEHATIN tidak menyimpulkan diagnosis." },
        elderly_context: { hydration_pattern: "sometimes_low", hydration_label: "Kadang minum lebih sedikit", eating_independence: "needs_reminder", eating_independence_label: "Perlu diingatkan", caregiver_support: "daily", caregiver_support_label: "Tersedia setiap hari", focus: ["Bangun pengingat minum yang realistis"] },
      },
    }));

    render(<AuthProvider initialUser={null} autoRefresh={false}><NutritionResult stage="elderly" /></AuthProvider>);
    expect(await screen.findByRole("heading", { name: /Konteks yang kamu laporkan/i })).toBeInTheDocument();
    expect(screen.getAllByText("Diabetes").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Osteoporosis").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Keteraturan waktu makan").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Gunakan arahan tenaga kesehatan/i).length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: /Cara makan, minum, dan dukungan sehari-hari/i })).toBeInTheDocument();
    expect(screen.getAllByText("Kadang minum lebih sedikit").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Perlu diingatkan").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Tersedia setiap hari").length).toBeGreaterThan(0);
  });

  it("keeps Guided Program enabled for chronic-condition context when no safety limit is present", async () => {
    mockedApiFetch.mockImplementation(async (path: string, options?: RequestInit) => {
      if (path === "/api/nutrition/program" && (!options?.method || options.method === "GET")) return [] as never;
      return valid as never;
    });
    sessionStorage.setItem("sehatin:nutrition-result:elderly", JSON.stringify({
      created_at: new Date().toISOString(),
      assessment: { stage: "elderly", age_years: 70, sex: "female", weight_kg: 55, height_cm: 155, swallowing_difficulty: false, has_condition: true, conditions: ["diabetes", "hypertension"] },
      result: {
        stage: "elderly", category: "Nutrisi lansia 60+ tahun", age_band: "Lansia 65–80 tahun", personalization_status: "personalized_education", validation: valid,
        input_summary: [], summary: "Disesuaikan dengan konteks kesehatan yang dilaporkan.", estimated_needs: {}, meal_pattern: {}, priority_nutrients: [], food_groups: [], recommendations: ["Pertahankan pola makan seimbang."], sample_menu: ["Nasi, ikan, sayur."], guidance: [], safety_notes: [], disclaimer: "Bukan diagnosis", references: [], suggested_goals: [], baseline: {}, detected_gaps: [], primary_gap: null, primary_target: null, support_targets: [],
        health_context: { has_condition: true, conditions: ["diabetes", "hypertension"], condition_labels: ["Diabetes", "Hipertensi"], nutrition_focus: ["Keteraturan waktu makan"], program_focus: ["Keteraturan waktu makan"], needs_clinical_consultation: false },
      },
    }));

    render(<AuthProvider initialUser={{ id: "u1", email: "elderly@example.com", created_at: "2026-09-25T00:00:00Z" }} autoRefresh={false}><NutritionResult stage="elderly" /></AuthProvider>);
    const start = await screen.findByRole("button", { name: /Mulai Guided Program/i });
    await waitFor(() => expect(start).toBeEnabled());
  });

  it("allows a swallowing-limited elderly result to start a general Guided Program without reassessment", async () => {
    mockedApiFetch.mockImplementation(async (path: string, options?: RequestInit) => {
      if (path === "/api/nutrition/program" && (!options?.method || options.method === "GET")) return [] as never;
      return valid as never;
    });
    sessionStorage.setItem("sehatin:nutrition-result:elderly", JSON.stringify({
      created_at: new Date().toISOString(),
      assessment: { stage: "elderly", age_years: 70, sex: "female", weight_kg: 55, height_cm: 155, swallowing_difficulty: true, has_condition: true, conditions: ["diabetes"] },
      result: {
        stage: "elderly", category: "Nutrisi lansia 60+ tahun", age_band: "Lansia 65–80 tahun", personalization_status: "limited_for_safety", validation: valid,
        input_summary: [], summary: "Hasil edukatif dibatasi untuk keselamatan.", estimated_needs: {}, meal_pattern: {}, priority_nutrients: [], food_groups: [], recommendations: [], sample_menu: ["Nasi + ikan + sayur + pepaya; gunakan bentuk/tekstur yang sudah diketahui aman"], guidance: [], safety_notes: ["Gangguan menelan memerlukan perhatian."], disclaimer: "Bukan diagnosis", references: [], suggested_goals: [], baseline: {}, detected_gaps: [], primary_gap: null, primary_target: null, support_targets: [], health_context: { has_condition: true, conditions: ["diabetes"], condition_labels: ["Diabetes"] },
      },
    }));

    render(<AuthProvider initialUser={{ id: "u1", email: "elderly@example.com", created_at: "2026-09-25T00:00:00Z" }} autoRefresh={false}><NutritionResult stage="elderly" /></AuthProvider>);
    expect(await screen.findByText(/Assessment mencatat kesulitan menelan/i)).toBeInTheDocument();
    expect(screen.getByText(/contoh komposisi menu berdasarkan kelompok pangan\/kandungan/i)).toBeInTheDocument();
    expect(screen.getByText(/Fokus pada kandungan, bukan level tekstur/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Nasi dengan ikan, sayur, dan pepaya\./i).length).toBeGreaterThan(0);
    const start = screen.getByRole("button", { name: /Mulai Guided Program/i });
    await waitFor(() => expect(start).toBeEnabled());
    expect(screen.queryByRole("link", { name: /Perbarui Assessment/i })).not.toBeInTheDocument();
  });

  it("lets elderly users name the program and sends the selected focus", async () => {
    mockedApiFetch.mockImplementation(async (path: string, options?: RequestInit) => {
      if (path === "/api/nutrition/program" && (!options?.method || options.method === "GET")) return [] as never;
      if (path === "/api/nutrition/program" && options?.method === "POST") {
        return { id: "elderly-program-1", stage: "elderly", title: "Program Minum Ibu", status: "ACTIVE" } as never;
      }
      return valid as never;
    });
    sessionStorage.setItem("sehatin:nutrition-result:elderly", JSON.stringify({
      created_at: new Date().toISOString(),
      assessment: { stage: "elderly", age_years: 70, sex: "female", weight_kg: 55, height_cm: 155, hydration_pattern: "often_low", swallowing_difficulty: false, has_condition: false, conditions: [] },
      result: {
        stage: "elderly", category: "Nutrisi lansia 60+ tahun", age_band: "Lansia 65–80 tahun", personalization_status: "personalized_education", validation: valid,
        input_summary: [], summary: "Keteraturan minum menjadi fokus utama.", estimated_needs: {}, meal_pattern: {}, priority_nutrients: [], food_groups: ["Karbohidrat", "Protein", "Sayur", "Buah"], recommendations: ["Bangun kebiasaan minum yang lebih teratur."], sample_menu: ["Nasi + ikan + sayur + pepaya"], guidance: [], safety_notes: [], disclaimer: "Bukan diagnosis", references: [], baseline: {}, detected_gaps: [], primary_gap: null, primary_target: null, support_targets: [],
        suggested_goals: [{ goal_key: "elderly_hydration_routine", title: "Bangun kebiasaan minum yang lebih teratur", description: "Bangun kesempatan minum yang realistis.", baseline: 0, target: 10, unit: "hari berhasil", measurement_method: "log cairan harian + hasil To Do hidrasi", duration: 14, priority: 1, baseline_label: "Sering minum lebih sedikit", target_label: "Pola minum lebih baik pada ≥10 dari 14 hari", selection_reason: "Keteraturan minum menjadi fokus yang paling perlu dibangun." }],
        health_context: { has_condition: false, conditions: [], condition_labels: [], nutrition_focus: [], program_focus: [], needs_clinical_consultation: false },
        elderly_context: { hydration_pattern: "often_low", hydration_label: "Sering minum lebih sedikit", eating_independence: "independent", eating_independence_label: "Mandiri", caregiver_support: "none", caregiver_support_label: "Tidak ada dukungan rutin", focus: ["Bangun kesempatan minum yang realistis"] },
      },
    }));

    render(<AuthProvider initialUser={{ id: "u1", email: "elderly@example.com", created_at: "2026-09-25T00:00:00Z" }} autoRefresh={false}><NutritionResult stage="elderly" /></AuthProvider>);
    const nameInput = await screen.findByLabelText(/Nama program/i);
    await waitFor(() => expect(nameInput).toHaveValue("Program Hidrasi Lansia"));
    fireEvent.change(nameInput, { target: { value: "Program Minum Ibu" } });
    const start = screen.getByRole("button", { name: /Mulai Guided Program/i });
    await waitFor(() => expect(start).toBeEnabled());
    fireEvent.click(start);

    await waitFor(() => expect(push).toHaveBeenCalledWith("/nutrition/program/elderly-program-1/today"));
    const createCall = mockedApiFetch.mock.calls.find(([path, options]) => path === "/api/nutrition/program" && options?.method === "POST");
    expect(createCall).toBeTruthy();
    const payload = JSON.parse(String(createCall?.[1]?.body));
    expect(payload.display_name).toBe("Program Minum Ibu");
    expect(payload.goal_key).toBe("elderly_hydration_routine");
  });

});
