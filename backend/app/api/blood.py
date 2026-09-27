from fastapi import APIRouter, HTTPException, Query

from app.schemas.blood import BloodFacility, BloodType, Rhesus
from app.services.blood_service import get_facility, list_facilities
from app.services.persistence import persist_blood_request

router = APIRouter(prefix="/api/blood", tags=["blood"])


@router.get("/facilities", response_model=list[BloodFacility])
def facilities(
    blood_type: BloodType | None = Query(default=None),
    rhesus: Rhesus | None = Query(default=None),
    city: str | None = Query(default=None, min_length=1, max_length=100),
    facility: str | None = Query(default=None, min_length=1, max_length=120),
) -> list[BloodFacility]:
    rows = list_facilities(blood_type=blood_type, rhesus=rhesus, city=city, facility=facility)
    persist_blood_request(blood_type=blood_type, rhesus=rhesus, location=city, facility=facility)
    return rows


@router.get("/inventory", response_model=list[BloodFacility])
def inventory(
    blood_type: BloodType | None = Query(default=None),
    rhesus: Rhesus | None = Query(default=None),
    city: str | None = Query(default=None, min_length=1, max_length=100),
    facility: str | None = Query(default=None, min_length=1, max_length=120),
) -> list[BloodFacility]:
    rows = list_facilities(blood_type=blood_type, rhesus=rhesus, city=city, facility=facility)
    persist_blood_request(blood_type=blood_type, rhesus=rhesus, location=city, facility=facility)
    return rows


@router.get("/facilities/{facility_id}", response_model=BloodFacility)
def facility_detail(facility_id: str) -> BloodFacility:
    if len(facility_id) > 100:
        raise HTTPException(status_code=422, detail="ID fasilitas tidak valid")
    row = get_facility(facility_id)
    if not row:
        raise HTTPException(status_code=404, detail="Fasilitas tidak ditemukan")
    return row
