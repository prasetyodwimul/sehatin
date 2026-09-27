import Link from "next/link";
import { StageCompanionIllustration } from "@/components/nutrition-visuals";
import type { NutritionStage } from "@/lib/nutrition";

const COPY: Record<NutritionStage,{eyebrow:string;title:string;body:string}> = {
  mpasi:{eyebrow:"Stage-based nutrition guidance",title:"Assessment MPASI 6–23 bulan",body:"Isi data dasar dan konteks makan. Sistem memvalidasi pengukuran, pola pemberian makan, alergi, dan batas keamanan sebelum membuat panduan."},
  toddler:{eyebrow:"Healthy eating habit guidance",title:"Assessment Toddler 24–59 bulan",body:"Fokus pada pola makan, nafsu makan, alergi, dan rutinitas keluarga—tanpa membuat diagnosis pertumbuhan."},
  elderly:{eyebrow:"Personalized educational guidance",title:"Assessment Nutrisi Lansia 60+",body:"Mempertimbangkan usia, aktivitas, kemampuan mengunyah/menelan, alergi, dan konteks medis untuk menentukan batas personalisasi yang aman."},
};
export function NutritionAssessmentHero({stage}:{stage:NutritionStage}){const c=COPY[stage];return <section className="mb-8 overflow-hidden rounded-2xl border border-line bg-[linear-gradient(135deg,#f7fbf9,#f5fbff_55%,#fff8ea)]"><div className="grid gap-5 md:grid-cols-[1fr_300px] md:items-center"><div className="p-7 md:p-9"><Link href="/nutrition" className="text-xs font-bold uppercase tracking-[.12em] text-muted hover:text-primary-dark">← Nutrition</Link><p className="eyebrow mt-6">{c.eyebrow}</p><h1 className="mt-3 max-w-4xl text-4xl font-semibold leading-[1.02] tracking-[-0.045em] sm:text-5xl">{c.title}</h1><p className="mt-4 max-w-2xl text-sm leading-7 text-secondary">{c.body}</p></div><div className="p-4"><StageCompanionIllustration stage={stage} compact/></div></div></section>}
