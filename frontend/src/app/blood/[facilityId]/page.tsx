import { BloodFacilityDetail } from "@/components/blood-facility-detail";
import { Container } from "@/components/layout";

export default function FacilityDetailPage({ params }: { params: { facilityId: string } }) {
  return <Container className="py-10 md:py-14"><BloodFacilityDetail facilityId={params.facilityId} /></Container>;
}
