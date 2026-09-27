"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, CheckCircle2, CircleDot, History, LockKeyhole, ShieldAlert, TrendingUp, XCircle } from "lucide-react";
import { NutritionProgramDailyWorkspace } from "@/components/nutrition-program-daily-workspace";
import { formatProgramRemaining, useNutritionProgramShell } from "@/components/nutrition-program-shell";
import { Alert, Badge, Button, ProgressBar, Textarea } from "@/components/ui";
import { extendNutritionProgram, formatPercent, getBlockReview, getExtensionRecommendation, type BlockReview, type ExtensionRecommendation, type ProgramDay } from "@/lib/nutrition-program";

function dayLabel(day: ProgramDay) {
  if (day.status === "COMPLETED") return "Selesai";
  if (day.status === "MISSED") return "Terlewat";
  if (day.status === "LOCKED") return "Terkunci";
  if (day.status === "IN_PROGRESS") return "Sedang dikerjakan";
  return "Tersedia";
}

function DayIcon({ day }: { day: ProgramDay }) {
  if (day.status === "COMPLETED") return <CheckCircle2 size={18}/>;
  if (day.status === "MISSED") return <XCircle size={18}/>;
  if (day.status === "LOCKED") return <LockKeyhole size={17}/>;
  return <CircleDot size={17}/>;
}

const ELDERLY_DAILY_LABELS: Record<string, Record<string, string>> = {
  appetite_status: { good: "Baik", reduced: "Menurun", poor: "Sangat sedikit" },
  hydration_status: { good: "Teratur", reduced: "Lebih sedikit", poor: "Sangat sedikit" },
  routine_adherence: { yes: "Terlaksana", partial: "Sebagian", no: "Belum" },
  eating_difficulty: { none: "Tidak ada", some: "Ada sedikit", difficult: "Cukup sulit" },
  eating_support: { independent: "Mandiri", reminder: "Perlu diingatkan", assisted: "Perlu dibantu" },
};

function elderlyRecentContext(program: ReturnType<typeof useNutritionProgramShell>["program"]) {
  const logs = program.days
    .map((day) => (day.action_details?.daily_log ?? null) as Record<string, unknown> | null)
    .filter((row): row is Record<string, unknown> => Boolean(row));
  const latest = logs.at(-1) ?? {};
  const count = (key: string, value: string) => logs.filter((row) => row[key] === value).length;
  return {
    loggedDays: logs.length,
    latest,
    reducedAppetiteDays: count("appetite_status", "reduced") + count("appetite_status", "poor"),
    lowHydrationDays: count("hydration_status", "reduced") + count("hydration_status", "poor"),
    difficultDays: count("eating_difficulty", "some") + count("eating_difficulty", "difficult"),
    assistedDays: count("eating_support", "reminder") + count("eating_support", "assisted"),
  };
}

