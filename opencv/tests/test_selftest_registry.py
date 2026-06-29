"""Expose legacy selftests to pytest for selective execution (-k)."""

from __future__ import annotations

import pytest

from photo_cropper.selftests.runner import TESTS


@pytest.mark.selftest
@pytest.mark.parametrize("test_fn", TESTS, ids=lambda fn: fn.__name__)
def test_selftest_registry_case(test_fn) -> None:
    test_fn()