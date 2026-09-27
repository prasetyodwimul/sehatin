from app.blood.provider import BloodProvider
from app.blood.provider_factory import build_blood_provider
from app.schemas.blood import BloodFacility, BloodType, Rhesus


class BloodService:
    def __init__(self, provider: BloodProvider | None = None):
        self.provider = provider or build_blood_provider()

    def list_facilities(
        self,
        blood_type: BloodType | None = None,
        rhesus: Rhesus | None = None,
        city: str | None = None,
        facility: str | None = None,
    ) -> list[BloodFacility]:
        facilities = self.provider.list_facilities()
        city_query = city.strip().lower() if city else None
        facility_query = facility.strip().lower() if facility else None
        result: list[BloodFacility] = []

        for item in facilities:
            if city_query and city_query not in item.city.lower() and city_query not in item.address.lower():
                continue
            if facility_query and facility_query not in item.name.lower() and facility_query not in item.id.lower():
                continue

            inventory = item.inventory
            if blood_type:
                inventory = [row for row in inventory if row.blood_type == blood_type]
            if rhesus:
                inventory = [row for row in inventory if row.rhesus == rhesus]
            if (blood_type or rhesus) and not inventory:
                continue

            result.append(item.model_copy(update={"inventory": inventory}))
        return result

    def get_facility(self, facility_id: str) -> BloodFacility | None:
        return self.provider.get_facility(facility_id)


blood_service = BloodService()
