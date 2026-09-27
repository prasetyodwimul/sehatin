"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, CheckCircle2, Minus, Plus } from "lucide-react";
import { Alert, Button, ProgressBar, Textarea } from "@/components/ui";
import { FOOD_GROUP_ORDER, MealIllustration, FoodGroupIcon, foodGroupsFrom, type FoodGroupKey } from "@/components/nutrition-visuals";
import { AuthGate } from "@/components/auth-gate";
import { ViewportModal } from "@/components/viewport-modal";
import { ApiError } from "@/lib/api";
import { getBlockReview, getNutritionProgram, saveDailyLog, type BlockReview, type DailyLogResponse, type DailyQuickLog, type DailyMetricResult, type ProgramDay, type ProgramDetail, type ProgramTask } from "@/lib/nutrition-program";
import { formatMenuDisplayTitle } from "@/lib/nutrition-menu-presentation";

export type DailySaveState = "IDLE" | "DIRTY" | "SAVING" | "SAVED" | "SAVE_ERROR";

type DailyDraft = {
  dayId: string;
  checks: boolean[];
  foodGroupChecks?: boolean[];
  results: Record<string, unknown>;
  hasComplaint: boolean | null;
  complaintNote: string;
  quickLog: DailyQuickLog;
  updatedAt: string;
};

const DAILY_DRAFT_PREFIX = "sehatin:nutrition-draft:";

function draftKey(programId: string, dayId: string) {
  return `${DAILY_DRAFT_PREFIX}${programId}:${dayId}`;
}

function readDraft(programId: string, dayId: string): DailyDraft | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(draftKey(programId, dayId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as DailyDraft;
    return parsed?.dayId === dayId ? parsed : null;
  } catch {
    return null;
  }
}

const GROUP_LABELS: Record<FoodGroupKey, string> = {
  protein: "Protein",
  carbohydrate: "Karbohidrat",
  vegetable: "Sayuran",
  fruit: "Buah",
  "healthy-fat": "Lemak baik",
};

function text(value: unknown, fallback = "â€”") {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function numericResult(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  if (typeof value === "string" && value.trim() && Number.isFinite(Number(value))) return value;
  return "";
}

function isChoiceLike(task: ProgramTask) {
  return task.input_type === "choice" || task.input_type === "rating" || task.input_type === "observation" || task.input_type === "simple_experience";
}

function taskInitialResult(task: ProgramTask, stored: Record<string, unknown>) {
  const result = stored?.[task.key];
  if (result === undefined || result === null) {
    if (task.input_type === "count" || isChoiceLike(task)) return "";
    return undefined;
  }
  if (task.input_type === "count") return numericResult(result);
  if (isChoiceLike(task)) return String(result);
  return typeof result === "boolean" ? result : undefined;
}

function hasResult(task: ProgramTask, value: unknown) {
  if (task.input_type === "count") return value !== "" && Number.isFinite(Number(value)) && Number(value) >= 0;
  if (isChoiceLike(task)) return typeof value === "string" && value.length > 0;
  return typeof value === "boolean";
}

function taskAdherence(task: ProgramTask, value: unknown) {
  if (!hasResult(task, value)) return null;
  if (task.input_type === "count") {
    const target = Number(task.target_value ?? 0);
    const actual = Math.max(0, Number(value));
    if (target <= 0) return actual === 0 ? 100 : 0;
    return Math.min(100, Math.round(((actual / target) * 100) * 100) / 100);
  }
  if (task.input_type === "boolean") {
    const metric = String(task.metric_id ?? task.metric ?? "");
    if (metric === "responsive_feeding") return value === true ? 100 : 0;
    return Boolean(value) === Boolean(task.target_value) ? 100 : 0;
  }
  const mapped = task.adherence_map?.[String(value)];
  return typeof mapped === "number" ? Math.max(0, Math.min(100, mapped)) : null;
}

function resultStatus(task: ProgramTask, value: unknown) {
  if (!hasResult(task, value)) return "Belum dicatat";
  const adherence = taskAdherence(task, value);
  if (adherence === null) return "Hasil tercatat";
  if (adherence >= 100) return "Target tercapai";
  if (adherence > 0) return "Sebagian tercapai";
  return "Target belum tercapai";
}

function stage6StatusDisplay(status: string, adherence?: number | null) {
  if (status === "COMPLETED" && adherence === null) return "Hasil tercatat";
  if (status === "COMPLETED") return "Target tercapai";
  if (status === "PARTIAL") return "Sebagian tercapai";
  if (status === "NOT_STARTED") return "Belum dimulai";
  if (status === "MISSED") return "Terlewat";
  return status || "Belum dicatat";
}

function targetDisplay(task: ProgramTask) {
  return task.target_label || `${String(task.target_value ?? "â€”")} ${task.unit ?? ""}`.trim();
}

function actualDisplay(task: ProgramTask, value: unknown, includeTarget = true) {
  if (!hasResult(task, value)) return "Belum dicatat";
  if (task.input_type === "count") return includeTarget ? `${String(value)} / ${String(task.target_value ?? "â€”")} ${task.unit ?? ""}`.trim() : `${String(value)} ${task.unit ?? ""}`.trim();
  if (task.input_type === "boolean") return value ? "Ya" : "Tidak";
  return task.options?.find((option) => option.value === String(value))?.label ?? String(value);
}

function CountResult({ task, value, editable, onChange, showTargetSuffix = true }: { task: ProgramTask; value: unknown; editable: boolean; onChange: (value: string) => void; showTargetSuffix?: boolean }) {
  const numeric = numericResult(value);
  const amount = numeric === "" ? 0 : Math.max(0, Number(numeric));
  const label = task.action_text ?? task.action ?? task.target_label;
  return (
    <div className="flex flex-wrap items-center gap-2">
      <button type="button" disabled={!editable || amount <= 0} aria-label={`Kurangi hasil ${label}`} onClick={() => onChange(String(Math.max(0, amount - 1)))} className="flex h-9 w-9 items-center justify-center rounded-full border border-line bg-white text-lg font-semibold disabled:opacity-40">âˆ’</button>
      <label className="sr-only" htmlFor={`result-${task.key}`}>Hasil aktual {label}</label>
      <input id={`result-${task.key}`} aria-label={`Hasil aktual ${label}`} type="number" min="0" step="1" inputMode="numeric" disabled={!editable} value={numeric} onChange={(event) => onChange(event.target.value)} className="h-9 w-20 rounded-lg border border-line bg-white px-2 text-center text-sm font-semibold outline-none focus:border-primary" />
      <button type="button" disabled={!editable} aria-label={`Tambah hasil ${label}`} onClick={() => onChange(String(amount + 1))} className="flex h-9 w-9 items-center justify-center rounded-full border border-line bg-white text-lg font-semibold disabled:opacity-40"><Plus className="h-4 w-4" strokeWidth={2.25} aria-hidden="true" /></button>
      {showTargetSuffix && <span className="text-xs text-muted">/ {String(task.target_value ?? "â€”")} {task.unit ?? ""}</span>}
    </div>
  );
}

function ChoiceResult({ task, value, editable, onChange }: { task: ProgramTask; value: unknown; editable: boolean; onChange: (value: string) => void }) {
  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label={task.result_prompt ?? `Hasil ${task.action_text ?? task.target_label}`}>
      {(task.options ?? []).map((option) => {
        const selected = value === option.value;
        return <button key={option.value} type="button" disabled={!editable} aria-pressed={selected} onClick={() => onChange(option.value)} className={`min-h-9 rounded-full border px-3 py-1.5 text-xs font-semibold ${selected ? "border-primary bg-primary text-white" : "border-line bg-white text-secondary"}`}>{option.label}</button>;
      })}
    </div>
  );
}

function QuickChoice<T extends string | boolean>({ label, value, options, editable, onChange }: { label: string; value: T | null | undefined; options: Array<{ value: T; label: string }>; editable: boolean; onChange: (value: T) => void }) {
  return (
    <div>
      <p className="text-xs font-bold uppercase tracking-[.09em] text-muted">{label}</p>
      <div className="mt-2 flex flex-wrap gap-2" role="group" aria-label={label}>
        {options.map((option) => <button key={String(option.value)} type="button" disabled={!editable} aria-pressed={value === option.value} onClick={() => onChange(option.value)} className={`min-h-9 rounded-full border px-3 py-1.5 text-xs font-semibold ${value === option.value ? "border-primary bg-primary text-white" : "border-line bg-white text-secondary"}`}>{option.label}</button>)}
      </div>
    </div>
  );
}

function blockStatusLabel(value?: string) {
  if (value === "MET") return "Tercapai konsisten";
  if (value === "PARTIALLY_MET") return "Sebagian tercapai";
  if (value === "NOT_MET") return "Perlu dilanjutkan";
  return value?.replaceAll("_", " ") || "Belum tersedia";
}

