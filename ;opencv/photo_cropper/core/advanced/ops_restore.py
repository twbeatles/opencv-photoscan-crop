from .processor import AdvancedImageProcessor

restore_old_photo = AdvancedImageProcessor.restore_old_photo
denoise_enhanced = AdvancedImageProcessor.denoise_enhanced
sharpen = AdvancedImageProcessor.sharpen

__all__ = ['restore_old_photo', 'denoise_enhanced', 'sharpen']
