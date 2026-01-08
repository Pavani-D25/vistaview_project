"""
Zero123 Novel View Synthesis Module
Generates side views of product images using Zero123 diffusion model
"""
import os
from typing import Optional, Tuple, Dict, List
from io import BytesIO

try:
    import torch
    import numpy as np
    from PIL import Image
    from diffusers import StableDiffusionPipeline, DiffusionPipeline
    from transformers import CLIPImageProcessor
    import gc
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    DEPENDENCIES_AVAILABLE = False
    print(f"⚠️  Zero123 dependencies not available: {e}")
    # Create dummy classes/functions for when dependencies are missing
    torch = None
    np = None
    Image = None


if DEPENDENCIES_AVAILABLE:
    class Zero123ViewGenerator:
        """
        Zero123-based view generator for product images
        Generates left and right views from a single input image
        """
        
        def __init__(self, device: str = "auto", model_id: str = "ashawkey/zero123-xl-diffusers"):
            """
            Initialize Zero123 model
        
        Args:
            device: Device to use ('cuda', 'cpu', or 'auto')
            model_id: HuggingFace model ID for Zero123
        """
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        self.model_id = model_id
        self.pipeline = None
        self.is_loaded = False
        
        print(f"🔧 Zero123ViewGenerator initialized (device: {self.device})")
    
    def load_model(self):
        """Load Zero123 model into memory"""
        if self.is_loaded:
            return
        
        print(f"📥 Loading Zero123 model: {self.model_id}...")
        
        try:
            # Load Zero123 pipeline
            self.pipeline = DiffusionPipeline.from_pretrained(
                self.model_id,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                safety_checker=None,
                local_files_only=False,
            )
            
            # Move to device
            self.pipeline = self.pipeline.to(self.device)
            
            # Enable memory optimizations
            if self.device == "cuda":
                try:
                    self.pipeline.enable_xformers_memory_efficient_attention()
                    print("   ✅ xFormers memory optimization enabled")
                except Exception as e:
                    print(f"   ⚠️  Could not enable xFormers: {e}")
            
            # Enable attention slicing to reduce memory
            self.pipeline.enable_attention_slicing()
            
            # Enable VAE slicing
            if hasattr(self.pipeline, 'enable_vae_slicing'):
                self.pipeline.enable_vae_slicing()
            
            self.is_loaded = True
            print("✅ Zero123 model loaded successfully")
            
        except Exception as e:
            print(f"❌ Failed to load Zero123 model: {e}")
            print("   Falling back to simplified view generation...")
            self.is_loaded = False
    
    def unload_model(self):
        """Unload model from memory to free resources"""
        if self.pipeline is not None:
            del self.pipeline
            self.pipeline = None
        
        self.is_loaded = False
        
        # Clear CUDA cache if available
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        gc.collect()
        print("🗑️  Zero123 model unloaded from memory")
    
    def generate_view(
        self,
        image: Image.Image,
        polar_angle: float = 0.0,
        azimuth_angle: float = 30.0,
        num_inference_steps: int = 50,
        guidance_scale: float = 3.0,
    ) -> Optional[Image.Image]:
        """
        Generate a novel view of the input image
        
        Args:
            image: Input PIL Image
            polar_angle: Elevation angle in degrees (0 = eye level)
            azimuth_angle: Rotation angle in degrees (positive = rotate right)
            num_inference_steps: Number of diffusion steps (higher = better quality)
            guidance_scale: Classifier-free guidance scale
        
        Returns:
            Generated PIL Image or None if failed
        """
        if not self.is_loaded:
            print("⚠️  Model not loaded, loading now...")
            self.load_model()
        
        if not self.is_loaded:
            return None
        
        try:
            # Preprocess image
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize to optimal size for Zero123 (256x256 or 512x512)
            original_size = image.size
            target_size = 256 if self.device == "cpu" else 512
            image_resized = image.resize((target_size, target_size), Image.Resampling.LANCZOS)
            
            # Generate view using Zero123
            with torch.no_grad():
                # Convert angles to radians for the model
                polar_rad = np.deg2rad(polar_angle)
                azimuth_rad = np.deg2rad(azimuth_angle)
                
                # Generate
                result = self.pipeline(
                    image=image_resized,
                    polar=polar_rad,
                    azimuth=azimuth_rad,
                    num_inference_steps=num_inference_steps,
                    guidance_scale=guidance_scale,
                )
                
                generated_image = result.images[0]
            
            # Resize back to original size
            generated_image = generated_image.resize(original_size, Image.Resampling.LANCZOS)
            
            return generated_image
            
        except Exception as e:
            print(f"❌ View generation failed: {e}")
            return None
    
    def generate_left_right_views(
        self,
        image: Image.Image,
        angle: float = 30.0,
        num_inference_steps: int = 50,
        guidance_scale: float = 3.0,
    ) -> Tuple[Optional[Image.Image], Optional[Image.Image]]:
        """
        Generate both left and right views of the input image
        
        Args:
            image: Input PIL Image
            angle: Rotation angle in degrees (default 30°)
            num_inference_steps: Number of diffusion steps
            guidance_scale: Guidance scale for generation
        
        Returns:
            Tuple of (left_view, right_view), either can be None if failed
        """
        print(f"   🔄 Generating left and right views (±{angle}°)...")
        
        # Generate left view (negative azimuth = rotate camera left)
        left_view = self.generate_view(
            image=image,
            polar_angle=0.0,
            azimuth_angle=-angle,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
        )
        
        if left_view:
            print("      ✅ Left view generated")
        else:
            print("      ❌ Left view generation failed")
        
        # Generate right view (positive azimuth = rotate camera right)
        right_view = self.generate_view(
            image=image,
            polar_angle=0.0,
            azimuth_angle=angle,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
        )
        
        if right_view:
            print("      ✅ Right view generated")
        else:
            print("      ❌ Right view generation failed")
        
        return left_view, right_view

    def generate_multi_angle_views(
        self,
        image: Image.Image,
        angles: List[float] = [15.0, 30.0, 45.0],
        num_inference_steps: int = 50,
        guidance_scale: float = 3.0,
    ) -> Dict[str, Optional[Image.Image]]:
        """
        Generate multiple side views at different angles
        
        Args:
            image: Input PIL Image
            angles: List of rotation angles in degrees (e.g., [15, 30, 45])
            num_inference_steps: Number of diffusion steps
            guidance_scale: Guidance scale for generation
        
        Returns:
            Dictionary mapping angle descriptors to generated images
            e.g., {'left_15': Image, 'right_15': Image, 'left_30': Image, ...}
        """
        print(f"   🔄 Generating multi-angle views at {angles}°...")
        views = {}
        
        for angle in angles:
            # Generate left view
            left_view = self.generate_view(
                image=image,
                polar_angle=0.0,
                azimuth_angle=-angle,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
            )
            
            angle_key = int(angle)
            if left_view:
                views[f'left_{angle_key}'] = left_view
                print(f"      ✅ Left {angle}° view generated")
            else:
                print(f"      ❌ Left {angle}° view failed")
            
            # Generate right view
            right_view = self.generate_view(
                image=image,
                polar_angle=0.0,
                azimuth_angle=angle,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
            )
            
            if right_view:
                views[f'right_{angle_key}'] = right_view
                print(f"      ✅ Right {angle}° view generated")
            else:
                print(f"      ❌ Right {angle}° view failed")
        
        return views


    # Global instance (singleton pattern for memory efficiency)
    _global_generator: Optional[Zero123ViewGenerator] = None


    def get_zero123_generator(force_reload: bool = False) -> Zero123ViewGenerator:
        """
        Get or create the global Zero123 generator instance
        
        Args:
            force_reload: Force reload the model even if already loaded
        
        Returns:
            Zero123ViewGenerator instance
        """
        global _global_generator
        
        if _global_generator is None or force_reload:
            _global_generator = Zero123ViewGenerator()
        
        return _global_generator


    def generate_side_views(
        image,
        angle: float = 30.0,
        use_zero123: bool = True,
        num_inference_steps: int = 50,
    ) -> Tuple[Optional, Optional, str]:
        """
        High-level function to generate side views
        
        Args:
            image: Input PIL Image
            angle: Rotation angle in degrees
            use_zero123: Whether to use Zero123 (if False, uses fallback method)
            num_inference_steps: Quality parameter (30-75 recommended)
        
        Returns:
            Tuple of (left_view, right_view, status_message)
        """
        if not use_zero123:
            return None, None, "zero123_disabled"
        
        try:
            generator = get_zero123_generator()
            
            # Load model if not loaded
            if not generator.is_loaded:
                generator.load_model()
            
            # Check if model loaded successfully
            if not generator.is_loaded:
                return None, None, "model_load_failed"
            
            # Generate views
            left_view, right_view = generator.generate_left_right_views(
                image=image,
                angle=angle,
                num_inference_steps=num_inference_steps,
                guidance_scale=3.0,
            )
            
            if left_view and right_view:
                return left_view, right_view, "success"
            elif left_view or right_view:
                return left_view, right_view, "partial_success"
            else:
                return None, None, "generation_failed"
                
        except Exception as e:
            print(f"❌ Error in generate_side_views: {e}")
            return None, None, f"error_{str(e)[:50]}"


    def generate_multi_angle_side_views(
        image,
        angles: List[float] = [15.0, 30.0, 45.0],
        use_zero123: bool = True,
        num_inference_steps: int = 50,
    ) -> Tuple[Dict[str, Optional], str]:
        """
        High-level function to generate multiple side views at different angles
        
        Args:
            image: Input PIL Image
            angles: List of rotation angles in degrees
            use_zero123: Whether to use Zero123 (if False, returns empty dict)
            num_inference_steps: Quality parameter (30-75 recommended)
        
        Returns:
            Tuple of (views_dict, status_message)
            views_dict: {'left_15': Image, 'right_15': Image, 'left_30': Image, ...}
        """
        if not use_zero123:
            return {}, "zero123_disabled"
        
        try:
            generator = get_zero123_generator()
            
            # Load model if not loaded
            if not generator.is_loaded:
                generator.load_model()
            
            # Check if model loaded successfully
            if not generator.is_loaded:
                return {}, "model_load_failed"
            
            # Generate views at multiple angles
            views = generator.generate_multi_angle_views(
                image=image,
                angles=angles,
                num_inference_steps=num_inference_steps,
                guidance_scale=3.0,
            )
            
            if len(views) == len(angles) * 2:  # All views generated
                return views, "success"
            elif len(views) > 0:
                return views, "partial_success"
            else:
                return {}, "generation_failed"
                
        except Exception as e:
            print(f"❌ Error in generate_multi_angle_side_views: {e}")
            return {}, f"error_{str(e)[:50]}"

