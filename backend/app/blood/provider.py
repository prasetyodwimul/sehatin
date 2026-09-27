from typing import Protocol
from app.schemas.blood import BloodFacility


class BloodProvider(Protocol):
    """Interface implemented by demo and future official blood-data providers."""

    @property
    def name(self) -> str: ...

    @property
    def is_demo(self) -> bool: ...

    def list_facilities(self) -> list[BloodFacility]: ...

    def get_facility(self, facility_id: str) -> BloodFacility | None: ...
