from .processor import ImageProcessor

resolve_debug_root = ImageProcessor._resolve_debug_root
save_debug_image = ImageProcessor._save_debug_image

__all__ = ['resolve_debug_root', 'save_debug_image']
