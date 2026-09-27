from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

from .evidence_provider import EvidenceRecord

PUBMED_EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

_TRANSLATIONS = {
    "antibiotik": "antibiotic",
    "resistensi antibiotik": "antimicrobial resistance",
    "vaksin": "vaccine",
    "vaksinasi": "immunization",
    "imunisasi": "immunization",
    "autisme": "autism",
    "pilek": "common cold",
    "flu": "influenza",
    "batuk": "cough",
    "gula darah": "blood glucose",
    "diabetes": "diabetes",
    "kolesterol": "cholesterol",
    "ldl": "LDL cholesterol",
    "trigliserida": "triglycerides",
    "daging merah": "red meat",
    "daging berlemak": "fatty meat",
    "daging": "meat",
    "lemak jenuh": "saturated fat",
    "lemak trans": "trans fat",
    "sayur": "vegetable",
    "buah": "fruit",
    "serat": "dietary fiber",
    "garam": "sodium salt",
    "gula": "free sugar",
    "mpasi": "complementary feeding",
    "makanan pendamping": "complementary feeding",
    "asi": "breastfeeding",
    "menyusui": "breastfeeding",
    "bayi": "infant",
    "balita": "child health",
    "anak": "child health",
    "lansia": "older adults ageing",
    "ibu hamil": "maternal health pregnancy",
    "kehamilan": "pregnancy",
    "tekanan darah": "blood pressure",
    "hipertensi": "hypertension",
    "jantung": "cardiovascular disease",
    "stroke": "stroke",
    "obesitas": "obesity",
    "berat badan": "body weight obesity",
    "aktivitas fisik": "physical activity",
    "olahraga": "exercise physical activity",
    "kesehatan jiwa": "mental health",
    "kesehatan mental": "mental health",
    "depresi": "depression",
    "cemas": "anxiety",
    "stres": "stress mental health",
    "dengue": "dengue",
    "dbd": "dengue",
    "demam berdarah": "dengue",
    "malaria": "malaria",
    "tbc": "tuberculosis",
    "tb": "tuberculosis",
    "tuberkulosis": "tuberculosis",
    "hepatitis": "hepatitis",
    "diare": "diarrhea",
    "pneumonia": "pneumonia",
    "kanker": "cancer",
    "kanker paru": "lung cancer",
    "kanker paru paru": "lung cancer",
    "kanker payudara": "breast cancer",
    "kanker serviks": "cervical cancer",
    "kanker leher rahim": "cervical cancer",
    "kanker hati": "liver cancer",
    "kanker lambung": "stomach cancer",
    "kanker usus besar": "colorectal cancer colon cancer",
    "kanker kolorektal": "colorectal cancer",
    "kanker kulit": "skin cancer melanoma",
    "kanker ginjal": "kidney cancer",
    "kanker kandung kemih": "bladder cancer",
    "rokok": "tobacco smoking",
    "merokok": "tobacco smoking",
    "asap rokok": "secondhand smoke tobacco",
    "perokok pasif": "secondhand smoke",
    "alkohol": "alcohol cancer",
    "obesitas": "obesity cancer",
    "gemuk": "obesity cancer",
    "berat badan berlebih": "overweight obesity cancer",
    "sinar uv": "ultraviolet radiation skin cancer",
    "sinar ultraviolet": "ultraviolet radiation skin cancer",
    "paparan matahari": "solar ultraviolet skin cancer",
    "polusi udara": "air pollution lung cancer",
    "asbes": "asbestos lung cancer mesothelioma",
    "benzena": "benzene cancer",
    "arsenik": "arsenic cancer",
    "radon": "radon lung cancer",
    "hpv": "human papillomavirus cervical cancer",
    "hepatitis b": "hepatitis B liver cancer",
    "hepatitis c": "hepatitis C liver cancer",
    "h. pylori": "Helicobacter pylori stomach cancer",
    "h pylori": "Helicobacter pylori stomach cancer",
    "epstein-barr": "Epstein-Barr virus cancer",
    "daging olahan": "processed meat colorectal cancer",
    "daging merah": "red meat colorectal cancer",
    "kurang olahraga": "physical inactivity cancer",
    "kurang aktivitas fisik": "physical inactivity cancer",
    "karies": "dental caries",
    "gigi": "oral health dental",
    "keamanan pangan": "food safety",
    "keracunan makanan": "foodborne illness",
    "rokok": "tobacco smoking",
    "merokok": "tobacco smoking",
    "alkohol": "alcohol",
    "tidur": "sleep",
    "malam": "night late eating",
    "larut": "late eating",
    "makan malam": "dinner meal timing late eating",
    "makan pada malam": "late eating meal timing",
    "gendut": "obesity weight gain",
    "gemuk": "obesity weight gain",
    "berat badan naik": "weight gain",
    "berat badan": "body weight obesity weight gain",
    "membuat": "risk association",
    "menyebabkan": "risk association",
    "mengakibatkan": "risk association",
    "maag": "gastroesophageal reflux GERD dyspepsia gastritis",
    "asam lambung": "gastroesophageal reflux GERD acid reflux",
    "refluks": "gastroesophageal reflux GERD acid reflux",
    "gerd": "gastroesophageal reflux GERD",
    "telat makan": "late eating late meal timing dinner timing",
    "pedas": "spicy food gastroesophageal reflux GERD",
    "makanan pedas": "spicy food gastroesophageal reflux GERD",
    "kopi": "coffee caffeine gastroesophageal reflux GERD",
    "kafein": "caffeine gastroesophageal reflux GERD",
    "gorengan": "fried food dietary fat cardiovascular risk",
    "kurang tidur": "sleep deprivation sleep duration obesity hypertension",
    "tidur kurang": "sleep deprivation sleep duration obesity hypertension",
    "vitamin c": "vitamin C common cold",
    "madu": "honey cough upper respiratory infection",
    "batuk": "cough honey upper respiratory infection",
    "dehidrasi": "dehydration fluid intake",
    "kurang air": "dehydration fluid intake",
    "sembelit": "constipation dietary fiber fluid intake",
    "susah buang air besar": "constipation dietary fiber fluid intake",
    "konstipasi": "constipation dietary fiber fluid intake",
    "jerawat": "acne high glycemic diet",
    "susu": "milk lactose intolerance",
    "laktosa": "lactose intolerance",
    "diare": "diarrhea gastroenteritis",
    "luka": "wound care wound infection",
    "luka terbuka": "wound care wound infection",
    "bernanah": "wound infection pus",
    "nanah": "pus wound infection",
    "infeksi luka": "wound infection",
    "cuci ayam": "washing raw chicken food safety",
    "ayam mentah": "raw chicken food safety",
    "mimisan": "nosebleed epistaxis first aid",
    "hidung berdarah": "nosebleed epistaxis first aid",
    "luka bakar": "burn scald cool running water",
    "terbakar": "burn scald first aid",
    "cegukan": "hiccups self care",
    "kurang minum": "dehydration fluid intake",
    "makan telat": "late eating late meal timing dinner timing",
    "makan larut": "late eating late meal timing dinner timing",
    "mencegah": "prevention",
    "menyembuhkan": "treatment",
    "mengobati": "treatment",
}


