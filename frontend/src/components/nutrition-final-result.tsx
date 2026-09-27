"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { ArrowRight, CheckCircle2, CircleDot, ShieldAlert, Sparkles, TrendingUp } from "lucide-react";
import { Alert, Badge } from "@/components/ui";
import { useAuth } from "@/components/auth-provider";
import {
  formatPercent,
  getFinalProgramResult,
  type FinalDailyProgressChange,
  type FinalDailyProgressPoint,
  type FinalProgramResult,
} from "@/lib/nutrition-program";

function statusLabel(status: string) {
  const normalized = status.toUpperCase();
  if (normalized === "MET") return "GOAL TERCAPAI";
  if (normalized === "PARTIALLY_MET") return "GOAL SEBAGIAN TERCAPAI";
  if (normalized === "NOT_MET") return "GOAL BELUM TERCAPAI";
  return normalized.replaceAll("_", " ");
}

function outcomeBadge(status: string) {
  if (status === "MET") return "success" as const;
  if (status === "PARTIALLY_MET") return "info" as const;
  return "warning" as const;
}

function stageLabel(stage?: string) {
  if (stage === "mpasi") return "MPASI";
  if (stage === "toddler") return "Toddler";
  if (stage === "elderly") return "Lansia";
  return "Nutrition";
}

function outcomeHeadline(status: string) {
  if (status === "MET") return "Target utama tercapai.";
  if (status === "PARTIALLY_MET") return "Ada progres yang terlihat.";
  if (status === "NOT_MET") return "Program selesai, pola harian sudah terbaca.";
  return "Program selesai dan hasilnya sudah siap ditinjau.";
}

function changeCopy(change?: FinalDailyProgressChange) {
  const delta = change?.delta_points;
  if (delta == null) return "Belum cukup data untuk membandingkan awal dan akhir program.";
  if (delta >= 10) return `Keterlaksanaan target naik ${Math.round(delta)} poin dibanding awal program.`;
  if (delta >= 5) return `Ada kenaikan ${Math.round(delta)} poin pada keterlaksanaan target.`;
  if (delta <= -10) return `Keterlaksanaan target turun ${Math.abs(Math.round(delta))} poin di akhir program.`;
  if (delta <= -5) return `Keterlaksanaan target masih berfluktuasi (${Math.round(delta)} poin).`;
  return "Pola keterlaksanaan relatif stabil dari awal sampai akhir program.";
}

function MetricCard({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="min-w-0 rounded-2xl border border-line bg-white p-4 sm:p-5">
      <p className="text-[10px] font-black uppercase tracking-[.11em] text-muted">{label}</p>
      <p className="mt-2 break-words text-2xl font-semibold tracking-[-.03em] text-text">{value}</p>
      {note ? <p className="mt-1 text-xs leading-5 text-secondary">{note}</p> : null}
    </div>
  );
}

function VisualRing({ value, label, caption }: { value: number; label: string; caption: string }) {
  const percent = Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));
  const radius = 44;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percent / 100) * circumference;
  return (
    <div className="flex min-w-0 items-center gap-4 rounded-3xl border border-line bg-white p-5">
      <div className="relative h-24 w-24 shrink-0" role="img" aria-label={`${label} ${Math.round(percent)} persen`}>
        <svg viewBox="0 0 108 108" className="h-24 w-24 -rotate-90" aria-hidden="true">
          <circle cx="54" cy="54" r={radius} fill="none" stroke="#e2e8f0" strokeWidth="10" />
          <circle cx="54" cy="54" r={radius} fill="none" stroke="#0f766e" strokeWidth="10" strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={offset} />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center"><strong className="text-xl text-primary-dark">{Math.round(percent)}%</strong></div>
      </div>
      <div className="min-w-0">
        <p className="text-xs font-black uppercase tracking-[.1em] text-muted">{label}</p>
        <p className="mt-2 break-words text-sm leading-6 text-secondary">{caption}</p>
      </div>
    </div>
  );
}

function VisualBar({ label, value, total, note }: { label: string; value: number; total: number; note?: string }) {
  const percent = total > 0 ? Math.max(0, Math.min(100, (value / total) * 100)) : 0;
  return (
    <div className="border-t border-line pt-4">
      <div className="flex items-center justify-between gap-4"><p className="text-sm font-semibold text-text">{label}</p><span className="text-xs font-bold text-primary-dark">{value}{total > 0 ? ` / ${total}` : ""}</span></div>
      <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-primary" style={{ width: `${percent}%` }} /></div>
      {note ? <p className="mt-2 text-xs leading-5 text-secondary">{note}</p> : null}
    </div>
  );
}

