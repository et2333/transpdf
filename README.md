# transpdf

Translate a Chinese operation manual PDF into English and deliver a **Word (.docx)** output, while enforcing an enterprise termbase and supporting termbase updates with incremental re-translation.

## User Guide (delivery / operators)

### Inputs

- **Manual PDF**: place the source PDF under `data/incoming/` (sensitive; not committed).
- **Enterprise termbase**: currently maintained as a 2-column (ZH / EN) Word file under `data/incoming/` (sensitive; not committed).

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

- `pdf-translation-multiagent-rag-design.zh-CN.md` (primary)
- `pdf-translation-multiagent-rag-design.en-US.md` (backup)
- `pdf-translation-multiagent-rag-implementation-plan.zh-CN.md` (primary)

### Directory layout

- `data/incoming/`: customer originals and other sensitive inputs (gitignored)
- `fixtures/`: safe-to-commit golden samples (optional; for regression/CI)
- `docs/solutions/`: design & plans

See `docs/solutions/sample-assets.en-US.md` for details.

### Encoding (Windows)

Save Markdown as **UTF-8 (no BOM)** to avoid garbled text.

