import { Container } from "@/components/layout";
import { ProfilePage } from "@/components/profile-page";

export default function ProfileRoute() {
  return (
    <Container className="py-10 md:py-12">
      <ProfilePage />
    </Container>
  );
}