export function NutritionProgramOverviewSection() {
  const { program, elapsedSeconds } = useNutritionProgramShell();
  const goal = program.goals[0] ?? program.goal ?? null;
  const current = program.days.find((day) => day.day_number === program.current_day) ?? program.days[0];
  const nextLocked = program.days.find((day) => day.status === "LOCKED" && day.remaining_seconds > 0) ?? null;

  return <div className="space-y-10">
    <section className="border-b border-line pb-8">
      <p className="eyebrow">Ringkasan Program</p>
      <div className="mt-3 grid gap-7 xl:grid-cols-[1.15fr_.85fr] xl:items-end">
        <div><h2 className="text-4xl font-semibold tracking-[-.045em] sm:text-5xl">Kamu ada di Hari {program.current_day} dari {program.duration_days}.</h2><p className="mt-4 max-w-2xl text-sm leading-7 text-secondary">Ringkasan ini memisahkan kemajuan block program dari pencapaian goal. Detail harian mengikuti data yang tersimpan di backend.</p></div>
        <div className="border-l-0 border-line xl:border-l xl:pl-7"><p className="text-xs font-black uppercase tracking-[.1em] text-muted">Fokus saat ini</p><p className="mt-2 text-xl font-semibold">{current?.focus || "Menjaga ritme program"}</p><Link href={`/nutrition/program/${program.id}/today`} className="mt-5 inline-flex min-h-11 items-center rounded-full bg-text px-5 text-sm font-semibold text-white">Buka Hari Ini <ArrowRight className="ml-2" size={16}/></Link></div>
      </div>
    </section>

    <section className="grid gap-6 md:grid-cols-2" aria-label="Kemajuan program dan goal">
      <article className="border-t border-line pt-5"><div className="flex items-end justify-between gap-4"><div><p className="text-xs font-black uppercase tracking-[.11em] text-muted">Program progress</p><h3 className="mt-2 text-3xl font-semibold">{program.days_completed} / {program.duration_days} hari</h3></div><strong className="text-2xl text-primary-dark">{formatPercent(program.progress_percent)}%</strong></div><div className="mt-4"><ProgressBar value={program.progress_percent} label={`${program.days_completed} dari ${program.duration_days} hari selesai`} /></div><p className="mt-3 text-xs text-secondary">{program.missed_days} hari terlewat · tidak dihitung sebagai completed.</p></article>
      <article className="border-t border-line pt-5"><div className="flex items-end justify-between gap-4"><div><p className="text-xs font-black uppercase tracking-[.11em] text-muted">Goal achievement</p><h3 className="mt-2 text-3xl font-semibold">{goal ? `${goal.actual} / ${goal.target} ${goal.unit}` : "—"}</h3></div><strong className="text-2xl text-primary-dark">{goal ? `${formatPercent(goal.progress_percentage)}%` : "—"}</strong></div><div className="mt-4"><ProgressBar value={goal?.progress_percentage ?? 0} label={goal ? `${goal.actual} dari ${goal.target} ${goal.unit}` : "Goal belum tersedia"} /></div><p className="mt-3 text-xs text-secondary">{goal?.title ?? "Goal program belum tersedia."}</p></article>
    </section>

    <section className="border-y border-line py-7">
      {program.status === "SAFETY_HOLD" ? <div><p className="eyebrow">Next guidance</p><h2 className="mt-2 text-2xl font-semibold">Panduan berikutnya dihentikan karena Safety Hold.</h2><p className="mt-2 text-sm leading-6 text-secondary">Safety hold tidak memiliki timer. Program dihentikan karena tanda bahaya dan tidak dapat dilanjutkan dari goal lama. Segera cari pertolongan medis, lalu ulangi asesmen sebelum memulai program baru.</p></div> : <div className="flex flex-wrap items-start justify-between gap-6"><div><p className="eyebrow">Next guidance</p><h2 className="mt-2 text-2xl font-semibold">{nextLocked ? `Hari ${nextLocked.day_number} masih terkunci.` : "Tidak ada countdown aktif."}</h2><p className="mt-2 text-sm leading-6 text-secondary">Unlock permission berasal dari server. Browser hanya menampilkan countdown lalu refetch ketika mencapai nol.</p></div>{nextLocked ? <div className="min-w-[220px] text-left md:text-right"><p className="text-xs font-black uppercase tracking-[.1em] text-muted">Unlocks in</p><p className="mt-2 text-3xl font-semibold text-primary-dark"><span aria-live="polite">{formatProgramRemaining(Math.max(0, nextLocked.remaining_seconds - elapsedSeconds))}</span></p><p className="mt-2 text-xs text-muted">{new Date(nextLocked.unlock_at).toLocaleString("id-ID")}</p></div> : null}</div>}
    </section>

    <section><div className="flex items-end justify-between gap-4"><div><p className="eyebrow">14-Day Journey</p><h2 className="mt-2 text-2xl font-semibold">Setiap hari punya status yang jelas.</h2></div><Link href={`/nutrition/program/${program.id}/progress`} className="text-sm font-semibold text-primary-dark">Lihat progres lengkap →</Link></div><div className="mt-5 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">{program.days.map((day) => <Link key={day.id} href={day.status === "LOCKED" ? "#" : `/nutrition/program/${program.id}/day/${day.day_number}`} aria-disabled={day.status === "LOCKED"} tabIndex={day.status === "LOCKED" ? -1 : 0} className={`flex min-h-16 items-center gap-3 border px-4 py-3 ${day.status === "LOCKED" ? "pointer-events-none border-line bg-slate-50 text-muted" : "border-line bg-white hover:border-primary/30"}`}><span className="text-primary-dark"><DayIcon day={day}/></span><span className="min-w-0 flex-1"><span className="block text-xs font-black uppercase tracking-[.09em] text-muted">Hari {day.day_number} · {dayLabel(day)}</span><span className="mt-1 block truncate text-sm font-semibold text-text">{day.focus || "Panduan adaptif"}</span></span></Link>)}</div></section>
  </div>;
}

