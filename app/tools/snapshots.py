
# app/tools/snapshots.py
# Kaam: page ka text hash karna, raw file save karna, snapshots table mein row likhna.
# Hash same ho to LLM dobara nahi chalana: yahi cost bachata hai.
import hashlib
import re
from datetime import datetime, timezone

from sqlalchemy import desc, select

from app.core.config import BASE_DIR
from app.db.models import Competitor, Snapshot

RAW_DIR = BASE_DIR / "data" / "raw"


def clean(text: str) -> str:
    """Extra spaces/newlines hatao, taake sirf formatting badalne par hash na badle."""
    return re.sub(r"\s+", " ", text).strip()


def hash_text(text: str) -> str:
    return hashlib.sha256(clean(text).encode("utf-8")).hexdigest()


def last_ok_snapshot(db, competitor_id: int, url: str) -> Snapshot | None:
    """Is URL ka aakhri kamyab (status ok) snapshot, compare karne ke liye."""
    return db.scalar(
        select(Snapshot)
        .where(Snapshot.competitor_id == competitor_id,
               Snapshot.url == url,
               Snapshot.status == "ok")
        .order_by(desc(Snapshot.id))
        .limit(1)
    )


def save_snapshot(db, comp: Competitor, url: str, text: str,
                  method: str = "auto") -> tuple[Snapshot, bool]:
    """Return (snapshot, changed). changed=False matlab page pehle jaisa hi hai."""
    new_hash = hash_text(text)
    prev = last_ok_snapshot(db, comp.id, url)

    # Case 1: hash same = page nahi badla. Raw file dobara save nahi karte.
    if prev and prev.content_hash == new_hash:
        snap = Snapshot(competitor_id=comp.id, url=url, content_hash=new_hash,
                        method=method, raw_path=None, status="skipped_unchanged")
        db.add(snap)
        db.commit()
        return snap, False

    # Case 2: naya ya badla hua page. Raw text file mein, DB mein sirf path.
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    raw_file = RAW_DIR / f"{comp.id}_{stamp}.md"
    raw_file.write_text(text, encoding="utf-8")

    snap = Snapshot(competitor_id=comp.id, url=url, content_hash=new_hash,
                    method=method, raw_path=str(raw_file), status="ok")
    db.add(snap)
    db.commit()
    return snap, True


def save_failure(db, comp: Competitor, url: str, method: str = "auto") -> Snapshot:
    """Fail hua fetch bhi record hota hai (history mein pata chale kab fail hua)."""
    snap = Snapshot(competitor_id=comp.id, url=url, content_hash="",
                    method=method, raw_path=None, status="failed")
    db.add(snap)
    db.commit()
    return snap
