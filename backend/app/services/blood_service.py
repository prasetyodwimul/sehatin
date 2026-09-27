"""Compatibility facade around the provider-based Blood Connect service."""
from app.blood.service import blood_service
from app.schemas.blood import BloodFacility, BloodType, Rhesus


def list_facilities(
    blood_type: BloodType | None = None,
    rhesus: Rhesus | None = None,
    city: str | None = None,
    facility: str | None = None,
) -> list[BloodFacility]:
    return blood_service.list_facilities(blood_type=blood_type, rhesus=rhesus, city=city, facility=facility)


def get_facility(facility_id: str) -> BloodFacility | None:
    return blood_service.get_facility(facility_id)
