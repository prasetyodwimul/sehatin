"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowRight, CheckCircle2, Clock3, Target } from "lucide-react";
import { AuthGate } from "@/components/auth-gate";
import { useAuth } from "@/components/auth-provider";
import { Alert, Badge, Button, ProgressBar } from "@/components/ui";
import { listNutritionPrograms, type ProgramSummary } from "@/lib/nutrition-program";
import { ProgressRing } from "@/components/nutrition-program-ui";

function ProgramRow({ program }: { program: ProgramSummary }) {
  const completed = Boolean(program.completed_at) || program.status !== "ACTIVE";
  const href = completed ? `/nutrition/program/${program.id}/history` : `/nutrition/program/${program.id}`;
  const statusLabel = program.status === "ACTIVE" ? "Sedang berjalan" : program.status === "COMPLETED" ? "Selesai" : program.status === "EXTENDED" ? "Diperpanjang" : "Dibatalkan";
  return (
    <Link href={href} className="group block rounded-2xl border border-line bg-white p-5 transition-all hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-[0_16px_45px_rgba(21,67,55,.07)]">
      <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
        <ProgressRing value={program.progress_percent} size={78} label={`Progress ${program.title}`} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-primary-light px-3 py-1 text-[10px] font-black uppercase tracking-[.1em] text-primary-dark">{program.stage}</span>
            <span className="text-xs font-semibold text-muted">{statusLabel}</span>
          </div>
          <h3 className="mt-3 text-xl font-semibold tracking-[-0.03em] text-text">{program.title}</h3>
          <p className="mt-1 text-xs text-secondary">Hari {Math.min(program.current_day, program.duration_days)} dari {program.duration_days} · {program.days_completed} hari selesai · {program.missed_days} terlewat</p>
          <div className="mt-4 h-2 overflow-hidden rounded-full bg-background"><div className="h-full rounded-full bg-primary" style={{ width: `${Math.max(0, Math.min(100, program.progress_percent))}%` }} /></div>
        </div>
        <span className="inline-flex min-h-10 shrink-0 items-center gap-1 rounded-full border border-primary/20 px-4 text-sm font-semibold text-primary-dark">{completed ? "Lihat" : "Lanjut"}<ArrowRight size={15} className="transition-transform group-hover:translate-x-0.5" /></span>
      </div>
    </Link>
  );
}

function SummaryStat({ icon: Icon, value, label }: { icon: typeof Target; value: string | number; label: string }) {
  return <div className="rounded-2xl border border-line bg-white p-4"><span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary-light text-primary-dark"><Icon size={17} /></span><p className="mt-4 text-2xl font-black tracking-[-0.04em] text-text">{value}</p><p className="mt-1 text-[10px] font-bold uppercase tracking-[.1em] text-muted">{label}</p></div>;
}

