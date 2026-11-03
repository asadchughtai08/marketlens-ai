# app/tools/store.py
# Kaam: extracted items ko DB mein save karna (items + claims).
# Ek item sirf ek baar banta hai; dobara dikhe to sirf last_seen update hota hai.
from sqlalchemy import select

from app.db.models import Claim, Competitor, Item, Snapshot, now
from app.schemas.extraction import ExtractionResult
from app.tools.categories import resolve_category
from app.tools.normalize import normalize_name
from app.tools.verifier import verify


def save_items(db, comp: Competitor, snap: Snapshot,
               result: ExtractionResult, page_text: str) -> dict:
    stats = {"new": 0, "seen_again": 0, "pending_review": 0, "skipped": 0,
             "proposed_categories": 0, "verified": 0, "weak": 0, "unsupported": 0}
    seen_in_run = set()

    for it in result.items:
        norm = normalize_name(it.name)
        # Khali naam ya isi page par duplicate: skip
        if not norm or norm in seen_in_run:
            stats["skipped"] += 1
            continue
        seen_in_run.add(norm)

        # Evidence Verifier: rules se saboot check
        llm_conf = max(0.0, min(1.0, it.confidence))
        res = verify(it.name, it.brand, it.model, it.capacity,
                     it.quote, page_text, llm_conf)
        stats[res.verdict] += 1
        if res.review_status == "pending":
            stats["pending_review"] += 1

        # Agent ki category ko approved category se jodo (ya proposed banao)
        cat_id, how = resolve_category(db, it.suggested_category)
        if how == "proposed_new":
            stats["proposed_categories"] += 1

        # Pehle se maujood item?
        item = db.scalar(select(Item).where(
            Item.competitor_id == comp.id, Item.normalized_name == norm))

        if item is None:
            item = Item(
                competitor_id=comp.id,
                category_id=cat_id,
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
            if item.category_id is None and cat_id is not None:
                item.category_id = cat_id
            stats["seen_again"] += 1

        db.flush()  # item.id chahiye claim ke liye
        db.add(Claim(
            item_id=item.id,
            snapshot_id=snap.id,
            source_url=snap.url,
            quote=it.quote[:500],
            confidence=res.confidence,
            llm_confidence=llm_conf,
            verdict=res.verdict,
            reasons=res.reasons,
            review_status=res.review_status,
        ))

    db.commit()
    return stats