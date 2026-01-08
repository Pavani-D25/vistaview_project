# 🚀 Production Pipeline Quick Start Checklist

Use this checklist to get the production pipeline up and running.

## ✅ Pre-Installation Checklist

- [ ] **Python 3.9+** installed
  ```powershell
  python --version
  # Should show 3.9 or higher
  ```

- [ ] **CUDA-capable GPU** (recommended)
  ```powershell
  nvidia-smi
  # Should show GPU info and CUDA version
  ```

- [ ] **Git** installed (for TripoSR)
  ```powershell
  git --version
  ```

- [ ] **Virtual environment** activated
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```

## ✅ Installation Checklist

### Automated Installation (Recommended)

- [ ] **Run setup script**
  ```powershell
  .\setup_production_pipeline.ps1
  ```

- [ ] **Verify PyTorch installation**
  ```powershell
  python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"
  # Should show: CUDA: True (if GPU available)
  ```

### Manual Installation (Alternative)

- [ ] **Install PyTorch**
  ```powershell
  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
  ```

- [ ] **Install base dependencies**
  ```powershell
  pip install trimesh pyrender "pyglet<2" scipy networkx
  ```

- [ ] **Install remaining requirements**
  ```powershell
  pip install -r requirements.txt
  ```

- [ ] **Install TripoSR (optional)**
  ```powershell
  pip install torchmcubes
  git clone https://github.com/VAST-AI-Research/TripoSR.git
  cd TripoSR && pip install -e . && cd ..
  ```

## ✅ Testing Checklist

### Component Tests

- [ ] **Test depth estimator**
  ```powershell
  python -c "from app.depth_estimator import get_depth_estimator; e = get_depth_estimator(); print('✅ Depth estimator OK')"
  ```

- [ ] **Test mesh reconstructor**
  ```powershell
  python -c "from app.mesh_reconstructor import get_mesh_reconstructor; r = get_mesh_reconstructor(); print('✅ Mesh reconstructor OK')"
  ```

- [ ] **Test mesh renderer**
  ```powershell
  python -c "from app.mesh_renderer import get_mesh_renderer; m = get_mesh_renderer(); print('✅ Mesh renderer OK')"
  ```

- [ ] **Run all component tests**
  ```powershell
  python test_production_pipeline.py --components-only
  ```

### Full Pipeline Test

- [ ] **Test with sample image**
  ```powershell
  # Use any product image you have
  python test_production_pipeline.py path\to\sample_product.jpg
  ```

- [ ] **Check output files**
  ```powershell
  ls test_output\
  # Should show generated view images
  ```

- [ ] **Verify output quality**
  - [ ] Images are clear and not corrupted
  - [ ] Multiple angles are visible
  - [ ] Proportions look correct

## ✅ Backend Integration Checklist

### Start Backend

- [ ] **Set environment variables**
  ```powershell
  $env:DATABASE_URL = "sqlite:///d:/vistaview_project/backend/data/vistaview.sqlite"
  # Or use your PostgreSQL connection string
  ```

- [ ] **Start backend server**
  ```powershell
  .\run_backend.ps1
  # Or: uvicorn app.main:app --reload
  ```

- [ ] **Verify backend is running**
  - Open http://localhost:8000/docs
  - Should see API documentation

### Test API Endpoint

- [ ] **Upload a test product** (if needed)
  - Go to http://localhost:5173 (frontend)
  - Upload a PDF catalog

- [ ] **Get product ID**
  ```powershell
  curl http://localhost:8000/api/products
  # Note down a product ID
  ```

- [ ] **Generate views via API**
  ```powershell
  # Replace {product_id} with actual ID
  curl -X POST "http://localhost:8000/api/products/{product_id}/generate-views?angles=15,30,45"
  ```

- [ ] **Check API response**
  - [ ] `"success": true`
  - [ ] `"status": "success"`
  - [ ] Multiple view URLs returned

- [ ] **Verify views in MinIO/Storage**
  - Open returned URLs
  - Images should load and look correct

## ✅ Frontend Integration Checklist

### Start Frontend

- [ ] **Install frontend dependencies**
  ```powershell
  cd frontend
  npm install
  ```

- [ ] **Start frontend dev server**
  ```powershell
  npm run dev
  ```

- [ ] **Access frontend**
  - Open http://localhost:5173
  - Should see product catalog interface

### Test User Flow

- [ ] **Upload PDF catalog**
  - Click "Upload PDF"
  - Select a PDF file
  - Wait for ingestion to complete

- [ ] **View products**
  - Products should appear in list
  - Each product shows main image

- [ ] **Generate views for a product**
  - Click on a product
  - Click "Generate Views" button
  - Wait for generation (~2 seconds)

- [ ] **View generated angles**
  - Multiple angle views should appear
  - Views should be consistent and clear
  - Proportions should look correct

## ✅ Performance Verification

### Expected Timings (GPU)

- [ ] **Depth estimation**: 10-40ms
- [ ] **Mesh reconstruction**: 1-2 seconds
- [ ] **First complete generation**: ~2 seconds
- [ ] **Additional views**: ~12ms each

### Check Logs

- [ ] **View backend logs**
  - Should see timing information
  - No errors or warnings

Example good output:
```
🏭 PRODUCTION PIPELINE: Image → 3D → Render Views
📊 Step 1: Depth Estimation (MiDaS)...
   ✅ Depth map generated in 0.35s
