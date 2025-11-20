from sqlalchemy.orm import Session
from . import models, schemas
from sqlalchemy import select, update, delete, func
from typing import List, Optional

def create_or_update_products_bulk(db: Session, rows: List[dict]):
    """
    Bulk upsert using SQL ON CONFLICT on lower(sku).
    We generate a VALUES statement and use Postgres ON CONFLICT.
    """
    if not rows:
        return 0

    conn = db.bind
    insert_stmt = """
    INSERT INTO products (sku, name, description, active, created_at, updated_at)
    VALUES %s
    ON CONFLICT (lower(sku)) DO UPDATE
      SET name = EXCLUDED.name,
          description = EXCLUDED.description,
          active = EXCLUDED.active,
          updated_at = now()
    """
    
    raw_conn = conn.raw_connection()
    try:
        with raw_conn.cursor() as cur:
            args_str = ",".join(cur.mogrify("(%s,%s,%s,%s,now(),now())",
                                            (r['sku'], r['name'], r.get('description'), r.get('active'))).decode('utf-8')
                                for r in rows)
            cur.execute(insert_stmt % args_str)
        raw_conn.commit()
    finally:
        raw_conn.close()
    return len(rows)

def get_products(db: Session, limit: int = 20, offset: int = 0, filters: dict = None):
    q = db.query(models.Product)
    if filters:
        if filters.get("sku"):
            q = q.filter(func.lower(models.Product.sku).like(f"%{filters['sku'].lower()}%"))
        if filters.get("name"):
            q = q.filter(models.Product.name.ilike(f"%{filters['name']}%"))
        if filters.get("active") is not None:
            q = q.filter(models.Product.active == filters['active'])
        if filters.get("description"):
            q = q.filter(models.Product.description.ilike(f"%{filters['description']}%"))
    total = q.count()
    items = q.order_by(models.Product.id.desc()).offset(offset).limit(limit).all()
    return total, items

def get_webhooks(db: Session):
    return db.query(models.Webhook).all()

def get_webhook(db: Session, webhook_id: int):
    return db.query(models.Webhook).filter(models.Webhook.id == webhook_id).first()

def create_webhook(db: Session, webhook: schemas.WebhookCreate):
    db_webhook = models.Webhook(**webhook.dict())
    db.add(db_webhook)
    db.commit()
    db.refresh(db_webhook)
    return db_webhook

def update_webhook(db: Session, webhook_id: int, webhook: schemas.WebhookUpdate):
    db_webhook = get_webhook(db, webhook_id)
    if not db_webhook:
        return None
    for key, value in webhook.dict().items():
        setattr(db_webhook, key, value)
    db.commit()
    db.refresh(db_webhook)
    return db_webhook

def delete_webhook(db: Session, webhook_id: int):
    db_webhook = get_webhook(db, webhook_id)
    if db_webhook:
        db.delete(db_webhook)
        db.commit()
        return True
    return False
