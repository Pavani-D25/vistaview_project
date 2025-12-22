
from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.sql import func
from .db import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True)
    sku_code = Column(String, index=True, nullable=True)
    cn_name = Column(String, index=True, nullable=True)
    category = Column(String, index=True, nullable=True)
    
    # Dimensions in mm
    dims_l = Column(Integer, nullable=True)
    dims_w = Column(Integer, nullable=True)
    dims_h = Column(Integer, nullable=True)
    
    description = Column(Text, nullable=True)
    
    # MinIO object keys (NOT URLs)
    image_key = Column(String, nullable=True)      # e.g., "images/p001.jpg"
    collage_key = Column(String, nullable=True)    # e.g., "collages/c001.jpg"
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())