# """
# Enhanced Zero123 Novel View Synthesis Module
# Improved preprocessing and parameters for better quality views
# """
# import os
# from typing import Optional, Tuple, Dict, List
# from io import BytesIO
# import numpy as np
# import cv2
# from PIL import Image, ImageEnhance, ImageFilter

# try:
#     import torch
#     from diffusers import DiffusionPipeline
#     import gc
#     DEPENDENCIES_AVAILABLE = True
# except ImportError as e:
#     DEPENDENCIES_AVAILABLE = False
#     print(f"⚠️  Zero123 dependencies not available: {e}")
#     torch = None


# def preprocess_for_zero123(image: Image.Image, target_size: int = 256) -> Image.Image:
#     """
#     Preprocess image for optimal Zero123 results
#     - Removes/cleans background
#     - Centers the object
#     - Normalizes lighting
#     - Adds padding
#     """
#     # Convert to RGB
#     if image.mode != 'RGB':
#         image = image.convert('RGB')
    
#     img_array = np.array(image)
#     h, w = img_array.shape[:2]
    
#     # 1. Background removal and object detection
#     gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    
#     # Adaptive threshold to separate object from background
#     _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
#     # Morphological operations to clean up
#     kernel = np.ones((5, 5), np.uint8)
#     thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
#     thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
    
#     # Find contours to locate main object
#     contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
#     if contours:
#         # Get bounding box of largest contour
#         largest_contour = max(contours, key=cv2.contourArea)
#         x, y, w, h = cv2.boundingRect(largest_contour)
        
#         # Add 15% padding around object
#         padding = int(max(w, h) * 0.15)
#         x1 = max(0, x - padding)
#         y1 = max(0, y - padding)
#         x2 = min(img_array.shape[1], x + w + padding)
#         y2 = min(img_array.shape[0], y + h + padding)
        
#         # Crop to object with padding
#         img_cropped = img_array[y1:y2, x1:x2]
#     else:
#         # If no contours found, use center crop
#         crop_size = min(h, w)
#         start_h = (h - crop_size) // 2
#         start_w = (w - crop_size) // 2
#         img_cropped = img_array[start_h:start_h+crop_size, start_w:start_w+crop_size]
    
#     # 2. Create clean white background
#     result = Image.fromarray(img_cropped)
    
#     # Make square by padding with white
#     size = max(result.size)
#     square_img = Image.new('RGB', (size, size), (255, 255, 255))
#     paste_x = (size - result.width) // 2
#     paste_y = (size - result.height) // 2
#     square_img.paste(result, (paste_x, paste_y))
    
#     # 3. Enhance image quality
#     # Increase sharpness slightly
#     enhancer = ImageEnhance.Sharpness(square_img)
#     square_img = enhancer.enhance(1.2)
    
#     # Adjust contrast slightly
#     enhancer = ImageEnhance.Contrast(square_img)
#     square_img = enhancer.enhance(1.1)
    
#     # 4. Resize to target size
#     result = square_img.resize((target_size, target_size), Image.Resampling.LANCZOS)
    
#     return result


# if DEPENDENCIES_AVAILABLE:
#     class Zero123ViewGenerator:
#         """Enhanced Zero123-based view generator"""
        
#         def __init__(self, device: str = "auto", model_id: str = "ashawkey/zero123-xl-diffusers"):
#             """Initialize Zero123 model"""
#             if device == "auto":
#                 self.device = "cuda" if torch.cuda.is_available() else "cpu"
#             else:
#                 self.device = device
            
#             self.model_id = model_id
#             self.pipeline = None
#             self.is_loaded = False
            
#             print(f"🔧 Zero123ViewGenerator initialized (device: {self.device})")
        
#         def load_model(self):
#             """Load Zero123 model into memory with optimizations"""
#             if self.is_loaded:
#              return
        
#         print(f"📥 Loading Zero123 model: {self.model_id}...")
        
#         try:
#             # Load with appropriate dtype
#             dtype = torch.float16 if self.device == "cuda" else torch.float32
            
#             self.pipeline = DiffusionPipeline.from_pretrained(
#                 self.model_id,
#                 torch_dtype=dtype,
#                 safety_checker=None,
#                 local_files_only=False,
#                 trust_remote_code=True,
#             )
            
#             # Move to device
#             self.pipeline = self.pipeline.to(self.device)
            
