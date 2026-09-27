import { Alert, Badge } from "@/components/ui";
import { EvidenceCard, type EvidenceView } from "@/components/evidence-card";
import { SourceCard, type SourceView } from "@/components/source-card";
import { Reveal } from "@/components/motion";
import { Check, CircleAlert, CircleHelp, ShieldCheck, ArrowDown, BookOpen, FileCheck2, Info, Sparkles } from "lucide-react";

export type Verdict = "SUPPORTED" | "PARTIALLY_SUPPORTED" | "INSUFFICIENT_EVIDENCE" | "CONTRADICTED";
export type VerificationData = {
  claim: string;
  verdict: Verdict;
  result: Verdict;
  trust_score: number;
  evidence_confidence: number;
  confidence: number;
  evidence_level?: "HIGH" | "MODERATE" | "LOW" | "INSUFFICIENT";
  confidence_label?: "HIGH" | "MODERATE" | "LOW" | "INSUFFICIENT" | null;
  score_breakdown: {
    source_authority: number;
    evidence_quality: number;
    recency: number;
    relevance: number;
    source_agreement: number;
    independent_publishers: number;
  };
  scoring_weights?: { source_authority: number; evidence_quality: number; recency: number; claim_relevance: number };
  explanation: string;
  summary: string;
  why_this_result: string;
  reason: string;
  supporting_evidence: EvidenceView[];
  contradicting_evidence: EvidenceView[];
  neutral_evidence?: EvidenceView[];
  sources: SourceView[];
  sources_checked: number;
  last_checked: string;
  limitations: string[];
  demo_evidence: boolean;
  original_claim?: string | null;
  normalized_claim?: string | null;
  claim_id?: string | null;
  claim_type?: string | null;
  topic?: string | null;
  retrieval_notes?: string[];
};

const META: Record<Verdict, { label: string; variant: "success" | "warning" | "neutral" | "error"; sentence: string; icon: typeof Check; meaning: string; tone: string; soft: string }> = {
  SUPPORTED: {
    label: "Didukung",
    variant: "success",
    sentence: "Sumber yang relevan menunjukkan hasil yang sejalan dengan informasi ini.",
    meaning: "Bukti yang ditemukan cukup konsisten untuk mendukung informasi yang kamu masukkan.",
    icon: Check,
    tone: "text-success border-success/20 bg-success/10",
    soft: "bg-success/10 text-success",
  },
  PARTIALLY_SUPPORTED: {
    label: "Sebagian didukung",
    variant: "warning",
    sentence: "Ada bukti yang mendukung, tetapi kesimpulannya masih memiliki batasan.",
    meaning: "Sumber yang relevan mendukung sebagian hubungan dalam informasi ini, tetapi belum cukup untuk menganggap seluruh kalimat sebagai fakta yang pasti.",
    icon: CircleAlert,
    tone: "text-warning border-warning/20 bg-warning/10",
    soft: "bg-warning/10 text-warning",
  },
  INSUFFICIENT_EVIDENCE: {
    label: "Belum cukup bukti",
    variant: "neutral",
    sentence: "Sumber terkait tersedia, tetapi belum cukup untuk memastikan informasi ini.",
    meaning: "Ada informasi yang berkaitan, tetapi bukti yang ditemukan belum cukup kuat atau belum membahas hubungan yang kamu masukkan secara langsung.",
    icon: CircleHelp,
    tone: "text-secondary border-line bg-surface",
    soft: "bg-slate-100 text-secondary",
  },
  CONTRADICTED: {
    label: "Tidak didukung",
    variant: "error",
    sentence: "Sumber yang relevan menunjukkan hasil yang berbeda dari informasi ini.",
    meaning: "Bukti yang ditemukan lebih banyak menunjukkan hasil yang berbeda atau tidak mendukung informasi yang kamu masukkan.",
    icon: CircleAlert,
    tone: "text-error border-error/20 bg-error/10",
    soft: "bg-error/10 text-error",
  },
};

