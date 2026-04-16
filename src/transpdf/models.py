from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass(frozen=True, slots=True)
class TermEntry:
    term_id: str
    source_term: str
    target_term: str
    domain: str | None = None
    notes: str | None = None
    synonyms: list[str] | None = None
    updated_at: datetime | None = None

    def all_source_forms(self) -> list[str]:
        forms: list[str] = [self.source_term]
        if self.synonyms:
            forms.extend([s for s in self.synonyms if s and s != self.source_term])
        # de-dup while preserving order
        seen: set[str] = set()
        out: list[str] = []
        for f in forms:
            if f in seen:
                continue
            seen.add(f)
            out.append(f)
        return out


@dataclass(frozen=True, slots=True)
class TranslationUnit:
    tu_id: str
    page_no: int
    channel: Literal["A", "B"]
    source_text: str
    target_text: str | None = None
    term_hits: list[str] | None = None
    confidence: float | None = None
    bbox_norm: tuple[float, float, float, float] | None = None
    style_hints: dict | None = None


@dataclass(frozen=True, slots=True)
class OverlayInstruction:
    tu_id: str
    level: Literal["L1", "L2", "L3", "L4"]
    payload: dict
    requires_manual_review: bool = False