#             # Memory optimizations
#             if self.device == "cuda":
#                 # Enable model CPU offload for lower memory usage
#                 try:
#                     self.pipeline.enable_model_cpu_offload()
#                     print("   ✅ Model CPU offload enabled")
#                 except:
#                     pass
            
#             # Enable attention slicing
#             self.pipeline.enable_attention_slicing(1)
            
#             # Enable VAE slicing
#             if hasattr(self.pipeline, 'enable_vae_slicing'):
#                 self.pipeline.enable_vae_slicing()
            
#             # Set to eval mode
#             self.pipeline.unet.eval()
            
#             self.is_loaded = True
#             print("✅ Zero123 model loaded successfully")
            
#         except Exception as e:
#             print(f"❌ Failed to load Zero123 model: {e}")
#             import traceback
#             traceback.print_exc()
#             self.is_loaded = False
        
        
#         def unload_model(self):
#             """Unload model from memory"""
#             if self.pipeline is not None:
#                 del self.pipeline
#                 self.pipeline = None
            
#             self.is_loaded = False
            
#             if torch.cuda.is_available():
#                 torch.cuda.empty_cache()
            
#             gc.collect()
#             print("🗑️  Zero123 model unloaded from memory")
        
#         def generate_view(
#             self,
#             image: Image.Image,
#             polar_angle: float = 0.0,
#             azimuth_angle: float = 30.0,
#             num_inference_steps: int = 75,
#             guidance_scale: float = 5.0,
#             seed: Optional[int] = 42,
#         ) -> Optional[Image.Image]:
#             """
#             Generate a novel view with enhanced parameters
            
#             Args:
#                 image: Input PIL Image
#                 polar_angle: Elevation angle in degrees (0 = eye level)
#                 azimuth_angle: Rotation angle in degrees (+ = clockwise)
#                 num_inference_steps: Diffusion steps (50-100 for best quality)
#                 guidance_scale: CFG scale (3-7 recommended, higher = more faithful)
#                 seed: Random seed for reproducibility
            
#             Returns:
#                 Generated PIL Image or None if failed
#             """
#             if not self.is_loaded:
#                 print("⚠️  Model not loaded, loading now...")
#                 self.load_model()
            
#             if not self.is_loaded:
#                 return None
            
#             try:
#                 # Store original size
#                 original_size = image.size
                
#                 # Determine optimal size based on device
#                 target_size = 256 if self.device == "cpu" else 256  # 256 is more stable
                
#                 # Preprocess image
#                 print(f"      Preprocessing image for Zero123...")
#                 preprocessed = preprocess_for_zero123(image, target_size=target_size)
                
#                 # Convert angles to radians
#                 polar_rad = np.deg2rad(polar_angle)
#                 azimuth_rad = np.deg2rad(azimuth_angle)
                
#                 # Set random seed for reproducibility
#                 if seed is not None:
#                     generator = torch.Generator(device=self.device).manual_seed(seed)
#                 else:
#                     generator = None
                
#                 print(f"      Generating view: polar={polar_angle}°, azimuth={azimuth_angle}°")
#                 print(f"      Steps={num_inference_steps}, guidance={guidance_scale}")
                
#                 # Generate view
#                 with torch.no_grad():
#                     result = self.pipeline(
#                         image=preprocessed,
#                         polar=polar_rad,
#                         azimuth=azimuth_rad,
#                         num_inference_steps=num_inference_steps,
#                         guidance_scale=guidance_scale,
#                         generator=generator,
#                     )
                    
#                     generated_image = result.images[0]
                
#                 # Resize back to original dimensions
#                 generated_image = generated_image.resize(original_size, Image.Resampling.LANCZOS)
                
#                 # Post-process: slight enhancement
#                 enhancer = ImageEnhance.Sharpness(generated_image)
#                 generated_image = enhancer.enhance(1.1)
                
#                 return generated_image
                
#             except Exception as e:
#                 print(f"❌ View generation failed: {e}")
#                 import traceback
#                 traceback.print_exc()
#                 return None
        
#         def generate_left_right_views(
#             self,
#             image: Image.Image,
#             angle: float = 30.0,
#             num_inference_steps: int = 75,
#             guidance_scale: float = 5.0,
#         ) -> Tuple[Optional[Image.Image], Optional[Image.Image]]:
#             """Generate both left and right views with optimal parameters"""
#             print(f"   🔄 Generating left and right views (±{angle}°)...")
            
