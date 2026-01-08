"""
MiDaS-based depth estimation for production-grade view generation
Uses MiDaS DPT-Large for fast and accurate depth maps
"""
import torch
import numpy as np
from PIL import Image
from typing import Optional, Tuple
import cv2

try:
    import torch
    from torchvision.transforms import Compose, Resize, Normalize
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("⚠️  PyTorch not available for depth estimation")


class DepthEstimator:
    """Production-grade depth estimation using MiDaS"""
    
    def __init__(self, model_type: str = "DPT_Large", device: Optional[str] = None):
        """
        Initialize depth estimator
        
        Args:
            model_type: MiDaS model type ('DPT_Large', 'DPT_Hybrid', 'MiDaS_small')
            device: Device to run on ('cuda', 'cpu', or None for auto-detect)
        """
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch is required for depth estimation")
        
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.model_type = model_type
        self.model = None
        self.transform = None
        
        print(f"🔧 Initializing DepthEstimator with {model_type} on {self.device}")
    
    def load_model(self):
        """Lazy load the MiDaS model"""
        if self.model is not None:
            return
        
        try:
            # Load MiDaS model from torch hub
            self.model = torch.hub.load("intel-isl/MiDaS", self.model_type)
            self.model.to(self.device)
            self.model.eval()
            
            # Load transforms
            midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
            
            if self.model_type in ["DPT_Large", "DPT_Hybrid"]:
                self.transform = midas_transforms.dpt_transform
            else:
                self.transform = midas_transforms.small_transform
            
            print(f"✅ MiDaS {self.model_type} loaded successfully")
            
        except Exception as e:
            print(f"❌ Failed to load MiDaS model: {e}")
            raise
    
    def estimate_depth(
        self, 
        image: Image.Image,
        output_size: Optional[Tuple[int, int]] = None
    ) -> np.ndarray:
        """
        Estimate depth map from RGB image
        
        Args:
            image: Input PIL Image (RGB)
            output_size: Optional (width, height) to resize output depth map
        
        Returns:
            Normalized depth map (H x W) as float32 numpy array [0, 1]
            Closer objects have HIGHER values
        """
        self.load_model()
        
        # Convert PIL to numpy
        img_np = np.array(image)
        
        # Apply MiDaS transform
        input_batch = self.transform(img_np).to(self.device)
        
        # Run inference
        with torch.no_grad():
            prediction = self.model(input_batch)
            
            # Interpolate to original size
            prediction = torch.nn.functional.interpolate(
                prediction.unsqueeze(1),
                size=img_np.shape[:2],
                mode="bicubic",
                align_corners=False,
            ).squeeze()
        
        # Convert to numpy
        depth_map = prediction.cpu().numpy()
        
        # Normalize to [0, 1]
        depth_min = depth_map.min()
        depth_max = depth_map.max()
        
        if depth_max - depth_min > 1e-6:
            depth_map = (depth_map - depth_min) / (depth_max - depth_min)
        else:
            depth_map = np.zeros_like(depth_map)
        
        # Resize if requested
        if output_size is not None:
            depth_map = cv2.resize(depth_map, output_size, interpolation=cv2.INTER_LINEAR)
        
        return depth_map.astype(np.float32)
    
    def estimate_depth_with_confidence(
        self, 
        image: Image.Image
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Estimate depth with confidence map
        
        Returns:
            depth_map: Normalized depth [0, 1]
            confidence_map: Confidence scores [0, 1]
        """
        depth_map = self.estimate_depth(image)
        
        # Simple confidence based on local variance
        # High variance areas = less confident
        kernel_size = 5
        kernel = np.ones((kernel_size, kernel_size), np.float32) / (kernel_size ** 2)
        
        local_mean = cv2.filter2D(depth_map, -1, kernel)
        local_sq_mean = cv2.filter2D(depth_map ** 2, -1, kernel)
        local_var = local_sq_mean - local_mean ** 2
        
        # Invert variance to get confidence (normalize)
        confidence_map = 1.0 - np.clip(local_var * 10, 0, 1)
        
        return depth_map, confidence_map
    
    def visualize_depth(self, depth_map: np.ndarray) -> Image.Image:
        """
        Convert depth map to colorized visualization
        
        Args:
            depth_map: Normalized depth map [0, 1]
        
        Returns:
            PIL Image with colorized depth
        """
        # Apply colormap
        depth_color = cv2.applyColorMap(
            (depth_map * 255).astype(np.uint8),
            cv2.COLORMAP_INFERNO
        )
        
        # Convert BGR to RGB
        depth_color = cv2.cvtColor(depth_color, cv2.COLOR_BGR2RGB)
        
        return Image.fromarray(depth_color)


# Global instance for reuse (lazy loaded)
_global_depth_estimator: Optional[DepthEstimator] = None


def get_depth_estimator(model_type: str = "DPT_Large") -> DepthEstimator:
    """Get or create global depth estimator instance"""
    global _global_depth_estimator
    
    if _global_depth_estimator is None:
        _global_depth_estimator = DepthEstimator(model_type=model_type)
    
    return _global_depth_estimator


def estimate_depth_fast(image: Image.Image) -> np.ndarray:
    """
    Quick helper function for depth estimation
    
    Args:
        image: Input PIL Image
    
    Returns:
        Normalized depth map [0, 1]
    """
    estimator = get_depth_estimator()
    return estimator.estimate_depth(image)
