import os
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from .db import engine, get_db
from .models import Base
from .minio_client import ensure_bucket
from .routes.products import router as products_router
from .ingestion import ingest_pdf, DATA_DIR

app = FastAPI(
    title="VistaView Catalog API",
    description="Product catalog with presigned image URLs",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create static file directories
IMAGES_DIR = DATA_DIR / "images"
COLLAGES_DIR = DATA_DIR / "collages"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
COLLAGES_DIR.mkdir(parents=True, exist_ok=True)

# Mount static file directories for local image serving
app.mount("/static/images", StaticFiles(directory=str(IMAGES_DIR)), name="images")
app.mount("/static/collages", StaticFiles(directory=str(COLLAGES_DIR)), name="collages")

@app.on_event("startup")
def startup():
    """Initialize database and storage on startup"""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")
    
    # Ensure MinIO bucket exists (only if MinIO is enabled)
    if os.getenv("MINIO_DISABLED", "").lower() != "true":
        try:
            ensure_bucket()
            print("✅ MinIO bucket ready")
        except Exception as e:
            print(f"⚠️ MinIO initialization failed: {e}")
            print("⚠️ Continuing with local storage only")
    else:
        print("⚠️ MinIO disabled via MINIO_DISABLED env var; skipping bucket init")

@app.get("/")
def root():
    return {
        "message": "VistaView API",
        "docs": "/docs",
        "products": "/api/products"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/api/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload and process a PDF catalog"""
    if not file.filename.endswith('.pdf'):
        return {"error": "File must be a PDF"}
    
    # Read PDF content
    pdf_bytes = await file.read()
    
    # Check if MinIO is disabled
    use_minio = os.getenv("MINIO_DISABLED", "").lower() != "true"
    
    # Process the PDF
    try:
        result = ingest_pdf(pdf_bytes, db, use_minio=use_minio)
        return {
            "status": "success",
            "message": f"Processed {result['pages_processed']} pages",
            "products_created": result['products_created'],
            "images_extracted": result['images_extracted'],
            "collages_created": result['collages_created'],
            "session_id": result.get('session_id', 'N/A')
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Include routers
app.include_router(products_router)