import { NutritionProgramDayPage } from "@/components/nutrition-program-day-page";

export default function NutritionProgramDayRoute({ params }: { params: { dayNumber: string } }) {
  return <NutritionProgramDayPage dayNumber={Number(params.dayNumber)} />;
}
