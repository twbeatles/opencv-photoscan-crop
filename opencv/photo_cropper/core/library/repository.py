from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Optional

from ...utils.file_helpers import compute_file_hash, get_image_dimensions
from .sqlite_store import LibrarySqliteStore
from .types import AssetQuery, AssetTimelineEvent


from ._repository_shared import compute_perceptual_hash, now_iso, safe_json_loads
from ._repository_assets import LibraryRepositoryAssetMixin
from ._repository_jobs import LibraryRepositoryJobMixin
from ._repository_queries import LibraryRepositoryQueryMixin
from ._repository_metadata import LibraryRepositoryMetadataMixin
from ._repository_duplicates import LibraryRepositoryDuplicateMixin
from ._repository_recipes import LibraryRepositoryRecipeMixin


class LibraryRepository(
    LibraryRepositoryAssetMixin,
    LibraryRepositoryJobMixin,
    LibraryRepositoryQueryMixin,
    LibraryRepositoryMetadataMixin,
    LibraryRepositoryDuplicateMixin,
    LibraryRepositoryRecipeMixin,
):
    def __init__(self, store: Optional[LibrarySqliteStore] = None):
        self.store = store or LibrarySqliteStore()
        self.store.ensure_initialized()

    @property
    def db_path(self) -> str:
        return self.store.db_path

    @property
    def fts_enabled(self) -> bool:
        return self.store.fts_enabled









































































_repository_instance: Optional[LibraryRepository] = None


def get_library_repository() -> LibraryRepository:
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = LibraryRepository()
    return _repository_instance


def reset_library_repository_for_tests() -> None:
    """Clear the cached repository singleton (test/agent isolation)."""
    global _repository_instance
    _repository_instance = None
