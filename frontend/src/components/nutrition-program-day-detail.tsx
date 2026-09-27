"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  Check,
  ChevronLeft,
  ChevronDown,
  Circle,
  Clock3,
  Lightbulb,
  LockKeyhole,
  Save,
  X,
} from "lucide-react";
import { AuthGate } from "@/components/auth-gate";
import { NutritionProgramDailyWorkspace } from "@/components/nutrition-program-daily-workspace";
import { useAuth } from "@/components/auth-provider";
import { ProgramCountdown } from "@/components/program-countdown";
import { formatProgramRemaining, useNutritionProgramShellOptional } from "@/components/nutrition-program-shell";
import {
  NutritionMobileProgramNav,
  NutritionProgramNav,
} from "@/components/nutrition-program-ui";
import {
  FOOD_GROUP_ORDER,
  FoodGroupCard,
  FoodGroupIcon,
  MealIllustration,
  foodGroupsFrom,
} from "@/components/nutrition-visuals";
import { Alert, Badge, Button, ProgressBar, Textarea } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  formatPercent,
  getNutritionProgram,
  getNutritionProgramDay,
  saveDailyLog,
  type ProgramDayDetail,
  type ProgramDetail,
} from "@/lib/nutrition-program";

type SaveState = "IDLE" | "DIRTY" | "SAVING" | "SAVED" | "SAVE_ERROR";

