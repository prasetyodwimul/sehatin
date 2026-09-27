"use client";

import Link from "next/link";
import { ArrowLeft, Clock3, LockKeyhole } from "lucide-react";
import { NutritionProgramDailyWorkspace } from "@/components/nutrition-program-daily-workspace";
import { ProgramCountdown } from "@/components/program-countdown";
import { useNutritionProgramShell } from "@/components/nutrition-program-shell";
import { Alert } from "@/components/ui";

export function NutritionProgramDayPage({ dayNumber }: { dayNumber: number }) {
  const { program, readOnly, refreshProgram, syncProgram, elapsedSeconds } = useNutritionProgramShell();
  const day = program.days.find((item) => item.day_number === dayNumber);

  if (!day) return <Alert variant="error" title="Hari tidak tersedia">Hari program ini tidak ditemukan pada state terbaru.</Alert>;

  // Defense-in-depth: a future day must never render editable controls.
  // Backend current_day/status remain the authority; this protects the UI from
  // stale/mismatched `locked` booleans or direct URL navigation.
  const lockedByBackend = day.status === "LOCKED" || day.status === "MISSED" || day.locked || day.day_number > program.current_day;

  if (lockedByBackend) {
    return <section className="relative min-h-[470px] overflow-hidden rounded-[28px] border border-line bg-white" aria-labelledby="locked-day-title">
      <div aria-hidden="true" className="absolute inset-0 select-none overflow-hidden opacity-45 blur-[3px]">
        <div className="space-y-8 p-7 sm:p-10">
          <div className="h-3 w-28 rounded-full bg-primary-light" />
          <div className="space-y-3"><div className="h-7 w-3/5 rounded-lg bg-slate-200"/><div className="h-3 w-4/5 rounded-full bg-slate-100"/><div className="h-3 w-2/3 rounded-full bg-slate-100"/></div>
          <div className="grid gap-4 sm:grid-cols-2"><div className="h-28 rounded-2xl border border-line bg-background"/><div className="h-28 rounded-2xl border border-line bg-background"/></div>
          <div className="h-36 rounded-2xl border border-line bg-background" />
        </div>
      </div>
      <div className="absolute inset-0 bg-white/74 backdrop-blur-[1px]" aria-hidden="true" />
      <div className="relative z-10 flex min-h-[470px] items-center justify-center p-5 sm:p-8">
        <div className="w-full max-w-md text-center">
          <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-full border border-line bg-white text-primary-dark shadow-sm"><LockKeyhole size={24}/></span>
          <p className="eyebrow mt-5">Hari {day.day_number}</p>
          <h2 id="locked-day-title" className="mt-2 text-3xl font-semibold tracking-[-.035em]">{day.status === "MISSED" ? "Hari sudah terkunci" : "Belum tersedia"}</h2>
          <p className="mt-3 text-sm leading-7 text-secondary">{day.status === "MISSED" ? "Progress harian ditutup tepat pukul 00.00. Hari ini sudah melewati batas waktu dan tidak dapat diubah atau dibuka kembali." : "Panduan berikutnya akan terbuka sesuai jadwal program. Aktivitas hari ini tetap tersembunyi sampai backend membukanya."}</p>
          {day.remaining_seconds > 0 ? <div className="mx-auto mt-5 inline-flex items-center gap-2 rounded-full border border-line bg-white px-4 py-2 text-sm font-semibold text-primary-dark" aria-live="polite"><Clock3 size={16}/><span>Tersedia dalam <ProgramCountdown seconds={day.remaining_seconds} syncElapsedSeconds={elapsedSeconds} onExpire={() => { void refreshProgram(); }} /></span></div> : null}
          <div className="mt-7"><Link href={`/nutrition/program/${program.id}`} className="inline-flex min-h-11 items-center justify-center rounded-full border border-line bg-white px-5 text-sm font-semibold text-primary-dark transition hover:border-primary/40 hover:bg-primary-light/20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"><ArrowLeft className="mr-2" size={16}/>Kembali ke Program</Link></div>
        </div>
      </div>
    </section>;
  }

  if (readOnly && day.status !== "MISSED") {
    return <section className="rounded-[28px] border border-line bg-white p-8"><p className="eyebrow">Hari {day.day_number} dari {program.duration_days}</p><h2 className="mt-2 text-3xl font-semibold">Review hari program</h2><p className="mt-4 max-w-2xl text-sm leading-7 text-secondary">Data yang sudah termuat hanya dapat ditinjau. Masuk kembali untuk melakukan perubahan.</p><div className="mt-8"><NutritionProgramDailyWorkspace program={{ ...program, status: "COMPLETED" }} day={{ ...day, status: day.status === "COMPLETED" ? "COMPLETED" : "MISSED" }} onProgramRefresh={syncProgram} /></div></section>;
  }

  return <div><div className="mb-7"><p className="eyebrow">Hari {day.day_number} dari {program.duration_days}</p><h2 className="mt-2 text-3xl font-semibold tracking-[-.035em]">{day.status === "COMPLETED" ? "Review hasil hari ini" : day.focus}</h2><p className="mt-3 text-sm leading-7 text-secondary">{day.status === "COMPLETED" ? "Hari ini sudah selesai. Checklist, log, dan hasil tetap tersedia sebagai riwayat." : "Panduan hari ini mengikuti state terbaru dari backend."}</p></div><NutritionProgramDailyWorkspace program={program} day={day} onProgramRefresh={syncProgram} /></div>;
}
