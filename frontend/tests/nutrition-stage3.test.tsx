import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { NutritionAssessment, calculateAgeMonths } from "@/components/nutrition-assessment";
import { apiFetch } from "@/lib/api";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  usePathname: () => "/nutrition/mpasi",
}));
vi.mock("@/lib/api", () => ({
  API_BASE: "http://localhost:8000",
  ApiError: class ApiError extends Error {},
  apiFetch: vi.fn(),
}));
const mockedApiFetch = vi.mocked(apiFetch);

const valid = { status: "VALID" as const, can_process: true, message: "Data dapat diproses", issues: [], indicators: [], references: [] };

function fillBasic(stage: "mpasi" | "toddler") {
  fireEvent.change(screen.getByLabelText(/Tanggal lahir/i), { target: { value: stage === "mpasi" ? "2026-01-24" : "2023-09-24" } });
  fireEvent.change(screen.getByLabelText(/Jenis kelamin/i), { target: { value: "female" } });
  fireEvent.change(screen.getByLabelText(/Berat badan/i), { target: { value: stage === "mpasi" ? "8.2" : "14" } });
  fireEvent.change(screen.getByLabelText(/Panjang\/Tinggi badan/i), { target: { value: stage === "mpasi" ? "69" : "95" } });
}

beforeEach(() => {
  mockedApiFetch.mockReset();
  push.mockReset();
});

describe("Stage 3 nutrition profile", () => {
  it("calculates age months deterministically from date-only values", () => {
    expect(calculateAgeMonths("2026-03-24", "2026-09-24")).toBe(6);
    expect(calculateAgeMonths("2025-12-24", "2026-09-24")).toBe(9);
    expect(calculateAgeMonths("2025-09-24", "2026-09-24")).toBe(12);
    expect(calculateAgeMonths("2024-09-25", "2026-09-24")).toBe(23);
  });

  it("does not call the API on child field changes and retains local state", async () => {
    mockedApiFetch.mockResolvedValue(valid as never);
    render(<NutritionAssessment stage="mpasi" />);
    fillBasic("mpasi");
    expect(mockedApiFetch).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: /Lanjut/i }));
    await screen.findByText(/Eating Context · MPASI/i);
    expect(mockedApiFetch).toHaveBeenCalledTimes(1);

    fireEvent.change(screen.getByLabelText(/Pola pemberian susu/i), { target: { value: "breastmilk" } });
    fireEvent.click(screen.getByRole("checkbox", { name: /Telur/i }));
    fireEvent.change(screen.getByLabelText(/Frekuensi snack/i), { target: { value: "2" } });
    expect(mockedApiFetch).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: /Lanjut/i }));
    fireEvent.click(screen.getByRole("button", { name: /Kembali/i }));
    expect(screen.getByLabelText(/Pola pemberian susu/i)).toHaveValue("breastmilk");
    expect(screen.getByRole("checkbox", { name: /Telur/i })).toBeChecked();
    expect(screen.getByLabelText(/Frekuensi snack/i)).toHaveValue(2);
  });

  it("shows food rejection details conditionally", async () => {
    mockedApiFetch.mockResolvedValue(valid as never);
    render(<NutritionAssessment stage="mpasi" />);
    fillBasic("mpasi");
    fireEvent.click(screen.getByRole("button", { name: /Lanjut/i }));
    await screen.findByText(/Eating Context · MPASI/i);
    fireEvent.change(screen.getByLabelText(/Pola pemberian susu/i), { target: { value: "mixed" } });
    fireEvent.click(screen.getByRole("button", { name: /Lanjut/i }));

    expect(screen.queryByLabelText(/Makanan yang sering ditolak/i)).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/Penolakan makanan/i), { target: { value: "frequent" } });
    expect(screen.getByLabelText(/Makanan yang sering ditolak/i)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/Penolakan makanan/i), { target: { value: "none" } });
    expect(screen.queryByLabelText(/Makanan yang sering ditolak/i)).not.toBeInTheDocument();
  });

  it("shows sweetened beverage frequency only when exposure is selected", async () => {
    mockedApiFetch.mockResolvedValue(valid as never);
    render(<NutritionAssessment stage="toddler" />);
    fillBasic("toddler");
    fireEvent.click(screen.getByRole("button", { name: /Lanjut/i }));
    await screen.findByText(/Eating Context · Toddler/i);
    fireEvent.click(screen.getByRole("button", { name: /Lanjut/i }));

    expect(screen.queryByLabelText(/Hari dengan minuman berpemanis/i)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("checkbox", { name: /Ada paparan minuman berpemanis/i }));
    expect(screen.getByLabelText(/Hari dengan minuman berpemanis/i)).toBeInTheDocument();
    expect(mockedApiFetch).toHaveBeenCalledTimes(1);
  });

  it("keeps guest assessment usable through review without auth requests", async () => {
    mockedApiFetch.mockImplementation(async (path: string) => {
      if (path === "/api/nutrition/validate") return valid as never;
      if (path === "/api/nutrition/recommendation") return {
        stage: "toddler", category: "Nutrisi anak 24–59 bulan", age_band: "Toddler 24–59 bulan", personalization_status: "personalized_education", validation: valid,
        input_summary: [], summary: "Panduan edukatif", estimated_needs: {}, meal_pattern: {}, priority_nutrients: [], food_groups: [], recommendations: [], sample_menu: [], guidance: [], safety_notes: [], disclaimer: "Bukan diagnosis", references: [], suggested_goals: [], baseline: {}, detected_gaps: [], primary_gap: null, primary_target: null, support_targets: [],
      } as never;
      throw new Error(`Unexpected path ${path}`);
    });
    render(<NutritionAssessment stage="toddler" />);
    fillBasic("toddler");
    fireEvent.click(screen.getByRole("button", { name: /Lanjut/i }));
    await screen.findByText(/Eating Context · Toddler/i);
    fireEvent.click(screen.getByRole("button", { name: /Lanjut/i }));
    fireEvent.click(screen.getByRole("button", { name: /Lanjut/i }));
    expect(screen.getByText(/Review before analysis/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Analyze My Nutrition/i }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/nutrition/toddler/result"));
    expect(mockedApiFetch.mock.calls.map(([path]) => path)).toEqual([
      "/api/nutrition/validate",
      "/api/nutrition/validate",
      "/api/nutrition/recommendation",
    ]);
  });
});