function NutritionBlockReviewInline({ review }: { review: BlockReview }) {
  const programProgress = review.program_progress;
  const goalProgress = review.goal_progress;
  const metrics = review.metrics ?? [];
  return <section className="mt-10 border-y border-line py-7" aria-labelledby="block-review-title">
    <p className="eyebrow">Hasil program</p>
    <h3 id="block-review-title" className="mt-2 text-2xl font-semibold tracking-[-.03em]">Ringkasan {review.duration_days ?? 14} hari</h3>
    <p className="mt-3 max-w-3xl text-sm leading-7 text-secondary">Periode program selesai. Status tujuan ditentukan dari kebiasaan yang benar-benar tercatat selama program.</p>

    <div className="mt-6 grid gap-5 border-y border-line py-5 sm:grid-cols-2">
      <div><p className="text-xs font-black uppercase tracking-[.1em] text-muted">Program</p><p className="mt-2 text-xl font-semibold">{programProgress?.completed_days ?? 0} / {programProgress?.planned_days ?? review.duration_days ?? 14} hari</p><p className="mt-1 text-sm text-secondary">{Math.round(programProgress?.percent ?? 0)}% block selesai</p></div>
      <div><p className="text-xs font-black uppercase tracking-[.1em] text-muted">Tujuan</p><p className="mt-2 text-xl font-semibold">{blockStatusLabel(review.goal_status)}</p><p className="mt-1 text-sm text-secondary">{String(goalProgress?.actual ?? "â€”")} / {String(goalProgress?.target ?? "â€”")} {goalProgress?.unit ?? ""} Â· {Math.round(goalProgress?.percent ?? 0)}%</p></div>
    </div>

    <div className="mt-6 grid gap-5 md:grid-cols-2">
      <div><p className="text-xs font-black uppercase tracking-[.1em] text-primary-dark">Apa yang berubah?</p><p className="mt-2 text-sm leading-7 text-secondary">{review.what_improved || "Belum ada perubahan yang cukup konsisten untuk diringkas."}</p></div>
      <div><p className="text-xs font-black uppercase tracking-[.1em] text-amber-800">Apa yang masih perlu?</p><p className="mt-2 text-sm leading-7 text-secondary">{review.what_remains || "Belum ada area tambahan yang perlu diringkas."}</p></div>
    </div>

    {metrics.length ? <div className="mt-6 overflow-x-auto" aria-label="Ringkasan fokus program"><table className="w-full min-w-[600px] border-collapse text-left text-sm"><thead><tr className="border-b border-line text-xs uppercase tracking-[.08em] text-muted"><th className="py-2 pr-4">Fokus</th><th className="py-2 pr-4">Target</th><th className="py-2 pr-4">Hasil</th><th className="py-2 pr-4">Pencapaian</th><th className="py-2">Status</th></tr></thead><tbody>{metrics.map((metric) => <tr key={metric.metric} className="border-b border-line/70"><td className="py-3 pr-4 font-semibold">{metric.label ?? metric.metric}</td><td className="py-3 pr-4 text-secondary">{String(metric.target ?? "â€”")} {metric.unit ?? ""}</td><td className="py-3 pr-4 text-secondary">{metric.actual ?? "â€”"}</td><td className="py-3 pr-4 text-secondary">{metric.adherence == null ? "â€”" : `${Math.round(metric.adherence)}%`}</td><td className="py-3 font-semibold">{metric.status?.replaceAll("_", " ") ?? "â€”"}</td></tr>)}</tbody></table></div> : null}

    <div className="mt-6 border-l-2 border-primary pl-4">
      <p className="text-xs font-black uppercase tracking-[.1em] text-muted">Langkah berikutnya</p>
      <p className="mt-2 text-lg font-semibold">{review.decision?.replaceAll("_", " ") || "CONTINUE"}</p>
      <p className="mt-2 text-sm leading-7 text-secondary">{review.next_focus || "Fokus berikutnya mengikuti hasil evaluasi block yang tersimpan."}</p>
    </div>
  </section>;
}


function clampPercent(value: number) {
  return Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));
}

function DailyResultRing({ value, label, detail }: { value: number; label: string; detail: string }) {
  const percent = clampPercent(value);
  const radius = 46;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percent / 100) * circumference;
  return <div className="flex items-center gap-5">
    <div className="relative h-28 w-28 shrink-0" role="img" aria-label={`${label} ${Math.round(percent)} persen`}>
      <svg viewBox="0 0 112 112" className="h-28 w-28 -rotate-90" aria-hidden="true">
        <circle cx="56" cy="56" r={radius} fill="none" stroke="#e2e8f0" strokeWidth="10" />
        <circle cx="56" cy="56" r={radius} fill="none" stroke="#0f766e" strokeWidth="10" strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={offset} />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center"><strong className="text-2xl text-primary-dark">{Math.round(percent)}%</strong></div>
    </div>
    <div><p className="text-xs font-black uppercase tracking-[.1em] text-muted">{label}</p><p className="mt-2 max-w-xs text-sm leading-6 text-secondary">{detail}</p></div>
  </div>;
}

function DailyMetricBar({ label, value, actual, status }: { label: string; value: number | null; actual: string; status: string }) {
  const percent = clampPercent(value ?? 0);
  return <div className="border-t border-line pt-4">
    <div className="flex items-start justify-between gap-4"><div className="min-w-0"><p className="break-words text-sm font-semibold leading-6 text-text">{label}</p><p className="mt-1 text-xs text-secondary">Hasil: {actual}</p></div><span className="shrink-0 text-xs font-bold text-primary-dark">{value === null ? "Tercatat" : `${Math.round(percent)}%`}</span></div>
    <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100" aria-hidden="true"><div className="h-full rounded-full bg-primary transition-[width]" style={{ width: `${value === null ? 100 : percent}%` }} /></div>
    <p className="mt-2 text-xs font-semibold text-muted">{status}</p>
  </div>;
}

const ELDERLY_QUICK_LABELS: Record<string, string> = {
  well: "Baik", unwell: "Kurang bugar", fatigue: "Lemas / cepat lelah", dizziness: "Pusing", nausea: "Mual", vomiting: "Muntah", fever: "Demam", diarrhea: "Diare", constipation: "Sembelit", pain_discomfort: "Nyeri / tidak nyaman", other_concern: "Perubahan kondisi lain",
  good: "Baik / teratur", reduced: "Menurun / lebih sedikit", poor: "Sangat sedikit", none: "Tidak ada", some: "Ada kendala ringan", difficult: "Lebih sulit", independent: "Mandiri", reminder: "Perlu diingatkan", assisted: "Perlu dibantu",
  low_appetite: "Tidak terasa lapar", early_satiety: "Cepat kenyang", chewing: "Sulit mengunyah", swallowing: "Menelan terasa lebih sulit", preparation: "Sulit menyiapkan makanan", availability: "Makanan/bahan tidak tersedia", support: "Bantuan tidak tersedia", other: "Hambatan lain",
};

const CHILD_QUICK_LABELS: Record<string, string> = {
  finished: "Habis", partial: "Sebagian", little: "Sedikit", none: "Tidak ada / tidak dimakan", liked: "Suka", neutral: "Netral", refused: "Menolak", healthy: "Sehat", fussy: "Rewel", sick: "Sakit", fever: "Demam", diarrhea: "Diare", severe_teething: "Tumbuh gigi berat", easy: "Mudah", somewhat_difficult: "Cukup sulit", difficult: "Sulit",
};

function QuickResultCard({ label, value, labels }: { label: string; value: unknown; labels: Record<string, string> }) {
  const raw = value === true ? "Ya" : value === false ? "Tidak" : String(value ?? "");
  const display = raw ? (labels[raw] ?? raw.replaceAll("_", " ")) : "Belum ada data";
  return <div className="min-w-0 rounded-2xl border border-line bg-white p-4"><p className="text-[10px] font-black uppercase tracking-[.1em] text-muted">{label}</p><p className="mt-2 break-words text-sm font-semibold leading-6 text-text">{display}</p></div>;
}

