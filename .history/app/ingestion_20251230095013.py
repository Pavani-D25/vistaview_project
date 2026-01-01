"""
PDF ingestion module for VistaView
Extracts images, metadata, and creates product records with multi-angle view generation using Zero123
"""
import os
import re
import uuid
import json
from datetime import datetime
from pathlib import Path
from io import BytesIO
from typing import Dict, List, Optional, Tuple

import fitz  # PyMuPDF
import numpy as np
import cv2
import torch
from PIL import Image
from sqlalchemy.orm import Session

from .models import Product
from .minio_client import upload_image
from .zero123_generator import generate_side_views, generate_multi_angle_side_views

# Configuration
MIN_IMAGE_SIZE = 200  # Skip small logos/icons
TILE_SIZE = 420  # Size of each tile in collage
TILES_PER_ROW = 3

# Regex patterns
SKU_RE = re.compile(r'\b([A-Z]{1,6}-?\d{1,6}[A-Z0-9]*)\b')
DIMS_RE = re.compile(r'(\d{2,4})\s*[x×]\s*(\d{2,4})\s*[x×]\s*(\d{2,4})', re.IGNORECASE)
CN_RE = re.compile(r'[\u4e00-\u9fff]{2,30}')


def best_cn_name(text: str) -> Optional[str]:
    """Extract the best Chinese name from text"""
    matches = CN_RE.findall(text)
    if not matches:
        return None
    
    # Look for common furniture keywords
    furniture_keywords = ['沙发', '床', '椅', '柜', '茶几', '凳', '桌', '架', '几', '圆', '方', '长', '边']
    for match in matches:
        for keyword in furniture_keywords:
            if keyword in match:
                return match
    
    # Return first match if no keyword found
    return matches[0] if matches else None


def estimate_depth_map(image: Image.Image) -> Optional[np.ndarray]:
    """
    Estimate depth map from image using MiDaS-like approach
    Simplified version - can be upgraded to full MiDaS model
    
    Returns: Normalized depth map or None if fails
    """
    try:
        # Convert to grayscale and numpy
        img_gray = np.array(image.convert('L'))
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(img_gray, (5, 5), 0)
        
        # Estimate depth using edge detection and intensity
        edges = cv2.Canny(blurred, 50, 150)
        
        # Create pseudo-depth map (inverted intensity as depth proxy)
        depth_map = 255 - blurred
        depth_map = depth_map.astype(np.float32) / 255.0
        
        # Combine with edges for better structure awareness
        edge_weight = edges.astype(np.float32) / 255.0 * 0.3
        depth_map = depth_map * (1 + edge_weight)
        
        # Normalize
        depth_map = np.clip(depth_map, 0, 1)
        
        return depth_map
    except Exception as e:
        print(f"      ⚠️  Depth estimation failed: {e}")
        return None


def check_if_suitable_for_view_generation(image: Image.Image, depth_map: np.ndarray) -> Tuple[bool, str]:
    """
    Determine if image is suitable for view generation
    
    Returns: (is_suitable, reason)
    """
    try:
        # Convert image to numpy
        img_array = np.array(image)
        
        # Check 1: Image has sufficient depth variance
        depth_std = np.std(depth_map)
        if depth_std < 0.1:
            return False, "insufficient_depth_variance"
        
        # Check 2: Check background uniformity (simple background is better)
        h, w = img_array.shape[:2]
        border_size = min(h, w) // 10
        edges = np.concatenate([
            img_array[:border_size, :].reshape(-1, 3),
            img_array[-border_size:, :].reshape(-1, 3),
            img_array[:, :border_size].reshape(-1, 3),
            img_array[:, -border_size:].reshape(-1, 3)
        ])
        
        edge_std = np.std(edges)
        if edge_std > 50:  # Complex background
            return False, "complex_background"
        
        # Check 3: Image has reasonable dimensions
        if w < 300 or h < 300:
            return False, "image_too_small"
        
        return True, "suitable"
        
    except Exception as e:
        print(f"      ⚠️  Suitability check failed: {e}")
        return False, "check_failed"


