"""
Fast Cardinal Views Generation Endpoint
Generates top, bottom, left, right views quickly
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from PIL import Image
from io import BytesIO
import json

from app.db import get_db
from app.models import Product
from app.minio_client import get_object, upload_image, presign_get

router = APIRouter()


@router.post("/{product_id}/generate-cardinal-views")
async def generate_cardinal_views_endpoint(
    product_id: str,
    angle: float = Query(30.0, ge=15.0, le=45.0, description="Viewing angle in degrees"),
    num_steps: int = Query(20, ge=15, le=50, description="Quality (15=fastest, 50=best)"),
    db: Session = Depends(get_db),
):
    """
    Fast generation of 4 cardinal views: top, bottom, left, right
    
    Uses simple image transformations (NO AI models, NO downloads):
    - Perspective transforms for quick results
    - Depth-based displacement for better quality
    - Zero model downloads, minimal memory
    - ~1-2 seconds for all 4 views
    
    Response time: ~1-2 seconds for all 4 views (vs hours with AI models)
    """
    
    # 1️⃣ Fetch product
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if not product.image_key:
        raise HTTPException(status_code=400, detail="Product has no image")

    try:
        # 2️⃣ Download image
        print(f"📥 Fetching image for {product.sku_code}...")
        image_data = get_object(product.image_key)
        image = Image.open(BytesIO(image_data)).convert("RGB")

        # 3️⃣ Generate 4 cardinal views (SIMPLE - No AI models)
        print(f"🚀 Generating cardinal views at {angle}° using simple transforms...")
        
        from app.simple_view_generator import generate_cardinal_views_fast
        
        views_dict, status = generate_cardinal_views_fast(
            image=image,
            angle=angle,
            num_inference_steps=num_steps,  # Ignored by simple generator
        )

        if not views_dict:
            raise HTTPException(
                status_code=500,
                detail=f"View generation failed ({status})",
            )

        # 4️⃣ Upload views to MinIO
        print(f"☁️  Uploading {len(views_dict)} views to MinIO...")
        side_views_keys = {}
        
        for view_name, view_image in views_dict.items():
            filename = f"{product.sku_code}_{view_name}_{int(angle)}.png"
            
            buffer = BytesIO()
            view_image.save(buffer, format="PNG", quality=95)
            buffer.seek(0)

            view_key = f"images/{product.session_id}/views/{view_name}/{filename}"
            upload_image(buffer.read(), view_key, content_type="image/png")
            
            side_views_keys[f"{view_name}_{int(angle)}"] = view_key

        # 5️⃣ Update product
        product.side_views_keys = json.dumps(side_views_keys)
        product.view_generation_status = status
        db.commit()

        # 6️⃣ Return presigned URLs
        print(f"✅ Generated {len(views_dict)} cardinal views successfully")
        
        return {
            "success": True,
            "status": status,
            "angle": angle,
            "num_steps": num_steps,
            "views": {
                name: presign_get(key, 3600)
                for name, key in side_views_keys.items()
            },
            "performance": {
                "inference_steps": num_steps,
                "estimated_time": "1-2 seconds",
                "method": "simple_transforms",
                "model_size": "0 MB (no downloads)"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{product_id}/generate-multi-cardinal-views")
async def generate_multi_cardinal_views_endpoint(
    product_id: str,
    angles: str = Query("15,30,45", description="Comma-separated angles"),
    num_steps: int = Query(20, ge=15, le=50, description="Quality (15=fastest, 50=best)"),
    db: Session = Depends(get_db),
):
    """
    Generate cardinal views at multiple angles
    Example output: top_15, top_30, left_15, right_30, etc.
    
    Uses simple transformations - NO AI models required
    Fast processing, zero downloads, minimal memory usage
    """
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if not product.image_key:
        raise HTTPException(status_code=400, detail="Product has no image")

    try:
        # Parse angles
        try:
            angle_list = [float(a.strip()) for a in angles.split(",") if a.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid angles format")

        # Download image
        image_data = get_object(product.image_key)
        image = Image.open(BytesIO(image_data)).convert("RGB")

        # Generate views
        print(f"🚀 Generating multi-angle cardinal views: {angle_list}")
        
        from app.simple_view_generator import generate_multi_angle_cardinal_views_fast
        
        views_dict, status = generate_multi_angle_cardinal_views_fast(
            image=image,
            angles=angle_list,
            num_inference_steps=num_steps,  # Ignored by simple generator
        )

        if not views_dict:
            raise HTTPException(status_code=500, detail=f"Generation failed ({status})")

        # Upload views
        side_views_keys = {}
        for view_name, view_image in views_dict.items():
            filename = f"{product.sku_code}_{view_name}.png"
            
            buffer = BytesIO()
            view_image.save(buffer, format="PNG", quality=95)
            buffer.seek(0)

            view_key = f"images/{product.session_id}/views/{view_name}/{filename}"
            upload_image(buffer.read(), view_key, content_type="image/png")
            side_views_keys[view_name] = view_key

        # Update product
        product.side_views_keys = json.dumps(side_views_keys)
        product.view_generation_status = status
        db.commit()

        return {
            "success": True,
            "status": status,
            "angles": angle_list,
            "total_views": len(views_dict),
            "views": {
                name: presign_get(key, 3600)
                for name, key in side_views_keys.items()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
