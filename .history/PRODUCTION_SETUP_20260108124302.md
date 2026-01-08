# Production Pipeline Setup Guide

This guide will help you set up the production-grade 3D pipeline for VistaView.

## Prerequisites

- Python 3.9 or higher
- CUDA-capable GPU (recommended, RTX 3060+ or better)
- 8GB+ GPU memory
- 16GB+ system RAM

## Step 1: Install Base Dependencies

```bash
# Activate your virtual environment
# On Windows:
.\venv\Scripts\activate

# On Linux/Mac:
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

## Step 2: Install PyTorch with CUDA

**For CUDA 11.8** (most common):
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

**For CUDA 12.1**:
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

**For CPU only** (not recommended for production):
```bash
pip install torch torchvision
```

**Verify installation**:
```bash
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}')"
```

## Step 3: Install Production Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `trimesh` - 3D mesh processing
- `pyrender` - OpenGL rendering
- `scipy` - Scientific computing
- `networkx` - Graph algorithms
- `torchmcubes` - Marching cubes for mesh extraction
- `rembg` - Background removal (optional)

## Step 4: Install TripoSR (Optional but Recommended)

TripoSR provides the best mesh reconstruction quality.

```bash
# Clone TripoSR repository
git clone https://github.com/VAST-AI-Research/TripoSR.git
cd TripoSR

# Install in development mode
pip install -e .

# Return to project directory
cd ..
```

**Note**: If TripoSR installation fails, the system will automatically fall back to depth-based reconstruction.

## Step 5: Setup OpenGL for Rendering

### Windows

OpenGL is typically pre-installed. No additional setup needed.

### Linux (Ubuntu/Debian)

**For desktop environments**:
```bash
sudo apt-get update
sudo apt-get install libgl1-mesa-glx libglib2.0-0
```

**For headless servers** (no display):
```bash
# Install OSMesa for offscreen rendering
sudo apt-get install libosmesa6-dev freeglut3-dev

# Set environment variable
export PYOPENGL_PLATFORM=osmesa

# Add to ~/.bashrc for persistence
echo "export PYOPENGL_PLATFORM=osmesa" >> ~/.bashrc
```

### macOS

OpenGL is pre-installed. No additional setup needed.

## Step 6: Verify Installation

Test individual components:

```bash
python test_production_pipeline.py --components-only
```

Expected output:
```
🔧 TESTING INDIVIDUAL COMPONENTS
======================================================================

1️⃣ Testing Depth Estimator...
   ✅ Depth estimator initialized
   ✅ Depth map generated: shape=(256, 256)

2️⃣ Testing Mesh Reconstructor...
   ✅ Mesh reconstructor initialized
   ✅ Mesh generated: 65536 vertices

3️⃣ Testing Mesh Renderer...
   ✅ Mesh renderer initialized
   ✅ View rendered: (512, 512)
```

## Step 7: Test with Sample Image

```bash
# Download a sample product image or use your own
python test_production_pipeline.py path/to/product_image.jpg
```

This will:
1. Test depth estimation
2. Test mesh reconstruction
3. Test dimension scaling
4. Render multiple angle views
5. Save results to `test_output/` directory

## Troubleshooting

### Issue: PyRender "No module named 'pyrender'"

**Solution**:
```bash
pip install pyrender pyglet<2
```

### Issue: "CUDA out of memory"

**Solutions**:
1. Reduce image size before processing
2. Lower mesh resolution
3. Use CPU mode (slower):

```python
# In app/mesh_reconstructor.py, change:
self.device = 'cpu'
```

### Issue: "OpenGL not available" on headless server

**Solution**:
```bash
# Install OSMesa
sudo apt-get install libosmesa6-dev

# Set platform
export PYOPENGL_PLATFORM=osmesa

# Test
python -c "import pyrender; print('PyRender OK')"
```

### Issue: TripoSR installation fails

**Solution**:
The system will automatically use the fallback depth-based reconstruction. This is acceptable for most use cases.

To retry TripoSR installation:
```bash
pip install torchmcubes
pip install git+https://github.com/VAST-AI-Research/TripoSR.git
```

### Issue: MiDaS download fails

**Solution**:
MiDaS models are downloaded automatically from PyTorch Hub. If download fails:

1. Check internet connection
2. Clear torch hub cache:
```bash
python -c "import torch; torch.hub.set_dir('~/.cache/torch/hub')"
rm -rf ~/.cache/torch/hub
```

3. Manual download:
```bash
mkdir -p ~/.cache/torch/hub/checkpoints
wget https://github.com/isl-org/MiDaS/releases/download/v3_1/dpt_beit_large_512.pt \
     -O ~/.cache/torch/hub/checkpoints/dpt_beit_large_512.pt
```

## Performance Optimization

### GPU Memory Optimization

For systems with limited GPU memory (< 8GB):

1. **Reduce input image size**:
```python
# Before processing
image.thumbnail((512, 512), Image.LANCZOS)
```

2. **Use smaller depth model**:
```python
# In app/depth_estimator.py
estimator = DepthEstimator(model_type="MiDaS_small")
```

3. **Lower mesh resolution**:
```python
# In app/mesh_reconstructor.py
mesh = reconstruct_mesh_triposr(image, mc_resolution=128)
```

### Speed Optimization

For faster processing:

1. **Use mixed precision**:
```python
# Add to model loading
torch.set_float32_matmul_precision('high')
```

2. **Batch processing** for multiple products
3. **Cache models** in memory (already implemented)

## Environment Variables

Add to `.env` file:

```bash
# Force CPU mode (for testing)
FORCE_CPU=false

# Disable Zero123 fallback
ZERO123_ENABLED=false

# Custom model cache directory
TORCH_HOME=/path/to/models/cache

# OpenGL platform (headless servers)
PYOPENGL_PLATFORM=osmesa

# Log level
LOG_LEVEL=INFO
```

## Docker Setup (Optional)

For containerized deployment:

```dockerfile
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    libosmesa6-dev \
    libgl1-mesa-glx \
    git

# Set OpenGL platform
ENV PYOPENGL_PLATFORM=osmesa

# Install Python packages
COPY requirements.txt .
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
RUN pip install -r requirements.txt

# Install TripoSR
RUN git clone https://github.com/VAST-AI-Research/TripoSR.git && \
    cd TripoSR && \
    pip install -e .

# Copy application
COPY . /app
WORKDIR /app

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Next Steps

1. **Test the pipeline** with your product images
2. **Adjust parameters** (angles, resolution) for your use case
3. **Integrate with frontend** to display generated views
4. **Monitor performance** and optimize as needed

## Support

If you encounter issues:

1. Check [PRODUCTION_PIPELINE.md](./PRODUCTION_PIPELINE.md) for detailed documentation
2. Run component tests: `python test_production_pipeline.py --components-only`
3. Check logs for specific error messages
4. Verify GPU availability: `nvidia-smi`

## Success Criteria

✅ All components test successfully  
✅ Sample image generates 5+ views in < 5 seconds on GPU  
✅ Views look realistic and maintain product proportions  
✅ API endpoint responds successfully  

Once everything works, you're ready for production! 🚀
