from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, func, Index
from sqlalchemy.sql import expression
from .database import Base
from sqlalchemy.dialects.postgresql import JSONB
import datetime
from sqlalchemy import UniqueConstraint

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(255), nullable=False)
    name = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(String(64), nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), server_default=func.now())

    __table_args__ = (
        
    )

from sqlalchemy import Index
Index('ux_products_lower_sku', func.lower(Product.sku), unique=True)

class Webhook(Base):
    __tablename__ = "webhooks"
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(2048), nullable=False)
    event_type = Column(String(128), nullable=False)
    enabled = Column(Boolean, default=True)

class ImportJob(Base):
    __tablename__ = "import_jobs"
    id = Column(Integer, primary_key=True, index=True)
    total_rows = Column(Integer, default=0)
    processed_rows = Column(Integer, default=0)
    status = Column(String(64), default="pending") 
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), server_default=func.now())
