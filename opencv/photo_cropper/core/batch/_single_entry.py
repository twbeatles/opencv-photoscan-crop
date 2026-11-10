from __future__ import annotations

import os
import logging
from typing import Optional, Any

from ...utils.file_helpers import (
    classify_failed_files,
)
from .types import FileResult, ProcessStatus

logger = logging.getLogger(__name__)


class BatchProcessorSingleEntryMixin:
    def process_single(
        self: Any,
        input_path: str,
        output_dir: str,
        input_root: Optional[str] = None,
        *,
        clear_stop_event: bool = True,
    ) -> FileResult:
        """Process one file synchronously using the same pipeline as batch mode."""
        normalized_input_path = os.path.abspath(str(input_path or ""))
        if not normalized_input_path or not os.path.exists(normalized_input_path):
            return FileResult(
                filename=os.path.basename(normalized_input_path) if normalized_input_path else "",
                status=ProcessStatus.FAILED,
                source_path=normalized_input_path,
                message="입력 파일이 존재하지 않습니다",
            )

        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            return FileResult(
                filename=os.path.basename(normalized_input_path),
                status=ProcessStatus.FAILED,
                source_path=normalized_input_path,
                message=f"출력 폴더 생성 실패: {e}",
            )

        if clear_stop_event:
            self._stop_event.clear()
        self._reset_output_reservations()
        backup_dir = None
        if self.settings.create_backup:
            backup_dir = os.path.join(output_dir, "backup")
            try:
                os.makedirs(backup_dir, exist_ok=True)
            except Exception:
                backup_dir = None

        result = self._process_single_file(
            os.path.dirname(normalized_input_path),
            output_dir,
            normalized_input_path,
            backup_dir,
            1,
            1,
            None,
            input_root=input_root or os.path.dirname(normalized_input_path),
        )

        if (
            result.status == ProcessStatus.FAILED
            and self.settings.file_management.move_failed_files
        ):
            try:
                classify_failed_files(
                    [normalized_input_path],
                    input_root or os.path.dirname(normalized_input_path),
                    failed_folder_name=self.settings.file_management.failed_folder_name,
                    copy_mode=self.settings.file_management.copy_failed_instead_of_move,
                    input_root=input_root or os.path.dirname(normalized_input_path),
                )
            except Exception as e:
                self._log(f"실패 파일 분류 중 오류: {e}", "warning")

        if not result.source_path:
            result.source_path = normalized_input_path
        return result
