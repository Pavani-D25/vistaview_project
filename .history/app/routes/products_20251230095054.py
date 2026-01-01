
import os
import json
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional
from ..db import get_db
from ..models import Product
from ..schemas import ProductOut, ProductListResponse
from ..minio_client import presign_get

router = APIRouter(prefix="/api/products", tags=["products"])

def get_image_url(image_key: str, expires_seconds: int = 3600) -> str:
    """Get image URL from MinIO"""
    if not image_key:
        return None
    
    # Return MinIO public URL
    return presign_get(image_key, expires_seconds)

@router.get("", response_model=ProductListResponse)
def list_products(
    q: Optional[str] = Query(None, description="Search in SKU, name, or category"),
    session_id: Optional[str] = Query(None, description="Filter by upload session ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    expires_seconds: int = Query(3600, ge=60, le=86400, description="URL expiry time"),
    db: Session = Depends(get_db),
):
    """
    List products with optional search and pagination
    
    - **q**: Search query (matches SKU, Chinese name, or category)
    - **session_id**: Filter products from a specific upload session
    - **skip**: Number of items to skip (for pagination)
    - **limit**: Max items to return
    - **expires_seconds**: How long the image URLs stay valid
    """
    # Build query
    query = db.query(Product)
    
    # Filter by session_id if provided
    if session_id:
        query = query.filter(Product.session_id == session_id)
    
    # Apply search filter
    if q:
        search = f"%{q}%"
        query = query.filter(
            or_(
                Product.sku_code.ilike(search),
                Product.cn_name.ilike(search),
                Product.category.ilike(search),
            )
        )
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    products = query.order_by(Product.created_at.desc()).offset(skip).limit(limit).all()
    
    # Generate presigned URLs for each product
    result = []
    for p in products:
        # Parse side_views_keys JSON if available
        side_views_urls = None
        if p.side_views_keys:
            try:
                side_views_dict = json.loads(p.side_views_keys)
                side_views_urls = {
                    angle_key: get_image_url(view_key, expires_seconds)
                    for angle_key, view_key in side_views_dict.items()
                }
            except json.JSONDecodeError:
                side_views_urls = None
        
        result.append(ProductOut(
            id=p.id,
            sku_code=p.sku_code,
            cn_name=p.cn_name,
            category=p.category,
            dims_l=p.dims_l,
            dims_w=p.dims_w,
            dims_h=p.dims_h,
            description=p.description,
            image_url=get_image_url(p.image_key, expires_seconds) if p.image_key else None,
            collage_url=get_image_url(p.collage_key, expires_seconds) if p.collage_key else None,
            left_view_url=get_image_url(p.left_view_key, expires_seconds) if p.left_view_key else None,
            right_view_url=get_image_url(p.right_view_key, expires_seconds) if p.right_view_key else None,
            side_views_urls=side_views_urls,
            view_generation_status=p.view_generation_status,
        ))
    
    return ProductListResponse(
        products=result,
        total=total,
        skip=skip,
        limit=limit
    )

@router.get("/{product_id}", response_model=ProductOut)
def get_product(
    product_id: str,
    expires_seconds: int = Query(3600, ge=60, le=86400),
    db: Session = Depends(get_db),
):
    """Get single product by ID"""
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Parse side_views_keys JSON if available
    side_views_urls = None
    if product.side_views_keys:
        try:
            side_views_dict = json.loads(product.side_views_keys)
            side_views_urls = {
                angle_key: get_image_url(view_key, expires_seconds)
                for angle_key, view_key in side_views_dict.items()
            }
        except json.JSONDecodeError:
            side_views_urls = None
    
    return ProductOut(
        id=product.id,
        sku_code=product.sku_code,
        cn_name=product.cn_name,
        category=product.category,
        dims_l=product.dims_l,
        dims_w=product.dims_w,
        dims_h=product.dims_h,
        description=product.description,
        image_url=get_image_url(product.image_key, expires_seconds),
        collage_url=get_image_url(product.collage_key, expires_seconds),
        left_view_url=get_image_url(product.left_view_key, expires_seconds) if product.left_view_key else None,
        right_view_url=get_image_url(product.right_view_key, expires_seconds) if product.right_view_key else None,
        side_views_urls=side_views_urls,
        view_generation_status=product.view_generation_status,
    )