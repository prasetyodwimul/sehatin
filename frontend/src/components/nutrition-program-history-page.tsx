"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { MoreHorizontal, X } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { useNutritionProgramShell } from "@/components/nutrition-program-shell";
import { Alert, Button, ProgressBar } from "@/components/ui";
import { ViewportModal } from "@/components/viewport-modal";
import { cancelNutritionProgram, formatPercent, listNutritionHistory, type ProgramSummary } from "@/lib/nutrition-program";

function rootId(program: ProgramSummary, map: Map<string, ProgramSummary>) {
  let current = program;
  const seen = new Set<string>();
  while (current.parent_program_id && map.has(current.parent_program_id) && !seen.has(current.id)) { seen.add(current.id); current = map.get(current.parent_program_id)!; }
  return current.id;
}

function destination(program: ProgramSummary) {
  if (program.status === "COMPLETED" || program.status === "EXTENDED" || program.completed_at) return `/nutrition/program/${program.id}/result`;
  if (program.status === "CANCELLED") return `/nutrition/history/${program.id}`;
  return `/nutrition/program/${program.id}`;
}

export function NutritionProgramHistoryPage() {
  const router = useRouter();
  const { status } = useAuth();
  const { program, loading, readOnly, refreshProgram } = useNutritionProgramShell();
  const [programs, setPrograms] = useState<ProgramSummary[]>([]);
  const [error, setError] = useState("");
  const programId = program?.id;
  const [menuId, setMenuId] = useState<string | null>(null);
  const [cancelTarget, setCancelTarget] = useState<ProgramSummary | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!programId || status !== "authenticated") return;
    let active = true;
    listNutritionHistory().then((rows) => { if (active) setPrograms(rows); }).catch((err) => { if (active) setError(err instanceof Error ? err.message : "Riwayat belum dapat dimuat."); });
    return () => { active = false; };
  }, [programId, status]);

  const family = useMemo(() => {
    if (!program) return [];
    const rows = programs.length ? programs : [program];
    const map = new Map(rows.map((item) => [item.id, item]));
    const targetRoot = rootId(program, map);
    return rows.filter((item) => rootId(item, map) === targetRoot).sort((a, b) => a.cycle_number - b.cycle_number);
  }, [program, programs]);

  async function confirmCancel() {
    if (!cancelTarget) return;
    setBusy(true); setError("");
    try {
      const updated = await cancelNutritionProgram(cancelTarget.id);
      setPrograms((current) => current.map((item) => item.id === updated.id ? { ...item, ...updated, status: "CANCELLED" } : item));
      setCancelTarget(null); setMenuId(null); await refreshProgram();
    } catch (err) { setError(err instanceof Error ? err.message : "Program belum dapat dibatalkan."); }
    finally { setBusy(false); }
  }

  if (loading) return <div className="min-h-[520px] animate-pulse rounded-[28px] border border-line bg-white" aria-label="Memuat riwayat program" />;
  if (!program) return <Alert variant="warning">Program belum dapat dimuat.</Alert>;

  return <div>
    <p className="eyebrow">Riwayat Program</p><h2 className="mt-2 text-4xl font-semibold tracking-[-.045em]">Cycle tetap terhubung, progress lama tidak dihapus.</h2><p className="mt-4 max-w-3xl text-sm leading-7 text-secondary">Klik seluruh kartu untuk membuka program detail atau Final Program Result. Cycle extension tetap mempertahankan hubungan dengan cycle sebelumnya.</p>
    {error ? <div className="mt-6"><Alert variant="error">{error}</Alert></div> : null}

    <section className="mt-8 space-y-4" aria-label="Program cycle history">{family.map((item) => {
      const goal = item.goal;
      const href = destination(item);
      const clickable = !readOnly;
      const card = <div className="p-5 sm:p-6"><div className="flex flex-wrap items-start justify-between gap-4 pr-10"><div><p className="text-xs font-black uppercase tracking-[.1em] text-primary-dark">{item.stage} · Cycle {item.cycle_number}</p><h3 className="mt-2 text-2xl font-semibold tracking-[-.03em]">{item.title}</h3></div><span className="text-xs font-bold uppercase tracking-[.08em] text-secondary">{item.status}</span></div><div className="mt-6 grid gap-5 sm:grid-cols-2"><div><div className="flex justify-between text-xs font-bold"><span>PROGRAM</span><span>{formatPercent(item.progress_percent)}%</span></div><div className="mt-2"><ProgressBar value={item.progress_percent} label={`${item.days_completed} dari ${item.duration_days} hari selesai`} /></div><p className="mt-2 text-xs text-muted">{item.days_completed}/{item.duration_days} hari · {item.missed_days} terlewat</p></div><div><div className="flex justify-between text-xs font-bold"><span>GOAL</span><span>{goal ? `${formatPercent(goal.progress_percentage)}%` : "—"}</span></div>{goal ? <><div className="mt-2"><ProgressBar value={goal.progress_percentage} label={`${formatPercent(goal.progress_percentage)}% goal achievement`} /></div><p className="mt-2 text-xs text-muted">{goal.actual}/{goal.target} {goal.unit}</p></> : <p className="mt-2 text-xs text-muted">Goal belum tersedia.</p>}</div></div></div>;
      return <article key={item.id} className="relative min-w-0 overflow-visible rounded-[28px] border border-line bg-white transition hover:border-primary/30 hover:shadow-[0_12px_40px_rgba(21,67,55,.06)]">{clickable ? <div role="link" tabIndex={0} aria-label={`Buka ${item.title}, cycle ${item.cycle_number}`} onClick={() => router.push(href)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); router.push(href); } }} className="cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2">{card}</div> : <div aria-disabled="true" className="opacity-75">{card}</div>}{status === "authenticated" && item.status === "ACTIVE" ? <div className="absolute right-4 top-4"><button type="button" aria-label={`Aksi ${item.title}`} onClick={() => setMenuId((value) => value === item.id ? null : item.id)} className="flex h-10 w-10 items-center justify-center rounded-full border border-line bg-white"><MoreHorizontal size={17}/></button>{menuId === item.id ? <div role="menu" className="absolute right-0 top-11 z-20 w-44 rounded-2xl border border-line bg-white p-2 shadow-xl"><button role="menuitem" type="button" onClick={() => setCancelTarget(item)} className="flex min-h-10 w-full items-center rounded-xl px-3 text-left text-sm font-semibold text-error hover:bg-red-50">Cancel Program</button></div> : null}</div> : null}</article>;
    })}</section>

    {cancelTarget ? <ViewportModal onClose={() => setCancelTarget(null)} labelledBy="cancel-shell-program"><div className="flex items-start justify-between gap-4"><div><p className="eyebrow">Cancel Program</p><h2 id="cancel-shell-program" className="mt-2 text-3xl font-semibold">Cancel this guided nutrition program?</h2></div><button type="button" onClick={() => setCancelTarget(null)} className="flex h-11 w-11 items-center justify-center rounded-full border border-line" aria-label="Tutup"><X size={18}/></button></div><p className="mt-4 text-sm leading-7 text-secondary">Your progress will remain in history. Program akan berubah menjadi CANCELLED dan tidak menampilkan Continue CTA.</p><div className="mt-7 flex flex-col gap-3 sm:flex-row sm:justify-end"><Button variant="secondary" onClick={() => setCancelTarget(null)}>Keep Program</Button><Button onClick={() => void confirmCancel()} isLoading={busy} loadingLabel="Cancelling...">Cancel Program</Button></div></ViewportModal> : null}
  </div>;
}
