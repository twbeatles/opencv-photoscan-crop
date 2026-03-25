#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Processed-output index for reliable skip-processed checks."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)

INDEX_VERSION = 2
INDEX_DIRNAME = ".photocropper"
INDEX_FILENAME = "processed_index.json"
RECORD_STATUS_SUCCESS = "success"
RECORD_STATUS_PARTIAL = "partial"


def _now_iso_utc() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _abs_norm(path: str) -> str:
    return os.path.normcase(os.path.abspath(str(path or "")))


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _unique_paths(paths: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    result: List[str] = []
    for raw in paths:
        candidate = str(raw or "").strip()
        if not candidate:
            continue
        normalized = _abs_norm(candidate)
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _normalize_record_status(value: Any) -> str:
    status = str(value or "").strip().lower()
    if status == RECORD_STATUS_PARTIAL:
        return RECORD_STATUS_PARTIAL
    return RECORD_STATUS_SUCCESS


def build_pipeline_signature(settings_obj: Any) -> str:
    """Build deterministic pipeline signature from settings payload."""
    if hasattr(settings_obj, "to_dict"):
        payload = dict(settings_obj.to_dict())
    elif isinstance(settings_obj, dict):
        payload = dict(settings_obj)
    else:
        payload = {}

    # Exclude runtime/UI-only fields that do not change output rendering/routing.
    for key in (
        "last_input_path",
        "last_output_path",
        "ui",
        "watch_mode",
        "notification",
        "debug",
        "create_backup",
    ):
        payload.pop(key, None)

    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class ProcessedIndexStore:
    """Per-output-root processed record index with atomic persistence."""

    def __init__(self, output_dir: str):
        self.output_dir = _abs_norm(output_dir)
        self._index_root = os.path.join(self.output_dir, INDEX_DIRNAME)
        self._index_path = os.path.join(self._index_root, INDEX_FILENAME)
        self._lock = threading.RLock()

        self._loaded = False
        self._usable = True
        self._error: str = ""

        self._records: Dict[Tuple[str, int, int, str], Dict[str, Any]] = {}

    @property
    def index_path(self) -> str:
        return self._index_path

    @property
    def is_usable(self) -> bool:
        with self._lock:
            self._ensure_loaded()
            return self._usable

    @property
    def last_error(self) -> str:
        with self._lock:
            return self._error

    def _mark_unusable(self, message: str) -> None:
        self._usable = False
        self._error = str(message or "processed index unavailable")

    def _normalize_record(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(raw, dict):
            return None

        source_path = _abs_norm(str(raw.get("source_path") or "").strip())
        if not source_path:
            return None

        size = _as_int(raw.get("size"), default=-1)
        mtime_ns = _as_int(raw.get("mtime_ns"), default=-1)
        if size < 0 or mtime_ns < 0:
            return None

        pipeline_signature = str(raw.get("pipeline_signature") or "").strip()
        if not pipeline_signature:
            return None

        outputs = _unique_paths(raw.get("outputs") or [])
        if not outputs:
            return None

        return {
            "source_path": source_path,
            "size": size,
            "mtime_ns": mtime_ns,
            "outputs": outputs,
            "pipeline_signature": pipeline_signature,
            "status": _normalize_record_status(raw.get("status")),
        }

    @staticmethod
    def _record_key(record: Dict[str, Any]) -> Tuple[str, int, int, str]:
        return (
            str(record["source_path"]),
            int(record["size"]),
            int(record["mtime_ns"]),
            str(record["pipeline_signature"]),
        )

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        self._loaded = True
        self._records = {}

        if not os.path.exists(self._index_path):
            return

        try:
            with open(self._index_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception as exc:
            logger.warning("Failed to read processed index (%s): %s", self._index_path, exc)
            self._mark_unusable(f"read_error: {exc}")
            return

        if not isinstance(payload, dict):
            self._mark_unusable("invalid_payload")
            return

        records = payload.get("records")
        if not isinstance(records, list):
            self._mark_unusable("invalid_records")
            return

        for raw in records:
            normalized = self._normalize_record(raw)
            if not normalized:
                continue
            self._records[self._record_key(normalized)] = normalized

    def _snapshot_records(self) -> List[Dict[str, Any]]:
        records = list(self._records.values())
        records.sort(
            key=lambda item: (
                str(item.get("source_path") or ""),
                int(item.get("mtime_ns") or 0),
                str(item.get("pipeline_signature") or ""),
            )
        )
        return records

    def _save_locked(self) -> bool:
        if not self._usable:
            return False

        try:
            os.makedirs(self._index_root, exist_ok=True)
            payload = {
                "version": INDEX_VERSION,
                "updated_at": _now_iso_utc(),
                "records": self._snapshot_records(),
            }
            tmp_path = f"{self._index_path}.tmp"
            with open(tmp_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
            os.replace(tmp_path, self._index_path)
            return True
        except Exception as exc:
            logger.warning("Failed to write processed index (%s): %s", self._index_path, exc)
            self._mark_unusable(f"write_error: {exc}")
            return False

    def lookup_outputs(
        self,
        source_path: str,
        size: int,
        mtime_ns: int,
        pipeline_signature: str,
    ) -> Tuple[Optional[List[str]], bool, str]:
        """Return matched outputs, whether index is usable, and record status."""
        with self._lock:
            self._ensure_loaded()
            if not self._usable:
                return None, False, ""

            key = (_abs_norm(source_path), int(size), int(mtime_ns), str(pipeline_signature))
            record = self._records.get(key)
            if record is None:
                return None, True, ""

            outputs = [p for p in list(record.get("outputs") or []) if os.path.exists(p)]
            status = _normalize_record_status(record.get("status"))
            if outputs:
                return outputs, True, status

            # Stale record without surviving outputs: remove it.
            self._records.pop(key, None)
            self._save_locked()
            return None, True, ""

    def upsert_record(
        self,
        source_path: str,
        size: int,
        mtime_ns: int,
        outputs: Iterable[str],
        pipeline_signature: str,
        status: str = RECORD_STATUS_SUCCESS,
    ) -> bool:
        with self._lock:
            self._ensure_loaded()
            if not self._usable:
                return False

            normalized_outputs = _unique_paths(outputs)
            if not normalized_outputs:
                return False

            record = {
                "source_path": _abs_norm(source_path),
                "size": int(size),
                "mtime_ns": int(mtime_ns),
                "outputs": normalized_outputs,
                "pipeline_signature": str(pipeline_signature),
                "status": _normalize_record_status(status),
            }
            self._records[self._record_key(record)] = record
            return self._save_locked()
