
# scripts/crawl.py
# Usage (project root se):
#   python -m scripts.crawl crawl --name "Company A"
#   python -m scripts.crawl crawl-all
#   python -m scripts.crawl paste --name "Company A" --url https://... --file paste.txt
#   python -m scripts.crawl history --name "Company A"
import argparse
import time
from pathlib import Path

from sqlalchemy import desc, select

from app.core.config import settings
from app.db.base import SessionLocal
from app.db.models import Competitor, Snapshot
from app.tools.crawler import fetch_page
from app.tools.robots import is_allowed
from app.tools.snapshots import save_failure, save_snapshot

# Isse chhota text = shayad page khali ya JavaScript se load hota hai
MIN_CHARS = 100


def get_comp(db, name: str) -> Competitor | None:
    return db.scalar(select(Competitor).where(Competitor.name == name))


def crawl_one(db, comp: Competitor) -> None:
    url = comp.products_url or comp.website

    # 1. Manual paste wali company ko crawler nahi chhoota
    if comp.crawl_method != "auto":
        print(f"{comp.name}: manual_paste. 'paste' command use karo.")
        return

    # 2. robots.txt: mana ho to fetch hi nahi karte
    ok, why = is_allowed(url)
    if not ok:
        save_failure(db, comp, url)
        print(f"{comp.name}: BLOCKED ({why}). Manual paste use karo.")
        return

    # 3. Page fetch
    text, err = fetch_page(url)
    if text is None or len(text.strip()) < MIN_CHARS:
        save_failure(db, comp, url)
        print(f"{comp.name}: FAILED ({err or 'text bohat chhota, shayad JS-heavy page'})")
        return

    # 4. Hash compare + save
    snap, changed = save_snapshot(db, comp, url, text, method="auto")
    if changed:
        print(f"{comp.name}: NEW/CHANGED snapshot #{snap.id} ({len(text)} chars)")
    else:
        print(f"{comp.name}: unchanged (skip, LLM ki zaroorat nahi)")


def cmd_crawl(a):
    with SessionLocal() as db:
        comp = get_comp(db, a.name)
        if not comp:
            return print("Company DB mein nahi. Pehle: python -m scripts.sync_competitors")
        crawl_one(db, comp)


def cmd_crawl_all(_):
    with SessionLocal() as db:
        for comp in db.scalars(select(Competitor).where(Competitor.active == True)):  # noqa: E712
            crawl_one(db, comp)
            time.sleep(settings.crawl_delay_seconds)  # sites par rehem


def cmd_paste(a):
    """Insaan ne page ka text file mein copy kiya, usay snapshot bana do."""
    text = Path(a.file).read_text(encoding="utf-8")
    with SessionLocal() as db:
        comp = get_comp(db, a.name)
        if not comp:
            return print("Company DB mein nahi")
        snap, changed = save_snapshot(db, comp, a.url, text, method="manual_paste")
        print(f"Paste snapshot #{snap.id}: {'new/changed' if changed else 'unchanged'}")


def cmd_history(a):
    with SessionLocal() as db:
        comp = get_comp(db, a.name)
        if not comp:
            return print("Company DB mein nahi")
        snaps = db.scalars(select(Snapshot).where(Snapshot.competitor_id == comp.id)
                           .order_by(desc(Snapshot.id)))
        for s in snaps:
            print(f"#{s.id:<3} {s.fetched_at:%Y-%m-%d %H:%M}  {s.status:<18} "
                  f"{s.method:<12} {s.content_hash[:10]}")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("crawl"); s.add_argument("--name", required=True); s.set_defaults(fn=cmd_crawl)
    sub.add_parser("crawl-all").set_defaults(fn=cmd_crawl_all)

    s = sub.add_parser("paste")
    s.add_argument("--name", required=True)
    s.add_argument("--url", required=True)
    s.add_argument("--file", required=True)
    s.set_defaults(fn=cmd_paste)

    s = sub.add_parser("history"); s.add_argument("--name", required=True); s.set_defaults(fn=cmd_history)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