_WORD_RE = re.compile(r"[A-Za-zÀ-ÿ0-9]+")
_STOPWORDS = {
    "yang", "dan", "atau", "untuk", "dengan", "dapat", "bisa", "karena", "adalah", "akan", "lebih", "dari",
    "pada", "dalam", "this", "that", "with", "from", "does", "can", "could", "health", "kesehatan",
}

_CONTRADICT_CUES = (
    "no evidence", "not associated", "not effective", "did not reduce", "does not reduce", "no significant",
    "failed to", "not support", "no benefit", "unlikely to", "does not improve",
)
_SUPPORT_CUES = (
    "was associated with", "is associated with", "significantly reduced", "significantly improved", "effective in",
    "benefit", "improved", "reduced risk", "increased risk", "higher risk", "greater risk",
    "positive association", "significantly associated", "higher odds", "higher prevalence",
    "supports the use", "protective effect", "increases the risk",
)


@dataclass(frozen=True)
class LiveRetrievalResult:
    records: list[EvidenceRecord]
    outage: str | None = None


def build_pubmed_query(claim: str) -> str:
    """Build a compact concept-oriented PubMed query.

    Claims are written in Indonesian, while PubMed literature is usually
    indexed with English scientific concepts. The query therefore uses OR
    groups for synonyms instead of AND-ing every literal claim word.
    """
    lowered = re.sub(r"\s+", " ", claim.lower()).strip()
    groups: list[list[str]] = []

    if any(term in lowered for term in ("kanker", "cancer", "tumor", "karsinogen", "carcinogen")):
        groups.append(["cancer", "cancer risk", "cancer prevention", "neoplasm", "malignancy"])
    if any(term in lowered for term in ("rokok", "merokok", "tobacco", "smoking", "asap rokok", "perokok pasif")):
        groups.append(["tobacco", "smoking", "cigarette smoking", "secondhand smoke", "lung cancer", "cancer"])
    if any(term in lowered for term in ("alkohol", "alcohol")):
        groups.append(["alcohol", "alcohol consumption", "cancer", "breast cancer", "liver cancer", "colorectal cancer"])
    if any(term in lowered for term in ("obesitas", "gemuk", "berat badan berlebih", "overweight", "obesity")):
        groups.append(["obesity", "overweight", "excess body weight", "cancer", "colorectal cancer", "breast cancer"] )
    if any(term in lowered for term in ("sinar uv", "sinar ultraviolet", "paparan matahari", "sunburn", "tanning", "ultraviolet")):
        groups.append(["ultraviolet radiation", "solar radiation", "sun exposure", "skin cancer", "melanoma"])
    if any(term in lowered for term in ("polusi udara", "pencemaran udara", "pm2.5", "asap kendaraan", "air pollution")):
        groups.append(["air pollution", "particulate matter", "PM2.5", "lung cancer", "cancer"])
    if any(term in lowered for term in ("asbes", "asbestos", "benzena", "benzene", "arsenik", "arsenic", "silika", "silica", "radon", "paparan kerja")):
        groups.append(["occupational exposure", "occupational carcinogen", "asbestos", "benzene", "arsenic", "silica", "radon", "lung cancer", "mesothelioma", "cancer"])
    if any(term in lowered for term in ("hpv", "hepatitis b", "hepatitis c", "h. pylori", "h pylori", "epstein-barr", "ebv", "infeksi penyebab kanker")):
        groups.append(["cancer causing infection", "HPV", "hepatitis B", "hepatitis C", "Helicobacter pylori", "Epstein-Barr virus", "cancer"])
    if any(term in lowered for term in ("daging olahan", "processed meat", "daging merah", "red meat")):
        groups.append(["processed meat", "red meat", "colorectal cancer", "colon cancer", "cancer"])

    if any(term in lowered for term in ("makan malam", "makan pada malam", "malam", "larut", "telat makan", "makan telat", "makan larut", "night")):
        groups.append(["late eating", "late meal timing", "meal timing", "dinner timing", "night eating"])
    if any(term in lowered for term in ("asam lambung", "refluks", "gerd", "acid reflux", "heartburn", "maag")):
        groups.append(["gastroesophageal reflux", "GERD", "acid reflux", "heartburn", "reflux symptoms"])
    if any(term in lowered for term in ("pedas", "makanan pedas", "spicy food")):
        groups.append(["spicy food", "gastroesophageal reflux", "GERD", "reflux symptoms"])
    if any(term in lowered for term in ("luka", "luka terbuka", "bernanah", "nanah", "infeksi luka", "wound")):
        groups.append(["wound care", "wound infection", "pus", "wound healing", "infection"] )
    if any(term in lowered for term in ("mimisan", "hidung berdarah", "nosebleed")):
        groups.append(["nosebleed", "epistaxis", "first aid"] )
    if any(term in lowered for term in ("luka bakar", "terbakar", "burn", "scald")):
        groups.append(["burn", "scald", "cool running water", "first aid"] )
    if any(term in lowered for term in ("cegukan", "hiccups")):
        groups.append(["hiccups", "self care", "water"] )
    if any(term in lowered for term in ("susu", "laktosa", "lactose")):
        groups.append(["milk", "lactose intolerance", "lactose", "diarrhea", "bloating"] )
    if any(term in lowered for term in ("jerawat", "acne")):
        groups.append(["acne", "high glycemic diet", "low glycemic diet", "skin"] )
    if any(term in lowered for term in ("sembelit", "susah buang air besar", "konstipasi")):
        groups.append(["constipation", "dietary fiber", "fluid intake", "bowel movement"] )
    if any(term in lowered for term in ("ayam mentah", "cuci ayam", "mencuci ayam")):
        groups.append(["raw chicken", "washing chicken", "food safety", "food poisoning"] )
    if any(term in lowered for term in ("kopi", "kafein", "coffee", "caffeine")):
        groups.append(["coffee", "caffeine", "gastroesophageal reflux", "GERD"])
    if any(term in lowered for term in ("kurang tidur", "tidur kurang", "sleep deprivation")):
        groups.append(["sleep deprivation", "short sleep", "sleep duration", "obesity", "hypertension"])
    if any(term in lowered for term in ("vitamin c", "vitamin c")):
        groups.append(["vitamin C", "common cold", "upper respiratory infection"])
    if any(term in lowered for term in ("madu", "honey")) and "batuk" in lowered:
        groups.append(["honey", "cough", "upper respiratory infection"])
    if any(term in lowered for term in ("gendut", "gemuk", "obesitas", "berat badan", "weight", "obesity")):
        groups.append(["obesity", "weight gain", "body weight", "body mass index", "BMI"])
    if any(term in lowered for term in ("gula", "manis", "minuman manis", "makanan manis", "sugar", "sweet")):
        groups.append(["sugar", "sugar-sweetened beverages", "sweetened beverages", "added sugar", "dietary sugar"])
    if "diabetes" in lowered or "diabet" in lowered:
        groups.append(["type 2 diabetes", "diabetes mellitus", "diabetes", "T2D"])
    if any(term in lowered for term in ("kolesterol", "ldl", "trigliserida")):
        groups.append(["cholesterol", "LDL cholesterol", "triglycerides", "dyslipidemia"])
    if any(term in lowered for term in ("tekanan darah", "hipertensi")):
        groups.append(["blood pressure", "hypertension"])
    if any(term in lowered for term in ("jantung", "kardiovaskular", "stroke")):
        groups.append(["cardiovascular disease", "heart disease", "stroke"])
    if any(term in lowered for term in ("aktivitas fisik", "olahraga", "exercise", "physical activity")):
        groups.append(["physical activity", "exercise", "physical fitness", "sedentary behavior"])
    if any(term in lowered for term in ("kesehatan mental", "kesehatan jiwa", "depresi", "cemas", "stres")):
        groups.append(["mental health", "depression", "anxiety", "stress"])
    if any(term in lowered for term in ("menyebabkan", "mengakibatkan", "membuat", "meningkatkan risiko", "risiko", "risk")):
        groups.append(["risk", "association", "incidence", "odds"])

    translated: list[str] = []
    for source, target in sorted(_TRANSLATIONS.items(), key=lambda item: len(item[0]), reverse=True):
        if source in lowered and target not in translated:
            translated.append(target)
    if translated:
        groups.append(translated[:5])

    if not groups:
        words = [word.lower() for word in _WORD_RE.findall(claim) if len(word) >= 4]
        words = [word for word in words if word not in _STOPWORDS and word.isascii()]
        return " AND ".join(f'"{word}"' for word in words[:6]) or claim[:160]

    normalized_groups: list[list[str]] = []
    seen_groups: set[tuple[str, ...]] = set()
    for group in groups:
        unique: list[str] = []
        seen_terms: set[str] = set()
        for term in group:
            normalized = term.lower().strip()
            if normalized and normalized not in seen_terms:
                unique.append(term)
                seen_terms.add(normalized)
        key = tuple(sorted(seen_terms))
        if unique and key not in seen_groups:
            normalized_groups.append(unique)
            seen_groups.add(key)

    return " AND ".join(
        "(" + " OR ".join(f'"{term}"' if " " in term else term for term in group) + ")"
        for group in normalized_groups[:8]
    )


