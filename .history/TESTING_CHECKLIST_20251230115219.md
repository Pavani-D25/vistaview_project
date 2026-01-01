# Testing Checklist - Multi-Angle Side Views Feature

Use this checklist to verify the feature is working correctly.

## ✅ Pre-Testing Setup

- [ ] Backend is running (`python -m app.main`)
- [ ] Frontend is running (`npm run dev` in frontend folder)
- [ ] MinIO is accessible (check Docker if using docker-compose)
- [ ] Database exists (auto-created on first run)
- [ ] `ZERO123_ENABLED=true` environment variable is set
- [ ] GPU is available (optional but recommended): Check with `torch.cuda.is_available()`

## 🧪 Test 1: Database Schema

**Objective:** Verify new column exists

```bash
# Option 1: Run migration script
python migrate_add_side_views.py

# Option 2: Check manually (if using SQLite)
sqlite3 vistaview.db
> .schema products
> # Look for: side_views_keys TEXT
> .quit
```

**Expected Result:**
- ✅ `side_views_keys` column exists in products table
- ✅ No migration errors

## 🧪 Test 2: Backend API Response

**Objective:** Verify API includes new fields

1. Upload a test PDF through the frontend
2. Wait for processing to complete
3. Check API response:

```bash
# Get products list
curl http://localhost:8000/api/products | jq

# Look for:
{
  "products": [
    {
      "side_views_urls": {
        "left_15": "https://...",
        "right_15": "https://...",
        "left_30": "https://...",
        "right_30": "https://...",
        "left_45": "https://...",
        "right_45": "https://..."
      }
    }
  ]
}
```

**Expected Result:**
- ✅ `side_views_urls` field exists in response
- ✅ Contains 6 URLs (if all views generated successfully)
- ✅ URLs are presigned and accessible

## 🧪 Test 3: MinIO Storage Structure

**Objective:** Verify files stored in correct folders

Check MinIO structure (via MinIO Console or CLI):

```
vistaview-catalog/
  images/
    {session_id}/
      views/
        15deg/
        30deg/
        45deg/
```

**Expected Result:**
- ✅ Three angle folders created (15deg, 30deg, 45deg)
- ✅ Each folder contains left and right images
- ✅ Files are accessible via presigned URLs

## 🧪 Test 4: View Generation

**Objective:** Verify Zero123 generates views correctly

Check backend logs during PDF upload:

```
🔄 Generating multi-angle Zero123 views for SKU-123 at [15.0, 30.0, 45.0]°...
   ✅ Left 15° view generated
   ✅ Right 15° view generated
   ✅ Left 30° view generated
   ✅ Right 30° view generated
   ✅ Left 45° view generated
   ✅ Right 45° view generated
   ✅ Uploaded 6 angle views
```

**Expected Result:**
- ✅ All 6 views generated successfully
- ✅ No CUDA errors (if using GPU)
- ✅ Processing completes in reasonable time (~30-60s per product on GPU)

## 🧪 Test 5: Frontend Display

**Objective:** Verify UI shows views correctly

1. Open frontend in browser
2. Upload PDF and wait for processing
3. Check product cards:

**Expected Result:**
- ✅ Product cards show main image
- ✅ "🔄 Side Views (6 angles)" button appears
- ✅ Button shows correct count
- ✅ Clicking button expands/collapses views

## 🧪 Test 6: Expandable UI

**Objective:** Verify toggle functionality

1. Click "Side Views" button on a product
2. Verify expansion
3. Click again to collapse

**Expected Result:**
- ✅ Views expand with slide-down animation
- ✅ Toggle icon changes (▶ to ▼)
- ✅ Views collapse smoothly
- ✅ State persists during scrolling

## 🧪 Test 7: View Display

**Objective:** Verify all angles display correctly

When views are expanded:

**Expected Result:**
- ✅ Three angle groups visible (15°, 30°, 45°)
- ✅ Each group shows left and right images
- ✅ Images load correctly (no broken links)
- ✅ Labels show "← Left" and "Right →"
- ✅ Hover effect works (image scales up)

## 🧪 Test 8: Image Quality

**Objective:** Verify generated views look realistic

Compare the generated views with the original image:

**Expected Result:**
- ✅ Views show product from side angles
- ✅ No major distortions or artifacts
- ✅ Proportions look natural
- ✅ Different angles are distinguishable