🔺 Step 2: Mesh Reconstruction...
   ✅ Mesh reconstructed in 1.82s
📏 Step 3: Metric Scaling to real dimensions...
   ✅ Mesh scaled to real dimensions
🎨 Step 4: Rendering 5 angle views...
   ✅ 5 views rendered in 0.15s
✅ PIPELINE COMPLETE
⏱️  Total time: 2.32s
```

## ✅ Troubleshooting Checklist

### Common Issues

- [ ] **"PyRender not available"**
  ```powershell
  pip install pyrender "pyglet<2"
  ```

- [ ] **"CUDA out of memory"**
  - [ ] Close other GPU applications
  - [ ] Reduce image size in code
  - [ ] Use CPU mode (slower):
    ```python
    # In app/depth_estimator.py
    self.device = 'cpu'
    ```

- [ ] **"TripoSR not available"**
  - [ ] This is OK - system uses fallback
  - [ ] To install: see [PRODUCTION_SETUP.md](./PRODUCTION_SETUP.md)

- [ ] **Slow performance**
  - [ ] Check GPU is being used:
    ```powershell
    nvidia-smi
    # Should show GPU utilization
    ```
  - [ ] Check CUDA version matches PyTorch
  - [ ] Close other GPU applications

- [ ] **Views look distorted**
  - [ ] Check product dimensions in database
  - [ ] Verify mesh scaling is enabled
  - [ ] Check input image quality

## ✅ Documentation Review

- [ ] **Read [PRODUCTION_PIPELINE.md](./PRODUCTION_PIPELINE.md)**
  - Understand architecture
  - Review API reference
  - Check performance benchmarks

- [ ] **Read [PRODUCTION_SETUP.md](./PRODUCTION_SETUP.md)**
  - Review installation steps
  - Check platform-specific notes
  - Review optimization tips

- [ ] **Read [ARCHITECTURE_DIAGRAM.md](./ARCHITECTURE_DIAGRAM.md)**
  - Understand data flow
  - Review component dependencies
  - Check timing breakdown

## ✅ Production Readiness

### Before Going Live

- [ ] **All tests pass**
- [ ] **API responds correctly**
- [ ] **Views look professional**
- [ ] **Performance meets requirements**
- [ ] **Error handling works**
- [ ] **Logs are clean**

### Performance Targets

- [ ] **GPU Mode**:
  - [ ] First generation: < 3 seconds
  - [ ] Additional views: < 20ms
  - [ ] GPU memory: < 6GB

- [ ] **Quality**:
  - [ ] Views are clear and sharp
  - [ ] No artifacts or distortions
  - [ ] Proportions are accurate
  - [ ] Lighting looks natural

### Monitoring

- [ ] **Set up logging**
  - Track generation times
  - Monitor success/failure rates
  - Log GPU memory usage

- [ ] **Set up alerts**
  - Alert on high error rates
  - Alert on slow performance
  - Alert on GPU memory issues

## ✅ Optional Enhancements

### Nice-to-Have

- [ ] **Background removal** (rembg)
  ```powershell
  pip install rembg
  ```

- [ ] **High-resolution rendering**
  - Edit render_size in code to (1024, 1024)
  - Note: Uses more GPU memory

- [ ] **Custom angles**
  - Test with different angle sets
  - Find optimal angles for your products

- [ ] **Batch processing**
  - Generate views for multiple products
  - Use async processing

## 📊 Final Checklist

### Ready for Production? ✅

- [ ] ✅ All components installed and tested
- [ ] ✅ Backend API works correctly
- [ ] ✅ Frontend displays views properly
- [ ] ✅ Performance meets expectations
- [ ] ✅ Quality is professional
- [ ] ✅ Error handling is robust
- [ ] ✅ Documentation is reviewed
- [ ] ✅ Team is trained on the system

### If All Checked Above: 🎉

**Congratulations! Your production pipeline is ready!**

You can now:
- Generate views for all products
- Handle customer requests quickly
- Scale to large catalogs
- Deliver professional results

---

## 🆘 Need Help?

If you're stuck on any step:

1. **Check documentation**: [PRODUCTION_SETUP.md](./PRODUCTION_SETUP.md)
2. **Run component tests**: `python test_production_pipeline.py --components-only`
3. **Check logs** for specific error messages
4. **Verify GPU**: `nvidia-smi`
5. **Review this checklist** again

## 📝 Notes Section

Use this space to track your progress and any custom configurations:

```
Installation Date: _______________

GPU Model: _______________

CUDA Version: _______________

Special Configurations:
- 
- 
- 

Issues Encountered:
- 
- 
- 

Performance Notes:
- Average generation time: _______________
- GPU memory usage: _______________
- Quality rating: _______________
```

---

**Ready to go? Start generating! 🚀**
