# app/tools/categories.py
# Kaam: agent ki di hui category ("suggested_category") ko approved category se jodna.
# Matching free aur simple hai: aliases + fuzzy string match (embeddings baad mein, Phase 4).
import re
from difflib import SequenceMatcher

from sqlalchemy import select

from app.db.models import Category, Item, Presence

# Starter categories (approved). Har ke saath milte julte naam (aliases).
# Nayi category ya alias baad mein review queue se aati hain, yahan hardcode karna zaroori nahi.
SEED = {
    "solar panel": ["pv module", "pv panel", "solar module", "photovoltaic panel"],
    "inverter": ["solar inverter", "on grid inverter", "off grid inverter",
                 "grid tie inverter"],
    "hybrid inverter": ["hybrid solar inverter", "hybrid on grid inverter"],
    "battery": ["solar battery", "lithium battery", "lithium ion battery",
                "lead acid battery", "energy storage", "battery storage"],
    "solar package": ["solar system", "residential package", "commercial package",
                      "solar kit", "complete solar system", "solar bundle"],
    "mounting structure": ["mounting", "solar mounting", "panel mounting",
                           "mounting system", "solar structure", "racking"],
    "monitoring": ["monitoring app", "remote monitoring", "wifi monitoring",
                   "wi fi monitoring", "monitoring system", "monitoring service"],
    "ev charger": ["ev charging station", "car charger", "electric vehicle charger",
                   "ev charging", "ev charger installation"],
    "water pump": ["solar water pump", "solar pump", "solar tubewell",
                   "water pumping system"],
    "smart meter": ["smart energy meter", "energy meter", "bidirectional meter",
                    "smart metering"],
    "net metering": ["net metering service", "net metering support",
                     "net metering application"],
    "maintenance": ["maintenance service", "panel cleaning", "cleaning service",
                    "om service", "annual maintenance"],
    "financing": ["installment", "installment plan", "easy installment",
                  "bank financing"],
    "accessories": ["accessory", "solar accessories", "cables", "wiring"],
}

# Bohat aam lafz: inse koi category nahi banti (warna review queue gandi hogi)
GENERIC = {"service", "product", "feature", "solution", "other", "item",
           "general", "solar", "offer"}

# Fuzzy match ki kam az kam similarity (0 se 1)
FUZZY_THRESHOLD = 0.88


def _singular(token: str) -> str:
    """panels -> panel, batteries -> battery. Dono taraf same rule, is liye match barabar."""
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def norm_label(text: str) -> str:
    """'Wi-Fi Monitoring Apps' -> 'wi fi monitoring app'."""
    s = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    return " ".join(_singular(t) for t in s.split())


def seed_categories(db) -> int:
    """Starter categories banata hai. Dobara chalane se duplicate nahi banti."""
    created = 0
    for name, aliases in SEED.items():
        cat = db.scalar(select(Category).where(Category.name == name))
        if cat is None:
            db.add(Category(name=name, status="approved", aliases=list(aliases)))
            created += 1
    db.commit()
    return created


def resolve_category(db, label: str | None) -> tuple[int | None, str]:
    """
    Return (category_id, how).
    how: exact / contains / fuzzy / proposed_existing / proposed_new / generic / none
    Dhyan: naya proposed banne par sirf flush hota hai, commit caller karta hai.
    """
    if not label:
        return None, "none"
    norm = norm_label(label)
    if not norm or norm in GENERIC:
        return None, "generic"

    # Sirf approved categories se match (naam + aliases)
    approved = db.scalars(select(Category).where(Category.status == "approved")).all()
    cands = []  # (normalized candidate, category)
    for c in approved:
        cands.append((norm_label(c.name), c))
        for a in c.aliases or []:
            cands.append((norm_label(a), c))

    # 1. Exact naam ya alias
    for cn, c in cands:
        if cn == norm:
            return c.id, "exact"

    # 2. Candidate ke lafz label mein maujood hain
    #    "ev charger installation service" mein "ev charger" maujood hai.
    #    Ek lafz wali category tab, jab wo label ka aakhri lafz ho ("lithium battery" -> battery).
    tokens = norm.split()
    best, best_score = None, 0
    for cn, c in cands:
        ct = cn.split()
        if not ct:
            continue
        if len(ct) >= 2 and all(t in tokens for t in ct):
            score = len(ct)
        elif len(ct) == 1 and len(tokens) > 1 and tokens[-1] == ct[0]:
            score = 1
        else:
            continue
        if score > best_score:        # zyada lafz wali match behtar
            best, best_score = c, score
    if best:
        return best.id, "contains"

    # 3. Fuzzy (spelling ka chhota farq)
    best, best_ratio = None, 0.0
    for cn, c in cands:
        ratio = SequenceMatcher(None, norm, cn).ratio()
        if ratio > best_ratio:
            best, best_ratio = c, ratio
    if best and best_ratio >= FUZZY_THRESHOLD:
        return best.id, "fuzzy"

    # 4. Pehle se proposed? Usi se jodo (duplicate proposed nahi banate)
    prop = db.scalar(select(Category).where(Category.name == norm))
    if prop:
        return prop.id, "proposed_existing"

    # 5. Bilkul nayi: proposed banao, review queue mein jayegi
    prop = Category(name=norm, status="proposed", aliases=[])
    db.add(prop)
    db.flush()   # id chahiye
    return prop.id, "proposed_new"


def approve_category(db, category_id: int) -> Category:
    cat = db.get(Category, category_id)
    if cat is None:
        raise ValueError("Category nahi mili")
    cat.status = "approved"
    db.commit()
    return cat


def merge_category(db, source_id: int, target_id: int) -> Category:
    """
    source ko target ka alias bana do. source ke items target par chale jate hain.
    Aage se source ka naam aaye to khud target se match hoga.
    """
    if source_id == target_id:
        raise ValueError("Source aur target ek hi hain")
    src, tgt = db.get(Category, source_id), db.get(Category, target_id)
    if src is None or tgt is None:
        raise ValueError("Category nahi mili")
    if tgt.status != "approved":
        raise ValueError("Target approved honi chahiye")

    aliases = list(tgt.aliases or [])
    for a in [src.name] + list(src.aliases or []):
        if a not in aliases:
            aliases.append(a)
    tgt.aliases = aliases   # nayi list assign: SQLAlchemy ko JSON change pata chalta hai

    for it in db.scalars(select(Item).where(Item.category_id == src.id)):
        it.category_id = tgt.id
    # presence abhi use nahi hoti, magar foreign key ki wajah se saaf karna zaroori
    for p in db.scalars(select(Presence).where(Presence.category_id == src.id)):
        db.delete(p)
    db.delete(src)
    db.commit()
    return tgt


def relink_all_items(db) -> dict:
    """Saare items ki suggested_category dobara resolve (Phase 1 ke purane items ke liye)."""
    counts: dict[str, int] = {}
    for it in db.scalars(select(Item)):
        cat_id, how = resolve_category(db, it.suggested_category)
        it.category_id = cat_id
        counts[how] = counts.get(how, 0) + 1
    db.commit()
    return counts