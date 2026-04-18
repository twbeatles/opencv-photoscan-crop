#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Central-widget builder for the main window."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ....i18n.catalog import t
from ...widgets.histogram_widget import HistogramWidget
from ...widgets.management_pages import (
    CollectionsPage,
    DuplicatesPage,
    JobsPage,
    LibraryPage,
    RecipesPage,
    ReviewPage,
    SettingsInfoPage,
    UnavailablePage,
    management_page_label,
)
from ...widgets.preview_widget import ImagePreviewWidget
from ...widgets.settings import SettingsPanel
from ..models import WindowRefs, WindowServices, WindowState


def _build_workbench_page(
    refs: WindowRefs,
    state: WindowState,
    *,
    input_actions,
    preview_actions,
    batch_actions,
    navigation_actions,
    settings_actions,
) -> QWidget:
    page = QWidget()
    main_layout = QVBoxLayout(page)
    main_layout.setContentsMargins(8, 8, 8, 8)
    main_layout.setSpacing(0)

    outer_splitter = QSplitter(Qt.Orientation.Vertical)
    outer_splitter.setHandleWidth(6)
    outer_splitter.setStyleSheet(
        """
        QSplitter::handle:vertical {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 transparent, stop:0.4 rgba(88, 166, 255, 0.5),
                stop:0.6 rgba(88, 166, 255, 0.5), stop:1 transparent);
            height: 6px;
            margin: 2px 0;
        }
        QSplitter::handle:vertical:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 transparent, stop:0.3 rgba(88, 166, 255, 0.8),
                stop:0.7 rgba(88, 166, 255, 0.8), stop:1 transparent);
        }
    """
    )

    folder_card = QFrame()
    folder_card.setObjectName("statsFrame")
    folder_card_layout = QVBoxLayout(folder_card)
    folder_card_layout.setContentsMargins(10, 8, 10, 8)
    folder_card_layout.setSpacing(6)

    path_grid = QGridLayout()
    path_grid.setSpacing(6)
    path_grid.setContentsMargins(0, 0, 0, 0)
    path_grid.setColumnStretch(1, 1)

    input_label = QLabel(t("central.input_folder"))
    input_label.setStyleSheet("font-weight: bold;")
    path_grid.addWidget(input_label, 0, 0)
    refs.labels["central.input_label"] = input_label

    refs.input_path_edit = QLineEdit()
    refs.input_path_edit.setPlaceholderText(t("central.input_placeholder"))
    refs.input_path_edit.setMinimumHeight(32)
    refs.input_path_edit.setTextMargins(8, 0, 8, 0)
    refs.input_path_edit.textChanged.connect(input_actions.on_input_path_changed)
    path_grid.addWidget(refs.input_path_edit, 0, 1)

    input_browse_btn = QPushButton(t("central.browse"))
    input_browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    input_browse_btn.setMinimumHeight(32)
    input_browse_btn.clicked.connect(input_actions.select_input_folder)
    path_grid.addWidget(input_browse_btn, 0, 2)
    refs.buttons["central.input_browse"] = input_browse_btn

    output_label = QLabel(t("central.output_folder"))
    output_label.setStyleSheet("font-weight: bold;")
    path_grid.addWidget(output_label, 1, 0)
    refs.labels["central.output_label"] = output_label

    refs.output_path_edit = QLineEdit()
    refs.output_path_edit.setPlaceholderText(t("central.output_placeholder"))
    refs.output_path_edit.setMinimumHeight(32)
    refs.output_path_edit.setTextMargins(8, 0, 8, 0)
    refs.output_path_edit.textChanged.connect(input_actions.on_output_path_changed)
    path_grid.addWidget(refs.output_path_edit, 1, 1)

    output_browse_btn = QPushButton(t("central.change"))
    output_browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    output_browse_btn.setMinimumHeight(32)
    output_browse_btn.clicked.connect(input_actions.select_output_folder)
    path_grid.addWidget(output_browse_btn, 1, 2)
    refs.buttons["central.output_browse"] = output_browse_btn

    output_open_btn = QPushButton(t("central.open_output_folder"))
    output_open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    output_open_btn.setMinimumHeight(32)
    output_open_btn.clicked.connect(input_actions.open_output_folder)
    path_grid.addWidget(output_open_btn, 1, 3)
    refs.buttons["central.output_open"] = output_open_btn
    folder_card_layout.addLayout(path_grid)

    hint_layout = QHBoxLayout()
    hint_layout.setContentsMargins(0, 0, 0, 0)
    hint_icon = QLabel("?뮕")
    hint_text = QLabel(t("central.drag_hint"))
    hint_text.setObjectName("subtitleLabel")
    hint_layout.addWidget(hint_icon)
    hint_layout.addWidget(hint_text)
    hint_layout.addStretch()
    folder_card_layout.addLayout(hint_layout)

    edit_nav_layout = QHBoxLayout()
    edit_nav_layout.setContentsMargins(0, 2, 0, 0)

    refs.batch_load_btn = QPushButton(t("central.load_batch"))
    refs.batch_load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    refs.batch_load_btn.setMinimumHeight(30)
    refs.batch_load_btn.clicked.connect(batch_actions.load_batch_images_for_edit)
    edit_nav_layout.addWidget(refs.batch_load_btn)

    refs.batch_failed_btn = QPushButton(t("central.load_failed"))
    refs.batch_failed_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    refs.batch_failed_btn.setMinimumHeight(30)
    refs.batch_failed_btn.clicked.connect(batch_actions.load_failed_boundary_images_for_edit)
    edit_nav_layout.addWidget(refs.batch_failed_btn)

    refs.batch_prev_btn = QPushButton(t("central.prev"))
    refs.batch_prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    refs.batch_prev_btn.setMinimumHeight(30)
    refs.batch_prev_btn.clicked.connect(navigation_actions.navigate_prev)
    edit_nav_layout.addWidget(refs.batch_prev_btn)

    refs.batch_next_btn = QPushButton(t("central.next"))
    refs.batch_next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    refs.batch_next_btn.setMinimumHeight(30)
    refs.batch_next_btn.clicked.connect(navigation_actions.navigate_next)
    edit_nav_layout.addWidget(refs.batch_next_btn)

    refs.batch_save_edits_btn = QPushButton(t("central.save_edits"))
    refs.batch_save_edits_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    refs.batch_save_edits_btn.setMinimumHeight(30)
    refs.batch_save_edits_btn.clicked.connect(batch_actions.save_batch_edited_crops)
    edit_nav_layout.addWidget(refs.batch_save_edits_btn)

    refs.batch_edit_status_label = QLabel(
        t("central.batch_status", current=0, total=0, edited=0, failed=0)
    )
    refs.batch_edit_status_label.setObjectName("subtitleLabel")
    edit_nav_layout.addWidget(refs.batch_edit_status_label)
    edit_nav_layout.addStretch()
    folder_card_layout.addLayout(edit_nav_layout)
    refs.buttons["central.batch_load"] = refs.batch_load_btn
    refs.buttons["central.batch_failed"] = refs.batch_failed_btn
    refs.buttons["central.batch_prev"] = refs.batch_prev_btn
    refs.buttons["central.batch_next"] = refs.batch_next_btn
    refs.buttons["central.batch_save"] = refs.batch_save_edits_btn
    refs.labels["central.drag_hint"] = hint_text

    outer_splitter.addWidget(folder_card)

    main_splitter = QSplitter(Qt.Orientation.Horizontal)
    main_splitter.setHandleWidth(6)
    main_splitter.setStyleSheet(
        """
        QSplitter::handle:horizontal {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 transparent, stop:0.4 rgba(88, 166, 255, 0.5),
                stop:0.6 rgba(88, 166, 255, 0.5), stop:1 transparent);
            width: 6px;
            margin: 0 2px;
        }
        QSplitter::handle:horizontal:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 transparent, stop:0.3 rgba(88, 166, 255, 0.8),
                stop:0.7 rgba(88, 166, 255, 0.8), stop:1 transparent);
        }
    """
    )

    left_splitter = QSplitter(Qt.Orientation.Vertical)
    left_splitter.setHandleWidth(6)
    left_splitter.setStyleSheet(outer_splitter.styleSheet())

    refs.preview_widget = ImagePreviewWidget()
    refs.preview_widget.contour_edited.connect(preview_actions.on_preview_contour_edited)
    left_splitter.addWidget(refs.preview_widget)

    refs.histogram_widget = HistogramWidget()
    left_splitter.addWidget(refs.histogram_widget)
    left_splitter.setStretchFactor(0, 5)
    left_splitter.setStretchFactor(1, 1)
    left_splitter.setSizes([500, 100])
    main_splitter.addWidget(left_splitter)

    refs.settings_panel = SettingsPanel(state.settings)
    refs.settings_panel.settings_changed.connect(settings_actions.on_settings_changed)
    refs.settings_panel.preview_requested.connect(preview_actions.request_preview)
    refs.settings_panel.setMaximumWidth(400)
    main_splitter.addWidget(refs.settings_panel)
    main_splitter.setSizes([850, 320])
    outer_splitter.addWidget(main_splitter)

    outer_splitter.setStretchFactor(0, 0)
    outer_splitter.setStretchFactor(1, 1)
    outer_splitter.setSizes([110, 700])
    main_layout.addWidget(outer_splitter)
    return page


