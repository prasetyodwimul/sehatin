"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowDown, ArrowRight, CalendarDays, Check, CheckCircle2, ListChecks, LockKeyhole, Save, Soup, Sparkles, Target, UtensilsCrossed, type LucideIcon } from "lucide-react";
import { AuthGate } from "@/components/auth-gate";
import { useAuth } from "@/components/auth-provider";
import { MealIllustration, foodGroupsFrom } from "@/components/nutrition-visuals";
import { Alert, Badge, Button } from "@/components/ui";
import { ViewportModal } from "@/components/viewport-modal";
import { getButtonClasses } from "@/components/button-styles";
import {
  createNutritionProgram,
  listNutritionPrograms,
  markNutritionProgramEntry,
  type ProgramSummary,
} from "@/lib/nutrition-program";
import { loadNutritionSession, nutritionAssessmentPath, type NutritionResultSession, type NutritionStage, type NutritionTargetCandidate } from "@/lib/nutrition";
import { formatMenuDisplayTitle } from "@/lib/nutrition-menu-presentation";

function humanize(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}


function formatStage3Value(value: unknown): string {
  if (value === null || value === undefined || value === "") return "Belum dicatat";
  if (typeof value === "boolean") return value ? "Ya" : "Tidak";
  if (Array.isArray(value)) return value.length ? value.map((item) => humanize(String(item))).join(", ") : "Belum dicatat";
  if (typeof value === "object" && value && "value" in value) {
    const row = value as { value?: unknown; unit?: string };
    const base: string = formatStage3Value(row.value);
    return row.unit ? `${base} ${row.unit.replace(/_/g, " ")}` : base;
  }
  return humanize(String(value));
}

function TargetCandidateCard({ target, title }: { target: NutritionTargetCandidate; title: string }) {
  return <article className="border-t border-line pt-4"><p className="text-[10px] font-black uppercase tracking-[.12em] text-primary-dark">{title}</p><h3 className="mt-2 text-lg font-semibold">{target.label}</h3><dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2"><div><dt className="text-xs text-muted">Baseline</dt><dd className="mt-1 font-medium">{formatStage3Value(target.baseline)}</dd></div><div><dt className="text-xs text-muted">Target kandidat</dt><dd className="mt-1 font-medium">{formatStage3Value(target.target)} {target.unit}</dd></div></dl><p className="mt-3 text-xs leading-5 text-secondary">{target.rationale}</p></article>;
}

function stageProgramLabel(stage: NutritionStage) {
  if (stage === "mpasi") return "Program MPASI";
  if (stage === "toddler") return "Program Toddler";
  return "Program Lansia";
}

function elderlyProgramName(goalKey?: string) {
  const names: Record<string, string> = {
    elderly_safe_nutrition_routine: "Program Makan Aman & Bergizi",
    elderly_hydration_routine: "Program Hidrasi Lansia",
    elderly_supported_meal_routine: "Program Dukungan Makan Lansia",
    elderly_meal_routine: "Program Makan Teratur Lansia",
    elderly_balanced_meal_routine: "Program Pola Makan Seimbang Lansia",
  };
  return names[String(goalKey ?? "")] ?? "Program Nutrisi Lansia";
}

export function resolveNutritionResultCta(
  status: "loading" | "authenticated" | "unauthenticated",
  existingProgram: ProgramSummary | null,
  programStateLoading: boolean,
) {
  const loading = status === "loading" || (status === "authenticated" && programStateLoading);
  return {
    loading,
    title: loading
      ? "Memeriksa program..."
      : status === "authenticated"
        ? existingProgram
          ? "Program aktif sudah tersedia."
          : "Mulai Guided Program"
        : "Simpan & Mulai Guided Program",
    button: loading
      ? "Memeriksa..."
      : status === "authenticated"
        ? existingProgram
          ? "Pilih program"
          : "Mulai Guided Program"
        : "Simpan & Mulai Guided Program",
  };
}