else:
    # Dummy implementations when dependencies are not available
    class Zero123ViewGenerator:
        def __init__(self, *args, **kwargs):
            print("⚠️  Zero123 dependencies not installed")
        
        def load_model(self):
            pass
        
        def unload_model(self):
            pass
        
        def generate_view(self, *args, **kwargs):
            return None
        
        def generate_left_right_views(self, *args, **kwargs):
            return None, None
        
        def generate_multi_angle_views(self, *args, **kwargs):
            return {}
    
    _global_generator = None
    
    def get_zero123_generator(force_reload=False):
        global _global_generator
        if _global_generator is None:
            _global_generator = Zero123ViewGenerator()
        return _global_generator
    
    def generate_side_views(*args, **kwargs):
        return None, None, "dependencies_not_available"
    
    def generate_multi_angle_side_views(*args, **kwargs):
        return {}, "dependencies_not_available"


def generate_perspective_views(image):
    """
    Generate simulated perspective views using proper perspective transformations.
    This is a lightweight alternative when Zero123 is not available.
    
    Creates top, bottom, left, and right views using OpenCV perspective warping.
    
    Args:
        image: PIL Image
    
    Returns:
        Dict mapping view names to PIL Images
        e.g., {'top': Image, 'bottom': Image, 'left': Image, 'right': Image}
    """
    from PIL import Image
    import numpy as np
    import cv2
    
    views = {}
    
    try:
        # Ensure image is RGB
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert PIL to numpy array for OpenCV
        img_array = np.array(image)
        height, width = img_array.shape[:2]
        
        # 1. TOP VIEW - Looking down at ~30 degrees
        # Top edge compressed, bottom edge normal
        src_pts = np.float32([[0, 0], [width, 0], [width, height], [0, height]])
        offset = int(width * 0.15)  # 15% compression at top
        dst_pts = np.float32([
            [offset, 0],
            [width - offset, 0],
            [width, height],
            [0, height]
        ])
        matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
        top_view = cv2.warpPerspective(img_array, matrix, (width, height), 
                                       borderMode=cv2.BORDER_CONSTANT, 
                                       borderValue=(255, 255, 255))
        # Apply slight blur to simulate depth of field
        top_view = cv2.GaussianBlur(top_view, (3, 3), 0)
        views['top'] = Image.fromarray(top_view)
        
        # 2. BOTTOM VIEW - Looking up at ~30 degrees
        # Bottom edge compressed, top edge normal
        dst_pts = np.float32([
            [0, 0],
            [width, 0],
            [width - offset, height],
            [offset, height]
        ])
        matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
        bottom_view = cv2.warpPerspective(img_array, matrix, (width, height),
                                          borderMode=cv2.BORDER_CONSTANT,
                                          borderValue=(255, 255, 255))
        bottom_view = cv2.GaussianBlur(bottom_view, (3, 3), 0)
        views['bottom'] = Image.fromarray(bottom_view)
        
        # 3. LEFT VIEW - Looking from left at ~45 degrees
        # Right edge compressed, simulating depth
        offset_h = int(height * 0.1)
        offset_w = int(width * 0.25)
        dst_pts = np.float32([
            [0, offset_h],
            [width - offset_w, 0],
            [width - offset_w, height],
            [0, height - offset_h]
        ])
        matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
        left_view = cv2.warpPerspective(img_array, matrix, (width, height),
                                        borderMode=cv2.BORDER_CONSTANT,
                                        borderValue=(255, 255, 255))
        # Add shadow gradient on right side
        shadow = np.zeros_like(left_view)
        for i in range(width):
            alpha = max(0, (i - width * 0.7) / (width * 0.3))
            shadow[:, i] = [int(20 * alpha)] * 3
        left_view = cv2.subtract(left_view, shadow)
        views['left'] = Image.fromarray(left_view)
        
        # 4. RIGHT VIEW - Looking from right at ~45 degrees
        # Left edge compressed, simulating depth
        dst_pts = np.float32([
            [offset_w, 0],
            [width, offset_h],
            [width, height - offset_h],
            [offset_w, height]
        ])
        matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
        right_view = cv2.warpPerspective(img_array, matrix, (width, height),
                                         borderMode=cv2.BORDER_CONSTANT,
                                         borderValue=(255, 255, 255))
        # Add shadow gradient on left side
        shadow = np.zeros_like(right_view)
        for i in range(width):
            alpha = max(0, (width * 0.3 - i) / (width * 0.3))
            shadow[:, i] = [int(20 * alpha)] * 3
        right_view = cv2.subtract(right_view, shadow)
        views['right'] = Image.fromarray(right_view)
        
        print(f"✅ Generated {len(views)} perspective views with proper transformations")
        return views
        
    except Exception as e:
        print(f"❌ Failed to generate perspective views: {e}")
        import traceback
        traceback.print_exc()
        return {}
