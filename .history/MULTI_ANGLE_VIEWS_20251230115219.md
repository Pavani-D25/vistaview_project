# Multi-Angle Side Views Feature

This feature enhances VistaView to generate and display multiple side-angle views of product images using Zero123.

## 🎯 What's New

Previously, VistaView generated only left and right views at 30°. Now it generates **multiple angle views**:
- **15° views** - Subtle angle change
- **30° views** - Medium angle change  
- **45° views** - Pronounced angle change

All views are saved in an organized subfolder structure and displayed in the product catalog.

## 📁 Folder Structure

Side views are now organized by angle in MinIO:
```
images/
  {session_id}/
    views/
      15deg/
        {sku}_page_left_15.jpg
        {sku}_page_right_15.jpg
      30deg/
        {sku}_page_left_30.jpg
        {sku}_page_right_30.jpg
      45deg/
        {sku}_page_left_45.jpg
        {sku}_page_right_45.jpg
```

## 🔧 Implementation Details

### Backend Changes

1. **zero123_generator.py**
   - Added `generate_multi_angle_views()` method to generate views at multiple angles
   - Added `generate_multi_angle_side_views()` high-level function

2. **models.py**
   - Added `side_views_keys` column (JSON) to store all angle view keys
   - Maintains backward compatibility with `left_view_key` and `right_view_key`

3. **ingestion.py**
   - Updated to generate views at 15°, 30°, and 45°
   - Organizes uploads in angle-specific subfolders
   - Stores view keys as JSON in database

4. **routes/products.py**
   - Parses `side_views_keys` JSON
   - Generates presigned URLs for all angle views
   - Returns `side_views_urls` dictionary in API response

### Frontend Changes

1. **ProductList.jsx**
   - Added side views section to product cards
   - Displays views grouped by angle (15°, 30°, 45°)
   - Shows left/right pairs for each angle

2. **ProductList.css**
   - Added styling for side views grid
   - Hover effects for side view images
   - Responsive layout for angle groups

## 🗄️ Database Migration

If you have an existing database, run the migration script:

```bash
python migrate_add_side_views.py
```

Or simply restart the backend - the new column will be added automatically via SQLAlchemy.

## 🚀 Usage

1. **Upload a PDF catalog** through the frontend
2. **Wait for processing** - Zero123 will generate 6 views per product (3 left + 3 right)
3. **View the results** - Product cards now show all angle views organized by degree

## ⚙️ Configuration

Control Zero123 generation via environment variables:

```bash
# Enable/disable Zero123
ZERO123_ENABLED=true

# Adjust generation quality (30-75 steps)
# Higher = better quality but slower
# Default is 50 in the code
```

## 🎨 Customizing Angles

To change which angles are generated, edit `app/ingestion.py`:

```python
# Line ~425
angles_to_generate = [15.0, 30.0, 45.0]  # Change these values
```

Supported range: 0-90 degrees

## 📊 API Response Format

Products now include a `side_views_urls` field:

```json
{
  "id": "...",
  "sku_code": "ABC-123",
  "side_views_urls": {
    "left_15": "https://minio.../left_15.jpg",
    "right_15": "https://minio.../right_15.jpg",
    "left_30": "https://minio.../left_30.jpg",
    "right_30": "https://minio.../right_30.jpg",
    "left_45": "https://minio.../left_45.jpg",
    "right_45": "https://minio.../right_45.jpg"
  }
}
```

## 🔍 Troubleshooting

**Views not generating?**
- Check Zero123 is enabled: `ZERO123_ENABLED=true`
- Check GPU availability: `torch.cuda.is_available()`
- Check logs for model loading errors

**Database errors?**
- Run migration script: `python migrate_add_side_views.py`
- Or delete `vistaview.db` and restart (data will be lost)

**Frontend not showing views?**
- Check browser console for errors
- Verify API returns `side_views_urls` field
- Clear browser cache and reload

## 💡 Performance Notes

- Generating 6 views per product takes ~2-3x longer than generating 2 views
- Total processing time: ~30-60 seconds per product on GPU
- CPU processing is much slower (not recommended for production)
- Views are generated sequentially to manage memory

## 🎯 Future Enhancements

Possible improvements:
- Interactive 360° viewer with angle slider
- Top/bottom views (elevation angles)
- Batch processing optimization
- View caching and regeneration
- Quality presets (fast/balanced/quality)
