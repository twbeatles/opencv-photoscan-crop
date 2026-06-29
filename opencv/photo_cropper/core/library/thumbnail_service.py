from __future__ import annotations

import hashlib
import os

from PIL import Image, ImageOps

from ..app_paths import get_thumbnails_dir


class ThumbnailService:
    def __init__(self, thumbnails_dir: str | None = None, size: int = 192):
        self.thumbnails_dir = thumbnails_dir or get_thumbnails_dir()
        self.size = max(64, int(size))
        os.makedirs(self.thumbnails_dir, exist_ok=True)

    def _thumb_name(self, file_path: str) -> str:
        try:
            stat = os.stat(file_path)
            mtime_ns = int(getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1e9)))
        except Exception:
            mtime_ns = 0
        token = f"{os.path.abspath(file_path)}::{mtime_ns}".encode("utf-8", errors="ignore")
        digest = hashlib.sha256(token).hexdigest()
        return os.path.join(self.thumbnails_dir, f"{digest}.png")

    def ensure_thumbnail(self, file_path: str) -> str:
        output_path = self._thumb_name(file_path)
        if os.path.exists(output_path):
            return output_path
        try:
            with Image.open(file_path) as image:
                image = ImageOps.exif_transpose(image)
                image.thumbnail((self.size, self.size))
                canvas = Image.new("RGBA", (self.size, self.size), (18, 18, 18, 255))
                x = (self.size - image.width) // 2
                y = (self.size - image.height) // 2
                canvas.paste(image.convert("RGBA"), (x, y))
                canvas.save(output_path, format="PNG")
        except Exception:
            return ""
        return output_path
