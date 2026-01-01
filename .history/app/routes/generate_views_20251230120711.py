from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from PIL import Image
from io import BytesIO
import json

from app.db import get_db
from app.models import Product
from app.minio_client import get_object, upload_image, presign_get

router = APIRouter()

@router.post("/{product_id}/generate-views")
async def generate_side_views_endpoint(
    product_id: str,
    angles: str = Query("15,30,45", description="Comma-separated angles (e.g., '15,30,45')"),
    db: Session = Depends(get_db),
):
    """
    Generate side views on-demand for a specific product.
    Returns URLs of the generated views.
    """
    try:
        # Import here to avoid issues when dependencies not available
        from ..zero123_generator import generate_multi_angle_side_views, DEPENDENCIES_AVAILABLE
        
        if not DEPENDENCIES_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="Zero123 dependencies not installed. Side view generation is not available."
            )
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Zero123 module not available. Side view generation is not available."
        )
    
    # Get product
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if product has an image
    if not product.image_key:
        raise HTTPException(status_code=400, detail="Product has no image to generate views from")
    
    try:
        # Download the original image from MinIO
        image_data = get_object(product.image_key)
        image = Image.open(BytesIO(image_data))
        
        # Parse angles
        angle_list = [float(a.strip()) for a in angles.split(",")]
        
        # Generate views using Zero123
        print(f"🎨 Generating on-demand views for product {product.sku_code} at angles: {angle_list}")
        views_dict, status = generate_multi_angle_side_views(
            image=image,
            angles=angle_list,
            use_zero123=True,
            num_inference_steps=50,
        )
        
        if not views_dict:
            raise HTTPException(
                status_code=500,
                detail=f"View generation failed: {status}"
            )
        
        # Upload generated views to MinIO
        side_views_keys = {}
        for view_name, view_image in views_dict.items():
            angle = view_name.split('_')[1]
            view_filename = f"{product.sku_code}_generated_{view_name}.jpg"
            view_buffer = BytesIO()
            view_image.save(view_buffer, format='JPEG', quality=95)
            view_buffer.seek(0)
            
            # Save in session folder: images/{session}/views/{angle}deg/
            view_key = f"images/{product.session_id}/views/{angle}deg/{view_filename}"
            upload_image(view_buffer.read(), view_key)
            side_views_keys[view_name] = view_key
        
        # Update product with generated view keys
        product.side_views_keys = json.dumps(side_views_keys)
        product.view_generation_status = status
        db.commit()
        
        # Generate presigned URLs for immediate return
        side_views_urls = {
            angle_key: presign_get(view_key, 3600)
            for angle_key, view_key in side_views_keys.items()
        }
        
        return {
            "success": True,
            "message": f"Generated {len(side_views_urls)} views",
            "views": side_views_urls,
            "status": status
        }
        
    except Exception as e:
        print(f"❌ Error generating views: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate views: {str(e)}"
        )
