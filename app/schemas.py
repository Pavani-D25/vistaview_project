from pydantic import BaseModel
from typing import Optional

class ProductOut(BaseModel):
    """Product response for API"""
    id: str
    sku_code: Optional[str] = None
    cn_name: Optional[str] = None
    category: Optional[str] = None
    dims_l: Optional[int] = None
    dims_w: Optional[int] = None
    dims_h: Optional[int] = None
    description: Optional[str] = None
    
    # These will be presigned URLs
    image_url: Optional[str] = None
    collage_url: Optional[str] = None
    
    class Config:
        from_attributes = True

class ProductListResponse(BaseModel):
    """Paginated product list"""
    products: list[ProductOut]
    total: int
    skip: int
    limit: int