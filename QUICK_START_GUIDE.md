# Quick Start Guide - Multi-Angle Side Views

## 📸 What You'll See

After uploading a PDF catalog, each product card will display:

### Main Product Section
- Product image or collage
- Product information (SKU, name, dimensions)

### Side Views Section (NEW! 🎉)
**Collapsible Button:**
```
▶ 🔄 Side Views (6 angles)
```

**When Expanded:**
```
▼ 🔄 Side Views (6 angles)

┌─────────────────────────────────┐
│      15° Views                  │
├──────────────┬──────────────────┤
│   [Image]    │    [Image]       │
│   ← Left     │    Right →       │
└──────────────┴──────────────────┘

┌─────────────────────────────────┐
│      30° Views                  │
├──────────────┬──────────────────┤
│   [Image]    │    [Image]       │
│   ← Left     │    Right →       │
└──────────────┴──────────────────┘

┌─────────────────────────────────┐
│      45° Views                  │
├──────────────┬──────────────────┤
│   [Image]    │    [Image]       │
│   ← Left     │    Right →       │
└──────────────┴──────────────────┘
```

## 🎬 How It Works

1. **Upload PDF** → Click "Upload PDF Catalog" and select a file
2. **Processing** → Zero123 generates 6 views per product:
   - Left 15°, Right 15°
   - Left 30°, Right 30°
   - Left 45°, Right 45°
3. **View Results** → Click "Side Views" button to expand/collapse
4. **Interact** → Hover over images for zoom effect

## ⏱️ Timeline

```
Upload PDF (1s)
    ↓
Parse Pages (2-5s per page)
    ↓
Extract Images (1s per page)
    ↓
Generate Views (30-60s per product) ← NEW: 6 views instead of 2
    ↓
Upload to MinIO (2s per product)
    ↓
Save to Database (1s)
    ↓
Display in Catalog ✅
```

## 🎯 Angle Comparison

### 15° - Subtle Angle
- Small perspective shift
- Good for showing minor details
- Minimal distortion

### 30° - Medium Angle
- Balanced view
- Shows side features clearly
- Most commonly used

### 45° - Pronounced Angle
- Strong perspective
- Shows deep side features
- Maximum viewing range

## 💡 Tips

### For Best Results:
- ✅ Use clear, high-resolution product images in PDF
- ✅ Single products per page work best
- ✅ Center products in frame
- ✅ Avoid cluttered backgrounds

### Performance:
- ⚡ GPU recommended (NVIDIA with CUDA)
- 💻 CPU works but slower
- 🎚️ Adjust `num_inference_steps` for speed vs quality balance

### Troubleshooting:
- If views don't appear → Check `ZERO123_ENABLED=true`
- If slow → Reduce `num_inference_steps` to 30
- If errors → Check logs for model loading issues

## 🔧 Customization Examples

### Change to Different Angles
```python
# In app/ingestion.py
angles_to_generate = [10.0, 25.0, 40.0, 60.0]  # 4 angles instead of 3
```

### Speed vs Quality Trade-off
```python
# Fast (lower quality)
num_inference_steps=30

# Balanced (recommended)
num_inference_steps=50

# High quality (slower)
num_inference_steps=75
```

### Disable Specific Angles
```python
# Only generate 30° views
angles_to_generate = [30.0]
```

## 📱 Mobile & Desktop

The UI is fully responsive:

**Desktop:**
- Views displayed in 2-column grid
- Larger preview images
- Smooth hover effects

**Mobile:**
- Single column layout
- Touch-friendly buttons
- Optimized image loading

## 🎨 Customizing the UI

### Change Colors
Edit `frontend/src/components/ProductList.css`:
```css
.angle-label {
  color: #667eea;  /* Change accent color */
}

.side-views-toggle:hover {
  border-color: #667eea;  /* Change hover color */
}
```

### Change Image Sizes
```css
.side-view-image {
  height: 120px;  /* Adjust height */
}
```

### Change Animation
```css
@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);  /* Adjust slide distance */
  }
}
```

## 📊 Data Structure

### Database (SQLite)
```sql
products table:
  - side_views_keys: TEXT (JSON)
    Stores: {"left_15": "path", "right_15": "path", ...}
```

### API Response
```json
{
  "side_views_urls": {
    "left_15": "https://minio.../presigned-url",
    "right_15": "https://minio.../presigned-url",
    "left_30": "https://minio.../presigned-url",
    "right_30": "https://minio.../presigned-url",
    "left_45": "https://minio.../presigned-url",
    "right_45": "https://minio.../presigned-url"
  }
}
```

### Frontend State
```javascript
const [expandedViews, setExpandedViews] = useState({
  "product-id-1": true,   // Expanded
  "product-id-2": false   // Collapsed
})
```

## 🚀 Deploy to Production

1. **Build Frontend:**
   ```bash
   cd frontend
   npm run build
   ```

2. **Set Environment:**
   ```bash
   export ZERO123_ENABLED=true
   export DATABASE_URL=postgresql://...
   ```

3. **Run Migration:**
   ```bash
   python migrate_add_side_views.py
   ```

4. **Start Backend:**
   ```bash
   python -m app.main
   ```

## 📈 Monitoring

Check generation status in logs:
```
✅ Left 15° view generated
✅ Right 15° view generated
✅ Left 30° view generated
✅ Right 30° view generated
✅ Left 45° view generated
✅ Right 45° view generated
✅ Uploaded 6 angle views
```

View generation status in database:
```python
product.view_generation_status
# 'success' | 'partial_success' | 'failed' | 'disabled'
```
