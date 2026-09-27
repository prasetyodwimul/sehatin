from app.config import get_settings

from .database_provider import DatabaseBloodProvider
from .demo_provider import DemoBloodProvider
from .provider import BloodProvider


class AutoBloodProvider:
    def __init__(self):
        self.database = DatabaseBloodProvider()
        self.demo = DemoBloodProvider()
        self._using_demo = True

    @property
    def name(self) -> str:
        return "SEHATIN Auto Blood Provider"

    @property
    def is_demo(self) -> bool:
        return self._using_demo

    def list_facilities(self):
        rows = self.database.list_facilities()
        if rows:
            self._using_demo = all(item.demo_data for item in rows)
            return rows
        self._using_demo = True
        return self.demo.list_facilities()

    def get_facility(self, facility_id: str):
        return next((item for item in self.list_facilities() if item.id == facility_id), None)


def build_blood_provider() -> BloodProvider:
    mode = get_settings().blood_provider
    if mode == "database":
        return DatabaseBloodProvider()
    if mode == "auto":
        return AutoBloodProvider()
    return DemoBloodProvider()
