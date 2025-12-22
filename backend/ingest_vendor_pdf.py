# #!/usr/bin/env python3
# """
# VistaView Vendor Catalog Ingestion Script
# Extracts images, dimensions, and metadata from PDF catalogs
# """
# import re
# import uuid
# import sqlite3
# from pathlib import Path
# from PIL import Image
# import fitz  # PyMuPDF

# # Directory setup
# BACKEND_DIR = Path(__file__).parent
# INPUT_DIR = BACKEND_DIR / "input"
# DATA_DIR = BACKEND_DIR / "data"
# IMG_DIR = DATA_DIR / "images"
# COL_DIR = DATA_DIR / "collages"
# DB_PATH = DATA_DIR / "vistaview.sqlite"
# PDF_PATH = INPUT_DIR / "catalog.pdf"

# # Regex patterns for parsing
# SKU_RE = re.compile(r"[A-Z]{1,6}-?\d{1,6}[A-Z0-9]*")
# DIMS_RE = re.compile(r"(\d{3,4})\s*[xX×*]\s*(\d{3,4})\s*[xX×*]\s*(\d{3,4})")
# CN_RE = re.compile(r"[\u4e00-\u9fff]{2,30}")


# def init_db():
#     """Initialize SQLite database with schema"""
#     conn = sqlite3.connect(DB_PATH)
#     cur = conn.cursor()
#     cur.execute("""
#     CREATE TABLE IF NOT EXISTS skus(
#         id TEXT PRIMARY KEY,
#         sku_code TEXT,
#         cn_name TEXT,
#         category TEXT,
#         dims_l INTEGER,
#         dims_w INTEGER,
#         dims_h INTEGER,
#         description TEXT,
#         image_path TEXT,
#         collage_path TEXT,
#         created_at TEXT DEFAULT CURRENT_TIMESTAMP
#     )
#     """)
#     conn.commit()
#     print("✅ Database initialized")
#     return conn


# def make_collage(img_paths, out_path):
#     """Create a 3x2 collage from product images"""
#     tiles = []
#     for p in img_paths[:6]:
#         try:
#             im = Image.open(p).convert("RGB")
#             im.thumbnail((420, 420))
#             canvas = Image.new("RGB", (420, 420), (255, 255, 255))
#             canvas.paste(im, ((420 - im.width)//2, (420 - im.height)//2))
#             tiles.append(canvas)
#         except Exception as e:
#             print(f"⚠️  Warning: Could not process image {p.name}: {e}")
#             continue
    
#     if not tiles:
#         return None
    
#     cols = 3
#     rows = (len(tiles) + cols - 1) // cols
#     collage = Image.new("RGB", (cols * 420, rows * 420), (255, 255, 255))
    
#     for i, tile in enumerate(tiles):
#         r, c = divmod(i, cols)
#         collage.paste(tile, (c * 420, r * 420))
    
#     collage.save(out_path, "JPEG", quality=90)
#     print(f"   ✓ Collage created: {out_path.name}")
#     return out_path


# def best_cn_name(text):
#     """Extract best Chinese product name from text"""
#     hits = CN_RE.findall(text or "")
#     if not hits:
#         return None
    
#     # Prefer common furniture terms
#     prefs = ["沙发", "床", "椅", "柜", "茶几", "凳", "桌", "架"]
#     for w in hits:
#         for p in prefs:
#             if p in w:
#                 return w
#     return hits[0]


# def extract_images_from_pdf(doc):
#     """Extract all images from PDF pages"""
#     images_by_page = {}
    
#     print(f"\n📄 Processing {len(doc)} pages...")
#     for pno in range(len(doc)):
#         page = doc[pno]
#         img_list = page.get_images(full=True)
        
#         for img in img_list:
#             xref = img[0]
#             try:
#                 pix = fitz.Pixmap(doc, xref)
                
#                 # Skip very small images (likely logos/icons)
#                 if pix.width < 200 or pix.height < 200:
#                     continue
                
#                 if pix.alpha:
#                     pix = fitz.Pixmap(fitz.csRGB, pix)
                
#                 out = IMG_DIR / f"p{pno+1:03d}_{xref}.jpg"
#                 out.write_bytes(pix.tobytes("jpeg"))
#                 images_by_page.setdefault(pno+1, []).append(out)
                