function text(value: unknown, fallback = "—") {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function list(value: unknown): string[] {
  return Array.isArray(value) ? value.map(String).filter(Boolean) : [];
}

export function NutritionProgramDayDetail({ programId, dayNumber, initialDetail, initialProgram }: { programId: string; dayNumber: number; initialDetail?: ProgramDayDetail; initialProgram?: ProgramDetail }) {
  const router = useRouter();
  const { status } = useAuth();
  const shell = useNutritionProgramShellOptional();
  const shellElapsedSeconds = (shell as { elapsedSeconds: number } | null)?.elapsedSeconds;
  const [detail, setDetail] = useState<ProgramDayDetail | null>(initialDetail ?? null);
  const [program, setProgram] = useState<ProgramDetail | null>(initialProgram ?? null);
  const [nextDay, setNextDay] = useState<ProgramDayDetail | null>(null);
  const [checks, setChecks] = useState<boolean[]>(initialDetail?.day.checklist_state ?? []);
  const [foodGroupChecks, setFoodGroupChecks] = useState<boolean[]>(FOOD_GROUP_ORDER.map(() => false));
  const [hasComplaint, setHasComplaint] = useState<boolean | null>(initialDetail?.day.has_complaint ?? null);
  const [complaintNote, setComplaintNote] = useState(initialDetail?.day.complaint_note ?? "");
  const [loading, setLoading] = useState(!(initialDetail && initialProgram));
  const [error, setError] = useState("");
  const [saveState, setSaveState] = useState<SaveState>("IDLE");
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null);
  const [authOpen, setAuthOpen] = useState(false);
  const [recipeOpen, setRecipeOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const value = await getNutritionProgramDay(programId, dayNumber);
      const full = shell?.program ?? await getNutritionProgram(programId);
      setDetail(value);
      setProgram(full);
      setChecks(value.day.checklist_state ?? []);
      setFoodGroupChecks(FOOD_GROUP_ORDER.map((_, index) => value.day.food_group_state?.[index] ?? false));
      setHasComplaint(value.day.has_complaint ?? null);
      setComplaintNote(value.day.complaint_note ?? "");
      setLastSavedAt(value.last_activity_at ?? null);
      setSaveState("IDLE");

      if (value.day.status === "COMPLETED" && dayNumber < value.duration_days) {
        try {
          setNextDay(await getNutritionProgramDay(programId, dayNumber + 1));
        } catch {
          setNextDay(null);
        }
      } else {
        setNextDay(null);
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Login diperlukan untuk membuka hari program tersimpan ini.");
      } else if (err instanceof ApiError && err.status === 404) {
        setError("Hari program tidak ditemukan atau tidak dapat diakses oleh akun ini.");
      } else {
        setError(err instanceof Error ? err.message : "Day detail belum dapat dimuat.");
      }
      setDetail(null);
      setProgram(null);
    } finally {
      setLoading(false);
    }
  }, [dayNumber, programId, shell?.program]);

  useEffect(() => {
    if (initialDetail && initialProgram) return;
    if (status === "authenticated") void load();
    if (status === "unauthenticated") {
      const next = `${window.location.pathname}${window.location.search}${window.location.hash}`;
      router.replace(`/login?next=${encodeURIComponent(next)}`);
      setDetail(null);
      setLoading(false);
    }
  }, [initialDetail, initialProgram, load, router, status]);

  useEffect(() => {
    if (saveState !== "DIRTY") return;
    const handler = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [saveState]);

  const day = detail?.day ?? null;
  const dayStatus = day?.status;
  const dayRemainingSeconds = day?.remaining_seconds ?? null;

  useEffect(() => {
    if (initialDetail) return;
    if (dayStatus !== "LOCKED" || dayRemainingSeconds === null) return;
    const timer = window.setTimeout(() => void load(), Math.max(0, dayRemainingSeconds * 1000) + 400);
    return () => window.clearTimeout(timer);
  }, [dayRemainingSeconds, dayStatus, initialDetail, load]);

  const editable = Boolean(day && ["AVAILABLE", "IN_PROGRESS"].includes(day.status) && detail?.program_status === "ACTIVE");
  const primaryGoal = detail?.goal ?? null;
  const doneCount = useMemo(() => checks.filter(Boolean).length, [checks]);
  const mealDetails = day?.meal_guidance_details ?? {};
  const recommendedGroups = foodGroupsFrom(mealDetails.food_groups);
  const interactiveFoodGroups = recommendedGroups.length ? recommendedGroups : FOOD_GROUP_ORDER;
  const selectedFoodGroupCount = useMemo(() => interactiveFoodGroups.filter((group) => foodGroupChecks[FOOD_GROUP_ORDER.indexOf(group)] ?? false).length, [foodGroupChecks, interactiveFoodGroups]);
  const safetyNotes = list(mealDetails.safety_notes);
  const allActionsDone = Boolean(day?.checklist.length && doneCount === day.checklist.length);
  const reflectionReady = hasComplaint !== null && (!hasComplaint || complaintNote.trim().length > 0);

  function markDirty() {
    if (!editable) return;
    setSaveState("DIRTY");
    setError("");
  }

  function chooseComplaint(value: boolean) {
    if (!editable) return;
    setHasComplaint(value);
    if (!value) setComplaintNote("");
    markDirty();
  }

  async function save() {
    if (!detail || !day || !editable || saveState !== "DIRTY") return;
    setSaveState("SAVING");
    setError("");
    try {
      const response = await saveDailyLog(programId, day.day_number, {
        checklistState: checks,
        foodGroupState: foodGroupChecks,
        hasComplaint,
        complaintNote,
      });

      setLastSavedAt(response.saved_at);
      setSaveState("SAVED");
      setFoodGroupChecks(FOOD_GROUP_ORDER.map((_, index) => response.food_group_state?.[index] ?? false));
      setHasComplaint(response.has_complaint ?? null);
      setComplaintNote(response.complaint_note ?? "");
      setDetail((current) =>
        current
          ? {
              ...current,
              program_status: response.program_status,
              current_day: response.current_day,
              progress_percent: response.progress_percent,
              missed_days: response.missed_days,
              inactive_days: response.inactive_days,
              last_activity_at: response.saved_at,
              goal: response.goals[0] ?? current.goal,
              cumulative_goal: response.cumulative_goal ?? current.cumulative_goal,
              day: {
                ...current.day,
                checklist_state: response.checklist_state,
                food_group_state: response.food_group_state,
                has_complaint: response.has_complaint,
                complaint_note: response.complaint_note,
                completed: response.day_completed,
                completed_at: response.day_completed_at,
                status: response.day_completed ? "COMPLETED" : "IN_PROGRESS",
              },
            }
          : current,
      );

      if (response.day_completed && dayNumber < detail.duration_days) {
        try {
          setNextDay(await getNutritionProgramDay(programId, dayNumber + 1));
        } catch {
          setNextDay(null);
        }
      }

      setProgram((current) =>
        current
          ? {
              ...current,
              progress_percent: response.progress_percent,
              days_completed: response.days_completed,
              missed_days: response.missed_days,
              current_day: response.current_day,
              goals: response.goals,
              goal: response.goals[0] ?? current.goal,
            }
          : current,
      );
      if (shell) void shell.refreshProgram();
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setSaveState("DIRTY");
        setError("Sesi berakhir. Masuk lagi untuk menyimpan.");
        setAuthOpen(true);
        return;
      }
      setSaveState("SAVE_ERROR");
      setError(err instanceof Error ? err.message : "Progress belum dapat disimpan.");
    }
  }

  if (status === "loading" || loading) {
    return <div className="min-h-[520px] animate-pulse rounded-2xl border border-line bg-surface" aria-label="Memuat daily guidance" />;
  }

  if (status === "unauthenticated") {
    return <section className="rounded-2xl border border-line bg-white p-8" aria-live="polite"><p className="eyebrow">Guided nutrition</p><h2 className="mt-4 text-4xl font-semibold tracking-[-0.04em]">Mengalihkan ke halaman masuk.</h2><p className="mt-4 text-sm leading-7 text-secondary">Setelah masuk, kamu akan kembali ke hari program ini.</p></section>;
  }

  if (!detail || !day || !program) {
    return (
      <div className="rounded-2xl border border-line bg-white p-8">
        <Alert variant="error">{error || "Daily guidance belum dapat dibuka."}</Alert>
        <Link href={`/nutrition/program/${programId}`} className="mt-6 inline-flex text-sm font-semibold text-primary-dark">← Program Overview</Link>
      </div>
    );
  }

  if (day.status === "LOCKED") {
    return (
      <div className="nutrition-enter pb-24 lg:pb-0">
        <div className={shell ? "grid gap-4" : "grid gap-4 xl:grid-cols-[200px_minmax(0,1fr)] 2xl:grid-cols-[210px_minmax(0,1fr)]"}>
          {!shell && <aside className="hidden xl:block"><NutritionProgramNav programId={programId} currentDay={detail.current_day} active="today" /></aside>}
          <main>
            <section className="relative mt-2 min-h-[470px] overflow-hidden rounded-[28px] border border-line bg-white" aria-labelledby="locked-day-title">
              <div aria-hidden="true" className="absolute inset-0 select-none overflow-hidden opacity-45 blur-[3px]"><div className="space-y-8 p-7 sm:p-10"><div className="h-3 w-28 rounded-full bg-primary-light"/><div className="space-y-3"><div className="h-7 w-3/5 rounded-lg bg-slate-200"/><div className="h-3 w-4/5 rounded-full bg-slate-100"/><div className="h-3 w-2/3 rounded-full bg-slate-100"/></div><div className="grid gap-4 sm:grid-cols-2"><div className="h-28 rounded-2xl border border-line bg-background"/><div className="h-28 rounded-2xl border border-line bg-background"/></div><div className="h-36 rounded-2xl border border-line bg-background"/></div></div>
              <div className="absolute inset-0 bg-white/74 backdrop-blur-[1px]" aria-hidden="true"/>
              <div className="relative z-10 flex min-h-[470px] items-center justify-center p-5 sm:p-8"><div className="w-full max-w-md text-center"><span className="mx-auto flex h-14 w-14 items-center justify-center rounded-full border border-line bg-white text-primary-dark shadow-sm"><LockKeyhole size={24}/></span><p className="eyebrow mt-5">Hari {day.day_number}</p><h2 id="locked-day-title" className="mt-2 text-3xl font-semibold tracking-[-.035em]">Belum tersedia</h2><p className="mt-3 text-sm leading-7 text-secondary">Panduan berikutnya akan terbuka sesuai jadwal program. Aktivitas hari ini tetap tersembunyi sampai backend membukanya.</p>{day.remaining_seconds > 0 ? <div className="mx-auto mt-5 inline-flex items-center gap-2 rounded-full border border-line bg-white px-4 py-2 text-sm font-semibold text-primary-dark" aria-live="polite"><span>Tersedia dalam <ProgramCountdown seconds={day.remaining_seconds} syncElapsedSeconds={shellElapsedSeconds} onExpire={() => void load()} /></span></div> : null}<div className="mt-7"><Link href={`/nutrition/program/${programId}`} className="inline-flex min-h-11 items-center justify-center rounded-full border border-line bg-white px-5 text-sm font-semibold text-primary-dark">← Kembali ke Program</Link></div></div></div>
            </section>
          </main>
        </div>
        {!shell && <NutritionMobileProgramNav programId={programId} currentDay={detail.current_day} active="today" />}
      </div>
    );
  }


  const missed = day.status === "MISSED";
  const structuredChildDay = Boolean(!missed && ["mpasi", "toddler"].includes(program.stage) && Array.isArray(day.action_details?.tasks) && day.action_details.tasks.length > 0);

  if (structuredChildDay) {
    return (
      <div className="space-y-6">
        <Link href={`/nutrition/program/${programId}/progress`} className="inline-flex min-h-11 items-center text-sm font-semibold text-primary-dark"><ChevronLeft className="mr-1" size={16}/> Kembali ke Progres</Link>
        <div className="border-y border-line py-5">
          <p className="eyebrow">Hari {day.day_number} dari {detail.duration_days}</p>
          <span className="sr-only">Day {day.day_number} of {detail.duration_days}</span>
          <h2 className="mt-2 text-3xl font-semibold tracking-[-.04em]">{text(day.focus, `Review Hari ${day.day_number}`)}</h2>
          <p className="mt-2 text-sm text-secondary">Tindakan, target, status, dan data hasil berasal dari Program Day ini sendiri. Progress hari lain tidak dipakai sebagai initial state.</p>
        </div>
        <NutritionProgramDailyWorkspace
          key={day.id}
          program={program}
          day={day}
          onProgramRefresh={(fresh) => {
            setProgram(fresh);
            shell?.setProgram(fresh);
            const refreshedDay = fresh.days.find((item) => item.day_number === dayNumber);
            if (refreshedDay) {
              setDetail((current) => current ? {
                ...current,
                program_status: fresh.status,
                current_day: fresh.current_day,
                progress_percent: fresh.progress_percent,
                missed_days: fresh.missed_days,
                last_activity_at: fresh.last_activity_at,
                goal: fresh.goals[0] ?? fresh.goal ?? current.goal,
                day: refreshedDay,
              } : current);
            }
          }}
        />
      </div>
    );
  }

  const completed = day.status === "COMPLETED";
  const saveButtonLabel = saveState === "SAVING" ? "Saving..." : saveState === "SAVED" || completed ? "✓ Progress Saved" : "Save Progress";
  const nextScheduledDay = nextDay?.day ?? program.days.find((item) => item.day_number > day.day_number && item.status === "LOCKED") ?? null;
  const programLabel = program.stage === "mpasi" ? "MPASI Guided Program" : program.stage === "toddler" ? "Toddler Guided Program" : "Lansia Guided Program";
  const programRemaining = Math.max(0, program.duration_days - program.current_day);
  const currentDayNumber = detail.current_day;
  const selectedDayNumber = day.day_number;

  function dayTone(item: ProgramDetail["days"][number]) {
    const current = item.day_number === currentDayNumber && ["AVAILABLE", "IN_PROGRESS"].includes(item.status);
    if (item.day_number === selectedDayNumber) return "border-primary/35 bg-primary-light text-primary-dark";
    if (current) return "border-teal-300 bg-teal-50 text-teal-900";
    if (item.status === "COMPLETED") return "border-emerald-200 bg-emerald-50/70 text-emerald-900";
    if (item.status === "MISSED") return "border-amber-200 bg-amber-50/80 text-amber-900";
    if (item.status === "LOCKED") return "border-slate-200 bg-slate-50 text-slate-500";
    return "border-line bg-white text-text";
  }

  function dayStatusText(item: ProgramDetail["days"][number]) {
    const current = item.day_number === currentDayNumber && ["AVAILABLE", "IN_PROGRESS"].includes(item.status);
    if (current) return "TODAY";
    return item.status;
  }

  return (
    <div className="nutrition-enter pb-24 lg:pb-0">
      <div className={shell ? "grid gap-5" : "grid gap-5 xl:grid-cols-[190px_minmax(0,1fr)_255px] 2xl:grid-cols-[200px_minmax(0,1fr)_270px]"}>
        {!shell && <aside className="hidden xl:block">
          <div className="sticky top-20 space-y-3">
            <NutritionProgramNav programId={programId} currentDay={detail.current_day} active="today" />
            <section className="rounded-2xl border border-line bg-white p-3 shadow-[0_10px_35px_rgba(21,67,55,.04)]">
              <div className="flex items-center justify-between px-2 pb-2">
                <p className="text-[10px] font-black uppercase tracking-[.12em] text-muted">Day navigation</p>
                <span className="text-[10px] font-bold text-muted">{day.day_number}/{detail.duration_days}</span>
              </div>
              <div className="max-h-[350px] space-y-1.5 overflow-y-auto pr-1">
                {program.days.map((item) => (
                  <Link
                    key={item.id}
                    href={`/nutrition/program/${programId}/day/${item.day_number}`}
                    aria-current={item.day_number === day.day_number ? "page" : undefined}
                    className={`flex min-h-11 items-center gap-2 rounded-xl border px-2.5 py-2 text-xs transition-colors ${dayTone(item)}`}
                  >
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white/85 text-[10px] font-black">{item.day_number}</span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-semibold">{item.focus}</span>
                      <span className="mt-0.5 block text-[9px] font-black uppercase tracking-[.08em] opacity-70">{dayStatusText(item)}</span>
                    </span>
                  </Link>
                ))}
              </div>
            </section>
          </div>
        </aside>}

        <main className="min-w-0 space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <Link href={`/nutrition/program/${programId}`} className="inline-flex min-h-10 items-center gap-1 text-xs font-bold uppercase tracking-[.12em] text-muted hover:text-text">
              <ChevronLeft size={14} /> Kembali ke Program
            </Link>
            <p className="hidden text-xs font-semibold text-muted sm:block">{programLabel}</p>
          </div>

          <details className="rounded-2xl border border-line bg-white p-3 xl:hidden">
            <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 px-2 text-sm font-semibold text-text">
              <span>Day {day.day_number} of {detail.duration_days} · Pilih Hari</span>
              <ChevronDown size={17} className="text-muted" />
            </summary>
            <div className="mt-2 grid max-h-[310px] gap-2 overflow-y-auto sm:grid-cols-2">
              {program.days.map((item) => (
                <Link key={item.id} href={`/nutrition/program/${programId}/day/${item.day_number}`} className={`flex min-h-12 items-center gap-3 rounded-xl border px-3 py-2 text-sm ${dayTone(item)}`}>
                  <span className="font-black">{item.day_number}</span>
                  <span className="min-w-0 flex-1 truncate font-semibold">{item.focus}</span>
                  <span className="text-[10px] font-black uppercase">{dayStatusText(item)}</span>
                </Link>
              ))}
            </div>
          </details>

          <header className="rounded-2xl border border-line bg-white px-5 py-5 shadow-[0_12px_40px_rgba(21,67,55,.04)] sm:px-6">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={completed ? "success" : missed ? "warning" : "info"}>{day.status}</Badge>
              <p className="eyebrow">Day {day.day_number} of {detail.duration_days}</p>
            </div>
            <div className="mt-3 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-[.12em] text-primary-dark">{programLabel}</p>
                <h2 className="mt-2 text-4xl font-semibold tracking-[-0.05em] md:text-5xl">{day.focus}</h2>
              </div>
              <p className="max-w-md text-sm leading-6 text-secondary">{text(day.action_details?.why, "Tindakan utama hari ini membantu goal program nutrisi tetap konsisten.")}</p>
            </div>
          </header>

          <section className="overflow-hidden rounded-2xl border border-primary/20 bg-[linear-gradient(135deg,#eef9f5_0%,#f8fbf9_62%,#fff9ed_100%)]">
            <div className="grid gap-0 lg:grid-cols-[minmax(0,1fr)_220px]">
              <div className="p-5 sm:p-6">
                <p className="eyebrow text-primary-dark">Today&apos;s Focus</p>
                <h2 className="mt-2 max-w-2xl text-2xl font-semibold tracking-[-0.035em] md:text-3xl">{text(day.action_details?.action, day.recommended_action)}</h2>
                <div className="mt-4 border-l-2 border-primary/25 pl-4">
                  <p className="text-[10px] font-black uppercase tracking-[.11em] text-muted">Why it matters</p>
                  <p className="mt-1 text-sm leading-6 text-secondary">{text(day.action_details?.why, "Mendukung rutinitas program dan goal yang sedang dijalankan.")}</p>
                </div>
                <div className="mt-5 grid gap-x-6 gap-y-4 sm:grid-cols-2">
                  <div><p className="text-[10px] font-black uppercase tracking-[.11em] text-primary-dark">When</p><p className="mt-1 text-sm leading-6">{text(day.action_details?.when, "Hari ini")}</p></div>
                  <div><p className="text-[10px] font-black uppercase tracking-[.11em] text-primary-dark">How</p><p className="mt-1 text-sm leading-6">{text(day.action_details?.how, "Ikuti meal guidance dan checklist hari ini.")}</p></div>
                  <div className="sm:col-span-2"><p className="text-[10px] font-black uppercase tracking-[.11em] text-primary-dark">Done when</p><p className="mt-1 text-sm leading-6">{text(day.action_details?.completion_criteria, "Checklist dan refleksi hari ini sudah tersimpan.")}</p></div>
                </div>
              </div>
              <div className="hidden border-l border-primary/10 p-3 lg:block">
                <MealIllustration stage={program.stage} title={text(mealDetails.example, day.focus)} groups={recommendedGroups} compact />
              </div>
            </div>
          </section>

          <section className="rounded-2xl border border-line bg-white p-5 sm:p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="eyebrow">Meal Guidance</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-[-0.035em]">Menu hari ini</h2>
              </div>
              <Button variant="secondary" onClick={() => setRecipeOpen(true)}>Lihat Detail Menu <ArrowRight size={15} /></Button>
            </div>
            <div className="mt-5 grid gap-5 md:grid-cols-[210px_minmax(0,1fr)] md:items-start">
              <MealIllustration stage={program.stage} title={text(mealDetails.example, day.focus)} groups={recommendedGroups} compact />
              <div className="min-w-0">
                <p className="text-xs font-black uppercase tracking-[.11em] text-muted">Main meal</p>
                <h3 className="mt-2 text-2xl font-semibold tracking-[-0.03em]">{text(mealDetails.example, day.focus)}</h3>
                <p className="mt-2 text-sm text-secondary">{text(mealDetails.occasion, "Waktu makan sesuai panduan hari ini")}</p>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <div><p className="text-[10px] font-black uppercase tracking-[.1em] text-muted">Preparation</p><p className="mt-1 text-sm leading-6 text-secondary">{text(mealDetails.preparation, "Ikuti tekstur dan preparation guidance yang tersimpan.")}</p></div>
                  <div><p className="text-[10px] font-black uppercase tracking-[.1em] text-muted">Alternative</p><p className="mt-1 text-sm leading-6 text-secondary">{text(mealDetails.substitutions, "Gunakan alternatif kelompok pangan setara sesuai toleransi.")}</p></div>
                </div>
              </div>
            </div>

            <div className="mt-5 border-t border-line pt-4">
              <div className="flex flex-wrap items-end justify-between gap-2">
                <div><p className="text-[10px] font-black uppercase tracking-[.11em] text-muted">Food groups</p><p className="mt-1 text-xs text-secondary">Centang yang benar-benar ada/diberikan hari ini.</p></div>
                <span className="text-xs font-bold text-primary-dark">{selectedFoodGroupCount}/{interactiveFoodGroups.length} dicatat</span>
              </div>
              <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                {interactiveFoodGroups.map((group) => {
                  const index = FOOD_GROUP_ORDER.indexOf(group);
                  const selected = foodGroupChecks[index] ?? false;
                  const label = group === "healthy-fat" ? "Lemak baik" : group === "vegetable" ? "Sayuran" : group === "fruit" ? "Buah" : group === "protein" ? "Protein" : "Karbohidrat";
                  return (
                    <button
                      key={group}
                      type="button"
                      disabled={!editable}
                      aria-pressed={selected}
                      onClick={() => {
                        if (!editable) return;
                        setFoodGroupChecks((current) => current.map((value, i) => i === index ? !value : value));
                        markDirty();
                      }}
                      className={`flex min-h-14 items-center gap-2 rounded-xl border px-3 py-2 text-left transition-all motion-reduce:transition-none ${selected ? "border-primary/30 bg-primary-light text-primary-dark" : "border-line bg-background/45 text-secondary hover:border-primary/25"} disabled:cursor-not-allowed disabled:opacity-65`}
                    >
                      <FoodGroupIcon group={group} size="sm" />
                      <span className="min-w-0 flex-1 text-xs font-semibold">{label}</span>
                      <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border ${selected ? "border-primary bg-primary text-white" : "border-slate-300 bg-white"}`}>{selected ? <Check size={12} /> : null}</span>
                    </button>
                  );
                })}
              </div>
              <p className="mt-2 text-[11px] leading-5 text-muted">Catatan kelompok pangan adalah pembelajaran komposisi menu, bukan penilaian kecukupan gizi.</p>
            </div>
          </section>

          <section className={`rounded-2xl border p-5 sm:p-6 ${missed ? "border-amber-200 bg-amber-50/60" : completed ? "border-emerald-200 bg-emerald-50/35" : "border-line bg-white"}`}>
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className={`eyebrow ${missed ? "text-amber-800" : ""}`}>{missed ? "Checklist expired · missed" : "Today&apos;s Checklist"}</p>
                {missed ? (
                  <>
                    <h2 className="mt-1.5 text-2xl font-semibold tracking-[-0.03em]">Hari sudah terkunci</h2>
                    <p className="mt-2 text-sm font-semibold text-amber-800">Progress harian ditutup tepat pukul 00.00</p>
                    <p className="mt-1 text-sm text-amber-800">Hari ini sudah expired. Checklist hanya dapat direview.</p>
                  </>
                ) : (
                  <h2 className="mt-1.5 text-2xl font-semibold tracking-[-0.03em]">{doneCount} dari {day.checklist.length} tindakan selesai</h2>
                )}
              </div>
              <div className="text-xs font-semibold text-muted">{saveState === "DIRTY" ? "Unsaved changes" : saveState === "SAVING" ? "Saving..." : lastSavedAt ? `Last saved ${new Date(lastSavedAt).toLocaleString("id-ID")}` : "Belum ada perubahan baru"}</div>
            </div>

            <div className="mt-4 grid gap-2.5 lg:grid-cols-3">
              {day.checklist.map((item, index) => {
                const content = (
                  <>
                    <input type="checkbox" className="sr-only" checked={checks[index] ?? false} disabled={!editable} onChange={(event) => { setChecks((current) => current.map((value, i) => i === index ? event.target.checked : value)); markDirty(); }} />
                    {missed ? (
                      <button
                        type="button"
                        disabled
                        aria-label={`Tandai tindakan: ${item}`}
                        aria-pressed={checks[index] ?? false}
                        className="mt-0.5 flex h-8 w-8 shrink-0 cursor-not-allowed items-center justify-center rounded-full border border-amber-300 bg-amber-50 text-amber-700 opacity-80"
                      ><X size={14} /></button>
                    ) : (
                      <span className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border ${checks[index] ? "border-primary bg-primary text-white" : "border-slate-300 bg-white"}`}>{checks[index] ? <Check size={15} /> : <Circle size={10} />}</span>
                    )}
                    <span className="min-w-0 flex-1"><span className={`block text-sm font-semibold ${missed ? "text-amber-950" : checks[index] ? "text-primary-dark" : "text-text"}`}>{item}</span><span className={`mt-1 block text-xs leading-5 ${missed ? "font-semibold text-amber-700" : "text-muted"}`}>{missed ? "Expired · tidak dapat diubah." : checks[index] ? "Completed" : "Tap untuk mencatat tindakan ini."}</span></span>
                  </>
                );
                const className = `flex min-h-[92px] items-start gap-3 rounded-xl border p-4 transition-all duration-300 motion-reduce:transition-none ${missed ? "border-amber-200 bg-white/70 opacity-80" : checks[index] ? "border-primary/25 bg-primary-light" : "border-line bg-white"} ${editable ? "cursor-pointer hover:border-primary/30" : "cursor-not-allowed"}`;
                return missed ? (
                  <div key={item} className={className} aria-disabled="true">{content}</div>
                ) : (
                  <label key={item} className={className} aria-disabled={!editable}>{content}</label>
                );
              })}
            </div>

            <div className="mt-4 rounded-xl border border-line bg-background/55 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div><p className="text-sm font-semibold text-text">Apakah ada keluhan atau kendala hari ini?</p><p className="mt-1 text-xs leading-5 text-muted">Jawab singkat sebelum hari dapat berstatus completed.</p></div>
                {hasComplaint !== null && <Badge variant={hasComplaint ? "warning" : "success"}>{hasComplaint ? "Ada keluhan" : "Tidak ada keluhan"}</Badge>}
              </div>
              <div className="mt-3 flex flex-wrap gap-2" role="group" aria-label="Apakah ada keluhan atau kendala hari ini?">
                <button type="button" disabled={!editable} aria-pressed={hasComplaint === false} onClick={() => chooseComplaint(false)} className={`min-h-11 rounded-full border px-4 text-sm font-semibold transition-colors ${hasComplaint === false ? "border-primary bg-primary text-white" : "border-line bg-white text-secondary hover:border-primary/40"} disabled:cursor-not-allowed disabled:opacity-70`}>Tidak ada keluhan</button>
                <button type="button" disabled={!editable} aria-pressed={hasComplaint === true} onClick={() => chooseComplaint(true)} className={`min-h-11 rounded-full border px-4 text-sm font-semibold transition-colors ${hasComplaint === true ? "border-amber-500 bg-amber-50 text-amber-900" : "border-line bg-white text-secondary hover:border-amber-300"} disabled:cursor-not-allowed disabled:opacity-70`}>Ada keluhan</button>
              </div>
              {hasComplaint === true && (
                <div className="mt-3">
                  <Textarea label={missed ? "Catatan keluhan (read-only karena missed)" : "Ceritakan keluhan atau kendalanya"} value={complaintNote} disabled={!editable} rows={3} maxLength={500} placeholder={missed ? "Hari ini sudah expired." : "Contoh: tekstur sulit diterima, makanan ditolak, atau bahan tidak tersedia."} onChange={(event) => { setComplaintNote(event.target.value); markDirty(); }} />
                  {!complaintNote.trim() && editable && <p className="mt-1.5 text-xs font-semibold text-amber-700">Isi catatan singkat agar hari ini dapat diselesaikan.</p>}
                </div>
              )}
              {hasComplaint === null && editable && <p className="mt-2 text-xs font-semibold text-amber-700">Pilih salah satu jawaban sebelum menyelesaikan hari ini.</p>}
            </div>

            {allActionsDone && !reflectionReady && !missed && !completed && <div className="mt-3"><Alert variant="warning" title="Satu langkah lagi">Checklist sudah lengkap. Jawab pertanyaan keluhan agar hari dapat diselesaikan.</Alert></div>}
            {error && <div className="mt-4"><Alert variant="error">{error}</Alert></div>}

            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
              <div className="text-xs text-muted">{reflectionReady ? "Refleksi siap disimpan." : "Refleksi belum lengkap."}</div>
              {missed ? (
                <Button variant="secondary" disabled><X size={16} /> Expired · Read Only</Button>
              ) : (
                <Button onClick={() => void save()} isLoading={saveState === "SAVING"} loadingLabel="Saving..." disabled={!editable || saveState === "IDLE" || saveState === "SAVED" || saveState === "SAVING"}><Save size={16} />{saveButtonLabel}</Button>
              )}
            </div>
          </section>

          <div className="grid gap-4 xl:hidden md:grid-cols-2">
            <section className="rounded-2xl border border-line bg-white p-5">
              <p className="eyebrow">Your Goal</p>
              <h2 className="mt-2 text-lg font-semibold">{primaryGoal?.title ?? "Goal program"}</h2>
              {primaryGoal && <><p className="mt-2 text-sm text-secondary">{primaryGoal.actual} / {primaryGoal.target} {primaryGoal.unit}</p><div className="mt-3"><ProgressBar value={primaryGoal.progress_percentage} label={`${formatPercent(primaryGoal.progress_percentage)}% goal achievement`} /></div></>}
            </section>
            <section className="rounded-2xl border border-line bg-white p-5">
              <div className="flex items-center justify-between"><p className="eyebrow">Program Progress</p><span className="font-black">{formatPercent(program.progress_percent)}%</span></div>
              <p className="mt-2 text-sm text-secondary">{program.days_completed} / {program.duration_days} hari · {program.missed_days} missed</p>
              <div className="mt-3"><ProgressBar value={program.progress_percent} label={`${formatPercent(program.progress_percent)}% program progress`} /></div>
            </section>
          </div>

          {completed && (
            <section className="rounded-2xl border border-primary/15 bg-primary-light p-5 sm:p-6">
              <p className="eyebrow">Day {day.day_number} complete ✓</p>
              <h2 className="mt-2 text-xl font-semibold">Nice work. Today&apos;s guidance has been completed.</h2>
              {nextDay?.day.status === "LOCKED" ? (
                <p className="mt-3 text-sm text-secondary">Panduan berikutnya tersedia dalam <ProgramCountdown seconds={nextDay.day.remaining_seconds} syncElapsedSeconds={shellElapsedSeconds} onExpire={() => void load()} className="font-semibold text-primary-dark" /> · {new Date(nextDay.day.unlock_at).toLocaleString("id-ID")}</p>
              ) : nextDay ? (
                <p className="mt-3 text-sm text-secondary">Day {dayNumber + 1} sudah tersedia. Buka dari Program Overview ketika kamu siap.</p>
              ) : null}
              <Link href={`/nutrition/program/${programId}`} className="mt-4 inline-flex min-h-11 items-center rounded-full bg-text px-5 text-sm font-semibold text-white">View Program <ArrowRight size={15} className="ml-2" /></Link>
            </section>
          )}

          {missed && <Alert variant="warning" title="Missed · hari ini sudah expired">Guidance tetap dapat direview, tetapi checklist, kelompok pangan, dan catatan dikunci.</Alert>}

          {safetyNotes.length > 0 && (
            <section className="rounded-2xl border border-amber-200 bg-amber-50/60 p-5 xl:hidden">
              <div className="flex items-center gap-2 text-amber-700"><Lightbulb size={16} /><p className="text-[10px] font-black uppercase tracking-[.11em]">Safety note</p></div>
              <p className="mt-2 text-xs leading-6 text-secondary">{safetyNotes.join(" ")}</p>
            </section>
          )}

          {day.reference_notes.length > 0 && (
            <details className="rounded-2xl border border-line bg-white">
              <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between gap-4 px-5 text-sm font-semibold text-text sm:px-6">
                <span>View references <span className="ml-2 text-xs font-normal text-muted">{day.reference_notes.length} sumber</span></span>
                <ChevronDown size={17} className="text-muted" />
              </summary>
              <ul className="grid gap-3 border-t border-line px-5 py-5 sm:px-6 lg:grid-cols-2">
                {day.reference_notes.map((item, index) => <li key={`${item}-${index}`} className="flex gap-3 text-sm leading-6 text-secondary"><span className="font-black text-primary-dark">0{index + 1}</span>{item}</li>)}
              </ul>
            </details>
          )}
        </main>

        {!shell && <aside className="hidden xl:block">
          <div className="sticky top-20 space-y-3">
            <section className={`rounded-2xl border p-4 shadow-[0_10px_35px_rgba(21,67,55,.04)] ${missed ? "border-amber-200 bg-amber-50/70" : "border-line bg-white"}`}>
              <p className="text-[10px] font-black uppercase tracking-[.11em] text-muted">Today status</p>
              <div className="mt-2 flex items-end justify-between gap-3"><p className="text-2xl font-semibold">{doneCount}/{day.checklist.length}</p><span className="text-xs font-bold text-muted">actions</span></div>
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-primary transition-[width] duration-300 motion-reduce:transition-none" style={{ width: `${day.checklist.length ? doneCount / day.checklist.length * 100 : 0}%` }} /></div>
              <p className="mt-3 text-xs font-semibold text-secondary">Food groups {selectedFoodGroupCount}/{interactiveFoodGroups.length} · {hasComplaint === null ? "refleksi belum dijawab" : hasComplaint ? "ada keluhan" : "tidak ada keluhan"}</p>
            </section>

            <section className="rounded-2xl border border-line bg-white p-4">
              <p className="text-[10px] font-black uppercase tracking-[.11em] text-muted">Goal</p>
              <p className="mt-2 text-sm font-semibold leading-5">{primaryGoal?.title ?? "Goal program"}</p>
              {primaryGoal && <><div className="mt-3 flex items-baseline justify-between"><span className="text-lg font-black">{primaryGoal.actual}/{primaryGoal.target}</span><span className="text-xs text-muted">{formatPercent(primaryGoal.progress_percentage)}%</span></div><div className="mt-2"><ProgressBar value={primaryGoal.progress_percentage} label={`${formatPercent(primaryGoal.progress_percentage)}% goal achievement`} /></div><p className="mt-2 text-[11px] text-muted">Remaining {primaryGoal.remaining_gap} {primaryGoal.unit}</p></>}
            </section>

            <section className="rounded-2xl border border-line bg-white p-4">
              <div className="flex items-center justify-between gap-2"><p className="text-[10px] font-black uppercase tracking-[.11em] text-muted">Program progress</p><span className="text-sm font-black">{formatPercent(program.progress_percent)}%</span></div>
              <p className="mt-2 text-sm font-semibold">{program.days_completed} / {program.duration_days} hari</p>
              <div className="mt-2"><ProgressBar value={program.progress_percent} label={`${formatPercent(program.progress_percent)}% program progress`} /></div>
              <div className="mt-3 flex gap-3 text-[11px] text-muted"><span>{program.missed_days} missed</span><span>{programRemaining} tersisa</span></div>
            </section>

            {nextScheduledDay?.status === "LOCKED" && (
              <section className="rounded-2xl border border-line bg-white p-4">
                <div className="flex items-center gap-2 text-primary-dark"><Clock3 size={15} /><p className="text-[10px] font-black uppercase tracking-[.11em]">Next unlock</p></div>
                <p className="mt-2 text-sm font-semibold">Day {nextScheduledDay.day_number}</p>
                <p className="mt-1 text-lg font-black text-primary-dark"><ProgramCountdown seconds={nextScheduledDay.remaining_seconds} syncElapsedSeconds={shellElapsedSeconds} onExpire={() => void load()} /></p>
              </section>
            )}

            {safetyNotes.length > 0 && (
              <section className="rounded-2xl border border-amber-200 bg-amber-50/60 p-4">
                <div className="flex items-center gap-2 text-amber-700"><Lightbulb size={15} /><p className="text-[10px] font-black uppercase tracking-[.11em]">Safety note</p></div>
                <p className="mt-2 text-[11px] leading-5 text-secondary">{safetyNotes.join(" ")}</p>
              </section>
            )}
          </div>
        </aside>}
      </div>

      {!shell && <NutritionMobileProgramNav programId={programId} currentDay={detail.current_day} active="today" />}

      <AuthGate
        open={authOpen}
        onClose={() => setAuthOpen(false)}
        contextLabel="Masuk kembali untuk menyimpan progress hari ini"
        onAuthenticated={async () => {
          setAuthOpen(false);
          if (saveState === "DIRTY") await save();
          else await load();
        }}
      />

      {recipeOpen && (
        <div className="fixed inset-0 z-[95] flex items-end justify-center bg-text/45 p-0 backdrop-blur-sm sm:items-center sm:p-5" role="presentation">
          <section role="dialog" aria-modal="true" aria-labelledby="meal-detail-title" className="max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-t-2xl bg-white p-6 shadow-2xl sm:rounded-2xl sm:p-8">
            <div className="flex items-start justify-between gap-4">
              <div><p className="eyebrow">Detail menu</p><h2 id="meal-detail-title" className="mt-2 text-3xl font-semibold tracking-[-0.04em]">{text(mealDetails.example, "Menu hari ini")}</h2></div>
              <button type="button" onClick={() => setRecipeOpen(false)} className="flex h-11 w-11 items-center justify-center rounded-full border border-line" aria-label="Tutup detail menu"><X size={18} /></button>
            </div>
            <div className="mt-6"><MealIllustration stage={program.stage} title={text(mealDetails.example, "Menu hari ini")} groups={recommendedGroups} /></div>
            <div className="mt-6 grid gap-5 sm:grid-cols-2">
              <div><p className="text-xs font-black uppercase tracking-[.1em] text-muted">Food groups relevan</p><div className="mt-3 space-y-2">{interactiveFoodGroups.map((group) => { const index = FOOD_GROUP_ORDER.indexOf(group); return <FoodGroupCard key={group} group={group} compact completed={foodGroupChecks[index] ?? false} recommended={recommendedGroups.includes(group)} />; })}</div></div>
              <div><p className="text-xs font-black uppercase tracking-[.1em] text-muted">Preparation guidance</p><p className="mt-3 text-sm leading-7 text-secondary">{text(mealDetails.preparation, "Preparation detail belum tersedia dari engine.")}</p><p className="mt-5 text-xs font-black uppercase tracking-[.1em] text-muted">Alternative / restriction</p><p className="mt-2 text-sm leading-7 text-secondary">{text(mealDetails.substitutions, "Gunakan alternatif dari kelompok pangan setara sesuai toleransi.")}</p></div>
            </div>
            <div className="mt-7 rounded-xl bg-background p-5"><p className="text-xs font-black uppercase tracking-[.1em] text-primary-dark">Tentang detail ini</p><p className="mt-2 text-sm leading-6 text-secondary">SEHATIN hanya menampilkan preparation, food groups, alternatives, dan safety notes yang tersedia dari Nutrition Engine. Kuantitas bahan atau langkah resep yang tidak tersedia tidak dibuat-buat.</p></div>
          </section>
        </div>
      )}
    </div>
  );
}
