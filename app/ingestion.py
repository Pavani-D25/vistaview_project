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
from typing import Dict, List, Optional

import fitz  # PyMuPDF
from PIL import Image
from sqlalchemy.orm import Session

from .models import Product
from .minio_client import upload_image

# Configuration
MIN_IMAGE_SIZE = 200  # Skip small logos/icons
TILE_SIZE = 420  # Size of each tile in collage
TILES_PER_ROW = 3

# Directory setup
BACKEND_DIR = Path(__file__).parent.parent / "backend"
DATA_DIR = BACKEND_DIR / "data"
IMAGES_BASE_DIR = DATA_DIR / "images"
COLLAGES_BASE_DIR = DATA_DIR / "collages"

# Ensure base directories exist
IMAGES_BASE_DIR.mkdir(parents=True, exist_ok=True)
COLLAGES_BASE_DIR.mkdir(parents=True, exist_ok=True)

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


def ingest_pdf(pdf_bytes: bytes, db: Session, use_minio: bool = False) -> Dict:
    """
    Main PDF ingestion function
    
    Args:
        pdf_bytes: PDF file content as bytes
        db: Database session
        use_minio: Whether to upload images to MinIO (True) or store locally (False)
    
    Returns:
        Dictionary with ingestion statistics
    """
    # Create unique session ID for this upload
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:8]
    
    # Create session directories
    session_images_dir = IMAGES_BASE_DIR / session_id
    session_collages_dir = COLLAGES_BASE_DIR / session_id
    session_images_dir.mkdir(parents=True, exist_ok=True)
    session_collages_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📄 Processing PDF with {len(pdf_bytes)} bytes...")
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
            
            # Save/upload main image
            main_img = page_images[0]['pil']
            img_filename = f"{sku}_{page_num + 1}_main.jpg"
            
            if use_minio:
                # Upload to MinIO
                img_buffer = BytesIO()
                main_img.save(img_buffer, format='JPEG', quality=95)
                img_buffer.seek(0)
                image_key = f"images/{img_filename}"
                upload_image(img_buffer.read(), image_key)
            else:
                # Save locally
                image_key = f"images/{session_id}/{img_filename}"
                image_path = session_images_dir / img_filename
                main_img.save(image_path, format='JPEG', quality=95)
            
            # Create and save/upload collage
            collage_key = None
            if len(page_images) > 1:
                collage = create_collage(page_images)
                if collage:
                    collage_filename = f"{sku}_{page_num + 1}_collage.jpg"
                    
                    if use_minio:
                        # Upload to MinIO
                        collage_buffer = BytesIO()
                        collage.save(collage_buffer, format='JPEG', quality=95)
                        collage_buffer.seek(0)
                        collage_key = f"collages/{collage_filename}"
                        upload_image(collage_buffer.read(), collage_key)
                    else:
                        # Save locally
                        collage_key = f"collages/{session_id}/{collage_filename}"
                        collage_path = session_collages_dir / collage_filename
                        collage.save(collage_path, format='JPEG', quality=95)
                    
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
    if not use_minio:
        print(f"📂 Images stored in: {session_images_dir}")
    
    return {
        'pages_processed': pages_processed,
        'products_created': products_created,
        'images_extracted': images_extracted,
        'collages_created': collages_created,
        'session_id': session_id
    }
