import Image from "next/image";
import Link from "next/link";
import { ArrowRight, CheckCircle2 } from "lucide-react";
import { Container } from "@/components/layout";
import { Reveal } from "@/components/motion";

const features = [
  {
    title: "Nutrition",
    copy: "Panduan nutrisi untuk MPASI, Toddler, dan Lansia, dengan kebutuhan yang berbeda pada setiap tahap kehidupan.",
    href: "/nutrition",
    image: "/images/sehatin/about/feature-nutrition.png",
    alt: "Ilustrasi mangkuk makanan sehat untuk Nutrition",
    tone: "bg-[#eef9f6]",
  },
  {
    title: "Blood Connect",
    copy: "Membantu mencatat dan memantau riwayat tekanan darah agar perkembangan pengukuran lebih mudah dilihat.",
    href: "/blood",
    image: "/images/sehatin/about/feature-blood-connect.png",
    alt: "Ilustrasi alat pemantau tekanan darah untuk Blood Connect",
    tone: "bg-[#eef7fb]",
  },
  {
    title: "Health Checker",
    copy: "Membantu menemukan dan mengecek informasi kesehatan berdasarkan referensi yang tersedia.",
    href: "/health-checker",
    image: "/images/sehatin/about/feature-health-checker.png",
    alt: "Ilustrasi clipboard dan kaca pembesar untuk Health Checker",
    tone: "bg-[#fff8ed]",
  },
];

const nutritionGroups = [
  {
    title: "MPASI",
    copy: "Panduan nutrisi dan progress untuk tahap awal pemberian makanan pendamping ASI.",
    image: "/images/sehatin/about/nutrition-mpasi.png",
    alt: "Ilustrasi bayi dan makanan MPASI",
  },
  {
    title: "Toddler",
    copy: "Panduan nutrisi untuk mendukung kebutuhan makan anak usia toddler.",
    image: "/images/sehatin/about/nutrition-toddler.png",
    alt: "Ilustrasi toddler dan makanan",
  },
  {
    title: "Lansia",
    copy: "Panduan pola makan yang dapat disesuaikan dengan kebutuhan dan kondisi lansia.",
    image: "/images/sehatin/about/nutrition-lansia.png",
    alt: "Ilustrasi lansia dan makanan sehat",
  },
];

const leafShapes = [
  "left-[-50px] top-28 h-44 w-24 -rotate-[28deg]",
  "left-[-15px] top-56 h-36 w-20 rotate-[18deg]",
  "right-[-35px] top-24 h-52 w-28 rotate-[28deg]",
  "right-[-18px] top-72 h-36 w-20 -rotate-[16deg]",
];

