from typing import Literal

from pydantic import BaseModel, Field, model_validator

Status = Literal["AVAILABLE", "LIMITED", "EMPTY", "UNKNOWN"]
DataMode = Literal["SIMULATED", "LIVE"]
BloodType = Literal["A", "B", "AB", "O"]
Rhesus = Literal["+", "-"]


class BloodInventoryItem(BaseModel):
    blood_type: BloodType
    rhesus: Rhesus
    status: Status
    units: int | None = Field(default=None, ge=0)
    quantity: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def synchronize_quantity(self):
        if self.quantity is None:
            self.quantity = self.units
        if self.units is None:
            self.units = self.quantity
        return self


class BloodFacility(BaseModel):
    id: str
    name: str
    facility_type: str = "blood_facility"
    city: str
    address: str
    location: str | None = None
    verified: bool
    last_updated: str
    data_source: str
    demo_data: bool = True
    data_mode: DataMode | None = None
    refresh_hint_seconds: int = Field(default=60, ge=15, le=3600)
    inventory: list[BloodInventoryItem]

    @model_validator(mode="after")
    def set_location(self):
        if not self.location:
            self.location = f"{self.city} — {self.address}"
        if not self.data_mode:
            self.data_mode = "SIMULATED" if self.demo_data else "LIVE"
        return self
