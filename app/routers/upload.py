from fastapi import APIRouter, File, UploadFile, HTTPException, Form, BackgroundTasks
from uuid import uuid4
import os, csv, io
from ..database import SessionLocal
from .. import models
from .. import crud
import traceback

router = APIRouter(prefix="/upload", tags=["upload"])

def process_csv_content(content: bytes, job_id: int):
    """Process CSV directly from memory"""
    db = SessionLocal()
    try:
        job = db.query(models.ImportJob).get(job_id)
        job.status = "importing"
        db.commit()
        
        csv_text = content.decode('utf-8')
        csv_file = io.StringIO(csv_text)
        reader = csv.DictReader(csv_file)
        
        total = 0
        processed = 0
        batch = []
        seen = set()
        BATCH_SIZE = 5000
        
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
        
    except Exception as e:
        job = db.query(models.ImportJob).get(job_id)
        if job:
            job.status = "failed"
            job.error = str(e)
            db.commit()
        print(f"[ERROR] Processing failed: {str(e)}")
        traceback.print_exc()
    finally:
        db.close()

@router.post("/chunk")
async def upload_chunk(
    chunk: UploadFile = File(...),
    chunkIndex: int = Form(...),
    totalChunks: int = Form(...),
    uploadId: str = Form(...),
    filename: str = Form(...)
):
    """Save chunks to /tmp (not database)"""
    try:
        upload_dir = f"/tmp/upload_chunks/{uploadId}"
        os.makedirs(upload_dir, exist_ok=True)
        
        chunk_path = os.path.join(upload_dir, f"chunk_{chunkIndex}")
        
        with open(chunk_path, "wb") as f:
            content = await chunk.read()
            f.write(content)
        
        print(f"[CHUNK] Saved {chunkIndex + 1}/{totalChunks}")
        
        return {"status": "success", "chunkIndex": chunkIndex}
        
    except Exception as e:
        print(f"[ERROR] Chunk failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/finalize")
async def finalize_upload(data: dict, background_tasks: BackgroundTasks):
    """Combine chunks and process in background"""
    try:
        upload_id = data.get("uploadId")
        filename = data.get("filename")
        
        upload_dir = f"/tmp/upload_chunks/{upload_id}"
        
        if not os.path.exists(upload_dir):
            raise HTTPException(status_code=404, detail="Upload not found")
        
        chunks = sorted(
            [f for f in os.listdir(upload_dir) if f.startswith("chunk_")],
            key=lambda x: int(x.split("_")[1])
        )
        
        combined_data = bytearray()
        for chunk_file in chunks:
            chunk_path = os.path.join(upload_dir, chunk_file)
            with open(chunk_path, "rb") as f:
                combined_data.extend(f.read())
            os.remove(chunk_path)
        
        os.rmdir(upload_dir)
        
        db = SessionLocal()
        try:
            job = models.ImportJob(status="pending", total_rows=0, processed_rows=0)
            db.add(job)
            db.commit()
            db.refresh(job)
            job_id = job.id
        finally:
            db.close()
        
        background_tasks.add_task(process_csv_content, bytes(combined_data), job_id)
        print(f"[FINALIZE] Processing started for job {job_id}")
        return {"job_id": job_id, "status": "started"}
        
    except Exception as e:
        print(f"[ERROR] Finalize failed: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
