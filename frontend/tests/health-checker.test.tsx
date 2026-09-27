import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import HealthCheckerPage from "@/app/health-checker/page";
import { HEALTH_CHECKER_RESULT_STORAGE_KEY } from "@/lib/health-checker-types";
import { apiFetch } from "@/lib/api";

vi.mock("@/lib/api", () => ({ apiFetch: vi.fn(), API_BASE: "http://localhost:8000" }));
const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
const mockedApiFetch = vi.mocked(apiFetch);

const baseResult = {
  claim: "Makan sayur dan buah mendukung pola makan sehat.",
  original_claim: "Makan sayur dan buah mendukung pola makan sehat.",
  normalized_claim: "Makan sayur dan buah mendukung pola makan sehat.",
  claim_id: "claim-1-demo",
  claim_type: "NUTRITION",
  topic: "sayur buah",
  verdict: "SUPPORTED" as const,
  result: "SUPPORTED" as const,
  trust_score: 92,
  evidence_confidence: 88,
  confidence: 88,
  evidence_level: "HIGH" as const,
  score_breakdown: { source_authority: 1, evidence_quality: 0.96, recency: 1, relevance: 0.8, source_agreement: 1, independent_publishers: 1 },
  scoring_weights: { source_authority: 0.3, evidence_quality: 0.3, recency: 0.15, claim_relevance: 0.25 },
  explanation: "Evidence mendukung klaim.",
  summary: "Evidence mendukung klaim.",
  why_this_result: "Sumber relevan mendukung klaim.",
  reason: "Sumber relevan mendukung klaim.",
  supporting_evidence: [],
  contradicting_evidence: [],
  neutral_evidence: [],
  sources: [],
  sources_checked: 1,
  last_checked: "2026-09-18T15:00:00Z",
  limitations: ["Bukan diagnosis."],
  demo_evidence: true,
  retrieval_notes: [],
};

beforeEach(() => {
  mockedApiFetch.mockReset();
  push.mockClear();
  sessionStorage.clear();
});

