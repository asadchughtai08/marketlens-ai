# app/db/base.py
# ------------------------------------------------------------------
# Is file ka kaam: database se connection banana aur session dena.
# Baaki saari files (models, scripts, agents) yahin se engine/session lengi.
# ------------------------------------------------------------------
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """
    Saare table models (Competitor, Snapshot, Item...) isi class se inherit
    karte hain. SQLAlchemy is class ke zariye jaan leta hai ke kaun kaun si
    tables banani hain (Base.metadata mein sab register ho jati hain).
    """


# engine = database ka connection point.
# database_url config se aata hai: sqlite:///.../data/marketlens.db
# echo=True karoge to har SQL query terminal mein print hogi (debugging ke liye).
engine = create_engine(settings.database_url, echo=False)


@event.listens_for(engine, "connect")
def _enable_sqlite_fk(dbapi_conn, _):
    # SQLite mein foreign key checking default band hoti hai.
    # Isay on na karein to ghalat id (jo exist hi nahi karti) bhi save ho jati hai.
    # Yeh function har naye connection par automatically chalta hai.
    dbapi_conn.execute("PRAGMA foreign_keys=ON")


# SessionLocal = database se baat karne ka "kaam ka session".
# Istemal: with SessionLocal() as db: db.add(...); db.commit()
# expire_on_commit=False: commit ke baad bhi object ki values padh sakte hain
# (warna dobara DB se load karni parti hain).
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
