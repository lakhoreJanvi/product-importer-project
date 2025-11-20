from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import requests
import time
from ..database import SessionLocal
from .. import models, schemas

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=schemas.WebhookRead)
def add_webhook(h: schemas.WebhookCreate, db: Session = Depends(get_db)):
    wh = models.Webhook(url=str(h.url), event_type=h.event_type, enabled=h.enabled)
    db.add(wh)
    db.commit() 
    db.refresh(wh)
    return wh

@router.get("/", response_model=List[schemas.WebhookRead])
def list_webhooks(db: Session = Depends(get_db)):
    return db.query(models.Webhook).all()

@router.put("/{webhook_id}", response_model=schemas.WebhookRead)
def update_webhook(webhook_id: int, h: schemas.WebhookUpdate, db: Session = Depends(get_db)):
    wh = db.query(models.Webhook).get(webhook_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")
    wh.url = str(h.url)
    wh.event_type = h.event_type
    wh.enabled = h.enabled
    db.commit()
    db.refresh(wh)
    return wh

@router.delete("/{webhook_id}")
def delete_webhook(webhook_id: int, db: Session = Depends(get_db)):
    wh = db.query(models.Webhook).get(webhook_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")
    db.delete(wh)
    db.commit()
    return {"status": "deleted"}

@router.post("/{webhook_id}/test")
def test_webhook(webhook_id: int, db: Session = Depends(get_db)):
    import requests
    wh = db.query(models.Webhook).get(webhook_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")
    try:
        resp = requests.post(wh.url, json={"test": True}, timeout=5)
        return {"status_code": resp.status_code, "response": resp.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