describe("Health Checker final UX", () => {
  it("uses a compact single-column form without internal demo controls", () => {
    render(<HealthCheckerPage />);
    expect(screen.getByRole("heading", { name: /Periksa informasi kesehatan sebelum kamu mempercayainya/i })).toBeInTheDocument();
    expect(screen.queryByText(/Skenario demo engine/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Evidence investigation workspace/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Evidence first/i)).not.toBeInTheDocument();
  });

  it("submits pasted article text as multi-claim input", async () => {
    mockedApiFetch.mockResolvedValueOnce({ ...baseResult, run_id: "r1", input_type: "article", checked_claims: 1, claims: [baseResult] } as never);
    render(<HealthCheckerPage />);
    fireEvent.click(screen.getByRole("tab", { name: /Teks artikel/i }));
    fireEvent.change(screen.getByLabelText(/Teks artikel/i), { target: { value: "Makan sayur dan buah mendukung pola makan sehat. Ini adalah artikel yang cukup panjang untuk dianalisis." } });
    fireEvent.click(screen.getByRole("button", { name: /Periksa Informasi/i }));
    await waitFor(() => expect(mockedApiFetch).toHaveBeenCalled());
    expect(mockedApiFetch.mock.calls[0]?.[0]).toBe("/api/health-checker/analyze");
    expect(String(mockedApiFetch.mock.calls[0]?.[1]?.body)).toContain('"input_type":"article"');
    expect(push).toHaveBeenCalledWith("/health-checker/result");
    expect(sessionStorage.getItem(HEALTH_CHECKER_RESULT_STORAGE_KEY)).toContain('"run_id":"r1"');
  });

  it("submits an article URL to the dedicated safe URL endpoint", async () => {
    mockedApiFetch.mockResolvedValueOnce({ ...baseResult, run_id: "r2", input_type: "url", checked_claims: 1, claims: [baseResult], article: { title: "Artikel", text_length: 300 } } as never);
    render(<HealthCheckerPage />);
    fireEvent.click(screen.getByRole("tab", { name: /URL artikel/i }));
    fireEvent.change(screen.getByLabelText(/URL artikel/i), { target: { value: "https://example.com/health" } });
    fireEvent.click(screen.getByRole("button", { name: /Periksa Informasi/i }));
    await waitFor(() => expect(mockedApiFetch).toHaveBeenCalled());
    expect(mockedApiFetch.mock.calls[0]?.[0]).toBe("/api/health-checker/analyze-url");
    expect(push).toHaveBeenCalledWith("/health-checker/result");
    expect(sessionStorage.getItem(HEALTH_CHECKER_RESULT_STORAGE_KEY)).toContain('"run_id":"r2"');
  });

  it("navigates to the dedicated result page after analysis", async () => {
    mockedApiFetch.mockResolvedValueOnce({ ...baseResult, run_id: "r3", input_type: "claim", checked_claims: 1, claims: [baseResult] } as never);
    render(<HealthCheckerPage />);
    fireEvent.change(screen.getByRole("textbox", { name: "Informasi kesehatan" }), { target: { value: baseResult.claim } });
    fireEvent.click(screen.getByRole("button", { name: /Periksa Informasi/i }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/health-checker/result"));
    expect(sessionStorage.getItem(HEALTH_CHECKER_RESULT_STORAGE_KEY)).toContain('"run_id":"r3"');
  });

  it("rejects a malformed URL before calling the backend", () => {
    render(<HealthCheckerPage />);
    fireEvent.click(screen.getByRole("tab", { name: /URL artikel/i }));
    fireEvent.change(screen.getByLabelText(/URL artikel/i), { target: { value: "file:///etc/passwd" } });
    fireEvent.click(screen.getByRole("button", { name: /Periksa Informasi/i }));
    expect(screen.getByText(/Masukkan URL http\/https yang valid/i)).toBeInTheDocument();
    expect(mockedApiFetch).not.toHaveBeenCalled();
  });
});


it("rejects an API response whose claim does not match the submitted claim", async () => {
  mockedApiFetch.mockResolvedValueOnce({
    ...baseResult,
    claim: "Antibiotik tidak bekerja melawan virus.",
    original_claim: "Antibiotik tidak bekerja melawan virus.",
    normalized_claim: "Antibiotik tidak bekerja melawan virus.",
    run_id: "mismatch",
    input_type: "claim",
    checked_claims: 1,
    claims: [{ ...baseResult, claim: "Antibiotik tidak bekerja melawan virus.", original_claim: "Antibiotik tidak bekerja melawan virus.", normalized_claim: "Antibiotik tidak bekerja melawan virus." }],
  } as never);
  render(<HealthCheckerPage />);
  const submittedClaim = "mengonsumsi makanan atau minuman manis setiap hari dapat menyebabkan diabetes";
  fireEvent.change(screen.getByRole("textbox", { name: "Informasi kesehatan" }), { target: { value: submittedClaim } });
  fireEvent.click(screen.getByRole("button", { name: /Periksa Informasi/i }));
  await waitFor(() => expect(screen.getByText(/Data hasil pemeriksaan tidak sesuai/i)).toBeInTheDocument());
  expect(push).not.toHaveBeenCalled();
  expect(sessionStorage.getItem(HEALTH_CHECKER_RESULT_STORAGE_KEY)).toBeNull();
});

it("does not let a slower earlier request overwrite the latest request result", async () => {
  let resolveFirst!: (value: unknown) => void;
  let resolveSecond!: (value: unknown) => void;
  mockedApiFetch
    .mockReturnValueOnce(new Promise((resolve) => { resolveFirst = resolve; }) as never)
    .mockReturnValueOnce(new Promise((resolve) => { resolveSecond = resolve; }) as never);

  render(<HealthCheckerPage />);
  const textbox = screen.getByRole("textbox", { name: "Informasi kesehatan" });
  const form = screen.getByRole("form", { name: "Form pemeriksaan informasi kesehatan" });
  fireEvent.change(textbox, { target: { value: "Klaim A tentang kesehatan yang cukup panjang." } });
  fireEvent.submit(form);
  fireEvent.change(textbox, { target: { value: "Klaim B tentang kesehatan yang cukup panjang." } });
  fireEvent.submit(form);

  resolveFirst({ ...baseResult, claim: "Klaim A tentang kesehatan yang cukup panjang.", original_claim: "Klaim A tentang kesehatan yang cukup panjang.", normalized_claim: "Klaim A tentang kesehatan yang cukup panjang.", run_id: "slow-A", input_type: "claim", checked_claims: 1, claims: [{ ...baseResult, claim: "Klaim A tentang kesehatan yang cukup panjang.", original_claim: "Klaim A tentang kesehatan yang cukup panjang.", normalized_claim: "Klaim A tentang kesehatan yang cukup panjang." }] });
  await Promise.resolve();
  expect(sessionStorage.getItem(HEALTH_CHECKER_RESULT_STORAGE_KEY)).toBeNull();

  resolveSecond({ ...baseResult, claim: "Klaim B tentang kesehatan yang cukup panjang.", original_claim: "Klaim B tentang kesehatan yang cukup panjang.", normalized_claim: "Klaim B tentang kesehatan yang cukup panjang.", run_id: "fast-B", input_type: "claim", checked_claims: 1, claims: [{ ...baseResult, claim: "Klaim B tentang kesehatan yang cukup panjang.", original_claim: "Klaim B tentang kesehatan yang cukup panjang.", normalized_claim: "Klaim B tentang kesehatan yang cukup panjang." }] });
  await waitFor(() => expect(sessionStorage.getItem(HEALTH_CHECKER_RESULT_STORAGE_KEY)).toContain('"run_id":"fast-B"'));
});
