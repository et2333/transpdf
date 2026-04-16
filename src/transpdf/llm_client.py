from __future__ import annotations

from dataclasses import dataclass

import httpx

from .config import LlmConfig

import json
import os
import time
from pathlib import Path


def _default_debug_log_path() -> Path:
    # Resolve to repo root (best-effort): .../src/transpdf/llm_client.py -> repo/
    here = Path(__file__).resolve()
    # parents: [transpdf, src, repo, ...]
    repo = here.parents[2] if len(here.parents) >= 3 else Path.cwd()
    return repo / "debug-8caa2c.log"


_DEBUG_LOG_PATH = Path(os.environ.get("TRANSPDF_DEBUG_LOG", str(_default_debug_log_path()))).resolve()


def debug_log_path() -> str:
    return str(_DEBUG_LOG_PATH)


def _dlog(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    # NEVER log secrets (api keys, tokens, etc.)
    payload = {
        "sessionId": "8caa2c",
        "runId": "pre-fix",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    _DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _DEBUG_LOG_PATH.exists():
        _DEBUG_LOG_PATH.write_text("", encoding="utf-8")
    with _DEBUG_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


@dataclass(frozen=True, slots=True)
class LlmUsage:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class LlmClient:
    def __init__(self, cfg: LlmConfig):
        self._cfg = cfg
        self._http = httpx.Client(
            base_url=cfg.base_url,
            headers={"Authorization": f"Bearer {cfg.api_key}"},
            timeout=httpx.Timeout(60.0),
        )
        # #region agent log
        _dlog(
            "H1-runtime-codepath",
            "llm_client.py:__init__",
            "Initialized LlmClient transport",
            {"transport": "httpx", "base_url": cfg.base_url, "model": cfg.model},
        )
        # #endregion agent log

    def translate_zh_to_en(self, source_text: str, must_use: list[dict]) -> tuple[str, LlmUsage]:
        glossary_lines = "\n".join([f'- {it["zh"]} => {it["en"]}' for it in must_use]) if must_use else ""
        system = (
            "You are a professional technical translator. Translate Chinese to English.\n"
            "Hard constraints:\n"
            "- Preserve numbers, units, paths, and identifiers as-is.\n"
            "- If a term from the glossary appears in the source, you MUST use the provided English translation.\n"
            "- Do not output any Chinese characters in the translation.\n"
            "Return only the translated English text, no extra commentary."
        )
        user = (
            f"Glossary (must-use):\n{glossary_lines}\n\n"
            f"Source (zh-CN):\n{source_text}"
        )

        payload = {
            "model": self._cfg.model,
            "temperature": self._cfg.temperature,
            "max_tokens": self._cfg.max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        # #region agent log
        _dlog(
            "H2-provider-error-body",
            "llm_client.py:translate_zh_to_en",
            "Sending chat/completions request",
            {"chars": len(source_text), "must_use_count": len(must_use), "model": self._cfg.model},
        )
        # #endregion agent log
        r = self._http.post("chat/completions", json=payload)
        if r.status_code >= 400:
            # Bubble up provider error details for debugging.
            # #region agent log
            _dlog(
                "H2-provider-error-body",
                "llm_client.py:translate_zh_to_en",
                "LLM request failed",
                {"status": r.status_code, "body_snippet": r.text[:800]},
            )
            # #endregion agent log
            raise RuntimeError(f"LLM request failed: status={r.status_code} body={r.text}")
        data = r.json()

        text = (((data.get("choices") or [])[0] or {}).get("message") or {}).get("content") or ""
        text = str(text).strip()
        usage_obj = data.get("usage") or {}
        usage = LlmUsage(
            prompt_tokens=usage_obj.get("prompt_tokens"),
            completion_tokens=usage_obj.get("completion_tokens"),
            total_tokens=usage_obj.get("total_tokens"),
        )
        return text, usage

