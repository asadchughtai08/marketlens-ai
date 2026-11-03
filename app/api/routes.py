# app/api/routes.py
# Saare API endpoints. Endpoints "def" (async nahi) hain kyunke crawl/Gemini blocking kaam hain;
# FastAPI inhein khud alag thread mein chalata hai, server atakta nahi.
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session
from app.db.base import SessionLocal
from app.services import pipeline

router = APIRouter()


def get_db():
    """Har request ko apna DB session; khatam hone par khud band."""
    with SessionLocal() as db:
        yield db


def comp_or_404(db: Session, comp_id: int) -> Competitor:
    comp = db.get(Competitor, comp_id)
    if comp is None:
        raise HTTPException(status_code=404, detail="Company nahi mili")
    return comp


# ---- Request bodies (Pydantic in/out validation) ----
class PasteIn(BaseModel):
    url: str
    # Bohat chhota ya bohat bara text reject
    text: str = Field(min_length=50, max_length=200_000)


class ReviewIn(BaseModel):
    status: Literal["approved", "rejected"]

class MergeIn(BaseModel):
    into_id: int


# ---- Competitors ----
@router.get("/competitors")
def list_competitors(db: Session = Depends(get_db)):
    rows = db.scalars(select(Competitor).order_by(Competitor.id))
    return [{"id": c.id, "name": c.name, "website": c.website,
             "products_url": c.products_url, "active": c.active,
             "crawl_method": c.crawl_method} for c in rows]


@router.get("/competitors/{comp_id}/snapshots")
def list_snapshots(comp_id: int, db: Session = Depends(get_db)):
    comp_or_404(db, comp_id)
    rows = db.scalars(select(Snapshot).where(Snapshot.competitor_id == comp_id)
                      .order_by(desc(Snapshot.id)))
    return [{"id": s.id, "url": s.url, "fetched_at": s.fetched_at,
             "status": s.status, "method": s.method,
             "hash": s.content_hash[:10]} for s in rows]


@router.get("/competitors/{comp_id}/items")
def list_items(comp_id: int, category: str | None = None,
               db: Session = Depends(get_db)):
    comp_or_404(db, comp_id)
    q = select(Item).where(Item.competitor_id == comp_id)
    if category:
        q = q.where(Item.suggested_category == category.lower().strip())
    out = []
    for it in db.scalars(q.order_by(Item.id)):
        # Sab se naya evidence
        claim = max(it.claims, key=lambda c: c.id) if it.claims else None
        out.append({
            "id": it.id, "kind": it.kind, "name": it.name,
            "brand": it.brand, "model": it.model, "capacity": it.capacity,
            "specs": it.specs, "category": it.suggested_category,
            "approved_category": it.category.name if it.category else None,
            "category_status": it.category.status if it.category else None,
            "first_seen_at": it.first_seen_at, "is_active": it.is_active,
            "evidence": None if claim is None else {
                "claim_id": claim.id, "quote": claim.quote,
                "source_url": claim.source_url,
                "confidence": claim.confidence,
                "review_status": claim.review_status,
                "verdict": claim.verdict, "reasons": claim.reasons,},
        })
    return out


# ---- Pipeline actions ----
@router.post("/competitors/{comp_id}/crawl")
def crawl(comp_id: int, db: Session = Depends(get_db)):
    return pipeline.crawl_competitor(db, comp_or_404(db, comp_id))


@router.post("/competitors/{comp_id}/paste")
def paste(comp_id: int, body: PasteIn, db: Session = Depends(get_db)):
    return pipeline.paste_snapshot(db, comp_or_404(db, comp_id), body.url, body.text)


@router.post("/competitors/{comp_id}/extract")
def extract(comp_id: int, force: bool = False, db: Session = Depends(get_db)):
    comp = comp_or_404(db, comp_id)
    try:
        return pipeline.extract_latest(db, comp, force)
    except RuntimeError as e:
        # Gemini ka masla (key, model, limit): 502 = upstream service fail
        raise HTTPException(status_code=502, detail=str(e))


# ---- Human review queue ----
@router.get("/review")
def review_queue(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Claim, Item).join(Item, Claim.item_id == Item.id)
        .where(Claim.review_status == "pending")
        .order_by(Claim.confidence)).all()
    return [{"claim_id": c.id, "company_id": it.competitor_id, "item": it.name,
             "confidence": c.confidence, "quote": c.quote,
             "source_url": c.source_url, "verdict": c.verdict, "reasons": c.reasons} for c, it in rows]


@router.post("/claims/{claim_id}/review")
def review_claim(claim_id: int, body: ReviewIn, db: Session = Depends(get_db)):
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim nahi mila")
    claim.review_status = body.status
    db.commit()
    return {"claim_id": claim_id, "review_status": claim.review_status}

# ---- Categories ----
@router.get("/categories")
def list_categories(status: str | None = None, db: Session = Depends(get_db)):
    q = (select(Category, func.count(Item.id))
         .outerjoin(Item, Item.category_id == Category.id)
         .group_by(Category.id).order_by(Category.name))
    if status:
        q = q.where(Category.status == status)
    return [{"id": c.id, "name": c.name, "status": c.status,
             "aliases": c.aliases, "items": n} for c, n in db.execute(q).all()]


@router.post("/categories/relink")
def relink_categories(db: Session = Depends(get_db)):
    return cats.relink_all_items(db)


@router.post("/categories/{category_id}/approve")
def approve_category(category_id: int, db: Session = Depends(get_db)):
    try:
        cat = cats.approve_category(db, category_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"id": cat.id, "name": cat.name, "status": cat.status}


@router.post("/categories/{category_id}/merge")
def merge_category(category_id: int, body: MergeIn, db: Session = Depends(get_db)):
    try:
        tgt = cats.merge_category(db, category_id, body.into_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"merged_into": tgt.name, "aliases": tgt.aliases}

@router.get("/verification/summary")
def verification_summary(db: Session = Depends(get_db)):
    rows = db.execute(select(Claim.verdict, func.count(Claim.id))
                      .group_by(Claim.verdict)).all()
    return {(v or "unverified"): n for v, n in rows}
