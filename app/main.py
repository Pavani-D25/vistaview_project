from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db import engine
from .models import Base
from .minio_client import ensure_bucket
from .routes.products import router as products_router

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

@app.on_event("startup")
def startup():
    """Initialize database and storage on startup"""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")
    
    # Ensure MinIO bucket exists
    ensure_bucket()
    print("✅ MinIO bucket ready")

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

# Include routers
app.include_router(products_router)