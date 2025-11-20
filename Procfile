web: uvicorn app.main:app --host 0.0.0.0 --port $PORT --timeout-keep-alive 600
worker: celery -A app.celery_app worker --loglevel=info