## 🧪 Test 9: Backward Compatibility

**Objective:** Verify legacy fields still work

Check API response for legacy fields:

```json
{
  "left_view_url": "https://...",  // Should be 30° left view
  "right_view_url": "https://..."  // Should be 30° right view
}
```

**Expected Result:**
- ✅ Legacy fields still populated
- ✅ Point to 30° views
- ✅ Existing code using these fields still works

## 🧪 Test 10: Error Handling

**Objective:** Verify graceful degradation

Test scenarios:
1. **Zero123 disabled:** Set `ZERO123_ENABLED=false`
2. **No GPU:** Test on CPU-only machine
3. **Model load failure:** Remove model cache

**Expected Result:**
- ✅ App doesn't crash
- ✅ Status shows 'disabled' or 'failed' appropriately
- ✅ Products still created without views
- ✅ Frontend handles missing `side_views_urls` gracefully

## 🧪 Test 11: Performance

**Objective:** Measure generation time

Upload a PDF with 3 products:

**Expected Result:**
- ✅ Processing completes in reasonable time
- ✅ GPU: ~30-60s per product
- ✅ CPU: ~2-5 minutes per product
- ✅ No memory errors or crashes

## 🧪 Test 12: Pagination

**Objective:** Verify views work with pagination

Upload enough products to trigger pagination (>20):

**Expected Result:**
- ✅ All pages load correctly
- ✅ Side views work on all pages
- ✅ Expanded state doesn't affect pagination
- ✅ URLs refresh correctly on page change

## 🧪 Test 13: Search Functionality

**Objective:** Verify search works with new feature

1. Upload products
2. Search by SKU or name
3. Check if side views appear

**Expected Result:**
- ✅ Search returns correct products
- ✅ Side views load for search results
- ✅ No performance degradation

## 🧪 Test 14: Mobile Responsiveness

**Objective:** Verify UI works on mobile

Open in mobile browser or use DevTools mobile emulation:

**Expected Result:**
- ✅ Product cards stack vertically
- ✅ Side views button is touch-friendly
- ✅ Images scale appropriately
- ✅ No horizontal scrolling
- ✅ Toggle works smoothly

## 🧪 Test 15: Multiple Sessions

**Objective:** Verify session isolation

1. Upload PDF #1
2. Upload PDF #2
3. Check both sessions

**Expected Result:**
- ✅ Each session has unique ID
- ✅ Views stored in separate folders
- ✅ No cross-contamination
- ✅ Both sessions display correctly

## 🐛 Common Issues & Solutions

### Issue: "side_views_urls is null"
**Solution:** 
- Run migration: `python migrate_add_side_views.py`
- Or restart backend to auto-create column

### Issue: "Views not generating"
**Solution:**
- Check `ZERO123_ENABLED=true`
- Verify Zero123 model installed
- Check GPU availability

### Issue: "Images not loading"
**Solution:**
- Verify MinIO is running
- Check presigned URL generation
- Verify bucket permissions

### Issue: "Slow generation"
**Solution:**
- Use GPU if available
- Reduce `num_inference_steps` to 30
- Consider generating fewer angles

### Issue: "Toggle not working"
**Solution:**
- Check browser console for JS errors
- Verify React state management
- Clear browser cache

## 📊 Test Results Template

```
Date: ___________
Tester: ___________

Backend Tests:
[ ] Test 1: Database Schema
[ ] Test 2: API Response
[ ] Test 3: MinIO Storage
[ ] Test 4: View Generation
[ ] Test 10: Error Handling
[ ] Test 11: Performance

Frontend Tests:
[ ] Test 5: Display
[ ] Test 6: Toggle UI
[ ] Test 7: View Display
[ ] Test 8: Image Quality
[ ] Test 14: Mobile

Integration Tests:
[ ] Test 9: Backward Compatibility
[ ] Test 12: Pagination
[ ] Test 13: Search
[ ] Test 15: Multiple Sessions

Notes:
_________________________________
_________________________________
_________________________________
```

## ✅ Sign-Off

Feature is ready for production when:
- [ ] All 15 tests pass
- [ ] No critical bugs
- [ ] Performance acceptable
- [ ] Documentation complete
- [ ] Code reviewed

---

**Happy Testing! 🎉**
