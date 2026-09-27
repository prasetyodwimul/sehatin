"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ArrowRight, BarChart3, BookOpenText, CalendarDays, CheckCircle2, ChevronRight, CircleDot, Clock3, History, Home, LockKeyhole, UtensilsCrossed, XCircle } from "lucide-react";
import { ProgramCountdown } from "@/components/program-countdown";
import { FoodGroupIcon, MealIllustration, StageCompanionIllustration, foodGroupsFrom, type FoodGroupKey } from "@/components/nutrition-visuals";
import { ProgressBar } from "@/components/ui";
import { formatPercent, type ProgramDay, type ProgramGoal, type ProgramSummary } from "@/lib/nutrition-program";
import { formatMenuDisplayTitle } from "@/lib/nutrition-menu-presentation";

export function NutritionProgramNav({ programId, currentDay = 1, active }: { programId: string; currentDay?: number; active: "overview" | "today" | "progress" | "history" }) {
  const [selected, setSelected] = useState(active);
  useEffect(() => {
    const syncFromHash = () => {
      if (window.location.hash === "#progress") setSelected("progress");
      else if (window.location.hash === "#overview") setSelected("overview");
      else if (window.location.hash === "#today") setSelected("today");
      else setSelected(active);
    };
    syncFromHash();
    window.addEventListener("hashchange", syncFromHash);
    return () => window.removeEventListener("hashchange", syncFromHash);
  }, [active]);
  const items = [
    { key: "overview", label: "Ringkasan", href: `/nutrition/program/${programId}`, icon: Home },
    { key: "today", label: "Hari Ini", href: `/nutrition/program/${programId}/today`, icon: CalendarDays },
    { key: "progress", label: "Progress", href: `/nutrition/program/${programId}/progress`, icon: BarChart3 },
    { key: "history", label: "Riwayat Program", href: `/nutrition/program/${programId}/history`, icon: History },
  ] as const;
  return <nav aria-label="Navigasi program nutrisi" className="rounded-2xl border border-line bg-white p-3 shadow-[0_12px_40px_rgba(21,67,55,.06)]">
    <Link href="/nutrition/program" className="mb-3 flex min-h-10 items-center gap-2 rounded-xl px-3 text-xs font-semibold text-muted hover:bg-background">← Kembali ke Program</Link>
    <div className="space-y-1">{items.map((item) => { const Icon = item.icon; const isSelected = item.key === selected; return <Link key={item.key} href={item.href} onClick={() => setSelected(item.key)} className={`flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm font-semibold transition-colors ${isSelected ? "bg-primary-light text-primary-dark" : "text-secondary hover:bg-background hover:text-text"}`} aria-current={isSelected ? "page" : undefined}><Icon size={17}/>{item.label}</Link>; })}</div>
  </nav>;
}

export function NutritionMobileProgramNav({ programId, currentDay = 1, active }: { programId: string; currentDay?: number; active: "today" | "progress" | "history" }) {
  const items = [
    { key: "today", label: "Hari Ini", href: `/nutrition/program/${programId}/today`, icon: CalendarDays },
    { key: "progress", label: "Progress", href: `/nutrition/program/${programId}/progress`, icon: BarChart3 },
    { key: "history", label: "Riwayat", href: `/nutrition/program/${programId}/history`, icon: History },
  ] as const;
  return <nav aria-label="Navigasi program seluler" className="fixed inset-x-3 bottom-3 z-40 grid grid-cols-3 rounded-2xl border border-line bg-white/95 p-2 shadow-2xl backdrop-blur lg:hidden">{items.map((item) => { const Icon = item.icon; const isSelected = item.key === active; return <Link key={item.key} href={item.href} className={`flex min-h-12 flex-col items-center justify-center gap-1 rounded-xl text-[11px] font-semibold ${isSelected ? "bg-primary-light text-primary-dark" : "text-muted"}`}><Icon size={17}/>{item.label}</Link>; })}</nav>;
}