function DailyTrendChart({ points }: { points: FinalDailyProgressPoint[] }) {
  const width = Math.max(760, points.length * 54);
  const height = 260;
  const left = 48;
  const right = 24;
  const top = 20;
  const bottom = 46;
  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;
  const xFor = (day: number) => left + ((Math.max(1, day) - 1) / Math.max(1, points.length - 1)) * plotWidth;
  const yFor = (value: number) => top + ((100 - Math.max(0, Math.min(100, value))) / 100) * plotHeight;
  const scored = points.filter((point) => point.adherence_percent != null);
  const linePath = scored.map((point, index) => `${index === 0 ? "M" : "L"} ${xFor(point.day)} ${yFor(Number(point.adherence_percent))}`).join(" ");
  const areaPath = scored.length >= 2 ? `${linePath} L ${xFor(scored.at(-1)!.day)} ${top + plotHeight} L ${xFor(scored[0].day)} ${top + plotHeight} Z` : "";

  if (!scored.length) {
    return <div className="rounded-3xl border border-dashed border-line bg-white px-5 py-10 text-center text-sm leading-6 text-muted">Belum ada data hasil harian yang cukup untuk membentuk grafik.</div>;
  }

  return (
    <div className="overflow-x-auto pb-2">
      <svg role="img" aria-label="Grafik pencapaian harian dari hari ke hari" viewBox={`0 0 ${width} ${height}`} className="min-w-[760px] w-full">
        <defs>
          <linearGradient id="daily-progress-area" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#0f766e" stopOpacity="0.18" />
            <stop offset="100%" stopColor="#0f766e" stopOpacity="0.02" />
          </linearGradient>
        </defs>
        {[0, 25, 50, 75, 100].map((value) => {
          const y = yFor(value);
          return <g key={value}><line x1={left} x2={width - right} y1={y} y2={y} stroke="#e2e8f0" strokeDasharray="4 6" /><text x={left - 10} y={y + 4} textAnchor="end" fontSize="10" fill="#64748b">{value}%</text></g>;
        })}
        {areaPath ? <path d={areaPath} fill="url(#daily-progress-area)" /> : null}
        {linePath ? <path d={linePath} fill="none" stroke="#0f766e" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" /> : null}
        {points.map((point) => {
          const x = xFor(point.day);
          const numeric = point.adherence_percent == null ? null : Number(point.adherence_percent);
          return <g key={point.day}>
            <text x={x} y={height - 16} textAnchor="middle" fontSize="10" fill="#64748b">H{point.day}</text>
            {numeric == null ? <circle cx={x} cy={top + plotHeight} r="4" fill="#cbd5e1"><title>{`Hari ${point.day}: belum ada skor target`}</title></circle> : <circle cx={x} cy={yFor(numeric)} r="6" fill="#ffffff" stroke="#0f766e" strokeWidth="4"><title>{`Hari ${point.day}: ${Math.round(numeric)}% target harian · ${point.decision ?? "tanpa adaptasi"}`}</title></circle>}
          </g>;
        })}
      </svg>
    </div>
  );
}

function InsightList({ title, icon, items, tone }: { title: string; icon: ReactNode; items: string[]; tone: "good" | "focus" }) {
  return (
    <div className={`rounded-3xl border p-5 md:p-6 ${tone === "good" ? "border-emerald-100 bg-emerald-50/55" : "border-amber-100 bg-amber-50/60"}`}>
      <div className={`flex items-center gap-2 ${tone === "good" ? "text-emerald-800" : "text-amber-800"}`}>{icon}<p className="text-xs font-black uppercase tracking-[.1em]">{title}</p></div>
      <ul className="mt-4 space-y-3 text-sm leading-6 text-secondary">{items.slice(0, 2).map((item) => <li key={item} className="border-t border-current/10 pt-3">{item}</li>)}</ul>
    </div>
  );
}

export function NutritionFinalResult({ programId, initialResult }: { programId: string; initialResult?: FinalProgramResult }) {
  const { status } = useAuth();
  const router = useRouter();
  const [result, setResult] = useState<FinalProgramResult | null>(initialResult ?? null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (status !== "unauthenticated") return;
    setResult(null);
    router.replace("/");
  }, [router, status]);

  useEffect(() => {
    if (initialResult || status !== "authenticated") return;
    let active = true;
    getFinalProgramResult(programId).then((value) => { if (active) setResult(value); }).catch((err) => {
      if (active) setError(err instanceof Error ? err.message : "Final Program Result belum dapat dimuat.");
    });
    return () => { active = false; };
  }, [initialResult, programId, status]);

  const adaptationDistribution = useMemo(() => {
    const counts = new Map<string, number>();
    (result?.adaptation_history ?? []).forEach((item) => {
      const key = String(item.decision ?? "CONTINUE");
      counts.set(key, (counts.get(key) ?? 0) + 1);
    });
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]);
  }, [result]);

  if (error) return <Alert variant="error" title="Final result belum tersedia">{error}</Alert>;
  if (!result) return <div className="min-h-[520px] animate-pulse border border-line bg-white" aria-label="Memuat Final Program Result" />;

  const goal = result.goal;
  const completed = Number(result.program_numbers.completed_days ?? result.program.days_completed ?? 0);
  const missed = Number(result.program_numbers.missed_days ?? result.program.missed_days ?? 0);
  const logged = Number(result.program_numbers.logged_days ?? 0);
  const adaptations = Number(result.program_numbers.adaptation_decisions ?? result.adaptation_history.length);
  const decision = String(result.next_step.decision ?? "REVIEW");
  const needsSafetyReview = decision === "REFER" || result.safety_notes.length > 0;
  const canExtend = Boolean(result.next_step.can_extend);
  const canReframe = Boolean(result.next_step.can_reframe);
  const dailyProgress = result.trends.daily_progress ?? [];
  const change = result.trends.daily_progress_change;
  const delta = change?.delta_points;
  const isElderly = result.program.stage === "elderly";
  const elderlyDaily = isElderly ? result.trends.elderly_daily_context : undefined;
  const elderlyBarriers = elderlyDaily?.barriers ?? {};
  const barrierLabels: Record<string, string> = { low_appetite: "Tidak terasa lapar", early_satiety: "Cepat kenyang", chewing: "Sulit mengunyah", swallowing: "Menelan terasa lebih sulit", preparation: "Sulit menyiapkan makanan", availability: "Makanan/bahan tidak tersedia", support: "Bantuan tidak tersedia", other: "Hambatan lain" };
  const topBarrier = Object.entries(elderlyBarriers).filter(([key]) => key !== "none").sort((a, b) => Number(b[1]) - Number(a[1]))[0];
  const authenticated = status === "authenticated";
  const strongDays = Number(change?.strong_days ?? dailyProgress.filter((point) => Number(point.adherence_percent ?? -1) >= 80).length);
  const scoredDays = Number(change?.scored_days ?? dailyProgress.filter((point) => point.adherence_percent != null).length);

  return <article className="pb-20">
    {authenticated ? <Link href={`/nutrition/program/${programId}/history`} className="text-xs font-bold uppercase tracking-[.12em] text-muted">← Riwayat Program</Link> : <p className="text-xs font-bold uppercase tracking-[.12em] text-muted">Snapshot hasil program</p>}

    <header className="mt-5 overflow-hidden rounded-[32px] border border-line bg-[linear-gradient(145deg,#f2fbf8_0%,#ffffff_55%,#fff8ea_100%)] p-6 sm:p-8 md:p-10">
      <div className="flex flex-wrap items-start justify-between gap-5">
        <div className="max-w-3xl">
          <p className="eyebrow">Final Result · {stageLabel(result.program.stage)} · Cycle {result.cycle}</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-[-.045em] text-text sm:text-5xl">{outcomeHeadline(result.goal_status)}</h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-secondary">{goal?.title ? `${goal.title}. ` : ""}{changeCopy(change)}</p>
          <p className="mt-3 text-sm font-semibold text-primary-dark">{result.program.title}</p>
        </div>
        <Badge variant={outcomeBadge(result.goal_status)}>{statusLabel(result.goal_status)}</Badge>
      </div>
      <div className="mt-8 grid gap-3 sm:grid-cols-3">
        <MetricCard label="Program selesai" value={`${completed} / ${result.duration_days} hari`} note={`${formatPercent(result.program_completion_percent)}% completion`} />
        <MetricCard label="Pencapaian goal" value={goal ? `${goal.actual} / ${goal.target}` : `${formatPercent(result.goal_achievement_percent)}%`} note={`${formatPercent(result.goal_achievement_percent)}% dari target utama`} />
        <MetricCard label="Perubahan awal → akhir" value={delta == null ? "Belum cukup data" : `${delta > 0 ? "+" : ""}${Math.round(delta)} poin`} note={scoredDays ? `${strongDays} dari ${scoredDays} hari berada di ≥80% target harian` : "Skor berasal dari target perilaku yang tersimpan"} />
      </div>
    </header>

    {needsSafetyReview ? <section className="mt-6"><Alert variant="warning" title="Safety review diperlukan">{result.safety_notes[0] ?? "Program memerlukan review sebelum otomatis dilanjutkan."}</Alert></section> : null}

    <section className="mt-10" aria-labelledby="visual-final-summary-title">
      <p className="eyebrow">Perjalanan program</p>
      <h2 id="visual-final-summary-title" className="mt-2 text-3xl font-semibold tracking-[-.035em]">Lihat hasil cycle dalam satu tampilan.</h2>
      <p className="mt-3 max-w-3xl text-sm leading-7 text-secondary">Grafik menunjukkan keterlaksanaan target harian dari Hari 1 sampai Hari {result.duration_days}. Ini adalah progres perilaku yang tercatat, bukan skor kesehatan atau diagnosis.</p>

      <div className="mt-6 rounded-[28px] border border-line bg-white p-4 sm:p-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div><p className="text-xs font-black uppercase tracking-[.1em] text-muted">Hari ke hari</p><h3 className="mt-1 text-xl font-semibold">Pola keterlaksanaan target</h3></div>
          <div className="flex flex-wrap gap-2 text-xs font-semibold text-secondary"><span className="rounded-full bg-primary-light/40 px-3 py-1.5">Awal {change?.early_average == null ? "—" : `${Math.round(change.early_average)}%`}</span><span className="rounded-full bg-primary-light/40 px-3 py-1.5">Akhir {change?.recent_average == null ? "—" : `${Math.round(change.recent_average)}%`}</span></div>
        </div>
        <div className="mt-5"><DailyTrendChart points={dailyProgress} /></div>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <VisualRing value={result.program_completion_percent} label="Program selesai" caption={`${completed} dari ${result.duration_days} hari selesai${missed ? ` · ${missed} hari terlewat` : ""}.`} />
        <VisualRing value={result.goal_achievement_percent} label="Pencapaian goal" caption={goal ? `${goal.actual} dari target ${goal.target} ${goal.unit}.` : "Goal belum memiliki data pengukuran lengkap."} />
      </div>
    </section>

    <section className="mt-10 grid gap-4 md:grid-cols-2" aria-label="Ringkasan hasil utama">
      <InsightList title="Yang sudah kuat" icon={<CheckCircle2 size={18} />} items={result.what_worked_well.length ? result.what_worked_well : result.what_accomplished} tone="good" />
      <InsightList title="Yang masih perlu fokus" icon={<CircleDot size={18} />} items={result.challenges} tone="focus" />
    </section>

    <section className="mt-10 rounded-[28px] border border-line bg-background/55 p-5 md:p-7" aria-labelledby="adaptation-summary-title">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div><div className="flex items-center gap-2 text-primary-dark"><TrendingUp size={18} /><p className="eyebrow">Adaptasi program</p></div><h2 id="adaptation-summary-title" className="mt-2 text-2xl font-semibold">Rencana menyesuaikan hasil harian.</h2></div>
        <span className="text-xs font-semibold text-muted">{adaptations} keputusan adaptasi</span>
      </div>
      {adaptationDistribution.length ? <div className="mt-5 flex flex-wrap gap-2">{adaptationDistribution.map(([name, count]) => <span key={name} className="rounded-full border border-line bg-white px-3 py-2 text-xs font-bold text-secondary">{name.replaceAll("_", " ")} · {count}×</span>)}</div> : <p className="mt-4 text-sm text-muted">Tidak ada perubahan adaptif yang perlu diringkas.</p>}
      <p className="mt-4 max-w-4xl text-sm leading-7 text-secondary">{result.what_changed}</p>
    </section>

    {isElderly && elderlyDaily ? <section className="mt-10 min-w-0 rounded-[28px] border border-line bg-white p-5 md:p-7" aria-labelledby="elderly-final-trends-title">
      <p className="eyebrow">Insight Lansia</p>
      <h2 id="elderly-final-trends-title" className="mt-2 text-2xl font-semibold">Apa yang paling sering muncul selama program?</h2>
      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_280px]">
        <div className="grid gap-x-6 sm:grid-cols-2">
          <VisualBar label="Nafsu makan menurun" value={Number(elderlyDaily.appetite?.reduced ?? 0) + Number(elderlyDaily.appetite?.poor ?? 0)} total={Number(elderlyDaily.logged_days ?? logged)} />
          <VisualBar label="Cairan berkurang" value={Number(elderlyDaily.hydration?.reduced ?? 0) + Number(elderlyDaily.hydration?.poor ?? 0)} total={Number(elderlyDaily.logged_days ?? logged)} />
          <VisualBar label="Ada kesulitan makan/minum" value={Number(elderlyDaily.difficulty?.some ?? 0) + Number(elderlyDaily.difficulty?.difficult ?? 0)} total={Number(elderlyDaily.logged_days ?? logged)} />
          <VisualBar label="Perlu pengingat / bantuan" value={Number(elderlyDaily.eating_support?.reminder ?? 0) + Number(elderlyDaily.eating_support?.assisted ?? 0)} total={Number(elderlyDaily.logged_days ?? logged)} />
        </div>
        <div className="rounded-3xl border border-line bg-[linear-gradient(145deg,#f7fbf9,#fffaf0)] p-5">
          <p className="text-[10px] font-black uppercase tracking-[.1em] text-muted">Hambatan dominan</p>
          <p className="mt-3 break-words text-2xl font-semibold">{topBarrier ? (barrierLabels[topBarrier[0]] ?? topBarrier[0].replaceAll("_", " ")) : "Tidak ada pola dominan"}</p>
          <p className="mt-2 text-sm leading-6 text-secondary">{topBarrier ? `${Number(topBarrier[1])} hari tercatat.` : "Belum ada hambatan berulang yang menonjol."}</p>
        </div>
      </div>
    </section> : null}

    <section className="mt-10 overflow-hidden rounded-[30px] bg-[#0b2723] p-6 text-white sm:p-8" aria-labelledby="next-step-title">
      <div className="flex flex-wrap items-start justify-between gap-6">
        <div className="max-w-3xl">
          <div className="flex items-center gap-2 text-emerald-200"><Sparkles size={18} /><p className="text-xs font-black uppercase tracking-[.12em]">Langkah berikutnya</p></div>
          <h2 id="next-step-title" className="mt-3 text-3xl font-semibold tracking-[-.035em]">{decision.replaceAll("_", " ")}</h2>
          <p className="mt-4 text-sm leading-7 text-white/75">{String(result.next_step.message ?? "Tinjau hasil dan tentukan langkah berikutnya.")}</p>
        </div>
        <div className="flex flex-wrap gap-3">
          {authenticated && needsSafetyReview ? <Link href={`/nutrition/program/${programId}/history`} className="inline-flex min-h-11 items-center rounded-full bg-amber-400 px-5 text-sm font-semibold text-slate-950">Lihat panduan & riwayat <ArrowRight className="ml-2" size={15} /></Link> : null}
          {authenticated && !needsSafetyReview && canExtend ? <Link href={`/nutrition/program/${programId}/history#extension-review`} className="inline-flex min-h-11 items-center rounded-full bg-white px-5 text-sm font-semibold text-slate-950">Extend Guided Program <ArrowRight className="ml-2" size={15} /></Link> : null}
          {authenticated && !needsSafetyReview && canReframe ? <Link href={`/nutrition/program/${programId}/history#extension-review`} className="inline-flex min-h-11 items-center rounded-full border border-white/25 px-5 text-sm font-semibold text-white">Reframe Goal</Link> : null}
          {!needsSafetyReview && !canExtend && !canReframe ? <Link href="/nutrition" className="inline-flex min-h-11 items-center rounded-full bg-white px-5 text-sm font-semibold text-slate-950">Selesai <ArrowRight className="ml-2" size={15} /></Link> : null}
        </div>
      </div>
    </section>

    {result.safety_notes.length ? <section className="mt-6 border border-amber-200 bg-amber-50 p-6" aria-labelledby="safety-title"><div className="flex items-center gap-2 text-amber-800"><ShieldAlert size={19} /><h2 id="safety-title" className="text-lg font-semibold">Safety / important notes</h2></div><ul className="mt-4 space-y-2 text-sm leading-6 text-secondary">{result.safety_notes.map((item) => <li key={item}>{item}</li>)}</ul></section> : null}

    {authenticated ? <div className="mt-6 flex justify-end"><Link href={`/nutrition/program/${programId}/history`} className="text-sm font-semibold text-secondary hover:text-text">Kembali ke Riwayat Program →</Link></div> : null}
  </article>;
}
