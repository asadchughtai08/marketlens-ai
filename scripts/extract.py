
# scripts/extract.py
# Usage (project root se):
#   python -m scripts.extract run --name "Company A"          (latest snapshot se items nikalo)
#   python -m scripts.extract run --name "Company A" --force  (dobara chalao)
#   python -m scripts.extract show --name "Company A"         (items dekho)
#   python -m scripts.extract review                          (pending claims dekho)
#   python -m scripts.extract set-review --id 5 --status approved
import argparse
from pathlib import Path

from sqlalchemy import desc, select

from app.db.base import SessionLocal
from app.db.models import Claim, Competitor, Item, Snapshot
from app.tools.extractor import extract_items
from app.tools.store import save_items


def get_comp(db, name):
    return db.scalar(select(Competitor).where(Competitor.name == name))


def cmd_run(a):
    with SessionLocal() as db:
        comp = get_comp(db, a.name)
        if not comp:
            return print("Company DB mein nahi")

        # Latest kamyab snapshot (skipped_unchanged/failed nahi)
        snap = db.scalar(select(Snapshot)
                         .where(Snapshot.competitor_id == comp.id, Snapshot.status == "ok")
                         .order_by(desc(Snapshot.id)).limit(1))
        if not snap or not snap.raw_path:
            return print("Koi ok snapshot nahi. Pehle crawl ya paste karo.")

        # Is snapshot se pehle hi claims ban chuke hain? To LLM dobara nahi chalana
        done = db.scalar(select(Claim.id).where(Claim.snapshot_id == snap.id).limit(1))
        if done and not a.force:
            return print(f"Snapshot #{snap.id} pehle extract ho chuka (skip). --force se dobara.")

        text = Path(snap.raw_path).read_text(encoding="utf-8")
        print(f"Snapshot #{snap.id}: {len(text)} chars Gemini ko bhej rahe hain...")
        result, tok_in, tok_out = extract_items(text, snap.url)
        print(f"Gemini ne {len(result.items)} items diye (tokens in={tok_in}, out={tok_out})")

        stats = save_items(db, comp, snap, result, text)
        print("Saved:", stats)


def cmd_show(a):
    with SessionLocal() as db:
        comp = get_comp(db, a.name)
        if not comp:
            return print("Company DB mein nahi")
        for it in db.scalars(select(Item).where(Item.competitor_id == comp.id)):
            print(f"#{it.id:<3} {it.kind:<9} {it.name:<35} cap={str(it.capacity):<8} "
                  f"cat={it.suggested_category}")


def cmd_review(_):
    with SessionLocal() as db:
        rows = db.execute(
            select(Claim, Item).join(Item, Claim.item_id == Item.id)
            .where(Claim.review_status == "pending")).all()
        if not rows:
            return print("Review queue khali")
        for c, it in rows:
            print(f"claim #{c.id:<3} conf={c.confidence:.2f}  {it.name}\n"
                  f"           quote: {c.quote[:90]}")


def cmd_set_review(a):
    with SessionLocal() as db:
        c = db.get(Claim, a.id)
        if not c:
            return print("Claim nahi mila")
        c.review_status = a.status
        db.commit()
        print(f"claim #{a.id} -> {a.status}")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("run")
    s.add_argument("--name", required=True)
    s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_run)

    s = sub.add_parser("show"); s.add_argument("--name", required=True); s.set_defaults(fn=cmd_show)
    sub.add_parser("review").set_defaults(fn=cmd_review)

    s = sub.add_parser("set-review")
    s.add_argument("--id", type=int, required=True)
    s.add_argument("--status", choices=["approved", "rejected"], required=True)
    s.set_defaults(fn=cmd_set_review)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
