
# app/tools/store.py
# Kaam: extracted items ko DB mein save karna (items + claims).
# Ek item sirf ek baar banta hai; dobara dikhe to sirf last_seen update hota hai.
from sqlalchemy import select

from app.db.models import Claim, Competitor, Item, Snapshot, now
from app.schemas.extraction import ExtractionResult
from app.tools.normalize import normalize_name, quote_in_text

# Isse kam confidence = insaan ki review chahiye
REVIEW_THRESHOLD = 0.7


def save_items(db, comp: Competitor, snap: Snapshot,
               result: ExtractionResult, page_text: str) -> dict:
    stats = {"new": 0, "seen_again": 0, "pending_review": 0, "skipped": 0}
    seen_in_run = set()

    for it in result.items:
        norm = normalize_name(it.name)
        # Khali naam ya isi page par duplicate: skip
        if not norm or norm in seen_in_run:
            stats["skipped"] += 1
            continue
        seen_in_run.add(norm)

        # Confidence 0 se 1 ke andar rakho
        conf = max(0.0, min(1.0, it.confidence))
        # Grounding check: quote page mein nahi mili = shak, confidence gira do
        verified = quote_in_text(it.quote, page_text)
        if not verified:
            conf = min(conf, 0.3)
        review = "approved" if (verified and conf >= REVIEW_THRESHOLD) else "pending"
        if review == "pending":
            stats["pending_review"] += 1

        # Pehle se maujood item?
        item = db.scalar(select(Item).where(
            Item.competitor_id == comp.id, Item.normalized_name == norm))

        if item is None:
            item = Item(
                competitor_id=comp.id,
                kind=it.kind,
                name=it.name,
                normalized_name=norm,
                brand=it.brand,
                model=it.model,
                capacity=it.capacity,
                description=it.description,
                specs={p.key: p.value for p in it.specs},
                suggested_category=(it.suggested_category or "").lower().strip() or None,
                first_seen_snapshot_id=snap.id,
                last_seen_snapshot_id=snap.id,
            )
            db.add(item)
            stats["new"] += 1
        else:
            # Dobara dikha: sirf last_seen update, naya item nahi
            item.last_seen_snapshot_id = snap.id
            item.last_seen_at = now()
            item.is_active = True
            stats["seen_again"] += 1

        db.flush()  # item.id chahiye claim ke liye
        db.add(Claim(
            item_id=item.id,
            snapshot_id=snap.id,
            source_url=snap.url,
            quote=it.quote[:500],
            confidence=conf,
            review_status=review,
        ))

    db.commit()
    return stats
