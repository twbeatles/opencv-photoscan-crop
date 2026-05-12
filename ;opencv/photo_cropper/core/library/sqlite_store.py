from __future__ import annotations

import os
import sqlite3
import threading
from contextlib import contextmanager
from typing import Iterator

from ..app_paths import get_library_db_path, ensure_library_dirs


SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        display_name TEXT NOT NULL,
        note TEXT NOT NULL DEFAULT '',
        exact_hash TEXT NOT NULL DEFAULT '',
        perceptual_hash TEXT NOT NULL DEFAULT '',
        perceptual_hash_updated_at TEXT NOT NULL DEFAULT '',
        primary_source_path TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS asset_sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_id INTEGER NOT NULL,
        source_path TEXT NOT NULL UNIQUE,
        source_hash TEXT NOT NULL DEFAULT '',
        file_size INTEGER NOT NULL DEFAULT 0,
        mtime_ns INTEGER NOT NULL DEFAULT 0,
        width INTEGER NOT NULL DEFAULT 0,
        height INTEGER NOT NULL DEFAULT 0,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        ingested_at TEXT NOT NULL,
        last_seen_at TEXT NOT NULL,
        is_missing INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY(asset_id) REFERENCES assets(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS asset_variants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_id INTEGER NOT NULL,
        source_id INTEGER,
        variant_kind TEXT NOT NULL,
        file_path TEXT NOT NULL UNIQUE,
        recipe_name TEXT NOT NULL DEFAULT '',
        job_item_id INTEGER,
        file_size_kb REAL NOT NULL DEFAULT 0.0,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        FOREIGN KEY(asset_id) REFERENCES assets(id),
        FOREIGN KEY(source_id) REFERENCES asset_sources(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS collections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS collection_assets (
        collection_id INTEGER NOT NULL,
        asset_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY(collection_id, asset_id),
        FOREIGN KEY(collection_id) REFERENCES collections(id),
        FOREIGN KEY(asset_id) REFERENCES assets(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        kind TEXT NOT NULL DEFAULT 'user',
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS asset_tags (
        asset_id INTEGER NOT NULL,
        tag_id INTEGER NOT NULL,
        source TEXT NOT NULL DEFAULT 'user',
        confidence REAL NOT NULL DEFAULT 1.0,
        created_at TEXT NOT NULL,
        PRIMARY KEY(asset_id, tag_id, source),
        FOREIGN KEY(asset_id) REFERENCES assets(id),
        FOREIGN KEY(tag_id) REFERENCES tags(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS faces (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_id INTEGER NOT NULL,
        source_id INTEGER,
        variant_id INTEGER,
        x INTEGER NOT NULL,
        y INTEGER NOT NULL,
        w INTEGER NOT NULL,
        h INTEGER NOT NULL,
        confidence REAL NOT NULL DEFAULT 0.0,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        FOREIGN KEY(asset_id) REFERENCES assets(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS people (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL DEFAULT '',
        provider TEXT NOT NULL DEFAULT '',
        external_id TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS person_faces (
        person_id INTEGER NOT NULL,
        face_id INTEGER NOT NULL,
        confidence REAL NOT NULL DEFAULT 0.0,
        created_at TEXT NOT NULL DEFAULT '',
        PRIMARY KEY(person_id, face_id),
        FOREIGN KEY(person_id) REFERENCES people(id),
        FOREIGN KEY(face_id) REFERENCES faces(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT NOT NULL DEFAULT '',
        settings_snapshot TEXT NOT NULL DEFAULT '{}',
        category_rules TEXT NOT NULL DEFAULT '{}',
        origin TEXT NOT NULL DEFAULT 'user',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS process_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_kind TEXT NOT NULL,
        status TEXT NOT NULL,
        input_path TEXT NOT NULL DEFAULT '',
        output_path TEXT NOT NULL DEFAULT '',
        recipe_name TEXT NOT NULL DEFAULT '',
        total_items INTEGER NOT NULL DEFAULT 0,
        processed_items INTEGER NOT NULL DEFAULT 0,
        success_count INTEGER NOT NULL DEFAULT 0,
        partial_count INTEGER NOT NULL DEFAULT 0,
        failed_count INTEGER NOT NULL DEFAULT 0,
        skipped_count INTEGER NOT NULL DEFAULT 0,
        started_at TEXT NOT NULL,
        finished_at TEXT NOT NULL DEFAULT '',
        summary_json TEXT NOT NULL DEFAULT '{}'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS process_job_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        source_path TEXT NOT NULL DEFAULT '',
        asset_id INTEGER,
        source_id INTEGER,
        status TEXT NOT NULL,
        message TEXT NOT NULL DEFAULT '',
        output_paths_json TEXT NOT NULL DEFAULT '[]',
        processing_time_ms REAL NOT NULL DEFAULT 0.0,
        created_at TEXT NOT NULL,
        FOREIGN KEY(job_id) REFERENCES process_jobs(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS duplicate_groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kind TEXT NOT NULL,
        signature TEXT NOT NULL UNIQUE,
        representative_asset_id INTEGER,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS duplicate_group_members (
        group_id INTEGER NOT NULL,
        asset_id INTEGER NOT NULL,
        role TEXT NOT NULL DEFAULT 'member',
        is_excluded INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY(group_id, asset_id),
        FOREIGN KEY(group_id) REFERENCES duplicate_groups(id),
        FOREIGN KEY(asset_id) REFERENCES assets(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS duplicate_member_preferences (
        kind TEXT NOT NULL,
        asset_id INTEGER NOT NULL,
        is_excluded INTEGER NOT NULL DEFAULT 0,
        prefer_representative INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL,
        PRIMARY KEY(kind, asset_id),
        FOREIGN KEY(asset_id) REFERENCES assets(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS review_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_id INTEGER,
        source_id INTEGER,
        variant_id INTEGER,
        job_id INTEGER,
        job_item_id INTEGER,
        status TEXT NOT NULL,
        reason TEXT NOT NULL DEFAULT '',
        notes TEXT NOT NULL DEFAULT '',
        action_context_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ocr_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_id INTEGER,
        source_id INTEGER,
        variant_id INTEGER,
        provider TEXT NOT NULL DEFAULT '',
        text TEXT NOT NULL DEFAULT '',
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS app_state (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL DEFAULT '',
        updated_at TEXT NOT NULL
    )
    """,
]


MIGRATION_STATEMENTS = [
    "ALTER TABLE assets ADD COLUMN perceptual_hash TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE assets ADD COLUMN perceptual_hash_updated_at TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE review_items ADD COLUMN action_context_json TEXT NOT NULL DEFAULT '{}'",
    "ALTER TABLE person_faces ADD COLUMN created_at TEXT NOT NULL DEFAULT ''",
]


class LibrarySqliteStore:
    def __init__(self, db_path: str | None = None):
        ensure_library_dirs()
        self.db_path = db_path or get_library_db_path()
        self._lock = threading.RLock()
        self._initialized = False
        self._fts_enabled = False
        self._wal_configured = False

    @property
    def fts_enabled(self) -> bool:
        self.ensure_initialized()
        return self._fts_enabled

    def ensure_initialized(self) -> None:
        with self._lock:
            if self._initialized:
                return
            os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
            with self.connect() as conn:
                if not self._wal_configured:
                    try:
                        conn.execute("PRAGMA journal_mode=WAL")
                    except sqlite3.DatabaseError:
                        pass
                    self._wal_configured = True
                for statement in SCHEMA_STATEMENTS:
                    conn.execute(statement)
                for statement in MIGRATION_STATEMENTS:
                    try:
                        conn.execute(statement)
                    except sqlite3.OperationalError:
                        pass
                try:
                    conn.execute(
                        """
                        CREATE VIRTUAL TABLE IF NOT EXISTS asset_search
                        USING fts5(
                            asset_id UNINDEXED,
                            file_name,
                            note,
                            tags,
                            collections,
                            ocr_text
                        )
                        """
                    )
                    self._fts_enabled = True
                except Exception:
                    self._fts_enabled = False
                conn.commit()
            self._initialized = True

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=30000")
            conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.DatabaseError:
            pass
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def write_connect(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            with self.connect() as conn:
                yield conn