#             except Exception as e:
#                 print(f"⚠️  Warning: Could not extract image from page {pno+1}: {e}")
#                 continue
        
#         if pno + 1 in images_by_page:
#             print(f"   Page {pno+1}: {len(images_by_page[pno+1])} images extracted")
    
#     return images_by_page


# def parse_page_text(text):
#     """Parse SKU, dimensions, and Chinese name from page text"""
#     # Extract SKU
#     sku_match = SKU_RE.search(text)
#     sku = sku_match.group(0) if sku_match else None
    
#     # Extract dimensions (L x W x H in mm)
#     dims_match = DIMS_RE.search(text.replace("×", "*"))
#     l = w = h = None
#     if dims_match:
#         l, w, h = map(int, dims_match.groups())
    
#     # Extract Chinese name
#     cn_name = best_cn_name(text)
    
#     return sku, l, w, h, cn_name


# def create_product_records(doc, images_by_page, conn):
#     """Create product records in database"""
#     cur = conn.cursor()
#     count = 0
    
#     print("\n🔄 Creating product records...")
#     for pno in range(1, len(doc) + 1):
#         text = doc[pno-1].get_text("text") or ""
        
#         # Parse metadata
#         sku, l, w, h, cn_name = parse_page_text(text)
        
#         # Get images for this page
#         imgs = images_by_page.get(pno, [])
#         main_img = imgs[0] if imgs else None
        
#         # Create collage if images exist
#         collage_path = None
#         if imgs:
#             sku_prefix = sku or f"ITEM_{pno:03d}"
#             out_col = COL_DIR / f"{sku_prefix}_collage.jpg"
#             if make_collage(imgs, out_col):
#                 collage_path = f"/collages/{out_col.name}"
        
#         # Create paths
#         image_path = f"/images/{main_img.name}" if main_img else None
        
#         # Generate description
#         dims_str = f"{l}×{w}×{h}" if all([l, w, h]) else "---"
#         description = f"{sku or 'ITEM'} {cn_name or ''} | Dimensions(mm): {dims_str}"
        
#         # Insert into database
#         cur.execute("""
#         INSERT INTO skus
#         (id, sku_code, cn_name, category, dims_l, dims_w, dims_h, 
#          description, image_path, collage_path)
#         VALUES (?,?,?,?,?,?,?,?,?,?)
#         """, (
#             str(uuid.uuid4()),
#             sku,
#             cn_name,
#             "Furniture",
#             l, w, h,
#             description,
#             image_path,
#             collage_path
#         ))
        
#         count += 1
#         status = f"Page {pno}: {sku or f'ITEM_{pno:03d}'}"
#         if cn_name:
#             status += f" ({cn_name})"
#         if imgs:
#             status += f" - {len(imgs)} images"
#         print(f"   ✓ {status}")
    
#     conn.commit()
#     return count


# def sync_to_frontend():
#     """Create symlinks for frontend to access images"""
#     frontend_public = BACKEND_DIR.parent / "frontend" / "public"
    
#     print("\n🔗 Syncing images to frontend...")
    
#     # Create public directories if they don't exist
#     (frontend_public / "images").mkdir(parents=True, exist_ok=True)
#     (frontend_public / "collages").mkdir(parents=True, exist_ok=True)
    
#     # Copy images
#     img_count = 0
#     for img in IMG_DIR.glob("*.jpg"):
#         dest = frontend_public / "images" / img.name
#         dest.write_bytes(img.read_bytes())
#         img_count += 1
    
#     col_count = 0
#     for col in COL_DIR.glob("*.jpg"):
#         dest = frontend_public / "collages" / col.name
#         dest.write_bytes(col.read_bytes())
#         col_count += 1
    
#     print(f"   ✓ Copied {img_count} images and {col_count} collages")


# def main():
#     """Main ingestion pipeline"""
#     print("=" * 60)
#     print("🏠 VistaView Vendor Catalog Ingestion")
#     print("=" * 60)
    
#     # Validate PDF exists
#     if not PDF_PATH.exists():
#         print(f"\n❌ Error: PDF not found at {PDF_PATH}")
#         print(f"   Please place your catalog PDF at: {PDF_PATH}")
#         return 1
    
