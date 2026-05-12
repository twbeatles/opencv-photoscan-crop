from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ....core.app_paths import ensure_library_dirs
from ....core.library import get_provider_status
from ....core.recipes import RecipeManager
from ....i18n.catalog import t
from .shared import _translated_job_kind

class SettingsInfoPage(QWidget):
    maintenance_requested = pyqtSignal(str)
    workbench_requested = pyqtSignal()

    def __init__(self, repository, recipe_manager: RecipeManager, parent=None):
        super().__init__(parent)
        self.repository = repository
        self.recipe_manager = recipe_manager
        self.maintenance_buttons: list[tuple[str, QPushButton]] = []

        layout = QVBoxLayout(self)
        self.header = QLabel()
        self.header.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(self.header)
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        self.info_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.info_label)
        actions = QGridLayout()
        buttons = [
            ("maintenance_missing_sources", "maintenance_missing_sources"),
            ("maintenance_thumbnails", "maintenance_thumbnails"),
            ("maintenance_exact_duplicates", "maintenance_exact_duplicates"),
            ("maintenance_near_duplicates", "maintenance_near_duplicates"),
            ("maintenance_search_index", "maintenance_search_index"),
            ("maintenance_ocr_refresh", "maintenance_ocr_refresh"),
            ("maintenance_people_refresh", "maintenance_people_refresh"),
        ]
        for index, (label_key, job_kind) in enumerate(buttons):
            button = QPushButton()
            button.clicked.connect(
                lambda _checked=False, kind=job_kind: self.maintenance_requested.emit(kind)
            )
            actions.addWidget(button, index // 2, index % 2)
            self.maintenance_buttons.append((label_key, button))
        self.workbench_btn = QPushButton()
        self.workbench_btn.clicked.connect(self.workbench_requested.emit)
        actions.addWidget(self.workbench_btn, (len(buttons) + 1) // 2, 0, 1, 2)
        layout.addLayout(actions)
        layout.addStretch()
        self.retranslate_ui()

    def refresh(self) -> None:
        paths = ensure_library_dirs()
        providers = get_provider_status()
        db_path = self.repository.db_path if self.repository is not None else t("management.common.disabled")
        lines = [
            t("management.settings.info.workbench_hint"),
            "",
            t("management.settings.info.library_db", value=db_path),
            t("management.settings.info.library_root", value=paths["root"]),
            t("management.settings.info.thumbnails", value=paths["thumbnails"]),
            t("management.settings.info.preview_cache", value=paths["preview_cache"]),
            t("management.settings.info.logs", value=paths["logs"]),
            "",
            t(
                "management.settings.info.ocr_provider",
                value=providers.ocr_name if providers.ocr_available else t("management.common.disabled"),
            ),
            t(
                "management.settings.info.person_provider",
                value=providers.person_name if providers.person_available else t("management.common.disabled"),
            ),
            t(
                "management.settings.info.current_recipe",
                value=self.recipe_manager.get_current_recipe_name() or t("management.common.none"),
            ),
        ]
        self.info_label.setText("\n".join(lines))

    def retranslate_ui(self) -> None:
        self.header.setText(t("management.settings.title"))
        for label_key, button in self.maintenance_buttons:
            button.setText(_translated_job_kind(label_key))
        self.workbench_btn.setText(t("management.settings.open_workbench"))
        self.refresh()
