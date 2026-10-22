
# app/tools/normalize.py
# Do kaam: (1) naam ko ek standard shakal dena, (2) check karna ke quote page mein hai.
import re


def normalize_name(name: str) -> str:
    """
    "LONGi Himo9" aur "Longi Hi-MO 9" dono -> "longi himo 9".
    Is se ek hi cheez ke do alag item ya fazool "changes" nahi bante.
    """
    s = name.lower()
    s = s.replace("-", "")                       # Hi-MO -> himo
    s = re.sub(r"[^a-z0-9\s]", " ", s)           # baaki punctuation hatao
    # Letter aur number ke beech space: himo9 -> himo 9, 5kw -> 5 kw
    s = re.sub(r"(?<=[a-z])(?=\d)|(?<=\d)(?=[a-z])", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    # Agar sirf non-latin (e.g. Urdu) naam ho to original hi rakho
    return s or name.lower().strip()


def _squash(text: str) -> str:
    """Punctuation/markdown/spaces ka farq ignore karne ke liye."""
    return re.sub(r"[\W_]+", " ", text.lower()).strip()


def quote_in_text(quote: str, page_text: str) -> bool:
    """Grounding check: kya LLM ki di hui quote sach mein page par hai?"""
    q = _squash(quote)
    return bool(q) and q in _squash(page_text)