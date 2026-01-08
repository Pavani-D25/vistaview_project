# Production Pipeline Installation Script
# Run this to install all dependencies for the 3D pipeline

Write-Host "=" -ForegroundColor Cyan -NoNewline
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host "VistaView Production Pipeline Setup" -ForegroundColor Green
Write-Host "=" -ForegroundColor Cyan -NoNewline
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (-not (Test-Path ".\venv\Scripts\Activate.ps1")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& ".\venv\Scripts\Activate.ps1"

# Upgrade pip
Write-Host "`nUpgrading pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip

# Step 1: Install PyTorch with CUDA
Write-Host "`n=== Step 1: Installing PyTorch with CUDA ===" -ForegroundColor Green

$cudaChoice = Read-Host "Do you have a CUDA-capable GPU? (y/n)"

if ($cudaChoice -eq "y") {
    Write-Host "Installing PyTorch with CUDA 11.8..." -ForegroundColor Cyan
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
} else {
    Write-Host "Installing PyTorch (CPU only)..." -ForegroundColor Yellow
    Write-Host "WARNING: CPU mode will be significantly slower" -ForegroundColor Yellow
    pip install torch torchvision
}

# Verify PyTorch installation
Write-Host "`nVerifying PyTorch installation..." -ForegroundColor Cyan
python -c "import torch; print(f'PyTorch version: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda if torch.cuda.is_available() else \"N/A\"}')"

# Step 2: Install production dependencies
Write-Host "`n=== Step 2: Installing Production Dependencies ===" -ForegroundColor Green
Write-Host "Installing trimesh, pyrender, scipy, etc..." -ForegroundColor Cyan

pip install trimesh==4.0.10
pip install pyrender==0.1.45
pip install "pyglet<2"
pip install scipy==1.11.4
pip install networkx==3.2.1
pip install rembg==2.0.57

# Step 3: Install remaining requirements
Write-Host "`n=== Step 3: Installing Remaining Requirements ===" -ForegroundColor Green
pip install -r requirements.txt

# Step 4: Optional TripoSR installation
Write-Host "`n=== Step 4: TripoSR Installation (Optional) ===" -ForegroundColor Green
$tripoChoice = Read-Host "Install TripoSR for best mesh quality? (y/n) [Recommended]"

if ($tripoChoice -eq "y") {
    Write-Host "Installing torchmcubes..." -ForegroundColor Cyan
    pip install torchmcubes==0.1.0
    
    Write-Host "Cloning TripoSR repository..." -ForegroundColor Cyan
    if (Test-Path ".\TripoSR") {
        Write-Host "TripoSR directory already exists, skipping clone" -ForegroundColor Yellow
    } else {
        git clone https://github.com/VAST-AI-Research/TripoSR.git
    }
    
    Write-Host "Installing TripoSR..." -ForegroundColor Cyan
    Set-Location TripoSR
    pip install -e .
    Set-Location ..
    
    Write-Host "TripoSR installed successfully!" -ForegroundColor Green
} else {
    Write-Host "Skipping TripoSR installation" -ForegroundColor Yellow
    Write-Host "The system will use depth-based fallback reconstruction" -ForegroundColor Yellow
}

# Step 5: Test installation
Write-Host "`n=== Step 5: Testing Installation ===" -ForegroundColor Green
Write-Host "Running component tests..." -ForegroundColor Cyan

python test_production_pipeline.py --components-only

# Summary
Write-Host "`n" -NoNewline
Write-Host "=" -ForegroundColor Cyan -NoNewline
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "=" -ForegroundColor Cyan -NoNewline
Write-Host ("=" * 69) -ForegroundColor Cyan

Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "1. Test with a sample image:" -ForegroundColor White
Write-Host "   python test_production_pipeline.py path\to\product.jpg" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Start the backend server:" -ForegroundColor White
Write-Host "   .\run_backend.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Read the documentation:" -ForegroundColor White
Write-Host "   - PRODUCTION_PIPELINE.md" -ForegroundColor Gray
Write-Host "   - PRODUCTION_SETUP.md" -ForegroundColor Gray
Write-Host ""

Write-Host "=" -ForegroundColor Cyan -NoNewline
Write-Host ("=" * 69) -ForegroundColor Cyan
