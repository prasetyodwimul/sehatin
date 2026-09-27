import Link from "next/link";
import { Container } from "@/components/layout";
import { NutritionProgramHome } from "@/components/nutrition-program-home";

export default function NutritionProgramPage() {
  return <Container className="py-10 md:py-16"><Link href="/nutrition" className="text-xs font-bold uppercase tracking-[0.14em] text-muted hover:text-primary-dark">← Nutrition</Link><div className="mt-8"><NutritionProgramHome /></div></Container>;
}
