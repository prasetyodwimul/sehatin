"use client";

/* eslint-disable @next/next/no-img-element */

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowRight, Droplets, SearchCheck, Utensils } from "lucide-react";
import { Container } from "@/components/layout";
import { Reveal } from "@/components/motion";
import { useAuth } from "@/components/auth-provider";
import { Alert, Button, ProgressBar } from "@/components/ui";
import { formatPercent, listNutritionPrograms, type ProgramSummary } from "@/lib/nutrition-program";

const PHOTO = {
  hero: { src: "/images/sehatin/home-hero-health-map.svg", alt: "Grafis editorial ekosistem kesehatan SEHATIN dengan simbol layanan, perlindungan, darah, dan verifikasi." },
  nutrition: { src: "/images/sehatin/home-card-nutrition-new.png", alt: "Ilustrasi makanan bergizi dengan sayuran, nasi, ikan, dan telur dalam gaya editorial SEHATIN." },
  blood: { src: "/images/sehatin/home-card-blood.svg", alt: "Grafis editorial kantong darah dan panel ketersediaan Blood Connect." },
  checker: { src: "/images/sehatin/home-card-evidence.svg", alt: "Grafis editorial dokumen evidence dan kaca pembesar." },
  bloodSecondary: { src: "/images/sehatin/home-feature-blood.svg", alt: "Grafis editorial inventori darah dan unit ketersediaan." },
  checkerSecondary: { src: "/images/sehatin/home-feature-evidence.svg", alt: "Grafis editorial dokumen sumber dan pemeriksaan evidence." },
} as const;

const MODULES = [
  {
    index: "01",
    title: "Nutrition Assistant",
    summary: "Mulai dari usia, pola makan, alergi, dan kebutuhan harian untuk mendapatkan panduan nutrisi yang lebih sesuai konteks.",
    href: "/nutrition",
    cta: "Mulai assessment nutrisi",
    icon: Utensils,
    photo: PHOTO.nutrition,
  },
  {
    index: "02",
    title: "Blood Connect",
    summary: "Cari informasi ketersediaan darah dengan melihat golongan, jumlah, fasilitas, sumber, dan waktu pembaruannya.",
    href: "/blood",
    cta: "Cari ketersediaan darah",
    icon: Droplets,
    photo: PHOTO.blood,
  },
  {
    index: "03",
    title: "Health Information Checker",
    summary: "Periksa klaim kesehatan dan lihat evidence, sumber, serta alasan yang digunakan untuk membentuk hasil pemeriksaan.",
    href: "/health-checker",
    cta: "Periksa informasi kesehatan",
    icon: SearchCheck,
    photo: PHOTO.checker,
  },
] as const;

