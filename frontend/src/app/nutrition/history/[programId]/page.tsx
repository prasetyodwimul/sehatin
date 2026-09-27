import { redirect } from "next/navigation";

export default function NutritionHistoryDetailPage({ params }: { params: { programId: string } }) {
  redirect(`/nutrition/program/${params.programId}/history`);
}