function confidenceText(result: VerificationData) {
  const label = result.confidence_label ?? result.evidence_level;
  if (label === "HIGH") return "Tinggi";
  if (label === "MODERATE") return "Sedang";
  if (label === "LOW") return "Rendah";
  if (label === "INSUFFICIENT") return "Belum cukup";
  const score = result.confidence ?? result.evidence_confidence;
  if (score >= 80) return "Tinggi";
  if (score >= 60) return "Sedang";
  if (score >= 40) return "Rendah";
  return "Belum cukup";
}

function confidenceScore(result: VerificationData) {
  const raw = result.confidence ?? result.evidence_confidence ?? 0;
  return Math.max(0, Math.min(100, Math.round(raw)));
}

function humanClaimType(value?: string | null) {
  if (!value) return null;
  const labels: Record<string, string> = { NUTRITION: "Nutrisi", GENERAL_HEALTH: "Kesehatan umum" };
  return labels[value] ?? value.replaceAll("_", " ").toLowerCase().replace(/(^|\s)\S/g, (letter) => letter.toUpperCase());
}

function StatCard({ icon: Icon, value, label, detail }: { icon: typeof FileCheck2; value: string | number; label: string; detail: string }) {
  return (
    <div className="rounded-2xl border border-line bg-white p-5 shadow-[0_10px_30px_rgba(15,64,58,.05)]">
      <div className="flex items-start justify-between gap-4">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary-light text-primary-dark"><Icon size={18} aria-hidden="true" /></span>
        <span className="text-2xl font-bold tracking-[-0.04em]">{value}</span>
      </div>
      <p className="mt-4 text-sm font-semibold">{label}</p>
      <p className="mt-1 text-xs leading-5 text-muted">{detail}</p>
    </div>
  );
}

function EvidenceOverview({ result }: { result: VerificationData }) {
  const support = result.supporting_evidence.length;
  const different = result.contradicting_evidence.length;
  const context = result.neutral_evidence?.length ?? 0;
  const total = support + different + context;
  return (
    <div className="rounded-3xl border border-line bg-white p-5 shadow-[0_14px_40px_rgba(15,64,58,.06)] md:p-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow">Peta bukti</p>
          <h3 className="mt-2 text-xl font-semibold tracking-[-0.03em]">Apa yang ditemukan SEHATIN?</h3>
        </div>
        <span className="rounded-full bg-background px-3 py-1.5 text-xs font-semibold text-secondary">{total} sumber relevan</span>
      </div>
      <div className="mt-6 grid grid-cols-3 gap-2">
        <div className="rounded-2xl bg-success/10 p-4"><p className="text-2xl font-bold text-success">{support}</p><p className="mt-1 text-xs font-medium text-success">Mendukung</p></div>
        <div className="rounded-2xl bg-error/10 p-4"><p className="text-2xl font-bold text-error">{different}</p><p className="mt-1 text-xs font-medium text-error">Berbeda</p></div>
        <div className="rounded-2xl bg-slate-100 p-4"><p className="text-2xl font-bold text-secondary">{context}</p><p className="mt-1 text-xs font-medium text-secondary">Konteks</p></div>
      </div>
      <div className="mt-5 flex items-center gap-2 text-xs text-muted">
        <Info size={14} aria-hidden="true" />
        <span>Sumber konteks tidak dipakai untuk menentukan benar atau salah.</span>
      </div>
    </div>
  );
}

