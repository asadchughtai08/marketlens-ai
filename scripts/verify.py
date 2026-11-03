# scripts/verify.py
# Usage (project root se):
#   python -m scripts.verify run                  purane claims ko dobara verify (status nahi badalta)
#   python -m scripts.verify run --apply-status   review_status bhi verdict ke mutabiq badlo
#   python -m scripts.verify report               verdict ka khulasa
#   python -m scripts.verify show --verdict weak  weak ya unsupported claims dekho
import argparse
from collections import Counter
from pathlib import Path

from sqlalchemy import select

from app.db.base import SessionLocal
from app.db.models import Claim, Item, Snapshot
from app.tools.verifier import verify


def cmd_run(a):
    with SessionLocal() as db:
        rows = db.execute(
            select(Claim, Item, Snapshot)
            .join(Item, Claim.item_id == Item.id)
            .join(Snapshot, Claim.snapshot_id == Snapshot.id)
        ).all()

        pages: dict[str, str] = {}   # har raw file sirf ek baar padho
        counts, skipped = Counter(), 0
        for claim, item, snap in rows:
            if not snap.raw_path or not Path(snap.raw_path).exists():
                skipped += 1
                continue
            if snap.raw_path not in pages:
                pages[snap.raw_path] = Path(snap.raw_path).read_text(encoding="utf-8")

            # Pehli baar: purani confidence ko "asli" maan lo
            if claim.llm_confidence is None:
                claim.llm_confidence = claim.confidence

            res = verify(item.name, item.brand, item.model, item.capacity,
                         claim.quote, pages[snap.raw_path], claim.llm_confidence)
            claim.verdict = res.verdict
            claim.reasons = res.reasons
            claim.confidence = res.confidence
            # Insaan ke faislay (approved/rejected) tab tak nahi chhoote jab tak --apply-status na ho
            if a.apply_status:
                claim.review_status = res.review_status
            counts[res.verdict] += 1

        db.commit()
        print(f"Verify hue: {dict(counts)}  |  raw file na milne par skip: {skipped}")


def cmd_report(_):
    with SessionLocal() as db:
        claims = db.scalars(select(Claim)).all()
    if not claims:
        return print("Koi claim nahi")
    total = len(claims)
    verdicts = Counter(c.verdict or "unverified" for c in claims)
    print(f"Total claims: {total}")
    for v, n in verdicts.most_common():
        print(f"  {v:<12} {n:<4} ({n / total:.0%})")
    reasons = Counter(r for c in claims for r in (c.reasons or []))
    print("Wajohat:")
    for r, n in reasons.most_common():
        print(f"  {r:<24} {n}")


def cmd_show(a):
    with SessionLocal() as db:
        rows = db.execute(
            select(Claim, Item).join(Item, Claim.item_id == Item.id)
            .where(Claim.verdict == a.verdict).order_by(Claim.confidence)
        ).all()
        if not rows:
            return print("Kuch nahi mila")
        for c, it in rows:
            print(f"claim #{c.id:<4} conf={c.confidence:.2f}  {it.name}\n"
                  f"   reasons: {c.reasons}\n   quote: {c.quote[:90]}")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("run")
    s.add_argument("--apply-status", action="store_true")
    s.set_defaults(fn=cmd_run)

    sub.add_parser("report").set_defaults(fn=cmd_report)

    s = sub.add_parser("show")
    s.add_argument("--verdict", choices=["verified", "weak", "unsupported"], required=True)
    s.set_defaults(fn=cmd_show)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()