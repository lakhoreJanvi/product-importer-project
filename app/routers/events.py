from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import redis
import os
from dotenv import load_dotenv
load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")
r = redis.from_url(REDIS_URL)

router = APIRouter(prefix="/events", tags=["events"])

def event_stream(job_id: int):
    pubsub = r.pubsub(ignore_subscribe_messages=True)

    channel = f"import:progress:{job_id}"
    pubsub.subscribe(channel)

    try:
        for message in pubsub.listen():
            if message["type"] != "message":
                continue

            data = message["data"].decode("utf-8")
            if isinstance(data, bytes):
                data = data.decode()

            yield f"data: {data}\n\n"
            yield ": heartbeat\n\n" 
    finally:
        pubsub.close()

@router.get("/import/{job_id}")
def import_events(job_id: int):
    return StreamingResponse(
        event_stream(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Transfer-Encoding": "chunked",
            "X-Accel-Buffering": "no",
        }
    )
