"""Pytest fixtures for Photo Cropper."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _test_env_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("PYTHONUTF8", "1")
    monkeypatch.setenv("PHOTOCROPPER_OFFLINE", "1")


@pytest.fixture
def isolated_library_db(tmp_path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "library.db"
    monkeypatch.setenv("PHOTOCROPPER_LIBRARY_DB", str(db_path))
    from photo_cropper.core.library.repository import reset_library_repository_for_tests

    reset_library_repository_for_tests()
    yield db_path
    reset_library_repository_for_tests()
    monkeypatch.delenv("PHOTOCROPPER_LIBRARY_DB", raising=False)