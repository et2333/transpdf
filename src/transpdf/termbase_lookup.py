from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from docx import Document

from .models import TermEntry


def _stable_term_id(source_term: str, target_term: str) -> str:
    h = hashlib.sha256()
    h.update(source_term.strip().encode("utf-8"))
    h.update(b"\x00")
    h.update(target_term.strip().encode("utf-8"))
    return h.hexdigest()[:16]


@dataclass(frozen=True, slots=True)
class TermHit:
    entry: TermEntry
    matched_form: str
    start: int
    end: int


class TermbaseLookup:
    """
    Two-column (ZH -> EN) termbase lookup.

    Design intent:
    - Deterministic, auditable must-use constraints.
    - Used as the "strong constraint" baseline before optional RAG.
    """

    def __init__(self, entries: list[TermEntry]):
        cleaned: list[TermEntry] = []
        for e in entries:
            if not e.source_term or not e.target_term:
                continue
            cleaned.append(e)

        # Prefer longer source terms first to avoid partial overlaps.
        self._entries = sorted(cleaned, key=lambda x: len(x.source_term), reverse=True)

        # Build a flat list of (source_form, entry) for matching.
        pairs: list[tuple[str, TermEntry]] = []
        for e in self._entries:
            for form in e.all_source_forms():
                if not form:
                    continue
                pairs.append((form, e))
        pairs.sort(key=lambda p: len(p[0]), reverse=True)
        self._forms = pairs

    @classmethod
    def from_docx_two_column(cls, path: str | Path) -> TermbaseLookup:
        """
        Parse a Word docx containing one or more tables with at least two columns:
        Column 0: Chinese term, Column 1: English term.

        Notes:
        - Ignores header rows where the first cells look like '中文' / 'English'.
        - Additional columns are ignored in this minimal implementation.
        """
        p = Path(path)
        doc = Document(str(p))

        entries: list[TermEntry] = []
        for table in doc.tables:
            for row in table.rows:
                cells = row.cells
                if len(cells) < 2:
                    continue
                zh = (cells[0].text or "").strip()
                en = (cells[1].text or "").strip()
                if not zh or not en:
                    continue
                if zh in {"中文", "Chinese"} and en in {"英文", "English"}:
                    continue
                term_id = _stable_term_id(zh, en)
                entries.append(TermEntry(term_id=term_id, source_term=zh, target_term=en))

        # De-dup by (zh,en) keeping first occurrence.
        seen: set[tuple[str, str]] = set()
        uniq: list[TermEntry] = []
        for e in entries:
            key = (e.source_term, e.target_term)
            if key in seen:
                continue
            seen.add(key)
            uniq.append(e)

        return cls(uniq)

    def find_hits(self, text: str) -> list[TermHit]:
        if not text:
            return []

        hits: list[TermHit] = []
        occupied: list[tuple[int, int]] = []

        def overlaps(a0: int, a1: int) -> bool:
            for b0, b1 in occupied:
                if a0 < b1 and b0 < a1:
                    return True
            return False

        for form, entry in self._forms:
            start = 0
            while True:
                idx = text.find(form, start)
                if idx == -1:
                    break
                j = idx + len(form)
                if not overlaps(idx, j):
                    hits.append(TermHit(entry=entry, matched_form=form, start=idx, end=j))
                    occupied.append((idx, j))
                start = j

        hits.sort(key=lambda h: (h.start, -(h.end - h.start)))
        return hits

    def must_use_glossary(self, text: str, max_items: int = 30) -> list[dict]:
        """
        Return a compact glossary payload for LLM prompting and reporting.
        """
        hits = self.find_hits(text)
        if not hits:
            return []

        # De-dup by term_id preserving earliest occurrence
        seen: set[str] = set()
        out: list[dict] = []
        for h in hits:
            if h.entry.term_id in seen:
                continue
            seen.add(h.entry.term_id)
            out.append(
                {
                    "term_id": h.entry.term_id,
                    "zh": h.entry.source_term,
                    "en": h.entry.target_term,
                }
            )
            if len(out) >= max_items:
                break
        return out