#     print(f"\n📂 Input PDF: {PDF_PATH}")
#     print(f"💾 Database: {DB_PATH}")
    
#     # Create directories
#     print("\n📁 Creating directories...")
#     IMG_DIR.mkdir(parents=True, exist_ok=True)
#     COL_DIR.mkdir(parents=True, exist_ok=True)
    
#     # Clear old database
#     if DB_PATH.exists():
#         DB_PATH.unlink()
#         print("   ✓ Cleared old database")
    
#     # Initialize database
#     conn = init_db()
    
#     # Open PDF
#     print(f"\n📖 Opening PDF...")
#     doc = fitz.open(str(PDF_PATH))
#     print(f"   ✓ Found {len(doc)} pages")
    
#     # Extract images
#     images_by_page = extract_images_from_pdf(doc)
#     total_images = sum(len(imgs) for imgs in images_by_page.values())
#     print(f"\n   ✓ Total images extracted: {total_images}")
    
#     # Create product records
#     count = create_product_records(doc, images_by_page, conn)
    
#     # Close database and PDF
#     conn.close()
#     doc.close()
    
#     # Sync to frontend
#     sync_to_frontend()
    
#     # Summary
#     print("\n" + "=" * 60)
#     print("✅ Ingestion Complete!")
#     print("=" * 60)
#     print(f"Products created: {count}")
#     print(f"Images extracted: {total_images}")
#     print(f"Collages generated: {len(list(COL_DIR.glob('*.jpg')))}")
#     print(f"\n🌐 Start frontend: cd ../frontend && npm run dev")
#     print(f"🔍 View at: http://localhost:3000")
#     print("=" * 60)
    
#     return 0


# if __name__ == "__main__":
#     try:
#         exit(main())
#     except Exception as e:
#         print(f"\n❌ Error: {e}")
#         import traceback
#         traceback.print_exc()
#         exit(1)



import os
import sys
import re
import uuid
from pathlib import Path
from io import BytesIO

import fitz  # PyMuPDF
from PIL import Image
from sqlalchemy.orm import Session

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal, engine
from app.models import Base, Product
from app.minio_client import upload_image, ensure_bucket

# Configuration
MIN_IMAGE_SIZE = 200  # Skip small logos/icons
COLLAGE_SIZE = (1200, 1800)  # 2 columns x 3 rows


def init_db():
    """Create database tables"""
    Base.metadata.create_all(bind=engine)
    ensure_bucket()
    print("✅ Database and storage initialized")