def _text(node: ET.Element | None) -> str:
    return " ".join("".join(node.itertext()).split()) if node is not None else ""


def _publication_date(article: ET.Element) -> str:
    year = _text(article.find(".//PubDate/Year"))
    month = _text(article.find(".//PubDate/Month"))
    day = _text(article.find(".//PubDate/Day"))
    if not year:
        medline = _text(article.find(".//PubDate/MedlineDate"))
        match = re.search(r"(19|20)\d{2}", medline)
        year = match.group(0) if match else ""
    if not year:
        return ""
    month_map = {name: idx for idx, name in enumerate(("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), 1)}
    try:
        month_num = int(month) if month.isdigit() else month_map.get(month[:3].title(), 1)
        day_num = int(day) if day.isdigit() else 1
        return date(int(year), max(1, min(12, month_num)), max(1, min(28, day_num))).isoformat()
    except (ValueError, TypeError):
        return f"{year}-01-01"


def _infer_stance(abstract: str) -> str:
    lowered = abstract.lower()
    if any(cue in lowered for cue in _CONTRADICT_CUES):
        return "contradict"
    if any(cue in lowered for cue in _SUPPORT_CUES):
        return "support"
    return "neutral"


def _keywords_from_query(query: str) -> tuple[str, ...]:
    phrases = re.findall(r'"([^"]+)"', query.lower())
    stripped = re.sub(r'"[^"]+"', ' ', query.lower())
    words = [term for term in re.findall(r"[a-z0-9]+", stripped) if len(term) >= 3 and term not in {"and", "or"}]
    terms = phrases + words
    return tuple(dict.fromkeys(terms[:18]))



class PubMedEvidenceProvider:
    """Optional live PubMed retrieval using NCBI E-utilities.

    No API key is required for low-volume development requests. Retrieved records
    are source-traceable. Stance inference is deliberately conservative; ambiguous
    abstracts stay NEUTRAL and therefore cannot manufacture a directional verdict.
    """

    def __init__(self, *, timeout: float = 6.0, max_results: int = 3):
        self.timeout = timeout
        self.max_results = max(1, min(8, max_results))

    def search(self, claim: str) -> LiveRetrievalResult:
        query = build_pubmed_query(claim)
        if len(query.strip()) < 3:
            return LiveRetrievalResult([])
        try:
            ids = self._search_ids(query)
            if not ids:
                return LiveRetrievalResult([])
            return LiveRetrievalResult(self._fetch_records(ids, query))
        except Exception as exc:
            return LiveRetrievalResult([], outage=f"PubMed live retrieval unavailable ({exc.__class__.__name__}).")

    def _get(self, endpoint: str, params: dict[str, str]) -> bytes:
        url = f"{PUBMED_EUTILS}/{endpoint}?{urlencode(params)}"
        req = Request(url, headers={"User-Agent": "SEHATIN-HealthChecker/1.0"})
        with urlopen(req, timeout=self.timeout) as response:  # noqa: S310 - fixed trusted NCBI host
            return response.read(1_500_000)

    def _search_ids(self, query: str) -> list[str]:
        payload = self._get(
            "esearch.fcgi",
            {"db": "pubmed", "retmode": "json", "retmax": str(self.max_results), "sort": "relevance", "term": query},
        )
        data = json.loads(payload.decode("utf-8"))
        return [str(item) for item in data.get("esearchresult", {}).get("idlist", [])][: self.max_results]

    def _fetch_records(self, ids: list[str], query: str) -> list[EvidenceRecord]:
        payload = self._get("efetch.fcgi", {"db": "pubmed", "id": ",".join(ids), "retmode": "xml"})
        root = ET.fromstring(payload)
        now = datetime.now(timezone.utc).date().isoformat()
        keywords = _keywords_from_query(query)
        records: list[EvidenceRecord] = []
        for article in root.findall(".//PubmedArticle"):
            pmid = _text(article.find(".//PMID"))
            title = _text(article.find(".//ArticleTitle"))
            abstract_parts = [_text(node) for node in article.findall(".//Abstract/AbstractText")]
            abstract = " ".join(part for part in abstract_parts if part)
            if not pmid or not title or len(abstract) < 40:
                continue
            journal = _text(article.find(".//Journal/Title")) or "PubMed indexed journal"
            excerpt = abstract[:700].rsplit(" ", 1)[0] if len(abstract) > 700 else abstract
            records.append(
                EvidenceRecord(
                    id=f"pubmed-{pmid}",
                    source_id=f"pubmed:{pmid}",
                    keywords=keywords,
                    title=title,
                    source=journal,
                    source_type="peer_reviewed",
                    publication_date=_publication_date(article),
                    retrieved_at=now,
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    canonical_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    stance=_infer_stance(abstract),
                    excerpt=excerpt,
                    quality=0.82,
                    authority_level=3,
                    authority_score=0.84,
                    verified=True,
                    demo=False,
                    provider="pubmed-live",
                    independent_group=f"pubmed:{pmid}",
                    trace_note="Live metadata/abstract retrieved from PubMed via NCBI E-utilities.",
                )
            )
        return records
