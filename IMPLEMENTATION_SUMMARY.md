# Multi-Angle Side Views - Implementation Summary

## ✅ Completed Changes

### 1. Backend - Zero123 Generator (`app/zero123_generator.py`)
- ✅ Added `generate_multi_angle_views()` method to generate views at multiple angles
- ✅ Added `generate_multi_angle_side_views()` high-level function for easy integration
- ✅ Maintains backward compatibility with existing single-angle generation

### 2. Backend - Database Models (`app/models.py`)
- ✅ Added `side_views_keys` column (Text/JSON) to store all angle view keys
- ✅ Keeps legacy `left_view_key` and `right_view_key` columns for compatibility

### 3. Backend - Schemas (`app/schemas.py`)
- ✅ Added `side_views_urls` field (Dict[str, str]) to `ProductOut` schema
- ✅ Returns presigned URLs for all generated angle views

### 4. Backend - Ingestion (`app/ingestion.py`)
- ✅ Added `generate_multi_angle_views()` function
- ✅ Modified `ingest_pdf()` to generate views at 15°, 30°, and 45°
- ✅ Organizes uploads in subfolder structure: `images/{session}/views/{angle}deg/`
- ✅ Stores view keys as JSON in database
- ✅ Maintains backward compatibility with legacy view keys

### 5. Backend - API Routes (`app/routes/products.py`)
- ✅ Added JSON parsing for `side_views_keys` column
- ✅ Generates presigned URLs for all angle views
- ✅ Returns `side_views_urls` in API responses

### 6. Frontend - Product List Component (`frontend/src/components/ProductList.jsx`)
- ✅ Added expandable side views section to product cards
- ✅ Displays views grouped by angle (15°, 30°, 45°)
- ✅ Shows left/right pairs for each angle
- ✅ Toggle button to expand/collapse views
- ✅ State management for expanded views

### 7. Frontend - Styling (`frontend/src/components/ProductList.css`)
- ✅ Added comprehensive styling for side views section
- ✅ Toggle button with hover effects
- ✅ Slide-down animation for expanding views
- ✅ Responsive grid layout for angle groups
- ✅ Hover effects on side view images

### 8. Documentation
- ✅ Created `MULTI_ANGLE_VIEWS.md` with feature documentation
- ✅ Created `migrate_add_side_views.py` for database migration

## 📁 MinIO Folder Structure

Views are now organized as:
```
vistaview-catalog/
  images/
    {session_id}/
      {sku}_page_main.jpg              # Main product image
      views/
        15deg/
          {sku}_page_left_15.jpg       # 15° left view
          {sku}_page_right_15.jpg      # 15° right view
        30deg/
          {sku}_page_left_30.jpg       # 30° left view
          {sku}_page_right_30.jpg      # 30° right view
        45deg/
          {sku}_page_left_45.jpg       # 45° left view
          {sku}_page_right_45.jpg      # 45° right view
```

## 🔄 Database Schema Changes

```sql
ALTER TABLE products ADD COLUMN side_views_keys TEXT;
```

Stores JSON like:
```json
{
  "left_15": "images/session/views/15deg/sku_left_15.jpg",
  "right_15": "images/session/views/15deg/sku_right_15.jpg",
  "left_30": "images/session/views/30deg/sku_left_30.jpg",
  "right_30": "images/session/views/30deg/sku_right_30.jpg",
  "left_45": "images/session/views/45deg/sku_left_45.jpg",
  "right_45": "images/session/views/45deg/sku_right_45.jpg"
}
```

## 🎯 Key Features

1. **Multiple Angles**: Generates 6 views per product (3 left + 3 right at different angles)
2. **Organized Storage**: Views stored in angle-specific subfolders
3. **Expandable UI**: Clean, collapsible interface to view all angles
4. **Backward Compatible**: Existing 30° views still available via legacy fields
5. **Easy Configuration**: Change angles by editing array in ingestion.py

## 🚀 Next Steps to Use

1. **Restart Backend**: The new column will be auto-created
   ```bash
   python -m app.main
   ```

2. **Or Run Migration** (for existing databases with data):
   ```bash
   python migrate_add_side_views.py
   ```

3. **Upload a PDF**: Process through the frontend

4. **View Results**: Expand the "Side Views" section on product cards

## ⚙️ Configuration Options

### Change Angles
Edit `app/ingestion.py` line ~425:
```python
angles_to_generate = [15.0, 30.0, 45.0]  # Customize angles here
```

### Change Generation Quality
Edit `app/ingestion.py` line ~446:
```python
num_inference_steps=50,  # 30-75 range (higher = better but slower)
```

### Enable/Disable Zero123
Set environment variable:
```bash
ZERO123_ENABLED=true  # or false to disable
```

## 📊 Performance Impact

- **Generation Time**: ~30-60 seconds per product (6 views)
- **Previous**: ~10-20 seconds per product (2 views)
- **Storage**: ~3x more images stored in MinIO
- **Processing**: Sequential generation to manage GPU memory

## 🎨 UI Features

- **Collapsible Views**: Click to expand/collapse
- **Organized Display**: Views grouped by angle
- **Smooth Animation**: Slide-down effect when expanding
- **Hover Effects**: Images scale on hover with shadow
- **Responsive**: Works on all screen sizes
- **Count Badge**: Shows number of views available

## ✨ Benefits

1. **Better Product Visualization**: Customers see products from multiple perspectives
2. **Professional Presentation**: Organized, clean interface
3. **Flexible**: Easy to add more angles or adjust existing ones
4. **Scalable**: Handles any number of angles efficiently
5. **Future-Ready**: Foundation for 360° viewer or AR features
