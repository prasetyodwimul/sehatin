"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Container } from "@/components/layout";
import { getButtonClasses } from "@/components/button-styles";
import { VerificationResult } from "@/components/verification-result";
import { type HealthRun, HEALTH_CHECKER_REQUEST_CLAIM_STORAGE_KEY, HEALTH_CHECKER_RESULT_STORAGE_KEY } from "@/lib/health-checker-types";

export default function HealthCheckerResultPage() {
  const [run, setRun] = useState<HealthRun | null>(null);
  const [selectedClaim, setSelectedClaim] = useState(0);
  const [ready, setReady] = useState(false);
  const [claimMismatch, setClaimMismatch] = useState(false);

  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "auto" });
    try {
      const raw = sessionStorage.getItem(HEALTH_CHECKER_RESULT_STORAGE_KEY);
      const expectedClaim = sessionStorage.getItem(HEALTH_CHECKER_REQUEST_CLAIM_STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as HealthRun;
        const firstResult = parsed.claims?.[0] ?? parsed;
        if (expectedClaim && firstResult.claim !== expectedClaim) {
          sessionStorage.removeItem(HEALTH_CHECKER_RESULT_STORAGE_KEY);
          setClaimMismatch(true);
        } else {
          setRun(parsed);
        }
      }
    } catch {
      setRun(null);
    } finally {
      setReady(true);
    }
  }, []);

  const activeResult = useMemo(() => {
    if (!run) return null;
    const claims = run.claims?.length ? run.claims : [run];
    return claims[Math.min(selectedClaim, claims.length - 1)] ?? run;
  }, [run, selectedClaim]);

  if (!ready) {
    return (
      <Container className="py-20">
        <p className="eyebrow">Health Checker</p>
        <h1 className="mt-4 text-3xl font-semibold tracking-[-0.04em]">Memuat hasil pemeriksaan...</h1>
      </Container>
    );
  }

  if (claimMismatch) {
    return (
      <Container className="py-16 md:py-24">
        <div className="max-w-2xl border-y border-line py-10">
          <p className="eyebrow">Health Checker · Hasil</p>
          <h1 className="mt-4 text-4xl font-semibold tracking-[-0.04em]">Hasil pemeriksaan tidak sesuai.</h1>
          <p className="mt-4 text-base leading-7 text-secondary">Data hasil pemeriksaan tidak sesuai dengan informasi yang diperiksa. Silakan ulangi pemeriksaan.</p>
          <Link href="/health-checker" className={`mt-7 ${getButtonClasses()}`}><ArrowLeft size={17} /> Periksa informasi</Link>
        </div>
      </Container>
    );
  }

  if (!run || !activeResult) {
    return (
      <Container className="py-16 md:py-24">
        <div className="max-w-2xl border-y border-line py-10">
          <p className="eyebrow">Health Checker · Hasil</p>
          <h1 className="mt-4 text-4xl font-semibold tracking-[-0.04em]">Belum ada hasil pemeriksaan.</h1>
          <p className="mt-4 text-base leading-7 text-secondary">Silakan masukkan informasi kesehatan terlebih dahulu agar SEHATIN dapat menjalankan pemeriksaan.</p>
          <Link href="/health-checker" className={`mt-7 ${getButtonClasses()}`}><ArrowLeft size={17} /> Periksa informasi</Link>
        </div>
      </Container>
    );
  }

  const claims = run.claims?.length ? run.claims : [run];

  return (
    <Container className="py-10 md:py-14">
      <header className="mb-10 border-b border-line pb-8">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div>
            <nav aria-label="Breadcrumb" className="text-sm text-secondary">
              <Link href="/health-checker" className="hover:text-primary-dark">Health Checker</Link>
              <span className="mx-2" aria-hidden="true">›</span>
              <span>Hasil Pemeriksaan</span>
            </nav>
            <p className="eyebrow mt-7">Hasil pemeriksaan</p>
            <h1 className="mt-4 max-w-4xl text-4xl font-semibold leading-tight tracking-[-0.04em] md:text-5xl">Hasil pemeriksaan informasi kesehatan</h1>
            <p className="mt-4 max-w-3xl text-base leading-7 text-secondary">Berikut hasil pemeriksaan SEHATIN berdasarkan sumber kesehatan yang relevan.</p>
          </div>
          <Link href="/health-checker" className={`shrink-0 ${getButtonClasses({ variant: "secondary" })}`}><ArrowLeft size={17} /> Periksa informasi lain</Link>
        </div>
      </header>

      {claims.length > 1 && (
        <section className="mb-8 border-b border-line pb-7" aria-label="Pilih klaim hasil ekstraksi">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="eyebrow">Klaim dari input</p>
              <p className="mt-2 text-sm text-secondary">{claims.length} klaim diperiksa</p>
            </div>
            <div className="flex max-w-full gap-2 overflow-x-auto pb-1">
              {claims.map((claim, index) => (
                <button
                  key={claim.claim_id || `${index}-${claim.claim}`}
                  type="button"
                  onClick={() => setSelectedClaim(index)}
                  aria-pressed={selectedClaim === index}
                  className={`min-h-11 shrink-0 rounded-full border px-4 text-sm font-semibold transition-colors ${selectedClaim === index ? "border-primary bg-primary-light text-primary-dark" : "border-line bg-surface text-secondary hover:border-primary/40"}`}
                >
                  Klaim {index + 1} · {claim.verdict.replaceAll("_", " ")}
                </button>
              ))}
            </div>
          </div>
        </section>
      )}

      {run.article && (
        <section className="mb-8 rounded-xl border border-line bg-surface p-5">
          <p className="eyebrow">Artikel yang diperiksa</p>
          <p className="mt-2 font-semibold">{run.article.title || "Artikel dari URL"}</p>
          <p className="mt-1 text-sm leading-6 text-muted">
            {run.article.publisher || "Publisher tidak tersedia"}
            {run.article.published_date ? ` · ${run.article.published_date}` : ""}
          </p>
        </section>
      )}

      <VerificationResult result={activeResult} />
    </Container>
  );
}
