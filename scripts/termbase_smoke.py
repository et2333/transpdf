from __future__ import annotations

from pathlib import Path

from transpdf.termbase_lookup import TermbaseLookup


def main() -> None:
    termbase_path = Path("data/incoming/机器人中英文对照专业词库_完整版.md.docx")
    if not termbase_path.exists():
        raise SystemExit(
            f"termbase file not found: {termbase_path}\n"
            "Put your two-column termbase docx there (or adjust this script)."
        )

    tb = TermbaseLookup.from_docx_two_column(termbase_path)

    sample = "翼菲智能的控制柜参数为 12mm，Robotphoenix 不应出现在中文原文中。"
    hits = tb.find_hits(sample)
    print(f"entries_loaded={len(tb._entries)} hits={len(hits)}")
    for h in hits[:20]:
        print(f"- {h.entry.source_term} => {h.entry.target_term} ({h.start}:{h.end})")

    glossary = tb.must_use_glossary(sample)
    print("glossary:", glossary)


if __name__ == "__main__":
    main()

