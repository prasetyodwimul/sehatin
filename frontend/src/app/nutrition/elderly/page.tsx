import { Container } from "@/components/layout";
import { NutritionAssessment } from "@/components/nutrition-assessment";
import { NutritionAssessmentHero } from "@/components/nutrition-assessment-hero";
export default function ElderlyAssessmentPage(){return <Container className="py-8 md:py-12"><NutritionAssessmentHero stage="elderly"/><NutritionAssessment stage="elderly"/></Container>}