export function NutritionProgramHero({ stage, currentDay, durationDays, focus, title, summary }: { stage: string; currentDay: number; durationDays: number; focus: string; title: string; summary: string }) {
  return <section className="overflow-hidden rounded-2xl border border-line bg-[linear-gradient(135deg,#f7fbf9_0%,#f6fbff_48%,#fff9ee_100%)] shadow-[0_20px_60px_rgba(23,68,56,.06)]">
    <div className="grid min-h-[240px] lg:grid-cols-[1.12fr_.88fr]">
      <div className="p-7 md:p-10">
        <div className="flex flex-wrap items-center gap-2 text-xs font-bold uppercase tracking-[0.12em] text-primary-dark"><span className="rounded-full bg-white px-3 py-1.5 shadow-sm">{title}</span><span>Day {currentDay} / {durationDays}</span></div>
        <h1 className="mt-6 text-4xl font-semibold leading-[.97] tracking-[-0.05em] text-text md:text-5xl">Hari ke {currentDay}</h1>
        <h2 className="mt-4 max-w-xl text-2xl font-semibold tracking-[-0.035em] text-text">{focus}</h2>
        <p className="mt-4 max-w-xl text-sm leading-7 text-secondary">{summary}</p>
      </div>
      <div className="p-4 lg:p-6"><StageCompanionIllustration stage={stage} /></div>
    </div>
  </section>;
}


export function NutritionDayProgressBar({
  programId,
  days,
  currentDay,
  onExpire,
  onLockedDay,
  syncElapsedSeconds,
}: {
  programId: string;
  days: ProgramDay[];
  currentDay: number;
  onExpire?: () => void;
  onLockedDay?: (day: ProgramDay) => void;
  syncElapsedSeconds?: number;
}) {
  const currentRef = useRef<HTMLAnchorElement | null>(null);

  useEffect(() => {
    currentRef.current?.scrollIntoView?.({ behavior: "smooth", block: "nearest", inline: "center" });
  }, [currentDay]);

  return (
    <div className="max-w-full overflow-x-auto overscroll-x-contain pb-2 touch-pan-x" aria-label="Progress hari program" data-testid="day-timeline-scroll">
      <div className="min-w-[760px] px-1 sm:min-w-[840px]">
        <div className="relative flex items-start justify-between gap-2">
          <div className="pointer-events-none absolute left-5 right-5 top-5 h-px bg-line" aria-hidden="true" />
          {days.map((day) => {
            const current = day.day_number === currentDay;
            const reviewable = day.day_number < currentDay && ["COMPLETED", "MISSED"].includes(day.status);
            const locked = day.status === "LOCKED";
            const base = current
              ? "border-primary bg-primary text-white shadow-sm"
              : day.status === "COMPLETED"
                ? "border-emerald-300 bg-emerald-50 text-emerald-700"
                : day.status === "MISSED"
                  ? "border-amber-300 bg-amber-50 text-amber-700"
                  : locked
                    ? "border-slate-200 bg-slate-50 text-slate-400"
                    : "border-line bg-white text-muted";
            const content = (
              <span className="relative z-10 flex min-w-[46px] flex-col items-center gap-2">
                <span className={`flex h-10 w-10 items-center justify-center rounded-full border text-xs font-black ${base}`}>
                  {day.status === "COMPLETED" ? <CheckCircle2 size={17} /> : day.status === "MISSED" ? <XCircle size={17} /> : locked ? <LockKeyhole size={16} /> : <span>{day.day_number}</span>}
                </span>
                <span className={`text-[10px] font-black uppercase tracking-[.08em] ${current ? "text-primary-dark" : "text-muted"}`}>Hari {day.day_number}</span>
                {locked && <span className="max-w-[72px] truncate text-[9px] font-semibold text-muted">{day.remaining_seconds > 0 ? <ProgramCountdown seconds={day.remaining_seconds} syncElapsedSeconds={syncElapsedSeconds} onExpire={onExpire} /> : "Belum terbuka"}</span>}
              </span>
            );
            if (current) {
              return <Link ref={currentRef} key={day.id} href={`/nutrition/program/${programId}`} aria-current="step" aria-label={`Hari ini, Hari ${day.day_number}`} className="relative flex shrink-0 items-start justify-center focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">{content}</Link>;
            }
            if (reviewable) {
              return <Link key={day.id} href={`/nutrition/program/${programId}/day/${day.day_number}`} aria-label={`Lihat Hari ${day.day_number}, ${day.status === "COMPLETED" ? "selesai" : "terlewat"}`} className="relative flex shrink-0 items-start justify-center hover:-translate-y-0.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">{content}</Link>;
            }
            if (locked) {
              return <Link
                key={day.id}
                href={`/nutrition/program/${programId}/day/${day.day_number}`}
                aria-label={`Lihat Hari ${day.day_number}, terkunci`}
                onClick={() => onLockedDay?.(day)}
                className="relative flex shrink-0 items-start justify-center focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
              >
                {content}
              </Link>;
            }
            return <span key={day.id} aria-label={`Hari ${day.day_number} akan datang`} className="relative flex shrink-0 items-start justify-center">{content}</span>;
          })}
        </div>
      </div>
    </div>
  );
}

