import { NutritionFinalResult } from "@/components/nutrition-final-result";
export default function NutritionProgramResultPage({ params }: { params: { programId: string } }) { return <NutritionFinalResult programId={params.programId} />; }
