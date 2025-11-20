from .celery_app import celery
from .database import SessionLocal
from . import models, crud, utils
import csv, os, httpx
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import time

load_dotenv()

BATCH_SIZE = 1000
UPLOAD_DIR = "/usr/src/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@celery.task(bind=True)
def process_csv_import(self, job_id: int, file_path: str):
    db: Session = SessionLocal()

    try:
        job = db.query(models.ImportJob).get(job_id)
        job.status = "parsing"
        db.commit()
        utils.publish_progress(job_id, {"status": "parsing", "processed": 0, "total": 0})

        processed = 0
        batch = []
        seen = set()

        with open(file_path, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            total = len(reader)

            job.status = "importing"
            db.commit()
            utils.publish_progress(job_id, {"status": "importing", "processed": 0, "total": total})

            for i, row in enumerate(reader, start=1):
                sku = row.get("sku") or row.get("SKU") or row.get("Sku")
                if not sku:
                    continue
                normalized = sku.strip().lower()
                if normalized in seen:
                    continue
                seen.add(normalized)

                batch.append({
                    "sku": sku.strip(),
                    "name": row.get("name", "")[:512],
                    "description": row.get("description"),
                    "price": row.get("price"),
                    "active": True,
                })

                if len(batch) >= BATCH_SIZE:
                    crud.create_or_update_products_bulk(db, batch)
                    processed += len(batch)
                    batch = []
                    seen = set()

                    job.processed_rows = processed
                    job.total_rows = total
                    db.commit()
                    utils.publish_progress(
                        job_id,
                        {"status": "importing", "processed": processed, "total": total},
                    )

            if batch:
                crud.create_or_update_products_bulk(db, batch)
                processed += len(batch)

            job.status = "validating"
            job.processed_rows = processed
            job.total_rows = total
            db.commit()
            utils.publish_progress(
                job_id,
                {"status": "validating", "processed": processed, "total": total}
            )
            time.sleep(0.5)

            job.status = "completed"
            db.commit()
            utils.publish_progress(
                job_id,
                {"status": "completed", "processed": processed, "total": total}
            )

        webhooks = (
            db.query(models.Webhook)
            .filter(models.Webhook.event_type == "import.finished",
                    models.Webhook.enabled == True)
            .all()
        )
        for wh in webhooks:
            celery.send_task("app.tasks.trigger_webhook", args=(wh.id, job_id))

        return {"processed": processed}

    except Exception as e:
        job.status = "failed"
        job.error = str(e)
        db.commit()
        utils.publish_progress(job_id, {"status": "failed", "error": str(e)})
        raise

    finally:
        db.close()

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
