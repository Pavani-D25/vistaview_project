#!/usr/bin/env python3
"""
VistaView Vendor Catalog Ingestion Script
Extracts images, dimensions, and metadata from PDF catalogs
"""
import re
import uuid
import sqlite3
import json
from pathlib import Path
from PIL import Image
import fitz  # PyMuPDF

# Directory setup
BACKEND_DIR = Path(__file__).parent
INPUT_DIR = BACKEND_DIR / "input"
DATA_DIR = BACKEND_DIR / "data"
IMG_DIR = DATA_DIR / "images"
COL_DIR = DATA_DIR / "collages"
DB_PATH = DATA_DIR / "vistaview.sqlite"
PDF_PATH = INPUT_DIR / "catalog.pdf"

# Regex patterns for parsing
SKU_RE = re.compile(r"[A-Z]{1,6}-?\d{1,6}[A-Z0-9]*")
DIMS_RE = re.compile(r"(\d{3,4})\s*[xX×*]\s*(\d{3,4})\s*[xX×*]\s*(\d{3,4})")
CN_RE = re.compile(r"[\u4e00-\u9fff]{2,30}")


def init_db():
    """Initialize SQLite database with schema"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS skus(
        id TEXT PRIMARY KEY,
        sku_code TEXT,
        cn_name TEXT,
        category TEXT,
        dims_l INTEGER,
        dims_w INTEGER,
        dims_h INTEGER,
        description TEXT,
        image_path TEXT,
        collage_path TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    print("✅ Database initialized")
    return conn


def make_collage(img_paths, out_path):
    """Create a 3x2 collage from product images"""
    tiles = []
    for p in img_paths[:6]:
        try:
            im = Image.open(p).convert("RGB")
            im.thumbnail((420, 420))
            canvas = Image.new("RGB", (420, 420), (255, 255, 255))
            canvas.paste(im, ((420 - im.width)//2, (420 - im.height)//2))
            tiles.append(canvas)
        except Exception as e:
            print(f"⚠️  Warning: Could not process image {p.name}: {e}")
            continue
    
    if not tiles:
        return None
    
    cols = 3
    rows = (len(tiles) + cols - 1) // cols
    collage = Image.new("RGB", (cols * 420, rows * 420), (255, 255, 255))
    
    for i, tile in enumerate(tiles):
        r, c = divmod(i, cols)
        collage.paste(tile, (c * 420, r * 420))
    
    collage.save(out_path, "JPEG", quality=90)
    print(f"   ✓ Collage created: {out_path.name}")
    return out_path


def best_cn_name(text):
    """Extract best Chinese product name from text"""
    hits = CN_RE.findall(text or "")
    if not hits:
        return None
    
    # Prefer common furniture terms
    prefs = ["沙发", "床", "椅", "柜", "茶几", "凳", "桌", "架"]
    for w in hits:
        for p in prefs:
            if p in w:
                return w
    return hits[0]


def extract_images_from_pdf(doc):
    """Extract all images from PDF pages"""
    images_by_page = {}
    
    print(f"\n📄 Processing {len(doc)} pages...")
    for pno in range(len(doc)):
        page = doc[pno]
        img_list = page.get_images(full=True)
        
        for img in img_list:
            xref = img[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                
                # Skip very small images (likely logos/icons)
                if pix.width < 200 or pix.height < 200:
                    continue
                
                if pix.alpha:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                
                out = IMG_DIR / f"p{pno+1:03d}_{xref}.jpg"
                out.write_bytes(pix.tobytes("jpeg"))
                images_by_page.setdefault(pno+1, []).append(out)
                
            except Exception as e:
                print(f"⚠️  Warning: Could not extract image from page {pno+1}: {e}")
                continue
        
        if pno + 1 in images_by_page:
            print(f"   Page {pno+1}: {len(images_by_page[pno+1])} images extracted")
    
    return images_by_page


def parse_page_text(text):
    """Parse SKU, dimensions, and Chinese name from page text"""
    # Extract SKU
    sku_match = SKU_RE.search(text)
    sku = sku_match.group(0) if sku_match else None
    
    # Extract dimensions (L x W x H in mm)
    dims_match = DIMS_RE.search(text.replace("×", "*"))
    l = w = h = None
    if dims_match:
        l, w, h = map(int, dims_match.groups())
    
    # Extract Chinese name
    cn_name = best_cn_name(text)
    
    return sku, l, w, h, cn_name


def create_product_records(doc, images_by_page, conn):
    """Create product records in database"""
    cur = conn.cursor()
    count = 0
    
    print("\n🔄 Creating product records...")
    for pno in range(1, len(doc) + 1):
        text = doc[pno-1].get_text("text") or ""
        
        # Parse metadata
        sku, l, w, h, cn_name = parse_page_text(text)
        
        # Get images for this page
        imgs = images_by_page.get(pno, [])
        main_img = imgs[0] if imgs else None
        
        # Create collage if images exist
        collage_path = None
        if imgs:
            sku_prefix = sku or f"ITEM_{pno:03d}"
            out_col = COL_DIR / f"{sku_prefix}_collage.jpg"
            if make_collage(imgs, out_col):
                collage_path = f"/collages/{out_col.name}"
        
        # Create paths
        image_path = f"/images/{main_img.name}" if main_img else None
        
        # Generate description
        dims_str = f"{l}×{w}×{h}" if all([l, w, h]) else "---"
        description = f"{sku or 'ITEM'} {cn_name or ''} | Dimensions(mm): {dims_str}"
        
        # Insert into database
        cur.execute("""
        INSERT INTO skus
        (id, sku_code, cn_name, category, dims_l, dims_w, dims_h, 
         description, image_path, collage_path)
        VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            str(uuid.uuid4()),
            sku,
            cn_name,
            "Furniture",
            l, w, h,
            description,
            image_path,
            collage_path
        ))
        
        count += 1
        status = f"Page {pno}: {sku or f'ITEM_{pno:03d}'}"
        if cn_name:
            status += f" ({cn_name})"
        if imgs:
            status += f" - {len(imgs)} images"
        print(f"   ✓ {status}")
    
    conn.commit()
    return count


