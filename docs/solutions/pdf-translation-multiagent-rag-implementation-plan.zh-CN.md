# PDF 多智能体翻译与术语 RAG：实施计划（中文）

本文档描述在 Windows 与 CI 环境下以 **Python** 为主栈、可插拔 LLM/OCR、兼顾可复制文本与图片 OCR 的 PDF 翻译落地路线；与《设计（中文）》配套阅读。

## 目标

- 将 **可复制文本** 与 **需 OCR 的图片区域** 统一纳入流水线，输出 **DOCX 可编辑稿** 与 **质量报告**。
- 通过 **config.yaml + 环境变量** 管理模型与密钥，避免硬编码，便于切换供应商与离线评测。
- 将 **图片类内容的人工复核率** 控制在 **<5%**（以页或块为统计口径，具体口径在 M1 冻结）。
- 以 **三件交付物** 为主线组织迭代：结构化中间件、DOCX、报告。

## 关键决策

| 决策项 | 结论 |
|--------|------|
| 主语言 | **Python 3.12+**（类型标注、丰富生态、Windows 友好） |
| LLM / OCR | **可插拔**：接口抽象 + `config.yaml` 声明实现类或端点 + **环境变量** 注入密钥与 endpoint |
| PDF 输入 | **双通道**：文本层直接抽取；扫描页/插图走 **OCR + 视觉理解**（可选多模态模型） |
| 图片人工 | **抽样 + 置信度阈值**：目标 **<5%** 进入人工复核队列 |
| 交付形态 | **三件**：① 结构化 JSONL/Parquet（TranslationUnit 等）② **DOCX** ③ **CSV/HTML 报告** |

## UTF-8 编码说明（Windows）

- 所有源码、配置、数据交换文件均使用 **UTF-8（无 BOM）**；PowerShell 5.x 默认 `UTF-8` 可能带 BOM，写入时请使用 `System.Text.UTF8Encoding($false)` 或 Python `open(..., encoding="utf-8")`（Python 3 默认不写 BOM）。
- 控制台日志若出现乱码，请设置终端代码页为 UTF-8（`chcp 65001`）或优先使用 **Python/IDE** 查看产物。
- **禁止** 将含中文的 JSON/CSV 以系统 ANSI 页另存，避免 `?` 替换字符。

## 建议仓库布局

```text
repo/
  config/
    config.example.yaml
  src/
    capgemini_translator/
      __init__.py
      orchestrator.py          # Orchestrator
      pdf_layout.py            # PdfLayout
      termbase_rag.py          # TermbaseRAG
      text_translation.py      # TextTranslation
      ocr_vision.py            # OcrVision
      image_overlay.py         # ImageOverlay
      docx_composer.py         # DocxComposer
      qa.py                    # QA
      models.py                # TermEntry, TranslationUnit, OverlayInstruction
      io_utils.py
  tests/
  docs/
    solutions/
      pdf-translation-multiagent-rag-design.zh-CN.md
      pdf-translation-multiagent-rag-design.en-US.md
      pdf-translation-multiagent-rag-implementation-plan.zh-CN.md
      sample-assets.en-US.md
  scripts/
    run_pipeline.py
  pyproject.toml / requirements.txt
```

> 样例与敏感输入的目录约定见：[sample-assets.en-US.md](sample-assets.en-US.md)。

## 配置与环境变量（字段建议）

### `config.yaml`（节选语义）

- `pipeline.locale_source` / `pipeline.locale_target`：源/目标语言 BCP-47。
- `llm.provider` / `llm.model` / `llm.temperature` / `llm.max_tokens`。
- `ocr.provider` / `ocr.lang` / `ocr.dpi`。
- `vision.provider`：图片描述或版式理解（可与 LLM 合并为同一多模态端点）。
- `termbase.path` / `termbase.embedding_model` / `termbase.top_k` / `termbase.refresh_cron`（可选）。
- `pdf.text_extraction.backend`：`pymupdf` / `pdfplumber` 等。
- `overlay.level_default`：`L1`–`L4`（见设计文档）。
- `qa.image_review.sample_rate` 与 `qa.image_review.confidence_threshold`：驱动 **<5%** 人工队列。
- `output.docx.template`（可选）：公司样式模板路径。

### 环境变量（示例命名）

- `LLM_API_KEY` / `LLM_BASE_URL`
- `OCR_API_KEY` / `OCR_BASE_URL`
- `VISION_API_KEY`（若独立）
- `EMBEDDING_API_KEY`（若与 LLM 不同）
- `TERMBASE_UPDATE_TOKEN`（增量更新钩子，可选）

> 具体键名以 `config.example.yaml` 为准；**密钥只走环境变量或密钥管理器**，不入库。

## 数据模型

### `TermEntry`

- `term_id: str`
- `source_term: str`
- `target_term: str`
- `domain: str | None`
- `notes: str | None`
- `synonyms: list[str]`（可选）
- `updated_at: datetime`

### `TranslationUnit`

- `tu_id: str`
- `page_no: int`
- `channel: Literal["A","B"]`（A=文本抽取，B=OCR/图像）
- `source_text: str`
- `target_text: str`
- `term_hits: list[str]`（命中的 `term_id`）
- `confidence: float | None`
- `bbox_norm: tuple[float,float,float,float] | None`（0–1 归一化坐标，可选）
- `style_hints: dict`（可选：标题/列表/脚注）

### `OverlayInstruction`

