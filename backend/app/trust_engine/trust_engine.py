from __future__ import annotations

from datetime import datetime, timezone
import re

from app.knowledge_base.provider_factory import build_evidence_provider
from app.schemas.health_checker import EvidenceItem, EvidenceTrace, HealthCheckResponse, ScoreBreakdown, ScoringWeights, SourceSummary

from .claim_analyzer import claim_evidence_relevance, concept_groups, normalize_claim, orient_stance, token_relevance
from .confidence_score import agreement_score, claim_support_score, verdict_confidence_score
from .config import DEFAULT_TRUST_WEIGHTS, MAX_EVIDENCE_RESULTS, MIN_EVIDENCE_RELEVANCE
from .evidence_provider import EvidenceProvider, EvidenceRecord
from .evidence_ranker import recency_score, weighted_evidence_score
from .live_evidence_provider import build_pubmed_query
from .source_validator import canonicalize_url, source_authority, source_is_usable, source_reason, source_tier


class TrustEngine:
    """Explainable deterministic evidence scorer.

    Evidence quality is computed from source authority, evidence quality,
    recency and claim relevance. Source agreement/diversity contributes to
    verdict confidence. Trust Score is evidence-weighted support for the claim,
    not absolute truth. Ambiguous NEUTRAL evidence can be displayed but cannot
    force a directional verdict.
    """

    def __init__(self, provider: EvidenceProvider | None = None):
        self.provider = provider or build_evidence_provider()

    @staticmethod
    def _deduplicate(records: list[EvidenceRecord]) -> list[EvidenceRecord]:
        seen: set[tuple[str, str]] = set()
        deduped: list[EvidenceRecord] = []
        for evidence in records:
            canonical = evidence.canonical_url or canonicalize_url(evidence.url)
            underlying = evidence.independent_group or canonical
            key = (underlying.casefold(), evidence.title.strip().casefold())
            if key in seen:
                continue
            seen.add(key)
            deduped.append(evidence)
        return deduped

    def analyze(
        self,
        text: str,
        *,
        claim_id: str | None = None,
        claim_type: str | None = None,
        topic: str | None = None,
        original_claim: str | None = None,
        retrieval_notes: list[str] | None = None,
    ) -> HealthCheckResponse:
        claim = normalize_claim(text)
        ranked: list[EvidenceItem] = []
        # Use the same deterministic scientific-term expansion used by PubMed
        # retrieval when checking relevance. This lets an Indonesian claim such
        # as "makan pada malam hari" match evidence indexed as "late eating"
        # without making the LLM or a keyword guess the verdict.
        retrieval_context = f"{claim} {build_pubmed_query(claim)}"
        relevance_context = retrieval_context
        for generic_term in ("risk", "association", "incidence", "odds", "evidence"):
            relevance_context = relevance_context.replace(generic_term, " ")

        for evidence in self._deduplicate(self.provider.records()):
            if not source_is_usable(evidence.url, evidence.verified):
                continue
            # Score against both the provider's explicit concept keywords and
            # the actual evidence title/excerpt. Live PubMed records previously
            # stored query tokens only, so a scientifically relevant article
            # could be discarded merely because the Indonesian wording differed.
            generic_topic_terms = {
                "risk", "association", "incidence", "odds", "evidence", "health", "kesehatan",
                "bmi", "body mass index", "pilek", "common cold", "flu", "virus",
                "diabetes", "obesity", "obesitas", "cancer", "kanker", "stroke",
                "hypertension", "hipertensi", "jantung", "heart disease", "nutrition", "gizi",
                "gastroesophageal reflux", "gerd", "acid reflux", "reflux symptoms", "heartburn",
                "dyspepsia", "gastritis", "maag",
            }
            relevance_keywords = tuple(
                keyword
                for keyword in evidence.keywords
                if keyword.lower() not in generic_topic_terms
            )
            keyword_relevance = token_relevance(relevance_context, relevance_keywords)

            # A source that matches only a broad disease/topic word (for
            # example "pilek") is not evidence for a different intervention
            # such as vitamin C. It may remain a topic anchor elsewhere, but it
            # cannot influence this claim's verdict.
            all_keywords = tuple(keyword.lower() for keyword in evidence.keywords)
            context_lower = relevance_context.lower()

            def has_concept(keyword: str) -> bool:
                # Use token/phrase boundaries instead of substring matching.
                # Without boundaries, a keyword such as "pus" can accidentally
                # match the word "corpus" in an unrelated claim.
                pattern = r"(?<![a-z0-9])" + re.escape(keyword) + r"(?![a-z0-9])"
                return re.search(pattern, context_lower) is not None

            specific_overlap = any(
                keyword not in generic_topic_terms and has_concept(keyword)
                for keyword in all_keywords
            )
            claim_groups = concept_groups(claim)
            evidence_groups = concept_groups(f"{evidence.title} {evidence.excerpt}")
            concept_overlap = bool(claim_groups.keys() & evidence_groups.keys())
            if not specific_overlap and not concept_overlap:
                # Title/excerpt similarity alone is not enough. Generic words
                # such as "health", "water", "blood" or "evidence" can occur
                # in many unrelated records and previously caused accidental
                # matches. A source must first share at least one known
                # claim-specific concept, either through provider keywords or
                # through the normalized concept registry.
                continue

            # The provider keyword list can be generated from the search query,
            # so it is not enough to prove that the returned article itself
            # discusses the relationship in the user's claim. Check the actual
            # title + abstract/excerpt and require the relevant concept sides
            # to be present there. This blocks false matches such as a scalp
            # abscess article being used for "luka terkena air menyebabkan
            # nanah" merely because both contain "wound" and "infection".
            semantic_relevance = claim_evidence_relevance(
                claim,
                f"{evidence.title} {evidence.excerpt}",
            )
            # Unknown/general claims keep the existing lexical relevance path.
            # Known relationship claims use the stricter two-sided concept check.
            # When a source covers only one side of a known claim, keep it as
            # neutral context instead of returning an empty result. This makes
            # common health questions discoverable while preventing a partial
            # match from affecting the true/false verdict.
            known_claim = bool(claim_groups)
            if semantic_relevance == 0.0 and not known_claim:
                semantic_relevance = 1.0
            if semantic_relevance == 0.0:
                # The provider keyword index may know that a source belongs to
                # the topic even when the short title/excerpt does not repeat
                # the exact concept. Keep it as context so common searches do
                # not look empty, but its stance is forced to neutral below.
                if known_claim and specific_overlap:
                    semantic_relevance = 0.5
                else:
                    continue

            # One strong, claim-specific concept (for example "antibiotik"
            # in an antibiotic claim) is enough to keep a source candidate
            # alive; generic topic words are explicitly excluded above.
            keyword_relevance = max(keyword_relevance, 0.70)
            title_relevance = token_relevance(relevance_context, tuple(
                token for token in evidence.title.lower().split() if len(token) >= 3
            ))
            excerpt_relevance = token_relevance(relevance_context, tuple(
                token for token in evidence.excerpt.lower().split() if len(token) >= 4
            ))
            # Explicit concept-keyword overlap is the anchor. Title/excerpt
            # context can refine relevance but can never make a generic claim
            # relevant by itself (e.g. an unrelated article containing the word
            # "evidence").
            relevance = round(
                0.65 * keyword_relevance + 0.25 * title_relevance + 0.10 * excerpt_relevance,
                4,
            )
            if relevance < MIN_EVIDENCE_RELEVANCE:
                continue
            authority = source_authority(
                evidence.source_type,
                declared_score=evidence.authority_score,
                verified=evidence.verified,
            )
            try:
                recency = recency_score(evidence.publication_date)
            except (ValueError, TypeError):
                recency = 0.6
            weighted = weighted_evidence_score(authority, evidence.quality, recency, relevance)
            canonical = evidence.canonical_url or canonicalize_url(evidence.url)
            ranked.append(
                EvidenceItem(
                    id=evidence.id,
                    source_id=evidence.source_id or evidence.id,
                    title=evidence.title,
                    source=evidence.source,
                    source_type=evidence.source_type,
                    publication_date=evidence.publication_date,
                    retrieved_at=evidence.retrieved_at,
                    url=evidence.url,
                    canonical_url=canonical,
                    # A partial concept match is useful context but must not
                    # be presented as directional evidence for the whole claim.
                    stance=(
                        orient_stance(evidence.stance, claim)
                        if semantic_relevance >= 1.0
                        else "neutral"
                    ),
                    excerpt=evidence.excerpt,
                    authority_level=evidence.authority_level,
                    authority_score=authority,
                    evidence_quality_score=evidence.quality,
                    recency_score=recency,
                    relevance_score=relevance,
                    weighted_score=weighted,
                    demo=evidence.demo,
                    verified=evidence.verified,
                    provider=evidence.provider,
                    independent_group=evidence.independent_group or canonical,
                    trace_note=evidence.trace_note,
                )
            )

        ranked.sort(key=lambda item: item.weighted_score, reverse=True)
        ranked = ranked[:MAX_EVIDENCE_RESULTS]
        supporting = [item for item in ranked if item.stance == "support"]
        contradicting = [item for item in ranked if item.stance == "contradict"]
        neutral = [item for item in ranked if item.stance == "neutral"]

        support_publishers = {item.independent_group or item.source for item in supporting}
        contradict_publishers = {item.independent_group or item.source for item in contradicting}
        publishers = {item.independent_group or item.source for item in ranked}
        agreement = agreement_score(support_publishers, contradict_publishers)

        support_scores = [item.weighted_score for item in supporting]
        contradict_scores = [item.weighted_score for item in contradicting]
        trust_score = claim_support_score(support_scores, contradict_scores)
        evidence_confidence = verdict_confidence_score(
            support_scores,
            contradict_scores,
            agreement,
            len(support_publishers | contradict_publishers),
        )

        verdict, explanation, why = self._map_verdict(
            supporting=supporting,
            contradicting=contradicting,
            agreement=agreement,
            claim=claim,
        )

        if verdict == "INSUFFICIENT_EVIDENCE":
            evidence_level = "INSUFFICIENT"
        elif evidence_confidence >= 75:
            evidence_level = "HIGH"
        elif evidence_confidence >= 45:
            evidence_level = "MODERATE"
        else:
            evidence_level = "LOW"

        confidence_label = evidence_level

        if ranked:
            average_authority = sum(x.authority_score for x in ranked) / len(ranked)
            average_quality = sum(x.evidence_quality_score for x in ranked) / len(ranked)
            average_recency = sum(x.recency_score for x in ranked) / len(ranked)
            average_relevance = sum(x.relevance_score for x in ranked) / len(ranked)
        else:
            average_authority = average_quality = average_recency = average_relevance = 0.0

        source_map: dict[tuple[str, str], SourceSummary] = {}
        for item in ranked:
            key = (item.source, item.canonical_url or item.url)
            source_map[key] = SourceSummary(
                name=item.source,
                title=item.title,
                source_type=item.source_type,
                publication_date=item.publication_date,
                url=item.url,
                last_checked=item.retrieved_at,
                verified=item.verified,
                authority_level=source_tier(item.source_type),
                provider=item.provider,
                why_considered=source_reason(item.source_type, item.verified),
            )

        limitations = [
            "Trust Score merupakan ringkasan transparan dari evidence yang ditemukan, bukan jaminan kebenaran absolut.",
            "Evidence confidence menilai kekuatan evidence untuk verdict, bukan kepastian medis.",
            "Hasil tidak menggantikan diagnosis atau saran tenaga kesehatan.",
        ]
        if ranked and all(item.demo for item in ranked):
            limitations.insert(0, "Evidence yang digunakan berasal dari curated snapshot, bukan pencarian ilmiah real-time.")
        elif any(not item.demo for item in ranked):
            limitations.insert(0, "Live evidence dapat berubah; metadata dan abstract yang tersedia tidak selalu cukup untuk menilai keseluruhan studi.")
        if neutral and not supporting and not contradicting:
            limitations.append("Sumber relevan ditemukan, tetapi arah evidence belum cukup jelas untuk membuat verdict directional.")

        trace = [
            EvidenceTrace(evidence_id=item.id, source_name=item.source, source_url=item.url, stance=item.stance)
            for item in ranked
        ]

        return HealthCheckResponse(
            claim=claim,
            original_claim=original_claim or text,
            normalized_claim=claim,
            claim_id=claim_id,
            claim_type=claim_type,
            topic=topic,
            verdict=verdict,
            result=verdict,
            trust_score=trust_score,
            evidence_confidence=evidence_confidence,
            confidence=evidence_confidence,
            confidence_label=confidence_label,
            score_breakdown=ScoreBreakdown(
                source_authority=round(average_authority, 3),
                evidence_quality=round(average_quality, 3),
                recency=round(average_recency, 3),
                relevance=round(average_relevance, 3),
                source_agreement=round(agreement, 3),
                independent_publishers=len(publishers),
            ),
            scoring_weights=ScoringWeights(
                source_authority=DEFAULT_TRUST_WEIGHTS.source_authority,
                evidence_quality=DEFAULT_TRUST_WEIGHTS.evidence_quality,
                recency=DEFAULT_TRUST_WEIGHTS.recency,
                claim_relevance=DEFAULT_TRUST_WEIGHTS.claim_relevance,
            ),
            evidence_level=evidence_level,
            explanation=explanation,
            summary=explanation,
            why_this_result=why,
            reason=why,
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            neutral_evidence=neutral,
            sources=list(source_map.values()),
            sources_checked=len(ranked),
            last_checked=datetime.now(timezone.utc).isoformat(),
            limitations=limitations,
            demo_evidence=all(item.demo for item in ranked) if ranked else self.provider.is_demo,
            evidence_trace=trace,
            retrieval_notes=retrieval_notes or [],
        )

    @staticmethod
    def _map_verdict(
        supporting: list[EvidenceItem],
        contradicting: list[EvidenceItem],
        agreement: float,
        claim: str,
    ) -> tuple[str, str, str]:
        if not supporting and not contradicting:
            return (
                "INSUFFICIENT_EVIDENCE",
                "Bukti yang ditemukan belum cukup untuk memastikan informasi ini benar atau salah.",
                "Sumber yang diperiksa membahas topik yang berkaitan, tetapi belum memberikan bukti yang cukup untuk memastikan hubungan dalam informasi ini.",
            )

        if supporting and contradicting:
            support_strength = sum(x.weighted_score for x in supporting)
            contradict_strength = sum(x.weighted_score for x in contradicting)
            if abs(support_strength - contradict_strength) < 0.25:
                return (
                    "PARTIALLY_SUPPORTED",
                    "Bukti yang ditemukan tidak sepenuhnya searah.",
                    "Ada sumber yang mendukung dan ada sumber yang memberikan hasil berbeda, sehingga hasil tidak disederhanakan menjadi benar atau salah.",
                )
            if support_strength > contradict_strength:
                return (
                    "PARTIALLY_SUPPORTED",
                    "Bukti lebih banyak mendukung informasi ini, tetapi masih ada batasan yang perlu diperhatikan.",
                    "Arah bukti lebih banyak mendukung, namun sebagian sumber memberikan batasan atau hasil yang berbeda.",
                )
            return (
                "CONTRADICTED",
                "Bukti yang ditemukan tidak mendukung informasi ini.",
                "Beberapa sumber yang relevan menunjukkan hasil yang berbeda dari informasi yang diperiksa.",
            )

        if contradicting:
            return (
                "CONTRADICTED",
                "Bukti yang ditemukan menunjukkan hasil yang berbeda dari informasi ini.",
                "Sumber yang relevan lebih banyak menunjukkan hasil yang berbeda dari informasi yang diperiksa.",
            )

        causal = any(
            cue in claim.lower()
            for cue in ("menyebabkan", "mengakibatkan", "membuat", "akan", "dapat", "menyembuhkan", "mencegah", "cause", "causes", "cure", "prevents")
        )
        association_only = all(
            any(marker in (item.trace_note or "").lower() for marker in ("association", "asosiasi", "does not establish", "tidak establish", "not an absolute causal", "not proof", "proof of causation", "tidak membuktikan"))
            for item in supporting
        )
        if causal and association_only:
            return (
                "PARTIALLY_SUPPORTED",
                "Bukti yang ditemukan mendukung hubungan ini, tetapi belum cukup untuk menyatakan hubungan sebab-akibat secara pasti.",
                "Sumber yang relevan menemukan hubungan atau peningkatan risiko, tetapi tidak membuktikan bahwa satu hal selalu secara langsung menyebabkan hal lainnya.",
            )

        return (
            "SUPPORTED",
            "Bukti yang ditemukan mendukung informasi ini.",
            "Sumber yang relevan menunjukkan hasil yang sejalan dengan informasi yang diperiksa.",
        )


trust_engine = TrustEngine()


def analyze_claim(text: str) -> HealthCheckResponse:
    return trust_engine.analyze(text)
