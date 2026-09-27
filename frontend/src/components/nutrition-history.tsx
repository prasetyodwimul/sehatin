"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowRight, Archive, BarChart3, CheckCircle2, Clock3, MoreHorizontal, Target, Trash2, X } from "lucide-react";
import { AuthGate } from "@/components/auth-gate";
import { useAuth } from "@/components/auth-provider";
import { HistoryVisualCard } from "@/components/nutrition-program-ui";
import { Alert, Button } from "@/components/ui";
import { ViewportModal } from "@/components/viewport-modal";
import { cancelNutritionProgram, deleteCancelledNutritionProgram, listNutritionHistory, type ProgramSummary } from "@/lib/nutrition-program";

type Filter = "ALL" | "ACTIVE" | "COMPLETED" | "EXTENDED" | "CANCELLED";
type StageFilter = "ALL" | "mpasi" | "toddler" | "elderly";

export function NutritionHistory({ initialPrograms }: { initialPrograms?: ProgramSummary[] }) {
  const { status } = useAuth();
  const [programs, setPrograms] = useState<ProgramSummary[]>(initialPrograms ?? []);
  const [filter, setFilter] = useState<Filter>("ALL");
  const [stageFilter, setStageFilter] = useState<StageFilter>("ALL");
  const [loading, setLoading] = useState(initialPrograms === undefined);
  const [error, setError] = useState("");
  const [authOpen, setAuthOpen] = useState(false);
  const [menuId, setMenuId] = useState<string | null>(null);
  const [cancelTarget, setCancelTarget] = useState<ProgramSummary | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<ProgramSummary | null>(null);

  useEffect(() => {
    if (initialPrograms !== undefined) { setLoading(false); return; }
    if (status !== "authenticated") { setLoading(false); return; }
    setLoading(true); setError("");
    listNutritionHistory().then(setPrograms).catch((err) => setError(err instanceof Error ? err.message : "History belum dapat dimuat.")).finally(() => setLoading(false));
  }, [initialPrograms, status]);

  const filtered = useMemo(() => programs.filter((item) => {
    const statusMatches = filter === "ALL" ? true : filter === "COMPLETED" ? item.status === "COMPLETED" : item.status === filter;
    const stageMatches = stageFilter === "ALL" ? true : item.stage === stageFilter;
    return statusMatches && stageMatches;
  }), [filter, programs, stageFilter]);


  async function confirmCancel() {
    if (!cancelTarget) return;
    setCancelling(true); setError("");
    try {
      const updated = await cancelNutritionProgram(cancelTarget.id);
      setPrograms((current) => current.map((item) => item.id === updated.id ? { ...item, ...updated, status: "CANCELLED" } : item));
      setCancelTarget(null); setMenuId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Plan belum dapat dibatalkan.");
    } finally { setCancelling(false); }
  }

  async function cancelAndDelete() {
    if (!cancelTarget) return;
    setCancelling(true); setDeleting(true); setError("");
    let cancellationCompleted = false;
    try {
      const updated = await cancelNutritionProgram(cancelTarget.id);
      cancellationCompleted = true;
      setPrograms((current) => current.map((item) => item.id === updated.id ? { ...item, ...updated, status: "CANCELLED" } : item));
      await deleteCancelledNutritionProgram(cancelTarget.id);
      setPrograms((current) => current.filter((item) => item.id !== cancelTarget.id));
      setCancelTarget(null); setMenuId(null);
    } catch (err) {
      if (cancellationCompleted) { setDeleteTarget({ ...cancelTarget, status: "CANCELLED", cancelled_at: new Date().toISOString() }); setCancelTarget(null); }
      setError(err instanceof Error ? err.message : "Plan belum dapat dibatalkan dan dihapus.");
    } finally { setCancelling(false); setDeleting(false); }
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    setDeleting(true); setError("");
    try {
      await deleteCancelledNutritionProgram(deleteTarget.id);
      setPrograms((current) => current.filter((item) => item.id !== deleteTarget.id));
      setDeleteTarget(null); setMenuId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Program belum dapat dihapus.");
    } finally { setDeleting(false); }
  }

  const activeCount = programs.filter((item) => item.status === "ACTIVE").length;

  if (status === "loading" || loading) return <div className="min-h-[420px] animate-pulse rounded-2xl border border-line bg-surface" aria-label="Memuat nutrition history" />;
  if (status === "unauthenticated") return <><section className="rounded-2xl border border-line bg-white p-8"><p className="eyebrow">Nutrition journey archive</p><h1 className="mt-4 text-4xl font-semibold tracking-[-0.04em] md:text-5xl">Login untuk melihat riwayat nutrisi yang tersimpan.</h1><p className="mt-4 max-w-2xl text-sm leading-7 text-secondary">Assessment publik tetap bisa digunakan tanpa login. History hanya berisi program yang sengaja disimpan.</p><Button className="mt-7" onClick={() => setAuthOpen(true)}>Login</Button></section><AuthGate open={authOpen} onClose={() => setAuthOpen(false)} onAuthenticated={() => window.location.reload()} /></>;

  return <div className="nutrition-enter">
    <header className="overflow-hidden rounded-3xl border border-line bg-[linear-gradient(135deg,#f4fbf8_0%,#f7fbff_55%,#fff9ed_100%)] p-6 md:p-9">
      <div className="grid gap-8 lg:grid-cols-[1fr_auto] lg:items-center">
        <div>
          <p className="eyebrow">Nutrition journey archive</p>
          <h1 className="mt-3 max-w-4xl text-4xl font-semibold leading-[1.03] tracking-[-0.055em] md:text-5xl">Riwayat yang menunjukkan perjalananmu.</h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-secondary">Lihat program yang sedang berjalan, pencapaian hari, target, dan perjalanan yang sudah selesai dalam satu tampilan.</p>
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-2xl border border-white/80 bg-white p-4 shadow-sm"><span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary-light text-primary-dark"><Target size={17}/></span><p className="mt-4 text-2xl font-black text-text">{activeCount}</p><p className="mt-1 text-[10px] font-bold uppercase tracking-[.1em] text-muted">Aktif</p></div>
          <div className="rounded-2xl border border-white/80 bg-white p-4 shadow-sm"><span className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700"><CheckCircle2 size={17}/></span><p className="mt-4 text-2xl font-black text-text">{programs.reduce((sum,item)=>sum+item.days_completed,0)}</p><p className="mt-1 text-[10px] font-bold uppercase tracking-[.1em] text-muted">Hari selesai</p></div>
          <div className="rounded-2xl border border-white/80 bg-white p-4 shadow-sm"><span className="flex h-9 w-9 items-center justify-center rounded-xl bg-amber-50 text-amber-700"><Clock3 size={17}/></span><p className="mt-4 text-2xl font-black text-text">{programs.reduce((sum,item)=>sum+item.missed_days,0)}</p><p className="mt-1 text-[10px] font-bold uppercase tracking-[.1em] text-muted">Terlewat</p></div>
        </div>
      </div>
    </header>
    {error && <div className="mt-6"><Alert variant="error">{error}</Alert></div>}

    <div className="mt-7 rounded-2xl border border-line bg-white p-4 md:p-5">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-4">
          <div><p className="mb-2 flex items-center gap-2 text-[11px] font-black uppercase tracking-[.1em] text-muted"><BarChart3 size={13}/> Kategori</p><div className="flex flex-wrap gap-2" role="group" aria-label="Filter kategori nutrition history">{([{ value: "ALL", label: "Semua" }, { value: "mpasi", label: "MPASI" }, { value: "toddler", label: "Toddler" }, { value: "elderly", label: "Lansia" }] as Array<{ value: StageFilter; label: string }>).map((item)=><button key={item.value} type="button" aria-pressed={stageFilter===item.value} onClick={()=>setStageFilter(item.value)} className={`min-h-10 rounded-full px-4 text-xs font-bold transition-colors ${stageFilter===item.value?"bg-primary text-white":"border border-line bg-white text-secondary hover:border-primary/30"}`}>{item.label}</button>)}</div></div>
          <div><p className="mb-2 text-[11px] font-black uppercase tracking-[.1em] text-muted">Status program</p><div className="flex flex-wrap gap-2" role="group" aria-label="Filter status nutrition history">{(["ALL","ACTIVE","COMPLETED","EXTENDED","CANCELLED"] as Filter[]).map((item)=><button key={item} type="button" aria-pressed={filter===item} onClick={()=>setFilter(item)} className={`min-h-10 rounded-full px-4 text-xs font-bold transition-colors ${filter===item?"bg-text text-white":"border border-line bg-white text-secondary hover:border-primary/30"}`}>{item === "ALL" ? "Semua" : item === "ACTIVE" ? "Aktif" : item === "COMPLETED" ? "Selesai" : item === "EXTENDED" ? "Diperpanjang" : "Dibatalkan"}</button>)}</div></div>
        </div>
        <Link href="/nutrition" className="inline-flex min-h-10 items-center justify-center rounded-full bg-primary-light px-4 text-sm font-semibold text-primary-dark">Mulai assessment baru <ArrowRight size={15} className="ml-1"/></Link>
      </div>
    </div>
    {!filtered.length ? <section className="mt-8 rounded-2xl border border-dashed border-line bg-white p-10 text-center"><span className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-primary-light text-primary-dark"><Archive size={24}/></span><h2 className="mt-5 text-2xl font-semibold">Belum ada perjalanan pada filter ini.</h2><p className="mx-auto mt-3 max-w-xl text-sm leading-7 text-secondary">Program yang kamu simpan akan muncul di sini lengkap dengan progress, goal, status, dan evaluation.</p><Link href="/nutrition" className="mt-6 inline-flex min-h-11 items-center rounded-full bg-text px-5 text-sm font-semibold text-white">Start Nutrition Assessment <ArrowRight className="ml-2" size={16}/></Link></section> : <section className="mt-6 grid gap-5 md:grid-cols-2">{filtered.map((program)=><div key={program.id} className="relative"><HistoryVisualCard program={program}/>{["ACTIVE","CANCELLED"].includes(program.status) && <div className="absolute right-5 top-5"><button type="button" onClick={()=>setMenuId((value)=>value===program.id?null:program.id)} className="flex h-9 w-9 items-center justify-center rounded-full border border-line bg-white shadow-sm" aria-label={`More actions for ${program.title}`}><MoreHorizontal size={17}/></button>{menuId===program.id && <div role="menu" className="absolute right-0 top-11 z-20 w-48 rounded-xl border border-line bg-white p-2 shadow-xl">{program.status === "ACTIVE" ? <button role="menuitem" type="button" onClick={()=>setCancelTarget(program)} className="flex min-h-10 w-full items-center rounded-lg px-3 text-left text-sm font-semibold text-error hover:bg-red-50">Cancel Plan</button> : <button role="menuitem" type="button" onClick={()=>setDeleteTarget(program)} className="flex min-h-10 w-full items-center gap-2 rounded-lg px-3 text-left text-sm font-semibold text-error hover:bg-red-50"><Trash2 size={15}/> Delete Program</button>}</div>}</div>}</div>)}</section>}

    {cancelTarget && <ViewportModal onClose={()=>setCancelTarget(null)} labelledBy="cancel-history-plan"><div className="flex items-start justify-between gap-4"><div><p className="eyebrow">Cancel plan</p><h2 id="cancel-history-plan" className="mt-3 text-3xl font-semibold tracking-[-0.04em]">Batalkan guided nutrition plan?</h2></div><button type="button" onClick={()=>setCancelTarget(null)} className="flex h-11 w-11 items-center justify-center rounded-full border border-line" aria-label="Tutup"><X size={18}/></button></div><p className="mt-4 text-sm leading-7 text-secondary">Cancel Only mempertahankan progress di history. Cancel & Delete membatalkan lalu menghapus program secara permanen.</p><div className="mt-7 grid gap-3"><Button variant="secondary" onClick={()=>setCancelTarget(null)}>Keep Plan</Button><Button variant="secondary" onClick={()=>void confirmCancel()} isLoading={cancelling && !deleting} loadingLabel="Cancelling...">Cancel Only · Keep History</Button><Button onClick={()=>void cancelAndDelete()} isLoading={deleting} loadingLabel="Cancelling & deleting..."><Trash2 size={16}/> Cancel & Delete</Button></div></ViewportModal>}
    {deleteTarget && <ViewportModal onClose={()=>setDeleteTarget(null)} labelledBy="delete-history-plan"><div className="flex items-start justify-between gap-4"><div><p className="eyebrow">Delete cancelled plan</p><h2 id="delete-history-plan" className="mt-3 text-3xl font-semibold tracking-[-0.04em]">Hapus program dari history?</h2></div><button type="button" onClick={()=>setDeleteTarget(null)} className="flex h-11 w-11 items-center justify-center rounded-full border border-line" aria-label="Tutup"><X size={18}/></button></div><p className="mt-4 text-sm leading-7 text-secondary">Program ini sudah CANCELLED. Delete akan menghapus days, checklist, progress, dan evaluation program secara permanen.</p><div className="mt-7 flex flex-col gap-3 sm:flex-row sm:justify-end"><Button variant="secondary" onClick={()=>setDeleteTarget(null)}>Keep History</Button><Button onClick={()=>void confirmDelete()} isLoading={deleting} loadingLabel="Deleting..."><Trash2 size={16}/> Delete Program</Button></div></ViewportModal>}
  </div>;
}
