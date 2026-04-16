# Contributing to transpdf

This repository contains the design and implementation plan for the **PDF manual translation pipeline** (CN PDF → EN DOCX) with an enterprise termbase.

Termbase strategy (current): **two-column termbase + deterministic lookup (strong constraint)** first; **RAG is optional** and used only for candidate recall in noisy / missed-match cases.

## Critical documentation policy (DO NOT DELETE)

The following documents are **project anchors**. They must **never** be deleted or replaced with unrelated content.

- `docs/solutions/transpdf-design.zh-CN.md`
- `docs/solutions/transpdf-design.en-US.md`
- `docs/solutions/transpdf-implementation-plan.zh-CN.md`

### Allowed changes (append-only)

You may **only**:

- **Add new sections** (recommended at the end)
- **Add a changelog entry** (see below)
- **Add clarifications** without removing prior decisions (keep historical context)

### Not allowed

- Deleting any of the anchor documents
- Renaming/moving them without an explicit repo-wide decision
- Rewriting the whole document and losing history

## How to update docs safely

When you need to change an approach or decision:

1. Add a short section titled `Update (YYYY-MM-DD)` describing:
   - what changed
   - why it changed (goal/risk/cost)
   - any compatibility impact (inputs/outputs/paths)
2. Keep the previous text as historical record.

## Encoding (Windows)

All Markdown files must be saved as **UTF-8 (no BOM)** to avoid garbled text on Windows and in CI.