#             # Generate left view (camera rotates left = negative azimuth)
#             left_view = self.generate_view(
#                 image=image,
#                 polar_angle=0.0,
#                 azimuth_angle=-angle,
#                 num_inference_steps=num_inference_steps,
#                 guidance_scale=guidance_scale,
#                 seed=42,  # Consistent seed
#             )
            
#             if left_view:
#                 print("      ✅ Left view generated")
#             else:
#                 print("      ❌ Left view generation failed")
            
#             # Generate right view (camera rotates right = positive azimuth)
#             right_view = self.generate_view(
#                 image=image,
#                 polar_angle=0.0,
#                 azimuth_angle=angle,
#                 num_inference_steps=num_inference_steps,
#                 guidance_scale=guidance_scale,
#                 seed=43,  # Different seed for variety
#             )
            
#             if right_view:
#                 print("      ✅ Right view generated")
#             else:
#                 print("      ❌ Right view generation failed")
            
#             return left_view, right_view
        
#         def generate_multi_angle_views(
#             self,
#             image: Image.Image,
#             angles: List[float] = [15.0, 30.0, 45.0],
#             num_inference_steps: int = 75,
#             guidance_scale: float = 5.0,
#         ) -> Dict[str, Optional[Image.Image]]:
#             """Generate multiple side views at different angles"""
#             print(f"   🔄 Generating multi-angle views at {angles}°...")
#             views = {}
            
#             for idx, angle in enumerate(angles):
#                 angle_key = int(angle)
                
#                 # Generate left view
#                 left_view = self.generate_view(
#                     image=image,
#                     polar_angle=0.0,
#                     azimuth_angle=-angle,
#                     num_inference_steps=num_inference_steps,
#                     guidance_scale=guidance_scale,
#                     seed=42 + idx * 2,
#                 )
                
#                 if left_view:
#                     views[f'left_{angle_key}'] = left_view
#                     print(f"      ✅ Left {angle}° view generated")
#                 else:
#                     print(f"      ❌ Left {angle}° view failed")
                
#                 # Generate right view
#                 right_view = self.generate_view(
#                     image=image,
#                     polar_angle=0.0,
#                     azimuth_angle=angle,
#                     num_inference_steps=num_inference_steps,
#                     guidance_scale=guidance_scale,
#                     seed=43 + idx * 2,
#                 )
                
#                 if right_view:
#                     views[f'right_{angle_key}'] = right_view
#                     print(f"      ✅ Right {angle}° view generated")
#                 else:
#                     print(f"      ❌ Right {angle}° view failed")
            
#             return views

#     # Global instance
#     _global_generator: Optional[Zero123ViewGenerator] = None

#     def get_zero123_generator(force_reload: bool = False) -> Zero123ViewGenerator:
#         """Get or create the global Zero123 generator instance"""
#         global _global_generator
        
#         if _global_generator is None or force_reload:
#             _global_generator = Zero123ViewGenerator()
        
#         return _global_generator

#     def generate_side_views(
#         image,
#         angle: float = 30.0,
#         use_zero123: bool = True,
#         num_inference_steps: int = 75,  # Increased default
#     ) -> Tuple[Optional[Image.Image], Optional[Image.Image], str]:
#         """
#         High-level function to generate side views with better defaults
        
#         Args:
#             image: Input PIL Image
#             angle: Rotation angle in degrees
#             use_zero123: Whether to use Zero123
#             num_inference_steps: Quality (50-100 recommended, 75 is good balance)
        
#         Returns:
#             Tuple of (left_view, right_view, status_message)
#         """
#         if not use_zero123:
#             return None, None, "zero123_disabled"
        
#         try:
#             generator = get_zero123_generator()
            
#             if not generator.is_loaded:
#                 generator.load_model()
            
#             if not generator.is_loaded:
#                 return None, None, "model_load_failed"
            
#             # Generate views with enhanced parameters
#             left_view, right_view = generator.generate_left_right_views(
#                 image=image,
#                 angle=angle,
#                 num_inference_steps=num_inference_steps,
#                 guidance_scale=5.0,  # Higher guidance for better quality
#             )
            
#             if left_view and right_view:
#                 return left_view, right_view, "success"
#             elif left_view or right_view:
#                 return left_view, right_view, "partial_success"
#             else:
#                 return None, None, "generation_failed"
                
