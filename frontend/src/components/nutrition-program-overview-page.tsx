"use client";

/* eslint-disable @next/next/no-img-element */

import Link from "next/link";
import { ArrowRight, CheckCircle2, CircleDot, LockKeyhole, XCircle } from "lucide-react";
import { ProgramCountdown } from "@/components/program-countdown";
import { Alert, ProgressBar } from "@/components/ui";
import { formatPercent } from "@/lib/nutrition-program";
import { useNutritionProgramShell } from "@/components/nutrition-program-shell";

export function NutritionProgramOverviewPage() {
  const { program, loading, readOnly, refreshProgram, elapsedSeconds } = useNutritionProgramShell();
  if (loading) return <div className="min-h-[520px] animate-pulse rounded-[28px] border border-line bg-white" aria-label="Memuat ringkasan program" />;
  if (!program) return <Alert variant="warning">Program belum dapat dimuat.</Alert>;
  const goal = program.goal ?? program.goals?.[0] ?? null;
  const nextLocked = program.days.find((day) => day.status === "LOCKED" && day.remaining_seconds > 0);
  const current = program.days.find((day) => day.day_number === program.current_day) ?? program.days[0];

  return <div>
    <section className="grid gap-6 lg:grid-cols-[1fr_300px] lg:items-end">
      <div><p className="eyebrow">Ringkasan</p><h2 className="mt-2 text-4xl font-semibold tracking-[-.045em]">Di mana kamu sekarang, apa goal-nya, dan apa berikutnya.</h2><p className="mt-4 max-w-3xl text-sm leading-7 text-secondary">Program ini berjalan sebagai block {program.duration_days} hari. Selesainya block tidak otomatis berarti goal tercapai.</p></div>
      <figure className="overflow-hidden rounded-[24px] border border-line bg-background shadow-[0_14px_40px_rgba(16,32,29,.06)]"><img src="/images/sehatin/program-overview.svg" alt="Grafis editorial kalender program, piring seimbang, dan ringkasan target nutrisi." className="aspect-[5/3] w-full object-cover object-[56%_54%]" /></figure>
    </section>

    <section className="mt-9 grid gap-8 border-y border-line py-7 md:grid-cols-2">
      <div><p className="text-xs font-black uppercase tracking-[.1em] text-muted">Current day</p><p className="mt-2 text-3xl font-semibold">Hari {program.current_day} dari {program.duration_days}</p><p className="mt-2 text-sm text-secondary">{current?.focus ?? "Daily guidance"} · {current?.status ?? program.status}</p>{!readOnly ? <Link href={`/nutrition/program/${program.id}/today`} className="mt-5 inline-flex min-h-11 items-center rounded-full bg-primary px-5 text-sm font-semibold text-white">Buka Hari Ini <ArrowRight className="ml-2" size={15}/></Link> : null}</div>
      <div><p className="text-xs font-black uppercase tracking-[.1em] text-muted">Next guidance</p>{nextLocked ? <><p className="mt-2 text-3xl font-semibold">Hari {nextLocked.day_number}</p><p className="mt-2 text-sm text-secondary">Unlocks in <ProgramCountdown seconds={nextLocked.remaining_seconds} syncElapsedSeconds={elapsedSeconds} onExpire={() => { void refreshProgram(); }} /></p><p className="mt-1 text-xs text-muted">Backend tetap menjadi source of truth untuk izin unlock.</p></> : <><p className="mt-2 text-3xl font-semibold">Tidak ada countdown aktif</p><p className="mt-2 text-sm text-secondary">Program mungkin sudah berada di hari terakhir atau semua guidance yang relevan sudah terbuka.</p></>}</div>
    </section>

    <section className="mt-10 grid gap-8 md:grid-cols-2">
      <div><div className="flex items-end justify-between"><div><p className="text-xs font-black uppercase tracking-[.1em] text-muted">Program Progress</p><p className="mt-2 text-3xl font-semibold">{program.days_completed} / {program.duration_days}</p></div><strong className="text-xl text-primary-dark">{formatPercent(program.progress_percent)}%</strong></div><div className="mt-3"><ProgressBar value={program.progress_percent} label={`${formatPercent(program.progress_percent)}% program progress`} /></div><p className="mt-2 text-xs text-muted">{program.missed_days} hari terlewat tidak dihitung sebagai completed.</p></div>
      <div><div className="flex items-end justify-between"><div><p className="text-xs font-black uppercase tracking-[.1em] text-muted">Goal Achievement</p><p className="mt-2 text-3xl font-semibold">{goal ? `${goal.actual} / ${goal.target}` : "—"}</p></div><strong className="text-xl text-primary-dark">{goal ? `${formatPercent(goal.progress_percentage)}%` : "—"}</strong></div>{goal ? <><div className="mt-3"><ProgressBar value={goal.progress_percentage} label={`${formatPercent(goal.progress_percentage)}% goal achievement`} /></div><p className="mt-2 text-xs text-muted">{goal.title}</p></> : <p className="mt-3 text-sm text-muted">Goal belum tersedia.</p>}</div>
    </section>

    <section className="mt-10" aria-labelledby="overview-journey"><p className="eyebrow">Journey</p><h3 id="overview-journey" className="mt-2 text-2xl font-semibold">Status setiap hari.</h3><div className="mt-5 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{program.days.map((day) => { const active = day.day_number === program.current_day && ["AVAILABLE", "IN_PROGRESS"].includes(day.status); const Icon = day.status === "COMPLETED" ? CheckCircle2 : day.status === "MISSED" ? XCircle : day.status === "LOCKED" ? LockKeyhole : CircleDot; return <article key={day.id} className={`border p-4 ${active ? "border-primary bg-primary-light/35" : "border-line bg-white"}`}><div className="flex items-start justify-between gap-3"><div><p className="text-xs font-black uppercase tracking-[.1em] text-muted">Hari {day.day_number}</p><p className="mt-2 text-sm font-semibold">{day.focus}</p></div><Icon size={18} className={day.status === "COMPLETED" ? "text-emerald-700" : day.status === "MISSED" ? "text-amber-700" : "text-primary-dark"}/></div><p className="mt-3 text-[11px] font-black uppercase tracking-[.09em] text-secondary">{active ? "TODAY" : day.status}</p>{day.status === "LOCKED" && day.remaining_seconds > 0 ? <p className="mt-2 text-xs text-muted"><ProgramCountdown seconds={day.remaining_seconds} syncElapsedSeconds={elapsedSeconds} onExpire={() => { void refreshProgram(); }} /></p> : null}</article>; })}</div></section>
  </div>;
}