def _connect_open_signal(page: QWidget, window) -> None:
    signal = getattr(page, "open_requested", None)
    if signal is not None:
        signal.connect(window.open_path_in_workbench)


def build_central_widget(
    window,
    refs: WindowRefs,
    state: WindowState,
    services: WindowServices,
    *,
    input_actions,
    preview_actions,
    batch_actions,
    navigation_actions,
    settings_actions,
) -> None:
    central = QWidget()
    window.setCentralWidget(central)

    shell_layout = QHBoxLayout(central)
    shell_layout.setContentsMargins(0, 0, 0, 0)
    shell_layout.setSpacing(0)

    refs.shell_nav = QListWidget()
    refs.shell_nav.setFixedWidth(180)
    refs.shell_nav.setSpacing(4)
    refs.shell_nav.setStyleSheet(
        """
        QListWidget {
            border: none;
            border-right: 1px solid rgba(128, 128, 128, 0.25);
            padding: 10px 8px;
        }
        QListWidget::item {
            padding: 10px 12px;
            border-radius: 8px;
            margin: 2px 0;
        }
        QListWidget::item:selected {
            background: rgba(88, 166, 255, 0.18);
            color: #58a6ff;
            font-weight: bold;
        }
        """
    )
    shell_layout.addWidget(refs.shell_nav)

    refs.shell_stack = QStackedWidget()
    shell_layout.addWidget(refs.shell_stack, 1)

    workbench_page = _build_workbench_page(
        refs,
        state,
        input_actions=input_actions,
        preview_actions=preview_actions,
        batch_actions=batch_actions,
        navigation_actions=navigation_actions,
        settings_actions=settings_actions,
    )

    if (
        services.library_repository is not None
        and services.query_service is not None
        and services.library_ingest_service is not None
        and services.thumbnail_service is not None
        and services.review_service is not None
        and services.duplicate_service is not None
        and services.recipe_manager is not None
    ):
        library_page = LibraryPage(
            services.query_service,
            services.library_ingest_service,
            services.thumbnail_service,
            services.library_repository,
        )
        review_page = ReviewPage(services.review_service)
        duplicates_page = DuplicatesPage(services.duplicate_service)
        jobs_page = JobsPage(services.query_service)
        collections_page = CollectionsPage(
            services.query_service,
            services.library_repository,
        )
        recipes_page = RecipesPage(
            services.recipe_manager,
            get_settings=lambda: state.settings,
        )
        settings_page = SettingsInfoPage(
            services.library_repository,
            services.recipe_manager,
        )
        _connect_open_signal(library_page, window)
        _connect_open_signal(review_page, window)
        _connect_open_signal(duplicates_page, window)
        _connect_open_signal(collections_page, window)
        recipes_page.recipe_applied.connect(window.apply_recipe_from_management)
        review_page.reprocess_requested.connect(window.run_review_reprocess)
        jobs_page.rerun_requested.connect(
            lambda job_id, failed_only: window.run_job_rerun(job_id, failed_only=failed_only)
        )
        jobs_page.open_review_requested.connect(window.show_review_page_for_job)
        settings_page.maintenance_requested.connect(window.run_maintenance_job)
        settings_page.workbench_requested.connect(
            lambda: refs.shell_nav.setCurrentRow(1) if refs.shell_nav is not None else None
        )
    else:
        unavailable_title = t("management.unavailable.library_title")
        unavailable_body = t("management.unavailable.library_body")
        library_page = UnavailablePage(unavailable_title, unavailable_body)
        review_page = UnavailablePage(unavailable_title, unavailable_body)
        duplicates_page = UnavailablePage(unavailable_title, unavailable_body)
        jobs_page = UnavailablePage(unavailable_title, unavailable_body)
        collections_page = UnavailablePage(unavailable_title, unavailable_body)
        recipes_page = UnavailablePage(
            t("management.unavailable.recipes_title"),
            t("management.unavailable.recipes_body"),
        )
        settings_page = UnavailablePage(
            t("management.unavailable.settings_title"),
            t("management.unavailable.settings_body"),
        )

    pages = [
        ("library", library_page),
        ("workbench", workbench_page),
        ("review", review_page),
        ("duplicates", duplicates_page),
        ("jobs", jobs_page),
        ("collections", collections_page),
        ("recipes", recipes_page),
        ("settings", settings_page),
    ]

    refs.management_pages.clear()
    for page_key, page in pages:
        refs.shell_nav.addItem(management_page_label(page_key))
        refs.shell_stack.addWidget(page)
        refs.management_pages[page_key] = page

    refs.shell_nav.currentRowChanged.connect(refs.shell_stack.setCurrentIndex)
    refs.shell_nav.setCurrentRow(1)
