from __future__ import annotations

import json
import os
from typing import Any, Optional

from ...utils.file_helpers import compute_file_hash, get_image_dimensions
from .types import AssetQuery, AssetTimelineEvent
from ._repository_shared import compute_perceptual_hash, now_iso, safe_json_loads


from ._repository_asset_core import LibraryRepositoryAssetCoreMixin
from ._repository_asset_search import LibraryRepositoryAssetSearchMixin
from ._repository_asset_sources import LibraryRepositoryAssetSourceMixin


class LibraryRepositoryAssetMixin(
    LibraryRepositoryAssetCoreMixin,
    LibraryRepositoryAssetSearchMixin,
    LibraryRepositoryAssetSourceMixin,
):
    pass
