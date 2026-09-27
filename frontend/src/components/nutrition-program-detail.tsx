"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { MoreHorizontal, Trash2, Check, LockKeyhole, XCircle } from "lucide-react";
import { AuthGate } from "@/components/auth-gate";
import { useAuth } from "@/components/auth-provider";
import { Alert, Button } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { ViewportModal } from "@/components/viewport-modal";
import { cancelNutritionProgram, deleteCancelledNutritionProgram, getNutritionProgram, pauseNutritionProgram, resumeNutritionProgram, skipNutritionProgramDay, type ProgramDay, type ProgramDetail } from "@/lib/nutrition-program";
import { clearNutritionSession, nutritionAssessmentPath, type NutritionStage } from "@/lib/nutrition";
import { NutritionProgramDailyWorkspace } from "@/components/nutrition-program-daily-workspace";

function stageLabel(stage: string) {
  if (stage === "mpasi") return "Program MPASI";
  if (stage === "toddler") return "Program Toddler";
  return "Program Nutrisi Lansia";
}


function DayJourneyHoverInfo({ title, detail, children }: { title: string; detail: string; children: ReactNode }) {
  const anchorRef = useRef<HTMLSpanElement>(null);
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0 });

  const updatePosition = useCallback(() => {
    if (typeof window === "undefined" || !anchorRef.current) return;
    const rect = anchorRef.current.getBoundingClientRect();
    const width = 220;
    const estimatedHeight = 104;
    const gutter = 10;
    const left = Math.min(Math.max(rect.left + rect.width / 2 - width / 2, 8), Math.max(8, window.innerWidth - width - 8));
    const hasRoomBelow = window.innerHeight - rect.bottom >= estimatedHeight + gutter;
    const top = hasRoomBelow ? rect.bottom + gutter : Math.max(8, rect.top - estimatedHeight - gutter);
    setPosition({ top, left });
  }, []);

  useEffect(() => {
    if (!open) return;
    updatePosition();
    const refresh = () => updatePosition();
    window.addEventListener("resize", refresh);
    window.addEventListener("scroll", refresh, true);
    return () => {
      window.removeEventListener("resize", refresh);
      window.removeEventListener("scroll", refresh, true);
    };
  }, [open, updatePosition]);

  return <span ref={anchorRef} className="flex min-w-0 flex-1" onMouseEnter={() => { setOpen(true); updatePosition(); }} onMouseLeave={() => setOpen(false)} onFocusCapture={() => { setOpen(true); updatePosition(); }} onBlurCapture={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setOpen(false); }}>
    {children}
    {open && typeof document !== "undefined" ? createPortal(
      <span role="tooltip" className="pointer-events-none fixed z-[100] w-[220px] rounded-2xl border border-line bg-white/95 p-3 text-left shadow-[0_18px_50px_rgba(16,32,29,.16)] backdrop-blur" style={{ top: position.top, left: position.left }}>
        <span className="block text-[10px] font-black uppercase tracking-[.1em] text-primary-dark">{title}</span>
        <span className="mt-1 block text-xs leading-5 text-secondary">{detail}</span>
      </span>,
      document.body,
    ) : null}
  </span>;
}
function dayStatusMeta(day: ProgramDay) {
  if (day.status === "COMPLETED") return { label: "Selesai", kind: "complete" as const };
  if (day.status === "MISSED") return { label: "Terlewat", kind: "missed" as const };
  if (day.status === "LOCKED") return { label: "Terkunci", kind: "locked" as const };
  if (day.status === "IN_PROGRESS") return { label: "Sedang berjalan", kind: "today" as const };
  return { label: "Hari ini", kind: "today" as const };
}

