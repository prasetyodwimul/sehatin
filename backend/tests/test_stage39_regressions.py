from __future__ import annotations

import pytest
from pydantic import ValidationError
from xml.etree import ElementTree as ET

from app.schemas.nutrition_program import ExtensionCreateRequest
from app.trust_engine.evidence_ranker import recency_score
from app.trust_engine.live_evidence_provider import _publication_date


def test_extension_contract_only_accepts_program_goal_choices():
    for preference in ("same_goal", "smaller_goal", "different_goal"):
        assert ExtensionCreateRequest(confirm=True, preference=preference).preference == preference
    with pytest.raises(ValidationError):
        ExtensionCreateRequest(confirm=True, preference="consult")


def test_pubmed_missing_publication_date_stays_unknown_and_is_not_scored_as_new():
    article = ET.fromstring("<PubmedArticle><Article><ArticleTitle>Example</ArticleTitle></Article></PubmedArticle>")
    assert _publication_date(article) == ""
    assert recency_score("") == 0.6