def generate_view_from_depth(image: Image.Image, depth_map: np.ndarray, direction: str) -> Optional[Image.Image]:
    """
    Generate left or right view using depth map and 3D warping
    
    Args:
        image: Original PIL Image
        depth_map: Normalized depth map
        direction: 'left' or 'right'
    
    Returns: Generated view as PIL Image or None
    """
    try:
        img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        h, w = img_cv.shape[:2]
        
        # Create mesh grid
        x, y = np.meshgrid(np.arange(w), np.arange(h))
        
        # Calculate horizontal displacement based on depth
        # More depth = more displacement
        max_displacement = w * 0.15  # 15% of width
        displacement = depth_map * max_displacement
        
        if direction == 'left':
            displacement = -displacement  # Shift left
        
        # Create new coordinates
        new_x = (x + displacement).astype(np.float32)
        new_y = y.astype(np.float32)
        
        # Remap image with depth-based displacement
        warped = cv2.remap(img_cv, new_x, new_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        
        # Apply slight perspective transform for more realistic view
        pts_src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
        
        if direction == 'right':
            # Right view: compress left side, expand right side
            pts_dst = np.float32([
                [w * 0.1, h * 0.05],
                [w * 0.95, 0],
                [w * 0.95, h],
                [w * 0.1, h * 0.95]
            ])
        else:
            # Left view: expand left side, compress right side
            pts_dst = np.float32([
                [w * 0.05, 0],
                [w * 0.9, h * 0.05],
                [w * 0.9, h * 0.95],
                [w * 0.05, h]
            ])
        
        matrix = cv2.getPerspectiveTransform(pts_src, pts_dst)
        final_view = cv2.warpPerspective(warped, matrix, (w, h))
        
        # Convert back to PIL
        result = Image.fromarray(cv2.cvtColor(final_view, cv2.COLOR_BGR2RGB))
        
        print(f"      ✅ Generated {direction} view successfully")
        return result
        
    except Exception as e:
        print(f"      ⚠️  View generation failed for {direction}: {e}")
        return None


def generate_left_right_views(image: Image.Image, sku: str) -> Tuple[Optional[Image.Image], Optional[Image.Image], str]:
    """
    Main function to generate left and right views of product image using Zero123
    
    Returns: (left_view, right_view, status)
    status can be: 'success', 'partial_success', 'model_load_failed', 'generation_failed', etc.
    """
    try:
        # Check if Zero123 is enabled via environment variable
        zero123_enabled = os.getenv('ZERO123_ENABLED', 'true').lower() == 'true'
        
        if not zero123_enabled:
            print(f"      ⚠️  Zero123 disabled via ZERO123_ENABLED env var")
            return None, None, 'disabled'
        
        print(f"      🔄 Generating Zero123 views for {sku}...")
        
        # Use Zero123 to generate views
        # Adjust parameters: angle (15-45°), num_inference_steps (30-75 for quality)
        left_view, right_view, status = generate_side_views(
            image=image,
            angle=30.0,  # 30 degree rotation
            use_zero123=True,
            num_inference_steps=50,  # Balance between quality and speed
        )
        
        return left_view, right_view, status
            
    except Exception as e:
        print(f"      ❌ View generation error: {e}")
        return None, None, f'error_{str(e)[:50]}'


def generate_multi_angle_views(image: Image.Image, sku: str, angles: List[float] = [15.0, 30.0, 45.0]) -> Tuple[Dict[str, Image.Image], str]:
    """
    Generate multiple side views at different angles using Zero123
    
    Args:
        image: Input PIL Image
        sku: Product SKU for logging
        angles: List of angles to generate (degrees)
    
    Returns: 
        (views_dict, status)
        views_dict: {"left_15": Image, "right_15": Image, ...}
        status: 'success', 'partial_success', etc.
    """
    try:
        # Check if Zero123 is enabled via environment variable
        zero123_enabled = os.getenv('ZERO123_ENABLED', 'true').lower() == 'true'
        
        if not zero123_enabled:
            print(f"      ⚠️  Zero123 disabled via ZERO123_ENABLED env var")
            return {}, 'disabled'
        
        print(f"      🔄 Generating multi-angle Zero123 views for {sku} at {angles}°...")
        
        # Use Zero123 to generate multiple angle views
        views_dict, status = generate_multi_angle_side_views(
            image=image,
            angles=angles,
            use_zero123=True,
            num_inference_steps=50,  # Balance between quality and speed
        )
        
        return views_dict, status
            
    except Exception as e:
        print(f"      ❌ Multi-angle view generation error: {e}")
        return {}, f'error_{str(e)[:50]}'


def extract_images_from_page(doc: fitz.Document, page_num: int) -> List[Dict]:
    """Extract images from a specific PDF page"""
    page = doc[page_num]
    image_list = page.get_images()
    page_images = []
    
    for img_index, img_info in enumerate(image_list):
        try:
            xref = img_info[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            
            # Load image
            img = Image.open(BytesIO(image_bytes))
            
            # Skip small images (logos, icons)
            if img.width < MIN_IMAGE_SIZE or img.height < MIN_IMAGE_SIZE:
                continue
            
            # Convert RGBA to RGB if needed
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            
            page_images.append({
                'pil': img,
                'bytes': image_bytes,
                'index': img_index
            })
        except Exception as e:
            print(f"      ⚠️  Error loading image {img_index} on page {page_num + 1}: {e}")
            continue
    
    return page_images


def parse_page_text(text: str) -> Dict:
    """Extract SKU, dimensions, and Chinese name from page text"""
    result = {
        'sku': None,
        'dims_l': None,
        'dims_w': None,
        'dims_h': None,
        'cn_name': None
    }
    
    # Extract SKU
    sku_match = SKU_RE.search(text)
    if sku_match:
        result['sku'] = sku_match.group(1)
    
    # Extract dimensions
    dims_match = DIMS_RE.search(text)
    if dims_match:
        result['dims_l'] = int(dims_match.group(1))
        result['dims_w'] = int(dims_match.group(2))
        result['dims_h'] = int(dims_match.group(3))
    
    # Extract Chinese name
    result['cn_name'] = best_cn_name(text)
    
    return result


def create_collage(images: List[Dict], max_images: int = 6) -> Optional[Image.Image]:
    """Create a collage from multiple images in a 3-column grid"""
    if not images:
        return None
    
    # Use up to max_images
    images = images[:max_images]
    num_images = len(images)
    
    # Calculate grid dimensions
    cols = TILES_PER_ROW
    rows = (num_images + cols - 1) // cols
    
    # Create collage canvas
    collage_width = TILE_SIZE * cols
    collage_height = TILE_SIZE * rows
    collage = Image.new('RGB', (collage_width, collage_height), 'white')
    
    # Place images
    for idx, img_data in enumerate(images):
        try:
            img = img_data['pil'].copy()
            
            # Resize to fit tile with padding
            img.thumbnail((TILE_SIZE - 20, TILE_SIZE - 20), Image.Resampling.LANCZOS)
            
            # Calculate position
            col = idx % cols
            row = idx // cols
            x = col * TILE_SIZE + (TILE_SIZE - img.width) // 2
            y = row * TILE_SIZE + (TILE_SIZE - img.height) // 2
            
            collage.paste(img, (x, y))
        except Exception as e:
            print(f"      ⚠️  Error adding image to collage: {e}")
            continue
    
    return collage


def ingest_pdf(pdf_bytes: bytes, db: Session, pdf_filename: str = "catalog.pdf") -> Dict:
    """
    Main PDF ingestion function - uploads images to MinIO
    
    Args:
        pdf_bytes: PDF file content as bytes
        db: Database session
        pdf_filename: Original name of the PDF file
    
    Returns:
        Dictionary with ingestion statistics
    """
    # Create unique session ID for this upload
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:8]
    
    print(f"\n📄 Processing PDF '{pdf_filename}' with {len(pdf_bytes)} bytes...")
    print(f"📁 Session folder: {session_id}")
    
    # Open PDF from bytes
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages_processed = len(doc)
    
    print(f"   📖 Loaded PDF with {pages_processed} pages...")
    
    products_created = 0
    images_extracted = 0
    collages_created = 0
    
    # Process each page
    for page_num in range(pages_processed):
        try:
            # Extract page text
            page = doc[page_num]
            text = page.get_text()
            
            # Parse metadata
            metadata = parse_page_text(text)
            sku = metadata['sku'] or f"P{page_num + 1:03d}"
            
            # Extract images
            page_images = extract_images_from_page(doc, page_num)
            
            if not page_images:
                print(f"   Page {page_num + 1}: {sku}")
                continue
            
            images_extracted += len(page_images)
            
            # Generate unique product ID
            product_id = str(uuid.uuid4())
            
            # Upload main image to MinIO
            main_img = page_images[0]['pil']
            img_filename = f"{sku}_{page_num + 1}_main.jpg"
            
            # Upload original to MinIO with session prefix
            img_buffer = BytesIO()
            main_img.save(img_buffer, format='JPEG', quality=95)
            img_buffer.seek(0)
            image_key = f"images/{session_id}/{img_filename}"
            upload_image(img_buffer.read(), image_key)
            
            # Generate multi-angle side views
            angles_to_generate = [15.0, 30.0, 45.0]
            views_dict, view_status = generate_multi_angle_views(main_img, sku, angles_to_generate)
            
            # Upload all generated views to subfolder structure
            side_views_keys = {}
            if views_dict:
                for view_name, view_image in views_dict.items():
                    # view_name is like "left_15", "right_30", etc.
                    view_filename = f"{sku}_{page_num + 1}_{view_name}.jpg"
                    view_buffer = BytesIO()
                    view_image.save(view_buffer, format='JPEG', quality=95)
                    view_buffer.seek(0)
                    
                    # Save in subfolder: images/{session}/views/{angle}/
                    angle = view_name.split('_')[1]  # Extract angle number
                    view_key = f"images/{session_id}/views/{angle}deg/{view_filename}"
                    upload_image(view_buffer.read(), view_key)
                    side_views_keys[view_name] = view_key
                    
                print(f"      ✅ Uploaded {len(side_views_keys)} angle views")
            
            # Also maintain legacy left/right views (30 degrees for backwards compatibility)
            left_view_key = side_views_keys.get('left_30')
            right_view_key = side_views_keys.get('right_30')
            
            # Log view generation status
            if view_status != 'success':
                not_possible_key = f"images/{session_id}/views/{sku}_{page_num + 1}_not_possible.txt"
                not_possible_content = f"View generation status: {view_status}".encode('utf-8')
                upload_image(not_possible_content, not_possible_key)
            
            # Create and upload collage to MinIO
            collage_key = None
            if len(page_images) > 1:
                collage = create_collage(page_images)
                if collage:
                    collage_filename = f"{sku}_{page_num + 1}_collage.jpg"
                    
                    # Upload to MinIO with session prefix
                    collage_buffer = BytesIO()
                    collage.save(collage_buffer, format='JPEG', quality=95)
                    collage_buffer.seek(0)
                    collage_key = f"collages/{session_id}/{collage_filename}"
                    upload_image(collage_buffer.read(), collage_key)
                    
                    collages_created += 1
            
            # Create product record
            product = Product(
                id=product_id,
                sku_code=sku,
                cn_name=metadata['cn_name'],
                category="Furniture",
                dims_l=metadata['dims_l'],
                dims_w=metadata['dims_w'],
                dims_h=metadata['dims_h'],
                description=f"Product from page {page_num + 1}",
                image_key=image_key,
                collage_key=collage_key,
                left_view_key=left_view_key,  # Legacy 30° left view
                right_view_key=right_view_key,  # Legacy 30° right view
                side_views_keys=json.dumps(side_views_keys) if side_views_keys else None,  # All angles
                view_generation_status=view_status,
                session_id=session_id,
                pdf_filename=pdf_filename,
            )
            
            db.add(product)
            products_created += 1
            
            # Print status
            status = f"   Page {page_num + 1}: {sku}"
            if metadata['cn_name']:
                status += f" ({metadata['cn_name']})"
            status += f" - {len(page_images)} images"
            print(status)
            
        except Exception as e:
            print(f"   ⚠️  Error processing page {page_num + 1}: {e}")
            continue
    
    # Commit all products
    db.commit()
    doc.close()
    
    print(f"\n✅ Ingestion complete: {products_created} products, {images_extracted} images, {collages_created} collages")
    print(f"☁️  Images uploaded to MinIO bucket: vistaview-catalog")
    
    return {
        'pages_processed': pages_processed,
        'products_created': products_created,
        'images_extracted': images_extracted,
        'collages_created': collages_created,
        'session_id': session_id
    }
