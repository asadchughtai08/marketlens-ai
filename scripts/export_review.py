# scripts/export_review.py
# Chalao: python -m scripts.export_review
# Saare items + evidence ek CSV mein (data/review_sheet.csv), manual verification ke liye.
# Aakhri 3 columns tum khud bharoge: correct, error_type, notes.
import csv

from sqlalchemy import select

from app.core.config import BASE_DIR
from app.db.base import SessionLocal
from app.db.models import Claim, Competitor, Item

OUT = BASE_DIR / "data" / "review_sheet.csv"

with SessionLocal() as db:
    rows = db.execute(
        select(Claim, Item, Competitor)
        .join(Item, Claim.item_id == Item.id)
        .join(Competitor, Item.competitor_id == Competitor.id)
        .order_by(Competitor.name, Item.id)
    ).all()

    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["company", "item_id", "kind", "name", "brand", "capacity",
                    "category", "confidence", "quote", "source_url",
                    "correct (yes/no)", "error_type", "notes"])
        for c, it, comp in rows:
            w.writerow([comp.name, it.id, it.kind, it.name, it.brand, it.capacity,
                        it.suggested_category, round(c.confidence, 2), c.quote,
                        c.source_url, "", "", ""])

print(f"{len(rows)} rows -> {OUT}")
