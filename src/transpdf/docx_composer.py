from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from docx import Document

from .models import TranslationUnit


@dataclass(frozen=True, slots=True)
class DocxComposeResult:
    output_path: Path
    paragraph_count: int


def compose_docx_from_units(units: list[TranslationUnit], output_path: str | Path) -> DocxComposeResult:
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    doc = Document()
    count = 0
    for tu in units:
        if not tu.target_text:
            continue
        doc.add_paragraph(tu.target_text)
        count += 1
    doc.save(str(p))
    return DocxComposeResult(output_path=p, paragraph_count=count)

