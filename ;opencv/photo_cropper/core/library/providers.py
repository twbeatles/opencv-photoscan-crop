from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Optional, Protocol, cast


class OcrProvider(Protocol):
    name: str

    def extract_text(self, image_path: str) -> tuple[str, dict]: ...


class PersonProvider(Protocol):
    name: str

    def assign_people(self, face_entries: list[dict]) -> list[dict]: ...


@dataclass(frozen=True)
class ProviderStatus:
    ocr_available: bool
    ocr_name: str = ""
    person_available: bool = False
    person_name: str = ""


def _load_provider(module_name: str, attr_name: str):
    try:
        module = importlib.import_module(module_name)
        factory = getattr(module, attr_name, None)
        if callable(factory):
            return factory()
    except Exception:
        return None
    return None


def get_ocr_provider() -> Optional[OcrProvider]:
    return cast(Optional[OcrProvider], _load_provider("photo_cropper_plugins.ocr_provider", "get_provider"))


def get_person_provider() -> Optional[PersonProvider]:
    return cast(Optional[PersonProvider], _load_provider("photo_cropper_plugins.person_provider", "get_provider"))


def get_provider_status() -> ProviderStatus:
    ocr = get_ocr_provider()
    person = get_person_provider()
    return ProviderStatus(
        ocr_available=ocr is not None,
        ocr_name=getattr(ocr, "name", "") if ocr is not None else "",
        person_available=person is not None,
        person_name=getattr(person, "name", "") if person is not None else "",
    )