export function NutritionProgramTodaySection() {
  const { program, setProgram, signedOutSnapshot } = useNutritionProgramShell();
  const current = program.days.find((day) => day.day_number === program.current_day)
    ?? program.days.find((day) => ["AVAILABLE", "IN_PROGRESS"].includes(day.status))
    ?? [...program.days].sort((a, b) => b.day_number - a.day_number).find((day) => ["COMPLETED", "MISSED"].includes(day.status))
    ?? program.days[0];

  if (!current) return <Alert variant="error">Hari program belum tersedia.</Alert>;
  if (signedOutSnapshot) return <section className="border-y border-line py-8"><p className="eyebrow">Hari Ini</p><h2 className="mt-2 text-3xl font-semibold">Program tersimpan bersifat pribadi.</h2><p className="mt-3 text-sm leading-7 text-secondary">Masuk kembali untuk membuka workspace dan menyimpan progress.</p></section>;

  return <div className="space-y-6">
    {program.status === "CANCELLED" ? <Alert variant="info" title="Program sudah dibatalkan">Hari yang sudah tersimpan tetap dapat ditinjau dalam mode read-only.</Alert> : null}
    {program.status === "EXTENDED" ? <Alert variant="info" title="Cycle ini sudah selesai">Workspace tetap dapat ditinjau. Cycle lanjutan tersedia dari riwayat program.</Alert> : null}
    <NutritionProgramDailyWorkspace key={current.id} program={program} day={current} onProgramRefresh={(fresh) => setProgram(fresh)} />
  </div>;
}

