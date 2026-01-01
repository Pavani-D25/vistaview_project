"""
Test script for Zero123 view generation
Run this after ingesting a PDF to verify Zero123 is working
"""
import sys
from pathlib import Path
from PIL import Image

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.zero123_generator import generate_side_views


def test_zero123(image_path: str, output_dir: str = "test_output"):
    """
    Test Zero123 view generation on a single image
    
    Args:
        image_path: Path to input image
        output_dir: Directory to save generated views
    """
    print(f"🧪 Testing Zero123 with image: {image_path}")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Load image
    print("📷 Loading image...")
    image = Image.open(image_path)
    print(f"   Image size: {image.size}")
    
    # Generate views
    print("\n🔄 Generating left and right views...")
    left_view, right_view, status = generate_side_views(
        image=image,
        angle=30.0,
        use_zero123=True,
        num_inference_steps=50,
    )
    
    # Check results
    print(f"\n📊 Generation status: {status}")
    
    if left_view:
        left_path = output_path / "left_view.jpg"
        left_view.save(left_path, quality=95)
        print(f"✅ Left view saved: {left_path}")
    else:
        print("❌ Left view generation failed")
    
    if right_view:
        right_path = output_path / "right_view.jpg"
        right_view.save(right_path, quality=95)
        print(f"✅ Right view saved: {right_path}")
    else:
        print("❌ Right view generation failed")
    
    # Save original for comparison
    original_path = output_path / "original.jpg"
    image.save(original_path, quality=95)
    print(f"💾 Original saved: {original_path}")
    
    print("\n✨ Test complete!")
    return left_view is not None and right_view is not None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_zero123.py <image_path> [output_dir]")
        print("\nExample:")
        print("  python test_zero123.py backend/data/images/session_id/product.jpg")
        sys.exit(1)
    
    image_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "test_output"
    
    success = test_zero123(image_path, output_dir)
    sys.exit(0 if success else 1)
