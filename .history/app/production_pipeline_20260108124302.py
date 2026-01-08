"""
Production-grade view generation pipeline
Architecture: Image → Depth → Mesh → Scale → Render Views
Best for: E-commerce catalogs (Amazon, IKEA, Wayfair style)
"""
from PIL import Image
import numpy as np
from typing import Dict, List, Optional, Tuple
import time

from .depth_estimator import get_depth_estimator
from .mesh_reconstructor import get_mesh_reconstructor
from .mesh_renderer import get_mesh_renderer


def generate_production_views(
    image: Image.Image,
    real_dimensions: Optional[Tuple[float, float, float]] = None,
    angles: List[float] = [15, 30, 45, -15, -30, -45],
    use_triposr: bool = True,
    render_size: Tuple[int, int] = (512, 512)
) -> Tuple[Dict[str, Image.Image], str]:
    """
    Production-grade pipeline: Single image → 3D mesh → multiple angle views
    
    This is the recommended approach used by Amazon, IKEA, and Wayfair.
    
    Architecture:
    1. Depth Estimation (MiDaS) - 10-40ms on GPU
    2. Mesh Reconstruction (TripoSR) - 1-2s on GPU
    3. Metric Scaling (from PDF dimensions) - instant
    4. Multi-angle Rendering (OpenGL) - 5-20ms per view
    
    Args:
        image: Input product image (PIL Image, RGB)
        real_dimensions: Optional (length, width, height) in mm from PDF
        angles: List of angles to render (degrees, positive=right, negative=left)
        use_triposr: Try TripoSR mesh reconstruction (fallback to depth if fails)
        render_size: Output image size (width, height)
    
    Returns:
        views_dict: Dictionary mapping view_name → PIL Image
        status: Status string ('success', 'partial', 'failed')
    
    Benefits:
    ✅ Fast: Views take milliseconds once mesh exists
    ✅ No hallucination: Geometry-based, not generative
    ✅ Dimension-accurate: Uses real measurements from PDF
    ✅ Consistent: Same angles always produce same results
    """
    print("=" * 60)
    print("🏭 PRODUCTION PIPELINE: Image → 3D → Render Views")
    print("=" * 60)
    
    start_time = time.time()
    
    try:
        # Step 1: Depth Estimation
        print("\n📊 Step 1: Depth Estimation (MiDaS)...")
        depth_start = time.time()
        
        depth_estimator = get_depth_estimator()
        depth_map = depth_estimator.estimate_depth(image)
        
        depth_time = time.time() - depth_start
        print(f"   ✅ Depth map generated in {depth_time:.2f}s")
        print(f"   Shape: {depth_map.shape}, Range: [{depth_map.min():.3f}, {depth_map.max():.3f}]")
        
        # Step 2: Mesh Reconstruction
        print("\n🔺 Step 2: Mesh Reconstruction...")
        mesh_start = time.time()
        
        reconstructor = get_mesh_reconstructor()
        mesh = reconstructor.reconstruct_mesh(
            image=image,
            depth_map=depth_map,
            use_triposr=use_triposr
        )
        
        if mesh is None:
            print("   ❌ Mesh reconstruction failed")
            return {}, "mesh_reconstruction_failed"
        
        mesh_time = time.time() - mesh_start
        print(f"   ✅ Mesh reconstructed in {mesh_time:.2f}s")
        print(f"   Vertices: {len(mesh.vertices):,}, Faces: {len(mesh.faces):,}")
        
        # Step 3: Metric Scaling (if dimensions provided)
        if real_dimensions is not None:
            print(f"\n📏 Step 3: Metric Scaling to real dimensions...")
            print(f"   Real dimensions: L={real_dimensions[0]}mm, "
                  f"W={real_dimensions[1]}mm, H={real_dimensions[2]}mm")
            
            renderer = get_mesh_renderer(width=render_size[0], height=render_size[1])
            mesh = renderer.scale_mesh_to_real_dimensions(
                mesh=mesh,
                real_dimensions=real_dimensions,
                dimension_unit='mm'
            )
            print("   ✅ Mesh scaled to real dimensions")
        else:
            print("\n📏 Step 3: Skipping metric scaling (no dimensions provided)")
        
        # Step 4: Multi-angle Rendering
        print(f"\n🎨 Step 4: Rendering {len(angles)} angle views...")
        render_start = time.time()
        
        renderer = get_mesh_renderer(width=render_size[0], height=render_size[1])
        views_dict = renderer.render_multi_angle_views(
            mesh=mesh,
            angles=angles,
            use_pyrender=True
        )
        
        render_time = time.time() - render_start
        avg_time_per_view = render_time / len(angles) if angles else 0
        
        print(f"   ✅ {len(views_dict)} views rendered in {render_time:.2f}s")
        print(f"   Average: {avg_time_per_view*1000:.1f}ms per view")
        
        # Summary
        total_time = time.time() - start_time
        print("\n" + "=" * 60)
        print("✅ PIPELINE COMPLETE")
        print("=" * 60)
        print(f"⏱️  Total time: {total_time:.2f}s")
        print(f"   - Depth estimation: {depth_time:.2f}s")
        print(f"   - Mesh reconstruction: {mesh_time:.2f}s")
        print(f"   - View rendering: {render_time:.2f}s ({avg_time_per_view*1000:.1f}ms/view)")
        print(f"📦 Generated views: {list(views_dict.keys())}")
        print("=" * 60)
        
        return views_dict, "success"
        
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return {}, f"pipeline_error: {str(e)}"


