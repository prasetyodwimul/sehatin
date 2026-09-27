from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .evidence_provider import EvidenceRecord
from .live_evidence_provider import _infer_stance, _keywords_from_query, build_pubmed_query

EUROPE_PMC_SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def _clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _date_value(value: object) -> str:
    raw = _clean(value)
    match = re.search(r"(19|20)\d{2}(?:-\d{2}(?:-\d{2})?)?", raw)
    if not match:
        return ""
    candidate = match.group(0)
    try:
        if len(candidate) == 4:
            return f"{candidate}-01-01"
        if len(candidate) == 7:
            return f"{candidate}-01"
        date.fromisoformat(candidate)
        return candidate
    except ValueError:
        return ""


class EuropePMCEvidenceProvider:
    """Secondary literature retrieval used when PubMed is unavailable.

    Europe PMC exposes publication metadata and abstracts through a public REST
    API. It is independent infrastructure from NCBI E-utilities, so a transient
    PubMed outage does not automatically become a zero-evidence result.
    """

    def __init__(self, *, timeout: float = 6.0, max_results: int = 6):
        self.timeout = timeout
        self.max_results = max(1, min(8, max_results))

    def search(self, claim: str) -> tuple[list[EvidenceRecord], str | None]:
        query = build_pubmed_query(claim)
        if len(query.strip()) < 3:
            return [], None
        try:
            payload = self._get(
                {
                    "query": query,
                    "format": "json",
                    "pageSize": str(self.max_results),
                    "resultType": "core",
                    "synonym": "true",
                }
            )
            data = json.loads(payload.decode("utf-8"))
            results = data.get("resultList", {}).get("result", [])
            records: list[EvidenceRecord] = []
            keywords = _keywords_from_query(query)
            now = datetime.now(timezone.utc).date().isoformat()
            for item in results:
                title = _clean(item.get("title"))
                abstract = _clean(item.get("abstractText"))
                identifier = _clean(item.get("pmid") or item.get("id"))
                if not title or not abstract or len(abstract) < 40 or not identifier:
                    continue
                journal = _clean(item.get("journalTitle")) or "Europe PMC indexed journal"
                records.append(
                    EvidenceRecord(
                        id=f"europepmc-{identifier}",
                        source_id=f"europepmc:{identifier}",
                        keywords=keywords,
                        title=title,
                        source=journal,
                        source_type="peer_reviewed",
                        publication_date=_date_value(item.get("firstPublicationDate") or item.get("pubYear")),
                        retrieved_at=now,
                        url=f"https://pubmed.ncbi.nlm.nih.gov/{identifier}/" if str(item.get("source", "")).upper() == "MED" else f"https://europepmc.org/article/MED/{identifier}",
                        canonical_url=f"https://europepmc.org/article/MED/{identifier}",
                        stance=_infer_stance(abstract),
                        excerpt=abstract[:700].rsplit(" ", 1)[0] if len(abstract) > 700 else abstract,
                        quality=0.82,
                        authority_level=3,
                        authority_score=0.84,
                        verified=True,
                        demo=False,
                        provider="europepmc-live",
                        independent_group=f"europepmc:{identifier}",
                        trace_note="Live metadata/abstract retrieved from Europe PMC REST API as secondary literature provider.",
                    )
                )
            return records, None
        except Exception as exc:
            return [], f"Europe PMC live retrieval unavailable ({exc.__class__.__name__})."

    def _get(self, params: dict[str, str]) -> bytes:
        url = f"{EUROPE_PMC_SEARCH}?{urlencode(params)}"
        req = Request(url, headers={"User-Agent": "SEHATIN-HealthChecker/1.0"})
        with urlopen(req, timeout=self.timeout) as response:  # noqa: S310 - fixed trusted EMBL-EBI host
            return response.read(2_000_000)