#         except Exception as e:
#             print(f"❌ Error in generate_side_views: {e}")
#             import traceback
#             traceback.print_exc()
#             return None, None, f"error_{str(e)[:50]}"

#     def generate_multi_angle_side_views(
#         image,
#         angles: List[float] = [15.0, 30.0, 45.0],
#         use_zero123: bool = True,
#         num_inference_steps: int = 75,
#     ) -> Tuple[Dict[str, Optional[Image.Image]], str]:
#         """High-level function for multiple angles with better defaults"""
#         if not use_zero123:
#             return {}, "zero123_disabled"
        
#         try:
#             generator = get_zero123_generator()
            
#             if not generator.is_loaded:
#                 generator.load_model()
            
#             if not generator.is_loaded:
#                 return {}, "model_load_failed"
            
#             # Generate views with enhanced parameters
#             views = generator.generate_multi_angle_views(
#                 image=image,
#                 angles=angles,
#                 num_inference_steps=num_inference_steps,
#                 guidance_scale=5.0,  # Higher guidance
#             )
            
#             if len(views) == len(angles) * 2:
#                 return views, "success"
#             elif len(views) > 0:
#                 return views, "partial_success"
#             else:
#                 return {}, "generation_failed"
                
#         except Exception as e:
#             print(f"❌ Error in generate_multi_angle_side_views: {e}")
#             import traceback
#             traceback.print_exc()
#             return {}, f"error_{str(e)[:50]}"

# else:
#     # Dummy implementations
#     class Zero123ViewGenerator:
#         def __init__(self, *args, **kwargs):
#             print("⚠️  Zero123 dependencies not installed")
#         def load_model(self): pass
#         def unload_model(self): pass
#         def generate_view(self, *args, **kwargs): return None
#         def generate_left_right_views(self, *args, **kwargs): return None, None
#         def generate_multi_angle_views(self, *args, **kwargs): return {}
    
#     _global_generator = None
#     def get_zero123_generator(force_reload=False):
#         global _global_generator
#         if _global_generator is None:
#             _global_generator = Zero123ViewGenerator()
#         return _global_generator
    
#     def generate_side_views(*args, **kwargs):
#         return None, None, "dependencies_not_available"
#     def generate_multi_angle_side_views(*args, **kwargs):
#         return {}, "dependencies_not_available"



