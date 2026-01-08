"""
Test script for production pipeline
Tests depth estimation, mesh reconstruction, and rendering
"""
import sys
import time
from pathlib import Path
from PIL import Image

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.production_pipeline import generate_production_views


def test_production_pipeline(image_path: str, output_dir: str = "test_output"):
    """
    Test the complete production pipeline
    
    Args:
        image_path: Path to test product image
        output_dir: Directory to save output images
    """
    print("=" * 70)
    print("🧪 TESTING PRODUCTION PIPELINE")
    print("=" * 70)
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Load test image
    print(f"\n📷 Loading image: {image_path}")
    try:
        image = Image.open(image_path).convert('RGB')
        print(f"   ✅ Image loaded: {image.size} ({image.mode})")
    except Exception as e:
        print(f"   ❌ Failed to load image: {e}")
        return False
    
    # Test 1: Without dimensions
    print("\n" + "=" * 70)
    print("TEST 1: Basic Pipeline (No Dimension Scaling)")
    print("=" * 70)
    
    start_time = time.time()
    views1, status1 = generate_production_views(
        image=image,
        real_dimensions=None,
        angles=[0, 15, 30, -30],
        use_triposr=True,
        render_size=(512, 512)
    )
    test1_time = time.time() - start_time
    
    print(f"\n📊 Test 1 Results:")
    print(f"   Status: {status1}")
    print(f"   Views generated: {len(views1)}")
    print(f"   Time: {test1_time:.2f}s")
    
    # Save views
    if views1:
        for view_name, view_img in views1.items():
            output_file = output_path / f"test1_{view_name}.png"
            view_img.save(output_file)
            print(f"   💾 Saved: {output_file}")
    
    # Test 2: With dimension scaling
    print("\n" + "=" * 70)
    print("TEST 2: With Dimension Scaling")
    print("=" * 70)
    
    # Example furniture dimensions (sofa)
    test_dimensions = (2000, 900, 850)  # L×W×H in mm
    print(f"   Using dimensions: {test_dimensions[0]}×{test_dimensions[1]}×{test_dimensions[2]} mm")
    
    start_time = time.time()
    views2, status2 = generate_production_views(
        image=image,
        real_dimensions=test_dimensions,
        angles=[15, 30, 45, -15, -30, -45],
        use_triposr=True,
        render_size=(512, 512)
    )
    test2_time = time.time() - start_time
    
    print(f"\n📊 Test 2 Results:")
    print(f"   Status: {status2}")
    print(f"   Views generated: {len(views2)}")
    print(f"   Time: {test2_time:.2f}s")
    
    # Save views
    if views2:
        for view_name, view_img in views2.items():
            output_file = output_path / f"test2_{view_name}.png"
            view_img.save(output_file)
            print(f"   💾 Saved: {output_file}")
    
    # Test 3: High resolution
    print("\n" + "=" * 70)
    print("TEST 3: High Resolution Rendering (1024×1024)")
    print("=" * 70)
    
    start_time = time.time()
    views3, status3 = generate_production_views(
        image=image,
        real_dimensions=test_dimensions,
        angles=[0, 30],
        use_triposr=True,
        render_size=(1024, 1024)
    )
    test3_time = time.time() - start_time
    
    print(f"\n📊 Test 3 Results:")
    print(f"   Status: {status3}")
    print(f"   Views generated: {len(views3)}")
    print(f"   Time: {test3_time:.2f}s")
    
    # Save views
    if views3:
        for view_name, view_img in views3.items():
            output_file = output_path / f"test3_highres_{view_name}.png"
            view_img.save(output_file)
            print(f"   💾 Saved: {output_file}")
    
    # Summary
    print("\n" + "=" * 70)
    print("📈 SUMMARY")
    print("=" * 70)
    print(f"Test 1 (Basic):        {status1:20s} - {test1_time:6.2f}s - {len(views1)} views")
    print(f"Test 2 (Scaled):       {status2:20s} - {test2_time:6.2f}s - {len(views2)} views")
    print(f"Test 3 (High-res):     {status3:20s} - {test3_time:6.2f}s - {len(views3)} views")
    print("=" * 70)
    
    success = all([
        status1 == "success",
        status2 == "success",
        status3 == "success",
        len(views1) > 0,
        len(views2) > 0,
        len(views3) > 0
    ])
    
    if success:
        print("\n✅ ALL TESTS PASSED")
    else:
        print("\n⚠️  SOME TESTS FAILED")
    
    print(f"\n📁 Output directory: {output_path.absolute()}")
    
    return success


