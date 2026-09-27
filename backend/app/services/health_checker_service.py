from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict, deque
from dataclasses import dataclass

from app.config import get_settings
from app.knowledge_base.provider_factory import build_evidence_provider
from app.schemas.health_checker import ArticleInfo, HealthCheckRequest, HealthCheckResponse, HealthCheckRunResponse
from app.services.article_extractor import ArticleFetchError, ExtractedArticle, fetch_article
from app.services.url_safety import UnsafeUrlError
from app.trust_engine.claim_extractor import ExtractedClaim, extract_claims
from app.trust_engine.evidence_provider import EvidenceProvider, EvidenceRecord
from app.trust_engine.live_evidence_provider import PubMedEvidenceProvider
from app.trust_engine.europe_pmc_evidence_provider import EuropePMCEvidenceProvider
from app.trust_engine.trust_engine import TrustEngine


class HealthCheckerError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: float = 60.0):
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            bucket = self._hits[key]
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self.limit:
                return False
            bucket.append(now)
            return True


@dataclass
class CompositeEvidenceProvider:
    base: EvidenceProvider
    extra_records: list[EvidenceRecord]

    @property
    def is_demo(self) -> bool:
        return self.base.is_demo and not self.extra_records

    def records(self) -> list[EvidenceRecord]:
        return [*self.base.records(), *self.extra_records]


class HealthCheckerService:
    def __init__(self):
        settings = get_settings()
        self.settings = settings
        self.base_provider = build_evidence_provider()
        self.live_provider = PubMedEvidenceProvider(
            timeout=settings.health_fetch_timeout_seconds,
            max_results=settings.health_live_max_results,
        )
        self.secondary_live_provider = EuropePMCEvidenceProvider(
            timeout=settings.health_fetch_timeout_seconds,
            max_results=settings.health_live_max_results,
        )
        self.limiter = SlidingWindowLimiter(settings.health_checker_rate_limit_per_minute)
        self._slots = threading.BoundedSemaphore(settings.health_checker_max_concurrent)

    def enforce_request_budget(self, client_key: str) -> None:
        if not self.limiter.allow(client_key or "anonymous"):
            raise HealthCheckerError("RATE_LIMITED", "Terlalu banyak pemeriksaan dalam satu menit. Coba lagi sebentar.", 429)

    def analyze(self, payload: HealthCheckRequest) -> HealthCheckRunResponse:
        if not self._slots.acquire(blocking=False):
            raise HealthCheckerError("CHECKER_BUSY", "Health Checker sedang menangani terlalu banyak permintaan. Coba lagi.", 503)
        try:
            return self._analyze(payload)
        finally:
            self._slots.release()

    def _analyze(self, payload: HealthCheckRequest) -> HealthCheckRunResponse:
        article: ExtractedArticle | None = None
        source_outages: list[str] = []

        if payload.input_type == "url":
            try:
                article = fetch_article(
                    payload.url or "",
                    timeout=self.settings.health_fetch_timeout_seconds,
                    max_bytes=self.settings.health_url_max_bytes,
                )
            except UnsafeUrlError as exc:
                raise HealthCheckerError("UNSAFE_URL", str(exc), 422) from exc
            except ArticleFetchError as exc:
                raise HealthCheckerError("ARTICLE_FETCH_FAILED", str(exc), 422) from exc
            input_text = article.main_text
        else:
            input_text = payload.text or ""

        extracted = extract_claims(input_text, max_claims=5 if payload.input_type != "claim" else 1)
        if not extracted:
            raise HealthCheckerError("NO_CHECKABLE_CLAIM", "Tidak ditemukan klaim kesehatan yang cukup jelas untuk diperiksa.", 422)

        claim_results: list[HealthCheckResponse] = []
        used_live = False
        for claim in extracted:
            live_records: list[EvidenceRecord] = []
            notes: list[str] = []
            if self.settings.health_live_retrieval_enabled:
                live = self.live_provider.search(claim.normalized_claim)
                if live.records:
                    live_records = live.records
                    used_live = True
                    notes.append(f"{len(live_records)} record PubMed live ditambahkan ke evidence candidate set.")
                else:
                    # Europe PMC is queried in parallel with the primary route so
                    # a slow/empty PubMed request cannot consume another full timeout.
                    if live.outage:
                        notes.append("PubMed live tidak tersedia; hasil dibandingkan dengan Europe PMC.")
                    else:
                        notes.append("PubMed live tidak menemukan record tambahan; hasil dibandingkan dengan Europe PMC.")
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(self.secondary_live_provider.search, claim.normalized_claim)
                        secondary_records, secondary_outage = future.result(timeout=self.settings.health_fetch_timeout_seconds + 1)
                    if secondary_records:
                        live_records = secondary_records
                        used_live = True
                        notes.append(f"{len(secondary_records)} record Europe PMC live ditambahkan sebagai fallback.")
                    elif secondary_outage:
                        notes.append("Europe PMC live juga tidak tersedia; sistem melanjutkan dengan evidence terverifikasi yang tersimpan.")
                    else:
                        notes.append("Europe PMC tidak menemukan record tambahan yang cukup relevan.")
            else:
                notes.append("Live retrieval nonaktif; gunakan HEALTH_LIVE_RETRIEVAL_ENABLED=true untuk mengaktifkan PubMed provider.")

            provider = CompositeEvidenceProvider(self.base_provider, live_records)
            engine = TrustEngine(provider)
            result = engine.analyze(
                claim.normalized_claim,
                claim_id=claim.claim_id,
                claim_type=claim.claim_type,
                topic=claim.topic,
                original_claim=claim.claim_text,
                retrieval_notes=notes,
            )
            # The result is bound to the exact normalized claim that entered
            # this iteration. Never allow a provider/cache/state bug to return
            # a result for another claim.
            if result.claim != claim.normalized_claim:
                raise HealthCheckerError(
                    "CLAIM_MISMATCH",
                    "Data hasil pemeriksaan tidak sesuai dengan informasi yang diperiksa.",
                    502,
                )
            claim_results.append(result)

        first = claim_results[0]
        retrieval_mode = "curated"
        if payload.input_type == "url":
            retrieval_mode = "url+live+curated" if used_live else "url+curated"
        elif used_live:
            retrieval_mode = "live+curated"

        article_info = None
        if article:
            article_info = ArticleInfo(
                title=article.title,
                publisher=article.publisher,
                published_date=article.published_date,
                author=article.author,
                url=article.url,
                text_length=len(article.main_text),
            )

        # Keep every legacy top-level field equal to the first claim result.
        data = first.model_dump()
        return HealthCheckRunResponse(
            **data,
            run_id=str(uuid.uuid4()),
            input_type=payload.input_type,
            claims=claim_results,
            article=article_info,
            retrieval_mode=retrieval_mode,
            source_outages=list(dict.fromkeys(source_outages)),
            checked_claims=len(claim_results),
        )


health_checker_service = HealthCheckerService()
