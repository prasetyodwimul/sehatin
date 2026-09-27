"use client";

/* eslint-disable @next/next/no-img-element */

import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, CircleDot, LockKeyhole, XCircle } from "lucide-react";
import { ProgramCountdown } from "@/components/program-countdown";
import { Alert, ProgressBar } from "@/components/ui";
import { formatPercent, getProgramEvaluation, type ProgramEvaluation } from "@/lib/nutrition-program";
import { useAuth } from "@/components/auth-provider";
import { useNutritionProgramShell } from "@/components/nutrition-program-shell";

type DecisionRow = { day?: number; decision?: { decision?: string; user_facing_reason?: string; reason?: string }; indicators?: { trend_direction?: string } };

export function NutritionProgramProgressPage() {
  const { status } = useAuth();
  const { program, loading, refreshProgram, elapsedSeconds } = useNutritionProgramShell();
  const [evaluation, setEvaluation] = useState<ProgramEvaluation | null>(null);
  const [error, setError] = useState("");
  const programId = program?.id;

  useEffect(() => {
    if (!programId || status !== "authenticated") return;
    let active = true;
    getProgramEvaluation(programId).then((value) => { if (active) setEvaluation(value); }).catch((err) => { if (active) setError(err instanceof Error ? err.message : "Evaluasi belum dapat dimuat."); });
    return () => { active = false; };
  }, [programId, status]);

  const decisions = useMemo(() => {
    const rows = evaluation?.details?.decision_history;
    return Array.isArray(rows) ? rows as DecisionRow[] : [];
  }, [evaluation]);

  if (loading) return <div className="min-h-[520px] animate-pulse rounded-[28px] border border-line bg-white" aria-label="Memuat progres program" />;
  if (!program) return <Alert variant="warning">Program belum dapat dimuat.</Alert>;
  const goal = program.goal ?? program.goals?.[0] ?? null;

  return <div>
    <section className="grid gap-6 lg:grid-cols-[1fr_280px] lg:items-end">
      <div><p className="eyebrow">Progress</p><h2 className="mt-2 text-4xl font-semibold tracking-[-.045em]">Perjalanan {program.duration_days} hari, tanpa mencampur goal.</h2><p className="mt-4 max-w-3xl text-sm leading-7 text-secondary">Program progress berasal dari completed days. Goal achievement berasal dari metric goal yang dipilih. Missed days tetap terlihat tetapi tidak dihitung sebagai completed.</p></div>
      <figure className="overflow-hidden rounded-[24px] border border-line bg-background"><img src="/images/sehatin/program-progress.svg" alt="Grafis editorial grafik perkembangan target harian program nutrisi." className="aspect-[16/9] w-full object-cover object-[72%_55%]" /></figure>
    </section>

    {error ? <div className="mt-6"><Alert variant="error">{error}</Alert></div> : null}

    <section className="mt-9 grid min-w-0 gap-8 rounded-[28px] border border-line bg-white p-6 md:grid-cols-2 md:p-7">
      <div><div className="flex items-end justify-between"><div><p className="text-xs font-black uppercase tracking-[.1em] text-muted">Program progress</p><p className="mt-2 text-3xl font-semibold">{program.days_completed} / {program.duration_days}</p></div><strong className="text-xl text-primary-dark">{formatPercent(program.progress_percent)}%</strong></div><div className="mt-3"><ProgressBar value={program.progress_percent} label={`${formatPercent(program.progress_percent)}% program progress`} /></div><p className="mt-2 text-xs text-muted">{program.missed_days} hari terlewat</p></div>
      <div><div className="flex items-end justify-between"><div><p className="text-xs font-black uppercase tracking-[.1em] text-muted">Goal achievement</p><p className="mt-2 text-3xl font-semibold">{goal ? `${goal.actual} / ${goal.target}` : "—"}</p></div><strong className="text-xl text-primary-dark">{goal ? `${formatPercent(goal.progress_percentage)}%` : "—"}</strong></div>{goal ? <><div className="mt-3"><ProgressBar value={goal.progress_percentage} label={`${formatPercent(goal.progress_percentage)}% goal achievement`} /></div><p className="mt-2 text-xs text-muted">{goal.title}</p></> : null}</div>
    </section>

    <section className="mt-10" aria-labelledby="journey-title"><p className="eyebrow">14-Day Journey</p><h3 id="journey-title" className="mt-2 text-2xl font-semibold">Setiap hari punya status sendiri.</h3><div className="mt-5 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{program.days.map((day) => { const current = day.day_number === program.current_day && ["AVAILABLE", "IN_PROGRESS"].includes(day.status); const Icon = day.status === "COMPLETED" ? CheckCircle2 : day.status === "MISSED" ? XCircle : day.status === "LOCKED" ? LockKeyhole : CircleDot; return <article key={day.id} className={`min-w-0 rounded-2xl border p-4 ${current ? "border-primary bg-primary-light/35" : "border-line bg-white"}`}><div className="flex items-start justify-between gap-3"><div><p className="text-xs font-black uppercase tracking-[.1em] text-muted">Hari {day.day_number}</p><p className="mt-2 text-sm font-semibold">{day.focus}</p></div><Icon size={18} className={day.status === "COMPLETED" ? "text-emerald-700" : day.status === "MISSED" ? "text-amber-700" : "text-primary-dark"}/></div><p className="mt-3 text-[11px] font-black uppercase tracking-[.09em] text-secondary">{current ? "TODAY" : day.status}</p>{day.status === "LOCKED" && day.remaining_seconds > 0 ? <p className="mt-2 text-xs text-muted">Unlock <ProgramCountdown seconds={day.remaining_seconds} syncElapsedSeconds={elapsedSeconds} onExpire={() => { void refreshProgram(); }} /></p> : null}</article>; })}</div></section>

    <section className="mt-10 border-t border-line pt-8" aria-labelledby="adaptation-title"><p className="eyebrow">Adaptation Timeline</p><h3 id="adaptation-title" className="mt-2 text-2xl font-semibold">Kenapa rencana berubah.</h3>{decisions.length ? <div className="mt-5 min-w-0 divide-y divide-line overflow-hidden rounded-[28px] border border-line bg-white px-5">{decisions.map((row, index) => <div key={`${row.day}-${index}`} className="grid gap-2 py-4 sm:grid-cols-[90px_130px_1fr]"><p className="text-xs font-black uppercase tracking-[.1em] text-muted">Hari {row.day ?? "—"}</p><p className="text-sm font-semibold text-primary-dark">{row.decision?.decision ?? "CONTINUE"}</p><p className="text-sm leading-6 text-secondary">{row.decision?.user_facing_reason ?? row.decision?.reason ?? "Tidak ada perubahan besar."}</p></div>)}</div> : <p className="mt-5 text-sm text-muted">Belum ada decision history yang cukup untuk ditampilkan.</p>}</section>
  </div>;
}
