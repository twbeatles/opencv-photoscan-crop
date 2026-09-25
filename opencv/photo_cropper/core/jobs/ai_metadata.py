from __future__ import annotations

from typing import Any, Optional

from ..face import FaceDetector
from ..image_classifier import ImageClassifier
from ..library import get_ocr_provider, get_person_provider
from ..settings_model import AppSettings


class JobAIMetadataMixin:
    """Classification / face / OCR enrichment recorded per processed variant."""

    repository: Any
    _classifier: Optional[ImageClassifier]
    _face_detector: Optional[FaceDetector]
    _ai_errors: list[str]

    def _record_ai_metadata(
        self,
        *,
        asset_id: int,
        source_id: Optional[int],
        variant_id: Optional[int],
        image_path: str,
        settings: AppSettings,
    ) -> None:
        if settings.classification.enabled:
            try:
                if self._classifier is None:
                    self._classifier = ImageClassifier()
                image = self._load_image_for_ai(image_path)
                if image is not None:
                    result = self._classifier.classify(image, model=settings.classification.model)
                    self.repository.clear_asset_tags(asset_id, source="classification")
                    self.repository.add_asset_tag(
                        asset_id,
                        result.category.value,
                        source="classification",
                        confidence=result.confidence,
                        kind="classification",
                    )
                    if result.is_grayscale:
                        self.repository.add_asset_tag(
                            asset_id,
                            "grayscale",
                            source="classification",
                            confidence=1.0,
                            kind="classification",
                        )
            except Exception:
                self._ai_errors.append("classification_failed")

        if settings.face_detection.enabled:
            try:
                if self._face_detector is None:
                    self._face_detector = FaceDetector(
                        use_dnn=settings.face_detection.use_dnn,
                        min_face_size=settings.face_detection.min_face_size,
                    )
                image = self._load_image_for_ai(image_path)
                if image is not None:
                    detection = self._face_detector.detect(
                        image,
                        detect_eyes=settings.face_detection.detect_eyes,
                        suggest_crop=False,
                    )
                    self.repository.clear_faces(asset_id, variant_id=variant_id)
                    self.repository.clear_person_links(asset_id, variant_id=variant_id)
                    face_entries: list[dict] = []
                    for face in detection.faces:
                        face_id = self.repository.add_face(
                            asset_id=asset_id,
                            source_id=source_id,
                            variant_id=variant_id,
                            x=int(face.x),
                            y=int(face.y),
                            w=int(face.width),
                            h=int(face.height),
                            confidence=float(getattr(face, "confidence", 0.0) or 0.0),
                            metadata={"kind": "face"},
                        )
                        face_entries.append(
                            {
                                "face_id": face_id,
                                "asset_id": asset_id,
                                "source_id": source_id,
                                "variant_id": variant_id,
                                "image_path": image_path,
                                "x": int(face.x),
                                "y": int(face.y),
                                "w": int(face.width),
                                "h": int(face.height),
                                "confidence": float(getattr(face, "confidence", 0.0) or 0.0),
                            }
                        )
                    person_provider = get_person_provider()
                    if person_provider is not None and face_entries:
                        try:
                            assignments = person_provider.assign_people(face_entries)
                            provider_name = getattr(person_provider, "name", "plugin")
                            for assignment in list(assignments or []):
                                face_id = int(assignment.get("face_id", 0) or 0)
                                if face_id <= 0:
                                    continue
                                person_id = self.repository.upsert_person(
                                    provider=provider_name,
                                    external_id=str(
                                        assignment.get("external_id")
                                        or assignment.get("person_key")
                                        or face_id
                                    ),
                                    name=str(assignment.get("name", "") or ""),
                                )
                                self.repository.link_person_face(
                                    face_id=face_id,
                                    person_id=person_id,
                                    confidence=float(assignment.get("confidence", 1.0) or 1.0),
                                )
                        except Exception:
                            self._ai_errors.append("person_provider_failed")
            except Exception:
                self._ai_errors.append("face_detection_failed")

        ocr_provider = get_ocr_provider()
        if ocr_provider is not None:
            try:
                text, metadata = ocr_provider.extract_text(image_path)
                if str(text or "").strip():
                    self.repository.add_ocr_document(
                        asset_id=asset_id,
                        source_id=source_id,
                        variant_id=variant_id,
                        provider=getattr(ocr_provider, "name", "plugin"),
                        text=text,
                        metadata=metadata,
                    )
            except Exception:
                self._ai_errors.append("ocr_provider_failed")

    def _load_image_for_ai(self, image_path: str):
        try:
            import cv2
            from ...utils.image_io import load_image_unicode

            return load_image_unicode(image_path, cv2.IMREAD_COLOR)
        except Exception:
            return None


__all__ = ["JobAIMetadataMixin"]