export function ProgressRing({ value, size = 104, label = "progress" }: { value: number; size?: number; label?: string }) {
  const safe = Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));
  return (
    <div
      className="relative shrink-0 rounded-full"
      style={{ width: size, height: size, background: `conic-gradient(#138b7d ${safe * 3.6}deg, #e7f1ef ${safe * 3.6}deg)` }}
      aria-label={`${label} ${formatPercent(safe)} persen`}
      role="img"
    >
      <div className="absolute inset-[9px] flex flex-col items-center justify-center rounded-full bg-white">
        <span className="text-2xl font-black tracking-[-0.05em] text-text">{formatPercent(safe)}%</span>
        <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-muted">selesai</span>
      </div>
    </div>
  );
}

export function ProgramProgressPanel({ program, goal }: { program: ProgramSummary; goal?: ProgramGoal | null }) {
  return <section className="grid gap-px overflow-hidden rounded-2xl border border-line bg-line shadow-[0_12px_40px_rgba(21,67,55,.05)] md:grid-cols-[1fr_1fr]">
    <div className="bg-white p-6"><div className="flex items-center justify-between"><p className="text-xs font-black uppercase tracking-[0.12em] text-muted">Progress Program</p><span className="text-lg font-black text-text">{formatPercent(program.progress_percent)}%</span></div><div className="mt-4"><ProgressBar value={program.progress_percent} label={`${program.days_completed} dari ${program.duration_days} hari selesai`} /></div><div className="mt-4 flex gap-5 text-xs text-secondary"><span><strong className="text-text">{program.days_completed}</strong> selesai</span><span><strong className="text-warning">{program.missed_days}</strong> terlewat</span><span><strong className="text-text">{Math.max(0, program.duration_days - program.current_day)}</strong> tersisa</span></div></div>
    <div className="bg-white p-6"><div className="flex gap-4"><span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-amber-50 text-amber-600"><CircleDot size={23}/></span><div className="min-w-0 flex-1"><p className="text-xs font-black uppercase tracking-[0.12em] text-muted">Target Utama</p><h3 className="mt-1 font-semibold text-text">{goal?.title ?? "Goal program"}</h3>{goal ? <><p className="mt-2 text-sm text-secondary">{goal.actual} / {goal.target} {goal.unit}</p><div className="mt-3"><ProgressBar value={goal.progress_percentage} label={`${formatPercent(goal.progress_percentage)}% goal achievement`} /></div></> : <p className="mt-2 text-sm text-muted">Goal belum tersedia.</p>}</div></div></div>
  </section>;
}

export function MealFeature({ stage, title, details }: { stage: string; title: string; details: Record<string, unknown> }) {
  const groups = foodGroupsFrom(details.food_groups);
  const displayTitle = formatMenuDisplayTitle(stage, details.example ?? title);
  return <article className="grid gap-5 rounded-2xl border border-line bg-white p-4 shadow-[0_12px_40px_rgba(21,67,55,.05)] sm:p-5 md:grid-cols-[minmax(220px,.8fr)_1.2fr] md:p-6">
    <div className="overflow-hidden rounded-[20px] bg-[#eef7f2] p-2.5"><div className="relative aspect-[4/3] overflow-hidden rounded-[16px]"><MealIllustration stage={stage} title={displayTitle} groups={groups} visualKey={String(details.visual_key ?? "")} /></div></div>
    <div className="flex min-w-0 flex-col justify-center"><p className="text-xs font-black uppercase tracking-[0.12em] text-primary-dark">Menu Hari Ini</p><h3 className="mt-3 break-words text-2xl font-semibold tracking-[-0.035em] text-text sm:text-3xl">{displayTitle}</h3><p className="mt-2 text-sm text-secondary">{String(details.occasion ?? "Waktu makan sesuai panduan")}</p><div className="mt-5 grid gap-3 sm:grid-cols-2">{groups.map((group) => <div key={group} className="flex items-center gap-3 rounded-xl bg-background p-3"><FoodGroupIcon group={group}/><span className="text-sm font-semibold text-text">{group === "healthy-fat" ? "Lemak baik" : group === "vegetable" ? "Sayuran" : group === "fruit" ? "Buah" : group === "protein" ? "Protein" : "Karbohidrat"}</span></div>)}</div><div className="mt-5 border-t border-line pt-4"><p className="text-xs font-bold uppercase tracking-[0.1em] text-muted">Tentang menu</p><p className="mt-2 text-sm leading-6 text-secondary">{String(details.preparation ?? "Ikuti preparation guidance yang tersimpan untuk program ini.")}</p></div></div>
  </article>;
}

