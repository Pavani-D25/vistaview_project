import os
import time
from datetime import timedelta
from minio import Minio
from minio.error import S3Error
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

client = None

def get_client():
    """Get or create MinIO client with connection validation"""
    global client
    if client is None:
        try:
            client = Minio(
                MINIO_ENDPOINT,
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
                secure=MINIO_SECURE,
            )
            # Test connection
            client.list_buckets()
        except Exception as e:
            print(f"⚠️  MinIO connection failed: {e}")
            client = None
            raise
    return client

def ensure_bucket():
    """Create bucket if it doesn't exist with retry logic"""
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            minio_client = get_client()
            
            if not minio_client.bucket_exists(MINIO_BUCKET):
                minio_client.make_bucket(MINIO_BUCKET)
                print(f"✅ Created MinIO bucket: {MINIO_BUCKET}")
            else:
                print(f"✅ MinIO bucket ready: {MINIO_BUCKET}")
            return True
            
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"⚠️  MinIO connection attempt {attempt + 1} failed, retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                print(f"❌ MinIO connection failed after {max_retries} attempts: {e}")
                raise

def upload_image(image_bytes: bytes, object_key: str, content_type: str = "image/jpeg"):
    """
    Upload image to MinIO with retry logic
    
    Args:
        image_bytes: Image data as bytes
        object_key: Path in bucket, e.g., "images/p001.jpg"
        content_type: MIME type
    
    Returns:
        object_key: The key that was used (for storing in DB)
    """
    from io import BytesIO
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            minio_client = get_client()
            minio_client.put_object(
                MINIO_BUCKET,
                object_key,
                BytesIO(image_bytes),
                length=len(image_bytes),
                content_type=content_type,
            )
            return object_key
        except S3Error as e:
            if attempt < max_retries - 1:
                print(f"⚠️  Upload retry {attempt + 1}/{max_retries} for {object_key}")
                time.sleep(1)
            else:
                print(f"❌ Upload failed for {object_key}: {e}")
                raise

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
    
    try:
        minio_client = get_client()
        # Get presigned URL from MinIO
        url = minio_client.presigned_get_object(
            MINIO_BUCKET,
            object_key,
            expires=timedelta(seconds=expires_seconds),
        )
        
        # Replace internal endpoint with public URL
        # Example: http://minio:9000/bucket/key?X-Amz... 
        #       → http://localhost:9000/bucket/key?X-Amz...
        parsed = urlparse(url)
        return f"{MINIO_PUBLIC_BASE_URL}{parsed.path}?{parsed.query}"
    except Exception as e:
        print(f"⚠️  Failed to generate presigned URL for {object_key}: {e}")
        # Return fallback static path
        return f"/static/{object_key}"