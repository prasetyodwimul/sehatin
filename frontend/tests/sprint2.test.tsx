import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import HomePage from "@/app/page";
import HealthCheckerPage from "@/app/health-checker/page";
import { BloodExplorer } from "@/components/blood-explorer";
import { BloodFacilityDetail } from "@/components/blood-facility-detail";
import { NutritionAssessment } from "@/components/nutrition-assessment";
import { NutritionResult } from "@/components/nutrition-result";
import { VerificationResult } from "@/components/verification-result";
import { apiFetch } from "@/lib/api";
import { HEALTH_CHECKER_RESULT_STORAGE_KEY } from "@/lib/health-checker-types";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  usePathname: () => "/",
}));
vi.mock("@/lib/api", () => ({
  API_BASE: "http://localhost:8000",
  ApiError: class ApiError extends Error {
    status: number;
    code?: string;
    constructor(message: string, status = 0, code?: string) {
      super(message); this.status = status; this.code = code;
    }
  },
  apiFetch: vi.fn(),
}));
const mockedApiFetch = vi.mocked(apiFetch);

const nutritionResponse = {
  stage: "mpasi" as const,
  category: "MPASI 6â€“23 bulan",
  age_band: "MPASI 6â€“8 bulan",
  personalization_status: "personalized_education" as const,
  validation: {
    status: "VALID" as const,
    can_process: true,
    message: "Data dapat diproses.",
    issues: [],
    indicators: [],
    references: [{ source: "World Health Organization", version: "WHO Child Growth Standards 2006" }],
  },
  summary: "Panduan edukatif sesuai tahap usia.",
  input_summary: ["Usia: 8 bulan", "Pola susu: ASI"],
  estimated_needs: { energi_dari_mpasi: "Sekitar 200 kkal/hari dari makanan pendamping." },
  meal_pattern: { meals: "2â€“3 kali makan/hari" },
  priority_nutrients: ["Zat besi"],
  food_groups: ["Protein hewani"],
  recommendations: ["Berikan makanan beragam."],
  sample_menu: ["Bubur nasi + ayam matang"],
  guidance: ["Naikkan tekstur bertahap sesuai kemampuan makan."],
  safety_notes: ["Bukan diagnosis."],
  disclaimer: "Informasi umum dan rekomendasi edukatif.",
  references: ["WHO complementary feeding guidance"],
};

const bloodFacility = {
  id: "demo-pmi",
  name: "PMI Kota Bandung",
  city: "Bandung",
  address: "Jl. Contoh",
  verified: false,
  last_updated: "2026-09-15T12:00:00Z",
  data_source: "SEHATIN Demo Provider",
  demo_data: true,
  data_mode: "SIMULATED" as const,
  refresh_hint_seconds: 60,
  inventory: [{ blood_type: "O" as const, rhesus: "+" as const, status: "AVAILABLE" as const, units: 12, quantity: 12 }],
};

const verificationResponse = {
  claim: "Antibiotik bisa menyembuhkan flu karena virus.",
  verdict: "CONTRADICTED" as const,
  result: "CONTRADICTED" as const,
  trust_score: 0,
  evidence_confidence: 92,
  confidence: 92,
  evidence_level: "HIGH" as const,
  score_breakdown: { source_authority: 1, evidence_quality: 0.95, recency: 1, relevance: 0.9, source_agreement: 1, independent_publishers: 2 },
  scoring_weights: { source_authority: 0.3, evidence_quality: 0.3, recency: 0.15, claim_relevance: 0.25 },
  explanation: "Evidence bertentangan dengan klaim.",
  summary: "Evidence yang tersedia bertentangan dengan klaim.",
  why_this_result: "Dua publisher independen searah.",
  reason: "Evidence resmi yang relevan tidak mendukung penggunaan antibiotik untuk infeksi virus.",
  supporting_evidence: [],
  contradicting_evidence: [{ id: "source-1", title: "Manage Common Cold", source: "CDC", source_type: "government", publication_date: "2026-03-11", retrieved_at: "2026-09-15", url: "https://www.cdc.gov/", stance: "contradict" as const, excerpt: "Antibiotik tidak bekerja melawan virus.", authority_level: 1, authority_score: 1, evidence_quality_score: 0.94, recency_score: 1, relevance_score: 0.9, weighted_score: 0.94, demo: true }],
  sources: [{ name: "CDC", title: "Manage Common Cold", source_type: "government", publication_date: "2026-03-11", url: "https://www.cdc.gov/", last_checked: "2026-09-15" }],
  sources_checked: 1,
  last_checked: "2026-09-15T12:00:00Z",
  limitations: ["Corpus demo."],
  demo_evidence: true,
};

beforeEach(() => {
  mockedApiFetch.mockReset();
  push.mockReset();
  sessionStorage.clear();
});

