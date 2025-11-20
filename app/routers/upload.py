from fastapi import APIRouter, File, UploadFile
from uuid import uuid4
import os
from ..database import SessionLocal
from .. import models
from ..tasks import process_csv_import
from supabase import create_client
from pydantic import BaseModel
import shutil

router = APIRouter(prefix="/upload", tags=["upload"])

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
BUCKET = os.environ.get("BUCKET", "uploads")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("Supabase env vars missing")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Request model
class FileNameRequest(BaseModel):
    filename: str

@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    file_location = f"/tmp/{uuid4().hex}_{file.filename}"

    # Save file in streaming mode — FIXES the error
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Trigger Celery task
    # task = process_csv_import.delay(file_location)

    return {"status": "uploaded", "temp_location": file_location}

@router.post("/signed-url")
def get_signed_url(req: FileNameRequest):
    unique_filename = f"{uuid4().hex}_{req.filename}"
    signed_url_data = supabase.storage.from_(BUCKET).create_signed_upload_url(unique_filename)

    # adjust keys depending on lib version
    upload_url = signed_url_data.get("signedurl") or signed_url_data.get("signed_url") or signed_url_data.get("signedURL")
    public_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{unique_filename}"

    if not upload_url:
        raise RuntimeError(f"Unexpected signed_url response: {signed_url_data}")

    return {"upload_url": upload_url, "filename": unique_filename, "public_url": public_url}

class CSVProcessRequest(BaseModel):
    filename: str
    public_url: str

@router.post("/process-csv")
def process_csv_task(req: CSVProcessRequest):
    db = SessionLocal()
    job = models.ImportJob(status="pending", total_rows=0, processed_rows=0)
    db.add(job)
    db.commit()
    db.refresh(job)
    job_id = job.id
    db.close()

    # CALL CELERY TASK
    process_csv_import.delay(job_id, req.public_url)

    return {"job_id": job_id, "message": "CSV processing started"}