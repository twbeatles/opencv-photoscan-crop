from __future__ import annotations

from .repository import LibraryRepository
from .types import AssetQuery


class QueryService:
    def __init__(self, repository: LibraryRepository):
        self.repository = repository

    def list_assets(
        self,
        query: AssetQuery | None = None,
        *,
        search_text: str = "",
        collection_id: int | None = None,
        tag_names: tuple[str, ...] | list[str] | None = None,
        review_status: str = "",
        sort_by: str = "updated",
        page: int = 1,
        page_size: int = 200,
        limit: int | None = None,
    ) -> list[dict]:
        asset_query = query or AssetQuery(
            search_text=search_text,
            collection_id=collection_id,
            tag_names=tuple(tag_names or ()),
            review_status=review_status,
            sort_by=sort_by,
            page=1 if limit is not None else page,
            page_size=int(limit or page_size),
        )
        return self.repository.list_assets(asset_query=asset_query)

    def count_assets(self, query: AssetQuery | None = None) -> int:
        return self.repository.count_assets(query)

    def get_asset_detail(self, asset_id: int):
        return self.repository.get_asset_detail(asset_id)

    def get_asset_timeline(self, asset_id: int):
        return self.repository.get_asset_timeline(asset_id)

    def list_jobs(self, *, limit: int = 200) -> list[dict]:
        return self.repository.list_jobs(limit=limit)

    def get_job(self, job_id: int):
        return self.repository.get_job(job_id)

    def list_job_items(
        self,
        job_id: int,
        *,
        statuses: list[str] | tuple[str, ...] | None = None,
    ) -> list[dict]:
        return self.repository.list_job_items(job_id, statuses=statuses)

    def list_review_items(self, *, limit: int = 500) -> list[dict]:
        return self.repository.list_review_items(limit=limit)

    def list_duplicate_groups(self, *, kind: str = "exact") -> list[dict]:
        return self.repository.list_duplicate_groups(kind=kind)

    def list_duplicate_members(self, group_id: int) -> list[dict]:
        return self.repository.list_duplicate_group_members(group_id)

    def list_collections(self) -> list[dict]:
        return self.repository.list_collections()

    def list_tags(self) -> list[dict]:
        return self.repository.list_tags()

    def list_people_for_asset(self, asset_id: int) -> list[dict]:
        return self.repository.list_people_for_asset(asset_id)

    def list_ocr_documents(self, asset_id: int) -> list[dict]:
        return self.repository.list_ocr_documents(asset_id)

    def list_recipes(self) -> list[dict]:
        return self.repository.list_recipes()