def test_individual_components():
    """Test individual pipeline components"""
    print("\n" + "=" * 70)
    print("🔧 TESTING INDIVIDUAL COMPONENTS")
    print("=" * 70)
    
    # Test 1: Depth Estimator
    print("\n1️⃣ Testing Depth Estimator...")
    try:
        from app.depth_estimator import get_depth_estimator
        
        estimator = get_depth_estimator()
        print("   ✅ Depth estimator initialized")
        
        # Create test image
        test_img = Image.new('RGB', (256, 256), (128, 128, 128))
        depth_map = estimator.estimate_depth(test_img)
        
        print(f"   ✅ Depth map generated: shape={depth_map.shape}")
        
    except Exception as e:
        print(f"   ❌ Depth estimator failed: {e}")
    
    # Test 2: Mesh Reconstructor
    print("\n2️⃣ Testing Mesh Reconstructor...")
    try:
        from app.mesh_reconstructor import get_mesh_reconstructor
        import numpy as np
        
        reconstructor = get_mesh_reconstructor()
        print("   ✅ Mesh reconstructor initialized")
        
        # Create test data
        test_img = Image.new('RGB', (256, 256), (128, 128, 128))
        test_depth = np.random.rand(256, 256).astype(np.float32)
        
        mesh = reconstructor.reconstruct_mesh_from_depth(test_img, test_depth)
        
        print(f"   ✅ Mesh generated: {len(mesh.vertices)} vertices")
        
    except Exception as e:
        print(f"   ❌ Mesh reconstructor failed: {e}")
    
    # Test 3: Mesh Renderer
    print("\n3️⃣ Testing Mesh Renderer...")
    try:
        from app.mesh_renderer import get_mesh_renderer
        import trimesh
        
        renderer = get_mesh_renderer()
        print("   ✅ Mesh renderer initialized")
        
        # Create test mesh (simple cube)
        test_mesh = trimesh.creation.box(extents=[1, 1, 1])
        
        view = renderer.render_view_simple(test_mesh, camera_angle=30)
        
        print(f"   ✅ View rendered: {view.size}")
        
    except Exception as e:
        print(f"   ❌ Mesh renderer failed: {e}")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test production pipeline")
    parser.add_argument(
        "image_path",
        nargs="?",
        help="Path to test image (optional)"
    )
    parser.add_argument(
        "--output-dir",
        default="test_output",
        help="Output directory for test results"
    )
    parser.add_argument(
        "--components-only",
        action="store_true",
        help="Only test individual components"
    )
    
    args = parser.parse_args()
    
    if args.components_only:
        test_individual_components()
    elif args.image_path:
        success = test_production_pipeline(args.image_path, args.output_dir)
        sys.exit(0 if success else 1)
    else:
        print("=" * 70)
        print("Production Pipeline Test Suite")
        print("=" * 70)
        print("\nUsage:")
        print("  python test_production_pipeline.py <image_path>")
        print("  python test_production_pipeline.py --components-only")
        print("\nExample:")
        print("  python test_production_pipeline.py sofa.jpg")
        print("  python test_production_pipeline.py chair.png --output-dir results")
        print("\nThis will:")
        print("  1. Test depth estimation (MiDaS)")
        print("  2. Test mesh reconstruction (TripoSR)")
        print("  3. Test dimension scaling")
        print("  4. Test multi-angle rendering")
        print("  5. Save output images to test_output/")
        print("=" * 70)
