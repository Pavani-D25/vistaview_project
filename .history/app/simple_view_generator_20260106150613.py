"""
Simple View Generator - No AI Models Required
Uses basic image transformations to create approximate side views
Zero downloads, fast processing, minimal memory
"""
import numpy as np
import cv2
from PIL import Image, ImageFilter, ImageEnhance
from typing import Optional, Dict, Tuple
from io import BytesIO


def remove_background_simple(image: Image.Image) -> Image.Image:
    """Simple background removal using color thresholding"""
    try:
        # Convert to numpy array
        img_array = np.array(image.convert('RGBA'))
        
        # Create mask for white/light backgrounds
        gray = cv2.cvtColor(img_array[:,:,:3], cv2.COLOR_RGB2GRAY)
        _, mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        
        # Apply morphological operations to clean up
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        # Apply mask to alpha channel
        img_array[:, :, 3] = mask
        
        return Image.fromarray(img_array, 'RGBA')
    except:
        return image.convert('RGBA')


def estimate_depth_simple(image: Image.Image) -> np.ndarray:
    """Estimate depth using simple heuristics"""
    # Convert to grayscale
    gray = np.array(image.convert('L'))
    
    # Use inverse intensity as depth (darker = further)
    depth = 255 - gray
    
    # Apply Gaussian blur for smoothing
    depth = cv2.GaussianBlur(depth, (9, 9), 0)
    
    # Normalize to 0-1 range
    depth = depth.astype(np.float32) / 255.0
    
    return depth


def create_perspective_transform(
    image: Image.Image,
    direction: str,
    angle: float = 30.0
) -> Optional[Image.Image]:
    """
    Create perspective view using simple transforms
    
    Args:
        image: Input PIL Image
        direction: 'left', 'right', 'top', or 'bottom'
        angle: Rotation angle (15-45 degrees)
    
    Returns:
        Transformed image
    """
    try:
        # Convert to RGBA
        img = image.convert('RGBA')
        width, height = img.size
        
        # Calculate transform parameters
        angle_rad = np.deg2rad(angle)
        shift_factor = np.sin(angle_rad) * 0.3
        
        # Define source points (corners of original image)
        src_points = np.float32([
            [0, 0],           # Top-left
            [width, 0],       # Top-right
            [width, height],  # Bottom-right
            [0, height]       # Bottom-left
        ])
        
        # Define destination points based on direction
        if direction == 'left':
            # Compress right side
            dst_points = np.float32([
                [width * shift_factor, 0],
                [width, height * shift_factor],
                [width, height * (1 - shift_factor)],
                [width * shift_factor, height]
            ])
        elif direction == 'right':
            # Compress left side
            dst_points = np.float32([
                [0, height * shift_factor],
                [width * (1 - shift_factor), 0],
                [width * (1 - shift_factor), height],
                [0, height * (1 - shift_factor)]
            ])
        elif direction == 'top':
            # Compress bottom
            dst_points = np.float32([
                [width * shift_factor, 0],
                [width * (1 - shift_factor), 0],
                [width, height],
                [0, height]
            ])
        elif direction == 'bottom':
            # Compress top
            dst_points = np.float32([
                [0, 0],
                [width, 0],
                [width * (1 - shift_factor), height],
                [width * shift_factor, height]
            ])
        else:
            return image
        
        # Calculate perspective transform matrix
        matrix = cv2.getPerspectiveTransform(src_points, dst_points)
        
        # Apply transform
        img_array = np.array(img)
        transformed = cv2.warpPerspective(
            img_array,
            matrix,
            (width, height),
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255, 0)
        )
        
        # Convert back to PIL
        result = Image.fromarray(transformed, 'RGBA')
        
        # Enhance the result
        result = enhance_view(result, direction)
        
        return result
        
    except Exception as e:
        print(f"❌ Transform failed: {e}")
        return None


def create_depth_based_view(
    image: Image.Image,
    direction: str,
    angle: float = 30.0
) -> Optional[Image.Image]:
    """
    Create side view using depth-based displacement
    More realistic than simple perspective
    """
    try:
        # Remove background
        img_rgba = remove_background_simple(image)
        img_array = np.array(img_rgba)
        
        # Estimate depth
        depth = estimate_depth_simple(image)
        
        height, width = depth.shape
        
        # Calculate displacement based on depth
        angle_rad = np.deg2rad(angle)
        max_shift = int(width * 0.15 * np.sin(angle_rad))
        
        # Create output image
        output = np.zeros_like(img_array)
        
        # Apply depth-based displacement
        for y in range(height):
            for x in range(width):
                depth_value = depth[y, x]
                shift = int(max_shift * depth_value)
                
                if direction == 'left':
                    new_x = max(0, min(width - 1, x - shift))
                elif direction == 'right':
                    new_x = max(0, min(width - 1, x + shift))
                else:
                    new_x = x
                
                if direction == 'top':
                    new_y = max(0, min(height - 1, y - shift))
                elif direction == 'bottom':
                    new_y = max(0, min(height - 1, y + shift))
                else:
                    new_y = y
                
                output[new_y, new_x] = img_array[y, x]
        
        # Fill holes using inpainting
        gray_output = cv2.cvtColor(output[:,:,:3], cv2.COLOR_RGB2GRAY)
        mask = (gray_output == 0).astype(np.uint8) * 255
        
        if np.sum(mask) > 0:
            output[:,:,:3] = cv2.inpaint(output[:,:,:3], mask, 3, cv2.INPAINT_TELEA)
        
        result = Image.fromarray(output, 'RGBA')
        result = enhance_view(result, direction)
        
        return result
        
    except Exception as e:
        print(f"❌ Depth-based view failed: {e}")
        return None


