"use client";

import { FormEvent, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { Container } from "@/components/layout";
import { Alert, Button, Input, Textarea } from "@/components/ui";
import { type HealthRun, type InputType, HEALTH_CHECKER_REQUEST_CLAIM_STORAGE_KEY, HEALTH_CHECKER_RESULT_STORAGE_KEY } from "@/lib/health-checker-types";
import { apiFetch } from "@/lib/api";
import { Reveal } from "@/components/motion";

const INPUT_OPTIONS: { value: InputType; label: string; description: string }[] = [
  { value: "claim", label: "Klaim", description: "Periksa satu pernyataan kesehatan." },
  { value: "article", label: "Teks artikel", description: "Periksa beberapa informasi dari teks artikel." },
  { value: "url", label: "URL artikel", description: "Periksa informasi dari artikel yang kamu bagikan." },
];

export default function HealthCheckerPage() {
  const [inputType, setInputType] = useState<InputType>("claim");
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const latestRequestId = useRef<string | null>(null);

  function chooseType(value: InputType) {
    setInputType(value);
    setError("");
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");

    const claim = text.trim();
    const articleUrl = url.trim();
    if (inputType === "claim" && claim.length < 8) {
      setError("Masukkan informasi kesehatan minimal 8 karakter.");
      return;
    }
    if (inputType === "article" && claim.length < 20) {
      setError("Masukkan teks artikel yang cukup lengkap untuk diperiksa.");
      return;
    }
    if (inputType === "url" && !/^https?:\/\//i.test(articleUrl)) {
      setError("Masukkan URL http/https yang valid.");
      return;
    }

    setLoading(true);
    setError("");
    // A new check always invalidates the previous result before the request starts.
    sessionStorage.removeItem(HEALTH_CHECKER_RESULT_STORAGE_KEY);
    if (inputType === "claim") {
      sessionStorage.setItem(HEALTH_CHECKER_REQUEST_CLAIM_STORAGE_KEY, claim);
    } else {
      sessionStorage.removeItem(HEALTH_CHECKER_REQUEST_CLAIM_STORAGE_KEY);
    }

    const requestId = typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random()}`;
    latestRequestId.current = requestId;

    try {
      const path = inputType === "url" ? "/api/health-checker/analyze-url" : "/api/health-checker/analyze";
      const body = inputType === "url" ? { input_type: "url", url: articleUrl } : { input_type: inputType, text: claim };
      const response = await apiFetch<HealthRun>(path, { method: "POST", body: JSON.stringify(body), timeoutMs: inputType === "url" ? 45_000 : 40_000 });

      if (latestRequestId.current !== requestId) return;

      const firstResult = response.claims?.[0] ?? response;
      if (inputType === "claim" && firstResult.claim !== claim) {
        throw new Error("Data hasil pemeriksaan tidak sesuai dengan informasi yang diperiksa.");
      }

      sessionStorage.setItem(HEALTH_CHECKER_RESULT_STORAGE_KEY, JSON.stringify(response));
      router.push("/health-checker/result");
    } catch (err) {
      if (latestRequestId.current !== requestId) return;
      setError(err instanceof Error ? err.message : "Pemeriksaan belum dapat dilakukan. Silakan coba lagi.");
    } finally {
      if (latestRequestId.current === requestId) setLoading(false);
    }
  }

  return (
    <>
      <section className="border-b border-line bg-surface">
        <Container className="flex min-h-[30vh] items-center py-10 md:min-h-[28vh] md:py-12">
          <Reveal>
            <p className="eyebrow">Health Information Checker</p>
            <h1 className="mt-3 max-w-4xl text-4xl font-semibold leading-[1.02] tracking-[-0.045em] md:text-5xl lg:text-[56px]">Periksa informasi kesehatan sebelum kamu mempercayainya.</h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-secondary md:text-lg">Masukkan informasi yang ingin kamu periksa. SEHATIN membantu melihat sumber yang tersedia dan menjelaskan dasar hasilnya dengan bahasa yang mudah dipahami.</p>
          </Reveal>
        </Container>
      </section>

      <Container className="py-10 md:py-14">
        <Reveal>
          <form onSubmit={submit} className="mx-auto max-w-3xl space-y-7" aria-label="Form pemeriksaan informasi kesehatan">
            <div>
              <p className="eyebrow">Mulai pemeriksaan</p>
              <h2 className="mt-3 text-3xl font-semibold tracking-[-0.04em] md:text-4xl">Apa yang ingin kamu periksa?</h2>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-secondary">Pilih jenis informasi, lalu masukkan teks atau URL yang ingin diperiksa. Jangan masukkan identitas, rekam medis, atau data pribadi yang tidak diperlukan.</p>
            </div>

            <div className="space-y-2" role="tablist" aria-label="Jenis input Health Checker">
              {INPUT_OPTIONS.map((option) => {
                const active = inputType === option.value;
                return (
                  <button
                    key={option.value}
                    type="button"
                    role="tab"
                    aria-selected={active}
                    onClick={() => chooseType(option.value)}
                    className={`flex min-h-16 w-full items-center justify-between rounded-xl border px-5 py-4 text-left transition-colors ${active ? "border-primary bg-primary-light text-primary-dark" : "border-line bg-surface text-secondary hover:border-primary/40"}`}
                  >
                    <span>
                      <span className="block text-sm font-semibold">{option.label}</span>
                      <span className="mt-1 block text-xs leading-5 text-muted">{option.description}</span>
                    </span>
                    <ArrowRight size={17} aria-hidden="true" className={active ? "text-primary-dark" : "text-muted"} />
                  </button>
                );
              })}
            </div>

            {inputType === "url" ? (
              <Input
                label="URL artikel"
                type="url"
                value={url}
                onChange={(event) => setUrl(event.target.value)}
                placeholder="https://example.org/artikel-kesehatan"
                required
                maxLength={2048}
                helperText="Gunakan URL http/https yang dapat diakses secara publik."
              />
            ) : (
              <Textarea
                label={inputType === "article" ? "Teks artikel" : "Informasi kesehatan"}
                value={text}
                onChange={(event) => setText(event.target.value)}
                required
                minLength={inputType === "article" ? 20 : 8}
                maxLength={inputType === "article" ? 20_000 : 5_000}
                rows={inputType === "article" ? 10 : 7}
                placeholder={inputType === "article" ? "Tempel teks artikel kesehatan di sini..." : "Contoh: Makan sayur dan buah mendukung pola makan sehat."}
                helperText={inputType === "article" ? "SEHATIN akan menemukan informasi yang dapat diperiksa dari teks tersebut." : "Tulis satu informasi yang spesifik agar hasil lebih mudah dipahami."}
              />
            )}

            {error && <Alert variant="error" title="Pemeriksaan belum dapat dilakukan">{error}</Alert>}
            <Button type="submit" size="lg" isLoading={loading} loadingLabel="Sedang memeriksa...">Periksa Informasi <ArrowRight size={17} /></Button>
            <p className="text-xs leading-5 text-muted">Hasil Health Checker adalah informasi pendukung, bukan diagnosis medis atau pengganti saran tenaga kesehatan.</p>
          </form>
        </Reveal>

      </Container>
    </>
  );
}
