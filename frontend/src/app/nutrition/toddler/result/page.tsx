import Link from "next/link";
import { Container } from "@/components/layout";
import { NutritionResult } from "@/components/nutrition-result";

export default function ResultPage() {
  return <Container className="pb-10 pt-5 md:pb-14 md:pt-6"><div className="mb-1 flex flex-wrap items-center justify-between gap-3"><Link href="/nutrition/toddler" className="text-xs font-bold uppercase tracking-[0.14em] text-muted hover:text-primary-dark">← Assessment</Link><span className="text-xs font-bold uppercase tracking-[0.14em] text-primary-dark">Result · session only</span></div><NutritionResult stage="toddler" /></Container>;
}
