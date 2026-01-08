"""
Zero123 Novel View Synthesis Module (Lightweight Fallback)
---------------------------------------------------------

This module exposes the same public API as the original
Zero123-based implementation, but instead of loading a
heavy diffusion model it generates approximate side views
using OpenCV perspective transforms.

Functions exported and used elsewhere:

- generate_side_views(image, angle, use_zero123, num_inference_steps)
- generate_multi_angle_side_views(image, angles, use_zero123, num_inference_steps)
- generate_perspective_views(image)

Both ingestion and endpoints can import these helpers
without pulling in large model dependencies, and the
backend will start cleanly.
"""

from typing import Dict, List, Optional, Tuple

from PIL import Image


def generate_perspective_views(image: Image.Image) -> Dict[str, Image.Image]:
    """Generate simulated perspective views using OpenCV.

    This is a lightweight alternative when a full Zero123
    model is not available. It creates top, bottom, left,
    and right views using perspective warping.

    Args:
        image: Input PIL Image.

    Returns:
        Dict mapping view names to PIL Images, e.g.:
        {"top": Image, "bottom": Image, "left": Image, "right": Image}.
    """

    import numpy as np
    import cv2

    views: Dict[str, Image.Image] = {}

    try:
        # Ensure image is RGB
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Convert PIL to numpy array for OpenCV
        img_array = np.array(image)
        height, width = img_array.shape[:2]

        # Source points (image corners)
        src_pts = np.float32([[0, 0], [width, 0], [width, height], [0, height]])

        # 1. TOP VIEW - Looking down at ~30 degrees (top edge compressed)
        offset_w = int(width * 0.15)  # 15% compression at top
        dst_pts_top = np.float32(
            [
                [offset_w, 0],
                [width - offset_w, 0],
                [width, height],
                [0, height],
            ]
        )
        matrix_top = cv2.getPerspectiveTransform(src_pts, dst_pts_top)
        top_view = cv2.warpPerspective(
            img_array,
            matrix_top,
            (width, height),
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255),
        )
        top_view = cv2.GaussianBlur(top_view, (3, 3), 0)
        views["top"] = Image.fromarray(top_view)

        # 2. BOTTOM VIEW - Looking up at ~30 degrees (bottom edge compressed)
        dst_pts_bottom = np.float32(
            [
                [0, 0],
                [width, 0],
                [width - offset_w, height],
                [offset_w, height],
            ]
        )
        matrix_bottom = cv2.getPerspectiveTransform(src_pts, dst_pts_bottom)
        bottom_view = cv2.warpPerspective(
            img_array,
            matrix_bottom,
            (width, height),
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255),
        )
        bottom_view = cv2.GaussianBlur(bottom_view, (3, 3), 0)
        views["bottom"] = Image.fromarray(bottom_view)

        # 3. LEFT VIEW - Looking from left at ~45 degrees (right side compressed)
        offset_h = int(height * 0.1)
        offset_w_side = int(width * 0.25)
        dst_pts_left = np.float32(
            [
                [0, offset_h],
                [width - offset_w_side, 0],
                [width - offset_w_side, height],
                [0, height - offset_h],
            ]
        )
        matrix_left = cv2.getPerspectiveTransform(src_pts, dst_pts_left)
        left_view = cv2.warpPerspective(
            img_array,
            matrix_left,
            (width, height),
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255),
        )
        # Add subtle shadow gradient on right side
        shadow_left = np.zeros_like(left_view)
        for i in range(width):
            alpha = max(0.0, (i - width * 0.7) / (width * 0.3))
            value = int(20 * alpha)
            shadow_left[:, i] = [value, value, value]
        left_view = cv2.subtract(left_view, shadow_left)
        views["left"] = Image.fromarray(left_view)

        # 4. RIGHT VIEW - Looking from right at ~45 degrees (left side compressed)
        dst_pts_right = np.float32(
            [
                [offset_w_side, 0],
                [width, offset_h],
                [width, height - offset_h],
                [offset_w_side, height],
            ]
        )
        matrix_right = cv2.getPerspectiveTransform(src_pts, dst_pts_right)
        right_view = cv2.warpPerspective(
            img_array,
            matrix_right,
            (width, height),
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255),
        )
        # Add subtle shadow gradient on left side
        shadow_right = np.zeros_like(right_view)
        for i in range(width):
            alpha = max(0.0, (width * 0.3 - i) / (width * 0.3))
            value = int(20 * alpha)
            shadow_right[:, i] = [value, value, value]
        right_view = cv2.subtract(right_view, shadow_right)
        views["right"] = Image.fromarray(right_view)

        print(f"✅ Generated {len(views)} perspective views")
        return views

    except Exception as e:  # pragma: no cover - defensive
        print(f"❌ Failed to generate perspective views: {e}")
        import traceback

        traceback.print_exc()
        return {}


def generate_side_views(
    image: Image.Image,
    angle: float = 30.0,
    use_zero123: bool = True,
    num_inference_steps: int = 50,
) -> Tuple[Optional[Image.Image], Optional[Image.Image], str]:
    """Generate left and right side views for a product image.

    This matches the original Zero123 API but always uses the
    perspective-based fallback rather than a heavy diffusion
    model. The ``angle`` and ``num_inference_steps`` arguments
    are accepted for compatibility but are not used.
    """

    try:
        views = generate_perspective_views(image)
        left = views.get("left")
        right = views.get("right")

        if left is not None and right is not None:
            return left, right, "fallback_success"
        if left is not None or right is not None:
            return left, right, "fallback_partial_success"
        return None, None, "fallback_failed"

    except Exception as e:  # pragma: no cover - defensive
        print(f"❌ Error in generate_side_views: {e}")
        return None, None, f"error_{str(e)[:50]}"


def generate_multi_angle_side_views(
    image: Image.Image,
    angles: List[float] = [15.0, 30.0, 45.0],
    use_zero123: bool = True,
    num_inference_steps: int = 50,
) -> Tuple[Dict[str, Optional[Image.Image]], str]:
    """Generate multiple labelled side views for different angles.

    For now this reuses the same left/right perspective views for
    each requested angle so callers get a full set of keys like
    ``left_15``, ``right_15``, ``left_30``, etc., even though the
    underlying imagery is shared.
    """

    try:
        base_views = generate_perspective_views(image)
        left = base_views.get("left")
        right = base_views.get("right")

        result: Dict[str, Optional[Image.Image]] = {}

        for angle in angles:
            angle_key = int(angle)
            if left is not None:
                result[f"left_{angle_key}"] = left
            if right is not None:
                result[f"right_{angle_key}"] = right

        if result:
            return result, "fallback_success"
        return {}, "fallback_failed"

    except Exception as e:  # pragma: no cover - defensive
        print(f"❌ Error in generate_multi_angle_side_views: {e}")
        return {}, f"error_{str(e)[:50]}"

