import { Container } from "@/components/layout";
import { NutritionAssessment } from "@/components/nutrition-assessment";
import { NutritionAssessmentHero } from "@/components/nutrition-assessment-hero";
export default function ToddlerAssessmentPage(){return <Container className="py-8 md:py-12"><NutritionAssessmentHero stage="toddler"/><NutritionAssessment stage="toddler"/></Container>}
