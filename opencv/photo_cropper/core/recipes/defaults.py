from __future__ import annotations

from .record import RecipeRecord

DEFAULT_RECIPES: dict[str, RecipeRecord] = {
    "문서 스캔": RecipeRecord(
        name="문서 스캔",
        description="문서 스캔/배치 처리에 맞춘 기본 레시피입니다.",
        settings_snapshot={
            "algorithm": {
                "canny_min": 30,
                "canny_max": 100,
                "use_clahe": True,
                "clahe_clip_limit": 2.5,
                "multi_scale_edge": True,
                "contour_scoring": "strict",
            },
            "processing": {
                "auto_contrast": True,
                "apply_sharpening": True,
                "sharpening_strength": 1.2,
                "denoise": True,
                "denoise_strength": 8,
            },
            "output": {
                "output_format": "PNG",
                "png_compression": 6,
            },
        },
        origin="default",
    ),
    "앨범 사진": RecipeRecord(
        name="앨범 사진",
        description="일반 사진 인화본 처리에 맞춘 균형형 레시피입니다.",
        settings_snapshot={
            "algorithm": {
                "canny_min": 50,
                "canny_max": 150,
                "use_clahe": True,
                "clahe_clip_limit": 2.0,
                "multi_scale_edge": True,
                "contour_scoring": "enhanced",
            },
            "processing": {
                "auto_contrast": True,
            },
            "output": {
                "output_format": "JPG",
                "jpg_quality": 95,
            },
        },
        origin="default",
    ),
    "오래된 앨범": RecipeRecord(
        name="오래된 앨범",
        description="오래된 사진 복원을 위한 개선형 레시피입니다.",
        settings_snapshot={
            "algorithm": {
                "canny_min": 40,
                "canny_max": 120,
                "use_clahe": True,
                "clahe_clip_limit": 3.0,
            },
            "processing": {
                "denoise": True,
                "denoise_strength": 12,
            },
            "advanced": {
                "auto_color_correct": True,
                "restore_old_photo": True,
            },
            "output": {
                "output_format": "JPG",
                "jpg_quality": 95,
            },
        },
        origin="default",
    ),
    "빠른 처리": RecipeRecord(
        name="빠른 처리",
        description="속도 우선 배치용 레시피입니다.",
        settings_snapshot={
            "algorithm": {
                "use_clahe": False,
                "multi_scale_edge": False,
                "use_corner_detection": False,
            },
            "processing": {
                "auto_contrast": False,
                "denoise": False,
            },
            "performance": {
                "thread_count": 8,
                "enable_multithreading": True,
            },
            "output": {
                "output_format": "JPG",
                "jpg_quality": 85,
            },
        },
        origin="default",
    ),
    "인물 사진": RecipeRecord(
        name="인물 사진",
        description="얼굴 중심 처리에 맞춘 레시피입니다.",
        settings_snapshot={
            "algorithm": {
                "use_clahe": True,
                "clahe_clip_limit": 1.5,
            },
            "processing": {
                "denoise": True,
                "denoise_strength": 8,
                "apply_sharpening": True,
                "sharpening_strength": 0.3,
            },
            "classification": {
                "enabled": True,
            },
            "face_detection": {
                "enabled": True,
                "auto_center_crop": True,
            },
            "output": {
                "output_format": "JPG",
                "jpg_quality": 95,
            },
        },
        origin="default",
    ),
}

__all__ = ["DEFAULT_RECIPES"]
