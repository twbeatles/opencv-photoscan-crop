from .processor import ImageProcessor

detect_edges_multiscale = ImageProcessor.detect_edges_multiscale
find_best_contour = ImageProcessor.find_best_contour

__all__ = ['detect_edges_multiscale', 'find_best_contour']