export default function AboutPage() {
  return (
    <main className="relative overflow-hidden bg-[#f9fcfb] text-text">
      <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
        {leafShapes.map((shape, index) => (
          <span
            key={shape}
            className={`absolute ${shape} rounded-[100%_0_100%_0] bg-[#bfe9e1]/30 ${index % 2 === 0 ? "blur-[1px]" : "bg-[#d7f2ed]/55"}`}
          />
        ))}
      </div>

      <section className="relative scroll-mt-28">
        <Container className="max-w-[1200px] pb-12 pt-8 sm:pb-16 sm:pt-10 lg:pb-12 lg:pt-12">
          <div className="grid items-center gap-5 lg:grid-cols-[.88fr_1.12fr] lg:gap-3 xl:grid-cols-[.84fr_1.16fr]">
            <Reveal className="relative z-10 max-w-[510px] lg:pl-2">
              <p className="eyebrow">Tentang Sehatin</p>
              <h1 className="mt-4 max-w-[13ch] text-[clamp(2.55rem,4vw,4rem)] font-semibold leading-[.98] tracking-[-.055em] text-[#0d302c]">
                Informasi kesehatan yang lebih mudah dipahami.
              </h1>
              <p className="mt-5 max-w-[500px] text-[16px] leading-6 text-[#52635f] sm:text-[17px] sm:leading-7">
                SEHATIN menyediakan beberapa fitur untuk membantu kamu memahami kebutuhan nutrisi, memantau tekanan darah, dan menemukan informasi kesehatan dari sumber yang terpercaya.
              </p>
              <Link
                href="#fitur"
                className="mt-6 inline-flex min-h-11 items-center gap-2 rounded-full bg-[#07554f] px-5 text-sm font-bold text-white shadow-[0_8px_18px_rgba(6,79,74,.12)] transition-transform duration-200 hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
              >
                Kenali lebih lanjut
                <ArrowRight size={16} aria-hidden="true" />
              </Link>
            </Reveal>

            <Reveal delay={100} className="relative -mr-2 lg:-mr-8 xl:-mr-12">
              <Image
                src="/images/sehatin/about/about-hero.png"
                alt="Ilustrasi anak, tenaga kesehatan, dan lansia sebagai bagian dari SEHATIN"
                width={720}
                height={460}
                priority
                className="h-auto w-full object-contain"
              />
            </Reveal>
          </div>
        </Container>
      </section>

      <section id="fitur" className="relative scroll-mt-28 rounded-t-[32px] bg-white shadow-[0_-10px_35px_rgba(15,64,58,.035)] sm:rounded-t-[38px]">
        <Container className="max-w-[1200px] py-10 sm:py-12 lg:py-14">
          <Reveal>
            <div className="max-w-[820px]">
              <p className="eyebrow">Fitur utama SEHATIN</p>
              <h2 className="mt-3 max-w-[23ch] text-[clamp(2rem,3.2vw,3rem)] font-semibold leading-[1.02] tracking-[-.045em] text-[#0d302c]">
                Tiga fitur untuk membantu memahami kesehatan
              </h2>
              <p className="mt-3 max-w-2xl text-[16px] leading-6 text-secondary">
                Fokus pada informasi yang jelas, pencatatan yang praktis, dan referensi yang mudah dipahami.
              </p>
            </div>
          </Reveal>

          <div className="mt-7 grid gap-4 md:grid-cols-3 lg:gap-5">
            {features.map((feature, index) => (
              <Reveal key={feature.title} delay={index * 60} className="h-full">
                <article className={`group flex h-full min-h-[350px] flex-col overflow-hidden rounded-[18px] border border-white/80 ${feature.tone} px-4 pb-5 pt-2 transition-transform duration-200 hover:-translate-y-0.5`}>
                  <div className="flex h-[168px] items-center justify-center sm:h-[176px]">
                    <Image
                      src={feature.image}
                      alt={feature.alt}
                      width={720}
                      height={460}
                      className="h-full w-full object-contain transition-transform duration-300 group-hover:scale-[1.015]"
                    />
                  </div>
                  <div className="px-1.5">
                    <h3 className="text-[21px] font-semibold tracking-[-.035em] text-[#102d29]">{feature.title}</h3>
                    <p className="mt-1.5 text-[14px] leading-5 text-[#52635f]">{feature.copy}</p>
                    <ul className="mt-3 space-y-1.5" aria-label={`Poin ${feature.title}`}>
                      {(feature.title === "Nutrition"
                        ? ["Panduan nutrisi sesuai kelompok", "Rekomendasi makanan", "Pemantauan progress"]
                        : feature.title === "Blood Connect"
                          ? ["Pencatatan tekanan darah", "Riwayat pengukuran", "Ringkasan perkembangan"]
                          : ["Cari topik kesehatan", "Ringkasan informasi", "Referensi yang jelas"]
                      ).map((item) => (
                        <li key={item} className="flex items-start gap-2 text-[13px] leading-5 text-[#38504b]">
                          <CheckCircle2 size={15} className="mt-0.5 shrink-0 text-[#0b776e]" aria-hidden="true" />
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                    <Link
                      href={feature.href}
                      aria-label={`Pelajari lebih lanjut ${feature.title}`}
                      className="mt-3 inline-flex items-center gap-1.5 text-[13px] font-bold text-[#0b665f] transition-colors hover:text-[#063f3a] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                    >
                      Pelajari lebih lanjut <ArrowRight size={15} aria-hidden="true" />
                    </Link>
                  </div>
                </article>
              </Reveal>
            ))}
          </div>
        </Container>
      </section>

      <section className="relative scroll-mt-28 bg-[#f9fcfb]">
        <Container className="max-w-[1200px] py-10 sm:py-12 lg:py-14">
          <Reveal>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <div className="max-w-[820px]">
                <p className="eyebrow">Nutrition</p>
                <h2 className="mt-3 max-w-[22ch] text-[clamp(2rem,3.2vw,3rem)] font-semibold leading-[1.02] tracking-[-.045em] text-[#0d302c]">
                  Nutrition untuk kebutuhan yang berbeda
                </h2>
                <p className="mt-3 max-w-2xl text-[16px] leading-6 text-secondary">
                  Setiap kelompok memiliki kebutuhan nutrisi yang berbeda. SEHATIN menyediakan panduan nutrisi yang disesuaikan dengan tiga kebutuhan utama.
                </p>
              </div>
              <Link
                href="/nutrition"
                className="inline-flex w-fit shrink-0 items-center gap-2 text-sm font-bold text-[#0b665f] transition-colors hover:text-[#063f3a] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              >
                Lihat semua fitur Nutrition <ArrowRight size={16} aria-hidden="true" />
              </Link>
            </div>
          </Reveal>

          <div className="mt-7 grid gap-3 md:grid-cols-3 md:gap-4">
            {nutritionGroups.map((group, index) => (
              <Reveal key={group.title} delay={index * 60}>
                <Link
                  href="/nutrition"
                  className="group flex min-h-[124px] items-center gap-3 rounded-[18px] border border-[#e5efec] bg-white px-3 py-2.5 shadow-[0_5px_18px_rgba(15,64,58,.035)] transition-transform duration-200 hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 sm:gap-4 sm:px-4"
                >
                  <div className="h-[104px] w-[108px] shrink-0 sm:h-[110px] sm:w-[118px]">
                    <Image src={group.image} alt={group.alt} width={720} height={460} className="h-full w-full object-contain" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="text-[17px] font-semibold tracking-[-.025em] text-[#102d29]">{group.title}</h3>
                    <p className="mt-1 text-[12px] leading-[1.45] text-[#52635f] sm:text-[13px]">{group.copy}</p>
                  </div>
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-[#b9e8e0] bg-[#f3fcfa] text-[#0b776e] transition-transform duration-200 group-hover:translate-x-0.5" aria-hidden="true">
                    <ArrowRight size={15} />
                  </span>
                </Link>
              </Reveal>
            ))}
          </div>
        </Container>
      </section>
    </main>
  );
}
