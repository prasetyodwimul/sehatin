"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { Clock3, MoreHorizontal, ShieldAlert } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { NutritionDayProgressBar } from "@/components/nutrition-program-ui";
import { Alert, Button } from "@/components/ui";
import { ViewportModal } from "@/components/viewport-modal";
import { ApiError } from "@/lib/api";
import { clearNutritionSession, elderlyConditionLabel, nutritionAssessmentPath, type ElderlyCondition, type NutritionStage } from "@/lib/nutrition";
import { cancelNutritionProgram, getNutritionProgram, resumeNutritionProgram, type ProgramDetail } from "@/lib/nutrition-program";

export type ProgramSection = "today" | "progress" | "history";

type ProgramShellContextValue = {
  program: ProgramDetail;
  loading: boolean;
  readOnly: boolean;
  refreshProgram: () => Promise<void>;
  syncProgram: (program: ProgramDetail) => void;
  setProgram: React.Dispatch<React.SetStateAction<ProgramDetail | null>>;
  signedOutSnapshot: boolean;
  elapsedSeconds: number;
};

const ProgramShellContext = createContext<ProgramShellContextValue | null>(null);

export function useNutritionProgramShell() {
  const value = useContext(ProgramShellContext);
  if (!value) throw new Error("useNutritionProgramShell must be used inside NutritionProgramShell");
  return value;
}

export function useNutritionProgramShellOptional() {
  return useContext(ProgramShellContext);
}

export function formatProgramRemaining(totalSeconds: number) {
  const seconds = Math.max(0, Math.ceil(totalSeconds));
  if (seconds <= 0) return "Memperbarui…";
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  if (days > 0) return `${days}d ${hours}h ${minutes}m`;
  if (hours > 0) return `${hours}h ${minutes}m ${secs}s`;
  return `${minutes}m ${secs}s`;
}

function stageLabel(stage: string) {
  if (stage === "mpasi") return "Program MPASI";
  if (stage === "toddler") return "Program Toddler";
  return "Lansia Guided Program";
}

function programStatusLabel(status: string) {
  if (status === "ACTIVE") return "Sedang berjalan";
  if (status === "PAUSED") return "Dijeda";
  if (status === "SAFETY_HOLD") return "Dihentikan sementara";
  if (status === "COMPLETED") return "Selesai";
  if (status === "CANCELLED") return "Dibatalkan";
  if (status === "EXTENDED") return "Dilanjutkan";
  return status.replaceAll("_", " ");
}

function activeSection(pathname: string): ProgramSection {
  if (pathname.includes("/progress")) return "progress";
  if (pathname.includes("/history") || pathname.includes("/result")) return "history";
  return "today";
}