function DayStatusIcon({ status, current }: { status: string; current?: boolean }) {
  if (status === "COMPLETED") return <CheckCircle2 size={18} className="text-emerald-700"/>;
  if (status === "MISSED") return <XCircle size={18} className="text-amber-700"/>;
  if (status === "LOCKED") return <LockKeyhole size={16} className="text-slate-500"/>;
  return <CircleDot size={18} className={current ? "text-teal-700" : "text-sky-700"}/>;
}

function dayStatusStyle(status: string, current: boolean) {
  if (current) return { row: "border-teal-300 bg-teal-50 shadow-sm", icon: "bg-white", label: "text-teal-800", text: "TODAY" };
  if (status === "COMPLETED") return { row: "border-emerald-200 bg-emerald-50/70", icon: "bg-white", label: "text-emerald-800", text: "COMPLETED" };
  if (status === "MISSED") return { row: "border-amber-200 bg-amber-50/80", icon: "bg-white", label: "text-amber-800", text: "MISSED" };
  if (status === "LOCKED") return { row: "border-slate-200 bg-slate-50/80", icon: "bg-white", label: "text-slate-600", text: "LOCKED" };
  return { row: "border-sky-200 bg-sky-50/60", icon: "bg-white", label: "text-sky-800", text: status };
}

