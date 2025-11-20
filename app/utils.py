import json
import os
from redis import Redis
from dotenv import load_dotenv
load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")
redis_cli = Redis.from_url(REDIS_URL)

def publish_progress(job_id: int, payload: dict):
    channel = f"import:progress:{job_id}"
    redis_cli.publish(channel, json.dumps(payload))