export function NutritionProgramShell({ programId, children, initialProgram, active }: { programId: string; children: React.ReactNode; initialProgram?: ProgramDetail; active?: ProgramSection }) {
  const pathname = usePathname();
  const router = useRouter();
  const { status } = useAuth();
  const [program, setProgram] = useState<ProgramDetail | null>(initialProgram ?? null);
  const [loading, setLoading] = useState(!initialProgram);
  const [error, setError] = useState("");
  const [cancelOpen, setCancelOpen] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [countdownNowMs, setCountdownNowMs] = useState(() => Date.now());
  const [safetyBusy, setSafetyBusy] = useState(false);
  const [safetyError, setSafetyError] = useState("");
  const [resumeOpen, setResumeOpen] = useState(false);
  const [resumeBusy, setResumeBusy] = useState(false);
  const [resumeError, setResumeError] = useState("");
  const [resumeNotice, setResumeNotice] = useState("");
  const [pauseNotifierOpen, setPauseNotifierOpen] = useState(false);
  const [safetyNotifierOpen, setSafetyNotifierOpen] = useState(false);
  const [lockedDayNotice, setLockedDayNotice] = useState<string | null>(null);
  const expiredDayRef = useRef<string | null>(null);
  const safetyPanelRef = useRef<HTMLElement | null>(null);
  const previousProgramStatusRef = useRef<string | null>(initialProgram?.status ?? null);

  const refreshProgram = useCallback(async () => {
    if (status !== "authenticated") return;
    try {
      setError("");
      setProgram(await getNutritionProgram(programId));
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) return;
      setError(err instanceof Error ? err.message : "Program belum dapat dimuat ulang.");
    }
  }, [programId, status]);

  useEffect(() => {
    if (status === "loading") return;
    if (status === "unauthenticated") {
      setProgram(null);
      setLoading(false);
      return;
    }
    if (initialProgram) {
      setLoading(false);
      return;
    }
    let mounted = true;
    setLoading(true);
    getNutritionProgram(programId)
      .then((value) => {
        if (!mounted) return;
        setProgram(value);
        setError("");
      })
      .catch((err) => {
        if (!mounted) return;
        setError(err instanceof Error ? err.message : "Program belum dapat dimuat.");
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => { mounted = false; };
  }, [initialProgram, programId, status]);

  useEffect(() => {
    if (status !== "unauthenticated") return;
    router.replace("/");
    router.refresh();
  }, [router, status]);

  const section = active ?? activeSection(pathname);
  const signedOutSnapshot = false;
  const readOnly = false;
  const syncProgram = useCallback((fresh: ProgramDetail) => setProgram(fresh), []);
  const nextLocked = useMemo(() => {
    if (!program) return null;
    return program.days.filter((day) => day.status === "LOCKED").sort((a, b) => a.day_number - b.day_number)[0] ?? null;
  }, [program]);
  const safetyHold = program?.status === "SAFETY_HOLD";
  const paused = program?.status === "PAUSED";

  // The shell persists across nested day routes. Clear a notice from the
  // previously selected locked day so Day 8 never remains visible after the
  // user navigates to Day 9, Day 10, and so on.
  useEffect(() => {
    setLockedDayNotice(null);
  }, [pathname]);

  useEffect(() => {
    const nextStatus = program?.status ?? null;
    const previousStatus = previousProgramStatusRef.current;
    previousProgramStatusRef.current = nextStatus;

    // Show a one-time notifier only for a real in-session transition into PAUSED.
    // Reloading an already-paused program keeps the persistent banner without
    // repeatedly interrupting the user with the same modal.
    if (nextStatus === "PAUSED" && previousStatus && previousStatus !== "PAUSED") {
      setPauseNotifierOpen(true);
    }

    if (nextStatus !== "SAFETY_HOLD" || previousStatus === "SAFETY_HOLD") return;
    setPauseNotifierOpen(false);
    if (previousStatus && previousStatus !== "SAFETY_HOLD") setSafetyNotifierOpen(true);
    const timer = window.setTimeout(() => safetyPanelRef.current?.scrollIntoView?.({ behavior: "smooth", block: "start" }), 100);
    return () => window.clearTimeout(timer);
  }, [program?.status]);

  const nextLockedId = nextLocked?.id ?? null;
  const nextLockedRemaining = nextLocked?.remaining_seconds ?? 0;
  const currentScheduledDay = useMemo(() => {
    if (!program) return null;
    return program.days.find((day) => day.day_number === program.current_day && ["AVAILABLE", "IN_PROGRESS"].includes(day.status)) ?? null;
  }, [program]);
  const currentCloseId = currentScheduledDay?.id ?? null;
  const countdownTargetId = currentCloseId ?? nextLockedId;
  const countdownTargetAt = currentScheduledDay?.close_at ?? nextLocked?.unlock_at ?? null;
  const countdownRemainingSeconds = countdownTargetAt
    ? Math.max(0, Math.ceil((new Date(countdownTargetAt).getTime() - countdownNowMs) / 1000))
    : 0;

  useEffect(() => {
    setElapsedSeconds(0);
    setCountdownNowMs(Date.now());
    expiredDayRef.current = null;
    if (status !== "authenticated" || paused || safetyHold || !countdownTargetId || !countdownTargetAt) return;

    // Use the authoritative UTC timestamp supplied by the backend rather than
    // subtracting a server-provided snapshot. This makes the visible timer a
    // true wall-clock countdown that updates every second without requiring a
    // page refresh, while the backend remains the source of truth at expiry.
    const targetMs = new Date(countdownTargetAt).getTime();
    let interval: number | undefined;
    let refreshTimer: number | undefined;

    const refreshAtBoundary = () => {
      if (expiredDayRef.current === countdownTargetId) return;
      expiredDayRef.current = countdownTargetId;
      void refreshProgram();
    };

    const tick = () => {
      const now = Date.now();
      setCountdownNowMs(now);
      const remaining = targetMs - now;
      if (remaining <= 0) {
        if (interval !== undefined) window.clearInterval(interval);
        refreshTimer = window.setTimeout(refreshAtBoundary, 0);
      }
    };

    tick();
    interval = window.setInterval(tick, 1000);

    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        setCountdownNowMs(Date.now());
        void refreshProgram();
      }
    };
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      if (interval !== undefined) window.clearInterval(interval);
      if (refreshTimer !== undefined) window.clearTimeout(refreshTimer);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [countdownTargetAt, countdownTargetId, paused, refreshProgram, safetyHold, status]);

  async function restartAfterSafetyHold() {
    if (!program || status !== "authenticated" || safetyBusy) return;
    setSafetyBusy(true);
    setSafetyError("");
    try {
      await cancelNutritionProgram(program.id);
      const stage = program.stage as NutritionStage;
      clearNutritionSession(stage);
      router.push(nutritionAssessmentPath(stage));
      router.refresh();
    } catch (err) {
      setSafetyError(err instanceof Error ? err.message : "Asesmen ulang belum dapat disiapkan.");
    } finally {
      setSafetyBusy(false);
    }
  }

  async function handleResume(recoveryStatus: "improved" | "still_unwell") {
    if (!program || status !== "authenticated" || resumeBusy) return;
    setResumeBusy(true);
    setResumeError("");
    setResumeNotice("");
    try {
      const summary = await resumeNutritionProgram(program.id, recoveryStatus);
      if (summary.status === "PAUSED") {
        setResumeNotice("Program tetap dijeda. Progress yang sudah dilakukan tetap tersimpan.");
        setResumeOpen(false);
        await refreshProgram();
        return;
      }
      const fresh = await getNutritionProgram(program.id);
      setProgram(fresh);
      setResumeOpen(false);
      router.push(`/nutrition/program/${program.id}/day/${fresh.current_day}`);
      router.refresh();
    } catch (err) {
      setResumeError(err instanceof Error ? err.message : "Program belum dapat dilanjutkan.");
    } finally {
      setResumeBusy(false);
    }
  }

  async function confirmCancel() {
    if (!program || status !== "authenticated") return;
    setCancelling(true);
    setError("");
    try {
      const updated = await cancelNutritionProgram(program.id);
      setProgram((current) => current ? { ...current, ...updated, status: "CANCELLED" } : current);
      setCancelOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Program belum dapat dibatalkan.");
    } finally {
      setCancelling(false);
    }
  }

  if (status === "loading" || loading) {
    return <div className="mx-auto w-full max-w-[1180px] px-4 py-8"><div className="min-h-[620px] animate-pulse rounded-[28px] border border-line bg-white" aria-label="Memuat program nutrisi" /></div>;
  }

  if (status === "unauthenticated") {
    return <div className="mx-auto w-full max-w-3xl px-4 py-10" role="status" aria-live="polite">Mengalihkan ke beranda…</div>;
  }

  if (!program) {
    return <div className="mx-auto w-full max-w-3xl px-4 py-10"><section className="rounded-[28px] border border-line bg-white p-8"><p className="eyebrow">Guided Nutrition Program</p><h1 className="mt-3 text-3xl font-semibold tracking-[-.04em]">Program belum dapat dibuka.</h1><p className="mt-4 text-sm leading-7 text-secondary">Data program pribadi hanya diminta dari server ketika sesi terautentikasi.</p>{error ? <div className="mt-5"><Alert variant="error">{error}</Alert></div> : null}</section></div>;
  }

  const canCancel = status === "authenticated" && program.status === "ACTIVE" && !program.cancelled_at && !program.completed_at;
  const elderlyConditions = program.stage === "elderly" && Boolean(program.assessment_snapshot?.has_condition)
    ? ((program.assessment_snapshot?.conditions as ElderlyCondition[] | undefined) ?? []).map((item) => elderlyConditionLabel(item, String(program.assessment_snapshot?.other_condition ?? "")))
    : [];

  return <ProgramShellContext.Provider value={{ program, loading, readOnly, refreshProgram, syncProgram, setProgram, signedOutSnapshot, elapsedSeconds }}>
    <div className="mx-auto w-full max-w-[1180px] px-4 pb-24 pt-5 sm:px-5 lg:px-6 lg:pb-16">
      {error ? <div className="mb-4"><Alert variant="error">{error}</Alert></div> : null}

      <header className="min-w-0 rounded-[32px] border border-line bg-white/80 px-5 py-5 shadow-[0_14px_45px_rgba(16,32,29,.05)] backdrop-blur sm:px-6 sm:py-6">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="min-w-0">
            <p className="eyebrow">{program.stage === "elderly" ? `${stageLabel(program.stage)} · Cycle ${program.cycle_number}` : `${stageLabel(program.stage)} · ${program.duration_days} hari${program.cycle_number > 1 ? ` · Periode ${program.cycle_number}` : ""}`}</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-[-.04em] sm:text-4xl">{program.title}</h1>
            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-secondary">
              <span className="font-semibold text-text">Hari {program.current_day} dari {program.duration_days}</span>
              <span>{program.stage === "elderly" ? program.status.replaceAll("_", " ") : programStatusLabel(program.status)}</span>
              <span>{program.days_completed} selesai · {program.missed_days} terlewat</span>
            </div>
            {elderlyConditions.length ? <div className="mt-3 flex flex-wrap items-center gap-2"><span className="text-[10px] font-black uppercase tracking-[.1em] text-muted">Konteks kesehatan</span>{elderlyConditions.map((item) => <span key={item} className="rounded-full border border-line bg-background px-2.5 py-1 text-xs font-semibold text-secondary">{item}</span>)}</div> : null}
          </div>
          <div className="flex items-center gap-3">
            {safetyHold ? <div className="hidden border-l-2 border-red-300 pl-4 text-right sm:block"><p className="text-[10px] font-black uppercase tracking-[.11em] text-red-700">Safety hold</p><p className="mt-1 text-sm font-semibold text-red-900">Program dihentikan</p></div> : paused ? <div className="hidden border-l-2 border-amber-300 pl-4 text-right sm:block"><p className="text-[10px] font-black uppercase tracking-[.11em] text-amber-700">Program dijeda</p><p className="mt-1 text-sm font-semibold text-amber-900">Progress tetap tersimpan</p></div> : nextLocked ? <div className="hidden border-l border-line pl-4 text-right sm:block"><p className="text-[10px] font-black uppercase tracking-[.11em] text-muted">Panduan berikutnya</p><div className="mt-1 flex items-center justify-end gap-2 text-sm font-semibold text-primary-dark"><Clock3 size={15}/><span aria-live="polite">{formatProgramRemaining(countdownRemainingSeconds)}</span></div></div> : null}
            {canCancel ? <button type="button" aria-label="Aksi program" onClick={() => setCancelOpen(true)} className="flex h-11 w-11 items-center justify-center rounded-full border border-line bg-white"><MoreHorizontal size={18}/></button> : null}
          </div>
        </div>

        <div className="mt-5 border-t border-line pt-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs font-black uppercase tracking-[.11em] text-muted">Perjalanan Hari 1–{program.duration_days}</p>
            <nav aria-label="Akses sekunder program" className="flex items-center gap-4 text-xs font-semibold">
              <Link href={`/nutrition/program/${program.id}`} aria-current={section === "today" ? "page" : undefined} className={section === "today" ? "text-primary-dark" : "text-secondary"}>Hari Ini</Link>
              <Link href={`/nutrition/program/${program.id}/progress`} aria-current={section === "progress" ? "page" : undefined} className={section === "progress" ? "text-primary-dark" : "text-secondary"}>Progres</Link>
              <Link href={`/nutrition/program/${program.id}/history`} aria-current={section === "history" ? "page" : undefined} className={section === "history" ? "text-primary-dark" : "text-secondary"}>Riwayat</Link>
            </nav>
          </div>
          <div className="mt-4">
            <NutritionDayProgressBar
              programId={program.id}
              days={program.days}
              currentDay={program.current_day}
              syncElapsedSeconds={elapsedSeconds}
              onExpire={() => { void refreshProgram(); }}
              onLockedDay={(day) => setLockedDayNotice(day.remaining_seconds > 0 ? `Hari ${day.day_number} belum terbuka. Tersedia ${new Date(day.unlock_at).toLocaleString("id-ID")}.` : `Hari ${day.day_number} belum terbuka.`)}
            />
          </div>
          {lockedDayNotice ? <div className="mt-3" role="status" aria-live="polite"><Alert variant="info" title="Hari yang dipilih belum terbuka">{lockedDayNotice}</Alert></div> : null}
        </div>
      </header>

      {paused ? <section className="mt-5 min-w-0 rounded-[28px] border border-amber-300 bg-amber-50 p-5 sm:p-6" aria-labelledby="program-paused-title">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="max-w-3xl"><p className="text-xs font-black uppercase tracking-[.12em] text-amber-800">PAUSED</p><h2 id="program-paused-title" className="mt-2 text-2xl font-semibold tracking-[-.03em] text-text">Program sedang dijeda</h2><p className="mt-3 text-sm leading-7 text-secondary">Progress yang sudah dilakukan tetap tersimpan. Hari berikutnya belum dibuka sampai program dilanjutkan dan hari ini selesai.</p>{resumeNotice ? <p className="mt-3 text-sm font-semibold text-amber-900" role="status" aria-live="polite">{resumeNotice}</p> : null}</div>
          <Button variant="secondary" onClick={() => { setResumeError(""); setResumeOpen(true); }}>Lanjutkan Program</Button>
        </div>
      </section> : null}

      {safetyHold ? <section ref={safetyPanelRef} className="scroll-mt-24 mt-5 min-w-0 rounded-[28px] border border-red-300 bg-red-50 p-5 sm:p-6" aria-labelledby="safety-hold-review-title" role="alert">
        <div className="flex items-start gap-3"><span className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-100 text-red-700"><ShieldAlert size={20}/></span><div className="min-w-0"><p className="text-xs font-black uppercase tracking-[.12em] text-red-700">{program.stage === "elderly" ? "Safety hold" : "Tanda bahaya terdeteksi"}</p><h2 id="safety-hold-review-title" className="mt-2 text-2xl font-semibold tracking-[-.03em] text-text">{program.stage === "elderly" ? "Panduan dihentikan sementara." : "Segera bawa anak ke IGD atau rumah sakit."}</h2><p className="mt-3 max-w-4xl text-sm leading-7 text-secondary">{program.stage === "elderly" ? "Data kondisi saat ini memerlukan perhatian lebih lanjut sebelum program dapat dilanjutkan. Progress terakhir tetap tersimpan." : "Program dihentikan dan tidak akan melanjutkan adaptasi otomatis. Setelah kondisi anak sudah dievaluasi, isi asesmen SEHATIN dari awal sebelum memulai program baru."}</p><p className="mt-3 max-w-4xl text-xs leading-6 text-red-800">SEHATIN tidak dapat memastikan diagnosis atau menggantikan pemeriksaan tenaga kesehatan.</p></div></div>
        {safetyError ? <div className="mt-5"><Alert variant="error">{safetyError}</Alert></div> : null}
        <div className="mt-6 border-t border-red-200 pt-5"><p className="text-sm font-semibold text-text">Langkah berikutnya</p><p className="mt-1 max-w-3xl text-sm leading-6 text-secondary">Cycle ini akan disimpan sebagai riwayat dan asesmen harus diulang.</p><Button className="mt-4" onClick={() => void restartAfterSafetyHold()} isLoading={safetyBusy} loadingLabel="Menyiapkan asesmen ulang...">Ulangi asesmen</Button></div>
      </section> : null}

      <main className="mx-auto mt-7 w-full max-w-[980px]">{children}</main>

      {safetyNotifierOpen ? <ViewportModal onClose={() => setSafetyNotifierOpen(false)} labelledBy="program-safety-notifier-title"><div className="text-center"><span className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-red-100 text-red-700"><ShieldAlert size={28}/></span><p className="eyebrow mt-5 text-red-700">Tanda bahaya terdeteksi</p><h2 id="program-safety-notifier-title" className="mt-2 text-3xl font-semibold tracking-[-.035em]">{program.stage === "elderly" ? "Segera bawa lansia ke IGD atau rumah sakit." : "Segera bawa anak ke IGD atau rumah sakit."}</h2><p className="mx-auto mt-4 max-w-md text-sm leading-7 text-secondary">Input yang baru disimpan memenuhi aturan tanda bahaya dan program langsung masuk Safety Hold. Jangan lanjutkan Guided Nutrition sampai kondisi sudah dievaluasi.</p><div className="mx-auto mt-5 max-w-md rounded-2xl border border-red-200 bg-red-50 p-4 text-left text-sm leading-6 text-red-900">Jika kondisi sedang gawat, cari pertolongan darurat setempat. SEHATIN tidak dapat memastikan diagnosis atau menggantikan pemeriksaan langsung.</div><div className="mt-7"><Button autoFocus onClick={() => setSafetyNotifierOpen(false)}>Mengerti</Button></div></div></ViewportModal> : null}

      {pauseNotifierOpen ? <ViewportModal onClose={() => setPauseNotifierOpen(false)} labelledBy="program-paused-notifier-title"><p className="eyebrow text-amber-800">Program dijeda</p><h2 id="program-paused-notifier-title" className="mt-2 text-2xl font-semibold tracking-[-.03em]">Program dijeda sementara</h2><p className="mt-3 text-sm leading-7 text-secondary">Kondisi hari ini membuat program perlu berhenti sementara. Progress yang sudah dicatat tetap tersimpan dan hari berikutnya belum dibuka sampai program dilanjutkan.</p><div className="mt-5 border-l-2 border-amber-300 pl-4 text-sm leading-6 text-secondary">Saat kondisi sudah membaik, gunakan tombol <span className="font-semibold text-text">Lanjutkan Program</span> pada status program untuk melanjutkan hari yang sama.</div><div className="mt-6 flex justify-end"><Button onClick={() => setPauseNotifierOpen(false)}>Mengerti</Button></div></ViewportModal> : null}

      {resumeOpen ? <ViewportModal onClose={() => !resumeBusy && setResumeOpen(false)} labelledBy="resume-program-title"><p className="eyebrow">Lanjutkan program</p><h2 id="resume-program-title" className="mt-2 text-2xl font-semibold tracking-[-.03em]">Bagaimana kondisi sekarang?</h2><p className="mt-3 text-sm leading-7 text-secondary">Program akan melanjutkan hari terakhir yang belum selesai. Progress yang sudah dicatat tidak di-reset.</p>{resumeError ? <div className="mt-4"><Alert variant="error">{resumeError}</Alert></div> : null}<div className="mt-6 grid gap-3 sm:grid-cols-2"><Button variant="secondary" disabled={resumeBusy} onClick={() => void handleResume("still_unwell")}>Masih kurang sehat</Button><Button isLoading={resumeBusy} loadingLabel="Memeriksa..." onClick={() => void handleResume("improved")}>Sudah membaik</Button></div></ViewportModal> : null}

      {cancelOpen ? <ViewportModal onClose={() => !cancelling && setCancelOpen(false)} labelledBy="shell-cancel-title"><h2 id="shell-cancel-title" className="text-2xl font-semibold tracking-[-.03em]">Batalkan program nutrisi ini?</h2><p className="mt-3 text-sm leading-7 text-secondary">Progress yang sudah tersimpan tetap berada di riwayat.</p><div className="mt-6 flex flex-wrap justify-end gap-3"><Button variant="secondary" onClick={() => setCancelOpen(false)} disabled={cancelling}>Pertahankan program</Button><Button onClick={() => void confirmCancel()} isLoading={cancelling} loadingLabel="Membatalkan...">Batalkan program</Button></div></ViewportModal> : null}
    </div>
  </ProgramShellContext.Provider>;
}
