from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
import os
from ..database import SessionLocal, engine
from .. import models
from ..tasks import process_csv_import
from .. import utils
from sqlalchemy.orm import Session
from fastapi import BackgroundTasks
from uuid import uuid4

router = APIRouter(prefix="/upload", tags=["upload"])

UPLOAD_DIR = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Only CSV allowed")

    filename = f"{uuid4().hex}_{file.filename}"
    path = os.path.join(UPLOAD_DIR, filename)

    with open(path, "wb") as buffer:
        while chunk := await file.read(1024 * 1024):
            buffer.write(chunk)

    db = SessionLocal()
    job = models.ImportJob(status="pending", total_rows=0, processed_rows=0)
    db.add(job)
    db.commit()
    db.refresh(job)
    job_id = job.id
    db.close()

    process_csv_import.delay(job_id, path)
    return {"job_id": job_id, "message": "Import started"}
