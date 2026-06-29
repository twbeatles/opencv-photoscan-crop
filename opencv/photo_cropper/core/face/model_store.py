from .detector import FaceDetector

get_model_cache_dir = FaceDetector._get_model_cache_dir
ensure_dnn_models = FaceDetector._ensure_dnn_models

__all__ = ['get_model_cache_dir', 'ensure_dnn_models']
