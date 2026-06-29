from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(slots=True)
class AssetQuery:
    search_text: str = ""
    collection_id: Optional[int] = None
    tag_names: tuple[str, ...] = ()
    review_status: str = ""
    sort_by: str = "updated"
    page: int = 1
    page_size: int = 200

    @property
    def normalized_page(self) -> int:
        return max(1, int(self.page or 1))

    @property
    def normalized_page_size(self) -> int:
        return max(1, int(self.page_size or 200))

    @property
    def offset(self) -> int:
        return (self.normalized_page - 1) * self.normalized_page_size


@dataclass(slots=True)
class AssetTimelineEvent:
    event_type: str
    timestamp: str
    asset_id: int
    source_id: Optional[int] = None
    variant_id: Optional[int] = None
    job_id: Optional[int] = None
    label: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