export function VerificationResult({ result }: { result: VerificationData }) {
  const meta = META[result.verdict];
  const neutral = result.neutral_evidence ?? [];
  const Icon = meta.icon;
  const confidence = confidenceText(result);
  const score = confidenceScore(result);
  const claimType = humanClaimType(result.claim_type);

  return (
    <div className="space-y-8">
      <Reveal>
        <section className="relative overflow-hidden rounded-[30px] border border-line bg-white shadow-[0_22px_70px_rgba(15,64,58,.08)]">
          <div className="absolute inset-x-0 top-0 h-1.5 bg-primary" aria-hidden="true" />
          <div className="absolute -right-28 -top-28 h-64 w-64 rounded-full bg-primary-light/70 blur-2xl" aria-hidden="true" />
          <div className="relative grid gap-8 p-6 md:p-8 lg:grid-cols-[minmax(0,1fr)_290px] lg:p-10">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <p className="eyebrow">Hasil pemeriksaan</p>
                {claimType && <Badge variant="neutral">{claimType}</Badge>}
              </div>
              <div className={`mt-6 inline-flex items-center gap-3 rounded-full border px-4 py-2.5 ${meta.tone}`}>
                <span className={`flex h-9 w-9 items-center justify-center rounded-full ${meta.soft}`}><Icon size={19} aria-hidden="true" /></span>
                <span className="text-sm font-bold">{meta.label}</span>
              </div>
              <h2 className="mt-5 max-w-4xl text-3xl font-semibold leading-tight tracking-[-0.04em] md:text-4xl">“{result.original_claim || result.claim}”</h2>
              <p className="mt-4 max-w-3xl text-base leading-7 text-secondary">{meta.sentence}</p>
              <div className="mt-6 flex flex-wrap gap-2 text-xs font-medium text-muted">
                <span className="rounded-full border border-line bg-background px-3 py-1.5">{result.sources_checked} sumber diperiksa</span>
                <span className="rounded-full border border-line bg-background px-3 py-1.5">{result.score_breakdown.independent_publishers} sumber berbeda</span>
              </div>
            </div>

            <div className="flex flex-col items-center justify-center rounded-3xl border border-primary/10 bg-primary-light/45 p-6 text-center">
              <div
                className="relative flex h-40 w-40 items-center justify-center rounded-full"
                style={{ background: `conic-gradient(var(--color-primary) ${score * 3.6}deg, rgba(15,118,110,.10) 0deg)` }}
                aria-label={`Kekuatan bukti ${confidence}, ${score} persen`}
              >
                <div className="flex h-32 w-32 flex-col items-center justify-center rounded-full bg-white shadow-inner">
                  <ShieldCheck size={21} className="text-primary-dark" aria-hidden="true" />
                  <span className="mt-1 text-3xl font-bold tracking-[-0.05em]">{score}%</span>
                  <span className="text-[11px] font-semibold text-muted">kekuatan bukti</span>
                </div>
              </div>
              <p className="mt-5 text-base font-bold text-primary-dark">{confidence}</p>
              <p className="mt-1 max-w-[220px] text-xs leading-5 text-secondary">Bukan jaminan mutlak, tetapi gambaran konsistensi bukti yang ditemukan.</p>
            </div>
          </div>
        </section>
      </Reveal>

      <Reveal delay={60}>
        <section className="grid gap-4 md:grid-cols-3">
          <StatCard icon={BookOpen} value={result.sources_checked} label="Sumber diperiksa" detail="Sumber yang relevan dengan pemeriksaan ini." />
          <StatCard icon={FileCheck2} value={result.supporting_evidence.length} label="Bukti mendukung" detail="Sumber yang cukup relevan untuk mendukung klaim." />
          <StatCard icon={ShieldCheck} value={confidence} label="Kekuatan bukti" detail="Seberapa konsisten sumber yang relevan." />
        </section>
      </Reveal>

      <Reveal delay={90}>
        <section className="grid gap-6 lg:grid-cols-[1.05fr_.95fr]">
          <div className="rounded-3xl border border-line bg-white p-6 shadow-[0_14px_40px_rgba(15,64,58,.05)] md:p-7">
            <div className="flex items-center gap-3">
              <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary-light text-primary-dark"><Sparkles size={19} aria-hidden="true" /></span>
              <div><p className="eyebrow">Ringkasan</p><h3 className="mt-1 text-xl font-semibold tracking-[-0.03em]">Jadi, apa artinya?</h3></div>
            </div>
            <p className="mt-6 text-base leading-7 text-secondary">{meta.meaning}</p>
            <div className="mt-5 rounded-2xl bg-background p-4">
              <p className="text-sm font-semibold">Dasar hasil pemeriksaan</p>
              <p className="mt-2 text-sm leading-6 text-secondary">{result.reason || result.why_this_result || result.explanation}</p>
            </div>
          </div>
          <EvidenceOverview result={result} />
        </section>
      </Reveal>

      <div className="flex justify-center" aria-hidden="true"><span className="flex h-9 w-9 items-center justify-center rounded-full border border-line bg-white text-muted"><ArrowDown size={16} /></span></div>

      {result.verdict === "INSUFFICIENT_EVIDENCE" && (
        <Reveal delay={110}>
          <Alert variant="warning" title="Belum cukup untuk memastikan">Sumber yang ditemukan membahas topik terkait, tetapi belum cukup untuk memastikan hubungan dalam informasi ini. Ini berbeda dari kesimpulan “salah”.</Alert>
        </Reveal>
      )}

      {result.supporting_evidence.length > 0 && <Reveal delay={120}><section className="rounded-3xl border border-line bg-white p-6 md:p-8"><p className="eyebrow">Bukti pendukung</p><h3 className="mt-3 text-2xl font-semibold tracking-[-0.03em]">Sumber yang mendukung</h3><p className="mt-2 max-w-3xl text-sm leading-6 text-secondary">Sumber di bawah dipilih karena membahas bagian yang relevan dengan informasi yang kamu masukkan.</p><div className="mt-5 divide-y divide-line">{result.supporting_evidence.map((item) => <EvidenceCard key={item.id} evidence={item} />)}</div></section></Reveal>}
      {result.contradicting_evidence.length > 0 && (
        <Reveal delay={140}>
          <section className="rounded-3xl border border-error/15 bg-error/5 p-6 md:p-8">
            <p className="eyebrow">Bukti berbeda</p>
            <h3 className="mt-3 text-2xl font-semibold tracking-[-0.03em]">Ada sumber dengan hasil berbeda</h3>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-secondary">Sumber ini tetap relevan, tetapi memberikan hasil yang berbeda atau membatasi kesimpulan dari informasi yang kamu masukkan.</p>
            <div className="mt-5 divide-y divide-error/10">{result.contradicting_evidence.map((item) => <EvidenceCard key={item.id} evidence={item} />)}</div>
          </section>
        </Reveal>
      )}
      {neutral.length > 0 && (
        <Reveal delay={160}>
          <section className="rounded-3xl border border-line bg-background p-6 md:p-8">
            <p className="eyebrow">Konteks tambahan</p>
            <h3 className="mt-3 text-2xl font-semibold tracking-[-0.03em]">Sumber yang berkaitan</h3>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-secondary">Sumber berikut membantu memberi konteks, tetapi tidak dipakai untuk menentukan apakah informasi kamu benar atau salah.</p>
            <div className="mt-5 divide-y divide-line">{neutral.map((item) => <EvidenceCard key={item.id} evidence={item} />)}</div>
          </section>
        </Reveal>
      )}

      {result.sources.length > 0 && <Reveal delay={180}><section className="rounded-3xl border border-line bg-white p-6 md:p-8"><div className="flex flex-wrap items-end justify-between gap-4"><div><p className="eyebrow">Sumber</p><h3 className="mt-3 text-2xl font-semibold tracking-[-0.03em]">Kalau kamu ingin mengecek lebih lanjut</h3></div><span className="rounded-full bg-background px-3 py-1.5 text-xs font-semibold text-secondary">{result.sources.length} sumber</span></div><div className="mt-5 grid gap-x-8 md:grid-cols-2">{result.sources.map((source) => <SourceCard key={`${source.url}-${source.title}`} source={source} />)}</div></section></Reveal>}

      <section className="grid gap-4 md:grid-cols-2">
        <Alert variant="info" title="Perlu diingat">Hasil ini dibuat dari sumber yang tersedia saat pemeriksaan dan dapat berubah ketika ada informasi baru.</Alert>
        <Alert variant="warning" title="Bukan diagnosis medis">Health Checker membantu mengevaluasi informasi. Untuk kondisi atau keputusan kesehatan pribadi, gunakan tenaga kesehatan yang berkualifikasi bila diperlukan.</Alert>
      </section>
    </div>
  );
}
