from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.blood.demo_provider import DEMO_FACILITIES
from app.database import session_scope
from app.models import BloodFacilityModel, BloodInventoryModel, EvidenceDocumentModel, EvidenceSourceModel, SystemLogModel
from app.trust_engine.demo_evidence import DemoEvidenceProvider
from app.trust_engine.source_validator import source_authority


def _as_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _as_date(value: str) -> date:
    return date.fromisoformat(value)


def seed_demo_data(db: Session) -> dict[str, int]:
    facility_count = 0
    inventory_count = 0
    source_count = 0
    document_count = 0

    for item in DEMO_FACILITIES:
        row = db.get(BloodFacilityModel, item["id"])
        if row is None:
            row = BloodFacilityModel(id=item["id"])
            db.add(row)
        row.name = item["name"]
        row.facility_type = "blood_facility"
        row.city = item["city"]
        row.address = item["address"]
        row.verified = bool(item["verified"])
        row.data_source = item["data_source"]
        row.is_demo = True
        row.last_updated = _as_datetime(item["last_updated"])
        facility_count += 1
        db.flush()

        for inv in item["inventory"]:
            existing = db.scalar(
                select(BloodInventoryModel).where(
                    BloodInventoryModel.facility_id == item["id"],
                    BloodInventoryModel.blood_type == inv["blood_type"],
                    BloodInventoryModel.rhesus == inv["rhesus"],
                )
            )
            if existing is None:
                existing = BloodInventoryModel(
                    facility_id=item["id"], blood_type=inv["blood_type"], rhesus=inv["rhesus"]
                )
                db.add(existing)
            existing.status = inv["status"]
            existing.quantity = inv["units"]
            existing.verified = False
            existing.is_demo = True
            existing.last_updated = _as_datetime(item["last_updated"])
            inventory_count += 1

    for record in DemoEvidenceProvider().records():
        source_id = f"{record.id}-source"
        source = db.get(EvidenceSourceModel, source_id)
        if source is None:
            source = EvidenceSourceModel(id=source_id)
            db.add(source)
        source.name = record.title
        source.organization = record.source
        source.url = record.url
        source.source_type = record.source_type
        source.authority_score = record.authority_score if record.authority_score is not None else source_authority(record.source_type)
        source.verified = record.verified
        source.publication_date = _as_date(record.publication_date)
        source.last_checked = _as_datetime(record.retrieved_at)
        source_count += 1
        db.flush()

        doc = db.get(EvidenceDocumentModel, record.id)
        if doc is None:
            doc = EvidenceDocumentModel(id=record.id)
            db.add(doc)
        doc.title = record.title
        doc.content = record.excerpt
        doc.topic = record.keywords[0] if record.keywords else "health"
        doc.source_id = source_id
        doc.publication_date = _as_date(record.publication_date)
        doc.evidence_quality = record.quality
        doc.keywords = list(record.keywords)
        doc.stance_hint = record.stance
        doc.is_demo = record.demo
        document_count += 1

    db.add(SystemLogModel(event_type="seed_demo_data", level="INFO", details={"demo": True}))
    db.flush()
    return {
        "blood_facilities": facility_count,
        "blood_inventory": inventory_count,
        "evidence_sources": source_count,
        "evidence_documents": document_count,
    }


def main() -> None:
    with session_scope() as db:
        counts = seed_demo_data(db)
    print("SEHATIN demo seed complete:", counts)


if __name__ == "__main__":
    main()