export function NutritionProgramProgressSection() {
  const { program, elapsedSeconds } = useNutritionProgramShell();
  const goal = program.goals[0] ?? program.goal ?? null;
  const decisions = program.days.flatMap((day) => {
    const decision = day.action_details?.adaptation ?? day.action_details?.decision;
    return decision?.decision ? [{ day: day.day_number, decision: decision.decision, reason: decision.user_facing_reason ?? decision.reason ?? "" }] : [];
  });
  const elderlyContext = program.stage === "elderly" ? elderlyRecentContext(program) : null;

  return <div className="space-y-10">
    <section className="border-b border-line pb-7"><p className="eyebrow">Progres</p><h2 className="mt-2 text-4xl font-semibold tracking-[-.045em]">Program dan goal tidak dicampur menjadi satu angka.</h2><p className="mt-4 max-w-3xl text-sm leading-7 text-secondary">Program progress menunjukkan hari selesai dalam block. Goal progress memakai ukuran goal yang sebenarnya.</p></section>
    <section className="grid gap-6 md:grid-cols-2"><article className="border-t border-line pt-5"><p className="text-xs font-black uppercase tracking-[.1em] text-muted">Program progress</p><div className="mt-2 flex items-end justify-between"><h3 className="text-3xl font-semibold">{program.days_completed} / {program.duration_days}</h3><strong>{formatPercent(program.progress_percent)}%</strong></div><div className="mt-4"><ProgressBar value={program.progress_percent} label={`${formatPercent(program.progress_percent)}% program progress`} /></div></article><article className="border-t border-line pt-5"><p className="text-xs font-black uppercase tracking-[.1em] text-muted">Goal achievement</p><div className="mt-2 flex items-end justify-between"><h3 className="text-3xl font-semibold">{goal ? `${goal.actual} / ${goal.target}` : "—"}</h3><strong>{goal ? `${formatPercent(goal.progress_percentage)}%` : "—"}</strong></div><div className="mt-4"><ProgressBar value={goal?.progress_percentage ?? 0} label={goal ? `${formatPercent(goal.progress_percentage)}% goal achievement` : "Goal belum tersedia"} /></div></article></section>

    {elderlyContext ? <section className="border-y border-line py-7" aria-labelledby="elderly-progress-context-title"><p className="eyebrow">Pola harian Lansia</p><h2 id="elderly-progress-context-title" className="mt-2 text-2xl font-semibold">Input harian yang dipakai untuk adaptasi.</h2><p className="mt-3 max-w-3xl text-sm leading-6 text-secondary">Ringkasan ini berasal dari catatan yang benar-benar disimpan. Ini membantu melihat pola keterlaksanaan, bukan menilai diagnosis atau status gizi.</p><div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-5"><article className="border-t border-line pt-3"><p className="text-xs font-bold uppercase tracking-[.08em] text-muted">Hari dengan log</p><p className="mt-1 text-2xl font-semibold">{elderlyContext.loggedDays}</p></article><article className="border-t border-line pt-3"><p className="text-xs font-bold uppercase tracking-[.08em] text-muted">Nafsu makan menurun</p><p className="mt-1 text-2xl font-semibold">{elderlyContext.reducedAppetiteDays} hari</p></article><article className="border-t border-line pt-3"><p className="text-xs font-bold uppercase tracking-[.08em] text-muted">Cairan berkurang</p><p className="mt-1 text-2xl font-semibold">{elderlyContext.lowHydrationDays} hari</p></article><article className="border-t border-line pt-3"><p className="text-xs font-bold uppercase tracking-[.08em] text-muted">Ada kesulitan</p><p className="mt-1 text-2xl font-semibold">{elderlyContext.difficultDays} hari</p></article><article className="border-t border-line pt-3"><p className="text-xs font-bold uppercase tracking-[.08em] text-muted">Perlu dukungan</p><p className="mt-1 text-2xl font-semibold">{elderlyContext.assistedDays} hari</p></article></div>{elderlyContext.loggedDays ? <div className="mt-5 rounded-xl bg-background p-4 text-sm leading-6 text-secondary"><strong className="text-text">Catatan terbaru:</strong> Nafsu makan {ELDERLY_DAILY_LABELS.appetite_status[String(elderlyContext.latest.appetite_status ?? "")] ?? "—"} · Cairan {ELDERLY_DAILY_LABELS.hydration_status[String(elderlyContext.latest.hydration_status ?? "")] ?? "—"} · Bantuan makan {ELDERLY_DAILY_LABELS.eating_support[String(elderlyContext.latest.eating_support ?? "")] ?? "—"}</div> : null}</section> : null}

    <section><p className="eyebrow">14-Day Journey</p><h2 className="mt-2 text-2xl font-semibold">Timeline status, fokus, dan keputusan.</h2><div className="mt-6 space-y-0 border-y border-line">{program.days.map((day) => { const decision = day.action_details?.adaptation ?? day.action_details?.decision; const openable = day.status !== "LOCKED"; return <div key={day.id} className="grid gap-3 border-b border-line py-4 last:border-b-0 sm:grid-cols-[90px_150px_minmax(0,1fr)_150px] sm:items-center"><div className="flex items-center gap-2 font-semibold"><DayIcon day={day}/> Hari {day.day_number}</div><Badge variant={day.status === "COMPLETED" ? "success" : day.status === "MISSED" ? "warning" : day.status === "LOCKED" ? "neutral" : "info"}>{dayLabel(day)}</Badge><div><p className="font-semibold text-text">{day.focus || "Panduan adaptif"}</p>{decision?.decision ? <p className="mt-1 text-xs text-secondary">{decision.decision}: {decision.user_facing_reason ?? decision.reason}</p> : null}</div>{openable ? <Link href={`/nutrition/program/${program.id}/day/${day.day_number}`} className="text-sm font-semibold text-primary-dark">Buka hari →</Link> : day.remaining_seconds > 0 ? <div className="text-xs text-muted" aria-live="polite">{formatProgramRemaining(Math.max(0, day.remaining_seconds - elapsedSeconds))}</div> : <span className="text-xs text-muted">Terkunci</span>}</div>; })}</div></section>

    <section><div className="flex items-center gap-2 text-primary-dark"><TrendingUp size={18}/><p className="eyebrow">Adaptation Timeline</p></div><h2 className="mt-2 text-2xl font-semibold">Kenapa rencana berubah.</h2>{decisions.length ? <div className="mt-5 divide-y divide-line border-y border-line">{decisions.map((item) => <div key={`${item.day}-${item.decision}`} className="grid gap-2 py-4 sm:grid-cols-[90px_140px_1fr]"><strong>Hari {item.day}</strong><span className="text-sm font-semibold text-primary-dark">{item.decision}</span><p className="text-sm leading-6 text-secondary">{item.reason || "Tidak ada penjelasan tambahan."}</p></div>)}</div> : <p className="mt-4 text-sm text-muted">Belum ada keputusan adaptasi tersimpan.</p>}</section>
  </div>;
}

export function NutritionProgramHistorySection() {
  const { program, signedOutSnapshot } = useNutritionProgramShell();
  const [review, setReview] = useState<BlockReview | null>(null);
  const [extension, setExtension] = useState<ExtensionRecommendation | null>(null);
  const [preference, setPreference] = useState<"same_goal" | "smaller_goal" | "different_goal">("same_goal");
  const [difficulty, setDifficulty] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState("");
  const completedOrMissed = program.days.filter((day) => ["COMPLETED", "MISSED"].includes(day.status));
  const extensionHistory = program.extension_history ?? [];
  const finished = Boolean(program.completed_at || program.status === "COMPLETED" || program.status === "EXTENDED");
  const extensionFocus = String(extension?.guidance_adjustments?.focus ?? "");
  const extensionFocusReason = String(extension?.guidance_adjustments?.reason ?? "");

  useEffect(() => {
    if (!finished || signedOutSnapshot) return;
    let active = true;
    if (program.stage === "elderly") {
      getExtensionRecommendation(program.id)
        .then((value) => { if (active) setExtension(value); })
        .catch(() => { if (active) setExtension(null); });
      return () => { active = false; };
    }
    Promise.allSettled([getBlockReview(program.id), getExtensionRecommendation(program.id)]).then(([reviewResult, extensionResult]) => {
      if (!active) return;
      if (reviewResult.status === "fulfilled") setReview(reviewResult.value);
      if (extensionResult.status === "fulfilled") setExtension(extensionResult.value);
    });
    return () => { active = false; };
  }, [finished, program.id, program.stage, signedOutSnapshot]);

  async function submitExtension() {
    if (busy || signedOutSnapshot || !extension) return;
    setBusy(true);
    setActionError("");
    try {
      const suggested = (program.recommendation.suggested_goals ?? []) as Array<{ goal_key?: string }>;
      const currentGoal = program.goals[0] ?? program.goal ?? null;
      const alternativeGoal = suggested.find((item) => item.goal_key && item.goal_key !== currentGoal?.goal_key)?.goal_key;
      const next = await extendNutritionProgram(program.id, {
        preference,
        difficulty,
        goalKey: preference === "different_goal" ? alternativeGoal : undefined,
      });
      window.location.assign(`/nutrition/program/${next.id}`);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Pilihan berikutnya belum dapat disimpan.");
      setBusy(false);
    }
  }

  return <div className="space-y-10">
    <section className="border-b border-line pb-7"><div className="flex items-center gap-2 text-primary-dark"><History size={18}/><p className="eyebrow">Riwayat Program</p></div><h2 className="mt-2 text-4xl font-semibold tracking-[-.045em]">Semua keputusan yang sudah terjadi tetap dapat ditinjau.</h2><p className="mt-4 max-w-3xl text-sm leading-7 text-secondary">Hari selesai dan terlewat tidak diubah kembali. Extension tetap mempertahankan cycle sebelumnya.</p></section>

    {finished ? <section className="border-y border-line py-6"><p className="eyebrow">Overall Program Outcome</p><h3 className="mt-2 text-2xl font-semibold">Final Program Result tersedia.</h3><p className="mt-2 text-sm leading-6 text-secondary">Lihat baseline, target, actual, adaptation journey, trend, safety notes, dan next step berdasarkan data tersimpan.</p><Link href={`/nutrition/program/${program.id}/result`} className="mt-5 inline-flex min-h-11 items-center rounded-full bg-text px-5 text-sm font-semibold text-white">Buka Final Program Result <ArrowRight className="ml-2" size={16}/></Link></section> : null}

    <section><p className="eyebrow">Day history</p><h3 className="mt-2 text-2xl font-semibold">Hari yang sudah memiliki outcome.</h3>{completedOrMissed.length ? <div className="mt-5 divide-y divide-line border-y border-line">{completedOrMissed.map((day) => <Link key={day.id} href={`/nutrition/program/${program.id}/day/${day.day_number}`} className="grid gap-2 py-4 hover:bg-background/60 sm:grid-cols-[100px_140px_1fr]"><strong>Hari {day.day_number}</strong><span className={day.status === "MISSED" ? "font-semibold text-amber-700" : "font-semibold text-emerald-700"}>{dayLabel(day)}</span><span className="text-sm text-secondary">{day.focus || "Review panduan dan hasil hari ini"}</span></Link>)}</div> : <p className="mt-4 text-sm text-muted">Belum ada hari historis.</p>}</section>

    <section><p className="eyebrow">Extension cycles</p><h3 className="mt-2 text-2xl font-semibold">Cycle sebelumnya tidak di-reset.</h3>{extensionHistory.length ? <div className="mt-5 divide-y divide-line border-y border-line">{extensionHistory.map((cycle) => <div key={cycle.id} className="grid gap-2 py-4 sm:grid-cols-[120px_1fr_160px]"><strong>Cycle {cycle.cycle_number}</strong><span className="text-sm text-secondary">{cycle.days_completed}/{cycle.duration_days} hari · {formatPercent(cycle.progress_percent)}%</span><Link href={cycle.completed_at ? `/nutrition/program/${cycle.id}/result` : `/nutrition/program/${cycle.id}`} className="text-sm font-semibold text-primary-dark">Buka cycle →</Link></div>)}</div> : <p className="mt-4 text-sm text-muted">Belum ada extension cycle.</p>}</section>

    {finished && extension && !signedOutSnapshot && (program.stage === "elderly" || review?.can_extend) ? <section id="extension-review" className="scroll-mt-28 border-y border-line py-7">
      <p className="eyebrow">Extension / Reframe Review</p>
      <h3 className="mt-2 text-3xl font-semibold tracking-[-.035em]">{program.stage === "elderly" ? "Cycle berikutnya mengikuti pola yang masih perlu diperkuat." : "Goal belum harus dianggap selesai hanya karena block berakhir."}</h3>
      <p className="mt-3 max-w-3xl text-sm leading-7 text-secondary">Sisa gap: {extension.remaining_gap} {extension.unit}. Cycle sebelumnya tetap tersimpan.</p>
      {program.stage === "elderly" && extensionFocus ? <div className="mt-5 rounded-2xl border border-primary/15 bg-primary-light/30 p-4"><p className="text-xs font-black uppercase tracking-[.1em] text-primary-dark">Fokus cycle berikutnya</p><p className="mt-2 text-lg font-semibold">{extensionFocus}</p>{extensionFocusReason ? <p className="mt-2 text-xs leading-5 text-secondary">{extensionFocusReason}</p> : null}</div> : null}
      <div className="mt-5 grid gap-2 sm:grid-cols-2" role="radiogroup" aria-label="Pilihan kelanjutan program">
        {((program.stage === "elderly" ? [
          ["same_goal", "Ikuti fokus yang disarankan"],
          ["smaller_goal", "Pertahankan fokus, sederhanakan target"],
        ] : [
          ["same_goal", "Lanjutkan goal yang sama"],
          ["smaller_goal", "Perkecil goal"],
          ["different_goal", "Ubah goal"],
        ]) as Array<["same_goal" | "smaller_goal" | "different_goal", string]>).map(([value, label]) => <button key={value} type="button" role="radio" aria-checked={preference === value} onClick={() => setPreference(value)} className={`min-h-12 border px-4 py-3 text-left text-sm font-semibold ${preference === value ? "border-primary bg-primary-light text-primary-dark" : "border-line bg-white text-secondary"}`}>{label}</button>)}
      </div>
      <div className="mt-5 max-w-2xl"><Textarea label="Apa yang membuat program terasa sulit? (opsional)" value={difficulty} onChange={(event) => setDifficulty(event.target.value)} rows={3} maxLength={500} placeholder={program.stage === "elderly" ? "Contoh: cepat kenyang, sulit menyiapkan makanan, atau perlu bantuan pada waktu makan." : "Contoh: bahan sulit tersedia, anak sedang rewel, atau jadwal keluarga berubah."} /></div>
      {actionError ? <div className="mt-4"><Alert variant="error">{actionError}</Alert></div> : null}
      <div className="mt-5"><Button onClick={() => void submitExtension()} isLoading={busy} loadingLabel="Menyimpan pilihan...">Konfirmasi langkah berikutnya</Button></div>
    </section> : null}

    {signedOutSnapshot && finished ? <Alert variant="info" title="Aksi riwayat dinonaktifkan">Masuk kembali untuk Extend, Reframe, atau mengubah program. Snapshot hasil tetap terlihat.</Alert> : null}
    {program.status === "SAFETY_HOLD" ? <Alert variant="warning" title="Safety hold aktif"><span className="inline-flex items-center gap-2"><ShieldAlert size={16}/> Tanda bahaya terdeteksi. Program dihentikan dan harus dimulai kembali dari asesmen baru setelah kondisi anak dievaluasi.</span></Alert> : null}
  </div>;
}