export function ProgramTimeline({ programId, days, currentDay, onExpire }: { programId: string; days: ProgramDay[]; currentDay: number; onExpire?: () => void }) {
  return <div className="space-y-2">{days.map((day) => {
    const current = day.day_number === currentDay && ["AVAILABLE","IN_PROGRESS"].includes(day.status);
    const style = dayStatusStyle(day.status, current);
    const href = current ? `/nutrition/program/${programId}/today` : `/nutrition/program/${programId}/day/${day.day_number}`;
    return <Link key={day.id} href={href} className={`group flex items-center gap-3 rounded-xl border p-3.5 transition-all duration-300 motion-reduce:transition-none ${style.row}`}>
      <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${style.icon}`}><DayStatusIcon status={day.status} current={current}/></span>
      <span className="min-w-0 flex-1"><span className="block text-xs font-black uppercase tracking-[0.1em] text-muted">Day {day.day_number}</span><span className="mt-0.5 block truncate text-sm font-semibold text-text">{day.focus}</span>{day.status === "LOCKED" && <span className="mt-1 block text-xs text-slate-500">Unlock <ProgramCountdown seconds={day.remaining_seconds} onExpire={onExpire}/></span>}{day.status === "MISSED" && <span className="mt-1 block text-xs font-semibold text-amber-700">Expired · review only</span>}{day.status === "COMPLETED" && <span className="mt-1 block text-xs font-semibold text-emerald-700">Progress tersimpan</span>}</span>
      <span className={`text-xs font-black ${style.label}`}>{style.text}</span><ChevronRight size={16} className="text-muted transition-transform group-hover:translate-x-0.5"/>
    </Link>;
  })}</div>;
}

export function HistoryVisualCard({ program }: { program: ProgramSummary }) {
  const goal = program.goal;
  const status = goal?.status ?? program.status;
  const isFinished = Boolean(program.completed_at) || ["EXTENDED", "COMPLETED"].includes(program.status);
  const href = isFinished ? `/nutrition/program/${program.id}/result` : `/nutrition/program/${program.id}`;
  const statusLabel: Record<string, string> = { ACTIVE: "Sedang berjalan", COMPLETED: "Selesai", EXTENDED: "Diperpanjang", CANCELLED: "Dibatalkan" };
  return (
    <Link
      href={href}
      aria-label={`${program.title}, cycle ${program.cycle_number}, buka ${isFinished ? "Final Program Result" : "program"}`}
      className="group block overflow-hidden rounded-2xl border border-line bg-white shadow-[0_16px_50px_rgba(21,67,55,.05)] transition-all hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-[0_20px_60px_rgba(21,67,55,.08)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary motion-reduce:transition-none"
    >
      <article>
        <div className="h-1.5 bg-[linear-gradient(90deg,#138b7d,#75c6ae,#f2c568)]" />
        <div className="p-5 md:p-6">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-primary-light px-3 py-1 text-[10px] font-black uppercase tracking-[.1em] text-primary-dark">{program.stage}</span>
                <span className="text-xs font-semibold text-muted">Siklus {program.cycle_number}</span>
              </div>
              <h2 className="mt-4 text-xl font-semibold leading-tight tracking-[-0.03em] text-text">{program.title}</h2>
              <p className="mt-2 text-xs text-muted">{new Date(program.started_at).toLocaleDateString("id-ID")} – {new Date(program.ends_at).toLocaleDateString("id-ID")}</p>
            </div>
            <span className={`shrink-0 rounded-full px-3 py-1 text-[10px] font-black ${program.status === "ACTIVE" ? "bg-primary-light text-primary-dark" : program.status === "CANCELLED" ? "bg-slate-100 text-slate-600" : "bg-amber-50 text-amber-700"}`}>{statusLabel[program.status] ?? program.status}{program.status === "CANCELLED" && <span className="sr-only">CANCELLED</span>}</span>
          </div>

          <div className="mt-6 flex items-center gap-5 rounded-2xl bg-[linear-gradient(135deg,#f6fbf9,#fbfcfa)] p-4">
            <ProgressRing value={program.progress_percent} size={88} label="Progress program" />
            <div className="min-w-0 flex-1">
              <p className="text-xs font-bold text-secondary">Perjalanan program</p>
              <p className="mt-1 text-lg font-bold text-text">{program.days_completed} dari {program.duration_days} hari</p>
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-white">
                <div className="h-full rounded-full bg-primary" style={{ width: `${Math.max(0, Math.min(100, program.progress_percent))}%` }} />
              </div>
              <p className="mt-2 text-xs text-muted">{program.completed_tasks} dari {program.total_tasks} aktivitas tercatat</p>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3">
            <div className="rounded-xl bg-background p-3"><p className="text-[9px] font-black uppercase tracking-[.1em] text-muted">Target</p><p className="mt-1 text-sm font-bold text-text">{goal ? `${goal.actual}/${goal.target} ${goal.unit}` : "Belum ada"}</p></div>
            <div className="rounded-xl bg-background p-3"><p className="text-[9px] font-black uppercase tracking-[.1em] text-muted">Selesai</p><p className="mt-1 text-sm font-bold text-text">{program.days_completed} hari</p></div>
            <div className="rounded-xl bg-background p-3"><p className="text-[9px] font-black uppercase tracking-[.1em] text-muted">Terlewat</p><p className="mt-1 text-sm font-bold text-text">{program.missed_days} hari</p></div>
          </div>

          <div className="mt-5 flex min-h-11 items-center justify-between border-t border-line pt-4 text-sm font-semibold text-primary-dark">
            <span>{isFinished ? "Lihat hasil program" : "Lanjutkan program"}</span><ArrowRight className="transition-transform group-hover:translate-x-0.5" size={16} />
          </div>
        </div>
      </article>
    </Link>
  );
}

export function EvaluationBars({ target, actual, unit }: { target: number; actual: number; unit: string }) {
  const max = Math.max(target, actual, 1); const gap = Math.max(0, target-actual);
  return <div className="space-y-4"><div><div className="flex justify-between text-xs font-bold"><span>TARGET</span><span>{target} {unit}</span></div><div className="mt-2 h-3 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-text" style={{width:`${Math.min(100,target/max*100)}%`}}/></div></div><div><div className="flex justify-between text-xs font-bold"><span>ACTUAL</span><span>{actual} {unit}</span></div><div className="mt-2 h-3 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-primary" style={{width:`${Math.min(100,actual/max*100)}%`}}/></div></div><div><div className="flex justify-between text-xs font-bold"><span>GAP</span><span>{gap} {unit}</span></div><div className="mt-2 h-3 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-amber-400" style={{width:`${Math.min(100,gap/max*100)}%`}}/></div></div></div>;
}

export function ProgramQuickStats({ program }: { program: ProgramSummary }) {
  return <div className="grid grid-cols-3 gap-2"><div className="rounded-xl bg-primary-light p-3 text-center"><p className="text-2xl font-black text-primary-dark">{program.days_completed}</p><p className="mt-1 text-[10px] font-bold uppercase tracking-[.08em] text-secondary">Hari selesai</p></div><div className="rounded-xl bg-amber-50 p-3 text-center"><p className="text-2xl font-black text-amber-700">{program.missed_days}</p><p className="mt-1 text-[10px] font-bold uppercase tracking-[.08em] text-secondary">Terlewat</p></div><div className="rounded-xl bg-slate-50 p-3 text-center"><p className="text-2xl font-black text-text">{Math.max(0,program.duration_days-program.current_day)}</p><p className="mt-1 text-[10px] font-bold uppercase tracking-[.08em] text-secondary">Tersisa</p></div></div>;
}
