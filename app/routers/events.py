from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json, asyncio
from app.database import SessionLocal
from app.models import ImportJob

router = APIRouter()  

@router.get("/events/import/{job_id}")
async def import_events(job_id: int):

    async def event_stream():
        while True:
            db = SessionLocal()
            job = db.query(ImportJob).get(job_id)
            db.close()

            if not job:
                # Send error event
                yield "data: " + json.dumps({
                    "status": "failed",
                    "error": "Job not found"
                }) + "\n\n"
                break

            payload = {
                "status": job.status,
                "processed": job.processed_rows,
                "total": job.total_rows,
                "error": job.error,
            }

            yield f"data: {json.dumps(payload)}\n\n"

            if job.status in ("completed", "failed"):
                break

            await asyncio.sleep(1)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