export function NutritionProgramDetail({ programId, initialProgram }: { programId: string; initialProgram?: ProgramDetail }) {
  const { status } = useAuth();
  const [program, setProgram] = useState<ProgramDetail | null>(initialProgram ?? null);
  const [loading, setLoading] = useState(!initialProgram);
  const [error, setError] = useState("");
  const [authOpen, setAuthOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setProgram(await getNutritionProgram(programId));
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) setError("Login diperlukan untuk membuka program tersimpan ini.");
      else if (err instanceof ApiError && err.status === 404) setError("Program tidak ditemukan atau tidak dapat diakses oleh akun ini.");
      else setError(err instanceof Error ? err.message : "Program belum dapat dimuat.");
      setProgram(null);
    } finally {
      setLoading(false);
    }
  }, [programId]);

  useEffect(() => {
    if (initialProgram) return;
    if (status === "authenticated") void load();
    if (status === "unauthenticated") {
      setProgram(null);
      setLoading(false);
    }
  }, [initialProgram, load, status]);

  const currentDay = useMemo(() => {
    if (!program) return null;
    return program.days.find((item) => item.day_number === program.current_day && ["AVAILABLE", "IN_PROGRESS"].includes(item.status))
      ?? program.days.find((item) => ["AVAILABLE", "IN_PROGRESS"].includes(item.status))
      ?? program.days.find((item) => item.day_number === program.current_day)
      ?? program.days[0]
      ?? null;
  }, [program]);

  const previousDays = useMemo(() => (program?.days ?? []).filter((day) => day.day_number < (currentDay?.day_number ?? 0) && ["COMPLETED", "MISSED"].includes(day.status)).sort((a, b) => b.day_number - a.day_number), [currentDay?.day_number, program?.days]);
  const active = Boolean(program && program.status === "ACTIVE" && !program.cancelled_at && !program.completed_at);
  const cancelled = Boolean(program && (program.status === "CANCELLED" || program.cancelled_at));
  const completed = Boolean(program && (program.status === "COMPLETED" || program.completed_at));
  const paused = Boolean(program && program.status === "PAUSED");
  const safetyHold = Boolean(program && program.status === "SAFETY_HOLD");
  async function confirmCancel() {
    if (!program) return;
    setBusy(true);
    setError("");
    try {
      const updated = await cancelNutritionProgram(program.id);
      setProgram((current) => current ? { ...current, ...updated, status: "CANCELLED" } : current);
      setCancelOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Program belum dapat dibatalkan.");
    } finally {
      setBusy(false);
    }
  }

  async function deleteProgram() {
    if (!program) return;
    setBusy(true);
    setError("");
    try {
      await deleteCancelledNutritionProgram(program.id);
      window.location.assign("/nutrition/history");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Program belum dapat dihapus.");
      setBusy(false);
    }
  }

  async function pauseProgram() {
    if (!program) return;
    setBusy(true); setError("");
    try { const updated = await pauseNutritionProgram(program.id); setProgram((current) => current ? { ...current, ...updated } : current); setMoreOpen(false); } catch (err) { setError(err instanceof Error ? err.message : "Program belum dapat dijeda."); } finally { setBusy(false); }
  }

  async function resumeProgram() {
    if (!program) return;
    setBusy(true); setError("");
    try { const updated = await resumeNutritionProgram(program.id); setProgram((current) => current ? { ...current, ...updated } : current); } catch (err) { setError(err instanceof Error ? err.message : "Program belum dapat dilanjutkan."); } finally { setBusy(false); }
  }

  async function skipToday() {
    if (!program) return;
    setBusy(true); setError("");
    try { await skipNutritionProgramDay(program.id); await load(); setMoreOpen(false); } catch (err) { setError(err instanceof Error ? err.message : "Hari ini belum dapat dilewati."); } finally { setBusy(false); }
  }

  async function restartAfterSafetyHold() {
    if (!program || busy) return;
    setBusy(true);
    setError("");
    try {
      await cancelNutritionProgram(program.id);
      const stage = program.stage as NutritionStage;
      clearNutritionSession(stage);
      window.location.assign(nutritionAssessmentPath(stage));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Asesmen ulang belum dapat disiapkan.");
    } finally {
      setBusy(false);
    }
  }

  if (status === "loading" || loading) {
    return <div className="mx-auto max-w-6xl animate-pulse py-8" aria-label="Memuat program nutrisi"><div className="h-9 w-48 bg-slate-200" /><div className="mt-5 h-3 w-full bg-slate-100" /><div className="mt-10 h-96 bg-slate-100" /></div>;
  }

  if (status === "unauthenticated") {
    return <>
      <section className="mx-auto max-w-3xl rounded-[28px] border border-line bg-white p-8">
        <p className="eyebrow">Program nutrisi</p>
        <h1 className="mt-3 text-3xl font-semibold">Masuk untuk melanjutkan program.</h1>
        <p className="mt-3 text-sm leading-7 text-secondary">Program, progress, dan riwayat pribadi hanya dapat dibuka setelah sesi terverifikasi.</p>
        <Button className="mt-6" onClick={() => setAuthOpen(true)}>Masuk</Button>
      </section>
      <AuthGate open={authOpen} onClose={() => setAuthOpen(false)} onAuthenticated={async () => { setAuthOpen(false); await load(); }} />
    </>;
  }

  if (!program || !currentDay) {
    return <div className="mx-auto max-w-3xl rounded-[28px] border border-line bg-white p-8"><Alert variant="error" title="Program tidak tersedia">{error || "Program belum dapat dibuka."}</Alert><Link href="/nutrition/program" className="mt-5 inline-flex text-sm font-semibold text-primary-dark">← Kembali ke program</Link></div>;
  }

  return <div className="mx-auto max-w-6xl pb-20">
    <div className="border-b border-line pb-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="eyebrow">{stageLabel(program.stage)}</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-[-0.035em] sm:text-4xl">{program.title}</h1>
          <div className="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <p className="text-lg font-semibold text-text">Hari {currentDay.day_number} dari {program.duration_days}</p>
            <span className="text-sm text-secondary">{program.days_completed} hari selesai</span>
          </div>
        </div>
        {active && <div className="relative">
          <button type="button" aria-label="Aksi program" onClick={() => setMoreOpen((value) => !value)} className="flex h-10 w-10 items-center justify-center rounded-full border border-line bg-white"><MoreHorizontal size={18} /></button>
          {moreOpen && <div className="absolute right-0 top-12 z-20 w-52 rounded-2xl border border-line bg-white p-2 shadow-lg"><button type="button" disabled={busy} className="flex min-h-10 w-full items-center px-3 text-left text-sm font-semibold text-secondary hover:bg-background" onClick={() => void pauseProgram()}>Jeda program</button><button type="button" disabled={busy || currentDay.status === "COMPLETED"} className="flex min-h-10 w-full items-center px-3 text-left text-sm font-semibold text-secondary hover:bg-background" onClick={() => void skipToday()}>Lewati hari ini</button><button type="button" className="flex min-h-10 w-full items-center px-3 text-left text-sm font-semibold text-error hover:bg-red-50" onClick={() => { setMoreOpen(false); setCancelOpen(true); }}>Batalkan program</button></div>}
        </div>}
        {paused && <Button variant="secondary" size="sm" onClick={() => void resumeProgram()} isLoading={busy} loadingLabel="Melanjutkan...">Lanjutkan program</Button>}
        {cancelled && <Button variant="secondary" size="sm" onClick={() => setDeleteOpen(true)}><Trash2 size={15} /> Hapus program</Button>}
      </div>
    </div>

    <section className="mt-6 overflow-visible" aria-label="Perjalanan hari program">
      <div className="overflow-x-auto pb-3 pt-1">
        <div className="min-w-[620px]">
          <div className="flex items-center overflow-visible">
            {program.days.map((day, index) => {
              const meta = dayStatusMeta(day);
              const clickable = day.status !== "LOCKED";
              const detailCopy = day.status === "LOCKED"
                ? (day.remaining_seconds > 0 ? "Belum terbuka. Tunggu countdown hari berjalan selesai." : "Belum terbuka untuk review.")
                : (day.focus || "Panduan hari ini tersedia untuk dibuka.");
              return <div key={day.id} className="flex min-w-0 flex-1 items-center">
                <DayJourneyHoverInfo title={`Hari ${day.day_number} · ${meta.label}`} detail={detailCopy}>
                  <Link
                    href={clickable ? `/nutrition/program/${program.id}/day/${day.day_number}` : "#"}
                    aria-label={`Hari ${day.day_number}: ${meta.label}. ${detailCopy}`}
                    aria-disabled={!clickable}
                    onClick={(event) => {
                      if (!clickable) event.preventDefault();
                    }}
                    className={`group flex min-w-0 flex-1 flex-col items-center gap-2 ${clickable ? "cursor-pointer" : "cursor-default"}`}
                  >
                    <span className={`flex h-9 w-9 items-center justify-center rounded-full border text-xs font-bold ${meta.kind === "complete" ? "border-primary bg-primary text-white" : meta.kind === "today" ? "border-primary bg-primary-light text-primary-dark" : meta.kind === "missed" ? "border-amber-300 bg-amber-50 text-amber-800" : "border-slate-200 bg-slate-50 text-slate-400"}`}>{meta.kind === "complete" ? <Check size={14} /> : meta.kind === "locked" ? <LockKeyhole size={14} /> : meta.kind === "missed" ? <XCircle size={14} /> : day.day_number}</span>
                    <span className={`text-[11px] font-semibold ${day.day_number === currentDay.day_number ? "text-primary-dark" : "text-muted"}`}>H{day.day_number}</span>
                  </Link>
                </DayJourneyHoverInfo>
                {index < program.days.length - 1 && <span className={`h-px flex-1 ${day.day_number < currentDay.day_number ? "bg-primary" : "bg-slate-200"}`} aria-hidden="true" />}
              </div>;
            })}
          </div>
        </div>
      </div>
      <p className="mt-2 text-xs text-muted">Hari yang sudah tersedia dapat dibuka untuk review. Saat di-hover atau difokuskan, info hari tidak lagi terpotong.</p>
    </section>

    {error && <div className="mt-6"><Alert variant="error">{error}</Alert></div>}
    {safetyHold && <section className="mt-6 border-y border-red-200 bg-red-50 px-5 py-6 sm:px-6" aria-labelledby="safety-review-title" role="alert">
      <Alert variant="error" title="Tanda bahaya terdeteksi — segera cari pertolongan medis">Program dihentikan. Segera bawa anak ke IGD atau rumah sakit. Setelah kondisi anak sudah dievaluasi, asesmen SEHATIN harus diulang sebelum memulai program baru.</Alert>
      <div className="mt-6">
        <p className="eyebrow">Safety hold</p>
        <h2 id="safety-review-title" className="mt-2 text-2xl font-semibold">Program tidak dapat dilanjutkan dari goal lama.</h2>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-secondary">Tidak ada pilihan untuk memperkecil atau mengganti goal. Cycle ini akan disimpan sebagai riwayat dan konteks terbaru harus dikumpulkan melalui asesmen ulang.</p>
        <Button className="mt-5" onClick={() => void restartAfterSafetyHold()} isLoading={busy} loadingLabel="Menyiapkan asesmen ulang...">Ulangi asesmen</Button>
      </div>
    </section>}
    {paused && <div className="mt-6"><Alert variant="warning" title="Program dijeda">Timeline program dibekukan selama jeda. Lanjutkan saat kondisi memungkinkan.</Alert></div>}
    {program.latest_decision?.decision === "BLOCK_REVIEW" && <div className="mt-6"><Alert variant="warning" title="Strategi perlu ditinjau">Perkembangan beberapa hari terakhir belum banyak berubah. Buka review untuk mempertimbangkan goal yang sama, goal lebih kecil, atau strategi lain.</Alert><Link href={`/nutrition/program/${program.id}/history`} className="mt-3 inline-flex text-sm font-semibold text-primary-dark">Buka Block Review →</Link></div>}

    <main className="mt-8">
      <NutritionProgramDailyWorkspace program={program} day={currentDay} onProgramRefresh={(fresh) => { setProgram(fresh); setError(""); }} />
    </main>

    {previousDays.length > 0 && <section className="mt-10 border-t border-line pt-7" id="history">
      <button type="button" className="flex w-full items-center justify-between text-left" onClick={() => setHistoryOpen((value) => !value)} aria-expanded={historyOpen}>
        <div><p className="eyebrow">History</p><h2 className="mt-2 text-xl font-semibold">Hari sebelumnya · {previousDays.length}</h2></div>
        <span className="text-sm font-semibold text-primary-dark">{historyOpen ? "Tutup" : "Buka"}</span>
      </button>
      {historyOpen && <div className="mt-4 space-y-2">{previousDays.map((day) => <Link key={day.id} href={`/nutrition/program/${program.id}/day/${day.day_number}`} className="flex min-w-0 items-center justify-between gap-4 rounded-2xl border border-line bg-white px-4 py-4 hover:border-primary/30"><span><span className="block text-xs font-bold uppercase tracking-[.1em] text-muted">Hari {day.day_number}</span><span className="mt-1 block text-sm font-semibold">{day.focus}</span></span><span className="text-xs font-semibold text-secondary">{day.status === "MISSED" ? "Terlewat · Review" : "Selesai · Review"}</span></Link>)}</div>}
    </section>}

    {(completed || cancelled) && <section className="mt-10 border-t border-line pt-7"><p className="eyebrow">Status program</p><h2 className="mt-2 text-xl font-semibold">{completed ? "Program block selesai" : "Program dibatalkan"}</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-secondary">{completed ? "Block selesai tidak otomatis berarti goal tercapai. Buka Final Program Result untuk melihat program completion, goal achievement, pola harian, keputusan adaptasi, dan langkah berikutnya." : "Program tetap tersimpan sebagai riwayat sampai kamu memilih menghapusnya."}</p>{completed && <Link href={`/nutrition/program/${program.id}/result`} className="mt-5 inline-flex min-h-11 items-center rounded-full bg-primary px-5 text-sm font-semibold text-white">Lihat Final Program Result →</Link>}</section>}

    {cancelOpen && <ViewportModal onClose={() => !busy && setCancelOpen(false)} labelledBy="cancel-program-title">
      <h2 id="cancel-program-title" className="text-xl font-semibold">Batalkan program?</h2>
      <p className="mt-3 text-sm leading-6 text-secondary">Program ini akan berhenti dan tidak lagi menjadi program aktif. Progress yang sudah tersimpan tetap berada di riwayat.</p>
      <div className="mt-6 flex flex-wrap justify-end gap-3"><Button variant="secondary" onClick={() => setCancelOpen(false)} disabled={busy}>Kembali</Button><Button onClick={() => void confirmCancel()} isLoading={busy} loadingLabel="Membatalkan...">Batalkan Program</Button></div>
    </ViewportModal>}

    {deleteOpen && <ViewportModal onClose={() => !busy && setDeleteOpen(false)} labelledBy="delete-program-title">
      <h2 id="delete-program-title" className="text-xl font-semibold">Hapus program?</h2>
      <p className="mt-3 text-sm leading-6 text-secondary">Program yang sudah dibatalkan akan dihapus dari riwayat setelah server berhasil memproses penghapusan.</p>
      <div className="mt-6 flex flex-wrap justify-end gap-3"><Button variant="secondary" onClick={() => setDeleteOpen(false)} disabled={busy}>Kembali</Button><Button onClick={() => void deleteProgram()} isLoading={busy} loadingLabel="Menghapus...">Hapus Program</Button></div>
    </ViewportModal>}
  </div>;
}

