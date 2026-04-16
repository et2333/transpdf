# Sample assets and sensitive inputs

This document explains where to place sample PDFs and the enterprise termbase for the **transpdf** project.

## Recommended locations

| Purpose | Path | Notes |
|--------|------|------|
| Golden samples (safe to commit) | `fixtures/` | Optional. Use for regression and CI gates (“golden set”). |
| Customer originals / sensitive files | `data/incoming/` | **Not committed**. This repo gitignores most files under this directory. |
| Design & plans | `docs/solutions/` | Markdown only. Do not store binary customer inputs here. |

## What is the “golden set”?

The **golden set** is a versioned, fixed subset of inputs (selected pages / image blocks) used to:

- compare changes across model/prompt/overlay iterations
- measure terminology compliance and image review rate consistently

It is not the full customer dataset.

## About `.gitignore` (for `data/incoming/`)

This repo ignores `data/incoming/*` by default, so PDFs and the termbase docx placed there will not be committed.

