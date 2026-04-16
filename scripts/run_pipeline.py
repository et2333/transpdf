from __future__ import annotations

import argparse
import os
import json
import time
from pathlib import Path

import transpdf
import transpdf.llm_client
import httpx

from transpdf.config import load_config
from transpdf.orchestrator import run_pipeline


def main() -> None:
    ap = argparse.ArgumentParser(description="transpdf minimal pipeline (Channel A).")
    ap.add_argument("--config", default="config/config.example.yaml", help="Path to config yaml.")
    ap.add_argument("--pdf", default=None, help="Input PDF path (optional; falls back to config input.pdf_path).")
    ap.add_argument("--out", default=None, help="Output directory (optional).")
    args = ap.parse_args()

    # Always write debug log to repo root (independent of cwd).
    debug_log = Path(__file__).resolve().parents[1] / "debug-8caa2c.log"
    debug_log.parent.mkdir(parents=True, exist_ok=True)
    with debug_log.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "sessionId": "8caa2c",
                    "runId": "pre-fix",
                    "hypothesisId": "H0-entry",
                    "location": "run_pipeline.py:main",
                    "message": "CLI entry",
                    "data": {},
                    "timestamp": int(time.time() * 1000),
                },
                ensure_ascii=False,
            )
            + "\n"
        )

    print(f"cwd={os.getcwd()}")
    print(f"transpdf_version={getattr(transpdf, '__version__', 'unknown')}")
    print(f"transpdf_pkg_path={transpdf.__file__}")
    print(f"llm_client_path={transpdf.llm_client.__file__}")
    print(f"debug_log_path={transpdf.llm_client.debug_log_path()}")
    print(f"debug_log_exists={debug_log.exists()} debug_log={debug_log}")

    with debug_log.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "sessionId": "8caa2c",
                    "runId": "pre-fix",
                    "hypothesisId": "H0-entry",
                    "location": "run_pipeline.py:main",
                    "message": "Runtime paths",
                    "data": {
                        "cwd": os.getcwd(),
                        "transpdf_pkg_path": transpdf.__file__,
                        "llm_client_path": transpdf.llm_client.__file__,
                        "debug_log_path": transpdf.llm_client.debug_log_path(),
                    },
                    "timestamp": int(time.time() * 1000),
                },
                ensure_ascii=False,
            )
            + "\n"
        )

    cfg = load_config(args.config)
    pdf_path = Path(args.pdf) if args.pdf else cfg.input.pdf_path
    if not pdf_path:
        raise SystemExit("Missing PDF path. Provide --pdf or set input.pdf_path in config.")

    # Preflight: validate Gemini OpenAI-compatible auth early (avoid long stack traces).
    try:
        r = httpx.get(
            cfg.llm.base_url + "models",
            headers={"Authorization": f"Bearer {cfg.llm.api_key}"},
            timeout=20.0,
        )
        if r.status_code >= 400:
            raise SystemExit(
                "LLM auth preflight failed.\n"
                f"status={r.status_code}\n"
                f"body={r.text}\n\n"
                "If you see API_KEY_INVALID, regenerate a Gemini API key in Google AI Studio "
                "and ensure the correct project/billing is selected."
            )
    except httpx.HTTPError as e:
        raise SystemExit(f"LLM preflight request failed: {e}") from e

    result = run_pipeline(cfg, pdf_path=pdf_path, output_dir=Path(args.out) if args.out else None)
    print(f"job_id={result.job_id}")
    print(f"termbase_rev={result.termbase_rev}")
    print(f"tu_count={result.tu_count}")
    print(f"docx={result.docx.output_path}")


if __name__ == "__main__":
    main()

