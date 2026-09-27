import { NutritionProgramShell } from "@/components/nutrition-program-shell";

export default function NutritionProgramLayout({ children, params }: { children: React.ReactNode; params: { programId: string } }) {
  return <NutritionProgramShell programId={params.programId}>{children}</NutritionProgramShell>;
}
