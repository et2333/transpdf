# transpdf

Translate a Chinese operation manual PDF into English and deliver a **Word (.docx)** output, while enforcing an enterprise termbase and supporting termbase updates with incremental re-translation.

Termbase strategy (current): **two-column termbase + deterministic lookup (strong constraint)** first; **RAG is optional** and used only for candidate recall in noisy / missed-match cases.

## User Guide (delivery / operators)

### Inputs

- **Manual PDF**: place the source PDF under `data/incoming/` (sensitive; not committed).
- **Enterprise termbase**: currently maintained as a 2-column (ZH / EN) Word file under `data/incoming/` (sensitive; not committed).
  - Default mode is `lookup` (strong constraint). Optional `rag` mode is an enhancement and should be gated by golden set evaluation.

### Outputs (“three-piece set”)

1. **English Word (.docx)**: structure best-effort (headings/numbering/tables/image placement).
2. **Terminology report**: split by Channel A (copyable text) / Channel B (image OCR), recommended **Excel + JSONL**.
3. **QA report**: practical checks (residual Chinese, terminology compliance, number/unit consistency, missing content, image overlay stats).

### Termbase updates → translation sync

When the termbase changes, the system should:

- compute a new `termbase_rev`
- identify impacted translation units (TUs)
- re-translate only impacted units (or fall back to full rerun)
- re-compose the DOCX and regenerate reports

## Developer Guide

### Project docs (do not delete)

See `CONTRIBUTING.md` for the non-deletion policy. Key docs live under `docs/solutions/`:

- `transpdf-design.zh-CN.md` (primary)
- `transpdf-design.en-US.md` (backup)
- `transpdf-implementation-plan.zh-CN.md` (primary)

### Directory layout

- `data/incoming/`: customer originals and other sensitive inputs (gitignored)
- `fixtures/`: safe-to-commit golden samples (optional; for regression/CI)
- `docs/solutions/`: design & plans
- `src/transpdf/`: Python package (including `agents/`)
- `config/`: configuration examples
- `scripts/`: local entry points / smoke checks

See `docs/solutions/sample-assets.en-US.md` for details.

### Encoding (Windows)

Save Markdown as **UTF-8 (no BOM)** to avoid garbled text.

