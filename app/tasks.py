# app/tasks.py
from .celery_app import celery
from .database import SessionLocal
from . import models, crud, utils
import csv, os, httpx, tempfile,requests
from io import TextIOWrapper
from sqlalchemy.orm import Session
import time

BATCH_SIZE = 5000

@celery.task(name="app.tasks.process_csv_import")
def process_csv_import(job_id: int, file_url: str):
    db = SessionLocal()
    try:
        job = db.query(models.ImportJob).get(job_id)
        job.status = "parsing"
        job.total_rows = 0
        job.processed_rows = 0
        db.commit()
        utils.publish_progress(job_id, {"status": "parsing", "processed": 0, "total": 0})

        # Stream file from URL
        resp = requests.get(file_url, stream=True, timeout=60)
        resp.raise_for_status()
        resp.raw.decode_content = True  # important

        wrapper = TextIOWrapper(resp.raw, encoding="utf-8")
        reader = csv.DictReader(wrapper)

        batch = []
        processed = 0
        total_estimate = 0  # unknown until we iterate

        seen = set()  # if you want to dedupe by sku
        for row in reader:
            total_estimate += 1

            # optional: normalize / validate fields before inserting
            sku = (row.get("sku") or row.get("SKU") or row.get("Sku") or "").strip()
            if not sku:
                continue

            if sku.lower() in seen:
                continue
            seen.add(sku.lower())

            # Map CSV columns to DB columns — adjust to your model
            mapped = {
                "sku": sku,
                "name": (row.get("name") or "")[:512],
                "description": row.get("description"),
                "active": True,
            }
            batch.append(mapped)

            if len(batch) >= BATCH_SIZE:
                # bulk insert - faster than add() per object
                db.bulk_insert_mappings(models.Product, batch)
                db.commit()
                processed += len(batch)
                batch = []
                seen.clear()  # reset dedupe set if desired

                job.processed_rows = processed
                job.total_rows = total_estimate
                job.status = "importing"
                db.commit()
                utils.publish_progress(job_id, {"status": "importing", "processed": processed, "total": total_estimate})

        # final batch
        if batch:
            db.bulk_insert_mappings(models.Product, batch)
            db.commit()
            processed += len(batch)

        # final status updates
        job.processed_rows = processed
        job.total_rows = total_estimate
        job.status = "validating"
        db.commit()
        utils.publish_progress(job_id, {"status": "validating", "processed": processed, "total": total_estimate})
        time.sleep(0.2)

        job.status = "completed"
        db.commit()
        utils.publish_progress(job_id, {"status": "completed", "processed": processed, "total": total_estimate})

        # optionally trigger webhooks
        webhooks = (
            db.query(models.Webhook)
            .filter(models.Webhook.event_type == "import.finished", models.Webhook.enabled == True)
            .all()
        )
        for wh in webhooks:
            celery.send_task("app.tasks.trigger_webhook", args=(wh.id, job_id))

        return {"processed": processed}

    except Exception as e:
        # mark job failed
        try:
            job.status = "failed"
            job.error = str(e)
            db.commit()
            utils.publish_progress(job_id, {"status": "failed", "error": str(e)})
        except Exception:
            pass
        raise
    finally:
        db.close()

# BATCH_SIZE = 1000

# @celery.task(bind=True)
# def process_csv_import(self, job_id: int, file_url: str):
#     db: Session = SessionLocal()
#     try:
#         job = db.query(models.ImportJob).get(job_id)
#         job.status = "parsing"
#         db.commit()
#         utils.publish_progress(job_id, {"status": "parsing", "processed": 0, "total": 0})

#         with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
#             tmp_path = tmp.name
#             with httpx.Client(timeout=30.0) as client:
#                 r = client.get(file_url)
#                 r.raise_for_status()
#                 tmp.write(r.content)

#         processed = 0
#         batch = []
#         seen = set()

#         with open(tmp_path, "r", encoding="utf-8") as f:
#             reader = list(csv.DictReader(f))
#             total = len(reader)

#             job.status = "importing"
#             db.commit()
#             utils.publish_progress(job_id, {"status": "importing", "processed": 0, "total": total})

#             for i, row in enumerate(reader, start=1):
#                 sku = row.get("sku") or row.get("SKU") or row.get("Sku")
#                 if not sku:
#                     continue
#                 normalized = sku.strip().lower()
#                 if normalized in seen:
#                     continue
#                 seen.add(normalized)

#                 batch.append({
#                     "sku": sku.strip(),
#                     "name": row.get("name", "")[:512],
#                     "description": row.get("description"),
#                     "price": row.get("price"),
#                     "active": True,
#                 })

#                 if len(batch) >= BATCH_SIZE:
#                     crud.create_or_update_products_bulk(db, batch)
#                     processed += len(batch)
#                     batch = []
#                     seen = set()

#                     job.processed_rows = processed
#                     job.total_rows = total
#                     db.commit()
#                     utils.publish_progress(job_id, {"status": "importing", "processed": processed, "total": total})

#             if batch:
#                 crud.create_or_update_products_bulk(db, batch)
#                 processed += len(batch)

#         job.status = "validating"
#         job.processed_rows = processed
#         job.total_rows = total
#         db.commit()
#         utils.publish_progress(job_id, {"status": "validating", "processed": processed, "total": total})
#         time.sleep(0.5)

#         job.status = "completed"
#         db.commit()
#         utils.publish_progress(job_id, {"status": "completed", "processed": processed, "total": total})

#         try:
#             os.remove(tmp_path)
#         except Exception:
#             pass

#         webhooks = (
#             db.query(models.Webhook)
#             .filter(models.Webhook.event_type == "import.finished",
#                     models.Webhook.enabled == True)
#             .all()
#         )
#         for wh in webhooks:
#             celery.send_task("app.tasks.trigger_webhook", args=(wh.id, job_id))

#         return {"processed": processed}

#     except Exception as e:
#         job.status = "failed"
#         job.error = str(e)
#         db.commit()
#         utils.publish_progress(job_id, {"status": "failed", "error": str(e)})
#         raise

#     finally:
#         db.close()

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
