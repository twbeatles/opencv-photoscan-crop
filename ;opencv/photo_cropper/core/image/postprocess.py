from .processor import ImageProcessor

apply_post_processing = ImageProcessor._apply_post_processing
save_image = ImageProcessor.save_image

__all__ = ['apply_post_processing', 'save_image']
