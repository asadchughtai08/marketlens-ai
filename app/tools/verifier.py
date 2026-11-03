# app/tools/verifier.py
# Kaam: har extracted item ke saboot ko rules se check karna.
# Gemini par bharosa nahi: wo kehta hai "confidence 0.9", hum page se khud confirm karte hain.
import re
from dataclasses import dataclass
from difflib import SequenceMatcher

# Naam ke aam lafz jinka quote mein hona zaroori nahi
STOP = {"in", "with", "without", "the", "a", "an", "and", "of", "for", "to",
        "pakistan", "our", "by"}

NEAR_MATCH = 0.85      # quote ka kitna hissa page se milna chahiye (near match)
NAME_COVERAGE = 0.6    # naam ke kitne lafz quote mein hone chahiye
MIN_QUOTE_CHARS = 8    # isse chhoti quote saboot nahi


@dataclass
class VerifyResult:
    verdict: str          # verified / weak / unsupported
    confidence: float     # rules ke baad ki final confidence
    reasons: list         # wajohat ke codes
    review_status: str    # approved ya pending


def _squash(text: str) -> str:
    """Punctuation, markdown aur spaces ka farq ignore: 'Hi-MO 6' -> 'hi mo 6'."""
    return re.sub(r"[\W_]+", " ", text.lower()).strip()


def _compact(text: str) -> str:
    """Saari spacing hata do: 'SPH 5000' aur 'SPH5000' barabar ho jayein."""
    return re.sub(r"[\W_]+", "", text.lower())


def quote_match(quote: str, page: str) -> str:
    """exact / near / missing: kya quote sach mein page par hai?"""
    q, p = _squash(quote), _squash(page)
    if not q:
        return "missing"
    if q in p:
        return "exact"
    # Sab se lambi lagatar milti hui tukri (chhoti formatting ke farq ke liye)
    m = SequenceMatcher(None, p, q, autojunk=False).find_longest_match(0, len(p), 0, len(q))
    return "near" if m.size / len(q) >= NEAR_MATCH else "missing"


def name_coverage(name: str, quote: str) -> float:
    """Item ke naam ke kitne lafz quote mein hain (0 se 1)."""
    tokens = [t for t in _squash(name).split() if t not in STOP]
    if not tokens:
        return 1.0
    qset = set(_squash(quote).split())
    qcompact = _compact(quote)
    hits = sum(1 for t in tokens if t in qset or (len(t) >= 3 and t in qcompact))
    return hits / len(tokens)


def capacity_on_page(capacity: str, page: str) -> bool:
    """'5kW' page par ho, magar '15kW' ya '5kWh' se confuse na ho."""
    # "5,000W" ko "5000W" banao taake comma ka masla na ho
    p = re.sub(r"(?<=\d),(?=\d)", "", page.lower())
    m = re.match(r"\s*(\d[\d.,]*)\s*([a-zA-Z]+)", capacity)
    if m:
        num = m.group(1).replace(",", "")
        unit = m.group(2).lower()
        # (?<![\d.]) = number ke pehle koi digit nahi; (?![a-z]) = unit ke baad koi harf nahi
        return re.search(rf"(?<![\d.]){re.escape(num)}\s*{re.escape(unit)}(?![a-z])", p) is not None
    # Ajeeb format (jaise "10-20kW"): seedha compact match
    return _compact(capacity) in _compact(page)


def verify(name: str, brand: str | None, model: str | None, capacity: str | None,
           quote: str, page_text: str, llm_conf: float) -> VerifyResult:
    reasons = []
    conf = max(0.0, min(1.0, llm_conf or 0.0))
    weak = False

    # 1. Quote page par hai?
    qm = quote_match(quote, page_text)
    if qm == "missing":
        reasons.append("quote_missing")
    elif qm == "near":
        reasons.append("quote_near_match")
        weak = True
    else:
        reasons.append("quote_exact")

    if len(_squash(quote)) < MIN_QUOTE_CHARS:
        reasons.append("quote_too_short")
        weak = True

    # 2. Quote isi item ke baare mein hai? (kahin kisi aur cheez ki quote to nahi)
    if name_coverage(name, quote) < NAME_COVERAGE:
        reasons.append("name_not_in_quote")
        weak = True

    # 3. Brand aur model page par maujood hain? (LLM ne khud se to nahi gadha)
    page_compact = _compact(page_text)
    for label, val in (("brand", brand), ("model", model)):
        if val and _compact(val) not in page_compact:
            reasons.append(f"{label}_not_on_page")
            weak = True

    # 4. Capacity page par maujood hai?
    if capacity and not capacity_on_page(capacity, page_text):
        reasons.append("capacity_not_on_page")
        weak = True

    # Faisla
    if qm == "missing":
        return VerifyResult("unsupported", min(conf, 0.2), reasons, "pending")
    if weak:
        return VerifyResult("weak", min(conf, 0.6), reasons, "pending")
    return VerifyResult("verified", max(conf, 0.8), reasons, "approved")