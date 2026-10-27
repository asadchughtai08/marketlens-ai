# app/services/pipeline.py
# Crawl, paste aur extract ka logic ek jagah. API (aur baad mein agents) yahin se use karte hain.
# Har function dict wapas karta hai, taake API seedha JSON bana sake.
from pathlib import Path

from sqlalchemy import desc, select

from app.db.models import Claim, Competitor, Snapshot
from app.tools.crawler import fetch_page
from app.tools.extractor import extract_items
from app.tools.robots import is_allowed
from app.tools.snapshots import save_failure, save_snapshot
from app.tools.store import save_items

# Isse chhota text = shayad page khali ya JavaScript se load hota hai
MIN_CHARS = 100


def crawl_competitor(db, comp: Competitor) -> dict:
    url = comp.products_url or comp.website

    # Manual paste wali company ko crawler nahi chhoota
    if comp.crawl_method != "auto":
        return {"status": "manual_paste_required",
                "detail": "Is company ka crawl_method manual_paste hai. /paste use karo."}

    # robots.txt mana kare to fetch hi nahi karte, failure record hoti hai
    ok, why = is_allowed(url)
    if not ok:
        save_failure(db, comp, url)
        return {"status": "blocked", "detail": why}

    text, err = fetch_page(url)
    if text is None or len(text.strip()) < MIN_CHARS:
        save_failure(db, comp, url)
        return {"status": "failed",
                "detail": err or "text bohat chhota, shayad JS-heavy page. /paste use karo."}

    # Hash compare: same hash = page nahi badla
    snap, changed = save_snapshot(db, comp, url, text, method="auto")
    return {"status": "changed" if changed else "unchanged",
            "snapshot_id": snap.id, "chars": len(text)}


def paste_snapshot(db, comp: Competitor, url: str, text: str) -> dict:
    snap, changed = save_snapshot(db, comp, url, text, method="manual_paste")
    return {"status": "changed" if changed else "unchanged", "snapshot_id": snap.id}


def extract_latest(db, comp: Competitor, force: bool = False) -> dict:
    # Latest kamyab snapshot (skipped_unchanged / failed nahi)
    snap = db.scalar(select(Snapshot)
                     .where(Snapshot.competitor_id == comp.id, Snapshot.status == "ok")
                     .order_by(desc(Snapshot.id)).limit(1))
    if not snap or not snap.raw_path:
        return {"status": "no_snapshot", "detail": "Pehle crawl ya paste karo."}

    # Pehle hi extract ho chuka? To Gemini ko dobara call nahi (cost bachao)
    done = db.scalar(select(Claim.id).where(Claim.snapshot_id == snap.id).limit(1))
    if done and not force:
        return {"status": "already_extracted", "snapshot_id": snap.id}

    text = Path(snap.raw_path).read_text(encoding="utf-8")
    result, tok_in, tok_out = extract_items(text, snap.url)
    stats = save_items(db, comp, snap, result, text)
    return {"status": "extracted", "snapshot_id": snap.id,
            "items_found": len(result.items),
            "tokens_in": tok_in, "tokens_out": tok_out, "saved": stats}