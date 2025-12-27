# MinIO Image Storage - Quick Start Guide

## What Changed

Your VistaView application now stores all images in MinIO object storage instead of local files. This provides:

✅ **Scalable Storage** - Images stored in S3-compatible object storage
✅ **Better Performance** - Direct URLs for image access
✅ **Production Ready** - Easy to deploy to cloud storage (AWS S3, etc.)
✅ **Public Access** - Images are publicly accessible via direct URLs

## Quick Start

### 1. Start the Services

```powershell
cd d:\vistaview_project
docker compose up -d
```

This will start:
- **Backend API** (port 8000) - with MinIO enabled
- **PostgreSQL** (port 5432) - database
- **MinIO** (ports 9000, 9001) - object storage

### 2. Verify MinIO is Running

Open the MinIO Console: http://localhost:9001

**Login credentials:**
- Username: `minio`
- Password: `minio12345`

You should see the `vistaview-catalog` bucket created automatically.

### 3. Start the Frontend

```powershell
cd frontend
npm install  # if not done already
npm run dev
```

Open: http://localhost:5173

### 4. Upload a PDF

1. Go to http://localhost:5173
2. Click "Choose PDF File" and select a furniture catalog PDF
3. Click "Upload & Process"
4. Images will be extracted and stored in MinIO
5. Product cards will display images loaded from MinIO

## How It Works

### Backend Changes

1. **docker-compose.yml** - MinIO is now enabled:
   - `MINIO_DISABLED=false` (was `true`)
   - Backend connects to MinIO service
   - Proper environment variables configured

2. **Image Storage**:
   - Images are uploaded to MinIO bucket: `vistaview-catalog`
   - Path format: `images/{session_id}/{sku}_main.jpg`
   - Collages: `collages/{session_id}/{sku}_collage.jpg`

3. **Public Access**:
   - Bucket policy set to allow public read access
   - Direct URLs: `http://localhost:9000/vistaview-catalog/images/...`
   - No presigned URLs needed (simpler for frontend)

### Frontend Changes

**No changes needed!** The frontend already displays images using the URLs provided by the backend API. It doesn't know or care whether images come from MinIO or local storage.

## Accessing Images

### Via API
```bash
GET http://localhost:8000/api/products
```

Response includes direct MinIO URLs:
```json
{
  "products": [
    {
      "id": "...",
      "sku_code": "SF-001",
      "image_url": "http://localhost:9000/vistaview-catalog/images/20251227_123456/SF-001_main.jpg",
      "collage_url": "http://localhost:9000/vistaview-catalog/collages/20251227_123456/SF-001_collage.jpg"
    }
  ]
}
```

### Via Browser
Direct access to any image:
```
http://localhost:9000/vistaview-catalog/images/{session_id}/{filename}
```

### Via MinIO Console
1. Go to http://localhost:9001
2. Login with `minio` / `minio12345`
3. Browse bucket: `vistaview-catalog`
4. View/download any image

## Environment Variables

All configured in [docker-compose.yml](docker-compose.yml):

| Variable | Value | Description |
|----------|-------|-------------|
| `MINIO_DISABLED` | `false` | MinIO is enabled |
| `MINIO_ENDPOINT` | `minio:9000` | Internal service name |
| `MINIO_ACCESS_KEY` | `minio` | MinIO credentials |
| `MINIO_SECRET_KEY` | `minio12345` | MinIO password |
| `MINIO_BUCKET` | `vistaview-catalog` | Bucket name |
| `MINIO_PUBLIC_BASE_URL` | `http://localhost:9000` | Browser-accessible URL |
| `MINIO_SECURE` | `false` | Use HTTP (not HTTPS) |

## Troubleshooting

### Images Not Loading

**Check MinIO is running:**
```powershell
docker ps
```
You should see `vistaview_minio` container running.

**Check backend logs:**
```powershell
docker compose logs backend
```
Look for:
```
✅ MinIO bucket ready: vistaview-catalog
✅ MinIO bucket policy set to public read
```

**Check MinIO connection:**
Open http://localhost:9000 - should show MinIO XML response (not an error).

### CORS Issues

If frontend can't load images due to CORS:

1. Check browser console for errors
2. MinIO bucket should be publicly readable
3. Backend sets bucket policy automatically on startup
4. Restart backend: `docker compose restart backend`

### Reset Everything

To start fresh:

```powershell
# Stop all services
docker compose down

# Remove MinIO data (WARNING: deletes all images!)
docker volume rm vistaview_project_minio_data

# Remove database
docker volume rm vistaview_project_postgres_data

# Start fresh
docker compose up -d
```

## Production Deployment

For production, update environment variables in docker-compose.yml:

1. **Change credentials:**
   ```yaml
   MINIO_ROOT_USER: your-secure-username
   MINIO_ROOT_PASSWORD: your-secure-password-min-8-chars
   MINIO_ACCESS_KEY: your-secure-username
   MINIO_SECRET_KEY: your-secure-password-min-8-chars
   ```

2. **Use HTTPS:**
   ```yaml
   MINIO_SECURE: true
   MINIO_PUBLIC_BASE_URL: https://your-domain.com
   ```

3. **Or use AWS S3:**
   ```yaml
   MINIO_DISABLED: false
   MINIO_ENDPOINT: s3.amazonaws.com
   MINIO_ACCESS_KEY: your-aws-key
   MINIO_SECRET_KEY: your-aws-secret
   MINIO_BUCKET: your-s3-bucket
   MINIO_PUBLIC_BASE_URL: https://your-s3-bucket.s3.amazonaws.com
   MINIO_SECURE: true
   ```

## Switching Back to Local Storage

If you want to disable MinIO and use local file storage:

1. Edit [docker-compose.yml](docker-compose.yml):
   ```yaml
   environment:
     - MINIO_DISABLED=true
   ```

2. Restart backend:
   ```powershell
   docker compose restart backend
   ```

Images will be stored in:
- `backend/data/images/{session_id}/`
- `backend/data/collages/{session_id}/`

And served via:
- `http://localhost:8000/static/images/{session_id}/...`

## Next Steps

1. ✅ Start services: `docker compose up -d`
2. ✅ Verify MinIO console: http://localhost:9001
3. ✅ Start frontend: `cd frontend && npm run dev`
4. ✅ Upload a PDF and verify images display correctly
5. ✅ Check MinIO console to see uploaded images

Need help? Check the backend logs: `docker compose logs -f backend`