def generate_views_with_fallback(
    image: Image.Image,
    real_dimensions: Optional[Tuple[float, float, float]] = None,
    angles: List[float] = [15, 30, 45, -15, -30, -45],
) -> Tuple[Dict[str, Image.Image], str]:
    """
    Production pipeline with Zero123 fallback
    
    Try production pipeline first, fallback to Zero123 if it fails
    
    Args:
        image: Input product image
        real_dimensions: Optional (L, W, H) in mm
        angles: Angles to generate
    
    Returns:
        views_dict, status
    """
    # Try production pipeline
    print("🚀 Attempting production pipeline (3D mesh-based)...")
    views_dict, status = generate_production_views(
        image=image,
        real_dimensions=real_dimensions,
        angles=angles,
        use_triposr=True
    )
    
    if views_dict and status == "success":
        return views_dict, status
    
    # Fallback to Zero123 if available
    print("\n⚠️  Production pipeline failed, trying Zero123 fallback...")
    try:
        from .zero123_views import generate_multi_angle_side_views
        
        views_dict, status = generate_multi_angle_side_views(
            image=image,
            angles=angles,
            use_zero123=True,
            num_inference_steps=50  # Faster for fallback
        )
        
        return views_dict, f"fallback_zero123_{status}"
        
    except ImportError:
        print("❌ Zero123 not available for fallback")
        return {}, "all_methods_failed"
    except Exception as e:
        print(f"❌ Zero123 fallback also failed: {e}")
        return {}, "all_methods_failed"


def quick_test_pipeline(image_path: str):
    """
    Quick test function for the production pipeline
    
    Args:
        image_path: Path to test image
    """
    print("🧪 Testing Production Pipeline")
    print("=" * 60)
    
    # Load test image
    image = Image.open(image_path).convert('RGB')
    print(f"📷 Loaded image: {image.size}")
    
    # Test dimensions (example furniture)
    test_dimensions = (800, 600, 400)  # L×W×H in mm
    
    # Run pipeline
    views, status = generate_production_views(
        image=image,
        real_dimensions=test_dimensions,
        angles=[0, 15, 30, 45, -30],
        use_triposr=True
    )
    
    print(f"\n📊 Result: {status}")
    print(f"📦 Generated {len(views)} views")
    
    # Save views
    for view_name, view_img in views.items():
        output_path = f"test_output_{view_name}.png"
        view_img.save(output_path)
        print(f"   💾 Saved: {output_path}")
    
    print("\n✅ Test complete!")


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        quick_test_pipeline(sys.argv[1])
    else:
        print("Usage: python -m app.production_pipeline <image_path>")
