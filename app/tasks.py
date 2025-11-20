from .celery_app import celery
from .database import SessionLocal
from . import models, crud, utils
import csv, os, httpx, tempfile,requests
from io import TextIOWrapper
from sqlalchemy.orm import Session
import time
from celery import shared_task
import traceback
from uuid import uuid4

BATCH_SIZE = 5000

@celery.task
def process_csv_import(job_id, filename):
    db: Session = SessionLocal()
    temp_file_path = None
    
    try:
        job = db.query(models.ImportJob).get(job_id)
        job.status = "downloading"
        db.commit()

        os.makedirs("/tmp/csv_processing", exist_ok=True)
        temp_file_path = f"/tmp/csv_processing/{filename}"
        
        print(f"[WORKER] Reconstructing file: {filename}")
        
        chunks = (
            db.query(models.TempFile)
            .filter(models.TempFile.filename == filename)
            .order_by(models.TempFile.chunk_index)
            .all()
        )
        
        if not chunks:
            raise FileNotFoundError(f"No file chunks found for: {filename}")
        
        with open(temp_file_path, "wb") as f:
            for chunk in chunks:
                f.write(chunk.chunk_data)
        
        print(f"[WORKER] File reconstructed: {temp_file_path}")
        
        db.query(models.TempFile).filter(
            models.TempFile.filename == filename
        ).delete()
        db.commit()
        
        job.status = "importing"
        db.commit()

        total = 0
        processed = 0
        batch = []
        seen = set()
        
        SEEN_CLEAR_INTERVAL = 10000

        with open(temp_file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                total += 1

                sku = row.get("sku")
                if not sku:
                    continue

                normalized = sku.strip().lower()
                if normalized in seen:
                    continue
                seen.add(normalized)

                batch.append({
                    "sku": sku.strip(),
                    "name": row.get("name", "").strip()[:512],
                    "description": row.get("description", "")[:2000],
                    "price": row.get("price") if "price" in row else None,
                    "active": True,
                })

                if len(batch) >= BATCH_SIZE:
                    crud.create_or_update_products_bulk(db, batch)
                    processed += len(batch)
                    batch = []
                    
                    if total % SEEN_CLEAR_INTERVAL == 0:
                        seen = set()

                    job.processed_rows = processed
                    job.total_rows = total
                    db.commit()
                    db.expire_all()

            if batch:
                crud.create_or_update_products_bulk(db, batch)
                processed += len(batch)

        job.status = "completed"
        job.processed_rows = processed
        job.total_rows = total
        db.commit()
        
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
                
        return True

    except Exception as e:
        job = db.query(models.ImportJob).get(job_id)
        if job:
            job.status = "failed"
            job.error = str(e)
            db.commit()
        print("ERROR:", traceback.format_exc())
        
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
        return False

    finally:
        db.close()

@celery.task
def cleanup_old_csv_files():
    """Clean up CSV files older than 24 hours"""
    import time
    upload_dir = "/app/csv_uploads"
    
    if not os.path.exists(upload_dir):
        return
    
    now = time.time()
    for filename in os.listdir(upload_dir):
        filepath = os.path.join(upload_dir, filename)
        if os.path.isfile(filepath):
            file_age = now - os.path.getmtime(filepath)
            # Delete files older than 24 hours
            if file_age > 86400:
                try:
                    os.remove(filepath)
                except:
                    pass

@celery.task
def trigger_webhook(webhook_id: int, job_id: int = None,
                    product_id: int = None, event: str = None):
    db = SessionLocal()
    try:
        wh = db.query(models.Webhook).get(webhook_id)
        if not wh or not wh.enabled:
            return {"status": "disabled"}

        payload = {"event": wh.event}
        if job_id:
            payload["job_id"] = job_id
        if product_id:
            payload["product_id"] = product_id

        with httpx.Client(timeout=10) as client:
            r = client.post(wh.url, json=payload)
            return {"status_code": r.status_code, "text": r.text}

    except Exception as e:
        return {"error": str(e)}

    finally:
        db.close()