def enhance_view(image: Image.Image, direction: str) -> Image.Image:
    """Apply enhancements to make view more realistic"""
    try:
        # Slight shadow on transformed sides
        enhancer = ImageEnhance.Brightness(image)
        if direction in ['left', 'right']:
            image = enhancer.enhance(0.95)
        
        # Slight sharpening
        image = image.filter(ImageFilter.UnsharpMask(radius=1, percent=100, threshold=2))
        
        return image
    except:
        return image


def generate_cardinal_views_simple(
    image: Image.Image,
    angle: float = 30.0,
    method: str = 'perspective'  # 'perspective' or 'depth'
) -> Dict[str, Image.Image]:
    """
    Generate 4 cardinal views using simple transformations
    No AI models, no downloads, fast processing
    
    Args:
        image: Input PIL Image
        angle: Viewing angle in degrees (15-45)
        method: 'perspective' (faster) or 'depth' (better quality)
    
    Returns:
        Dictionary with keys: 'top', 'bottom', 'left', 'right'
    """
    print(f"🔄 Generating simple cardinal views at {angle}° using {method} method...")
    views = {}
    
    # Choose generation method
    if method == 'depth':
        generator_func = create_depth_based_view
    else:
        generator_func = create_perspective_transform
    
    # Generate each direction
    directions = ['top', 'bottom', 'left', 'right']
    for direction in directions:
        print(f"   📸 Generating {direction} view...")
        view = generator_func(image, direction, angle)
        if view:
            # Convert RGBA to RGB with white background
            if view.mode == 'RGBA':
                background = Image.new('RGB', view.size, (255, 255, 255))
                background.paste(view, mask=view.split()[3])
                view = background
            views[direction] = view
            print(f"      ✅ {direction.capitalize()} view generated")
    
    print(f"✅ Generated {len(views)}/4 views (no model download needed)")
    return views


def generate_multi_angle_views_simple(
    image: Image.Image,
    angles: list = [15.0, 30.0, 45.0],
    method: str = 'perspective'
) -> Dict[str, Image.Image]:
    """
    Generate views at multiple angles
    Returns dict with keys like: 'top_15', 'left_30', etc.
    """
    print(f"🔄 Generating multi-angle views at {angles}° using {method} method...")
    all_views = {}
    
    for angle in angles:
        views = generate_cardinal_views_simple(image, angle, method)
        angle_key = int(angle)
        
        for direction, view_image in views.items():
            all_views[f'{direction}_{angle_key}'] = view_image
    
    print(f"✅ Generated {len(all_views)} total views")
    return all_views


# Backwards compatibility wrappers
def generate_cardinal_views_fast(
    image: Image.Image,
    angle: float = 30.0,
    num_inference_steps: int = 20,  # Ignored, kept for compatibility
) -> Tuple[Dict[str, Image.Image], str]:
    """Wrapper for compatibility with existing code"""
    try:
        views = generate_cardinal_views_simple(image, angle, method='depth')
        if len(views) == 4:
            return views, "success"
        elif len(views) > 0:
            return views, "partial_success"
        else:
            return {}, "generation_failed"
    except Exception as e:
        print(f"❌ Error: {e}")
        return {}, f"error_{str(e)[:50]}"


def generate_multi_angle_cardinal_views_fast(
    image: Image.Image,
    angles: list = [15.0, 30.0, 45.0],
    num_inference_steps: int = 20,  # Ignored
) -> Tuple[Dict[str, Image.Image], str]:
    """Wrapper for compatibility"""
    try:
        views = generate_multi_angle_views_simple(image, angles, method='depth')
        expected_count = len(angles) * 4
        if len(views) == expected_count:
            return views, "success"
        elif len(views) > 0:
            return views, "partial_success"
        else:
            return {}, "generation_failed"
    except Exception as e:
        print(f"❌ Error: {e}")
        return {}, f"error_{str(e)[:50]}"
