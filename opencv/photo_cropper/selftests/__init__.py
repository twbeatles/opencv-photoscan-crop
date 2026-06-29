# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
"""Self-test package for Photo Cropper.

The public entrypoint remains ``python -m photo_cropper.selftest``.
"""

from .runner import TESTS, main

__all__ = ["TESTS", "main"]
