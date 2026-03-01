from .detector import FaceDetector

detect_faces_cascade = FaceDetector._detect_faces_cascade
detect_eyes = FaceDetector._detect_eyes

__all__ = ['detect_faces_cascade', 'detect_eyes']
