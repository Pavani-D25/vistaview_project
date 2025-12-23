# VistaView Setup Script
# This script sets up and runs the VistaView backend with MinIO

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  VistaView Project Setup" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is available
Write-Host "Checking Docker..." -ForegroundColor Yellow
$dockerAvailable = $false
try {
    $dockerVersion = docker --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Docker is installed: $dockerVersion" -ForegroundColor Green
        $dockerAvailable = $true
    }
} catch {
    Write-Host "❌ Docker is not installed or not in PATH" -ForegroundColor Red
}

Write-Host ""

# Ask user if they want to use MinIO
if ($dockerAvailable) {
    Write-Host "Would you like to use MinIO for image storage? (y/n)" -ForegroundColor Yellow
    Write-Host "  - Yes: Images stored in MinIO (recommended for production)" -ForegroundColor Gray
    Write-Host "  - No:  Images stored locally in backend/data/images/" -ForegroundColor Gray
    $useMinIO = Read-Host "Choice"
    
    if ($useMinIO -eq "y" -or $useMinIO -eq "Y") {
        Write-Host ""
        Write-Host "Starting MinIO container..." -ForegroundColor Yellow
        docker compose up -d minio
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ MinIO started successfully" -ForegroundColor Green
            Write-Host "   - API: http://localhost:9000" -ForegroundColor Gray
            Write-Host "   - Console: http://localhost:9001" -ForegroundColor Gray
            Write-Host "   - Login: minio / minio12345" -ForegroundColor Gray
            
            # Wait for MinIO to be ready
            Write-Host ""
            Write-Host "Waiting for MinIO to be ready..." -ForegroundColor Yellow
            Start-Sleep -Seconds 3
            
            $env:MINIO_DISABLED = "false"
        } else {
            Write-Host "❌ Failed to start MinIO, using local storage" -ForegroundColor Red
            $env:MINIO_DISABLED = "true"
        }
    } else {
        Write-Host "Using local storage" -ForegroundColor Yellow
        $env:MINIO_DISABLED = "true"
    }
} else {
    Write-Host "Using local storage (Docker not available)" -ForegroundColor Yellow
    $env:MINIO_DISABLED = "true"
}

# Set database URL
$env:DATABASE_URL = "sqlite:///d:/vistaview_project/backend/data/vistaview.sqlite"

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Starting Backend Server" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  - Database: $env:DATABASE_URL" -ForegroundColor Gray
Write-Host "  - MinIO: $(if ($env:MINIO_DISABLED -eq 'true') { 'Disabled (local storage)' } else { 'Enabled' })" -ForegroundColor Gray
Write-Host "  - Backend: http://localhost:8000" -ForegroundColor Gray
Write-Host "  - API Docs: http://localhost:8000/docs" -ForegroundColor Gray
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Start the backend
d:\vistaview_project\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