- `tu_id: str`
- `level: Literal["L1","L2","L3","L4"]`（与设计文档一致）
- `payload: dict`（例如替换文本、图片裁剪参数、字体大小建议）
- `requires_manual_review: bool`

## 模块接口（职责边界）

| 模块 | 接口名 | 职责 |
|------|--------|------|
| 编排 | `Orchestrator` | 解析配置、调度 A/B 通道、聚合状态机、写报告总览 |
| 版式 | `PdfLayout` | 页级结构、块级 bbox、阅读顺序、与 DOCX 样式映射 |
| 术语 | `TermbaseRAG` | 向量检索 + 过滤 + 命中解释；支持增量重建索引 |
| 文本翻译 | `TextTranslation` | 术语增强提示词、批量翻译、回退策略 |
| OCR/视觉 | `OcrVision` | 对 B 通道块 OCR；可选版式/元素分类 |
| 图像叠字 | `ImageOverlay` | 根据 `OverlayInstruction` 生成可编辑替代或占位策略 |
| 合成 | `DocxComposer` | 从 `TranslationUnit` 列表生成 DOCX |
| 质检 | `QA` | 规则扫描、LLM 二次审校（可选）、**图片人工队列** |

> 以上为 **Protocol / ABC** 级接口；实现类在 `config.yaml` 中绑定。

## 报告列（CSV/HTML 建议）

| 列名 | 说明 |
|------|------|
| `job_id` | 任务编号 |
| `file` | 源 PDF |
| `page` | 页码 |
| `channel` | A 或 B |
| `tu_id` | 翻译单元 ID |
| `source_excerpt` | 源文摘要（截断） |
| `target_excerpt` | 译文摘要 |
| `term_hit_count` | 术语命中数 |
| `confidence` | 模型置信度或启发式分数 |
| `qa_flags` | 规则命中标签（术语不一致、数字、单位等） |
| `manual_review` | 是否进入人工（图片类重点） |
| `duration_ms` | 处理耗时 |

## 里程碑 M0–M4

| 阶段 | 目标 | 主要产出 |
|------|------|----------|
| **M0** 基线 | 仓库骨架、配置范式、空跑流水线 | `config.example.yaml`、CI lint、最小 `Orchestrator` |
| **M1** 数据契约 | 冻结模型与报告口径 | `models.py`、JSON Schema（可选）、样例 JSONL |
| **M2** A 通道 | 可复制文本 E2E | `PdfLayout` + `TextTranslation` + `DocxComposer`（文本为主） |
| **M3** B 通道 | OCR + 叠字 + 人工队列 | `OcrVision` + `ImageOverlay` + `QA` 抽样逻辑 |
| **M4** 术语能力增强（RAG 可选） | 在两列词库（中文/英文）基础上补召回：向量检索、阈值策略、回归评测；并不改变“术语强约束”的基本原则 | `TermbaseRAG`（可选启用）、评测集、回归脚本、阈值/策略配置 |

### 关于「RAG 升级」的澄清（两列词库场景）

为实现项目目标（专有名词必须正确、词库可替换、词库更新后译文可同步），术语系统建议采用 **Lookup 强约束 + RAG 候选补召回**：

- **Lookup（强约束，必须）**：对两列词库做精确匹配（例如「翼菲智能」必须翻译为 Robotphoenix）。该路径保证确定性与可审计。
- **RAG（可选增强）**：构建词库向量索引，用于 **lookup 未命中**、**OCR 噪声**、**近似表述** 等场景的候选召回。\n  - 默认不直接强制替换：RAG 输出候选词条与相似度，达到阈值才升级为 must-use，否则进入术语报告/人工队列，避免误命中。

> 结论：RAG 不是“必须才能成功”的前置条件；它是对“漏召回/噪声场景”的可选增强，是否启用与阈值以黄金样例集回归结果为准。

## 验收标准（摘要）

- 给定 **含可复制文本** 的样例 PDF：可生成 **无乱码 UTF-8** 中间件与 **DOCX**，核心术语与数字不被擅自改写（允许配置关闭创意性）。
- 给定 **扫描页或图片块** 样例：B 通道可产出译文与 `OverlayInstruction`；**进入人工复核的块占比 <5%**（在默认阈值下，基于固定黄金集）。
- `config.yaml` **切换 LLM/OCR 提供商** 无需改业务代码路径（仅改配置与密钥）。
- 报告包含上表列，并可按 `manual_review=true` 过滤。

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| PDF 字体子集化导致抽取乱码 | 多后端抽取回退；异常页标记并走 B 通道 |
| OCR 语言误判 | 语言检测 + 页级配置覆盖 |
| 术语表漂移 | 版本化 `TermEntry`；索引重建可重复 |
| 成本激增 | 批处理、缓存、视觉调用仅对 B 通道与低置信子集 |
| Windows 路径与编码 | 统一 `pathlib`；UTF-8 无 BOM；CI 加编码自检 |

## 实施过程中需拍板的四项（随迭代收敛）

1. **「<5% 图片人工」统计口径**：按页、按图块还是按字符面积占比。
2. **L1–L4 默认策略与回退**：当目标字体缺失时的降级规则。
3. **术语命中冲突裁决**：多条 `TermEntry` 重叠时的优先级（领域、最近更新、人工权重）。
4. **DOCX 样式来源**：纯程序生成 vs. 公司模板映射表维护方式。

---

*文档版本：与仓库同步演进；变更请走 PR 说明编码与配置兼容性。*