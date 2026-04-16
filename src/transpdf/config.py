from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


_ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")

def _load_dotenv_if_present(dotenv_path: Path) -> None:
    """
    Minimal .env loader.

    - Supports KEY=VALUE per line
    - Ignores blank lines and lines starting with '#'
    - Does NOT override existing os.environ values
    """
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip("'").strip('"')
        if not k:
            continue
        os.environ.setdefault(k, v)


def _expand_env_vars(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _expand_env_vars(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand_env_vars(v) for v in obj]
    if isinstance(obj, str):
        def repl(m: re.Match[str]) -> str:
            key = m.group(1)
            return os.environ.get(key, "")

        return _ENV_PATTERN.sub(repl, obj)
    return obj


@dataclass(frozen=True, slots=True)
class LlmConfig:
    base_url: str
    api_key: str
    model: str
    temperature: float = 0.1
    max_tokens: int = 2048

    def normalized(self) -> "LlmConfig":
        # Guard against accidentally embedding credentials in the URL (e.g. ?key=...),
        # which can cause "Multiple authentication credentials received" errors.
        base_url = self.base_url.split("?", 1)[0].strip()
        return LlmConfig(
            base_url=base_url,
            api_key=self.api_key,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )


@dataclass(frozen=True, slots=True)
class TermbaseConfig:
    path: Path
    mode: str = "lookup"


@dataclass(frozen=True, slots=True)
class OutputConfig:
    dir: Path


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    locale_source: str = "zh-CN"
    locale_target: str = "en-US"


@dataclass(frozen=True, slots=True)
class InputConfig:
    pdf_path: Path | None = None


@dataclass(frozen=True, slots=True)
class AppConfig:
    pipeline: PipelineConfig
    input: InputConfig
    llm: LlmConfig
    termbase: TermbaseConfig
    output: OutputConfig


def load_config(path: str | Path) -> AppConfig:
    p = Path(path)
    # Allow local development without having to export env vars manually.
    # We search for a repo-root `.env` next to `pyproject.toml` (best effort).
    repo_root = p.resolve().parent.parent if p.resolve().parent.name == "config" else p.resolve().parent
    _load_dotenv_if_present(repo_root / ".env")

    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    raw = _expand_env_vars(raw)

    pipeline = raw.get("pipeline", {}) or {}
    input_ = raw.get("input", {}) or {}
    llm = raw.get("llm", {}) or {}
    termbase = raw.get("termbase", {}) or {}
    output = raw.get("output", {}) or {}

    cfg = AppConfig(
        pipeline=PipelineConfig(
            locale_source=str(pipeline.get("locale_source", "zh-CN")),
            locale_target=str(pipeline.get("locale_target", "en-US")),
        ),
        input=InputConfig(
            pdf_path=Path(str(input_.get("pdf_path"))) if input_.get("pdf_path") else None
        ),
        llm=LlmConfig(
            base_url=str(llm.get("base_url", "")),
            api_key=str(llm.get("api_key", "")),
            model=str(llm.get("model", "")),
            temperature=float(llm.get("temperature", 0.1)),
            max_tokens=int(llm.get("max_tokens", 2048)),
        ).normalized(),
        termbase=TermbaseConfig(
            path=Path(str(termbase.get("path", ""))),
            mode=str(termbase.get("mode", "lookup")),
        ),
        output=OutputConfig(dir=Path(str(output.get("dir", "outputs")))),
    )

    if not cfg.llm.base_url:
        raise ValueError("llm.base_url is required (set env var in config.example.yaml).")
    if not cfg.llm.api_key:
        raise ValueError("llm.api_key is required (set env var in config.example.yaml).")
    if not cfg.llm.model:
        raise ValueError("llm.model is required.")
    if not cfg.termbase.path:
        raise ValueError("termbase.path is required.")

    return cfg

