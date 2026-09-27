from __future__ import annotations

import logging

from sqlalchemy import select

from app.database import session_scope
from app.models import BloodFacilityModel, BloodInventoryModel
from app.schemas.blood import BloodFacility, BloodInventoryItem

logger = logging.getLogger("sehatin.blood.database")


class DatabaseBloodProvider:
    @property
    def name(self) -> str:
        return "SEHATIN Database Blood Provider"

    @property
    def is_demo(self) -> bool:
        # PART 1 seeds database rows from demo data. This remains explicit.
        return True

    def list_facilities(self) -> list[BloodFacility]:
        try:
            with session_scope() as db:
                facilities = db.scalars(select(BloodFacilityModel).order_by(BloodFacilityModel.name)).all()
                if not facilities:
                    return []
                inventory_rows = db.scalars(select(BloodInventoryModel)).all()
                grouped: dict[str, list[BloodInventoryItem]] = {}
                for row in inventory_rows:
                    grouped.setdefault(row.facility_id, []).append(
                        BloodInventoryItem(
                            blood_type=row.blood_type,
                            rhesus=row.rhesus,
                            status=row.status,
                            units=row.quantity,
                            quantity=row.quantity,
                        )
                    )
                return [
                    BloodFacility(
                        id=row.id,
                        name=row.name,
                        facility_type=row.facility_type,
                        city=row.city,
                        address=row.address,
                        verified=row.verified,
                        last_updated=row.last_updated.isoformat(),
                        data_source=row.data_source,
                        demo_data=row.is_demo,
                        inventory=grouped.get(row.id, []),
                    )
                    for row in facilities
                ]
        except Exception as exc:
            logger.warning("Database blood provider unavailable: %s", exc.__class__.__name__)
            return []

    def get_facility(self, facility_id: str) -> BloodFacility | None:
        return next((item for item in self.list_facilities() if item.id == facility_id), None)
