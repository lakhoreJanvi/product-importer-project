from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, LargeBinary
from sqlalchemy.sql import expression
from sqlalchemy.sql import func
from .database import Base
from sqlalchemy.dialects.postgresql import JSONB
import datetime
from sqlalchemy import UniqueConstraint

class ImportJob(Base):
    __tablename__ = "import_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    status = Column(String(50), default="pending")
    total_rows = Column(Integer, default=0)
    processed_rows = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class TempFile(Base):
    __tablename__ = "temp_files"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_data = Column(LargeBinary, nullable=False)  # Stores file chunks
    created_at = Column(DateTime(timezone=True), server_default=func.now())

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
