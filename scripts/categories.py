# scripts/categories.py
# Usage (project root se):
#   python -m scripts.categories seed                     starter categories banao
#   python -m scripts.categories test --label "EV charger installation service"
#   python -m scripts.categories relink                   purane items dobara jodo
#   python -m scripts.categories list                     saari categories
#   python -m scripts.categories proposed                 review queue
#   python -m scripts.categories approve --id 20
#   python -m scripts.categories merge --from-id 20 --into-id 8
import argparse

from sqlalchemy import func, select

from app.db.base import SessionLocal
from app.db.models import Category, Item
from app.tools import categories as cats


def _print(db, status=None):
    # Har category ke saath kitne items juray hain
    q = (select(Category, func.count(Item.id))
         .outerjoin(Item, Item.category_id == Category.id)
         .group_by(Category.id)
         .order_by(Category.status, Category.name))
    if status:
        q = q.where(Category.status == status)
    rows = db.execute(q).all()
    if not rows:
        return print("Kuch nahi mila")
    for c, n in rows:
        print(f"#{c.id:<3} {c.status:<9} {c.name:<26} items={n:<3} aliases={len(c.aliases or [])}")


def cmd_seed(_):
    with SessionLocal() as db:
        print(f"{cats.seed_categories(db)} nayi categories seed hui")


def cmd_test(a):
    """Dry run: dekho ke label kis category se jata hai. Kuch save nahi hota."""
    with SessionLocal() as db:
        cat_id, how = cats.resolve_category(db, a.label)
        cat = db.get(Category, cat_id) if cat_id else None
        print(f"{a.label!r} -> {cat.name if cat else None}  ({how})")
        db.rollback()


def cmd_relink(_):
    with SessionLocal() as db:
        print("Result:", cats.relink_all_items(db))


def cmd_list(_):
    with SessionLocal() as db:
        _print(db)


def cmd_proposed(_):
    with SessionLocal() as db:
        _print(db, status="proposed")


def cmd_approve(a):
    with SessionLocal() as db:
        cat = cats.approve_category(db, a.id)
        print(f"{cat.name} approve ho gayi")


def cmd_merge(a):
    with SessionLocal() as db:
        tgt = cats.merge_category(db, a.from_id, a.into_id)
        print(f"Merge ho gayi -> {tgt.name} (aliases: {len(tgt.aliases)})")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("seed").set_defaults(fn=cmd_seed)
    sub.add_parser("relink").set_defaults(fn=cmd_relink)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    sub.add_parser("proposed").set_defaults(fn=cmd_proposed)

    s = sub.add_parser("test")
    s.add_argument("--label", required=True)
    s.set_defaults(fn=cmd_test)

    s = sub.add_parser("approve")
    s.add_argument("--id", type=int, required=True)
    s.set_defaults(fn=cmd_approve)

    s = sub.add_parser("merge")
    s.add_argument("--from-id", type=int, required=True)
    s.add_argument("--into-id", type=int, required=True)
    s.set_defaults(fn=cmd_merge)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
    