function displayName(email: string | undefined) {
  const local = email?.split("@")[0]?.replace(/[._-]+/g, " ").trim();
  if (!local) return "di sini";
  return local.replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function programTitle(stage: string) {
  if (stage === "mpasi") return "Program MPASI";
  if (stage === "toddler") return "Program Toddler";
  return "Program Lansia";
}

function ProgramCard({ program, completed = false }: { program: ProgramSummary; completed?: boolean }) {
  return (
    <Link href={completed ? `/nutrition/program/${program.id}/result` : `/nutrition/program/${program.id}`} className="group block h-full rounded-[24px] border border-line bg-white p-5 transition-[transform,box-shadow,border-color] duration-300 hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-[0_14px_40px_rgba(16,32,29,.08)]">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="eyebrow">{programTitle(program.stage)}</p>
          <h2 className="mt-2 text-xl font-semibold tracking-[-0.025em]">{program.title}</h2>
        </div>
        <span className={`text-xs font-black uppercase tracking-[.1em] ${completed ? "text-success" : "text-primary-dark"}`}>{completed ? "SELESAI" : "AKTIF"}</span>
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-[1fr_auto] sm:items-end">
        <div>
          <p className="text-sm text-secondary">{completed ? `${program.days_completed} dari ${program.duration_days} hari selesai` : `Hari ${program.current_day} dari ${program.duration_days}`}</p>
          {!completed && <p className="mt-1 text-sm font-semibold">Fokus: {program.goal?.title ?? "Panduan hari ini"}</p>}
        </div>
        <p className="text-2xl font-semibold tracking-[-0.03em]">{formatPercent(program.progress_percent)}%</p>
      </div>

      <div className="mt-3"><ProgressBar value={program.progress_percent} label={`${formatPercent(program.progress_percent)}% program progress`} /></div>
      <div className="mt-5 flex items-center justify-between gap-4 border-t border-line pt-4 text-sm font-semibold text-primary-dark">
        <span>{completed ? "Lihat Final Program Result" : "Lanjutkan program"}</span>
        <ArrowRight size={16} className="transition-transform duration-300 group-hover:translate-x-1" aria-hidden="true" />
      </div>
    </Link>
  );
}

function PublicHome() {
  return (
    <>
      <section className="border-b border-line bg-background">
        <Container className="grid items-center gap-10 py-12 md:py-16 lg:grid-cols-[1.02fr_.98fr] lg:gap-14 lg:py-20">
          <Reveal>
            <p className="eyebrow">SEHATIN · Trusted Health Ecosystem</p>
            <h1 className="mt-5 max-w-[12ch] text-5xl font-semibold leading-[.98] tracking-[-0.05em] text-text sm:text-6xl lg:text-[4.1rem]">Lebih mudah memahami informasi kesehatan.</h1>
            <p className="mt-6 max-w-2xl text-base leading-7 text-secondary md:text-lg md:leading-8">Cari informasi yang kamu butuhkan, lihat sumbernya, lalu pahami hasilnya tanpa harus menebak-nebak dasar informasinya.</p>
            <div className="mt-7 flex flex-col gap-3 sm:flex-row">
              <Link href="/health-checker" className="inline-flex min-h-12 items-center justify-center gap-2 rounded-full bg-primary px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-primary-dark">Periksa informasi kesehatan <ArrowRight size={16} aria-hidden="true" /></Link>
              <Link href="/nutrition" className="inline-flex min-h-12 items-center justify-center rounded-full border border-primary/35 bg-surface px-6 py-3 text-sm font-semibold text-primary-dark transition-colors hover:bg-primary-light/60">Jelajahi nutrisi</Link>
            </div>
          </Reveal>
          <Reveal delay={100}>
            <figure className="overflow-hidden rounded-[24px] border border-line bg-surface shadow-[0_20px_60px_rgba(16,32,29,.08)]">
              {/* eslint-disable-next-line @next/next/no-img-element */}<img src={PHOTO.hero.src} alt={PHOTO.hero.alt} className="aspect-[4/3] w-full bg-background object-cover object-center saturate-[.92]" loading="eager" />
              <figcaption className="border-t border-line p-5"><p className="text-xs font-bold uppercase tracking-[0.14em] text-primary-dark">Informasi yang bisa ditelusuri</p><p className="mt-2 text-sm leading-6 text-secondary">SEHATIN membantu kamu melihat bukan hanya hasil, tetapi juga konteks dan sumber yang menyertainya.</p></figcaption>
            </figure>
          </Reveal>
        </Container>
      </section>

      <section className="bg-surface"><Container className="py-14 md:py-16 lg:py-20">
        <Reveal className="max-w-3xl"><p className="eyebrow">Pilih fitur</p><h2 className="mt-4 text-3xl font-semibold leading-tight tracking-[-0.035em] sm:text-4xl">Mulai dari yang sedang kamu butuhkan.</h2><p className="mt-4 max-w-2xl text-base leading-7 text-secondary">Ada tiga jalur utama: panduan nutrisi, informasi ketersediaan darah, dan pemeriksaan klaim kesehatan.</p></Reveal>
        <div className="mt-9 grid gap-5 lg:grid-cols-3">{MODULES.map(({ index, title, summary, href, cta, icon: Icon, photo }, position) => <Reveal key={title} delay={position * 70} className="h-full"><Link href={href} aria-label={`${title} — ${cta}`} className="group block h-full rounded-[24px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-4"><article className="flex h-full flex-col overflow-hidden rounded-[24px] border border-line bg-background transition-[transform,box-shadow,border-color] duration-300 group-hover:-translate-y-1 group-hover:border-primary/30 group-hover:shadow-[0_18px_50px_rgba(16,32,29,.08)]"><div className="relative overflow-hidden bg-background">{/* eslint-disable-next-line @next/next/no-img-element */}<img src={photo.src} alt={photo.alt} className="aspect-[16/6] w-full object-contain object-center bg-background saturate-[.9] transition-transform duration-500 group-hover:scale-[1.02]" loading="lazy" /><span className="absolute left-4 top-4 rounded-full bg-white/95 px-3 py-1 text-[10px] font-black tracking-[0.14em] text-primary-dark shadow-sm backdrop-blur">{index}</span></div><div className="flex flex-1 flex-col p-5 md:p-6"><div className="flex items-center gap-2 text-primary-dark"><Icon size={18} aria-hidden="true" /><h3 className="text-sm font-semibold tracking-[-0.01em]">{title}</h3></div><p className="mt-4 text-sm leading-6 text-secondary md:text-[15px] md:leading-7">{summary}</p><div className="mt-auto flex items-center justify-between gap-4 border-t border-line pt-5 text-sm font-semibold text-primary-dark"><span>{cta}</span><ArrowRight size={16} className="transition-transform duration-300 group-hover:translate-x-1" aria-hidden="true" /></div></div></article></Link></Reveal>)}</div>
        <div className="mt-14 border-t border-line pt-10">
          <p className="eyebrow">How trust is built</p>
          <div className="mt-4 grid gap-5 md:grid-cols-2 lg:grid-cols-4">
            {["Input", "Evidence", "Verification", "Trust"].map((step, index) => (
              <div key={step} className="border-l border-line pl-4">
                <p className="text-xs font-black tracking-[.12em] text-primary-dark">0{index + 1}</p>
                <h3 className="mt-2 text-lg font-semibold">{step}</h3>
                <p className="mt-1 text-sm leading-6 text-secondary">Informasi dipahami bertahap, dari kebutuhan awal sampai alasan di balik hasil.</p>
              </div>
            ))}
          </div>
        </div>
      </Container></section>
    </>
  );
}

function AuthenticatedHome({ userEmail }: { userEmail: string | undefined }) {
  const [programs, setPrograms] = useState<ProgramSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadPrograms = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setPrograms(await listNutritionPrograms());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Program belum dapat dimuat.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadPrograms(); }, [loadPrograms]);

  const activePrograms = useMemo(() => programs.filter((program) => program.status === "ACTIVE" && !program.completed_at), [programs]);
  const completedPrograms = useMemo(() => programs.filter((program) => program.status !== "ACTIVE" || Boolean(program.completed_at)), [programs]);

  return (
    <section className="bg-background">
      <Container className="py-10 md:py-14 lg:py-18">
        <Reveal>
          <p className="eyebrow">Ruang kamu di SEHATIN</p>
          <h1 className="mt-4 max-w-3xl text-4xl font-semibold leading-tight tracking-[-0.045em] sm:text-5xl">Halo, {displayName(userEmail)}.</h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-secondary">Lanjutkan langkah yang sedang kamu kerjakan, atau mulai program nutrisi baru.</p>
        </Reveal>

        {error && <div className="mt-6"><Alert variant="error">{error}</Alert></div>}

        {loading ? (
          <div className="mt-10 grid gap-4 lg:grid-cols-2" aria-label="Memuat program"><div className="h-52 animate-pulse rounded-[24px] border border-line bg-white" /><div className="h-52 animate-pulse rounded-[24px] border border-line bg-white" /></div>
        ) : activePrograms.length > 0 ? (
          <section className="mt-10">
            <div className="flex items-end justify-between gap-4 border-b border-line pb-3"><div><p className="eyebrow">Program sedang berjalan</p><h2 className="mt-2 text-2xl font-semibold">Lanjutkan dari hari ini.</h2></div><Link href="/nutrition/program" className="text-sm font-semibold text-primary-dark">Lihat semua →</Link></div>
            <div className="mt-5 grid gap-4 lg:grid-cols-2">{activePrograms.map((program) => <ProgramCard key={program.id} program={program} />)}</div>
          </section>
        ) : (
          <section className="mt-10 border-y border-line py-8">
            <p className="eyebrow">Belum ada program</p>
            <h2 className="mt-2 text-2xl font-semibold">Belum ada program nutrisi yang sedang berjalan.</h2>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-secondary">Pilih kategori yang sesuai untuk membuat program baru. Hasil assessment tetap dapat digunakan tanpa harus membuka program tersimpan.</p>
            <div className="mt-6 flex flex-wrap gap-3"><Link href="/nutrition/mpasi" className="inline-flex min-h-11 items-center rounded-full border border-line bg-white px-4 text-sm font-semibold">MPASI</Link><Link href="/nutrition/toddler" className="inline-flex min-h-11 items-center rounded-full border border-line bg-white px-4 text-sm font-semibold">Toddler</Link><Link href="/nutrition/elderly" className="inline-flex min-h-11 items-center rounded-full border border-line bg-white px-4 text-sm font-semibold">Lansia</Link></div>
          </section>
        )}

        {completedPrograms.length > 0 && (
          <section className="mt-12">
            <div className="border-b border-line pb-3"><p className="eyebrow">Program selesai</p><h2 className="mt-2 text-2xl font-semibold">Riwayat yang sudah kamu selesaikan.</h2></div>
            <div className="mt-5 grid gap-4 lg:grid-cols-2">{completedPrograms.slice(0, 4).map((program) => <ProgramCard key={program.id} program={program} completed />)}</div>
          </section>
        )}

        <section className="mt-14 border-t border-line pt-10"><div className="flex flex-wrap items-end justify-between gap-4"><div><p className="eyebrow">Pilih fitur</p><h2 className="mt-2 text-2xl font-semibold">Akses fitur SEHATIN lainnya.</h2></div><Link href="/nutrition" className="text-sm font-semibold text-primary-dark">Semua fitur →</Link></div><div className="mt-5 grid gap-4 md:grid-cols-2 lg:grid-cols-3"><Link href="/nutrition" className="group overflow-hidden rounded-[24px] border border-line bg-white transition-[transform,box-shadow] hover:-translate-y-0.5 hover:shadow-subtle"><div className="overflow-hidden bg-background"><img src={PHOTO.nutrition.src} alt={PHOTO.nutrition.alt} className="aspect-[16/6] w-full object-cover object-center saturate-[.96] transition-transform duration-500 group-hover:scale-[1.02]" loading="lazy" /></div><div className="p-5"><p className="eyebrow">Nutrition Assistant</p><h3 className="mt-2 text-xl font-semibold">Dapatkan panduan nutrisi yang sesuai konteks.</h3><span className="mt-5 inline-flex items-center text-sm font-semibold text-primary-dark">Mulai assessment nutrisi <ArrowRight size={15} className="ml-2" /></span></div></Link><Link href="/blood" className="group overflow-hidden rounded-[24px] border border-line bg-white transition-[transform,box-shadow] hover:-translate-y-0.5 hover:shadow-subtle"><div className="overflow-hidden bg-background"><img src={PHOTO.bloodSecondary.src} alt={PHOTO.bloodSecondary.alt} className="aspect-[16/6] w-full object-cover object-[50%_42%] saturate-[.88] transition-transform duration-500 group-hover:scale-[1.02]" loading="lazy" /></div><div className="p-5"><p className="eyebrow">Blood Connect</p><h3 className="mt-2 text-xl font-semibold">Cari informasi ketersediaan darah.</h3><span className="mt-5 inline-flex items-center text-sm font-semibold text-primary-dark">Buka Blood Connect <ArrowRight size={15} className="ml-2" /></span></div></Link><Link href="/health-checker" className="group overflow-hidden rounded-[24px] border border-line bg-white transition-[transform,box-shadow] hover:-translate-y-0.5 hover:shadow-subtle"><div className="overflow-hidden bg-background"><img src={PHOTO.checkerSecondary.src} alt={PHOTO.checkerSecondary.alt} className="aspect-[16/6] w-full object-cover object-[50%_48%] saturate-[.88] transition-transform duration-500 group-hover:scale-[1.02]" loading="lazy" /></div><div className="p-5"><p className="eyebrow">Health Checker</p><h3 className="mt-2 text-xl font-semibold">Periksa dasar sebuah klaim kesehatan.</h3><span className="mt-5 inline-flex items-center text-sm font-semibold text-primary-dark">Check Evidence <ArrowRight size={15} className="ml-2" /></span></div></Link></div></section>
      </Container>
    </section>
  );
}

export default function HomePage() {
  const { status, user } = useAuth();
  if (status === "loading") return <div className="min-h-[70vh] animate-pulse bg-background" aria-label="Memuat halaman utama" />;
  return status === "authenticated" ? <AuthenticatedHome userEmail={user?.email} /> : <PublicHome />;
}
