"""
PDF ingestion module for VistaView
Extracts images, metadata, and creates product records
"""
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from io import BytesIO
from typing import Dict, List, Optional, Tuple

import fitz  # PyMuPDF
import numpy as np
import cv2
from PIL import Image
from sqlalchemy.orm import Session

from .models import Product
from .minio_client import upload_image

# Configuration
MIN_IMAGE_SIZE = 200  # Skip small logos/icons
TILE_SIZE = 420  # Size of each tile in collage
TILES_PER_ROW = 3
ENHANCEMENT_THRESHOLD = 600  # Enhance images smaller than 600px in either dimension
TARGET_ENHANCEMENT_SIZE = 1920  # Target size for enhanced images
SIMPLE_BACKGROUND_THRESHOLD = 0.85  # Threshold for detecting simple backgrounds (85% similarity)

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


def has_simple_background(img: Image.Image) -> bool:
    """
    Detect if an image has a simple/uniform background (white or solid color)
    
    Args:
        img: PIL Image object
    
    Returns:
        True if background is simple, False otherwise
    """
    # Convert to numpy array
    img_array = np.array(img)
    
    # Get image dimensions
    height, width = img_array.shape[:2]
    
    # Sample edges (10% border around image)
    border_size = int(min(height, width) * 0.1)
    
    # Extract edge pixels
    top_edge = img_array[:border_size, :]
    bottom_edge = img_array[-border_size:, :]
    left_edge = img_array[:, :border_size]
    right_edge = img_array[:, -border_size:]
    
    # Combine all edge pixels
    edges = np.vstack([
        top_edge.reshape(-1, 3 if len(img_array.shape) == 3 else 1),
        bottom_edge.reshape(-1, 3 if len(img_array.shape) == 3 else 1),
        left_edge.reshape(-1, 3 if len(img_array.shape) == 3 else 1),
        right_edge.reshape(-1, 3 if len(img_array.shape) == 3 else 1)
    ])
    
    # Calculate standard deviation of edge pixels
    std_dev = np.std(edges, axis=0).mean()
    
    # If standard deviation is low, background is uniform
    is_simple = std_dev < 30  # Threshold for uniform color
    
    if is_simple:
        print(f"      ✅ Simple background detected (std: {std_dev:.2f})")
    else:
        print(f"      ⚠️  Complex background detected (std: {std_dev:.2f}), skipping side views")
    
    return is_simple


def generate_side_views(img: Image.Image, sku: str) -> Tuple[Optional[Image.Image], Optional[Image.Image]]:
    """
    Generate left and right side views of a product image using image transformation
    
    This function creates perspective-transformed versions to simulate side views.
    For production, integrate with AI image generation APIs like:
    - Stability AI (Stable Diffusion)
    - Replicate API
    - OpenAI DALL-E
    
    Args:
        img: PIL Image object
        sku: Product SKU code
    
    Returns:
        Tuple of (left_view, right_view) PIL Images or (None, None) if generation fails
    """
    try:
        # Convert PIL to OpenCV format
        img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        height, width = img_cv.shape[:2]
        
        # Generate left side view (perspective transform)
        # Simulate viewing from left side
        pts_left_src = np.float32([[0, 0], [width, 0], [width, height], [0, height]])
        pts_left_dst = np.float32([
            [width * 0.15, height * 0.1],  # Top-left moved right and down
            [width * 0.85, 0],              # Top-right
            [width * 0.85, height],         # Bottom-right
            [width * 0.15, height * 0.9]    # Bottom-left moved right and up
        ])
        
        matrix_left = cv2.getPerspectiveTransform(pts_left_src, pts_left_dst)
        left_view_cv = cv2.warpPerspective(img_cv, matrix_left, (width, height))
        left_view = Image.fromarray(cv2.cvtColor(left_view_cv, cv2.COLOR_BGR2RGB))
        
        # Generate right side view (opposite perspective)
        pts_right_dst = np.float32([
            [width * 0.15, 0],              # Top-left
            [width * 0.85, height * 0.1],   # Top-right moved left and down
            [width * 0.85, height * 0.9],   # Bottom-right moved left and up
            [width * 0.15, height]          # Bottom-left
        ])
        
        matrix_right = cv2.getPerspectiveTransform(pts_left_src, pts_right_dst)
        right_view_cv = cv2.warpPerspective(img_cv, matrix_right, (width, height))
        right_view = Image.fromarray(cv2.cvtColor(right_view_cv, cv2.COLOR_BGR2RGB))
        
        print(f"      🔄 Generated left and right side views for {sku}")
        return left_view, right_view
        
    except Exception as e:
        print(f"      ⚠️  Error generating side views: {e}")
        return None, None


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
            
            # Check if image needs enhancement and upload enhanced version
            enhanced_image_key = None
            enhanced_img = enhance_image(main_img)
            if enhanced_img:
                enhanced_filename = f"{sku}_{page_num + 1}_enhanced.jpg"
                enhanced_buffer = BytesIO()
                enhanced_img.save(enhanced_buffer, format='JPEG', quality=95)
                enhanced_buffer.seek(0)
                enhanced_image_key = f"images/{session_id}/enhanced/{enhanced_filename}"
                upload_image(enhanced_buffer.read(), enhanced_image_key)
            
            # Generate side views if background is simple
            left_view_key = None
            right_view_key = None
            if has_simple_background(main_img):
                left_view, right_view = generate_side_views(main_img, sku)
                
                if left_view:
                    left_filename = f"{sku}_{page_num + 1}_left.jpg"
                    left_buffer = BytesIO()
                    left_view.save(left_buffer, format='JPEG', quality=95)
                    left_buffer.seek(0)
                    left_view_key = f"images/{session_id}/sideviews/{left_filename}"
                    upload_image(left_buffer.read(), left_view_key)
                
                if right_view:
                    right_filename = f"{sku}_{page_num + 1}_right.jpg"
                    right_buffer = BytesIO()
                    right_view.save(right_buffer, format='JPEG', quality=95)
                    right_buffer.seek(0)
                    right_view_key = f"images/{session_id}/sideviews/{right_filename}"
                    upload_image(right_buffer.read(), right_view_key)
            
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
                enhanced_image_key=enhanced_image_key,
                left_view_key=left_view_key,
                right_view_key=right_view_key,
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
