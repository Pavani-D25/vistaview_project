from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from PIL import Image
from io import BytesIO
import json

from app.db import get_db
from app.models import Product
from app.minio_client import get_object, upload_image, presign_get
from app.zero123_views import generate_multi_angle_side_views

router = APIRouter()


@router.post("/{product_id}/generate-views")
async def generate_side_views_endpoint(
    product_id: str,
    angles: str = Query("15,30,45", description="Comma-separated angles"),
    db: Session = Depends(get_db),
):
    """Generate Zero123/SD-based multi-angle side views for a product."""

    # 1️⃣ Fetch product
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if not product.image_key:
        raise HTTPException(
            status_code=400,
            detail="Product has no image to generate views from",
        )

    try:
        # 2️⃣ Download original image from MinIO
        image_data = get_object(product.image_key)
        image = Image.open(BytesIO(image_data)).convert("RGB")

        # 3️⃣ Parse angles
        try:
            angle_list = [float(a.strip()) for a in angles.split(",") if a.strip()]
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid angles format; expected comma-separated numbers",
            )

        print(f"🎨 Generating Zero123 views for SKU {product.sku_code}")
        print(f"   Angles: {angle_list}")

        # 4️⃣ Generate views via Zero123/SD fallback
        views_dict, status = generate_multi_angle_side_views(
            image=image,
            angles=angle_list,
            use_zero123=True,
            num_inference_steps=75,
        )

        if not views_dict:
            raise HTTPException(
                status_code=500,
                detail=f"View generation failed ({status})",
            )

        # 5️⃣ Upload generated views to MinIO, merging with any existing ones
        # Load existing keys if present so we can add new angles incrementally
        side_views_keys = {}
        if product.side_views_keys:
            try:
                side_views_keys = json.loads(product.side_views_keys)
            except json.JSONDecodeError:
                side_views_keys = {}
        for view_name, view_image in views_dict.items():
            filename = f"{product.sku_code}_{view_name}.png"

            buffer = BytesIO()
            view_image.save(buffer, format="PNG", quality=95)
            buffer.seek(0)

            view_key = f"images/{product.session_id}/views/{view_name}/{filename}"

            upload_image(
                buffer.read(),
                view_key,
                content_type="image/png",
            )

            side_views_keys[view_name] = view_key

        # 6️⃣ Update product record
        product.side_views_keys = json.dumps(side_views_keys)
        product.view_generation_status = status
        db.commit()

        # 7️⃣ Return presigned URLs
        return {
            "success": True,
            "status": status,
            "views": {
                name: presign_get(key, 3600)
                for name, key in side_views_keys.items()
            },
        }

    except HTTPException:
        # Re-raise HTTPException without wrapping
        raise
    except Exception as e:
        print(f"❌ Error generating views: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate views: {str(e)}",
        )
