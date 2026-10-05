#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Central-widget builder for the main window."""

from __future__ import annotations

from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QWidget,
)

from ....i18n.catalog import t
from ...design_tokens import NAV_LIST_QSS, NAV_RAIL_WIDTH
from ...fluent import nav_icon
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
from ..models import WindowRefs, WindowServices, WindowState
from .workbench import build_workbench_page

# Shell page order: the crop workbench is the app's main job, so it leads.
PAGE_ORDER = (
    "workbench",
    "library",
    "review",
    "duplicates",
    "jobs",
    "collections",
    "recipes",
    "settings",
)


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
    tool_actions,
) -> None:
    central = QWidget()
    window.setCentralWidget(central)

    shell_layout = QHBoxLayout(central)
    shell_layout.setContentsMargins(0, 0, 0, 0)
    shell_layout.setSpacing(0)

    refs.shell_nav = QListWidget()
    refs.shell_nav.setFixedWidth(NAV_RAIL_WIDTH)
    refs.shell_nav.setIconSize(QSize(16, 16))
    refs.shell_nav.setStyleSheet(NAV_LIST_QSS)
    shell_layout.addWidget(refs.shell_nav)

    refs.shell_stack = QStackedWidget()
    shell_layout.addWidget(refs.shell_stack, 1)

    workbench_page = build_workbench_page(
        refs,
        state,
        input_actions=input_actions,
        preview_actions=preview_actions,
        batch_actions=batch_actions,
        navigation_actions=navigation_actions,
        settings_actions=settings_actions,
        tool_actions=tool_actions,
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
            history_manager=services.history_manager,
        )
        review_page = ReviewPage(services.review_service)
        duplicates_page = DuplicatesPage(services.duplicate_service)
        jobs_page = JobsPage(services.query_service)
        collections_page = CollectionsPage(
            services.query_service,
            services.library_repository,
            history_manager=services.history_manager,
        )
        recipes_page = RecipesPage(
            services.recipe_manager,
            get_settings=lambda: state.settings,
            history_manager=services.history_manager,
        )
        settings_page = SettingsInfoPage(
            services.library_repository,
            services.recipe_manager,
        )
        _connect_open_signal(library_page, window)
        _connect_open_signal(review_page, window)
        _connect_open_signal(duplicates_page, window)
        _connect_open_signal(collections_page, window)
        library_page.import_requested.connect(window.run_library_import_job)
        duplicates_page.maintenance_requested.connect(window.run_maintenance_job)
        recipes_page.recipe_applied.connect(window.apply_recipe_from_management)
        review_page.reprocess_requested.connect(window.run_review_reprocess)
        jobs_page.rerun_requested.connect(
            lambda job_id, failed_only: window.run_job_rerun(job_id, failed_only=failed_only)
        )
        jobs_page.open_review_requested.connect(window.show_review_page_for_job)
        settings_page.maintenance_requested.connect(window.run_maintenance_job)
        settings_page.workbench_requested.connect(lambda: window.show_page("workbench"))
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

    pages = {
        "workbench": workbench_page,
        "library": library_page,
        "review": review_page,
        "duplicates": duplicates_page,
        "jobs": jobs_page,
        "collections": collections_page,
        "recipes": recipes_page,
        "settings": settings_page,
    }

    refs.management_pages.clear()
    for page_key in PAGE_ORDER:
        page = pages[page_key]
        item = QListWidgetItem(management_page_label(page_key))
        icon = nav_icon(page_key)
        if icon is not None:
            item.setIcon(icon)
        refs.shell_nav.addItem(item)
        refs.shell_stack.addWidget(page)
        refs.management_pages[page_key] = page

    refs.shell_nav.currentRowChanged.connect(refs.shell_stack.setCurrentIndex)
    refs.shell_nav.setCurrentRow(PAGE_ORDER.index("workbench"))