describe("SEHATIN final frontend journeys", () => {
  it("renders homepage product positioning and all core modules", () => {
    render(<HomePage />);
    expect(screen.getByRole("heading", { name: /Lebih mudah memahami informasi kesehatan./i })).toBeInTheDocument();
    expect(screen.getByText("Nutrition Assistant")).toBeInTheDocument();
    expect(screen.getByText("Blood Connect")).toBeInTheDocument();
    expect(screen.getByText("Health Information Checker")).toBeInTheDocument();

  });

  it("submits nutrition assessment, validates measurements, stores temporary result, and navigates to dedicated result page", async () => {
    mockedApiFetch.mockImplementation(async (path: string) => {
      if (path === "/api/nutrition/validate") return nutritionResponse.validation as never;
      if (path === "/api/nutrition/recommendation") return nutritionResponse as never;
      throw new Error("Unexpected API call");
    });
    render(<NutritionAssessment stage="mpasi" />);
    fireEvent.change(screen.getByLabelText(/Tanggal lahir/i), { target: { value: "2026-01-24" } });
    fireEvent.change(screen.getByLabelText(/Jenis kelamin/i), { target: { value: "male" } });
    fireEvent.change(screen.getByLabelText(/Berat badan/i), { target: { value: "8.2" } });
    fireEvent.change(screen.getByLabelText(/Panjang\/Tinggi badan/i), { target: { value: "69" } });
    fireEvent.click(screen.getByRole("button", { name: /Lanjut/i }));
    await screen.findByText(/Eating Context/i);
    fireEvent.change(screen.getByLabelText(/Pola pemberian susu/i), { target: { value: "breastmilk" } });
    fireEvent.click(screen.getByRole("button", { name: /Lanjut/i }));
    fireEvent.click(screen.getByRole("button", { name: /Lanjut/i }));
    fireEvent.click(screen.getByRole("button", { name: /Analyze My Nutrition/i }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/nutrition/mpasi/result"));
    expect(sessionStorage.getItem("sehatin:nutrition-result:mpasi")).toContain("MPASI 6â€“23 bulan");
    expect(sessionStorage.getItem("sehatin:nutrition-result:mpasi")).toContain('"height_cm":69');
  });

  it("renders the compact user-first nutrition result before program creation", async () => {
    sessionStorage.setItem("sehatin:nutrition-result:mpasi", JSON.stringify({ result: nutritionResponse, assessment: { stage: "mpasi", age_months: 8, sex: "male", weight_kg: 8.2, height_cm: 69, feeding_mode: "breastmilk" }, created_at: new Date().toISOString() }));
    render(<NutritionResult stage="mpasi" />);
    expect(await screen.findByText("Hasil Nutrition Assistant")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Apa yang paling penting untuk diperhatikan sekarang/i })).toBeInTheDocument();
    expect(screen.getByText(/^Fokus utama$/i)).toBeInTheDocument();
    expect(screen.getByText("8 bulan")).toBeInTheDocument();
    expect(screen.getByText("ASI + MPASI")).toBeInTheDocument();
    expect(screen.getByText(/Target utama/i)).toBeInTheDocument();
    expect(screen.getByText(/Program yang akan kamu jalankan/i)).toBeInTheDocument();
    expect(screen.getByText(/Program MPASI · 14 hari/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Beri nama program/i)).toHaveValue("Program MPASI");
    expect(screen.getByText(/200 kkal/i)).toBeInTheDocument();
    fireEvent.click(screen.getByText(/Lihat dasar rekomendasi & referensi/i));
    expect(screen.getByText(/WHO complementary feeding guidance/i)).toBeInTheDocument();
    expect(screen.queryByText(/Stage 3 · Profile & baseline/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Evidence Rule Engine/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/\{.*\}/)).not.toBeInTheDocument();
  });

  it("shows nutrition result empty state without crashing", async () => {
    render(<NutritionResult stage="toddler" />);
    expect(await screen.findByRole("heading", { name: /Selesaikan assessment lebih dulu/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Kembali ke Assessment/i })).toHaveAttribute("href", "/nutrition/toddler");
  });

  it("loads Blood Connect simulated inventory with quantity, status, and mode", async () => {
    mockedApiFetch.mockResolvedValue(bloodFacility ? [bloodFacility] : []);
    render(<BloodExplorer />);
    expect(await screen.findByText("PMI Kota Bandung")).toBeInTheDocument();
    expect(screen.getByText("Tersedia")).toBeInTheDocument();
    expect(screen.getByText(/12 unit/i)).toBeInTheDocument();
    
    
  });

  it("renders Blood facility detail with provenance and simulated status", async () => {
    mockedApiFetch.mockResolvedValueOnce(bloodFacility);
    render(<BloodFacilityDetail facilityId="demo-pmi" />);
    expect(await screen.findByText("Ketersediaan darah")).toBeInTheDocument();
    expect(screen.getByText("Sumber data")).toBeInTheDocument();
    
    expect(screen.getByText("SEHATIN Demo Provider")).toBeInTheDocument();
  });

  it("submits Health Checker claim, stores result, and navigates to dedicated result page", async () => {
    mockedApiFetch.mockResolvedValueOnce(verificationResponse);

    render(<HealthCheckerPage />);

    fireEvent.change(
      screen.getByRole("textbox", { name: "Informasi kesehatan" }),
      { target: { value: verificationResponse.claim } },
    );

    fireEvent.click(
      screen.getByRole("button", { name: /Periksa Informasi/i }),
    );

    await waitFor(() => {
      expect(mockedApiFetch).toHaveBeenCalledWith(
        "/api/health-checker/analyze",
        expect.objectContaining({
          method: "POST",
        }),
      );
    });

    expect(
      sessionStorage.getItem(HEALTH_CHECKER_RESULT_STORAGE_KEY),
    ).toContain(verificationResponse.claim);

    expect(push).toHaveBeenCalledWith("/health-checker/result");
  });

  it("shows insufficient evidence state without inventing an answer", () => {
    render(<VerificationResult result={{ ...verificationResponse, verdict: "INSUFFICIENT_EVIDENCE", result: "INSUFFICIENT_EVIDENCE", trust_score: 0, confidence: 0, evidence_confidence: 0, evidence_level: "INSUFFICIENT", supporting_evidence: [], contradicting_evidence: [], sources: [], sources_checked: 0 }} />);
    expect(screen.getByText("Belum cukup bukti")).toBeInTheDocument();
    expect(screen.getByText(/Sumber yang ditemukan membahas topik terkait, tetapi belum cukup untuk memastikan hubungan dalam informasi ini/i)).toBeInTheDocument();
  });

  it("shows safe Health Checker error state", async () => {
    mockedApiFetch.mockRejectedValueOnce(new Error("Analisis belum dapat dilakukan. Silakan coba lagi."));
    render(<HealthCheckerPage />);
    fireEvent.change(screen.getByRole("textbox", { name: "Informasi kesehatan" }), { target: { value: "Klaim kesehatan contoh yang cukup panjang." } });
    fireEvent.click(screen.getByRole("button", { name: /Periksa Informasi/i }));
    expect(await screen.findByText("Analisis belum dapat dilakukan. Silakan coba lagi.")).toBeInTheDocument();
  });
  it("shows nutrition processing state while recommendation is being prepared", async () => {
    mockedApiFetch.mockImplementation((path: string) => {
      if (path === "/api/nutrition/validate") return Promise.resolve(nutritionResponse.validation as never);
      return new Promise(() => {});
    });
    render(<NutritionAssessment stage="mpasi" />);
    fireEvent.change(screen.getByLabelText(/Tanggal lahir/i), { target: { value: "2026-01-24" } });
    fireEvent.change(screen.getByLabelText(/Jenis kelamin/i), { target: { value: "male" } });
    fireEvent.change(screen.getByLabelText(/Berat badan/i), { target: { value: "8.2" } });
    fireEvent.change(screen.getByLabelText(/Panjang\/Tinggi badan/i), { target: { value: "69" } });
    fireEvent.click(screen.getByRole("button", { name: /Lanjut/i }));
    await screen.findByText(/Eating Context/i);
    fireEvent.change(screen.getByLabelText(/Pola pemberian susu/i), { target: { value: "breastmilk" } });
    fireEvent.click(screen.getByRole("button", { name: /Lanjut/i }));
    fireEvent.click(screen.getByRole("button", { name: /Lanjut/i }));
    fireEvent.click(screen.getByRole("button", { name: /Analyze My Nutrition/i }));
    expect(await screen.findByText(/Preparing your nutrition guidance/i)).toBeInTheDocument();
  });

  it("shows Blood Connect empty state when no availability matches", async () => {
    mockedApiFetch.mockResolvedValueOnce([]);
    render(<BloodExplorer />);
    expect(await screen.findByText(/Belum ada fasilitas yang cocok/i)).toBeInTheDocument();
    expect(screen.getByText(/No Availability/i)).toBeInTheDocument();
  });

  it("shows Blood Connect safe error state when backend is unavailable", async () => {
    mockedApiFetch.mockRejectedValueOnce(new Error("Data darah belum dapat dimuat."));
    render(<BloodExplorer />);
    expect(await screen.findByText(/Data darah belum dapat dimuat/i)).toBeInTheDocument();
  });

  it("shows only compact button loading while evidence is being checked", async () => {
    mockedApiFetch.mockImplementationOnce(() => new Promise(() => {}));
    render(<HealthCheckerPage />);
    fireEvent.change(screen.getByRole("textbox", { name: "Informasi kesehatan" }), { target: { value: verificationResponse.claim } });
    fireEvent.click(screen.getByRole("button", { name: /Periksa Informasi/i }));
    expect(screen.queryByRole("heading", { name: /Sebentar, kami sedang mencari sumber yang relevan/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Sedang memeriksa/i })).toBeDisabled();
  });

});