function CompletedDayResultView({ program, day, tasks, results, savedMetricResults, checks, quickLog, complaintNote, hasComplaint, lastResponse }: { program: ProgramDetail; day: ProgramDay; tasks: ProgramTask[]; results: Record<string, unknown>; savedMetricResults: DailyMetricResult[]; checks: boolean[]; quickLog: DailyQuickLog; complaintNote: string; hasComplaint: boolean | null; lastResponse: DailyLogResponse | null }) {
  const metricByTask = Object.fromEntries(savedMetricResults.map((row) => [row.task_id, row]));
  const rows = tasks.map((task) => {
    const value = results[task.key];
    const backend = metricByTask[task.key];
    const adherence = backend ? (backend.adherence ?? null) : taskAdherence(task, value);
    const status = backend ? stage6StatusDisplay(backend.status, backend.adherence ?? null) : resultStatus(task, value);
    return { task, value, adherence, status };
  });
  const measurable = rows.map((row) => row.adherence).filter((value): value is number => typeof value === "number");
  const averageAdherence = measurable.length ? measurable.reduce((sum, value) => sum + value, 0) / measurable.length : (tasks.length ? (checks.filter(Boolean).length / tasks.length) * 100 : 0);
  const achieved = rows.filter((row) => (row.adherence ?? 0) >= 100).length;
  const dailySummary = lastResponse?.daily_summary ?? day.action_details?.daily_summary;
  const adaptation = lastResponse?.adaptation ?? day.action_details?.adaptation;
  const child = program.stage === "mpasi" || program.stage === "toddler";
  const quickCards = program.stage === "elderly"
    ? [
        ["Kondisi", quickLog.health_condition], ["Nafsu makan", quickLog.appetite_status], ["Cairan", quickLog.hydration_status], ["Kenyamanan makan/minum", quickLog.eating_difficulty], ["Dukungan", quickLog.eating_support], ["Hambatan utama", quickLog.eating_barrier],
      ] as Array<[string, unknown]>
    : child
      ? [["Porsi", quickLog.portion], ["Penerimaan", quickLog.acceptance], ["Kondisi anak", quickLog.child_condition], ["Kesulitan caregiver", quickLog.parent_difficulty]] as Array<[string, unknown]>
      : [];
  const labels = program.stage === "elderly" ? ELDERLY_QUICK_LABELS : CHILD_QUICK_LABELS;

  return <div className="border-t border-line pt-8">
    <div className="flex flex-wrap items-start justify-between gap-5"><div><p className="eyebrow">Hasil Hari {day.day_number}</p><h2 className="mt-2 text-3xl font-semibold tracking-[-.04em]">Hari ini sudah tersimpan.</h2><p className="mt-3 max-w-2xl text-sm leading-7 text-secondary">Input harian sudah dikunci. Halaman ini menampilkan hasil dan pola yang tercatat tanpa menampilkan kembali form pengisian.</p></div><span className="rounded-full bg-emerald-50 px-4 py-2 text-xs font-black uppercase tracking-[.08em] text-emerald-800">Completed</span></div>

    <section className="mt-7 grid gap-5 rounded-3xl border border-line bg-[linear-gradient(145deg,#f7fbf9,#fff)] p-5 md:grid-cols-[auto_1fr] md:p-7" aria-label={`Visualisasi hasil Hari ${day.day_number}`}>
      <DailyResultRing value={averageAdherence} label="Pencapaian hari" detail={`${achieved} dari ${tasks.length} target mencapai hasil penuh. Persentase dihitung dari hasil aktual yang tersimpan.`} />
      <div className="grid gap-3 sm:grid-cols-3"><div className="rounded-2xl bg-white p-4 shadow-sm"><p className="text-[10px] font-black uppercase tracking-[.1em] text-muted">Aktivitas dilakukan</p><p className="mt-2 text-3xl font-semibold">{checks.filter(Boolean).length}/{tasks.length}</p></div><div className="rounded-2xl bg-white p-4 shadow-sm"><p className="text-[10px] font-black uppercase tracking-[.1em] text-muted">Target tercapai</p><p className="mt-2 text-3xl font-semibold">{achieved}</p></div><div className="rounded-2xl bg-white p-4 shadow-sm"><p className="text-[10px] font-black uppercase tracking-[.1em] text-muted">Adaptasi berikutnya</p><p className="mt-2 break-words text-lg font-semibold">{String(adaptation?.decision ?? "Menunggu data berikutnya").replaceAll("_", " ")}</p></div></div>
    </section>

    <section className="mt-8" aria-labelledby="saved-task-results-title"><p className="eyebrow">Visual hasil To Do</p><h3 id="saved-task-results-title" className="mt-2 text-2xl font-semibold">Target dan hasil aktual.</h3><div className="mt-5 grid gap-x-6 lg:grid-cols-2">{rows.map(({ task, value, adherence, status }) => <DailyMetricBar key={task.key} label={task.action_text ?? task.action ?? task.target_label} value={adherence} actual={actualDisplay(task, value, !child)} status={status} />)}</div></section>

    {quickCards.length ? <section className="mt-8 border-t border-line pt-7" aria-labelledby="saved-context-title"><p className="eyebrow">Kondisi yang tersimpan</p><h3 id="saved-context-title" className="mt-2 text-xl font-semibold">Snapshot hari ini</h3><div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{quickCards.map(([label, value]) => <QuickResultCard key={label} label={label} value={value} labels={labels} />)}</div></section> : null}

    {(dailySummary || adaptation) ? <section className="mt-8 grid gap-3 border-t border-line pt-7 md:grid-cols-3"><div className="rounded-2xl bg-primary-light/30 p-4"><p className="text-[10px] font-black uppercase tracking-[.1em] text-primary-dark">Yang berjalan baik</p><p className="mt-2 text-sm leading-6 text-secondary">{dailySummary?.what_went_well ?? "Hasil hari ini sudah tercatat."}</p></div><div className="rounded-2xl bg-amber-50 p-4"><p className="text-[10px] font-black uppercase tracking-[.1em] text-amber-800">Yang masih sulit</p><p className="mt-2 text-sm leading-6 text-secondary">{dailySummary?.what_was_difficult ?? "Tidak ada hambatan utama yang tercatat."}</p></div><div className="rounded-2xl border border-line bg-white p-4"><p className="text-[10px] font-black uppercase tracking-[.1em] text-muted">Fokus berikutnya</p><p className="mt-2 text-sm leading-6 text-secondary">{adaptation?.explanation?.what_next ?? dailySummary?.tomorrow_preview ?? "Rencana berikutnya mengikuti hasil hari ini."}</p></div></section> : null}

    {hasComplaint ? <section className="mt-7 rounded-2xl border border-amber-200 bg-amber-50 p-4"><p className="text-xs font-black uppercase tracking-[.1em] text-amber-800">Keluhan / kendala tersimpan</p><p className="mt-2 text-sm leading-6 text-secondary">{complaintNote || "Keluhan dicatat tanpa detail tambahan."}</p></section> : null}
  </div>;
}

