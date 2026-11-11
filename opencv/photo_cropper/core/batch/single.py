from __future__ import annotations

import logging

from ._single_batch import BatchProcessorBatchLoopMixin
from ._single_entry import BatchProcessorSingleEntryMixin
from ._single_file import BatchProcessorSingleFileMixin
from ._single_multi import BatchProcessorMultiPhotoMixin

logger = logging.getLogger(__name__)


class BatchProcessorExecutionMixin(
    BatchProcessorSingleEntryMixin,
    BatchProcessorBatchLoopMixin,
    BatchProcessorSingleFileMixin,
    BatchProcessorMultiPhotoMixin,
):
    pass
