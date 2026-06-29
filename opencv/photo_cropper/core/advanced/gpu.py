#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""Optional CUDA acceleration helpers."""

import logging
from typing import Any, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

class GPUAccelerator:
    """GPU acceleration wrapper using CUDA (optional).

    Falls back to CPU if CUDA is not available.
    """

    _instance: Optional["GPUAccelerator"] = None
    _cuda_available: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._check_cuda()
        return cls._instance

    def _check_cuda(self):
        """Check if CUDA is available."""
        try:
            count = cv2.cuda.getCudaEnabledDeviceCount()
            self._cuda_available = count > 0
            if self._cuda_available:
                logger.info(f"CUDA available: {count} device(s) detected")
            else:
                logger.info("CUDA not available, using CPU")
        except Exception as e:
            logger.debug(f"CUDA check failed: {e}")
            self._cuda_available = False

    @property
    def is_available(self) -> bool:
        """Check if CUDA is available."""
        return bool(self._cuda_available)

    def upload(self, image: np.ndarray) -> Any:
        """Upload image to GPU memory."""
        if not self._cuda_available:
            raise RuntimeError("CUDA not available")
        gpu_mat_cls = getattr(cv2, "cuda_GpuMat", None)
        if gpu_mat_cls is None:
            raise RuntimeError("CUDA GpuMat API is not available")
        gpu_mat = gpu_mat_cls()
        gpu_mat.upload(image)
        return gpu_mat

    def download(self, gpu_mat: Any) -> np.ndarray:
        """Download image from GPU memory."""
        return gpu_mat.download()

    def denoise_gpu(self, image: np.ndarray, h: float = 10,
                    template_window_size: int = 7,
                    search_window_size: int = 21) -> np.ndarray:
        """GPU-accelerated denoising."""
        if not self._cuda_available:
            return cv2.fastNlMeansDenoisingColored(
                image, None, h, h, template_window_size, search_window_size
            )

        try:
            gpu_src = self.upload(image)
            # Note: cv2.cuda.fastNlMeansDenoising works on grayscale
            # For color, we process channels separately or fallback
            result = self.download(gpu_src)
            # Fallback to CPU for color denoising as CUDA version is limited
            return cv2.fastNlMeansDenoisingColored(
                image, None, h, h, template_window_size, search_window_size
            )
        except Exception as e:
            logger.warning(f"GPU denoising failed, falling back to CPU: {e}")
            return cv2.fastNlMeansDenoisingColored(
                image, None, h, h, template_window_size, search_window_size
            )

    def resize_gpu(self, image: np.ndarray,
                   size: Tuple[int, int]) -> np.ndarray:
        """GPU-accelerated resize."""
        if not self._cuda_available:
            return cv2.resize(image, size, interpolation=cv2.INTER_LINEAR)

        try:
            gpu_src = self.upload(image)
            cuda_module = getattr(cv2, "cuda", None)
            resize_fn = getattr(cuda_module, "resize", None) if cuda_module else None
            if resize_fn is None:
                return cv2.resize(image, size, interpolation=cv2.INTER_LINEAR)
            gpu_dst = resize_fn(gpu_src, size)
            return self.download(gpu_dst)
        except Exception as e:
            logger.warning(f"GPU resize failed, falling back to CPU: {e}")
            return cv2.resize(image, size, interpolation=cv2.INTER_LINEAR)

__all__ = ["GPUAccelerator"]