export function NutritionResult({ stage }: { stage: NutritionStage }) {
  const router = useRouter();
  const { status } = useAuth();
  const [session, setSession] = useState<NutritionResultSession | null | undefined>(undefined);
  const [authOpen, setAuthOpen] = useState(false);
  const [saveLoading, setSaveLoading] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [existingProgram, setExistingProgram] = useState<ProgramSummary | null>(null);
  const [programStateLoading, setProgramStateLoading] = useState(false);
  const [conflictOpen, setConflictOpen] = useState(false);
  const [selectedGoalKey, setSelectedGoalKey] = useState("");
  const [programName, setProgramName] = useState(stage === "mpasi" ? "Program MPASI" : stage === "toddler" ? "Program Toddler" : "");
  const [programNameTouched, setProgramNameTouched] = useState(false);

  useEffect(() => {
    if (status !== "authenticated") {
      setExistingProgram(null);
      setProgramStateLoading(false);
      return;
    }
    setProgramStateLoading(true);
    void listNutritionPrograms()
      .then((programs) => setExistingProgram(programs.find((item) => item.stage === stage && item.status === "ACTIVE" && !item.completed_at) ?? null))
      .catch(() => setExistingProgram(null))
      .finally(() => setProgramStateLoading(false));
  }, [stage, status]);

  useEffect(() => setSession(loadNutritionSession(stage)), [stage]);

  useEffect(() => {
    const first = session?.result?.suggested_goals?.[0]?.goal_key;
    if (first && !selectedGoalKey) setSelectedGoalKey(first);
    if (stage === "elderly" && first && !programNameTouched) setProgramName(elderlyProgramName(selectedGoalKey || first));
  }, [programNameTouched, selectedGoalKey, session, stage]);

  if (session === undefined) return <div className="min-h-[420px] animate-pulse rounded-2xl border border-line bg-surface" aria-label="Memuat hasil nutrisi" />;

  if (!session) {
    return (
      <section className="mx-auto max-w-3xl rounded-2xl border border-line bg-white p-10 text-center">
        <p className="eyebrow">Belum ada hasil</p>
        <h2 className="mt-4 text-3xl font-semibold tracking-[-0.04em]">Selesaikan assessment lebih dulu.</h2>
        <p className="mx-auto mt-4 max-w-xl text-sm leading-7 text-secondary">Hasil Nutrition Assistant tersedia setelah assessment valid selesai. Login tidak diperlukan untuk melihat rekomendasi publik.</p>
        <Link href={nutritionAssessmentPath(stage)} className={getButtonClasses({ variant: "secondary", size: "lg", className: "mt-7" })}>Kembali ke Assessment</Link>
      </section>
    );
  }

  const result = session.result;
  const assessment = session.assessment;
  const groups = foodGroupsFrom(result.food_groups);
  const cta = resolveNutritionResultCta(status, existingProgram, programStateLoading);
  const ctaLoading = cta.loading;
  const elderlySafetyLimited = stage === "elderly" && result.personalization_status === "limited_for_safety";
  const elderlySwallowingLimited = elderlySafetyLimited && assessment?.swallowing_difficulty === true;
  const elderlyGuidedBlocked = elderlySafetyLimited && !elderlySwallowingLimited;
  const guidedTitle = elderlySwallowingLimited
    ? "Mulai Guided Program dengan panduan umum yang dibatasi untuk keamanan."
    : elderlyGuidedBlocked
      ? "Guided Program belum dapat dimulai dari assessment ini."
      : cta.title;
  const guidedButton = elderlySwallowingLimited ? "Mulai Guided Program" : cta.button;

  async function createAndOpenProgram() {
    if (!assessment) {
      setSaveError("Assessment versi lama tidak memiliki data yang dibutuhkan untuk disimpan. Ulangi assessment.");
      return;
    }

    setSaveLoading(true);
    setSaveError("");
    try {
      const effectiveProgramName = stage === "elderly" ? (programName.trim() || elderlyProgramName(selectedGoalKey)) : programName;
      const program = await createNutritionProgram(assessment, 14, selectedGoalKey || undefined, effectiveProgramName);
      markNutritionProgramEntry(program.id);
      setAuthOpen(false);
      setConflictOpen(false);
      router.push(stage === "elderly" ? `/nutrition/program/${program.id}/today` : `/nutrition/program/${program.id}`);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : (stage === "elderly" ? "Guided Program belum dapat dibuat." : "Program belum dapat dibuat."));
      setSaveLoading(false);
    }
  }

  async function handlePrimaryAction() {
    if (!assessment) {
      setSaveError("Ulangi assessment agar hasil dapat disimpan dengan format terbaru.");
      return;
    }
    if (result.personalization_status === "limited_for_safety" && !(stage === "elderly" && assessment.swallowing_difficulty === true)) {
      setSaveError(stage === "elderly" ? "Guided Program tidak tersedia untuk assessment yang membutuhkan batasan keselamatan." : "Program belum dapat dimulai karena hasil ini memerlukan perhatian keselamatan terlebih dahulu.");
      return;
    }
    if (status === "authenticated") {
      if (existingProgram) {
        setConflictOpen(true);
        return;
      }
      await createAndOpenProgram();
      return;
    }
    setAuthOpen(true);
  }

  if (stage !== "elderly") {
    const primaryFocus = result.primary_gap?.label ?? result.primary_target?.label ?? result.recommendations[0] ?? "Bangun kebiasaan makan yang lebih konsisten.";
    const primaryReason = result.primary_gap?.rationale ?? result.primary_target?.rationale ?? result.summary;
    const actionItems = result.recommendations.length ? result.recommendations.slice(0, 4) : [result.primary_target?.label ?? "Ikuti target utama yang dipilih dari hasil assessment."];
    const primaryTarget = result.primary_target ?? result.evidence_rule_evaluation?.primary_target ?? null;
    const targetText = primaryTarget?.label ?? result.suggested_goals?.find((goal) => goal.goal_key === selectedGoalKey)?.title ?? primaryFocus;
    const estimatedEntries = Object.entries(result.estimated_needs).slice(0, 4);
    const profileItems: Array<{ icon: LucideIcon; label: string; value: string }> = [];
    const ageMonths = assessment?.age_months;
    profileItems.push({ icon: CalendarDays, label: "Usia", value: typeof ageMonths === "number" ? `${ageMonths} bulan` : result.age_band });
    if (stage === "mpasi") {
      const feedingMode = assessment?.feeding_mode === "breastmilk" ? "ASI + MPASI" : assessment?.feeding_mode === "formula" ? "Formula + MPASI" : assessment?.feeding_mode === "mixed" ? "ASI/formula + MPASI" : assessment?.feeding_mode === "other" ? "Pola susu lain + MPASI" : result.meal_pattern?.meals ?? "Konteks makan tercatat";
      const texture = assessment?.texture_level === "smooth_mashed" ? "Tekstur lumat" : assessment?.texture_level === "mashed_lumpy" ? "Tekstur lumat bertekstur" : assessment?.texture_level === "finger_food" ? "Finger food" : assessment?.texture_level === "family_soft" ? "Makanan keluarga lunak" : "Tekstur sesuai kemampuan";
      profileItems.push({ icon: UtensilsCrossed, label: "Pola makan", value: feedingMode });
      profileItems.push({ icon: Soup, label: "Tekstur", value: texture });
    } else {
      const meals = typeof assessment?.meal_frequency === "number" ? `${assessment.meal_frequency}× makan utama` : result.meal_pattern?.routine ?? result.meal_pattern?.meals ?? "Rutinitas makan tercatat";
      const routine = assessment?.meal_routine === "regular" ? "Rutinitas teratur" : assessment?.meal_routine === "mixed" ? "Rutinitas campuran" : assessment?.meal_routine === "irregular" ? "Rutinitas belum teratur" : typeof assessment?.snack_frequency === "number" ? `${assessment.snack_frequency}× snack` : "Pola makan sesuai assessment";
      profileItems.push({ icon: UtensilsCrossed, label: "Makan utama", value: meals });
      profileItems.push({ icon: ListChecks, label: "Rutinitas", value: routine });
    }

    return (
      <div className="nutrition-enter mx-auto max-w-5xl space-y-7">
        <section className="relative flex min-h-[calc(100svh-9rem)] items-center border-y border-line py-10 md:min-h-[calc(100svh-8rem)] md:py-14">
          <div className="max-w-4xl">
            <div className="flex flex-wrap gap-2"><Badge variant="info">Hasil Nutrition Assistant</Badge>{result.personalization_status === "limited_for_safety" && <Badge variant="warning">Panduan dibatasi untuk keamanan</Badge>}</div>
            <h1 className="mt-5 max-w-4xl text-5xl font-semibold leading-[.98] tracking-[-0.055em] sm:text-6xl lg:text-7xl">Apa yang paling penting untuk diperhatikan sekarang?</h1>
          </div>
          <div className="absolute bottom-6 left-0 inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[.12em] text-muted" aria-hidden="true">
            Gulir untuk melihat hasil <ArrowDown size={15} />
          </div>
        </section>

        <section className="border-b border-line pb-6 pt-1" aria-label="Profil singkat hasil assessment">
          <p className="max-w-2xl text-sm leading-7 text-secondary">Hasil ini disusun berdasarkan jawaban assessment kamu. Mulai dari fokus utama, lalu lihat langkah yang paling mudah dilakukan.</p>
          <div className="mt-4 flex flex-wrap gap-2">
            {profileItems.map(({ icon: Icon, label, value }) => <span key={`${label}-${value}`} className="inline-flex min-h-10 items-center gap-2 rounded-full border border-line bg-white px-3 py-2 text-sm text-secondary"><Icon size={15} className="text-primary-dark" aria-hidden="true"/><span className="sr-only">{label}: </span>{value}</span>)}
          </div>
        </section>

        <section className="grid gap-5 lg:grid-cols-[1.08fr_.92fr]" aria-label="Fokus dan target utama">
          <div className="border-l-2 border-primary bg-primary-light/20 px-5 py-5 sm:px-6">
            <div className="flex items-center gap-3"><span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white text-primary-dark shadow-sm"><Sparkles size={19}/></span><p className="eyebrow">Fokus utama</p></div>
            <h2 className="mt-4 text-2xl font-semibold tracking-[-0.03em] sm:text-3xl">{primaryFocus}</h2>
            <p className="mt-3 text-sm leading-7 text-secondary">{primaryReason}</p>
          </div>
          <div className="border-y border-line py-5 lg:border-y-0 lg:border-l lg:pl-6">
            <div className="flex items-center gap-3"><Target size={20} className="text-primary-dark"/><p className="eyebrow">Target utama</p></div>
            <p className="mt-4 text-xl font-semibold tracking-[-0.02em]">{targetText}</p>
            {primaryTarget ? <div className="mt-5 grid grid-cols-2 gap-4 border-t border-line pt-4 text-sm"><div><p className="text-xs font-bold uppercase tracking-[.09em] text-muted">Baseline</p><p className="mt-1 font-semibold text-text">{formatStage3Value(primaryTarget.baseline)}</p></div><div><p className="text-xs font-bold uppercase tracking-[.09em] text-muted">Target</p><p className="mt-1 font-semibold text-text">{formatStage3Value(primaryTarget.target)} {primaryTarget.unit}</p></div></div> : <p className="mt-3 text-sm leading-6 text-secondary">Target perilaku mengikuti hasil assessment dan fokus program yang dipilih.</p>}
          </div>
        </section>

        <section className="grid gap-7 border-y border-line py-6 lg:grid-cols-[1.15fr_.85fr]" aria-labelledby="actionable-result-title">
          <div>
            <p className="eyebrow">Yang bisa mulai dilakukan</p>
            <h2 id="actionable-result-title" className="mt-2 text-2xl font-semibold tracking-[-0.03em]">Langkah paling relevan dari hasilmu.</h2>
            <ol className="mt-4 divide-y divide-line border-y border-line">{actionItems.map((item, index) => <li key={`${item}-${index}`} className="flex gap-4 py-3.5"><span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary-light text-xs font-black text-primary-dark">{String(index + 1).padStart(2, "0")}</span><p className="text-sm leading-6 text-secondary">{item}</p></li>)}</ol>
          </div>
          <div>
            <p className="eyebrow">Prioritas nutrisi</p>
            <div className="mt-3 flex flex-wrap gap-2">{result.priority_nutrients.length ? result.priority_nutrients.map((item) => <Badge key={item} variant="info">{item}</Badge>) : <span className="text-sm text-secondary">Mengikuti fokus utama hasil assessment.</span>}</div>
            {estimatedEntries.length ? <div className="mt-6"><p className="text-xs font-bold uppercase tracking-[.1em] text-muted">Estimasi kebutuhan</p><dl className="mt-3 grid gap-x-5 gap-y-3 sm:grid-cols-2">{estimatedEntries.map(([key, value]) => <div key={key} className="border-t border-line pt-2"><dt className="text-xs text-muted">{humanize(key)}</dt><dd className="mt-1 text-sm font-semibold leading-6 text-text">{value}</dd></div>)}</dl><p className="mt-3 text-xs leading-5 text-muted">Angka ini adalah estimasi edukatif/reference dari hasil yang tersedia, bukan preskripsi individual.</p></div> : null}
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[.72fr_1.28fr]" aria-labelledby="menu-example-title">
          <div className="overflow-hidden rounded-2xl bg-background"><MealIllustration stage={stage} title={formatMenuDisplayTitle(stage, result.sample_menu[0] ?? "Contoh pilihan makanan")} groups={groups} compact /></div>
          <div>
            <p className="eyebrow">Contoh pilihan makanan</p>
            <h2 id="menu-example-title" className="mt-2 text-2xl font-semibold tracking-[-0.03em]">Contoh yang mudah dipindai.</h2>
            <div className="mt-3 divide-y divide-line border-y border-line">{result.sample_menu.length ? result.sample_menu.slice(0, 3).map((item, index) => <div key={item} className="grid grid-cols-[34px_1fr] gap-3 py-3"><span className="text-xs font-black text-primary-dark">0{index + 1}</span><p className="text-sm leading-6 text-secondary">{formatMenuDisplayTitle(stage, item)}</p></div>) : <p className="py-4 text-sm text-secondary">Contoh menu spesifik belum tersedia untuk hasil ini.</p>}</div>
          </div>
        </section>

        {result.suggested_goals?.length > 0 ? <section aria-labelledby="goal-choice-title" className="border-y border-line py-7">
          <div className="max-w-2xl">
            <p className="eyebrow">Fokus program</p>
            <h2 id="goal-choice-title" className="mt-2 text-2xl font-semibold tracking-[-0.03em] sm:text-3xl">Pilih fokus yang ingin dijalankan.</h2>
            <p className="mt-2 text-sm leading-6 text-secondary">Pilihan ini hanya menentukan fokus program yang akan dibuat dari hasil assessment.</p>
          </div>
          <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {result.suggested_goals.map((goal) => {
              const selected = selectedGoalKey === goal.goal_key;
              return <button key={goal.goal_key} type="button" aria-pressed={selected} onClick={() => setSelectedGoalKey(goal.goal_key)} className={`relative flex min-h-44 w-full flex-col justify-between rounded-xl border p-5 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 ${selected ? "border-primary bg-primary-light/30 shadow-[0_8px_24px_rgba(16,123,112,.08)]" : "border-line bg-white hover:border-primary/50 hover:bg-background"}`}>
                <span>
                  <span className="block pr-8 text-lg font-semibold text-text">{goal.title}</span>
                  <span className="mt-2 block text-sm leading-6 text-secondary">{goal.description}</span>
                </span>
                <span className={`mt-5 inline-flex w-fit items-center gap-2 text-xs font-bold uppercase tracking-[.08em] ${selected ? "text-primary-dark" : "text-muted"}`}>{selected ? "Fokus dipilih" : "Pilih fokus"}</span>
                <span aria-hidden="true" className={`absolute right-4 top-4 flex h-6 w-6 items-center justify-center rounded-md border ${selected ? "border-primary bg-primary text-white" : "border-line bg-white"}`}>{selected ? <Check className="h-4 w-4" strokeWidth={2.5} aria-hidden="true" /> : null}</span>
              </button>;
            })}
          </div>
        </section> : null}

        <section className="border-y border-line bg-background/45 py-6" aria-labelledby="program-preview-title">
          <div className="grid gap-6 px-4 sm:px-0 lg:grid-cols-[1.05fr_.95fr] lg:items-center">
            <div>
              <div className="flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-full bg-white text-primary-dark shadow-sm"><ListChecks size={19}/></span><div><p className="eyebrow">Program yang akan kamu jalankan</p><h2 id="program-preview-title" className="mt-1 text-2xl font-semibold tracking-[-0.03em]">{programName.trim() || stageProgramLabel(stage)}</h2></div></div>
              <p className="mt-3 text-sm font-semibold text-text">{stageProgramLabel(stage)} · 14 hari</p>
              <dl className="mt-4 space-y-2 text-sm"><div className="grid grid-cols-[70px_1fr] gap-3"><dt className="text-muted">Fokus</dt><dd className="font-medium text-text">{primaryFocus}</dd></div><div className="grid grid-cols-[70px_1fr] gap-3"><dt className="text-muted">Target</dt><dd className="font-medium text-text">{targetText}</dd></div></dl>
            </div>
            <div>
              <label htmlFor="nutrition-program-name" className="text-sm font-semibold text-text">Beri nama program</label>
              <input id="nutrition-program-name" value={programName} maxLength={80} onChange={(event) => setProgramName(event.target.value)} placeholder={stage === "mpasi" ? "Contoh: MPASI Dinda" : "Contoh: Rutinitas Makan Raka"} className="mt-2 min-h-11 w-full rounded-lg border border-line bg-white px-3 text-sm outline-none focus:border-primary" />
              <p className="mt-1 text-xs text-muted">Nama ini digunakan untuk mengenali programmu.</p>
              <Button className="mt-4 w-full justify-center sm:w-auto" size="lg" onClick={() => void handlePrimaryAction()} isLoading={saveLoading || ctaLoading} loadingLabel="Menyiapkan program..." disabled={result.personalization_status === "limited_for_safety" || ctaLoading}>{status === "authenticated" ? <ArrowRight size={17}/> : <LockKeyhole size={17}/>} {status === "authenticated" ? (existingProgram ? "Pilih langkah program" : "Buat program dari hasil ini") : "Masuk & buat program"}</Button>
            </div>
          </div>
        </section>

        {result.validation.status !== "VALID" && <Alert variant={result.validation.status === "WARNING" ? "warning" : "error"} title="Ada hal yang perlu diperhatikan">{result.validation.message}</Alert>}
        {result.safety_notes.length > 0 && <Alert variant="warning" title="Catatan keselamatan">{result.safety_notes.join(" ")}</Alert>}

        <section className="space-y-3" aria-label="Detail tambahan hasil nutrisi">
          <details className="border-y border-line py-4"><summary className="cursor-pointer font-semibold text-text">Lihat detail assessment</summary><div className="mt-4"><p className="text-xs font-bold uppercase tracking-[.1em] text-muted">Yang kamu masukkan</p><ul className="mt-3 grid gap-2 text-sm leading-6 text-secondary sm:grid-cols-2">{result.input_summary.map((item) => <li key={item} className="border-t border-line pt-2">{item}</li>)}</ul></div></details>
          <details className="border-b border-line py-4"><summary className="cursor-pointer font-semibold text-text">Lihat dasar rekomendasi & referensi</summary><div className="mt-4 space-y-4 text-sm leading-6 text-secondary">{result.guidance.length > 0 && <div><p className="font-semibold text-text">Panduan tambahan</p><ul className="mt-2 space-y-2">{result.guidance.map((item) => <li key={item}>• {item}</li>)}</ul></div>}{result.references.length > 0 && <div><p className="font-semibold text-text">Referensi</p><ul className="mt-2 space-y-2">{result.references.map((item) => <li key={item}>• {item}</li>)}</ul></div>}</div></details>
        </section>

        {saveError && <Alert variant="warning" title="Program belum dapat dimulai">{saveError}</Alert>}
        <Alert variant="info" title="Catatan">{result.disclaimer}</Alert>

        <AuthGate open={authOpen} onClose={() => setAuthOpen(false)} requireSaveConsent contextLabel={`Masuk untuk menyimpan ${stageProgramLabel(stage)}`} onAuthenticated={async () => { await createAndOpenProgram(); }} />

        {conflictOpen && existingProgram && <ViewportModal onClose={() => !saveLoading && setConflictOpen(false)} labelledBy="program-conflict-title">
          <p className="eyebrow">Program aktif</p><h2 id="program-conflict-title" className="mt-3 text-2xl font-semibold tracking-[-0.035em]">Sudah ada {stageProgramLabel(stage)} yang sedang berjalan.</h2><p className="mt-3 text-sm leading-7 text-secondary">Pilih apakah kamu ingin kembali ke program yang aktif atau membuat program baru dari hasil ini.</p><div className="mt-5 border-y border-line py-4"><p className="text-xs font-black uppercase tracking-[.1em] text-muted">Program aktif</p><p className="mt-2 text-lg font-semibold">{existingProgram.title}</p><p className="mt-1 text-sm text-secondary">Hari {existingProgram.current_day} dari {existingProgram.duration_days}</p></div><div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-end"><Button autoFocus variant="secondary" onClick={() => setConflictOpen(false)}>Kembali</Button><Button variant="secondary" onClick={() => router.push(`/nutrition/program/${existingProgram.id}`)}>Lanjutkan program yang ada</Button><Button onClick={() => void createAndOpenProgram()} isLoading={saveLoading} loadingLabel="Membuat program...">Buat program baru</Button></div>
        </ViewportModal>}
      </div>
    );
  }

  const elderlyGoal = result.suggested_goals?.find((goal) => goal.goal_key === selectedGoalKey) ?? result.suggested_goals?.[0] ?? null;
  const elderlyPrimaryFocus = elderlyGoal?.title ?? result.primary_gap?.label ?? result.primary_target?.label ?? result.recommendations[0] ?? "Bangun pola makan dan minum yang lebih konsisten.";
  const elderlyPrimaryReason = elderlyGoal?.selection_reason ?? elderlyGoal?.description ?? result.primary_gap?.rationale ?? result.primary_target?.rationale ?? result.summary;
  const elderlyTargetText = elderlyGoal?.target_label ?? (elderlyGoal ? `${elderlyGoal.target} / ${elderlyGoal.duration}` : result.primary_target?.label ?? elderlyPrimaryFocus);
  const elderlyBaselineText = elderlyGoal?.baseline_label ?? (elderlyGoal ? `${elderlyGoal.baseline} ${elderlyGoal.unit}` : result.primary_target ? formatStage3Value(result.primary_target.baseline) : "Mengikuti hasil assessment");
  const elderlyActionItems = result.recommendations.length ? result.recommendations.slice(0, 4) : ["Jalankan satu langkah yang paling realistis dari fokus program hari ini."];
  const elderlyEstimatedEntries = Object.entries(result.estimated_needs).slice(0, 4);
  const elderlyProfileItems: Array<{ icon: LucideIcon; label: string; value: string }> = [
    { icon: CalendarDays, label: "Tahap", value: result.age_band },
    { icon: UtensilsCrossed, label: "Makan utama", value: typeof assessment?.meal_frequency === "number" ? `${assessment.meal_frequency}× per hari` : result.meal_pattern?.meals ?? "Pola makan tercatat" },
    { icon: Soup, label: "Cairan", value: result.elderly_context?.hydration_label ?? "Kebiasaan minum tercatat" },
  ];

  return (
    <div className="nutrition-enter mx-auto max-w-5xl space-y-7">
      <section className="relative flex min-h-[calc(100svh-9rem)] items-center border-y border-line py-10 md:min-h-[calc(100svh-8rem)] md:py-14">
        <div className="max-w-4xl">
          <div className="flex flex-wrap gap-2"><Badge variant="info">Hasil Nutrition Assistant</Badge>{result.personalization_status === "limited_for_safety" && <Badge variant="warning">Panduan dibatasi untuk keamanan</Badge>}</div>
          <h1 className="mt-5 max-w-4xl text-5xl font-semibold leading-[.98] tracking-[-0.055em] sm:text-6xl lg:text-7xl">Apa yang paling penting untuk diperhatikan sekarang?</h1>
          <p className="mt-5 max-w-2xl text-sm leading-7 text-secondary sm:text-base">{result.summary}</p>
        </div>
        <div className="absolute bottom-6 left-0 inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[.12em] text-muted" aria-hidden="true">Gulir untuk melihat hasil <ArrowDown size={15} /></div>
      </section>

      <section className="border-b border-line pb-6 pt-1" aria-label="Profil singkat hasil assessment lansia">
        <p className="max-w-2xl text-sm leading-7 text-secondary">Hasil ini disusun dari pola makan, kondisi kesehatan yang dilaporkan, hidrasi, kemampuan makan/minum, dan dukungan sehari-hari. Mulai dari fokus utama, lalu lihat langkah yang paling realistis.</p>
        <div className="mt-4 flex flex-wrap gap-2">
          {elderlyProfileItems.map(({ icon: Icon, label, value }) => <span key={`${label}-${value}`} className="inline-flex min-h-10 items-center gap-2 rounded-full border border-line bg-white px-3 py-2 text-sm text-secondary"><Icon size={15} className="text-primary-dark" aria-hidden="true"/><span className="sr-only">{label}: </span>{value}</span>)}
        </div>
      </section>

      <section className="grid gap-5 lg:grid-cols-[1.08fr_.92fr]" aria-label="Fokus dan target utama lansia">
        <div className="border-l-2 border-primary bg-primary-light/20 px-5 py-5 sm:px-6">
          <div className="flex items-center gap-3"><span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white text-primary-dark shadow-sm"><Sparkles size={19}/></span><p className="eyebrow">Fokus utama</p></div>
          <h2 className="mt-4 text-2xl font-semibold tracking-[-0.03em] sm:text-3xl">{elderlyPrimaryFocus}</h2>
          <p className="mt-3 text-sm leading-7 text-secondary">{elderlyPrimaryReason}</p>
        </div>
        <div className="border-y border-line py-5 lg:border-y-0 lg:border-l lg:pl-6">
          <div className="flex items-center gap-3"><Target size={20} className="text-primary-dark"/><p className="eyebrow">Target utama</p></div>
          <p className="mt-4 text-xl font-semibold tracking-[-0.02em]">{elderlyTargetText}</p>
          <div className="mt-5 grid grid-cols-2 gap-4 border-t border-line pt-4 text-sm"><div><p className="text-xs font-bold uppercase tracking-[.09em] text-muted">Kondisi awal</p><p className="mt-1 font-semibold text-text">{elderlyBaselineText}</p></div><div><p className="text-xs font-bold uppercase tracking-[.09em] text-muted">Durasi</p><p className="mt-1 font-semibold text-text">14 hari</p></div></div>
        </div>
      </section>

      {(result.health_context?.has_condition || result.elderly_context) ? <section className="grid gap-7 border-y border-line py-6 lg:grid-cols-2" aria-label="Konteks pendukung lansia">
        {result.health_context?.has_condition ? <div className="min-w-0">
          <p className="eyebrow">Kondisi kesehatan</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em]">Konteks yang kamu laporkan.</h2>
          <div className="mt-4 flex flex-wrap gap-2">{(result.health_context.condition_labels ?? []).map((item) => <Badge key={item} variant="neutral">{item}</Badge>)}</div>
          {(result.health_context.nutrition_focus ?? []).length ? <ul className="mt-4 divide-y divide-line border-y border-line">{(result.health_context.nutrition_focus ?? []).slice(0, 4).map((item) => <li key={item} className="flex min-w-0 gap-3 py-3 text-sm leading-6 text-secondary"><CheckCircle2 size={16} className="mt-1 shrink-0 text-primary"/><span className="min-w-0 break-words">{item}</span></li>)}</ul> : null}
          {result.health_context.consultation_note ? <p className="mt-3 text-sm font-semibold leading-6 text-secondary">{result.health_context.consultation_note}</p> : null}
          <p className="mt-2 text-xs leading-5 text-muted">{result.health_context.source_note ?? "Kondisi digunakan sebagai konteks edukasi nutrisi, bukan diagnosis."}</p>
        </div> : <div><p className="eyebrow">Kondisi kesehatan</p><h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em]">Tidak ada kondisi khusus yang dilaporkan.</h2><p className="mt-3 text-sm leading-6 text-secondary">Program tetap menggunakan pola makan, hidrasi, kemampuan makan/minum, dan dukungan sehari-hari sebagai konteks personalisasi.</p></div>}
        {result.elderly_context ? <div className="min-w-0">
          <p className="eyebrow">Konteks harian</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em]">Cara makan, minum, dan dukungan sehari-hari.</h2>
          <dl className="mt-4 divide-y divide-line border-y border-line text-sm"><div className="grid gap-1 py-3 sm:grid-cols-[150px_1fr]"><dt className="font-semibold">Kebiasaan minum</dt><dd className="text-secondary">{result.elderly_context.hydration_label ?? "Belum ditentukan"}</dd></div><div className="grid gap-1 py-3 sm:grid-cols-[150px_1fr]"><dt className="font-semibold">Kemandirian</dt><dd className="text-secondary">{result.elderly_context.eating_independence_label ?? "Belum ditentukan"}</dd></div><div className="grid gap-1 py-3 sm:grid-cols-[150px_1fr]"><dt className="font-semibold">Dukungan</dt><dd className="text-secondary">{result.elderly_context.caregiver_support_label ?? "Belum ditentukan"}</dd></div></dl>
        </div> : null}
      </section> : null}

      <section className="grid gap-7 border-y border-line py-6 lg:grid-cols-[1.15fr_.85fr]" aria-labelledby="elderly-actionable-result-title">
        <div>
          <p className="eyebrow">Yang bisa mulai dilakukan</p>
          <h2 id="elderly-actionable-result-title" className="mt-2 text-2xl font-semibold tracking-[-0.03em]">Langkah paling relevan dari hasilmu.</h2>
          <ol className="mt-4 divide-y divide-line border-y border-line">{elderlyActionItems.map((item, index) => <li key={`${item}-${index}`} className="flex gap-4 py-3.5"><span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary-light text-xs font-black text-primary-dark">{String(index + 1).padStart(2, "0")}</span><p className="text-sm leading-6 text-secondary">{item}</p></li>)}</ol>
        </div>
        <div>
          <p className="eyebrow">Prioritas nutrisi</p>
          <div className="mt-3 flex flex-wrap gap-2">{result.priority_nutrients.length ? result.priority_nutrients.map((item) => <Badge key={item} variant="info">{item}</Badge>) : <span className="text-sm text-secondary">Mengikuti fokus utama hasil assessment.</span>}</div>
          {elderlyEstimatedEntries.length ? <div className="mt-6"><p className="text-xs font-bold uppercase tracking-[.1em] text-muted">Estimasi kebutuhan</p><dl className="mt-3 grid gap-x-5 gap-y-3 sm:grid-cols-2">{elderlyEstimatedEntries.map(([key, value]) => <div key={key} className="border-t border-line pt-2"><dt className="text-xs text-muted">{humanize(key)}</dt><dd className="mt-1 text-sm font-semibold leading-6 text-text">{value}</dd></div>)}</dl><p className="mt-3 text-xs leading-5 text-muted">Angka ini adalah estimasi edukatif/reference, bukan preskripsi individual.</p></div> : null}
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[.72fr_1.28fr]" aria-labelledby="elderly-menu-example-title">
        <div className="overflow-hidden rounded-2xl bg-background"><MealIllustration stage={stage} title={formatMenuDisplayTitle(stage, result.sample_menu[0] ?? "Contoh pilihan makanan")} groups={groups} compact /></div>
        <div className="min-w-0">
          <p className="eyebrow">Contoh pilihan makanan</p>
          <h2 id="elderly-menu-example-title" className="mt-2 text-2xl font-semibold tracking-[-0.03em]">Contoh yang mudah dipindai.</h2>
          {assessment?.swallowing_difficulty === true ? <div className="mt-4"><Alert variant="info" title="Fokus pada kandungan, bukan level tekstur">Gunakan komposisi makanan di bawah dengan bentuk, tekstur, dan kekentalan yang sudah diketahui aman. Aplikasi tidak menentukan level tekstur terapi.</Alert></div> : null}
          <div className="mt-3 divide-y divide-line border-y border-line">{result.sample_menu.length ? result.sample_menu.slice(0, 4).map((item, index) => <div key={item} className="grid grid-cols-[34px_1fr] gap-3 py-3"><span className="text-xs font-black text-primary-dark">{String(index + 1).padStart(2, "0")}</span><p className="min-w-0 break-words text-sm leading-6 text-secondary">{formatMenuDisplayTitle(stage, item)}</p></div>) : <p className="py-4 text-sm text-secondary">Contoh menu spesifik belum tersedia untuk hasil ini.</p>}</div>
        </div>
      </section>

      {result.suggested_goals?.length > 0 ? <section aria-labelledby="elderly-goal-choice-title" className="border-y border-line py-7">
        <div className="max-w-2xl"><p className="eyebrow">Fokus program</p><h2 id="elderly-goal-choice-title" className="mt-2 text-2xl font-semibold tracking-[-0.03em] sm:text-3xl">Goal yang akan dilacak selama program.</h2><p className="mt-2 text-sm leading-6 text-secondary">Fokus dipilih dari masalah yang paling relevan di assessment dan digunakan untuk menentukan To Do harian serta evaluasi akhir.</p></div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2">{result.suggested_goals.map((goal) => {
          const selected = selectedGoalKey === goal.goal_key || (!selectedGoalKey && goal === result.suggested_goals[0]);
          return <button key={goal.goal_key} type="button" aria-pressed={selected} onClick={() => { setSelectedGoalKey(goal.goal_key); if (!programNameTouched) setProgramName(elderlyProgramName(goal.goal_key)); }} className={`relative flex min-h-44 w-full flex-col justify-between rounded-xl border p-5 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 ${selected ? "border-primary bg-primary-light/30 shadow-[0_8px_24px_rgba(16,123,112,.08)]" : "border-line bg-white hover:border-primary/50 hover:bg-background"}`}>
            <span><span className="block pr-8 text-lg font-semibold text-text">{goal.title}</span><span className="mt-2 block text-sm leading-6 text-secondary">{goal.description}</span>{goal.selection_reason ? <span className="mt-3 block text-xs leading-5 text-muted">Mengapa: {goal.selection_reason}</span> : null}</span>
            <span className="mt-5 grid w-full grid-cols-2 gap-3 border-t border-line pt-4 text-xs"><span><span className="block text-muted">Kondisi awal</span><span className="mt-1 block font-semibold text-text">{goal.baseline_label ?? `${goal.baseline} ${goal.unit}`}</span></span><span><span className="block text-muted">Target</span><span className="mt-1 block font-semibold text-text">{goal.target_label ?? `${goal.target} / ${goal.duration}`}</span></span></span>
            <span aria-hidden="true" className={`absolute right-4 top-4 flex h-6 w-6 items-center justify-center rounded-md border ${selected ? "border-primary bg-primary text-white" : "border-line bg-white"}`}>{selected ? <Check className="h-4 w-4" strokeWidth={2.5} aria-hidden="true" /> : null}</span>
          </button>;
        })}</div>
      </section> : null}

      <section className="border-y border-line bg-background/45 py-6" aria-labelledby="elderly-program-preview-title">
        <div className="grid gap-6 px-4 sm:px-0 lg:grid-cols-[1.05fr_.95fr] lg:items-center">
          <div className="min-w-0">
            <div className="flex items-center gap-3"><span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white text-primary-dark shadow-sm"><ListChecks size={19}/></span><div className="min-w-0"><p className="eyebrow">Program yang akan kamu jalankan</p><h2 id="elderly-program-preview-title" className="mt-1 break-words text-2xl font-semibold tracking-[-0.03em]">{programName.trim() || elderlyProgramName(selectedGoalKey)}</h2></div></div>
            <p className="mt-3 text-sm font-semibold text-text">Program Lansia · 14 hari</p>
            <dl className="mt-4 space-y-2 text-sm"><div className="grid grid-cols-[70px_1fr] gap-3"><dt className="text-muted">Fokus</dt><dd className="min-w-0 break-words font-medium text-text">{elderlyPrimaryFocus}</dd></div><div className="grid grid-cols-[70px_1fr] gap-3"><dt className="text-muted">Target</dt><dd className="min-w-0 break-words font-medium text-text">{elderlyTargetText}</dd></div></dl>
            {result.health_context?.has_condition ? <p className="mt-4 max-w-2xl text-xs leading-5 text-muted">Kondisi kesehatan yang dilaporkan digunakan sebagai konteks edukasi untuk menyesuaikan fokus program, bukan sebagai diagnosis.</p> : null}
            {elderlySwallowingLimited ? <p className="mt-3 max-w-2xl text-xs leading-5 text-muted">Assessment mencatat kesulitan menelan. Guided Program tetap memberi contoh komposisi menu berdasarkan kelompok pangan/kandungan; bentuk, tekstur, dan kekentalan mengikuti pola yang sudah diketahui aman.</p> : null}
          </div>
          <div>
            {!elderlyGuidedBlocked ? <><label htmlFor="elderly-program-name" className="text-sm font-semibold text-text">Beri nama program</label><input id="elderly-program-name" value={programName} maxLength={180} onChange={(event) => { setProgramNameTouched(true); setProgramName(event.target.value); }} placeholder="Contoh: Program Hidrasi Ibu" className="mt-2 min-h-11 w-full rounded-lg border border-line bg-white px-3 text-sm outline-none focus:border-primary"/><p className="mt-1 text-xs text-muted">Nama ini digunakan untuk mengenali program di History dan Final Result.</p></> : null}
            {elderlyGuidedBlocked ? <Link href={nutritionAssessmentPath(stage)} className={getButtonClasses({ size: "lg", className: "mt-4 justify-center" })}>Perbarui Assessment <ArrowRight size={17}/></Link> : <Button className="mt-4 w-full justify-center sm:w-auto" size="lg" onClick={() => void handlePrimaryAction()} isLoading={saveLoading || ctaLoading} loadingLabel="Menyiapkan program..." disabled={ctaLoading}>{status === "authenticated" ? <ArrowRight size={17}/> : <LockKeyhole size={17}/>} {guidedButton}</Button>}
          </div>
        </div>
      </section>

      {result.validation.status !== "VALID" && <Alert variant={result.validation.status === "WARNING" ? "warning" : "error"} title="Ada hal yang perlu diperhatikan">{result.validation.message}</Alert>}
      {result.safety_notes.length > 0 && <Alert variant="warning" title="Catatan keselamatan">{result.safety_notes.join(" ")}</Alert>}

      <section className="space-y-3" aria-label="Detail tambahan hasil nutrisi lansia">
        <details className="border-y border-line py-4"><summary className="cursor-pointer font-semibold text-text">Lihat detail assessment</summary><div className="mt-4"><p className="text-xs font-bold uppercase tracking-[.1em] text-muted">Yang kamu masukkan</p><ul className="mt-3 grid gap-2 text-sm leading-6 text-secondary sm:grid-cols-2">{result.input_summary.map((item) => <li key={item} className="border-t border-line pt-2">{item}</li>)}</ul></div></details>
        <details className="border-b border-line py-4"><summary className="cursor-pointer font-semibold text-text">Lihat dasar rekomendasi & referensi</summary><div className="mt-4 space-y-4 text-sm leading-6 text-secondary">{result.guidance.length > 0 && <div><p className="font-semibold text-text">Panduan tambahan</p><ul className="mt-2 space-y-2">{result.guidance.map((item) => <li key={item}>• {item}</li>)}</ul></div>}{result.references.length > 0 && <div><p className="font-semibold text-text">Referensi</p><ul className="mt-2 space-y-2">{result.references.map((item) => <li key={item}>• {item}</li>)}</ul></div>}{result.health_context?.needs_clinical_consultation && result.health_context.consultation_note ? <Alert variant="info" title="Penyesuaian khusus">{result.health_context.consultation_note}</Alert> : null}</div></details>
      </section>

      {saveError && <Alert variant="warning" title="Guided Program belum dapat dimulai">{saveError}</Alert>}
      <Alert variant="info" title="Disclaimer">{result.disclaimer}</Alert>

      <AuthGate open={authOpen} onClose={() => setAuthOpen(false)} requireSaveConsent contextLabel={`Masuk untuk menyimpan ${stageProgramLabel(stage)}`} onAuthenticated={async () => { await createAndOpenProgram(); }} />

      {conflictOpen && existingProgram && <ViewportModal onClose={() => !saveLoading && setConflictOpen(false)} labelledBy="program-conflict-title">
        <p className="eyebrow">Program aktif</p><h2 id="program-conflict-title" className="mt-3 text-2xl font-semibold tracking-[-0.035em]">Sudah ada {stageProgramLabel(stage)} yang sedang berjalan.</h2><p className="mt-3 text-sm leading-7 text-secondary">Pilih apakah kamu ingin kembali ke program yang aktif atau membuat program baru dari hasil ini.</p><div className="mt-5 border-y border-line py-4"><p className="text-xs font-black uppercase tracking-[.1em] text-muted">Program aktif</p><p className="mt-2 text-lg font-semibold">{existingProgram.title}</p><p className="mt-1 text-sm text-secondary">Hari {existingProgram.current_day} dari {existingProgram.duration_days}</p></div><div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-end"><Button autoFocus variant="secondary" onClick={() => setConflictOpen(false)}>Kembali</Button><Button variant="secondary" onClick={() => router.push(`/nutrition/program/${existingProgram.id}/today`)}>Lanjutkan program yang ada</Button><Button onClick={() => void createAndOpenProgram()} isLoading={saveLoading} loadingLabel="Membuat program...">Buat program baru</Button></div>
      </ViewportModal>}
    </div>
  );
}
