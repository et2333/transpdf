from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from .agents import TermAgent
from .config import AppConfig
from .docx_composer import DocxComposeResult, compose_docx_from_units
from .llm_client import LlmClient
from .models import TranslationUnit
from .pdf_text import extract_text_units_pymupdf


def _utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _termbase_rev(path: Path) -> str:
    try:
        st = path.stat()
        return f"{path.name}:{int(st.st_mtime)}:{st.st_size}"
    except FileNotFoundError:
        return f"{path.name}:missing"


class PipelineState(TypedDict, total=False):
    job_id: str
    pdf_path: str
    termbase_path: str
    locale_source: str
    locale_target: str
    termbase_rev: str
    tus: list[TranslationUnit]
    output_dir: str
    output_docx: str
    stats: dict[str, Any]


@dataclass(frozen=True, slots=True)
class RunResult:
    job_id: str
    termbase_rev: str
    tu_count: int
    docx: DocxComposeResult


def build_graph(cfg: AppConfig) -> Any:
    llm = LlmClient(cfg.llm)
    term_agent = TermAgent.from_docx_two_column(cfg.termbase.path)

    def node_init(state: PipelineState) -> PipelineState:
        pdf_path = Path(state["pdf_path"])
        out_dir = Path(state.get("output_dir") or cfg.output.dir)
        job_id = state.get("job_id") or f"job-{_utc_now_compact()}"
        out_docx = out_dir / f"{pdf_path.stem}.{job_id}.en-US.docx"
        return {
            **state,
            "job_id": job_id,
            "locale_source": cfg.pipeline.locale_source,
            "locale_target": cfg.pipeline.locale_target,
            "termbase_path": str(cfg.termbase.path),
            "termbase_rev": _termbase_rev(cfg.termbase.path),
            "output_dir": str(out_dir),
            "output_docx": str(out_docx),
            "stats": {},
        }

    def node_extract_a(state: PipelineState) -> PipelineState:
        r = extract_text_units_pymupdf(state["pdf_path"])
        stats = dict(state.get("stats") or {})
        stats["page_count"] = r.page_count
        stats["tu_count_a"] = len(r.tus)
        return {**state, "tus": r.tus, "stats": stats}

    def node_translate_a(state: PipelineState) -> PipelineState:
        tus = state.get("tus") or []
        out: list[TranslationUnit] = []
        stats = dict(state.get("stats") or {})
        translated = 0
        for tu in tus:
            constraints = term_agent.constraints_for_text(tu.source_text)
            text, _usage = llm.translate_zh_to_en(tu.source_text, must_use=constraints.must_use)
            out.append(
                TranslationUnit(
                    tu_id=tu.tu_id,
                    page_no=tu.page_no,
                    channel=tu.channel,
                    source_text=tu.source_text,
                    target_text=text,
                    term_hits=[it["term_id"] for it in constraints.must_use] if constraints.must_use else [],
                )
            )
            translated += 1
        stats["translated_a"] = translated
        return {**state, "tus": out, "stats": stats}

    def node_compose_docx(state: PipelineState) -> PipelineState:
        tus = state.get("tus") or []
        result = compose_docx_from_units(tus, state["output_docx"])
        stats = dict(state.get("stats") or {})
        stats["docx_paragraphs"] = result.paragraph_count
        return {**state, "stats": stats}

    g = StateGraph(PipelineState)
    g.add_node("init", node_init)
    g.add_node("extract_a", node_extract_a)
    g.add_node("translate_a", node_translate_a)
    g.add_node("compose_docx", node_compose_docx)

    g.set_entry_point("init")
    g.add_edge("init", "extract_a")
    g.add_edge("extract_a", "translate_a")
    g.add_edge("translate_a", "compose_docx")
    g.add_edge("compose_docx", END)

    return g.compile()


def run_pipeline(cfg: AppConfig, pdf_path: str | Path, output_dir: str | Path | None = None) -> RunResult:
    graph = build_graph(cfg)
    state: PipelineState = {"pdf_path": str(pdf_path)}
    if output_dir is not None:
        state["output_dir"] = str(output_dir)
    final_state = graph.invoke(state)

    docx = DocxComposeResult(output_path=Path(final_state["output_docx"]), paragraph_count=int(final_state["stats"]["docx_paragraphs"]))
    tus = final_state.get("tus") or []
    return RunResult(
        job_id=str(final_state["job_id"]),
        termbase_rev=str(final_state["termbase_rev"]),
        tu_count=len(tus),
        docx=docx,
    )

