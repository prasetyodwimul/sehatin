"use client";

import { LockKeyhole } from "lucide-react";
import { NutritionProgramDailyWorkspace } from "@/components/nutrition-program-daily-workspace";
import { ProgramCountdown } from "@/components/program-countdown";
import { Alert } from "@/components/ui";
import { useNutritionProgramShell } from "@/components/nutrition-program-shell";

export function NutritionProgramToday() {
  const { program, loading, readOnly, refreshProgram, syncProgram, elapsedSeconds } = useNutritionProgramShell();
  if (loading) return <div className="min-h-[520px] animate-pulse rounded-[28px] border border-line bg-white" aria-label="Memuat hari ini" />;
  if (!program) return <Alert variant="warning" title="Program belum dapat dimuat">Masuk untuk membuka daily guidance yang tersimpan.</Alert>;

  const day = program.days.find((item) => item.day_number === program.current_day && ["AVAILABLE", "IN_PROGRESS"].includes(item.status))
    ?? program.days.find((item) => ["AVAILABLE", "IN_PROGRESS"].includes(item.status))
    ?? program.days.find((item) => item.day_number === program.current_day)
    ?? program.days[0];
  if (!day) return <Alert variant="error">Hari program tidak tersedia.</Alert>;

  if (readOnly) return <section className="border-y border-line py-8"><p className="eyebrow">Hari {day.day_number} dari {program.duration_days}</p><h2 className="mt-2 text-3xl font-semibold">Daily guidance tersimpan dalam mode read-only.</h2><p className="mt-4 max-w-2xl text-sm leading-7 text-secondary">Masuk kembali untuk mengubah checklist, mengirim daily log, atau menyimpan progress.</p></section>;

  if (day.status === "LOCKED") return <section className="border-y border-line py-12 text-center"><LockKeyhole className="mx-auto text-primary-dark"/><p className="eyebrow mt-5">Hari {day.day_number} · Locked</p><h2 className="mt-2 text-3xl font-semibold">Panduan berikutnya belum tersedia.</h2><p className="mt-4 text-sm text-secondary">Unlocks in <ProgramCountdown seconds={day.remaining_seconds} syncElapsedSeconds={elapsedSeconds} onExpire={() => { void refreshProgram(); }} /></p></section>;

  return <>
    <div className="mb-7"><p className="eyebrow">Day {day.day_number} of {program.duration_days}</p><h2 className="mt-2 text-3xl font-semibold tracking-[-.035em]">{day.focus}</h2><p className="mt-3 text-sm leading-7 text-secondary">Hari Ini mengikuti state terbaru dari backend. Ketika countdown mencapai 0, shell akan refetch dan current day berpindah sesuai aturan server.</p></div>
    <NutritionProgramDailyWorkspace program={program} day={day} onProgramRefresh={syncProgram} />
  </>;
}
