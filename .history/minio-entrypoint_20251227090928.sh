#!/bin/sh

# Start MinIO server in background
minio server /data --console-address ":9001" &

# Wait for MinIO to be ready
sleep 5

# Configure MinIO client
mc alias set local http://localhost:9000 ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD}

# Create bucket if it doesn't exist
mc mb local/vistaview-catalog --ignore-existing

# Set CORS policy to allow frontend access
mc anonymous set download local/vistaview-catalog

# Set CORS rules for the bucket
cat > /tmp/cors.json <<EOF
{
  "CORSRules": [
    {
      "AllowedOrigins": ["*"],
      "AllowedMethods": ["GET", "HEAD"],
      "AllowedHeaders": ["*"],
      "ExposeHeaders": ["ETag"]
    }
  ]
}
EOF

mc anonymous set-json /tmp/cors.json local/vistaview-catalog

echo "✅ MinIO configured with CORS support"

# Keep container running
wait
