from __future__ import annotations

import os
from typing import Any, Optional, cast

import cv2
import numpy as np

from ...utils.image_io import load_image_unicode
from .repository import LibraryRepository
from .types import AssetQuery


class DuplicateService:
    def __init__(self, repository: LibraryRepository):
        self.repository = repository

    def rebuild_exact_groups(self) -> int:
        current_groups = {
            str(group.get("signature", "") or ""): group
            for group in self.repository.list_duplicate_groups(kind="exact")
        }
        preferences = self.repository.get_duplicate_member_preferences("exact")
        active_signatures: list[str] = []
        with self.repository.store.connect() as conn:
            rows = conn.execute(
                """
                SELECT exact_hash, GROUP_CONCAT(id) AS asset_ids
                FROM assets
                WHERE exact_hash != ''
                GROUP BY exact_hash
                HAVING COUNT(*) > 1
                """
            ).fetchall()
        created = 0
        for row in rows:
            hash_value = str(row["exact_hash"] or "")
            asset_ids = [
                int(item)
                for item in str(row["asset_ids"] or "").split(",")
                if str(item).strip()
            ]
            if len(asset_ids) < 2:
                continue
            signature = f"exact:{hash_value}"
            representative = self._choose_representative(
                kind="exact",
                asset_ids=asset_ids,
                signature=signature,
                preferences=preferences,
                current_groups=current_groups,
            )
            self.repository.replace_duplicate_group(
                kind="exact",
                signature=signature,
                representative_asset_id=representative,
                asset_ids=asset_ids,
            )
            active_signatures.append(signature)
            created += 1
        self.repository.prune_duplicate_groups("exact", active_signatures)
        return created

    @staticmethod
    def _phash(file_path: str) -> str:
        try:
            image = load_image_unicode(file_path, cv2.IMREAD_GRAYSCALE)
            if image is None:
                return ""
            image = cv2.resize(image, (32, 32))
            image = np.float32(image)
            dct = cv2.dct(cast(Any, image))
            low = dct[:8, :8]
            median = np.median(low[1:, :].flatten())
            bits = low > median
            return "".join("1" if bool(flag) else "0" for flag in bits.flatten())
        except Exception:
            return ""

    @staticmethod
    def _hamming(left: str, right: str) -> int:
        if len(left) != len(right):
            return 9999
        return sum(1 for a, b in zip(left, right) if a != b)

    def refresh_perceptual_hashes(
        self,
        asset_ids: Optional[list[int] | tuple[int, ...]] = None,
    ) -> int:
        if asset_ids is None:
            assets = self.repository.list_assets(
                asset_query=AssetQuery(page=1, page_size=5000)
            )
        else:
            wanted = {int(item) for item in asset_ids if int(item) > 0}
            assets = [
                asset
                for asset in self.repository.list_assets(
                    asset_query=AssetQuery(page=1, page_size=max(len(wanted), 1))
                )
                if int(asset.get("id", 0) or 0) in wanted
            ]

        updated = 0
        for asset in assets:
            asset_id = int(asset.get("id", 0) or 0)
            if asset_id <= 0:
                continue
            visual_path = self.repository.get_asset_visual_path(asset_id)
            if not visual_path or not os.path.exists(visual_path):
                self.repository.set_asset_perceptual_hash(asset_id, "")
                continue
            phash = self._phash(visual_path)
            self.repository.set_asset_perceptual_hash(asset_id, phash)
            updated += 1
        return updated

    def rebuild_near_groups(self, *, max_distance: int = 16, limit: int = 2000) -> int:
        current_groups = {
            str(group.get("signature", "") or ""): group
            for group in self.repository.list_duplicate_groups(kind="near")
        }
        preferences = self.repository.get_duplicate_member_preferences("near")
        active_signatures: list[str] = []
        assets = self.repository.list_assets(
            asset_query=AssetQuery(page=1, page_size=max(int(limit or 2000), 1))
        )
        records = []
        for asset in assets:
            asset_id = int(asset.get("id", 0) or 0)
            if asset_id <= 0:
                continue
            visual_path = self.repository.get_asset_visual_path(asset_id)
            if not visual_path or not os.path.exists(visual_path):
                continue
            phash = str(asset.get("perceptual_hash", "") or "")
            if not phash:
                phash = self._phash(visual_path)
                self.repository.set_asset_perceptual_hash(asset_id, phash)
            if not phash:
                continue
            records.append(
                {
                    "asset_id": asset_id,
                    "path": visual_path,
                    "phash": phash,
                    "exact_hash": str(asset.get("exact_hash", "") or ""),
                }
            )

        parent: dict[int, int] = {}

        def find(node: int) -> int:
            parent.setdefault(node, node)
            while parent[node] != node:
                parent[node] = parent[parent[node]]
                node = parent[node]
            return node

        def union(left: int, right: int) -> None:
            left_root = find(left)
            right_root = find(right)
            if left_root != right_root:
                parent[right_root] = left_root

        for index, left in enumerate(records):
            for right in records[index + 1 :]:
                if left["exact_hash"] and left["exact_hash"] == right["exact_hash"]:
                    continue
                if self._hamming(left["phash"], right["phash"]) <= int(max_distance):
                    union(int(left["asset_id"]), int(right["asset_id"]))

        groups: dict[int, list[int]] = {}
        for record in records:
            asset_id = int(record["asset_id"])
            root = find(asset_id)
            groups.setdefault(root, []).append(asset_id)

        created = 0
        for asset_ids in groups.values():
            unique_ids = sorted(set(int(item) for item in asset_ids))
            if len(unique_ids) < 2:
                continue
            signature = "near:" + ",".join(str(item) for item in unique_ids)
            representative = self._choose_representative(
                kind="near",
                asset_ids=unique_ids,
                signature=signature,
                preferences=preferences,
                current_groups=current_groups,
            )
            self.repository.replace_duplicate_group(
                kind="near",
                signature=signature,
                representative_asset_id=representative,
                asset_ids=unique_ids,
            )
            active_signatures.append(signature)
            created += 1
        self.repository.prune_duplicate_groups("near", active_signatures)
        return created

    def list_groups(self, *, kind: str | None = "exact") -> list[dict]:
        return self.repository.list_duplicate_groups(kind=kind)

    def list_members(self, group_id: int) -> list[dict]:
        return self.repository.list_duplicate_group_members(group_id)

    def set_representative(self, group_id: int, asset_id: int) -> None:
        self.repository.set_duplicate_representative(group_id, asset_id)

    def set_excluded(self, group_id: int, asset_id: int, excluded: bool) -> None:
        self.repository.set_duplicate_member_excluded(group_id, asset_id, excluded)

    def set_member_preference(
        self,
        kind: str,
        asset_id: int,
        *,
        excluded: Optional[bool] = None,
        prefer_representative: Optional[bool] = None,
    ) -> None:
        self.repository.set_duplicate_member_preference(
            kind,
            asset_id,
            excluded=excluded,
            prefer_representative=prefer_representative,
        )

    def _choose_representative(
        self,
        *,
        kind: str,
        asset_ids: list[int],
        signature: str,
        preferences: dict[int, dict],
        current_groups: dict[str, dict],
    ) -> int:
        unique_ids = sorted({int(item) for item in asset_ids if int(item) > 0})
        if not unique_ids:
            return 0

        preferred = [
            asset_id
            for asset_id in unique_ids
            if bool(int(preferences.get(asset_id, {}).get("prefer_representative", 0) or 0))
        ]
        if len(preferred) == 1:
            return preferred[0]

        existing_group = current_groups.get(signature)
        if existing_group is not None:
            representative = int(existing_group.get("representative_asset_id", 0) or 0)
            if representative in unique_ids:
                return representative

        carried = []
        for group in self.repository.list_duplicate_groups(kind=kind):
            group_id = int(group.get("id", 0) or 0)
            representative = int(group.get("representative_asset_id", 0) or 0)
            if group_id <= 0 or representative not in unique_ids:
                continue
            members = self.repository.list_duplicate_group_members(group_id)
            member_ids = {int(item.get("asset_id", 0) or 0) for item in members}
            if member_ids.intersection(unique_ids):
                carried.append(representative)
        carried = sorted(set(carried))
        if len(carried) == 1:
            return carried[0]
        return unique_ids[0]
