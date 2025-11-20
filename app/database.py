from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

import os
DATABASE_URL = os.environ.get("DATABASE_URL")
REDIS_URL = os.environ.get("REDIS_URL") or os.environ.get("CELERY_BROKER_URL")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()
