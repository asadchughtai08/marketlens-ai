# scripts/run_graph.py
# Usage (project root se):
#   python -m scripts.run_graph run --name "Company A"
#   python -m scripts.run_graph run --name "Company A" --force
#   python -m scripts.run_graph run-all
#   python -m scripts.run_graph paste --name "Company B" --url https://... --file page.txt
#   python -m scripts.run_graph diagram        (Mermaid diagram, README ke liye)
import argparse
import time
from pathlib import Path

from sqlalchemy import select

from app.agents.pipeline_graph import graph, run_company
from app.core.config import settings
from app.db.base import SessionLocal
from app.db.models import Competitor


def comp_id(name: str) -> int | None:
    with SessionLocal() as db:
        c = db.scalar(select(Competitor).where(Competitor.name == name))
        return c.id if c else None


def show(name: str, final: dict) -> None:
    print(f"{name}: [{final.get('outcome')}] {final.get('message', '')}\n")


def cmd_run(a):
    cid = comp_id(a.name)
    if cid is None:
        return print("Company DB mein nahi. Pehle: python -m scripts.sync_competitors")
    print(f"== {a.name} ==")
    show(a.name, run_company(cid, force=a.force))


def cmd_run_all(a):
    with SessionLocal() as db:
        comps = [(c.id, c.name) for c in db.scalars(
            select(Competitor).where(Competitor.active == True))]  # noqa: E712
    for cid, name in comps:
        print(f"== {name} ==")
        show(name, run_company(cid, force=a.force))
        time.sleep(settings.crawl_delay_seconds)   # sites par rehem


def cmd_paste(a):
    cid = comp_id(a.name)
    if cid is None:
        return print("Company DB mein nahi")
    text = Path(a.file).read_text(encoding="utf-8")
    print(f"== {a.name} (manual paste) ==")
    show(a.name, run_company(cid, force=a.force, paste_url=a.url, paste_text=text))


def cmd_diagram(_):
    print(graph.get_graph().draw_mermaid())


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("run")
    s.add_argument("--name", required=True)
    s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_run)

    s = sub.add_parser("run-all")
    s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_run_all)

    s = sub.add_parser("paste")
    s.add_argument("--name", required=True)
    s.add_argument("--url", required=True)
    s.add_argument("--file", required=True)
    s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_paste)

    sub.add_parser("diagram").set_defaults(fn=cmd_diagram)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
    