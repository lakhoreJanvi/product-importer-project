from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from ..database import SessionLocal
from .. import models, schemas, crud
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

router = APIRouter(prefix="/products", tags=["products"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/")
def list_products(
    limit: int = 20,
    page: int = 1,
    sku: str = Query(None),
    name: str = Query(None),
    description: str = Query(None),
    active: bool = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(models.Product)

    if sku:
        query = query.filter(models.Product.sku.ilike(f"%{sku}%"))
    if name:
        query = query.filter(models.Product.name.ilike(f"%{name}%"))
    if description:
        query = query.filter(models.Product.description.ilike(f"%{description}%"))
    if active is not None:
        query = query.filter(models.Product.active == active)

    total = query.count()
    items = query.offset((page - 1) * limit).limit(limit).all()
    return {"items": items, "total": total, "page": page, "limit": limit}

@router.post("/", response_model=schemas.ProductRead)
def create_product(p: schemas.ProductCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Product).filter(func.lower(models.Product.sku) == p.sku.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="SKU already exists")

    prod = models.Product(sku=p.sku.strip(), name=p.name, description=p.description, price=p.price, active=p.active)
    try:
        db.add(prod)
        db.commit()
        db.refresh(prod)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="SKU already exists")
    
    from ..tasks import trigger_webhook
    webhooks = db.query(models.Webhook).filter(models.Webhook.event_type=="product.created", models.Webhook.enabled==True).all()
    for wh in webhooks:
        trigger_webhook.delay(wh.id, product_id=prod.id)
    return prod

@router.get("/{product_id}", response_model=schemas.ProductRead)
def get_product(product_id: int, db: Session = Depends(get_db)):
    prod = db.query(models.Product).get(product_id)
    if not prod:
        raise HTTPException(404, "Not found")
    return prod

@router.put("/{product_id}", response_model=schemas.ProductRead)
def update_product(product_id: int, p: schemas.ProductCreate, db: Session = Depends(get_db)):
    prod = db.query(models.Product).get(product_id)
    if not prod:
        raise HTTPException(404, "Not found")
    existing = db.query(models.Product)\
                 .filter(func.lower(models.Product.sku) == p.sku.lower(), models.Product.id != product_id)\
                 .first()
    if existing:
        raise HTTPException(status_code=400, detail="SKU already exists")

    prod.sku = p.sku.strip()
    prod.name = p.name
    prod.description = p.description
    prod.price = p.price
    prod.active = p.active
    try:
        db.commit()
        db.refresh(prod)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="SKU already exists")

    from ..tasks import trigger_webhook
    webhooks = db.query(models.Webhook).filter(models.Webhook.event_type=="product.updated", models.Webhook.enabled==True).all()
    for wh in webhooks:
        trigger_webhook.delay(wh.id, product_id=prod.id)
    return prod

@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    prod = db.query(models.Product).get(product_id)
    if not prod:
        raise HTTPException(404, "Not found")
    db.delete(prod)
    db.commit()
    from ..tasks import trigger_webhook
    webhooks = db.query(models.Webhook).filter(models.Webhook.event_type=="product.deleted", models.Webhook.enabled==True).all()
    for wh in webhooks:
        trigger_webhook.delay(wh.id, product_id=product_id)
    return {"status":"deleted"}

@router.delete("/")
def bulk_delete_all(confirm: bool = Query(False), db: Session = Depends(get_db)):
    if not confirm:
        raise HTTPException(400, "Pass confirm=true to actually delete all products")
    deleted = db.query(models.Product).delete()
    db.commit()
    return {"deleted": deleted}
