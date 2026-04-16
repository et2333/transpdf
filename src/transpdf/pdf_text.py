from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import fitz  # pymupdf

from .models import TranslationUnit


@dataclass(frozen=True, slots=True)
class PdfExtractResult:
    tus: list[TranslationUnit]
    page_count: int


def _tu_id(page_no: int, para_idx: int, text: str) -> str:
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]
    return f"A-p{page_no:04d}-t{para_idx:04d}-{h}"


def extract_text_units_pymupdf(pdf_path: str | Path) -> PdfExtractResult:
    p = Path(pdf_path)
    doc = fitz.open(str(p))
    tus: list[TranslationUnit] = []

    page_count = doc.page_count
    for page_idx in range(page_count):
        page = doc.load_page(page_idx)
        text = page.get_text("text") or ""
        # Split on blank lines; keep non-empty chunks
        parts = [t.strip() for t in text.split("\n\n") if t.strip()]
        for i, part in enumerate(parts):
            tus.append(
                TranslationUnit(
                    tu_id=_tu_id(page_idx + 1, i + 1, part),
                    page_no=page_idx + 1,
                    channel="A",
                    source_text=part,
                )
            )

    doc.close()
    return PdfExtractResult(tus=tus, page_count=page_count)

