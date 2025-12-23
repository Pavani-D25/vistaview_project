# MinIO Setup Instructions

## Option 1: Run MinIO with Docker (Recommended)

### Install Docker Desktop
1. Download Docker Desktop from: https://www.docker.com/products/docker-desktop
2. Install and restart your computer
3. Start Docker Desktop

### Start MinIO
```powershell
cd d:\vistaview_project
docker compose up -d minio
```

### Verify MinIO is running
- MinIO API: http://localhost:9000
- MinIO Console: http://localhost:9001
- Login credentials:
  - Username: `minio`
  - Password: `minio12345`

## Option 2: Run without MinIO (Local Storage Only)

If you don't want to use MinIO, the system will automatically use local file storage.

### Run Backend without MinIO
```powershell
$env:DATABASE_URL = "sqlite:///d:/vistaview_project/backend/data/vistaview.sqlite"
$env:MINIO_DISABLED = "true"
d:\vistaview_project\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Images will be stored in:
- `backend/data/images/<session_id>/`
- `backend/data/collages/<session_id>/`

And served via:
- `http://localhost:8000/static/images/...`
- `http://localhost:8000/static/collages/...`

## Option 3: Run MinIO Standalone (Without Docker)

### Download MinIO
```powershell
# Download MinIO executable
Invoke-WebRequest -Uri "https://dl.min.io/server/minio/release/windows-amd64/minio.exe" -OutFile "minio.exe"
```

### Run MinIO
```powershell
# Set credentials
$env:MINIO_ROOT_USER = "minio"
$env:MINIO_ROOT_PASSWORD = "minio12345"

# Start MinIO server
.\minio.exe server d:\vistaview_project\backend\data\minio_storage --console-address ":9001"
```

### Run Backend with MinIO
```powershell
$env:DATABASE_URL = "sqlite:///d:/vistaview_project/backend/data/vistaview.sqlite"
$env:MINIO_DISABLED = "false"  # or remove this line
d:\vistaview_project\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MINIO_DISABLED` | `false` | Set to `"true"` to use local storage instead of MinIO |
| `MINIO_ENDPOINT` | `localhost:9000` | MinIO server endpoint |
| `MINIO_ACCESS_KEY` | `minio` | MinIO access key |
| `MINIO_SECRET_KEY` | `minio12345` | MinIO secret key |
| `MINIO_BUCKET` | `vistaview-catalog` | Bucket name for storing images |
| `MINIO_PUBLIC_BASE_URL` | `http://localhost:9000` | Public URL for accessing MinIO |

## Troubleshooting

### Connection Refused Error
- **Check Docker:** Make sure Docker Desktop is running
- **Check Port:** Ensure port 9000 is not used by another application
- **Restart MinIO:** `docker compose restart minio`

### Images Not Displaying
- **With MinIO:** Check MinIO console at http://localhost:9001 to verify bucket exists
- **Without MinIO:** Check `backend/data/images/` folder for images
- **Check Logs:** Backend logs show whether MinIO or local storage is being used

### Bucket Not Found
The backend automatically creates the bucket on startup. If you see errors:
1. Access MinIO Console: http://localhost:9001
2. Login with `minio` / `minio12345`
3. Check if `vistaview-catalog` bucket exists
4. If not, create it manually or restart the backend

## Current Status Check

Run this in PowerShell to check your setup:

```powershell
# Check if Docker is running
docker ps

# Check if MinIO container is running
docker ps | Select-String "minio"

# Check MinIO health
Invoke-WebRequest -Uri "http://localhost:9000/minio/health/live" -UseBasicParsing

# Check backend health
Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing
```
