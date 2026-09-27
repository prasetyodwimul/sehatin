import Link from "next/link";
import { ArrowRight, Droplets } from "lucide-react";
import { BloodExplorer } from "@/components/blood-explorer";
import { Container } from "@/components/layout";

export default function BloodPage() {
  return (
    <>
      <section className="border-b border-line bg-[linear-gradient(135deg,#fff8f8_0%,#fff_50%,#f7fbfb_100%)]">
        <Container className="py-12 md:py-16 lg:py-18">
          <div className="grid gap-9 lg:grid-cols-[1fr_.82fr] lg:items-center lg:gap-14">
            <div>
              <p className="eyebrow">Blood Connect</p>
              <h1 className="mt-4 max-w-[12ch] text-4xl font-semibold leading-[1] tracking-[-0.05em] text-text sm:text-[3.25rem] lg:text-[3.7rem]">
                Cari ketersediaan darah dengan lebih cepat.
              </h1>
              <p className="mt-5 max-w-2xl text-base leading-7 text-secondary md:text-lg md:leading-8">
                Telusuri fasilitas berdasarkan lokasi dan golongan darah. Lihat jumlah unit, status ketersediaan, serta waktu pembaruan sebelum menghubungi fasilitas.
              </p>
              <div className="mt-7">
                <a
                  href="#blood-search"
                  className="inline-flex min-h-12 items-center justify-center gap-2 rounded-full bg-primary px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-primary-dark"
                >
                  Cari ketersediaan darah <ArrowRight size={16} aria-hidden="true" />
                </a>
              </div>
            </div>

            <figure className="overflow-hidden rounded-[28px] border border-line bg-white shadow-[0_18px_60px_rgba(16,32,29,.08)]">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src="/images/sehatin/blood-hero.svg"
                alt="Grafis editorial kantong darah, simbol tetes darah, dan panel ketersediaan unit."
                className="aspect-[4/3] w-full object-cover"
              />
            </figure>
          </div>
        </Container>
      </section>

      <section id="blood-search" className="scroll-mt-24 bg-surface">
        <Container className="py-12 md:py-14 lg:py-16">
          <BloodExplorer />
        </Container>
      </section>
    </>
  );
}
