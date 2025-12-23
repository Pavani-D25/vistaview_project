import os
from datetime import timedelta
from minio import Minio
from urllib.parse import urlparse

# MinIO connection config
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio12345")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "vistaview-catalog")

# This is what the browser will use (must be publicly accessible)
MINIO_PUBLIC_BASE_URL = os.getenv(
    "MINIO_PUBLIC_BASE_URL", 
    "http://localhost:9000"
).rstrip("/")

client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE,
)

def ensure_bucket():
    """Create bucket if it doesn't exist"""
    if not client.bucket_exists(MINIO_BUCKET):
        client.make_bucket(MINIO_BUCKET)
        print(f"✅ Created bucket: {MINIO_BUCKET}")

def upload_image(image_bytes: bytes, object_key: str, content_type: str = "image/jpeg"):
    """
    Upload image to MinIO
    
    Args:
        image_bytes: Image data as bytes
        object_key: Path in bucket, e.g., "images/p001.jpg"
        content_type: MIME type
    
    Returns:
        object_key: The key that was used (for storing in DB)
    """
    from io import BytesIO
    
    client.put_object(
        MINIO_BUCKET,
        object_key,
        BytesIO(image_bytes),
        length=len(image_bytes),
        content_type=content_type,
    )
    return object_key

def presign_get(object_key: str, expires_seconds: int = 3600) -> str:
    """
    Generate a presigned URL that the browser can use
    
    Args:
        object_key: MinIO object key, e.g., "images/p001.jpg"
        expires_seconds: How long the URL is valid (default 1 hour)
    
    Returns:
        Full presigned URL with query parameters
    """
    if not object_key:
        return None
    
    # Get presigned URL from MinIO
    url = client.presigned_get_object(
        MINIO_BUCKET,
        object_key,
        expires=timedelta(seconds=expires_seconds),
    )
    
    # Replace internal endpoint with public URL
    # Example: http://minio:9000/bucket/key?X-Amz... 
    #       → http://localhost:9000/bucket/key?X-Amz...
    parsed = urlparse(url)
    return f"{MINIO_PUBLIC_BASE_URL}{parsed.path}?{parsed.query}"