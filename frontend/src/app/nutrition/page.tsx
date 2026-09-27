"use client";

import Link from "next/link";
import { ArrowRight, CheckCircle2, ShieldCheck, Sparkles } from "lucide-react";
import { Container } from "@/components/layout";
import { StageCompanionIllustration } from "@/components/nutrition-visuals";
import { Reveal } from "@/components/motion";
import { useAuth } from "@/components/auth-provider";

const CATEGORIES = [
  {
    stage: "mpasi",
    index: "01",
    title: "MPASI",
    range: "6–23 bulan",
    description: "Frekuensi makan, tekstur, keragaman pangan, dan responsive feeding sesuai tahap usia.",
    href: "/nutrition/mpasi",
    note: "Fokus: perkembangan makan",
  },
  {
    stage: "toddler",
    index: "02",
    title: "Toddler",
    range: "24–59 bulan",
    description: "Kebiasaan makan, variasi pangan, nafsu makan, alergi, dan rutinitas keluarga.",
    href: "/nutrition/toddler",
    note: "Fokus: healthy eating habits",
  },
  {
    stage: "elderly",
    index: "03",
    title: "Lansia",
    range: "60+ tahun",
    description: "Kebutuhan makan, aktivitas, kemampuan mengunyah/menelan, dan safety boundary yang relevan.",
    href: "/nutrition/elderly",
    note: "Fokus: kebutuhan & kemampuan makan",
  },
];

export default function NutritionHomePage() {
  const { status, user } = useAuth();
  const showSavedProgram = status === "authenticated" && Boolean(user);

  return (
    <div className="nutrition-program-mobile-safe nutrition-home-mobile-safe">
      <section className="border-b border-line bg-[linear-gradient(135deg,#f7fbf9,#f5fbff_55%,#fff8ea)]">
        <Container className="py-14 md:py-20">
          <Reveal>
            <div className="grid gap-8 lg:grid-cols-[1.15fr_.85fr] lg:items-center">
              <div>
                <div className="inline-flex items-center gap-2 rounded-full bg-white px-4 py-2 text-xs font-black uppercase tracking-[.12em] text-primary-dark shadow-sm">
                  <Sparkles size={15} /> Nutrition Assistant
                </div>
                <h1 className="mt-6 max-w-4xl text-5xl font-semibold leading-[.98] tracking-[-0.055em] md:text-6xl">
                  Pilih tahap hidupnya. Lihat panduannya dengan lebih visual.
                </h1>
                <p className="mt-6 max-w-2xl text-base leading-8 text-secondary">
                  SEHATIN memulai dari assessment yang relevan, lalu mengubah hasil menjadi rekomendasi, menu, goal, dan guided program yang mudah dipahami.
                </p>
                <div className="mt-7 flex flex-wrap gap-4 text-sm text-secondary">
                  <span className="inline-flex items-center gap-2"><CheckCircle2 size={16} className="text-primary" /> Public assessment tanpa login</span>
                  <span className="inline-flex items-center gap-2"><ShieldCheck size={16} className="text-primary" /> Safety-limited bila konteks membutuhkan profesional</span>
                </div>
              </div>
              <StageCompanionIllustration stage="toddler" />
            </div>
          </Reveal>
        </Container>
      </section>

      <section className="bg-surface">
        <Container className="py-14 md:py-20">
          <div className="mb-9 max-w-3xl">
            <p className="eyebrow">Pilih tahap</p>
            <h2 className="mt-4 text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">Mulai dari kebutuhan yang paling sesuai.</h2>
            <p className="mt-4 max-w-2xl text-base leading-7 text-secondary">
              Pilih tahap usia untuk membuka assessment dan panduan nutrisi yang sesuai dengan konteksnya.
            </p>
          </div>

          <div className="grid gap-5 lg:grid-cols-3">
            {CATEGORIES.map((item, index) => (
              <Reveal key={item.href} delay={index * 70}>
                <Link
                  href={item.href}
                  aria-label={`${item.title} — buka assessment nutrisi`}
                  className="group block h-full rounded-[24px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-4"
                >
                  <article className="flex h-full cursor-pointer flex-col overflow-hidden rounded-[24px] border border-line bg-white shadow-[0_16px_50px_rgba(21,67,55,.05)] transition-[transform,box-shadow,border-color] duration-300 group-hover:-translate-y-1 group-hover:border-primary/30 group-hover:shadow-[0_22px_65px_rgba(21,67,55,.1)] motion-reduce:transform-none motion-reduce:transition-none">
                    <div className="p-3 pb-0">
                      <StageCompanionIllustration stage={item.stage} compact />
                    </div>
                    <div className="flex flex-1 flex-col p-6 pt-4">
                      <div className="flex items-center justify-between gap-4">
                        <p className="text-xs font-black uppercase tracking-[.12em] text-primary-dark">{item.index} · {item.range}</p>
                        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-background text-primary-dark transition-transform duration-300 group-hover:translate-x-1" aria-hidden="true">
                          <ArrowRight size={17} />
                        </span>
                      </div>
                      <h3 className="mt-4 text-3xl font-semibold tracking-[-0.04em]">{item.title}</h3>
                      <p className="mt-2 text-xs font-bold uppercase tracking-[.1em] text-muted">{item.note}</p>
                      <p className="mt-4 text-sm leading-7 text-secondary">{item.description}</p>
                      <p className="mt-auto border-t border-line pt-5 text-sm font-semibold text-primary-dark">Buka assessment <ArrowRight size={15} className="ml-1 inline" /></p>
                    </div>
                  </article>
                </Link>
              </Reveal>
            ))}
          </div>
        </Container>
      </section>

      {showSavedProgram && (
        <section className="bg-background">
          <Container className="py-14 md:py-16">
            <div className="grid gap-6 rounded-2xl border border-line bg-primary-light/40 p-7 md:grid-cols-[1fr_auto] md:items-center">
              <div>
                <p className="eyebrow">Sudah punya program?</p>
                <h2 className="mt-3 text-3xl font-semibold tracking-[-0.04em]">Lanjutkan dari hari yang tersedia.</h2>
                <p className="mt-3 max-w-2xl text-sm leading-7 text-secondary">Buka kembali Guided Nutrition Program yang sudah kamu simpan di akun ini.</p>
              </div>
              <Link href="/nutrition/program" className="inline-flex min-h-11 items-center justify-center rounded-full bg-text px-5 text-sm font-semibold text-white transition-colors hover:bg-primary-dark">
                Continue My Program <ArrowRight className="ml-2" size={16} />
              </Link>
            </div>
          </Container>
        </section>
      )}

    </div>
  );
}
