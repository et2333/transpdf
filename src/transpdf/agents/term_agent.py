from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..termbase_lookup import TermbaseLookup


@dataclass(frozen=True, slots=True)
class TermConstraints:
    """
    Minimal constraint payload for translation prompting/reporting.
    """

    must_use: list[dict]


class TermAgent:
    """
    Agent-style wrapper around termbase capabilities.

    This keeps "node logic" under transpdf/agents/ while allowing the
    underlying storage/matching implementations to evolve independently.
    """

    def __init__(self, lookup: TermbaseLookup):
        self._lookup = lookup

    @classmethod
    def from_docx_two_column(cls, path: str | Path) -> TermAgent:
        return cls(TermbaseLookup.from_docx_two_column(path))

    def constraints_for_text(self, text: str, max_items: int = 30) -> TermConstraints:
        must_use = self._lookup.must_use_glossary(text, max_items=max_items)
        return TermConstraints(must_use=must_use)