export function NutritionProgramHome() {
  const { status, user } = useAuth();
  const [programs, setPrograms] = useState<ProgramSummary[]>([]);
  const [loadingPrograms, setLoadingPrograms] = useState(false);
  const [error, setError] = useState("");
  const [authOpen, setAuthOpen] = useState(false);

  const loadPrograms = useCallback(async () => {
    setLoadingPrograms(true);
    setError("");
    try {
      setPrograms(await listNutritionPrograms());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Program belum dapat dimuat.");
    } finally {
      setLoadingPrograms(false);
    }
  }, []);

  useEffect(() => {
    if (status === "authenticated") void loadPrograms();
    if (status === "unauthenticated") setPrograms([]);
  }, [loadPrograms, status, user?.id]);

  const activePrograms = useMemo(() => programs.filter((item) => item.status === "ACTIVE" && !item.completed_at), [programs]);
  const completedPrograms = useMemo(() => programs.filter((item) => item.status !== "ACTIVE" || Boolean(item.completed_at)), [programs]);

  if (status === "loading") {
    return <div className="min-h-[300px] animate-pulse border-y border-line bg-surface" aria-label="Memeriksa sesi" />;
  }

  if (status === "unauthenticated") {
    return (
      <>
        <div className="border-y border-line py-12">
          <p className="eyebrow">Continue My Program</p>
          <h2 className="mt-4 max-w-3xl text-4xl font-semibold tracking-[-0.04em]">Login to continue your saved nutrition program</h2>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-secondary">Assessment dan rekomendasi publik tetap bisa digunakan tanpa login. Masuk hanya untuk membuka program yang sebelumnya sengaja kamu simpan.</p>
          <Button className="mt-7" size="lg" onClick={() => setAuthOpen(true)}>Login <ArrowRight size={17} /></Button>
        </div>
        <AuthGate open={authOpen} onClose={() => setAuthOpen(false)} onAuthenticated={async () => { setAuthOpen(false); await loadPrograms(); }} />
      </>
    );
  }

  const activeProgram = activePrograms[0];
  const totalCompletedDays = programs.reduce((sum, item) => sum + item.days_completed, 0);
  const totalMissedDays = programs.reduce((sum, item) => sum + item.missed_days, 0);

  return (
    <div>
      <section className="overflow-hidden rounded-3xl border border-line bg-[linear-gradient(135deg,#f4fbf8_0%,#f7fbff_55%,#fff9ed_100%)] p-6 md:p-9">
        <div className="grid gap-8 lg:grid-cols-[1.15fr_.85fr] lg:items-center">
          <div>
            <p className="eyebrow">Guided Nutrition</p>
            <h2 className="mt-3 max-w-3xl text-4xl font-semibold leading-[1.02] tracking-[-0.055em] md:text-5xl">Perjalanan nutrisimu, lebih mudah dilihat.</h2>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-secondary">Pantau program yang sedang berjalan, lihat pencapaianmu, dan lanjutkan dari hari terakhir tanpa harus mencari-cari.</p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link href="/nutrition/history" className="inline-flex min-h-11 items-center rounded-full border border-primary/20 bg-white px-5 text-sm font-semibold text-primary-dark">Lihat semua riwayat <ArrowRight size={15} className="ml-2" /></Link>
              <Link href="/profile" className="inline-flex min-h-11 items-center rounded-full border border-line bg-white/70 px-5 text-sm font-semibold text-secondary">Profil</Link>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <SummaryStat icon={Target} value={activePrograms.length} label="Aktif" />
            <SummaryStat icon={CheckCircle2} value={totalCompletedDays} label="Hari selesai" />
            <SummaryStat icon={Clock3} value={totalMissedDays} label="Hari terlewat" />
          </div>
        </div>
      </section>

      {error && <div className="mt-6"><Alert variant="error">{error}</Alert></div>}
      {loadingPrograms ? (
        <div className="mt-8 grid gap-4 md:grid-cols-2"><div className="h-52 animate-pulse rounded-2xl bg-surface" /><div className="h-52 animate-pulse rounded-2xl bg-surface" /></div>
      ) : programs.length === 0 ? (
        <section className="mt-8 rounded-2xl border border-dashed border-line bg-white p-10 text-center">
          <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-primary-light text-primary-dark"><Target size={25} /></span>
          <h3 className="mt-5 text-2xl font-semibold">Belum ada program tersimpan.</h3>
          <p className="mx-auto mt-3 max-w-xl text-sm leading-7 text-secondary">Mulai dari assessment nutrisi, lalu simpan rekomendasinya sebagai program yang bisa kamu ikuti hari demi hari.</p>
          <Link href="/nutrition" className="mt-6 inline-flex min-h-11 items-center rounded-full bg-primary px-5 text-sm font-semibold text-white">Mulai assessment <ArrowRight size={16} className="ml-2" /></Link>
        </section>
      ) : (
        <>
          <section className="mt-9">
            <div className="mb-4 flex items-end justify-between gap-4"><div><p className="eyebrow">Program aktif</p><h3 className="mt-2 text-2xl font-semibold tracking-[-0.03em]">Lanjutkan dari sini.</h3></div><span className="text-xs font-semibold text-muted">{activePrograms.length} program aktif</span></div>
            {activeProgram ? (
              <Link href={`/nutrition/program/${activeProgram.id}`} className="group block overflow-hidden rounded-3xl border border-primary/15 bg-white shadow-[0_18px_55px_rgba(21,67,55,.07)] transition-all hover:-translate-y-0.5 hover:shadow-[0_24px_65px_rgba(21,67,55,.1)]">
                <div className="h-1.5 bg-[linear-gradient(90deg,#138b7d,#79c8ae,#f2c568)]" />
                <div className="grid gap-7 p-6 md:grid-cols-[auto_1fr] md:p-8">
                  <ProgressRing value={activeProgram.progress_percent} size={142} label="Progress program aktif" />
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2"><span className="rounded-full bg-primary-light px-3 py-1 text-[10px] font-black uppercase tracking-[.1em] text-primary-dark">{activeProgram.stage}</span><span className="rounded-full bg-emerald-50 px-3 py-1 text-[10px] font-bold text-emerald-700">Sedang berjalan</span></div>
                    <h3 className="mt-4 text-2xl font-semibold tracking-[-0.035em] md:text-3xl">{activeProgram.title}</h3>
                    <p className="mt-2 text-sm text-secondary">Hari {Math.min(activeProgram.current_day, activeProgram.duration_days)} dari {activeProgram.duration_days}. Kamu sudah menyelesaikan {activeProgram.days_completed} hari.</p>
                    <div className="mt-5 grid grid-cols-3 gap-2">
                      <div className="rounded-xl bg-background p-3"><p className="text-xl font-black">{activeProgram.days_completed}</p><p className="text-[10px] font-bold uppercase tracking-[.08em] text-muted">Selesai</p></div>
                      <div className="rounded-xl bg-amber-50 p-3"><p className="text-xl font-black text-amber-700">{activeProgram.missed_days}</p><p className="text-[10px] font-bold uppercase tracking-[.08em] text-amber-700">Terlewat</p></div>
                      <div className="rounded-xl bg-primary-light p-3"><p className="text-xl font-black text-primary-dark">{Math.max(0, activeProgram.duration_days - activeProgram.current_day)}</p><p className="text-[10px] font-bold uppercase tracking-[.08em] text-primary-dark">Tersisa</p></div>
                    </div>
                    <div className="mt-5 inline-flex min-h-11 items-center rounded-full bg-primary px-5 text-sm font-semibold text-white">Lanjutkan program <ArrowRight size={16} className="ml-2 transition-transform group-hover:translate-x-1" /></div>
                  </div>
                </div>
              </Link>
            ) : (
              <div className="rounded-2xl border border-line bg-white p-7"><div className="flex items-center gap-3 text-secondary"><CheckCircle2 className="text-primary" size={20} /><span>Tidak ada program aktif saat ini.</span></div><Link href="/nutrition" className="mt-4 inline-flex text-sm font-semibold text-primary-dark">Mulai program baru <ArrowRight size={15} className="ml-1" /></Link></div>
            )}
          </section>

          {completedPrograms.length > 0 && <section className="mt-12">
            <div className="mb-4 flex items-end justify-between gap-4"><div><p className="eyebrow">Riwayat program</p><h3 className="mt-2 text-2xl font-semibold tracking-[-0.03em]">Perjalanan sebelumnya.</h3></div><Link href="/nutrition/history" className="text-sm font-semibold text-primary-dark">Lihat semua →</Link></div>
            <div className="grid gap-4 md:grid-cols-2">{completedPrograms.slice(0, 4).map((program) => <ProgramRow key={program.id} program={program} />)}</div>
          </section>}
        </>
      )}
    </div>
  );
}
