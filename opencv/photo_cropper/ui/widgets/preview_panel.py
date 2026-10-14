"""Image preview panel with zoom, pan, and contour overlay."""

from typing import Any, Dict, List, Optional

import numpy as np
from PySide6.QtCore import QObject, QPointF, QRectF, Qt, QEvent, Signal
from PySide6.QtGui import QBrush, QColor, QMouseEvent, QPalette, QPen, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ...i18n.catalog import t
from ..components import make_secondary, themed_splitter
from ..design_tokens import CONTROL_GAP, CONTROL_HEIGHT_SM, SPACE_XS, SPACE_XXS
from .preview_conversions import numpy_to_qpixmap
from .zoomable_view import ZoomableGraphicsView

class ImagePreviewWidget(QWidget):
    """
    Complete image preview widget with controls.
    
    Features:
        - Zoomable image display
        - Contour overlay toggle
        - Zoom controls
        - Side-by-side comparison mode
    """
    
    contour_edited = Signal(object)  # np.ndarray(4,2) in preview coordinates

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._original_image: Optional[np.ndarray] = None
        self._processed_image: Optional[np.ndarray] = None
        self._contour_overlay: Optional[np.ndarray] = None
        self._show_contour = True
        self._contour_points: Optional[np.ndarray] = None
        self._manual_seed_points: List[List[float]] = []
        self._contour_lines: List[Any] = []
        self._contour_handles: List[Any] = []
        self._drag_handle_index: Optional[int] = None
        self._hover_handle_index: Optional[int] = None
        self._handle_pick_radius = 20.0
        self._contour_pen = QPen(QColor(64, 220, 128, 220), 2)
        self._seed_line_pen = QPen(
            QColor(251, 191, 36, 230), 2, Qt.PenStyle.DashLine
        )
        self._handle_pen = QPen(QColor(255, 255, 255, 220), 1)
        self._handle_brush = QBrush(QColor(244, 63, 94, 220))
        self._seed_brush = QBrush(QColor(251, 191, 36, 210))
        self._handle_radius = 8.0
        self._pixmap_cache: Dict[str, Optional[QPixmap]] = {
            "original": None,
            "overlay": None,
            "processed": None,
        }
        self._source_cache: Dict[str, Optional[np.ndarray]] = {
            "original": None,
            "overlay": None,
            "processed": None,
        }
        
        self._placeholder_items: Dict[str, Any] = {}

        self._setup_ui()
        self.show_placeholder()
    
    def show_placeholder(self):
        """Show placeholder text in empty views."""
        self._drag_handle_index = None
        self._hover_handle_index = None
        self._contour_points = None
        self._manual_seed_points = []
        self._clear_contour_overlay()
        placeholder_color = self.palette().color(QPalette.ColorRole.PlaceholderText)
        for scene, text_key in (
            (self.original_scene, "preview.placeholder"),
            (self.processed_scene, "preview.placeholder.result"),
        ):
            scene.clear()
            # Reset any scene rect left over from a previous image so the
            # placeholder is centred in the view.
            scene.setSceneRect(QRectF())

            text_item = QGraphicsTextItem()
            text_item.setPlainText(t(text_key))
            text_item.setDefaultTextColor(placeholder_color)
            document = text_item.document()
            if document is not None:
                option = document.defaultTextOption()
                option.setAlignment(Qt.AlignmentFlag.AlignHCenter)
                document.setDefaultTextOption(option)
                text_item.setTextWidth(text_item.boundingRect().width())

            rect = text_item.boundingRect()
            text_item.setPos(-rect.width() / 2, -rect.height() / 2)
            scene.addItem(text_item)
            self._placeholder_items[text_key] = text_item

        # Reset items references
        self.original_pixmap_item = QGraphicsPixmapItem()
        self.processed_pixmap_item = QGraphicsPixmapItem()
        
        self.original_scene.addItem(self.original_pixmap_item)
        self.processed_scene.addItem(self.processed_pixmap_item)
        for view in (self.original_view, self.processed_view):
            # Undo any zoom from the previous image so the text is readable.
            view.reset_zoom()
            view.centerOn(0, 0)
        self._pixmap_cache["original"] = None
        self._pixmap_cache["overlay"] = None
        self._pixmap_cache["processed"] = None
        self._source_cache["original"] = None
        self._source_cache["overlay"] = None
        self._source_cache["processed"] = None

    def _drop_placeholder(self, text_key: str) -> None:
        """Remove the empty-state text once a real image is shown."""
        item = self._placeholder_items.pop(text_key, None)
        if item is not None and item.scene() is not None:
            item.scene().removeItem(item)

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE_XS)

        # Original | result, side by side with a draggable divider.
        self._splitter = themed_splitter(Qt.Orientation.Horizontal)

        # Original image view
        self.original_scene = QGraphicsScene()
        self.original_view = ZoomableGraphicsView()
        self.original_view.setScene(self.original_scene)
        viewport = self.original_view.viewport()
        if viewport is not None:
            viewport.installEventFilter(self)
        self.original_pixmap_item = QGraphicsPixmapItem()
        self.original_scene.addItem(self.original_pixmap_item)
        
        original_container = QFrame()
        original_container.setFrameStyle(QFrame.Shape.StyledPanel)
        original_layout = QVBoxLayout(original_container)
        original_layout.setContentsMargins(SPACE_XS, SPACE_XS, SPACE_XS, SPACE_XS)
        original_layout.setSpacing(SPACE_XXS)
        self._original_label = make_secondary(QLabel(t("preview.title.original")))
        original_layout.addWidget(self._original_label)
        original_layout.addWidget(self.original_view)
        # views_layout.addWidget(original_container)
        self._splitter.addWidget(original_container)
        
        # Processed image view
        self.processed_scene = QGraphicsScene()
        self.processed_view = ZoomableGraphicsView()
        self.processed_view.setScene(self.processed_scene)
        self.processed_pixmap_item = QGraphicsPixmapItem()
        self.processed_scene.addItem(self.processed_pixmap_item)
        
        processed_container = QFrame()
        processed_container.setFrameStyle(QFrame.Shape.StyledPanel)
        processed_layout = QVBoxLayout(processed_container)
        processed_layout.setContentsMargins(SPACE_XS, SPACE_XS, SPACE_XS, SPACE_XS)
        processed_layout.setSpacing(SPACE_XXS)
        self._processed_label = make_secondary(QLabel(t("preview.title.result")))
        processed_layout.addWidget(self._processed_label)
        processed_layout.addWidget(self.processed_view)
        # views_layout.addWidget(processed_container)
        self._splitter.addWidget(processed_container)
        
        # Set initial sizes (equal)
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setSizes([10000, 10000])
        
        layout.addWidget(self._splitter, 1)

        # View controls: area overlay on the left, zoom on the right.
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(CONTROL_GAP)

        self.contour_check = QCheckBox(t("preview.show_area"))
        self.contour_check.setToolTip(t("preview.show_area.tooltip"))
        self.contour_check.setChecked(True)
        self.contour_check.stateChanged.connect(self._on_contour_toggle)
        controls_layout.addWidget(self.contour_check)

        controls_layout.addStretch()

        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 500)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(120)
        self.zoom_slider.valueChanged.connect(self._on_zoom_slider_changed)
        controls_layout.addWidget(self.zoom_slider)

        self.zoom_label = make_secondary(QLabel("100%"))
        self.zoom_label.setMinimumWidth(44)
        controls_layout.addWidget(self.zoom_label)

        self._fit_btn = QPushButton(t("preview.fit"))
        self._fit_btn.setMinimumHeight(CONTROL_HEIGHT_SM)
        self._fit_btn.clicked.connect(self._fit_all)
        controls_layout.addWidget(self._fit_btn)

        self._reset_btn = QPushButton(t("preview.actual_size"))
        self._reset_btn.setMinimumHeight(CONTROL_HEIGHT_SM)
        self._reset_btn.clicked.connect(self._reset_zoom)
        controls_layout.addWidget(self._reset_btn)

        layout.addLayout(controls_layout)

        # Connect zoom signals
        self.original_view.zoom_changed.connect(self._on_zoom_changed)
        self.processed_view.zoom_changed.connect(self._on_zoom_changed)
        
    def set_original_image(
        self,
        image: Optional[np.ndarray],
        contour_overlay: Optional[np.ndarray] = None,
        contour_points: Optional[np.ndarray] = None,
    ):
        """
        Set original image with optional contour overlay.
        
        Args:
            image: Original image
            contour_overlay: Image with contour drawn on it
        """
        self._original_image = image
        self._contour_overlay = contour_overlay
        self._contour_points = (
            np.array(contour_points, dtype=np.float32).reshape((-1, 2))
            if contour_points is not None
            else None
        )
        self._manual_seed_points = []

        if image is not None:
            self._drop_placeholder("preview.placeholder")
        is_new_image = image is not self._source_cache["original"]
        if is_new_image:
            self._pixmap_cache["original"] = (
                numpy_to_qpixmap(image) if image is not None else None
            )
            self._source_cache["original"] = image

        if contour_overlay is not self._source_cache["overlay"]:
            self._pixmap_cache["overlay"] = (
                numpy_to_qpixmap(contour_overlay)
                if contour_overlay is not None
                else None
            )
            self._source_cache["overlay"] = contour_overlay

        self._update_original_display()
        if is_new_image and image is not None:
            # Show the whole scan first; the user can zoom in from there.
            self.original_view.fit_in_view()
    
    def set_processed_image(self, image: Optional[np.ndarray]):
        """
        Set processed image.
        
        Args:
            image: Processed/cropped image
        """
        self._processed_image = image
        is_new_image = image is not self._source_cache["processed"]
        if is_new_image:
            self._pixmap_cache["processed"] = (
                numpy_to_qpixmap(image) if image is not None else None
            )
            self._source_cache["processed"] = image

        if self._pixmap_cache["processed"] is not None:
            self._drop_placeholder("preview.placeholder.result")
            self.processed_pixmap_item.setPixmap(self._pixmap_cache["processed"])
            self.processed_scene.setSceneRect(
                self._pixmap_cache["processed"].rect().toRectF()
            )
            if is_new_image:
                self.processed_view.fit_in_view()
        else:
            self.processed_pixmap_item.setPixmap(QPixmap())
    
    def _update_original_display(self):
        """Update original image display based on contour toggle."""
        if self._show_contour and self._pixmap_cache["overlay"] is not None:
            pixmap = self._pixmap_cache["overlay"]
        else:
            pixmap = self._pixmap_cache["original"]

        if pixmap is not None:
            self.original_pixmap_item.setPixmap(pixmap)
            self.original_scene.setSceneRect(pixmap.rect().toRectF())
        else:
            self.original_pixmap_item.setPixmap(QPixmap())
        self._redraw_contour_overlay()
    
    def _on_contour_toggle(self, state):
        """Handle contour overlay toggle."""
        self._show_contour = bool(state)
        self._update_original_display()

    def _clear_contour_overlay(self):
        self._hover_handle_index = None
        for item in self._contour_lines + self._contour_handles:
            try:
                if item.scene() is not None:
                    self.original_scene.removeItem(item)
            except Exception:
                pass
        self._contour_lines.clear()
        self._contour_handles.clear()

    def _redraw_contour_overlay(self):
        self._clear_contour_overlay()
        if not self._show_contour or self._pixmap_cache["original"] is None:
            return

        if self._contour_points is None or len(self._contour_points) != 4:
            if not self._manual_seed_points:
                return
            seed_points = self._manual_seed_points
            for i in range(len(seed_points) - 1):
                p1 = seed_points[i]
                p2 = seed_points[i + 1]
                line = self.original_scene.addLine(
                    float(p1[0]),
                    float(p1[1]),
                    float(p2[0]),
                    float(p2[1]),
                    self._seed_line_pen,
                )
                if line is not None:
                    line.setZValue(45)
                    self._contour_lines.append(line)

            seed_radius = self._handle_radius * 0.7
            for p in seed_points:
                handle = self.original_scene.addEllipse(
                    float(p[0]) - seed_radius,
                    float(p[1]) - seed_radius,
                    seed_radius * 2.0,
                    seed_radius * 2.0,
                    self._handle_pen,
                    self._seed_brush,
                )
                if handle is not None:
                    handle.setZValue(55)
                    self._contour_handles.append(handle)
            return

        points = self._contour_points
        if points is None:
            return
        for i in range(4):
            p1 = points[i]
            p2 = points[(i + 1) % 4]
            line = self.original_scene.addLine(
                float(p1[0]),
                float(p1[1]),
                float(p2[0]),
                float(p2[1]),
                self._contour_pen,
            )
            if line is not None:
                line.setZValue(50)
                self._contour_lines.append(line)

        for i, p in enumerate(points):
            handle = self.original_scene.addEllipse(
                float(p[0]) - self._handle_radius,
                float(p[1]) - self._handle_radius,
                self._handle_radius * 2.0,
                self._handle_radius * 2.0,
                self._handle_pen,
                self._handle_brush,
            )
            if handle is not None:
                handle.setZValue(60)
                handle.setData(0, i)
                self._contour_handles.append(handle)

    def _pick_contour_handle(self, scene_pos: QPointF) -> Optional[int]:
        if self._contour_points is None or len(self._contour_points) != 4:
            return None
        px = float(scene_pos.x())
        py = float(scene_pos.y())
        best_idx = None
        best_dist = self._handle_pick_radius
        for i, p in enumerate(self._contour_points):
            dx = float(p[0]) - px
            dy = float(p[1]) - py
            dist = (dx * dx + dy * dy) ** 0.5
            if dist <= best_dist:
                best_dist = dist
                best_idx = i
        return best_idx

    def _clamp_to_image_bounds(self, scene_pos: QPointF) -> QPointF:
        pix = self.original_pixmap_item.pixmap()
        if pix.isNull():
            return scene_pos
        max_x = max(0.0, float(pix.width() - 1))
        max_y = max(0.0, float(pix.height() - 1))
        return QPointF(
            min(max(float(scene_pos.x()), 0.0), max_x),
            min(max(float(scene_pos.y()), 0.0), max_y),
        )

    def _has_visible_original_image(self) -> bool:
        """Return True when original pane currently has a drawable pixmap."""
        pix = self.original_pixmap_item.pixmap()
        return pix is not None and not pix.isNull()

    def _append_manual_seed_point(self, scene_pos: QPointF):
        """Append one seed point; auto-complete contour after 4 points."""
        clamped = self._clamp_to_image_bounds(scene_pos)
        self._manual_seed_points.append([float(clamped.x()), float(clamped.y())])
        if len(self._manual_seed_points) >= 4:
            self._contour_points = np.array(
                self._manual_seed_points[:4], dtype=np.float32
            )
            self._manual_seed_points = []
            self._redraw_contour_overlay()
            self.contour_edited.emit(np.array(self._contour_points, dtype=np.float32))
            return
        self._redraw_contour_overlay()

    def eventFilter(self, watched: QObject | None, event: QEvent) -> bool:
        viewport = self.original_view.viewport()
        if viewport is not None and watched is viewport:
            event_type = event.type()
            if event_type == QEvent.Type.MouseButtonPress:
                if (
                    isinstance(event, QMouseEvent)
                    and event.button() == Qt.MouseButton.LeftButton
                    and not (event.modifiers() & Qt.KeyboardModifier.ControlModifier)
                    and self._show_contour
                ):
                    scene_pos = self.original_view.mapToScene(event.position().toPoint())
                    if self._contour_points is not None and len(self._contour_points) == 4:
                        idx = self._pick_contour_handle(scene_pos)
                        if idx is not None:
                            self._drag_handle_index = idx
                            viewport.setCursor(Qt.CursorShape.ClosedHandCursor)
                            return True
                    elif self._has_visible_original_image():
                        self._append_manual_seed_point(scene_pos)
                        viewport.setCursor(Qt.CursorShape.CrossCursor)
                        return True
            elif event_type == QEvent.Type.MouseMove:
                if (
                    isinstance(event, QMouseEvent)
                    and self._drag_handle_index is not None
                    and self._contour_points is not None
                ):
                    scene_pos = self.original_view.mapToScene(event.position().toPoint())
                    clamped = self._clamp_to_image_bounds(scene_pos)
                    self._contour_points[self._drag_handle_index] = [
                        float(clamped.x()),
                        float(clamped.y()),
                    ]
                    self._redraw_contour_overlay()
                    return True
                if (
                    isinstance(event, QMouseEvent)
                    and self._show_contour
                    and self._contour_points is not None
                    and len(self._contour_points) == 4
                    and not (event.modifiers() & Qt.KeyboardModifier.ControlModifier)
                ):
                    scene_pos = self.original_view.mapToScene(event.position().toPoint())
                    idx = self._pick_contour_handle(scene_pos)
                    if idx is not None:
                        if self._hover_handle_index != idx:
                            self._hover_handle_index = idx
                            viewport.setCursor(Qt.CursorShape.PointingHandCursor)
                    elif self._hover_handle_index is not None:
                        self._hover_handle_index = None
                        viewport.setCursor(Qt.CursorShape.ArrowCursor)
                elif (
                    isinstance(event, QMouseEvent)
                    and self._show_contour
                    and (self._contour_points is None or len(self._contour_points) != 4)
                    and self._has_visible_original_image()
                    and not (event.modifiers() & Qt.KeyboardModifier.ControlModifier)
                ):
                    viewport.setCursor(Qt.CursorShape.CrossCursor)
            elif event_type == QEvent.Type.MouseButtonRelease:
                if (
                    isinstance(event, QMouseEvent)
                    and event.button() == Qt.MouseButton.LeftButton
                    and self._drag_handle_index is not None
                ):
                    self._drag_handle_index = None
                    viewport.setCursor(Qt.CursorShape.ArrowCursor)
                    if self._contour_points is not None and len(self._contour_points) == 4:
                        self.contour_edited.emit(
                            np.array(self._contour_points, dtype=np.float32)
                        )
                    return True
            elif event_type == QEvent.Type.MouseButtonDblClick:
                if (
                    isinstance(event, QMouseEvent)
                    and event.button() == Qt.MouseButton.LeftButton
                    and self._show_contour
                    and not (event.modifiers() & Qt.KeyboardModifier.ControlModifier)
                ):
                    self._drag_handle_index = None
                    self._contour_points = None
                    self._manual_seed_points = []
                    self._redraw_contour_overlay()
                    viewport.setCursor(Qt.CursorShape.CrossCursor)
                    return True
            elif event_type == QEvent.Type.Leave:
                self._hover_handle_index = None
                if self._drag_handle_index is None:
                    viewport.setCursor(Qt.CursorShape.ArrowCursor)
        return super().eventFilter(watched, event)
    
    def _on_zoom_changed(self, zoom: float):
        """Handle zoom level change from view."""
        percent = int(zoom * 100)
        self.zoom_label.setText(f"{percent}%")
        # Sync slider without triggering signal
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(min(500, max(10, percent)))
        self.zoom_slider.blockSignals(False)
    
    def _on_zoom_slider_changed(self, value: int):
        """Handle zoom slider change."""
        zoom = value / 100.0
        self.zoom_label.setText(f"{value}%")
        # Apply zoom to both views
        self.original_view.resetTransform()
        self.original_view.scale(zoom, zoom)
        self.original_view._zoom = zoom
        self.processed_view.resetTransform()
        self.processed_view.scale(zoom, zoom)
        self.processed_view._zoom = zoom
    
    def _fit_all(self):
        """Fit all views."""
        self.original_view.fit_in_view()
        self.processed_view.fit_in_view()
        # Update slider
        self.zoom_slider.setValue(100)
    
    def _reset_zoom(self):
        """Reset all zooms."""
        self.original_view.reset_zoom()
        self.processed_view.reset_zoom()
        # Update slider
        self.zoom_slider.setValue(100)
    
    def retranslate_ui(self):
        """Refresh texts after a language change."""
        self._original_label.setText(t("preview.title.original"))
        self._processed_label.setText(t("preview.title.result"))
        self.contour_check.setText(t("preview.show_area"))
        self.contour_check.setToolTip(t("preview.show_area.tooltip"))
        self._fit_btn.setText(t("preview.fit"))
        self._reset_btn.setText(t("preview.actual_size"))
        if self._original_image is None and self._processed_image is None:
            self.show_placeholder()

    def clear(self):
        """Clear all images and show placeholder."""
        self._original_image = None
        self._processed_image = None
        self._contour_overlay = None
        self._pixmap_cache["original"] = None
        self._pixmap_cache["overlay"] = None
        self._pixmap_cache["processed"] = None
        self._source_cache["original"] = None
        self._source_cache["overlay"] = None
        self._source_cache["processed"] = None
        
        self.show_placeholder()
    
    @property
    def show_contour(self) -> bool:
        """Get contour visibility state."""
        return self._show_contour
    
    @show_contour.setter
    def show_contour(self, value: bool):
        """Set contour visibility."""
        self._show_contour = value
        self.contour_check.setChecked(value)
        self._update_original_display()