def extract_images_from_pdf(doc):
    """Extract images from PDF pages"""
    images_by_page = {}
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        image_list = page.get_images()
        page_images = []
        
        for img_index, img_info in enumerate(image_list):
            xref = img_info[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            
            # Load image
            try:
                img = Image.open(BytesIO(image_bytes))
                
                # Skip small images (logos, icons)
                if img.width < MIN_IMAGE_SIZE or img.height < MIN_IMAGE_SIZE:
                    continue
                
                page_images.append({
                    'pil': img,
                    'bytes': image_bytes,
                    'index': img_index
                })
            except Exception as e:
                print(f"⚠️  Error loading image on page {page_num}: {e}")
                continue
        
        if page_images:
            images_by_page[page_num] = page_images
    
    print(f"✅ Extracted images from {len(images_by_page)} pages")
    return images_by_page


def parse_page_text(text):
    """Extract SKU, dimensions, and Chinese name from page text"""
    result = {
        'sku': None,
        'dims': {'l': None, 'w': None, 'h': None},
        'cn_name': None
    }
    
    # Extract SKU (e.g., A95, SKU-123, etc.)
    sku_match = re.search(r'\b([A-Z]{1,6}-?\d{1,6}[A-Z0-9]*)\b', text)
    if sku_match:
        result['sku'] = sku_match.group(1)
    
    # Extract dimensions (e.g., 1020 x 1020 x 300 or 1020×1020×300)
    dims_match = re.search(r'(\d{2,4})\s*[x×]\s*(\d{2,4})\s*[x×]\s*(\d{2,4})', text, re.IGNORECASE)
    if dims_match:
        result['dims']['l'] = int(dims_match.group(1))
        result['dims']['w'] = int(dims_match.group(2))
        result['dims']['h'] = int(dims_match.group(3))
    
    # Extract Chinese name (look for common furniture terms)
    cn_keywords = ['沙发', '床', '椅', '柜', '茶几', '凳', '桌', '架']
    for keyword in cn_keywords:
        if keyword in text:
            # Get surrounding context
            idx = text.find(keyword)
            start = max(0, idx - 10)
            end = min(len(text), idx + 20)
            result['cn_name'] = text[start:end].strip()
            break
    
    return result


def make_collage(images, cols=2, rows=3):
    """Create a collage from multiple images"""
    if not images:
        return None
    
    # Use up to 6 images (2x3 grid)
    images = images[:cols * rows]
    
    # Calculate cell size
    cell_width = COLLAGE_SIZE[0] // cols
    cell_height = COLLAGE_SIZE[1] // rows
    
    # Create blank collage
    collage = Image.new('RGB', COLLAGE_SIZE, 'white')
    
    # Place images
    for idx, img_data in enumerate(images):
        img = img_data['pil'].copy()
        
        # Resize to fit cell
        img.thumbnail((cell_width - 20, cell_height - 20), Image.Resampling.LANCZOS)
        
        # Calculate position
        col = idx % cols
        row = idx // cols
        x = col * cell_width + (cell_width - img.width) // 2
        y = row * cell_height + (cell_height - img.height) // 2
        
        collage.paste(img, (x, y))
    
    return collage


def create_product_records(doc, images_by_page, db: Session):
    """Process each page and create product records"""
    products_created = 0
    
    for page_num, page_images in images_by_page.items():
        try:
            # Get page text
            page = doc[page_num]
            text = page.get_text()
            
            # Parse metadata
            metadata = parse_page_text(text)
            
            # Generate IDs
            product_id = str(uuid.uuid4())
            sku = metadata['sku'] or f"P{page_num + 1:03d}"
            
            # Upload main image to MinIO
            main_img = page_images[0]
            img_buffer = BytesIO()
            main_img['pil'].save(img_buffer, format='JPEG', quality=95)
            img_buffer.seek(0)
            
            image_key = f"images/{product_id}.jpg"
            upload_image(img_buffer.read(), image_key)
            
            # Create and upload collage
            collage = make_collage(page_images)
            collage_key = None
            if collage:
                collage_buffer = BytesIO()
                collage.save(collage_buffer, format='JPEG', quality=95)
                collage_buffer.seek(0)
                
                collage_key = f"collages/{product_id}.jpg"
                upload_image(collage_buffer.read(), collage_key)
            
            # Create product record
            product = Product(
                id=product_id,
                sku_code=sku,
                cn_name=metadata['cn_name'],
                category="Furniture",
                dims_l=metadata['dims']['l'],
                dims_w=metadata['dims']['w'],
                dims_h=metadata['dims']['h'],
                description=f"Product from page {page_num + 1}",
                image_key=image_key,
                collage_key=collage_key,
            )
            
            db.add(product)
            products_created += 1
            
            if products_created % 10 == 0:
                print(f"✅ Processed {products_created} products...")
        
        except Exception as e:
            print(f"⚠️  Error processing page {page_num}: {e}")
            continue
    
    db.commit()
    print(f"✅ Created {products_created} product records")


def main():
    """Main ingestion pipeline"""
    pdf_path = Path(__file__).parent / "input" / "catalog.pdf"
    
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        print("   Place your catalog.pdf in backend/input/")
        return
    
    print(f"📄 Processing: {pdf_path}")
    
    # Initialize
    init_db()
    
    # Open PDF
    doc = fitz.open(pdf_path)
    print(f"📖 Loaded PDF with {len(doc)} pages")
    
    # Extract images
    images_by_page = extract_images_from_pdf(doc)
    
    # Create records
    db = SessionLocal()
    try:
        create_product_records(doc, images_by_page, db)
    finally:
        db.close()
    
    doc.close()
    print("✅ Ingestion complete!")
    print("🚀 Run: uvicorn app.main:app --reload")
    print("🌐 Then open: http://localhost:8000/docs")


if __name__ == "__main__":
    main()