# app/db/models.py
# ------------------------------------------------------------------
# Saari tables yahan class ki shakal mein hain.
# 1 class = 1 table, 1 attribute = 1 column.
# Mapped[...] type hint batata hai column ki type aur nullable hai ya nahi:
#   Mapped[str]         -> zaroori (NOT NULL)
#   Mapped[str | None]  -> khali ho sakta hai (NULL)
# ------------------------------------------------------------------
from datetime import datetime, timezone

from sqlalchemy import (JSON, Boolean, DateTime, Float, ForeignKey, Integer,
                        String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def now() -> datetime:
    """Hamesha UTC time deta hai, taake timezone ka jhanjhat na ho."""
    return datetime.now(timezone.utc)


# ==================================================================
# TABLE 1: competitors
# Har solar company ki ek row. CSV registry se sync hoti hai.
# ==================================================================
class Competitor(Base):
    __tablename__ = "competitors"

    id: Mapped[int] = mapped_column(primary_key=True)
    # unique=True: ek naam do baar nahi aa sakta
    name: Mapped[str] = mapped_column(String(200), unique=True)
    website: Mapped[str] = mapped_column(String(500))
    # Products page ka URL; shuru mein khali ho sakta hai
    products_url: Mapped[str | None] = mapped_column(String(500))
    city: Mapped[str] = mapped_column(String(100), default="Islamabad")
    # False = monitoring band, magar purana data safe rehta hai
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    # auto = crawler, manual_paste = robots.txt block ho to insaan paste karega
    crawl_method: Mapped[str] = mapped_column(String(20), default="auto")

    # relationship: Python mein competitor.snapshots / competitor.items likh kar
    # related rows mil jati hain (alag query likhne ki zaroorat nahi)
    snapshots: Mapped[list["Snapshot"]] = relationship(back_populates="competitor")
    items: Mapped[list["Item"]] = relationship(back_populates="competitor")


# ==================================================================
# TABLE 2: snapshots
# Ek page ka ek fetch. Har crawl par nayi row banti hai.
# Isi table se "history" aur "pehle kya tha" pata chalta hai.
# ==================================================================
class Snapshot(Base):
    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    # ForeignKey: yeh competitors table ki id se juda hai
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitors.id"))
    url: Mapped[str] = mapped_column(String(1000))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    # Page ke text ka SHA-256 hash. Hash same = page nahi badla =
    # LLM dobara nahi chalana = paisa aur time bachta hai.
    content_hash: Mapped[str] = mapped_column(String(64))
    # auto (crawler) ya manual_paste (insaan ne paste kiya)
    method: Mapped[str] = mapped_column(String(20), default="auto")
    # Raw text DB mein nahi, data/raw/ ki file mein. Yahan sirf path.
    raw_path: Mapped[str | None] = mapped_column(String(500))
    # ok / failed / skipped_unchanged
    status: Mapped[str] = mapped_column(String(30), default="ok")

    competitor: Mapped[Competitor] = relationship(back_populates="snapshots")


# ==================================================================
# TABLE 3: categories
# Flat (bina hierarchy ke) canonical categories.
# Agent naya naam suggest kare to "proposed", tum approve karo to "approved".
# ==================================================================
class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Standard naam, jaise "EV charger"
    name: Mapped[str] = mapped_column(String(100), unique=True)
    # approved = official, proposed = review queue mein
    status: Mapped[str] = mapped_column(String(20), default="proposed")
    # Milte julte naam ek hi category mein: ["EV charging station", "car charger"]
    # JSON column: Python list seedha save/load hoti hai
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# ==================================================================
# TABLE 4: items
# Site par mili koi bhi cheez: product, feature, ya (optional) service.
# Ek item sirf EK baar banta hai. Har crawl par naya nahi banta,
# sirf last_seen update hota hai. Isi se "naya aaya" / "hata" pata chalta hai.
# ==================================================================
class Item(Base):
    __tablename__ = "items"
    # Ek company mein ek normalized naam sirf ek baar (duplicate se bachao)
    __table_args__ = (UniqueConstraint("competitor_id", "normalized_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitors.id"))
    # Official category (approve hone ke baad hi bharti hai, warna NULL)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))

    # product / feature / service / solution
    kind: Mapped[str] = mapped_column(String(20), default="product")
    # Jaisa site par likha hai (original)
    name: Mapped[str] = mapped_column(String(300))
    # Saaf shakal: "LONGi Himo9" aur "Longi Hi-MO 9" dono "longi himo 9" banenge,
    # taake ek hi cheez ke do alag item ya fazool "changes" na banen.
    # (Normalization function Task 5 mein banegi)
    normalized_name: Mapped[str] = mapped_column(String(300))
    brand: Mapped[str | None] = mapped_column(String(100))
    model: Mapped[str | None] = mapped_column(String(100))
    capacity: Mapped[str | None] = mapped_column(String(50))  # "5kW", "550W"
    description: Mapped[str | None] = mapped_column(Text)
    # Flexible extra details: {"type": "N-type", "mode": "on-grid"}
    specs: Mapped[dict] = mapped_column(JSON, default=dict)

    # Agent ki raaye (text). Tum approve karo to category_id se link hoti hai.
    # Is tarah agent ke alag alag naam directly official data ko gandha nahi karte.
    suggested_category: Mapped[str | None] = mapped_column(String(100))

    # Lifecycle tracking: pehli baar kis snapshot mein dikha, aakhri baar kis mein
    first_seen_snapshot_id: Mapped[int] = mapped_column(ForeignKey("snapshots.id"))
    last_seen_snapshot_id: Mapped[int] = mapped_column(ForeignKey("snapshots.id"))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    # Naye snapshot mein na mile to False ("hata diya gaya")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    competitor: Mapped[Competitor] = relationship(back_populates="items")
    category: Mapped[Category | None] = relationship()
    claims: Mapped[list["Claim"]] = relationship(back_populates="item")


# ==================================================================
# TABLE 5: claims
# Evidence table. Har item ke peeche saboot: URL, quote, date, confidence.
# review_status hi tumhari Human-in-the-loop review queue hai.
# ==================================================================
class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("snapshots.id"))
    source_url: Mapped[str] = mapped_column(String(1000))
    # Page se chhoti exact quote (poora page copy nahi)
    quote: Mapped[str] = mapped_column(Text)
    accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    # 0.0 (bilkul shak) se 1.0 (pakka). Kam score = review ke liye
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    # pending = review chahiye, approved, rejected
    review_status: Mapped[str] = mapped_column(String(20), default="pending")

    item: Mapped[Item] = relationship(back_populates="claims")


# ==================================================================
# TABLE 6: presence
# Market map ki table: kaun si company kis category mein active hai.
# first_seen_at se pata chalta hai trend kisne pehle shuru kiya (early mover).
# ==================================================================
class Presence(Base):
    __tablename__ = "presence"
    # Ek company + ek category ki sirf ek row
    __table_args__ = (UniqueConstraint("competitor_id", "category_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitors.id"))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


# ==================================================================
# TABLE 7: changes
# Do snapshots ka farq: kya naya aaya, kya hata, kya badla.
# Alerts yahin se nikalte hain.
# ==================================================================
class Change(Base):
    __tablename__ = "changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitors.id"))
    # Kis item ki tabdeeli (nullable: category level change mein item nahi hota)
    item_id: Mapped[int | None] = mapped_column(ForeignKey("items.id"))
    # new_item / removed_item / modified_item / new_category
    change_type: Mapped[str] = mapped_column(String(30))
    # high / medium / low (low sirf log hota hai, alert nahi bhejta)
    priority: Mapped[str] = mapped_column(String(10), default="low")
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    # Alert bheja ja chuka hai ya nahi (dobara alert se bachne ke liye)
    alerted: Mapped[bool] = mapped_column(Boolean, default=False)