def sync_to_frontend():
    """Create symlinks for frontend to access images"""
    frontend_public = BACKEND_DIR.parent / "frontend" / "public"
    
    print("\n🔗 Syncing images to frontend...")
    
    # Create public directories if they don't exist
    (frontend_public / "images").mkdir(parents=True, exist_ok=True)
    (frontend_public / "collages").mkdir(parents=True, exist_ok=True)
    
    # Copy images
    img_count = 0
    for img in IMG_DIR.glob("*.jpg"):
        dest = frontend_public / "images" / img.name
        dest.write_bytes(img.read_bytes())
        img_count += 1
    
    col_count = 0
    for col in COL_DIR.glob("*.jpg"):
        dest = frontend_public / "collages" / col.name
        dest.write_bytes(col.read_bytes())
        col_count += 1
    
    print(f"   ✓ Copied {img_count} images and {col_count} collages")

    # NEW: export database rows to public/skus.json for the frontend
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM skus ORDER BY created_at").fetchall()
        data = [dict(r) for r in rows]
        out_json = frontend_public / "skus.json"
        out_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"   ✓ Exported {len(data)} records to /public/skus.json")
    except Exception as e:
        print(f"⚠️  Warning: could not export skus.json: {e}")
    finally:
        try:
            conn.close()
        except:
            pass


def main():
    """Main ingestion pipeline"""
    print("=" * 60)
    print("🏠 VistaView Vendor Catalog Ingestion")
    print("=" * 60)
    
    # Validate PDF exists
    if not PDF_PATH.exists():
        print(f"\n❌ Error: PDF not found at {PDF_PATH}")
        print(f"   Please place your catalog PDF at: {PDF_PATH}")
        return 1
    
    print(f"\n📂 Input PDF: {PDF_PATH}")
    print(f"💾 Database: {DB_PATH}")
    
    # Create directories
    print("\n📁 Creating directories...")
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    COL_DIR.mkdir(parents=True, exist_ok=True)
    
    # Clear old database
    if DB_PATH.exists():
        DB_PATH.unlink()
        print("   ✓ Cleared old database")
    
    # Initialize database
    conn = init_db()
    
    # Open PDF
    print(f"\n📖 Opening PDF...")
    doc = fitz.open(str(PDF_PATH))
    print(f"   ✓ Found {len(doc)} pages")
    
    # Extract images
    images_by_page = extract_images_from_pdf(doc)
    total_images = sum(len(imgs) for imgs in images_by_page.values())
    print(f"\n   ✓ Total images extracted: {total_images}")
    
    # Create product records
    count = create_product_records(doc, images_by_page, conn)
    
    # Close database and PDF
    conn.close()
    doc.close()
    
    # Sync to frontend
    sync_to_frontend()
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ Ingestion Complete!")
    print("=" * 60)
    print(f"Products created: {count}")