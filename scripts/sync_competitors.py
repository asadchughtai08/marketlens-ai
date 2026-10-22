# scripts/sync_competitors.py
# ------------------------------------------------------------------
# Chalao: python -m scripts.sync_competitors
# Kaam: CSV registry (data/competitors.csv) ko DB ki competitors table mein copy/update.
# CSV source of truth hai: wahan company add/edit karo, phir yeh script chalao.
# Dobara chalane se duplicate nahi bante (naam se pehchan hoti hai).
# ------------------------------------------------------------------
from sqlalchemy import select

from app.db.base import SessionLocal
from app.db.models import Competitor
from app.tools import registry

# with block khatam hote hi session khud band ho jata hai
with SessionLocal() as db:
    # CSV ki har row ke liye
    for r in registry.load():
        # DB mein is naam ki company dhoondo
        comp = db.scalar(select(Competitor).where(Competitor.name == r["name"]))

        # Nahi mili to nayi banao
        if comp is None:
            comp = Competitor(name=r["name"], website=r["website"])
            db.add(comp)

        # Nayi ho ya purani, har baar CSV ki values se update
        # (CSV mein khali string ho to None rakho)
        comp.website = r["website"]
        comp.products_url = r["products_url"] or None
        comp.city = r["city"]
        comp.active = r["active"] == "yes"   # CSV mein "yes"/"no" text hai, DB mein True/False
        comp.crawl_method = r["crawl_method"]

    # Saari tabdeelian ek saath save
    db.commit()

    print("Competitors in DB:", [c.name for c in db.scalars(select(Competitor))])
    