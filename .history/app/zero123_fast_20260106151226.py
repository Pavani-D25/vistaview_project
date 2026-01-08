"""
Optimized Zero123 Multi-View Generator
Generates top, bottom, left, right views quickly
"""
import os
from typing import Optional, Tuple, Dict, List
from io import BytesIO
import numpy as np
import cv2
from PIL import Image, ImageEnhance, ImageFilter

try:
    import torch
    from diffusers import DiffusionPipeline, EulerAncestralDiscreteScheduler
    import gc
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    DEPENDENCIES_AVAILABLE = False
    print(f"⚠️  Zero123 dependencies not available: {e}")
    torch = None


def preprocess_image_fast(image: Image.Image, target_size: int = 320) -> Image.Image:
    """Preprocessing for Zero123 - balanced quality"""
    # Convert to RGB
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Make square quickly
    size = max(image.size)
    square_img = Image.new('RGB', (size, size), (255, 255, 255))
    paste_x = (size - image.width) // 2
    paste_y = (size - image.height) // 2
    square_img.paste(image, (paste_x, paste_y))
    
    # Resize to target size (smaller = faster)
    result = square_img.resize((target_size, target_size), Image.Resampling.LANCZOS)
    
    return result


if DEPENDENCIES_AVAILABLE:
    class FastZero123Generator:
        """Optimized Zero123 generator for fast multi-view generation"""
        
        def __init__(self, device: Optional[str] = None):
            """Initialize with optimized settings"""
            self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
            self.pipeline = None
            self.is_loaded = False
            
            # Balanced parameters for quality
            self.default_size = 320  # Better quality than 256
            self.default_steps = 30  # Better quality (balanced)
            self.default_guidance = 4.0  # Better adherence to input
            
            print(f"🚀 FastZero123Generator initialized on {self.device}")
        
        def load_model(self):
            """Load Zero123 model with optimizations"""
            if self.is_loaded:
                return True
            
            try:
                print("📦 Loading Zero123 model (optimized for speed)...")
                
                # Load Zero123-XL model
                self.pipeline = DiffusionPipeline.from_pretrained(
                    "sudo-ai/zero123plus-v1.2",
                    custom_pipeline="sudo-ai/zero123plus-pipeline",
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                )
                
                self.pipeline.to(self.device)
                
                # Enable optimizations
                if self.device == "cuda":
                    # Enable memory efficient attention
                    self.pipeline.enable_attention_slicing()
                    self.pipeline.enable_vae_slicing()
                
                # Use faster scheduler
                self.pipeline.scheduler = EulerAncestralDiscreteScheduler.from_config(
                    self.pipeline.scheduler.config
                )
                
                self.is_loaded = True
                print(f"✅ Zero123 model loaded successfully")
                return True
                
            except Exception as e:
                print(f"❌ Failed to load Zero123 model: {e}")
                self.is_loaded = False
                return False
        
        def unload_model(self):
            """Unload model to free memory"""
            if self.pipeline is not None:
                del self.pipeline
                self.pipeline = None
            self.is_loaded = False
            
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()
            print("🧹 Zero123 model unloaded")
        
        def generate_view(
            self,
            image: Image.Image,
            polar_angle: float,
            azimuth_angle: float,
            num_inference_steps: int = 20,
            guidance_scale: float = 3.0,
            seed: Optional[int] = None,
        ) -> Optional[Image.Image]:
            """
            Generate a single view - optimized for speed
            
            Args:
                image: Input PIL Image
                polar_angle: Vertical rotation (0=horizontal, 90=top, -90=bottom)
                azimuth_angle: Horizontal rotation (positive=right, negative=left)
                num_inference_steps: Quality vs speed (15-30 recommended)
                guidance_scale: How closely to follow the prompt (2-4 recommended)
                seed: Random seed for reproducibility
            """
            if not self.is_loaded:
                print("⚠️  Model not loaded")
                return None
            
            try:
                # Preprocess image - fast version
                original_size = image.size
                preprocessed = preprocess_image_fast(image, self.default_size)
                
                # Set seed for reproducibility
                generator = None
                if seed is not None:
                    generator = torch.Generator(device=self.device).manual_seed(seed)
                
                # Generate view
                with torch.inference_mode():
                    result = self.pipeline(
                        preprocessed,
                        polar_angle=polar_angle,
                        azimuth_angle=azimuth_angle,
                        num_inference_steps=num_inference_steps,
                        guidance_scale=guidance_scale,
                        generator=generator,
                    )
                    
                    generated_image = result.images[0]
                
                # Resize back to good quality size
                output_size = (640, 640)  # Higher quality output
                generated_image = generated_image.resize(output_size, Image.Resampling.LANCZOS)
                
                # Clear memory after generation
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                return generated_image
                
            except Exception as e:
                print(f"❌ View generation failed: {e}")
                return None
        
        def generate_four_cardinal_views(
            self,
            image: Image.Image,
            angle: float = 30.0,
            num_inference_steps: int = 20,
        ) -> Dict[str, Optional[Image.Image]]:
            """
            Generate 4 cardinal views: top, bottom, left, right
            Optimized for speed with reduced inference steps
            """
            print(f"🔄 Generating 4-way views (top, bottom, left, right) at {angle}°...")
            views = {}
            
            # Top view (looking down from above)
            print("   📸 Generating top view...")
            top_view = self.generate_view(
                image=image,
                polar_angle=angle,  # Look down from above
                azimuth_angle=0.0,
                num_inference_steps=num_inference_steps,
                guidance_scale=self.default_guidance,
                seed=100,
            )
            if top_view:
                views['top'] = top_view
                print("      ✅ Top view generated")
            
            # Bottom view (looking up from below)
            print("   📸 Generating bottom view...")
            bottom_view = self.generate_view(
                image=image,
                polar_angle=-angle,  # Look up from below
                azimuth_angle=0.0,
                num_inference_steps=num_inference_steps,
                guidance_scale=self.default_guidance,
                seed=101,
            )
            if bottom_view:
                views['bottom'] = bottom_view
                print("      ✅ Bottom view generated")
            
            # Left view
            print("   📸 Generating left view...")
            left_view = self.generate_view(
                image=image,
                polar_angle=0.0,
                azimuth_angle=-angle,
                num_inference_steps=num_inference_steps,
                guidance_scale=self.default_guidance,
                seed=102,
            )
            if left_view:
                views['left'] = left_view
                print("      ✅ Left view generated")
            
            # Right view
            print("   📸 Generating right view...")
            right_view = self.generate_view(
                image=image,
                polar_angle=0.0,
                azimuth_angle=angle,
                num_inference_steps=num_inference_steps,
                guidance_scale=self.default_guidance,
                seed=103,
            )
            if right_view:
                views['right'] = right_view
                print("      ✅ Right view generated")
            
            print(f"✅ Generated {len(views)}/4 views")
            return views
        
        def generate_multi_angle_cardinal_views(
            self,
            image: Image.Image,
            angles: List[float] = [15.0, 30.0, 45.0],
            num_inference_steps: int = 20,
        ) -> Dict[str, Optional[Image.Image]]:
            """
            Generate top/bottom/left/right views at multiple angles
            Example: top_15, top_30, left_15, left_30, etc.
            """
            print(f"🔄 Generating multi-angle cardinal views at {angles}°...")
            views = {}
            
            for angle in angles:
                angle_key = int(angle)
                
                # Top
                print(f"   📸 Generating top {angle_key}°...")
                top = self.generate_view(
                    image, polar_angle=angle, azimuth_angle=0.0,
                    num_inference_steps=num_inference_steps,
                    seed=100 + angle_key
                )
                if top:
                    views[f'top_{angle_key}'] = top
                    print(f"      ✅ Top {angle_key}° generated")
                
                # Bottom
                print(f"   📸 Generating bottom {angle_key}°...")
                bottom = self.generate_view(
                    image, polar_angle=-angle, azimuth_angle=0.0,
                    num_inference_steps=num_inference_steps,
                    seed=200 + angle_key
                )
                if bottom:
                    views[f'bottom_{angle_key}'] = bottom
                    print(f"      ✅ Bottom {angle_key}° generated")
                
                # Left
                print(f"   📸 Generating left {angle_key}°...")
                left = self.generate_view(
                    image, polar_angle=0.0, azimuth_angle=-angle,
                    num_inference_steps=num_inference_steps,
                    seed=300 + angle_key
                )
                if left:
                    views[f'left_{angle_key}'] = left
                    print(f"      ✅ Left {angle_key}° generated")
                
                # Right
                print(f"   📸 Generating right {angle_key}°...")
                right = self.generate_view(
                    image, polar_angle=0.0, azimuth_angle=angle,
                    num_inference_steps=num_inference_steps,
                    seed=400 + angle_key
                )
                if right:
                    views[f'right_{angle_key}'] = right
                    print(f"      ✅ Right {angle_key}° generated")
                
                print(f"   ✅ Completed angle {angle}°")
            
            print(f"✅ Generated {len(views)} total views")
            return views

    # Global instance
    _fast_generator: Optional[FastZero123Generator] = None

    def get_fast_zero123_generator(force_reload: bool = False) -> FastZero123Generator:
        """Get or create the global fast generator instance"""
        global _fast_generator
        
        if _fast_generator is None or force_reload:
            _fast_generator = FastZero123Generator()
        
        return _fast_generator

    def generate_cardinal_views_fast(
        image: Image.Image,
        angle: float = 30.0,
        num_inference_steps: int = 20,
    ) -> Tuple[Dict[str, Image.Image], str]:
        """
        Fast generation of top, bottom, left, right views
        
        Args:
            image: Input PIL Image
            angle: Rotation angle in degrees (15-45 recommended)
            num_inference_steps: Quality (15-25 for speed, 30-50 for quality)
        
        Returns:
            Tuple of (views_dict, status)
        """
        try:
            generator = get_fast_zero123_generator()
            
            if not generator.is_loaded:
                print("📦 Loading model...")
                success = generator.load_model()
                if not success:
                    return {}, "model_load_failed"
            
            # Generate 4 cardinal views
            views = generator.generate_four_cardinal_views(
                image=image,
                angle=angle,
                num_inference_steps=num_inference_steps,
            )
            
            if len(views) == 4:
                return views, "success"
            elif len(views) > 0:
                return views, "partial_success"
            else:
                return {}, "generation_failed"
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return {}, f"error_{str(e)[:50]}"

    def generate_multi_angle_cardinal_views_fast(
        image: Image.Image,
        angles: List[float] = [15.0, 30.0, 45.0],
        num_inference_steps: int = 20,
    ) -> Tuple[Dict[str, Image.Image], str]:
        """
        Fast generation of multi-angle cardinal views
        
        Returns views like: top_15, top_30, left_15, right_30, etc.
        """
        try:
            generator = get_fast_zero123_generator()
            
            if not generator.is_loaded:
                print("📦 Loading model...")
                success = generator.load_model()
                if not success:
                    return {}, "model_load_failed"
            
            views = generator.generate_multi_angle_cardinal_views(
                image=image,
                angles=angles,
                num_inference_steps=num_inference_steps,
            )
            
            expected_count = len(angles) * 4  # 4 views per angle
            if len(views) == expected_count:
                return views, "success"
            elif len(views) > 0:
                return views, "partial_success"
            else:
                return {}, "generation_failed"
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return {}, f"error_{str(e)[:50]}"

else:
    # Dummy implementations when dependencies not available
    class FastZero123Generator:
        def __init__(self, *args, **kwargs):
            print("⚠️  Zero123 dependencies not installed")
        def load_model(self): return False
        def generate_four_cardinal_views(self, *args, **kwargs): return {}
        def generate_multi_angle_cardinal_views(self, *args, **kwargs): return {}
    
    _fast_generator = None
    
    def get_fast_zero123_generator(force_reload=False):
        global _fast_generator
        if _fast_generator is None:
            _fast_generator = FastZero123Generator()
        return _fast_generator
    
    def generate_cardinal_views_fast(*args, **kwargs):
        return {}, "dependencies_not_available"
    
    def generate_multi_angle_cardinal_views_fast(*args, **kwargs):
        return {}, "dependencies_not_available"
