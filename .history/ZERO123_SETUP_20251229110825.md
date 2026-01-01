# Zero123 View Generation Configuration

This project uses Zero123 for novel view synthesis to generate left and right side views of product images extracted from PDF catalogs.

## What is Zero123?

Zero123 is a state-of-the-art diffusion model for novel view synthesis. Given a single image, it can generate photorealistic views from different camera angles. This is perfect for furniture catalogs where you typically only have one frontal view.

## Configuration

### Model Settings

Located in `app/zero123_generator.py`:

```python
# Model ID (HuggingFace)
model_id = "ashawkey/zero123-xl-diffusers"

# Generation parameters (can be adjusted in ingestion.py)
angle = 30.0  # Rotation angle in degrees (15-45° recommended)
num_inference_steps = 50  # Quality vs speed (30-75 recommended)
guidance_scale = 3.0  # Classifier-free guidance (2.0-5.0)
```

### Performance

- **GPU**: Recommended for production use
  - RTX 3060+ with 8GB+ VRAM
  - Generation time: ~5-10 seconds per view
  
- **CPU**: Functional but slower
  - Generation time: ~30-60 seconds per view
  - Automatically reduces resolution to 256x256

### Memory Optimization

The implementation includes several optimizations:
- Model singleton pattern (loads once, reuses for all images)
- xFormers memory-efficient attention (GPU only)
- Attention slicing to reduce memory usage
- VAE slicing for large images
- Automatic GPU memory cleanup

### Disabling Zero123

If you want to temporarily disable Zero123 view generation:

In `app/ingestion.py`, modify the `generate_left_right_views` function:

```python
left_view, right_view, status = generate_side_views(
    image=image,
    angle=30.0,
    use_zero123=False,  # Set to False to disable
    num_inference_steps=50,
)
```

## Docker Considerations

### Build Time

The Docker build includes PyTorch, Diffusers, and other ML libraries:
- First build: ~10-20 minutes (downloads ~5GB of packages)
- Subsequent builds: Cached (faster)

### Model Download

Zero123 model (~5GB) downloads automatically on first use:
- Stored in Docker container's HuggingFace cache
- Downloaded once per container rebuild
- To persist across rebuilds, mount: `/root/.cache/huggingface`

### Environment Variables

Add to `docker-compose.yml` for customization:

```yaml
environment:
  - ZERO123_ENABLED=true  # Enable/disable Zero123
  - ZERO123_ANGLE=30.0  # Rotation angle
  - ZERO123_STEPS=50  # Inference steps
  - ZERO123_DEVICE=cuda  # 'cuda' or 'cpu'
```

## Usage in Code

```python
from app.zero123_generator import generate_side_views
from PIL import Image

# Load image
image = Image.open("product.jpg")

# Generate views
left_view, right_view, status = generate_side_views(
    image=image,
    angle=30.0,  # 30 degree rotation
    use_zero123=True,
    num_inference_steps=50,
)

if status == "success":
    left_view.save("product_left.jpg")
    right_view.save("product_right.jpg")
```

## Troubleshooting

### Out of Memory (OOM)

If you encounter CUDA OOM errors:

1. Reduce `num_inference_steps` (e.g., from 50 to 30)
2. Enable CPU offloading in `zero123_generator.py`:
   ```python
   self.pipeline.enable_model_cpu_offload()
   ```
3. Process fewer images in parallel

### Model Download Fails

If model download fails:
1. Check internet connection
2. Verify HuggingFace is accessible
3. Try alternative mirror:
   ```bash
   export HF_ENDPOINT=https://hf-mirror.com
   ```

### Slow Generation

For faster generation:
1. Use GPU (10x faster than CPU)
2. Reduce `num_inference_steps` to 30
3. Consider batch processing multiple images

## Quality Tips

- **Best results**: Clean, well-lit product images with simple backgrounds
- **Angle**: 30° provides good balance between subtle and dramatic
- **Steps**: 50 steps is a good quality/speed tradeoff
- **Post-processing**: Generated views can be enhanced with upscaling models

## API Integration

The generated views are automatically:
1. Saved to MinIO storage under `images/{session_id}/views/`
2. Linked in the database (`left_view_key`, `right_view_key`)
3. Accessible via the product API endpoints

## Future Enhancements

Potential improvements:
- Multiple view angles (top, bottom, isometric)
- Batch processing for faster ingestion
- Quality assessment and automatic retry
- Custom fine-tuning on furniture datasets
- Interactive view angle selection via API