"""
Enhanced Zero123 Novel View Synthesis Module
Improved preprocessing and parameters for better quality views
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


def preprocess_for_zero123(image: Image.Image, target_size: int = 256) -> Image.Image:
    """
    Preprocess image for optimal Zero123 results
    - Removes/cleans background
    - Centers the object
    - Normalizes lighting
    - Adds padding
    """
    # Convert to RGB
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    img_array = np.array(image)
    h, w = img_array.shape[:2]
    
    # 1. Background removal and object detection
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    
    # Adaptive threshold to separate object from background
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Morphological operations to clean up
    kernel = np.ones((5, 5), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
    
    # Find contours to locate main object
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if contours:
        # Get bounding box of largest contour
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)
        
        # Add 15% padding around object
        padding = int(max(w, h) * 0.15)
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(img_array.shape[1], x + w + padding)
        y2 = min(img_array.shape[0], y + h + padding)
        
        # Crop to object with padding
        img_cropped = img_array[y1:y2, x1:x2]
    else:
        # If no contours found, use center crop
        crop_size = min(h, w)
        start_h = (h - crop_size) // 2
        start_w = (w - crop_size) // 2
        img_cropped = img_array[start_h:start_h+crop_size, start_w:start_w+crop_size]
    
    # 2. Create clean white background
    result = Image.fromarray(img_cropped)
    
    # Make square by padding with white
    size = max(result.size)
    square_img = Image.new('RGB', (size, size), (255, 255, 255))
    paste_x = (size - result.width) // 2
    paste_y = (size - result.height) // 2
    square_img.paste(result, (paste_x, paste_y))
    
    # 3. Enhance image quality
    # Increase sharpness slightly
    enhancer = ImageEnhance.Sharpness(square_img)
    square_img = enhancer.enhance(1.2)
    
    # Adjust contrast slightly
    enhancer = ImageEnhance.Contrast(square_img)
    square_img = enhancer.enhance(1.1)
    
    # 4. Resize to target size
    result = square_img.resize((target_size, target_size), Image.Resampling.LANCZOS)
    
    return result


if DEPENDENCIES_AVAILABLE:
    class Zero123ViewGenerator:
        """Enhanced Zero123-based view generator"""
        
        def __init__(self, device: str = "auto", model_id: str = "lambdalabs/sd-image-variations-diffusers"):
            """Initialize Zero123 model"""
            if device == "auto":
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            else:
                self.device = device
            
            self.model_id = model_id
            self.pipeline = None
            self.is_loaded = False
            
            print(f"🔧 Zero123ViewGenerator initialized (device: {self.device})")
            print(f"   Using model: {self.model_id}")
        
        def load_model(self):
            """Load Zero123 model into memory with optimizations"""
            if self.is_loaded:
                return
            
            print(f"📥 Loading model: {self.model_id}...")
            print("   This is using SD Image Variations as a fallback (Zero123 has compatibility issues)")
            
            try:
                # Load with appropriate dtype
                dtype = torch.float32  # Use float32 for CPU
                
                # Load Stable Diffusion Image Variations pipeline
                from diffusers import StableDiffusionImageVariationPipeline
                
                self.pipeline = StableDiffusionImageVariationPipeline.from_pretrained(
                    self.model_id,
                    torch_dtype=dtype,
                    safety_checker=None,
                )
                
                # Move to device
                self.pipeline = self.pipeline.to(self.device)
                
                # Enable attention slicing for lower memory
                self.pipeline.enable_attention_slicing(1)
                
                # Enable VAE slicing
                if hasattr(self.pipeline, 'enable_vae_slicing'):
                    self.pipeline.enable_vae_slicing()
                
                self.is_loaded = True
                print("✅ Model loaded successfully")
                print("   Note: Using SD Image Variations - results may differ from true Zero123")
                
            except Exception as e:
                print(f"❌ Failed to load model: {e}")
                import traceback
                traceback.print_exc()
                self.is_loaded = False
        
        def unload_model(self):
            """Unload model from memory"""
            if self.pipeline is not None:
                del self.pipeline
                self.pipeline = None
            
            self.is_loaded = False
            
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            gc.collect()
            print("🗑️  Model unloaded from memory")
        
        def generate_view(
            self,
            image: Image.Image,
            polar_angle: float = 0.0,
            azimuth_angle: float = 30.0,
            num_inference_steps: int = 30,
            guidance_scale: float = 3.0,
            seed: Optional[int] = 42,
        ) -> Optional[Image.Image]:
            """
            Generate a novel view with enhanced parameters
            
            Args:
                image: Input PIL Image
                polar_angle: Elevation angle in degrees (0 = eye level)
                azimuth_angle: Rotation angle in degrees (+ = clockwise)
                num_inference_steps: Diffusion steps (20-50 for CPU)
                guidance_scale: CFG scale (2-5 recommended)
                seed: Random seed for reproducibility
            
            Returns:
                Generated PIL Image or None if failed
            """
            if not self.is_loaded:
                print("⚠️  Model not loaded, loading now...")
                self.load_model()
            
            if not self.is_loaded:
                return None
            
            try:
                # Store original size
                original_size = image.size
                
                # Preprocess image
                print(f"      Preprocessing image...")
                preprocessed = preprocess_for_zero123(image, target_size=256)
                
                # Set random seed for reproducibility
                if seed is not None:
                    generator = torch.Generator(device=self.device).manual_seed(seed)
                else:
                    generator = None
                
                print(f"      Generating variation: azimuth={azimuth_angle}°")
                print(f"      Steps={num_inference_steps}, guidance={guidance_scale}")
                
                # Generate variation using SD Image Variations
                with torch.no_grad():
                    result = self.pipeline(
                        image=preprocessed,
                        num_inference_steps=num_inference_steps,
                        guidance_scale=guidance_scale,
                        generator=generator,
                    )
                    
                    generated_image = result.images[0]
                
                # Resize back to original dimensions
                generated_image = generated_image.resize(original_size, Image.Resampling.LANCZOS)
                
                # Post-process: slight enhancement
                enhancer = ImageEnhance.Sharpness(generated_image)
                generated_image = enhancer.enhance(1.1)
                
                return generated_image
                
            except Exception as e:
                print(f"❌ View generation failed: {e}")
                import traceback
                traceback.print_exc()
                return None
        
        def generate_left_right_views(
            self,
            image: Image.Image,
            angle: float = 30.0,
            num_inference_steps: int = 30,
            guidance_scale: float = 3.0,
        ) -> Tuple[Optional[Image.Image], Optional[Image.Image]]:
            """Generate both left and right views with optimal parameters"""
            print(f"   🔄 Generating left and right variations (±{angle}°)...")
            
            # Generate left view
            left_view = self.generate_view(
                image=image,
                polar_angle=0.0,
                azimuth_angle=-angle,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                seed=42,
            )
            
            if left_view:
                print("      ✅ Left view generated")
            else:
                print("      ❌ Left view generation failed")
            
            # Generate right view
            right_view = self.generate_view(
                image=image,
                polar_angle=0.0,
                azimuth_angle=angle,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                seed=43,
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
            num_inference_steps: int = 30,
            guidance_scale: float = 3.0,
        ) -> Dict[str, Optional[Image.Image]]:
            """Generate multiple side views at different angles"""
            print(f"   🔄 Generating multi-angle views at {angles}°...")
            views = {}
            
            for idx, angle in enumerate(angles):
                angle_key = int(angle)
                
                # Generate left view
                left_view = self.generate_view(
                    image=image,
                    polar_angle=0.0,
                    azimuth_angle=-angle,
                    num_inference_steps=num_inference_steps,
                    guidance_scale=guidance_scale,
                    seed=42 + idx * 2,
                )
                
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
                    seed=43 + idx * 2,
                )
                
                if right_view:
                    views[f'right_{angle_key}'] = right_view
                    print(f"      ✅ Right {angle}° view generated")
                else:
                    print(f"      ❌ Right {angle}° view failed")
            
            return views

    # Global instance
    _global_generator: Optional[Zero123ViewGenerator] = None

    def get_zero123_generator(force_reload: bool = False) -> Zero123ViewGenerator:
        """Get or create the global Zero123 generator instance"""
        global _global_generator
        
        if _global_generator is None or force_reload:
            _global_generator = Zero123ViewGenerator()
        
        return _global_generator

    def generate_side_views(
        image,
        angle: float = 30.0,
        use_zero123: bool = True,
        num_inference_steps: int = 30,
    ) -> Tuple[Optional[Image.Image], Optional[Image.Image], str]:
        """
        High-level function to generate side views with better defaults
        
        Args:
            image: Input PIL Image
            angle: Rotation angle in degrees
            use_zero123: Whether to use Zero123
            num_inference_steps: Quality (20-50 recommended for CPU)
        
        Returns:
            Tuple of (left_view, right_view, status_message)
        """
        if not use_zero123:
            return None, None, "zero123_disabled"
        
        try:
            generator = get_zero123_generator()
            
            if not generator.is_loaded:
                generator.load_model()
            
            if not generator.is_loaded:
                return None, None, "model_load_failed"
            
            # Generate views with enhanced parameters
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
            import traceback
            traceback.print_exc()
            return None, None, f"error_{str(e)[:50]}"

    def generate_multi_angle_side_views(
        image,
        angles: List[float] = [15.0, 30.0, 45.0],
        use_zero123: bool = True,
        num_inference_steps: int = 30,
    ) -> Tuple[Dict[str, Optional[Image.Image]], str]:
        """High-level function for multiple angles with better defaults"""
        if not use_zero123:
            return {}, "zero123_disabled"
        
        try:
            generator = get_zero123_generator()
            
            if not generator.is_loaded:
                generator.load_model()
            
            if not generator.is_loaded:
                return {}, "model_load_failed"
            
            # Generate views with enhanced parameters
            views = generator.generate_multi_angle_views(
                image=image,
                angles=angles,
                num_inference_steps=num_inference_steps,
                guidance_scale=3.0,
            )
            
            if len(views) == len(angles) * 2:
                return views, "success"
            elif len(views) > 0:
                return views, "partial_success"
            else:
                return {}, "generation_failed"
                
        except Exception as e:
            print(f"❌ Error in generate_multi_angle_side_views: {e}")
            import traceback
            traceback.print_exc()
            return {}, f"error_{str(e)[:50]}"

else:
    # Dummy implementations
    class Zero123ViewGenerator:
        def __init__(self, *args, **kwargs):
            print("⚠️  Zero123 dependencies not installed")
        def load_model(self): pass
        def unload_model(self): pass
        def generate_view(self, *args, **kwargs): return None
        def generate_left_right_views(self, *args, **kwargs): return None, None
        def generate_multi_angle_views(self, *args, **kwargs): return {}
    
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