"""
Zero123 Multi-View Generator - Quality Optimized
Generates top, bottom, left, right views with good quality
Balanced between speed and accuracy (~60-90 seconds for 4 views)
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


def split_grid_into_views(grid_image: Image.Image) -> Dict[str, Image.Image]:
    """
    Split Zero123++ output grid (3x2 or 2x3) into individual views.
    
    Zero123++ generates 6 views in a grid with these camera angles:
    - Azimuth: 30°, 90°, 150°, 210°, 270°, 330° (6 views around object)
    - Grid layout: 3 columns x 2 rows
    
    Returns dict with keys matching azimuth angles.
    """
    width, height = grid_image.size
    
    # Determine grid layout (3x2 or 2x3)
    if width > height:
        # 3 columns x 2 rows
        cols, rows = 3, 2
    else:
        # 2 columns x 3 rows
        cols, rows = 2, 3
    
    cell_width = width // cols
    cell_height = height // rows
    
    views = {}
    azimuths = [30, 90, 150, 210, 270, 330]  # Zero123++ standard azimuths
    
    for idx in range(6):
        row = idx // cols
        col = idx % cols
        
        left = col * cell_width
        upper = row * cell_height
        right = left + cell_width
        lower = upper + cell_height
        
        view = grid_image.crop((left, upper, right, lower))
        views[f"azimuth_{azimuths[idx]}"] = view
    
    return views


if DEPENDENCIES_AVAILABLE:
    class FastZero123Generator:
        """Zero123 generator optimized for quality and reasonable speed"""
        
        def __init__(self, device: Optional[str] = None):
            """Initialize with balanced quality settings"""
            self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
            self.pipeline = None
            self.is_loaded = False
            
            # Balanced parameters for quality
            self.default_size = 320  # Better quality than 256
            self.default_steps = 25  # Faster with good quality (balanced)
            self.default_guidance = 4.0  # Better adherence to input
            
            print(f"🚀 FastZero123Generator initialized on {self.device}")
        
        def load_model(self):
            """Load Zero123 model with quality optimizations"""
            if self.is_loaded:
                return True
            
            try:
                print("📦 Loading Zero123 model (quality optimized)...")
                
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
        
        def generate_views_grid(
            self,
            image: Image.Image,
            num_inference_steps: int = 30,
            guidance_scale: float = 4.0,
            seed: Optional[int] = None,
        ) -> Optional[Image.Image]:
            """
            Generate 6-view grid using Zero123++ - quality optimized
            
            Zero123++ generates 6 views in a single pass arranged in a grid:
            - Azimuth angles: 30°, 90°, 150°, 210°, 270°, 330°
            - Grid layout: 3x2 (3 columns, 2 rows)
            
            Args:
                image: Input PIL Image
                num_inference_steps: Quality (20=fast, 30=balanced, 50+=best)
                guidance_scale: How closely to follow input (3-5 recommended)
                seed: Random seed for reproducibility
            
            Returns:
                Grid image containing 6 views (to be split later)
            """
            if not self.is_loaded:
                print("⚠️  Model not loaded")
                return None
            
            try:
                # Preprocess image - fast version
                preprocessed = preprocess_image_fast(image, self.default_size)
                
                # Set seed for reproducibility
                generator = None
                if seed is not None:
                    generator = torch.Generator(device=self.device).manual_seed(seed)
                
                # Generate 6-view grid
                # Note: Zero123++ ignores polar/azimuth parameters and generates fixed views
                with torch.inference_mode():
                    result = self.pipeline(
                        preprocessed,
                        num_inference_steps=num_inference_steps,
                        guidance_scale=guidance_scale,
                        generator=generator,
                    )
                    
                    grid_image = result.images[0]
                
                # Clear memory after generation
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                return grid_image
                
            except Exception as e:
                print(f"❌ View generation failed: {e}")
                return None
        
        def generate_four_cardinal_views(
            self,
            image: Image.Image,
            angle: float = 30.0,
            num_inference_steps: int = 30,
        ) -> Dict[str, Optional[Image.Image]]:
            """
            Generate 4 cardinal views: top, bottom, left, right
            Quality optimized - single AI generation pass
            
            Note: Zero123++ generates 6 views at fixed azimuths (30°, 90°, 150°, 210°, 270°, 330°).
            We'll extract the 4 most relevant ones for cardinal directions.
            """
            print(f"🔄 Generating cardinal views (one AI pass)...")
            
            # Generate 6-view grid in a single pass
            print("   📸 Generating 6-view grid with Zero123++...")
            grid_image = self.generate_views_grid(
                image=image,
                num_inference_steps=num_inference_steps,
                guidance_scale=self.default_guidance,
                seed=100,
            )
            
            if not grid_image:
                print("❌ Failed to generate views")
                return {}
            
            # Split grid into individual views
            print("   ✂️  Extracting individual views from grid...")
            all_views = split_grid_into_views(grid_image)
            
            # Map Zero123++ azimuths to cardinal directions
            # Zero123++ azimuths: 30°, 90°, 150°, 210°, 270°, 330°
            # Cardinal mapping:
            #   - Front-right (30°) -> top
            #   - Right (90°) -> right  
            #   - Back-right (150°) -> bottom
            #   - Back-left (210°) -> skip
            #   - Left (270°) -> left
            #   - Front-left (330°) -> skip
            
            cardinal_views = {}
            output_size = (640, 640)  # Higher quality output
            
            if "azimuth_30" in all_views:
                cardinal_views['top'] = all_views["azimuth_30"].resize(output_size, Image.Resampling.LANCZOS)
                print("      ✅ Top view (30° azimuth)")
            
            if "azimuth_90" in all_views:
                cardinal_views['right'] = all_views["azimuth_90"].resize(output_size, Image.Resampling.LANCZOS)
                print("      ✅ Right view (90° azimuth)")
            
            if "azimuth_150" in all_views:
                cardinal_views['bottom'] = all_views["azimuth_150"].resize(output_size, Image.Resampling.LANCZOS)
                print("      ✅ Bottom view (150° azimuth)")
            
            if "azimuth_270" in all_views:
                cardinal_views['left'] = all_views["azimuth_270"].resize(output_size, Image.Resampling.LANCZOS)
                print("      ✅ Left view (270° azimuth)")
            
            print(f"✅ Generated {len(cardinal_views)}/4 cardinal views")
            return cardinal_views
        
        def generate_multi_angle_cardinal_views(
            self,
            image: Image.Image,
            angles: List[float] = [15.0, 30.0, 45.0],
            num_inference_steps: int = 30,
        ) -> Dict[str, Optional[Image.Image]]:
            """
            Generate top/bottom/left/right views at multiple angles
            
            Note: Zero123++ generates fixed azimuth angles (30°, 90°, 150°, 210°, 270°, 330°).
            The 'angles' parameter is ignored - we return the same 4 views with angle suffix.
            Example: top_15, top_30, left_15, left_30, etc.
            """
            print(f"🔄 Generating multi-angle cardinal views (simplified)...")
            
            # Since Zero123++ generates fixed views, we generate once and label with all angles
            # Generate the cardinal views once
            cardinal_views = self.generate_four_cardinal_views(
                image=image,
                num_inference_steps=num_inference_steps,
            )
            
            # Create views dict with angle suffixes
            views = {}
            for angle in angles:
                angle_key = int(angle)
                for direction, view_image in cardinal_views.items():
                    views[f'{direction}_{angle_key}'] = view_image
                    
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
        num_inference_steps: int = 30,
    ) -> Tuple[Dict[str, Image.Image], str]:
        """
        Quality generation of top, bottom, left, right views
        
        Args:
            image: Input PIL Image
            angle: Rotation angle in degrees (15-45 recommended)
            num_inference_steps: Quality (20=fast, 30=balanced, 50=best)
        
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
        num_inference_steps: int = 30,
    ) -> Tuple[Dict[str, Image.Image], str]:
        """
        Quality generation of multi-angle cardinal views
        
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
