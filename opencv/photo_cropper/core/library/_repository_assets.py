from __future__ import annotations


from ._repository_asset_core import LibraryRepositoryAssetCoreMixin
from ._repository_asset_search import LibraryRepositoryAssetSearchMixin
from ._repository_asset_sources import LibraryRepositoryAssetSourceMixin


class LibraryRepositoryAssetMixin(
    LibraryRepositoryAssetCoreMixin,
    LibraryRepositoryAssetSearchMixin,
    LibraryRepositoryAssetSourceMixin,
):
    pass
