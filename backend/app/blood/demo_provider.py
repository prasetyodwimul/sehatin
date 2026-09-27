from app.schemas.blood import BloodFacility


DEMO_FACILITIES = [
    {
        "id": "pmi-bandung",
        "name": "PMI Kota Bandung",
        "facility_type": "PMI",
        "city": "Bandung",
        "address": "Jl. Aceh No. 79, Bandung, Jawa Barat",
        "verified": False,
        "last_updated": "2026-09-19T20:05:00+07:00",
        "data_source": "Data demonstrasi SEHATIN · perlu konfirmasi ke fasilitas",
        "demo_data": True,
        "inventory": [
            {"blood_type": "A", "rhesus": "+", "status": "AVAILABLE", "units": 18},
            {"blood_type": "A", "rhesus": "-", "status": "LIMITED", "units": 4},
            {"blood_type": "B", "rhesus": "+", "status": "AVAILABLE", "units": 14},
            {"blood_type": "B", "rhesus": "-", "status": "LIMITED", "units": 2},
            {"blood_type": "O", "rhesus": "+", "status": "AVAILABLE", "units": 22},
            {"blood_type": "O", "rhesus": "-", "status": "LIMITED", "units": 3},
            {"blood_type": "AB", "rhesus": "+", "status": "LIMITED", "units": 5},
        ],
    },
    {
        "id": "rs-mitra-cimahi",
        "name": "RS Mitra Cendekia",
        "facility_type": "Rumah sakit",
        "city": "Cimahi",
        "address": "Jl. Kerkoff No. 41, Cimahi, Jawa Barat",
        "verified": False,
        "last_updated": "2026-09-19T19:42:00+07:00",
        "data_source": "Data demonstrasi SEHATIN · perlu konfirmasi ke fasilitas",
        "demo_data": True,
        "inventory": [
            {"blood_type": "A", "rhesus": "+", "status": "LIMITED", "units": 4},
            {"blood_type": "B", "rhesus": "+", "status": "AVAILABLE", "units": 13},
            {"blood_type": "AB", "rhesus": "+", "status": "UNKNOWN", "units": None},
            {"blood_type": "AB", "rhesus": "-", "status": "UNKNOWN", "units": None},
            {"blood_type": "O", "rhesus": "+", "status": "LIMITED", "units": 3},
        ],
    },
    {
        "id": "rs-bina-medika-sumedang",
        "name": "RS Bina Medika",
        "facility_type": "Rumah sakit",
        "city": "Sumedang",
        "address": "Jl. Prabu Gajah Agung No. 12, Sumedang, Jawa Barat",
        "verified": False,
        "last_updated": "2026-09-19T18:55:00+07:00",
        "data_source": "Data demonstrasi SEHATIN · perlu konfirmasi ke fasilitas",
        "demo_data": True,
        "inventory": [
            {"blood_type": "A", "rhesus": "+", "status": "AVAILABLE", "units": 8},
            {"blood_type": "B", "rhesus": "+", "status": "LIMITED", "units": 3},
            {"blood_type": "O", "rhesus": "+", "status": "AVAILABLE", "units": 11},
            {"blood_type": "AB", "rhesus": "+", "status": "EMPTY", "units": 0},
        ],
    },
    {
        "id": "udd-garut",
        "name": "Unit Donor Darah Garut",
        "facility_type": "Unit donor darah",
        "city": "Garut",
        "address": "Jl. Merdeka No. 98, Garut, Jawa Barat",
        "verified": False,
        "last_updated": "2026-09-19T18:10:00+07:00",
        "data_source": "Data demonstrasi SEHATIN · perlu konfirmasi ke fasilitas",
        "demo_data": True,
        "inventory": [
            {"blood_type": "A", "rhesus": "+", "status": "UNKNOWN", "units": None},
            {"blood_type": "B", "rhesus": "+", "status": "LIMITED", "units": 2},
            {"blood_type": "AB", "rhesus": "+", "status": "LIMITED", "units": 1},
            {"blood_type": "O", "rhesus": "+", "status": "EMPTY", "units": 0},
        ],
    },
    {
        "id": "rs-sentosa-tasikmalaya",
        "name": "RS Sentosa Tasikmalaya",
        "facility_type": "Rumah sakit",
        "city": "Tasikmalaya",
        "address": "Jl. KHZ Mustofa No. 27, Tasikmalaya, Jawa Barat",
        "verified": False,
        "last_updated": "2026-09-19T17:36:00+07:00",
        "data_source": "Data demonstrasi SEHATIN · perlu konfirmasi ke fasilitas",
        "demo_data": True,
        "inventory": [
            {"blood_type": "A", "rhesus": "+", "status": "AVAILABLE", "units": 6},
            {"blood_type": "A", "rhesus": "-", "status": "LIMITED", "units": 1},
            {"blood_type": "B", "rhesus": "+", "status": "AVAILABLE", "units": 7},
            {"blood_type": "O", "rhesus": "+", "status": "LIMITED", "units": 2},
            {"blood_type": "AB", "rhesus": "+", "status": "LIMITED", "units": 2},
        ],
    },
    {
        "id": "rs-cakra-bogor",
        "name": "RS Cakra Husada",
        "facility_type": "Rumah sakit",
        "city": "Bogor",
        "address": "Jl. Pajajaran No. 115, Bogor, Jawa Barat",
        "verified": False,
        "last_updated": "2026-09-19T17:05:00+07:00",
        "data_source": "Data demonstrasi SEHATIN · perlu konfirmasi ke fasilitas",
        "demo_data": True,
        "inventory": [
            {"blood_type": "A", "rhesus": "+", "status": "LIMITED", "units": 3},
            {"blood_type": "B", "rhesus": "+", "status": "AVAILABLE", "units": 9},
            {"blood_type": "AB", "rhesus": "+", "status": "UNKNOWN", "units": None},
            {"blood_type": "O", "rhesus": "+", "status": "AVAILABLE", "units": 12},
            {"blood_type": "O", "rhesus": "-", "status": "LIMITED", "units": 2},
        ],
    },
    {
        "id": "rs-pelita-cirebon",
        "name": "RS Pelita Cirebon",
        "facility_type": "Rumah sakit",
        "city": "Cirebon",
        "address": "Jl. Tuparev No. 64, Cirebon, Jawa Barat",
        "verified": False,
        "last_updated": "2026-09-19T16:44:00+07:00",
        "data_source": "Data demonstrasi SEHATIN · perlu konfirmasi ke fasilitas",
        "demo_data": True,
        "inventory": [
            {"blood_type": "A", "rhesus": "+", "status": "AVAILABLE", "units": 5},
            {"blood_type": "B", "rhesus": "+", "status": "LIMITED", "units": 2},
            {"blood_type": "AB", "rhesus": "+", "status": "LIMITED", "units": 1},
            {"blood_type": "O", "rhesus": "+", "status": "AVAILABLE", "units": 10},
            {"blood_type": "O", "rhesus": "-", "status": "UNKNOWN", "units": None},
        ],
    },
]


class DemoBloodProvider:
    @property
    def name(self) -> str:
        return "SEHATIN Demo Blood Provider"

    @property
    def is_demo(self) -> bool:
        return True

    def list_facilities(self) -> list[BloodFacility]:
        return [BloodFacility.model_validate(item) for item in DEMO_FACILITIES]

    def get_facility(self, facility_id: str) -> BloodFacility | None:
        return next((item for item in self.list_facilities() if item.id == facility_id), None)