export function NutritionProgramDailyWorkspace({ program, day, onProgramRefresh }: { program: ProgramDetail; day: ProgramDay; onProgramRefresh: (program: ProgramDetail) => void }) {
  const router = useRouter();
  const tasks = useMemo<ProgramTask[]>(() => {
    const raw = (day.action_details?.tasks ?? []) as ProgramTask[];
    if (raw.length) return raw;
    if (program.stage !== "elderly") return [];
    return day.checklist.map((target, index) => ({
      key: `legacy-${index}`,
      metric: "legacy",
      input_type: "boolean" as const,
      target_value: true,
      target_label: target,
      action: target,
      action_text: target,
      result_prompt: "Apakah tindakan ini berhasil diterapkan hari ini?",
      success_criteria: "Hasil dicatat terpisah dari checkbox tindakan.",
    }));
  }, [day.action_details, day.checklist, program.stage]);

  const storedResults = (day.action_details?.task_results ?? day.task_results ?? {}) as Record<string, unknown>;
  const [checks, setChecks] = useState<boolean[]>(day.checklist_state ?? tasks.map(() => false));
  const [foodGroupChecks, setFoodGroupChecks] = useState<boolean[]>(day.food_group_state ?? FOOD_GROUP_ORDER.map(() => false));
  const [results, setResults] = useState<Record<string, unknown>>(() => Object.fromEntries(tasks.map((task) => [task.key, taskInitialResult(task, storedResults)])));
  const [savedMetricResults, setSavedMetricResults] = useState<DailyMetricResult[]>(() => (day.metric_results ?? day.action_details?.metric_results ?? []) as DailyMetricResult[]);
  const [hasComplaint, setHasComplaint] = useState<boolean | null>(day.has_complaint ?? null);
  const [complaintNote, setComplaintNote] = useState(day.complaint_note ?? "");
  const [quickLog, setQuickLog] = useState<DailyQuickLog>(() => (day.action_details?.daily_log ?? {}) as DailyQuickLog);
  const [lastResponse, setLastResponse] = useState<DailyLogResponse | null>(null);
  const [saveState, setSaveState] = useState<DailySaveState>("IDLE");
  const [error, setError] = useState("");
  const [authOpen, setAuthOpen] = useState(false);
  const [blockReview, setBlockReview] = useState<BlockReview | null>(null);
  const [blockReviewError, setBlockReviewError] = useState("");
  const [completionOpen, setCompletionOpen] = useState(false);
  const [processingSavedResult, setProcessingSavedResult] = useState(false);
  const resultTopRef = useRef<HTMLElement | null>(null);
  const processingTimerRef = useRef<number | null>(null);
  const responseDayIdRef = useRef(day.id);
  const saveInFlightRef = useRef(false);

  const childAdaptive = program.stage === "mpasi" || program.stage === "toddler";
  const elderlyAdaptive = program.stage === "elderly";
  const dailyCompletionFeedback = childAdaptive || elderlyAdaptive;
  const safetyTracked = childAdaptive || elderlyAdaptive;
  const editable = !day.locked && day.status !== "LOCKED" && !day.missed && day.status !== "COMPLETED" && program.status === "ACTIVE";

  useEffect(() => {
    setProcessingSavedResult(false);
    if (processingTimerRef.current !== null) {
      window.clearTimeout(processingTimerRef.current);
      processingTimerRef.current = null;
    }
    return () => {
      if (processingTimerRef.current !== null) window.clearTimeout(processingTimerRef.current);
    };
  }, [day.id]);

  useEffect(() => {
    const serverResults = (day.action_details?.task_results ?? day.task_results ?? {}) as Record<string, unknown>;
    const draft = editable ? readDraft(program.id, day.id) : null;
    setChecks(draft?.checks ?? day.checklist_state ?? tasks.map(() => false));
    setFoodGroupChecks(draft?.foodGroupChecks ?? day.food_group_state ?? FOOD_GROUP_ORDER.map(() => false));
    setResults(draft?.results ?? Object.fromEntries(tasks.map((task) => [task.key, taskInitialResult(task, serverResults)])));
    setSavedMetricResults(((day.metric_results ?? day.action_details?.metric_results ?? []) as DailyMetricResult[]));
    setHasComplaint(draft?.hasComplaint ?? day.has_complaint ?? null);
    setComplaintNote(draft?.complaintNote ?? day.complaint_note ?? "");
    setQuickLog(draft?.quickLog ?? ((day.action_details?.daily_log ?? {}) as DailyQuickLog));
    // Preserve the latest save/safety response when the same day changes from
    // ACTIVE to SAFETY_HOLD. Clearing it here used to remove the emergency
    // alert immediately after onProgramRefresh() changed program.status.
    if (responseDayIdRef.current !== day.id) {
      responseDayIdRef.current = day.id;
      setLastResponse(null);
      setCompletionOpen(false);
    }
    setSaveState(draft ? "DIRTY" : "IDLE");
    setError("");
  }, [day.action_details?.daily_log, day.action_details?.metric_results, day.action_details?.task_results, day.checklist_state, day.complaint_note, day.food_group_state, day.has_complaint, day.id, day.metric_results, day.task_results, editable, program.id, tasks]);

  useEffect(() => {
    if (!editable || saveState !== "DIRTY" || typeof window === "undefined") return;
    const draft: DailyDraft = {
      dayId: day.id,
      checks,
      foodGroupChecks,
      results,
      hasComplaint,
      complaintNote,
      quickLog,
      updatedAt: new Date().toISOString(),
    };
    sessionStorage.setItem(draftKey(program.id, day.id), JSON.stringify(draft));
  }, [checks, complaintNote, day.id, editable, foodGroupChecks, hasComplaint, program.id, quickLog, results, saveState]);

  useEffect(() => {
    if (saveState !== "DIRTY" || typeof window === "undefined") return;
    const protectUnsaved = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", protectUnsaved);
    return () => window.removeEventListener("beforeunload", protectUnsaved);
  }, [saveState]);

  useEffect(() => {
    const shouldLoad = day.day_number === program.duration_days && (day.status === "COMPLETED" || Boolean(program.completed_at) || program.status === "COMPLETED");
    if (!shouldLoad || program.stage === "elderly" || blockReview) return;
    let active = true;
    setBlockReviewError("");
    getBlockReview(program.id).then((review) => {
      if (active) setBlockReview(review);
    }).catch((err) => {
      if (active) setBlockReviewError(err instanceof Error ? err.message : "Evaluasi Hari 14 belum dapat dimuat.");
    });
    return () => { active = false; };
  }, [blockReview, day.day_number, day.status, program.completed_at, program.duration_days, program.id, program.stage, program.status]);
  const doneCount = checks.filter(Boolean).length;
  const previewAchievedCount = tasks.filter((task) => (taskAdherence(task, results[task.key]) ?? 0) >= 100).length;
  const recommendedGroups = useMemo(() => foodGroupsFrom(day.meal_guidance_details?.food_groups ?? program.recommendation?.food_groups ?? []), [day.meal_guidance_details, program.recommendation]);
  const mealDetails = day.meal_guidance_details ?? {};
  const elderlySwallowingMode = program.stage === "elderly" && program.assessment_snapshot?.swallowing_difficulty === true;
  const emergencySafety = lastResponse?.safety?.before_adaptation?.emergency
    ? lastResponse.safety.before_adaptation
    : undefined;
  const savedMetricByTask = useMemo(() => Object.fromEntries(savedMetricResults.map((row) => [row.task_id, row])), [savedMetricResults]);
  const useBackendMeasurement = saveState === "SAVED" || saveState === "IDLE";
  const achievedCount = useBackendMeasurement && savedMetricResults.length
    ? tasks.filter((task) => (savedMetricByTask[task.key]?.adherence ?? 0) >= 100).length
    : previewAchievedCount;
  const targetProgressPercent = tasks.length ? (achievedCount / tasks.length) * 100 : 0;
  const dailyActivityProgress = tasks.length ? (doneCount / tasks.length) * 100 : 0;

  function markDirty() {
    if (editable) setSaveState("DIRTY");
  }

  function setTaskResult(task: ProgramTask, value: unknown) {
    setResults((current) => ({ ...current, [task.key]: value }));
    markDirty();
  }

  function toggleAction(index: number) {
    setChecks((current) => current.map((item, i) => i === index ? !item : item));
    markDirty();
  }

  function setQuickValue<K extends keyof DailyQuickLog>(key: K, value: DailyQuickLog[K]) {
    setQuickLog((current) => ({ ...current, [key]: value }));
    markDirty();
  }

  async function persist() {
    if (!editable || saveInFlightRef.current) return;
    if (!tasks.length) {
      setError("Aktivitas hari ini belum tersedia. Muat ulang halaman untuk melihat rencana terbaru.");
      return;
    }
    const childPauseRequested = childAdaptive && ["sick", "fever", "diarrhea", "severe_teething"].includes(String(quickLog.child_condition ?? ""));
    const elderlyPauseRequested = program.stage === "elderly" && ["unwell", "nausea", "vomiting", "fever", "diarrhea", "dizziness", "pain_discomfort", "difficulty_eating_drinking", "other_concern"].includes(String(quickLog.health_condition ?? ""));
    const safetyPauseRequested = childPauseRequested || elderlyPauseRequested;
    const missing = tasks.find((task) => !hasResult(task, results[task.key]));
    if (missing && !safetyPauseRequested) {
      setError(`Isi hasil aktual untuk "${missing.action_text ?? missing.action ?? missing.target_label}" sebelum menyimpan.`);
      return;
    }
    if (program.stage === "elderly" && !quickLog.health_condition) {
      setError("Pilih kondisi hari ini sebelum menyimpan.");
      return;
    }
    if (program.stage === "elderly" && !safetyPauseRequested && (!quickLog.appetite_status || !quickLog.eating_difficulty || !quickLog.hydration_status || !quickLog.eating_support || !quickLog.eating_barrier)) {
      setError("Lengkapi nafsu makan, cairan, kenyamanan, hambatan utama, dan kebutuhan bantuan agar program dapat menyesuaikan hari berikutnya.");
      return;
    }
    if (hasComplaint === null && !safetyPauseRequested) {
      setError("Pilih apakah ada keluhan atau kendala hari ini.");
      return;
    }
    if (hasComplaint && !complaintNote.trim() && !safetyPauseRequested) {
      setError("Ceritakan singkat keluhan atau kendalanya sebelum menyimpan.");
      return;
    }
    if (childAdaptive && quickLog.reaction === "detected" && !quickLog.reaction_notes?.trim()) {
      setError("Jelaskan reaksi tidak biasa yang terlihat agar tanda bahaya dapat diperiksa dengan benar.");
      return;
    }
    saveInFlightRef.current = true;
    setSaveState("SAVING");
    setError("");
    try {
      const response = await saveDailyLog(program.id, day.day_number, {
        checklistState: checks,
        foodGroupState: foodGroupChecks,
        hasComplaint,
        complaintNote,
        mealLabel: formatMenuDisplayTitle(program.stage, mealDetails.example),
        mealNotes: text(mealDetails.preparation, "Panduan menu hari ini"),
        taskResults: results,
        quickLog: safetyTracked ? quickLog : undefined,
      });
      if (typeof window !== "undefined") sessionStorage.removeItem(draftKey(program.id, day.id));
      setChecks(response.checklist_state ?? checks);
      setFoodGroupChecks(response.food_group_state ?? foodGroupChecks);
      if (response.task_results) setResults(response.task_results);
      if (response.metric_results) setSavedMetricResults(response.metric_results);
      setLastResponse(response);
      setSaveState("SAVED");
      if (response.day_completed) setError("");
      if (response.day_completed && response.program_status === "ACTIVE" && dailyCompletionFeedback && day.day_number < program.duration_days) setCompletionOpen(true);
      const finalDayCompleted = Boolean(response.day_completed && day.day_number === program.duration_days && response.program_status === "COMPLETED");
      if (response.day_completed && day.day_number === program.duration_days && program.stage !== "elderly") {
        try {
          setBlockReview(await getBlockReview(program.id));
          setBlockReviewError("");
        } catch (reviewError) {
          setBlockReviewError(reviewError instanceof Error ? reviewError.message : "Hasil Hari 14 tersimpan, tetapi evaluasi program belum dapat dimuat.");
        }
      }

      // Promote SAFETY_HOLD into the shared shell immediately so the review
      // panel appears even before the follow-up program refetch completes.
      if (response.program_status === "SAFETY_HOLD" && program.status !== "SAFETY_HOLD") {
        onProgramRefresh({ ...program, status: "SAFETY_HOLD" });
      } else if (response.program_status === "PAUSED" && program.status !== "PAUSED") {
        onProgramRefresh({ ...program, status: "PAUSED" });
      }

      // A successful log save must stay successful even when follow-up refreshes fail.
      // Run follow-ups in parallel so the UI reaches SAVED promptly and tests/user actions do not wait on an unrelated refresh.
      const freshResult = await Promise.allSettled([getNutritionProgram(program.id)]);

      if (freshResult[0].status === "fulfilled") {
        const fresh = freshResult[0].value;
        onProgramRefresh(fresh);
        const savedDay = fresh.days.find((item) => item.day_number === day.day_number);
        if (savedDay) {
          // Keep the just-saved response authoritative for the current form.
          // A follow-up program refetch can briefly return a stale day snapshot;
          // it must not erase task results/checks that were accepted by the save API.
          setChecks(response.checklist_state ?? savedDay.checklist_state ?? []);
          setFoodGroupChecks(response.food_group_state ?? savedDay.food_group_state ?? FOOD_GROUP_ORDER.map(() => false));
          setResults((response.task_results ?? savedDay.action_details?.task_results ?? savedDay.task_results ?? results) as Record<string, unknown>);
          setSavedMetricResults(((response.metric_results ?? savedDay.metric_results ?? savedDay.action_details?.metric_results ?? []) as DailyMetricResult[]));
        }
      }
      if (finalDayCompleted) {
        setCompletionOpen(false);
        router.push(`/nutrition/program/${program.id}/result`);
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setSaveState("DIRTY");
        setError("Sesi berakhir. Masuk lagi untuk menyimpan.");
        setAuthOpen(true);
        return;
      }
      setSaveState("SAVE_ERROR");
      setError(err instanceof Error ? err.message : "Progress belum dapat disimpan.");
    } finally {
      saveInFlightRef.current = false;
    }
  }

  function stayOnSavedDay() {
    setCompletionOpen(false);
    setProcessingSavedResult(true);

    // Move the user to the beginning of the saved-day result instead of
    // leaving the viewport at the bottom of the completed form.
    window.requestAnimationFrame(() => {
      resultTopRef.current?.scrollIntoView?.({ behavior: "smooth", block: "start" });
    });

    if (processingTimerRef.current !== null) window.clearTimeout(processingTimerRef.current);
    processingTimerRef.current = window.setTimeout(() => {
      setProcessingSavedResult(false);
      processingTimerRef.current = null;
      window.requestAnimationFrame(() => {
        resultTopRef.current?.scrollIntoView?.({ behavior: "smooth", block: "start" });
      });
    }, 650);
  }

  const statusCopy = day.status === "MISSED"
    ? "Hari ini sudah lewat. Data tersedia untuk ditinjau."
    : day.status === "COMPLETED"
      ? "Hari ini sudah selesai dan menjadi bagian dari riwayat."
      : day.status === "LOCKED"
        ? "Hari ini belum tersedia."
        : day.day_number === 1
          ? "Hari pertama digunakan sebagai baseline: catat kondisi aktual apa adanya sebelum program beradaptasi."
          : "Lakukan action, isi hasil aktual apa adanya, lalu simpan. Hasil di bawah target tetap valid sebagai data.";
  const completedView = day.status === "COMPLETED" || Boolean(lastResponse?.day_completed);

  if (completedView) return <section ref={resultTopRef} id="today" className="scroll-mt-24">
    {processingSavedResult ? <div className="flex min-h-[420px] items-center justify-center border-t border-line px-4 py-14" role="status" aria-live="polite" aria-label={`Memproses hasil Hari ${day.day_number}`}>
      <div className="max-w-md text-center">
        <span className="mx-auto block h-12 w-12 animate-spin rounded-full border-4 border-primary/15 border-t-primary" aria-hidden="true" />
        <p className="eyebrow mt-6">Memproses hasil</p>
        <h2 className="mt-2 text-3xl font-semibold tracking-[-.04em]">Menyiapkan progres Hari {day.day_number}â€¦</h2>
        <p className="mt-3 text-sm leading-7 text-secondary">Menyusun hasil To Do, kondisi harian, dan ringkasan progres yang baru saja disimpan.</p>
        <div className="mx-auto mt-6 h-1.5 max-w-xs overflow-hidden rounded-full bg-slate-100"><div className="h-full w-2/3 animate-pulse rounded-full bg-primary" /></div>
      </div>
    </div> : <CompletedDayResultView program={program} day={day} tasks={tasks} results={results} savedMetricResults={savedMetricResults} checks={checks} quickLog={quickLog} complaintNote={complaintNote} hasComplaint={hasComplaint} lastResponse={lastResponse} />}
    {!processingSavedResult && blockReviewError ? <div className="mt-8"><Alert variant="warning" title="Evaluasi Hari 14 belum dapat dimuat">{blockReviewError} Hasil harian yang sudah tersimpan tetap aman.</Alert></div> : null}
    {!processingSavedResult && blockReview ? <NutritionBlockReviewInline review={blockReview} /> : null}
    {completionOpen && dailyCompletionFeedback && day.day_number < program.duration_days ? <ViewportModal onClose={() => setCompletionOpen(false)} labelledBy="daily-completion-title">
      <div className="text-center">
        <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-50 text-emerald-700"><CheckCircle2 size={28}/></span>
        <p className="eyebrow mt-5">Hari {day.day_number} dari {program.duration_days}</p>
        <h2 id="daily-completion-title" className="mt-2 text-3xl font-semibold tracking-[-.035em]">Hari {day.day_number} selesai</h2>
        <p className="mx-auto mt-3 max-w-sm text-sm leading-7 text-secondary">Semua aktivitas dan catatan hari ini sudah tersimpan. Pilih tetap melihat hasil Hari {day.day_number} atau lanjut melihat Hari {day.day_number + 1}.</p>
        <div className="mx-auto mt-5 h-1.5 max-w-xs overflow-hidden rounded-full bg-slate-100" aria-hidden="true"><div className="h-full rounded-full bg-primary" style={{ width: `${Math.min(100, (day.day_number / program.duration_days) * 100)}%` }}/></div>
        <div className="mt-7 grid gap-3 sm:grid-cols-2">
          <Button autoFocus variant="secondary" className="w-full justify-center" onClick={stayOnSavedDay}>Tetap di Hari {day.day_number}</Button>
          <Button className="w-full justify-center" onClick={() => { setCompletionOpen(false); router.push(`/nutrition/program/${program.id}/day/${day.day_number + 1}`); }}>Lihat Hari {day.day_number + 1}<ArrowRight size={16}/></Button>
        </div>
        <p className="mt-3 text-xs leading-5 text-muted">Jika hari berikutnya belum waktunya, halaman berikutnya tetap tampil sebagai panduan yang terkunci.</p>
      </div>
    </ViewportModal> : null}
    <AuthGate open={authOpen} onClose={() => setAuthOpen(false)} onAuthenticated={async () => { setAuthOpen(false); setError(""); }} />
  </section>;

  const menuTitle = formatMenuDisplayTitle(program.stage, elderlySwallowingMode ? "Contoh komposisi menu" : text(mealDetails.example, "Menu sesuai panduan"));
  const menuVisualKey = text(mealDetails.visual_key, "");

  return (
    <section id="today" className="guided-program-mobile-safe scroll-mt-24">
      <div className="border-t border-line pt-8">
        <p className="eyebrow">Guidance hari ini</p>
        <h2 className="mt-3 text-2xl font-semibold tracking-[-0.03em] sm:text-3xl">{text(day.focus, "Panduan hari ini")}</h2>
        <p className="mt-3 max-w-3xl text-base leading-7 text-secondary">{text(day.recommended_action, statusCopy)}</p>
        <div className="mt-4 max-w-3xl border-l-2 border-primary pl-4 text-sm leading-6 text-secondary">{statusCopy}</div>
        {childAdaptive && ((Array.isArray(mealDetails.safety_notes) && mealDetails.safety_notes.length > 0) || day.reference_notes?.length > 0) ? <details className="mt-4 max-w-3xl text-xs text-muted"><summary className="cursor-pointer font-semibold text-primary-dark">Dasar panduan & catatan aman</summary>{Array.isArray(mealDetails.safety_notes) && mealDetails.safety_notes.length > 0 ? <ul className="mt-2 space-y-1 leading-5">{(mealDetails.safety_notes as string[]).map((item) => <li key={item}>â€¢ {item}</li>)}</ul> : null}{day.reference_notes?.length > 0 ? <ul className="mt-2 space-y-1 leading-5">{day.reference_notes.map((item) => <li key={item}>{item}</li>)}</ul> : null}</details> : null}
      </div>

      {childAdaptive && (day.action_details?.why_this_plan || program.goal) && <section className="mt-6 grid gap-3 md:grid-cols-2" aria-label="Konteks rencana hari ini">
        {day.action_details?.why_this_plan && <div className="min-w-0 rounded-2xl border border-primary/20 bg-primary-light/25 px-4 py-3"><p className="text-xs font-bold uppercase tracking-[.1em] text-primary-dark">Kenapa rencana hari ini seperti ini?</p><p className="mt-2 text-sm leading-6 text-secondary">{String(day.action_details.why_this_plan)}</p></div>}
        {program.goal && <div className="min-w-0 rounded-2xl border border-line bg-background px-4 py-3"><p className="text-xs font-bold uppercase tracking-[.1em] text-muted">Hubungan dengan goal</p><p className="mt-2 text-sm font-semibold">{program.goal.title}</p><p className="mt-1 text-xs leading-5 text-secondary">Goal progress dihitung dari metric target, terpisah dari jumlah hari program.</p></div>}
      </section>}

      <section className="mt-8" aria-labelledby="menu-today-title">
        <p className="eyebrow">Menu hari ini</p>
        <div className="mt-4 min-w-0 overflow-hidden rounded-[30px] border border-line bg-white shadow-[0_14px_48px_rgba(21,67,55,.05)]">
          <div className="grid md:grid-cols-[320px_minmax(0,1fr)] md:grid-rows-[auto_auto]">
            <div className="min-w-0 p-3 sm:p-4 md:border-r md:border-line">
              <div className="relative aspect-[4/3] overflow-hidden rounded-[22px] bg-[#eef7f2] shadow-[inset_0_1px_0_rgba(255,255,255,.72)]">
                <MealIllustration stage={program.stage as "mpasi" | "toddler" | "elderly"} title={menuTitle} groups={recommendedGroups} visualKey={menuVisualKey} fill />
              </div>
            </div>
            <div className="min-w-0 px-5 pb-5 pt-1 sm:px-6 sm:pb-6 md:flex md:flex-col md:justify-center md:py-6">
              {elderlySwallowingMode ? <p className="mb-3 inline-flex w-fit rounded-full border border-primary/20 bg-primary-light px-3 py-1 text-xs font-bold text-primary-dark">Fokus kandungan Â· bukan level tekstur</p> : null}
              <h3 id="menu-today-title" className="break-words text-xl font-semibold tracking-[-0.025em] sm:text-2xl">{menuTitle}</h3>
              <p className="mt-2 text-sm leading-6 text-secondary">{text(mealDetails.occasion, "Waktu makan sesuai panduan program.")}</p>
              <div className="mt-5 flex flex-wrap gap-2.5">
                {recommendedGroups.map((group) => {
                  const index = FOOD_GROUP_ORDER.indexOf(group);
                  const selected = foodGroupChecks[index] ?? false;
                  return <button key={group} type="button" disabled={!editable} aria-pressed={selected} onClick={() => {
                    if (!editable) return;
                    setFoodGroupChecks((current) => current.map((value, i) => i === index ? !value : value));
                    markDirty();
                  }} className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors ${selected ? "border-primary bg-primary-light text-primary-dark" : "border-line bg-background text-secondary"}`}><FoodGroupIcon group={group} size="sm" />{GROUP_LABELS[group]}</button>;
                })}
              </div>
            </div>
            <div className="hidden border-r border-line md:block" aria-hidden="true" />
            <div className="border-t border-line px-5 py-4 sm:px-6 sm:py-5">
              <p className="text-[11px] font-bold uppercase tracking-[.1em] text-muted">Catatan menu</p>
              <p className="mt-2 text-sm leading-6 text-secondary">{text(mealDetails.preparation, program.stage === "elderly" ? "Sesuaikan bahan dengan alergi atau pantangan, lalu gunakan bentuk yang sudah diketahui aman." : "Sesuaikan tekstur, porsi, dan bahan dengan profil serta toleransi anak.")}</p>
            </div>
          </div>
        </div>
      </section>

      <section className="mt-10" aria-labelledby="todo-title">
        <div className="flex flex-wrap items-end justify-between gap-3 border-b border-line pb-3">
          <div><p className="eyebrow">Tindakan terukur</p><h3 id="todo-title" className="mt-2 text-xl font-semibold">To Do hari ini</h3></div>
          <span className="text-xs text-muted">{editable ? `${doneCount} dari ${tasks.length} tindakan dilakukan` : "Hanya ditinjau"}</span>
        </div>

        {!tasks.length && program.stage !== "elderly" ? (
          <div className="mt-4"><Alert variant="warning" title="Aktivitas hari ini belum tersedia">Muat ulang halaman untuk melihat rencana terbaru. Riwayat hari yang sudah selesai tetap tersimpan.</Alert></div>
        ) : (
          <div className="mt-4 min-w-0 divide-y divide-line overflow-hidden rounded-[28px] border border-line bg-white">
            {tasks.map((task, index) => {
              const done = checks[index] ?? false;
              const value = results[task.key];
              const backendMetric = useBackendMeasurement ? savedMetricByTask[task.key] : undefined;
              const adherence = backendMetric ? (backendMetric.adherence ?? null) : taskAdherence(task, value);
              const status = backendMetric ? stage6StatusDisplay(backendMetric.status, backendMetric.adherence ?? null) : resultStatus(task, value);
              const actionLabel = task.action_text ?? task.action ?? task.target_label;
              return (
                <article key={task.key} className={`grid gap-3 px-4 py-4 sm:grid-cols-[36px_minmax(0,1fr)_minmax(260px,0.75fr)] sm:items-start sm:px-5 ${done ? "bg-primary-light/25" : "bg-white"}`}>
                  <button type="button" disabled={!editable} aria-label={`${done ? "Batalkan tindakan" : "Tandai tindakan"}: ${actionLabel}`} aria-pressed={done} onClick={() => toggleAction(index)} className={`flex h-8 w-8 items-center justify-center rounded-full border ${done ? "border-primary bg-primary text-white" : "border-slate-300 bg-white text-muted"}`}>{done ? "âœ“" : ""}</button>

                  <div className="min-w-0">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div className="min-w-0">
                        {task.stage5_engine_version && <p className="mb-1 text-[10px] font-bold uppercase tracking-[.1em] text-primary-dark">{task.priority === 1 ? "Fokus utama" : "Pendukung"}</p>}
                        <p className="text-sm font-semibold leading-6 text-text">{actionLabel}</p>
                      </div>
                      <span className={`rounded-full px-2 py-1 text-[11px] font-semibold ${done ? "bg-primary-light text-primary-dark" : "bg-slate-100 text-muted"}`}>{done ? "Dilakukan" : "Belum dilakukan"}</span>
                    </div>
                    <dl className="mt-2 grid gap-x-4 gap-y-1 text-xs sm:grid-cols-[72px_1fr]">
                      <dt className="font-semibold uppercase tracking-[.08em] text-muted">Target</dt><dd className="text-secondary">{targetDisplay(task)}</dd>
                      <dt className="font-semibold uppercase tracking-[.08em] text-muted">Status</dt><dd className={adherence === 100 ? "font-semibold text-primary-dark" : adherence === null ? "text-muted" : "font-semibold text-amber-700"}>{status}{!childAdaptive && adherence !== null ? ` Â· ${adherence}%` : ""}</dd>
                    </dl>
                    {task.why && <details className="mt-2 text-xs text-muted"><summary className="cursor-pointer font-semibold text-primary-dark">Mengapa target ini?</summary><p className="mt-1 max-w-xl leading-5">{task.why}</p>{task.evidence_rule?.source_name && <p className="mt-1 leading-5">Dasar: {task.evidence_rule.source_name}{task.evidence_rule.source_url ? ` Â· ${task.evidence_rule.source_url}` : ""}</p>}</details>}
                  </div>

                  <div className="min-w-0 rounded-xl bg-background/60 p-3">
                    <p className="text-[11px] font-bold uppercase tracking-[.1em] text-muted">{childAdaptive ? "Hasil hari ini" : "Data hasil"}</p>
                    <p className="mt-1 text-xs leading-5 text-secondary">{task.result_prompt ?? "Catat hasil aktual hari ini."}</p>
                    <div className="mt-2">
                      {task.input_type === "count" && <CountResult task={task} value={value} editable={editable} onChange={(next) => setTaskResult(task, next)} showTargetSuffix={!childAdaptive} />}
                      {task.input_type === "boolean" && <div className="flex flex-wrap gap-2" role="group" aria-label={task.result_prompt ?? "Hasil Ya atau Tidak"}>
                        <button type="button" disabled={!editable} aria-pressed={value === true} onClick={() => setTaskResult(task, true)} className={`min-h-9 rounded-full border px-3 py-1.5 text-xs font-semibold ${value === true ? "border-primary bg-primary text-white" : "border-line bg-white text-secondary"}`}>Ya</button>
                        <button type="button" disabled={!editable} aria-pressed={value === false} onClick={() => setTaskResult(task, false)} className={`min-h-9 rounded-full border px-3 py-1.5 text-xs font-semibold ${value === false ? "border-primary bg-primary text-white" : "border-line bg-white text-secondary"}`}>Tidak</button>
                      </div>}
                      {isChoiceLike(task) && <ChoiceResult task={task} value={value} editable={editable} onChange={(next) => setTaskResult(task, next)} />}
                    </div>
                    <p className="mt-2 text-xs font-semibold text-text">Hasil hari ini: {actualDisplay(task, value, !childAdaptive)}</p>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>

      {childAdaptive && <section className="mt-10" aria-labelledby="daily-log-title">
        <div className="flex flex-wrap items-end justify-between gap-3 border-b border-line pb-3"><div><p className="eyebrow">Hasil & pengalaman hari ini</p><h3 id="daily-log-title" className="mt-2 text-xl font-semibold">Catat sesi hari ini</h3></div><span className="text-xs text-muted">Jawab singkat sesuai kondisi hari ini</span></div>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-secondary">Jawaban singkat ini membantu rencana berikutnya tetap sesuai dengan pengalaman makan hari ini.</p>
        <div className="mt-5 min-w-0 grid gap-5 rounded-[28px] border border-line bg-white px-4 py-5 md:grid-cols-2 md:px-5">
          <QuickChoice label="Porsi" value={quickLog.portion} editable={editable} onChange={(value) => setQuickValue("portion", value)} options={[{value:"finished",label:"Habis"},{value:"partial",label:"Sebagian"},{value:"little",label:"Sedikit"},{value:"none",label:"Tidak dimakan"}]} />
          <QuickChoice label="Penerimaan" value={quickLog.acceptance} editable={editable} onChange={(value) => setQuickValue("acceptance", value)} options={[{value:"liked",label:"Suka"},{value:"neutral",label:"Netral"},{value:"refused",label:"Menolak"}]} />
          <QuickChoice label="Kondisi anak" value={quickLog.child_condition} editable={editable} onChange={(value) => setQuickValue("child_condition", value)} options={[{value:"healthy",label:"Sehat"},{value:"fussy",label:"Rewel"},{value:"sick",label:"Sakit"},{value:"fever",label:"Demam"},{value:"diarrhea",label:"Diare"},{value:"severe_teething",label:"Tumbuh gigi berat"}]} />
          <QuickChoice label="Makanan baru" value={quickLog.new_food} editable={editable} onChange={(value) => setQuickValue("new_food", value)} options={[{value:true,label:"Ya"},{value:false,label:"Tidak"}]} />
          <QuickChoice label="Reaksi tidak biasa" value={quickLog.reaction} editable={editable} onChange={(value) => {
            setQuickValue("reaction", value);
            if (value === "none") setQuickValue("reaction_notes", null);
          }} options={[{value:"none",label:"Tidak ada"},{value:"detected",label:"Ada"}]} />
          <QuickChoice label="Kesulitan caregiver" value={quickLog.parent_difficulty} editable={editable} onChange={(value) => setQuickValue("parent_difficulty", value)} options={[{value:"easy",label:"Mudah"},{value:"somewhat_difficult",label:"Cukup sulit"},{value:"difficult",label:"Sulit"}]} />
          {quickLog.reaction === "detected" && <div className="md:col-span-2">
            <Textarea
              label="Jelaskan reaksi tidak biasa yang terlihat"
              value={quickLog.reaction_notes ?? ""}
              disabled={!editable}
              rows={3}
              maxLength={500}
              placeholder="Contoh: muncul ruam ringan, muntah sekali, sulit bernapas, kejang, atau reaksi lain yang terlihat hari ini."
              helperText="Tuliskan apa yang benar-benar terlihat hari ini. Backend akan memeriksa tanda bahaya saat progress disimpan; pilihan â€˜Adaâ€™ saja tidak otomatis memicu Safety Hold."
              onChange={(event) => setQuickValue("reaction_notes", event.target.value)}
            />
          </div>}
          <QuickChoice label="Rencana dilakukan" value={quickLog.caregiver_adherence} editable={editable} onChange={(value) => setQuickValue("caregiver_adherence", value)} options={[{value:"yes",label:"Ya"},{value:"partial",label:"Sebagian"},{value:"no",label:"Belum"}]} />
          <div><label htmlFor="daily-texture" className="text-xs font-bold uppercase tracking-[.09em] text-muted">Tekstur / bentuk yang dicoba</label><input id="daily-texture" disabled={!editable} value={quickLog.texture ?? ""} onChange={(event) => setQuickValue("texture", event.target.value)} placeholder="Contoh: lumat, cincang, finger food" className="mt-2 min-h-10 w-full rounded-lg border border-line bg-white px-3 text-sm outline-none focus:border-primary" /></div>
        </div>
      </section>}

      {program.stage === "elderly" && <section className="mt-10" aria-labelledby="elderly-condition-title">
        <div className="border-b border-line pb-3"><p className="eyebrow">Kondisi & pengalaman makan/minum</p><h3 id="elderly-condition-title" className="mt-2 text-xl font-semibold">Bagaimana kondisi dan pengalaman makan/minum hari ini?</h3></div>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-secondary">Check-in ini khusus Lansia: catat kondisi umum, nafsu makan, cairan, kenyamanan, hambatan makan/minum, dan dukungan yang dibutuhkan. Hasil To Do tetap menjadi ukuran keterlaksanaan utama.</p>
        <div className="mt-5 min-w-0 grid gap-5 rounded-[28px] border border-line bg-white px-4 py-5 md:grid-cols-2 md:px-5">
          <div className="md:col-span-2">
            <QuickChoice
              label="Kondisi saat ini"
              value={quickLog.health_condition}
              editable={editable}
              onChange={(value) => setQuickValue("health_condition", value)}
              options={[
                { value: "well", label: "Baik" },
                { value: "unwell", label: "Kurang bugar" },
                { value: "fatigue", label: "Lemas / cepat lelah" },
                { value: "dizziness", label: "Pusing" },
                { value: "nausea", label: "Mual" },
                { value: "vomiting", label: "Muntah" },
                { value: "fever", label: "Demam" },
                { value: "diarrhea", label: "Diare" },
                { value: "constipation", label: "Sembelit" },
                { value: "pain_discomfort", label: "Nyeri / tidak nyaman" },
                { value: "other_concern", label: "Perubahan kondisi lain" },
              ]}
            />
          </div>
          <QuickChoice
            label="Nafsu makan hari ini"
            value={quickLog.appetite_status}
            editable={editable}
            onChange={(value) => setQuickValue("appetite_status", value)}
            options={[{ value: "good", label: "Baik" }, { value: "reduced", label: "Menurun" }, { value: "poor", label: "Sangat sedikit" }]}
          />
          <QuickChoice
            label="Cairan hari ini"
            value={quickLog.hydration_status}
            editable={editable}
            onChange={(value) => setQuickValue("hydration_status", value)}
            options={[{ value: "good", label: "Teratur" }, { value: "reduced", label: "Lebih sedikit" }, { value: "poor", label: "Sangat sedikit" }]}
          />
          <QuickChoice
            label="Kenyamanan makan/minum hari ini"
            value={quickLog.eating_difficulty}
            editable={editable}
            onChange={(value) => setQuickValue("eating_difficulty", value)}
            options={[{ value: "none", label: "Tidak ada kendala" }, { value: "some", label: "Ada kendala ringan" }, { value: "difficult", label: "Lebih sulit dari biasanya" }]}
          />
          <QuickChoice
            label="Bantuan saat makan/minum"
            value={quickLog.eating_support}
            editable={editable}
            onChange={(value) => setQuickValue("eating_support", value)}
            options={[{ value: "independent", label: "Mandiri" }, { value: "reminder", label: "Perlu diingatkan" }, { value: "assisted", label: "Perlu dibantu" }]}
          />
          <div className="md:col-span-2">
            <QuickChoice
              label="Hambatan utama makan/minum hari ini"
              value={quickLog.eating_barrier}
              editable={editable}
              onChange={(value) => setQuickValue("eating_barrier", value)}
              options={[
                { value: "none", label: "Tidak ada" },
                { value: "low_appetite", label: "Tidak terasa lapar" },
                { value: "early_satiety", label: "Cepat kenyang" },
                { value: "chewing", label: "Sulit mengunyah" },
                { value: "swallowing", label: "Menelan terasa lebih sulit" },
                { value: "preparation", label: "Sulit menyiapkan makanan" },
                { value: "availability", label: "Makanan/bahan tidak tersedia" },
                { value: "support", label: "Bantuan tidak tersedia" },
                { value: "other", label: "Hambatan lain" },
              ]}
            />
          </div>
        </div>
        <p className="mt-3 text-xs leading-5 text-muted">Program membaca pola beberapa hari untuk menyederhanakan, mempertahankan, atau menambah satu langkah kecil. Keberhasilan rencana dihitung dari hasil aktual setiap To Do, sehingga tidak perlu dijawab ulang di bagian ini. Input ini bukan diagnosis medis.</p>
      </section>}

      <section className="mt-10" aria-labelledby="complaint-title">
        <div className="border-b border-line pb-3"><p className="eyebrow">Catatan / keluhan</p><h3 id="complaint-title" className="mt-2 text-xl font-semibold">Apakah ada keluhan atau kendala hari ini?</h3></div>
        <div className="mt-4 flex flex-wrap gap-2">
          <button type="button" disabled={!editable} aria-label="Tidak ada keluhan" aria-pressed={hasComplaint === false} onClick={() => { setHasComplaint(false); setComplaintNote(""); markDirty(); }} className={`min-h-10 rounded-full border px-4 text-sm font-semibold ${hasComplaint === false ? "border-primary bg-primary text-white" : "border-line bg-white text-secondary"}`}>Tidak ada</button>
          <button type="button" disabled={!editable} aria-label="Ada keluhan" aria-pressed={hasComplaint === true} onClick={() => { setHasComplaint(true); markDirty(); }} className={`min-h-10 rounded-full border px-4 text-sm font-semibold ${hasComplaint === true ? "border-amber-500 bg-amber-50 text-amber-900" : "border-line bg-white text-secondary"}`}>Ada</button>
        </div>
        {hasComplaint === true && <div className="mt-4"><Textarea label="Ceritakan keluhan atau kendalanya" value={complaintNote} disabled={!editable} rows={3} maxLength={500} placeholder={program.stage === "elderly" ? "Contoh: cepat kenyang, sulit menyiapkan makanan, rasa tidak nyaman, atau bantuan tidak tersedia." : "Contoh: makanan ditolak, bahan tidak tersedia, atau tekstur sulit diterima."} onChange={(event) => { setComplaintNote(event.target.value); markDirty(); }} /></div>}
        {hasComplaint === null && editable && <p className="mt-3 text-xs font-semibold text-amber-700">Pilih salah satu jawaban sebelum menyimpan hari ini.</p>}
      </section>

      {error && <div className="mt-6"><Alert variant="error" title="Perlu diperiksa">{error}</Alert></div>}
      {emergencySafety && <div className="mt-6">
        <Alert variant="error" title="Tanda bahaya terdeteksi â€” segera cari pertolongan medis">
          {emergencySafety.recommended_action ?? (program.stage === "elderly" ? "Hentikan program untuk saat ini dan segera bawa lansia ke IGD/rumah sakit atau hubungi layanan darurat setempat." : "Hentikan program untuk saat ini dan segera bawa anak ke IGD/rumah sakit atau hubungi layanan darurat setempat.")}
        </Alert>
        {emergencySafety.red_flags?.length ? <ul className="mt-3 space-y-1 text-sm text-secondary" aria-label="Tanda bahaya yang terdeteksi">
          {emergencySafety.red_flags.map((flag) => <li key={flag.code ?? flag.label}>â€¢ {flag.label ?? "Tanda bahaya"}</li>)}
        </ul> : null}
      </div>}

      {editable && <div className="mt-8 flex flex-wrap items-center justify-between gap-4 border-t border-line pt-5">
        <div className="text-sm font-medium text-muted" aria-live="polite">
          {saveState === "DIRTY" && <>Perubahan belum disimpan<span className="sr-only">Unsaved changes</span></>}
          {saveState === "SAVING" && "Menyimpan..."}
          {saveState === "SAVED" && <>âœ“ Catatan hari ini sudah diperbarui<span className="sr-only">Perubahan sudah tersimpan</span></>}
          {saveState === "SAVE_ERROR" && "Gagal menyimpan Â· Perubahan tetap ada di layar"}
          {saveState === "IDLE" && "Belum ada perubahan baru"}
        </div>
        <Button aria-label={(childAdaptive || program.stage === "elderly") ? (saveState === "SAVED" ? "Catatan hari ini tersimpan" : saveState === "SAVING" ? "Menyimpan catatan hari ini" : "Simpan catatan hari ini") : (saveState === "SAVED" ? "Progress Saved" : saveState === "SAVING" ? "Saving Progress" : "Save Progress")} onClick={() => void persist()} isLoading={saveState === "SAVING"} loadingLabel="Menyimpan..." disabled={saveState !== "DIRTY"}>{(childAdaptive || program.stage === "elderly") ? "Simpan hari ini" : "Simpan progress"}</Button>
      </div>}




      <section className="mt-10 border-t border-line pt-7" aria-labelledby="today-result-title">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="eyebrow">Progress harian</p>
            <h3 id="today-result-title" className="mt-2 text-xl font-semibold">Hasil hari ini</h3>
            <p className="mt-2 text-sm font-semibold text-secondary">{childAdaptive ? `${doneCount} dari ${tasks.length} aktivitas selesai` : `${achievedCount} dari ${tasks.length} target tercapai`}</p>
          </div>
          {!childAdaptive && <strong className="text-2xl text-primary-dark">{Math.round(targetProgressPercent)}%</strong>}
        </div>
        <div className="mt-3"><ProgressBar value={childAdaptive ? dailyActivityProgress : targetProgressPercent} label={childAdaptive ? `${doneCount} dari ${tasks.length} aktivitas selesai` : `${achievedCount} dari ${tasks.length} target tercapai`} showPercentage={!childAdaptive} /></div>
        <div className="mt-5 overflow-x-auto">
          <table className={`w-full ${childAdaptive ? "min-w-[560px]" : "min-w-[640px]"} border-collapse text-left text-sm`}>
            <thead><tr className="border-b border-line text-xs uppercase tracking-[.08em] text-muted"><th className="py-2 pr-4">Aktivitas</th><th className="py-2 pr-4">Target</th><th className="py-2 pr-4">Hasil</th>{!childAdaptive && <th className="py-2 pr-4">Adherence</th>}<th className="py-2">Status</th></tr></thead>
            <tbody>{tasks.map((task) => { const value = results[task.key]; const backendMetric = useBackendMeasurement ? savedMetricByTask[task.key] : undefined; const adherence = backendMetric ? (backendMetric.adherence ?? null) : taskAdherence(task, value); const status = backendMetric ? stage6StatusDisplay(backendMetric.status, backendMetric.adherence ?? null) : resultStatus(task, value); return <tr key={`result-${task.key}`} className="border-b border-line/70"><td className="py-3 pr-4 font-semibold">{task.action_text ?? task.action ?? task.target_label}</td><td className="py-3 pr-4 text-secondary">{targetDisplay(task)}</td><td className="py-3 pr-4 text-secondary">{actualDisplay(task, value, !childAdaptive)}</td>{!childAdaptive && <td className="py-3 pr-4 text-secondary">{adherence === null ? "â€”" : `${adherence}%`}</td>}<td className="py-3 font-semibold">{status}</td></tr>; })}</tbody>
          </table>
        </div>
      </section>

      {childAdaptive && (() => {
        const dailySummary = lastResponse?.daily_summary ?? day.action_details?.daily_summary;
        const adaptation = lastResponse?.adaptation ?? day.action_details?.adaptation;
        const safety = lastResponse?.safety ?? day.action_details?.safety;
        const safetyBefore = safety?.before_adaptation;
        if (!dailySummary && !adaptation && !safetyBefore) return null;
        return <section className="mt-10 border-t border-line pt-7" aria-labelledby="daily-summary-title">
          {safetyBefore?.blocked && (!safetyBefore.emergency || !emergencySafety) && <div className="mb-5"><Alert variant={safetyBefore.emergency ? "error" : "warning"} title={safetyBefore.emergency ? "Tanda bahaya terdeteksi" : "Perhatian untuk hari ini"}>{safetyBefore.user_facing_reason ?? safetyBefore.reason ?? "Penyesuaian rencana dijeda sementara demi keamanan."} {safetyBefore.recommended_action ?? ""}</Alert></div>}
          <p className="eyebrow">Hari ini</p><h3 id="daily-summary-title" className="mt-2 text-xl font-semibold">Ringkasan hari ini</h3>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <div className="bg-primary-light/25 p-4"><p className="text-xs font-bold uppercase tracking-[.1em] text-primary-dark">Yang berjalan baik</p><p className="mt-2 text-sm leading-6 text-secondary">{dailySummary?.what_went_well ?? "Hari ini sudah dicatat."}</p></div>
            <div className="bg-amber-50 p-4"><p className="text-xs font-bold uppercase tracking-[.1em] text-amber-800">Yang terasa sulit</p><p className="mt-2 text-sm leading-6 text-secondary">{dailySummary?.what_was_difficult ?? "Belum ada kesulitan utama yang tercatat."}</p></div>
            <div className="border border-line p-4 md:col-span-2"><p className="text-xs font-bold uppercase tracking-[.1em] text-muted">Penyesuaian rencana</p><div className="mt-3 grid gap-3 sm:grid-cols-3"><div><p className="text-xs font-bold uppercase tracking-[.08em] text-muted">Apa berubah?</p><p className="mt-1 text-sm leading-6 text-secondary">{adaptation?.explanation?.what_changed ?? dailySummary?.what_changed ?? "Rencana utama belum berubah."}</p></div><div><p className="text-xs font-bold uppercase tracking-[.08em] text-muted">Kenapa?</p><p className="mt-1 text-sm leading-6 text-secondary">{adaptation?.explanation?.why ?? adaptation?.user_facing_reason ?? dailySummary?.why_plan_changes ?? "Belum ada alasan perubahan baru."}</p></div><div><p className="text-xs font-bold uppercase tracking-[.08em] text-muted">Apa berikutnya?</p><p className="mt-1 text-sm leading-6 text-secondary">{adaptation?.explanation?.what_next ?? dailySummary?.what_next ?? dailySummary?.tomorrow_preview ?? "Lanjutkan tindakan utama dan catat hasil hari ini."}</p></div></div></div>
            <div className="border border-line p-4 md:col-span-2"><p className="text-xs font-bold uppercase tracking-[.1em] text-muted">Fokus berikutnya</p><p className="mt-2 text-sm leading-6 text-secondary">{dailySummary?.tomorrow_preview ?? "Fokus berikutnya akan mengikuti catatan hari ini."}</p></div>
          </div>
        </section>;
      })()}

      {blockReviewError ? <div className="mt-8"><Alert variant="warning" title="Evaluasi Hari 14 belum dapat dimuat">{blockReviewError} Hasil harian yang sudah tersimpan tetap aman.</Alert></div> : null}
      {blockReview ? <NutritionBlockReviewInline review={blockReview} /> : null}

      <AuthGate open={authOpen} onClose={() => setAuthOpen(false)} onAuthenticated={async () => { setAuthOpen(false); setError(""); }} />
    </section>
  );
}


