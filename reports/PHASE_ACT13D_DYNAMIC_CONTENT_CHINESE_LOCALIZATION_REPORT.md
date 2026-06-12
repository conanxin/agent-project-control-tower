# ACT-13D — Dashboard Dynamic Content Chinese Localization — Phase Report

> 在 ACT-13B（静态 UI 中文化）之上，把"动态内容"（项目摘要、阶段名、下一步、
> 最近活动原文、项目名）也改成中文优先。所有 24 个真实事件做了中文映射；
> `project_id` / `agent_id` / `repo` / `source_commit` / `phase_id`
> 这些机器字段保留英文。**没有改动任何 public-data JSON**。

---

## 1. 执行摘要

ACT-13D 完成。Dashboard 4 个主要页面（首页 / Timeline / 项目详情 / Agent 详情）
的"动态内容"现在全部中文优先显示：

- **项目名**：首页和项目详情页同时显示中文项目名（`Agent 项目控制塔` /
  `Artvee 艺术图库` / `BookTrans Desk`），保留英文原文在「（原文：…）」小字里。
- **阶段名**：所有 24 个真实事件的 `phase_name` 都做了中文映射，例如
  `S13 · 阻塞修复与人工验证重跑`、`P3B · 每日灵感摘要`、
  `ACT-12 · 周期性 public-data 更新试验`。
- **项目摘要 / 下一步**：首页和项目页"最新事件"卡片显示中文 summary /
  next，英文原文折叠在 `原文` 区域里。
- **Timeline**：每条事件显示中文 phase_name + summary。
- **Search filter**：搜索栏同时覆盖中英文 summary / 项目名 / 阶段名。
- **机器字段保留英文**：`project_id` / `agent_id` / `event_id` / `repo` /
  `source_commit` / `phase_id` 全部保持原文。

新增 commit `0b1eb8a`，push 成功；线上 https://control-tower.conanxin.com/
已通过 curl 验证，全部新中文文案均命中。

## 2. 为什么 ACT-13B 后仍需要 ACT-13D

ACT-13B 解决了"页面骨架"的中文化：导航、表格列名、按钮文案、状态徽标。
但用户实际浏览 dashboard 时看到的内容主要是"动态内容"——也就是从
`public-data/events/*.json` 和 `public-data/registry/*.yml` 里读出来的
英文原文：

| 字段 | ACT-13B 状态 | ACT-13D 状态 |
| --- | --- | --- |
| 导航 / 标题 / 列名 | ✅ 中文 | — |
| 状态徽标（PASS / PARTIAL / ACTIVE…） | ✅ 中文 + 英文双语 | — |
| 事件类型徽标（阶段 / 复查 / 交接…） | ✅ 中文 | — |
| 项目摘要（"Added daily inspiration digest…"） | ❌ 英文原文 | ✅ 中文 |
| 阶段名（"S13 — Blocker Fixes…"） | ❌ 英文原文 | ✅ 中文 |
| 下一步（"Continue release hardening…"） | ❌ 英文原文 | ✅ 中文 |
| Timeline 整页事件摘要 | ❌ 英文原文 | ✅ 中文 |

如果不做 ACT-13D，dashboard 的"门面"中文了，但内容主体还是英文，违背
"中文优先"承诺。

## 3. 哪些内容来自 public-data 原始英文

| 字段 | 来源 | 例子 |
| --- | --- | --- |
| `project.name` | `public-data/registry/projects.yml` | `"BookTrans Desk"`、`"Artvee Gallery"` |
| `project.current_phase_name` | `public-data/registry/projects.yml` | `"S13 — Blocker Fixes and Manual Validation Rerun"` |
| `project.last_summary` | `public-data/registry/projects.yml`（由 build_index 从 events 聚合） | `"S13 reran the S11 blocker fixes…"` |
| `project.next` | `public-data/registry/projects.yml` | `"Continue release hardening and documentation…"` |
| `timeline[i].phase_name` | `public-data/events/*.json` | `"Recurring Public-data Update Trial"` |
| `timeline[i].summary` | `public-data/events/*.json` | `"Ran a real recurring public-data update trial using the ACT-11 preflight workflow…"` |
| `timeline[i].next` | `public-data/events/*.json` | `"Enter ACT-10B for release polish screenshots or ACT-12B for a second recurring update trial."` |

## 4. 本阶段采取的显示层中文映射策略

**不直接修改 public-data JSON**（这是公开快照的 source of truth）。
**不改 build_index.py**（已经是纯数据 → generated 转换器，没有"翻译"职责）。
**不改 generated/index.json**（build 产物，不应手改）。

新增一个**纯 TypeScript 显示层**：

```
apps/dashboard/src/lib/localized-content.ts
  ├── PROJECT_DISPLAY          // 3 项目（id → {nameZh, descriptionZh}）
  ├── EVENT_ZH                 // 24 事件（"project_id::phase_id" → {phaseNameZh, summaryZh, nextZh}）
  ├── getProjectDisplay(p)     // helper
  ├── getLocalizedEvent(t)     // helper，自动 fallback
  ├── hasLocalizedMapping(t)   // helper，判断是否需要"原文"折叠
  └── EVENT_TYPE_LABEL ...     // 重新导出静态 UI 标签
```

**Fallback 行为**：

```ts
// getLocalizedEvent 的 fallback 顺序
// 1. "agent-project-control-tower::ACT-12" 在 EVENT_ZH 里有？→ 返回中文。
// 2. 没找到？返回原始 phase_name / summary / next（英文）。
// 3. summary / phase_id 是 null？安全处理，返回空字符串。
// 4. 永远不 throw。partial map 永远不会破坏 build。
```

## 5. 为什么不直接修改 public-data

5 个原因：

1. **source of truth 不变**：public-data 是 Git 跟踪的公开快照，agent /
   其它 dashboard 用英文原文做 grep / 比对。改 public-data 会破坏它们。
2. **不可逆**：export_public_data.py 会覆盖 public-data。任何时候跑
   `make public-update-preflight` 都会把 data/ → public-data，万一 data/
   里没中文，public-data 又会回到英文。所以显示层才是稳定位置。
3. **简洁**：24 个 event 现在手工 curated 中文映射，加在 1 个 TS 文件里
   比改 24 个 JSON 容易。
4. **可演进**：未来 phase 命名变化，只需在 `localized-content.ts` 加一行。
   public-data 改动需要 commit + 触发部署。
5. **可审查**：所有中文决策集中在一个文件里 diff / review，public-data
   改动会"掺"在 build 流程里。

## 6. 新增 localized-content.ts

| 函数 | 行为 | Fallback |
| --- | --- | --- |
| `getProjectDisplay(p)` | 返回 `{nameZh, descriptionZh}` | `nameZh` ← `p.name`；`descriptionZh` ← `""` |
| `getLocalizedEvent(t)` | 返回 `{phaseNameZh, summaryZh, nextZh}` | 各字段 ← 原始 `t.*` |
| `hasLocalizedMapping(t)` | bool，UI 用此判断是否渲染 "原文" 折叠 | — |
| `EVENT_TYPE_LABEL` / `STATUS_LABEL` / `HEALTH_LABEL` | 从 `labels.ts` re-export | 已在 ACT-13B 处理 |

## 7. 中文映射覆盖范围

| 类别 | 数量 | 说明 |
| --- | --- | --- |
| 项目 | 3 / 3 | `agent-project-control-tower` / `artvee-gallery` / `booktrans-desk` |
| 事件 | 24 / 24 | 100% 覆盖（24 个真实事件中，22 个 `PHASE_REPORT` + 2 个 `REVIEW_REPORT`） |
| 注册事件 | 2 / 2 | `PROJECT_REGISTERED` 和 `AGENT_REGISTERED`（虽然 public-data 里是 4 个，但 4 个都是 `::registration` key） |
| 总计 | 27 映射项 | 0 fallback，0 build break |

### 项目中文映射

| `project_id` | 中文名 | 中文简介 |
| --- | --- | --- |
| `agent-project-control-tower` | Agent 项目控制塔 | 用 Git 记录多个 agent 项目的阶段进展，并通过 Cloudflare Dashboard 在线展示。 |
| `artvee-gallery` | Artvee 艺术图库 | 开源艺术图库与每日灵感摘要项目，负责抓取、整理和展示艺术作品灵感内容。 |
| `booktrans-desk` | BookTrans Desk | 面向 PDF / EPUB 翻译与结构化导出的桌面工具项目。 |

### 阶段中文映射（部分）

| `project_id` | `phase_id` | 中文阶段名 |
| --- | --- | --- |
| `agent-project-control-tower` | `ACT-0` | 项目设计与架构 |
| `agent-project-control-tower` | `ACT-1` | 本地数据流原型 |
| `agent-project-control-tower` | `ACT-2` | Tower CLI 与事件上报 |
| `agent-project-control-tower` | `ACT-3A` | Astro 面板骨架 |
| `agent-project-control-tower` | `ACT-5` | Cloudflare Pages 上线验证 |
| `agent-project-control-tower` | `ACT-5B` | 自定义域名验证 |
| `agent-project-control-tower` | `ACT-6` | 首个真实项目公开导出 |
| `agent-project-control-tower` | `ACT-6B` | 第二个真实项目公开导出 |
| `agent-project-control-tower` | `ACT-6C` | 第三个真实项目公开导出 |
| `agent-project-control-tower` | `ACT-7` | 多机 Agent 使用手册 |
| `agent-project-control-tower` | `ACT-8` | 真实多 Agent 上手试验 |
| `agent-project-control-tower` | `ACT-8B` | 生成命令的多 Agent 试验 |
| `agent-project-control-tower` | `ACT-9` | public-data 导出自动化策略 |
| `agent-project-control-tower` | `ACT-9B` | CI 候选导出 Artifact 原型 |
| `agent-project-control-tower` | `ACT-9C` | 导出计划审查工作流 |
| `agent-project-control-tower` | `ACT-11` | public-data 更新预检流程 |
| `agent-project-control-tower` | `ACT-12` | 周期性 public-data 更新试验 |
| `agent-project-control-tower` | `ACT-8-review` | 第二个 Agent 对 ACT-7 手册的复查 |
| `agent-project-control-tower` | `ACT-8B-review` | 第二个 Agent 对生成命令试验的复查 |
| `artvee-gallery` | `P2` | 公开 Demo 导出 |
| `artvee-gallery` | `P3B` | 每日灵感摘要 |
| `booktrans-desk` | `S13` | 阻塞修复与人工验证重跑 |

## 8. Fallback 机制

- **有映射**：显示中文，"原文"折叠区显示英文。
- **无映射**：直接显示英文，不显示"原文"折叠区。
- **新事件**：`localized-content.ts` 加一行即可，不动其它文件。
- **缺失 summary / next / phase_name**：不渲染该字段（empty string / null），不报错。

UI 端的具体表现（`TimelineItem.astro`）：

```astro
const phaseNameDisplay = zh.phaseNameZh && zh.phaseNameZh !== t.phase_name
  ? zh.phaseNameZh
  : (t.phase_name ?? "");
const summaryDisplay = zh.summaryZh && zh.summaryZh !== t.summary
  ? zh.summaryZh
  : (t.summary ?? "");
const showOrig = hasLocalizedMapping(t) && !!t.summary
              && summaryDisplay === zh.summaryZh;
```

只有**有中文映射**且**原文非空**才显示"原文"折叠区。

## 9. 页面修改范围

| 文件 | 改动 |
| --- | --- |
| `apps/dashboard/src/lib/localized-content.ts` | **新增** 16.4 KB — 中文映射中心 + helper |
| `apps/dashboard/src/components/ProjectCard.astro` | 改：项目名优先用中文，保留"（原文：…）"小字 |
| `apps/dashboard/src/components/TimelineItem.astro` | 改：phase_name / summary 用中文，加"原文"折叠区 |
| `apps/dashboard/src/pages/index.astro` | 改：`data-name-zh` / `data-summary-zh` 加到 dataset；form 加 search-target |
| `apps/dashboard/src/pages/timeline.astro` | 改：`data-summary-zh` / `data-phase_name-zh` 加到 dataset；form 加 search-target |
| `apps/dashboard/src/pages/projects/[project_id].astro` | 改：项目名、简介、当前阶段、最新事件 summary / next、阶段组标题都中文化 |
| `apps/dashboard/src/pages/agents/[agent_id].astro` | 改：参与项目列表显示中文名 |
| `apps/dashboard/src/pages/help.astro` | 改：新增"为什么有些字段仍保留英文？"小节 |
| `templates/telegram/report-phase.txt` | 改：phase_name / summary / next 提示用中文 |
| `templates/telegram/report-phase-artvee-example.txt` | 改：示例 phase_name / summary / next 改为中文，hard rules 加 ACT-13D 提示 |
| `README.md` | 改：状态行 + ACT-13D 段落 |
| `docs/MVP_PLAN.md` | 改：当前阶段 ACT-13D + 时间线 |

## 10. Help / template 更新

### Help 页

新增章节「为什么有些字段仍保留英文？」，3 个 sub-section：

- **机器字段清单**：`project_id` / `agent_id` / `event_id` / `repo` /
  `source_commit` / `phase_id`（举具体例子说明为什么不能翻译）
- **未来新增事件怎么办**：临时显示英文 + 折叠"原文"；补中文只需
  `localized-content.ts` 加一行
- **发阶段报告时怎么避免再次出现英文**：summary / next 建议中文；
  phase_name 可中文优先；source_repo / source_commit 保持原文

### Telegram 模板

- `report-phase.txt`：每个字段加 ACT-13D 注释（`# prefer Chinese`）
- `report-phase-artvee-example.txt`：
  - 实际命令示例改为中文（`--phase-name "P5F · 精选后正式发布"`）
  - hard rules 末尾加 ACT-13D 提示：
    > ACT-13D: prefer Chinese for --summary, --next, --phase-name.
    > The dashboard will display the Chinese text first; the original
    > English (if any) hides behind a "原文" toggle. --project-id /
    > --agent-id / --source-repo / --source-commit stay verbatim.

## 11. make all 结果

跟 baseline 一致：9 个历史 FAIL（ACT-1/ACT-2D fixture，本阶段不动）。

## 12. make publish-preflight 结果

✅ PASS。`public-data/`, `generated/`, `site/embedded`, `apps/dashboard/dist/`
全部 rebuild from public-data。**临时**把 ACT-13 / ACT-13B / ACT-13C 历史
event re-export 进 public-data / events_count=27 — 本阶段结束后立即
`git checkout HEAD -- public-data/MANIFEST.json site/index.embedded.html` +
`rm <history events>` 恢复 baseline。

## 13. make public-update-preflight 结果

✅ PASS：
- `project_count_meets_plan`: 3/3
- `booktrans_repo_not_homepage`: `conanxin/booktrans-desk` (OK)
- `booktrans_no_hp33`: 0 events

## 14. make public-update-test 结果

✅ PASS（11/11 ok）。

## 15. npm run build 结果

✅ 8 pages built in 3.18s。`dist/` 中：
- 中文 `phaseNameZh` / `summaryZh` 全部出现
- 英文原文仍在 hidden `<details>` 折叠区（24 处 "原文" toggle）
- data-* 搜索 attribute 包含中英文双版本

## 16. 敏感扫描结果

唯一命中全部是**教学反例 / 政策定义 / 历史上下文**，无真实敏感信息：

- README.md L682 / L801 / DEPLOYMENT_PLAN.md L563：扫描结果 "0 hits" 表格
- PUBLIC_DATA_AUTOMATION_POLICY.md L251：政策定义本身列出了哪些是 FAIL
- README.md L1645：`api_key=sk-123...abcdef` 是反例占位符

gitignore 检查 PASS（data/ / generated/ / artifacts/ / dist/ / node_modules/ / .env 全部 `!!`）。

## 17. 线上验收结果

| 路径 | 命中关键词 |
| --- | --- |
| `/` | `Artvee 艺术图库` / `开源艺术图库与每日灵感摘要` / `BookTrans Desk` / `面向 PDF` |
| `/timeline/` | `周期性 public-data 更新试验` / `本地数据流原型` / `项目设计与架构` / `阻塞修复与人工验证重跑` / `每日灵感摘要` / `原文`（24 处折叠区） |
| `/projects/booktrans-desk/` | `阻塞修复与人工验证重跑` / `部分完成 · PARTIAL` / `16f38b6` / `conanxin/booktrans-desk` |
| `/projects/artvee-gallery/` | `每日灵感摘要` / `Artvee 艺术图库` / `P3B` |
| `/agents/local-hermes/` | `本地数据流原型`（timeline 中文 phase_name 出现） |
| `/agents/cloud-openclaw/` | `生成命令的多 Agent 试验`（timeline 中文 phase_name 出现） |
| `/help/` | `为什么有些字段仍保留英文？`（新增章节命中） |

## 18. 当前公开边界

| 不变式 | 状态 |
| --- | --- |
| `public-data/` 范围 | ✅ 未变（3 projects / 2 agents / 24 events） |
| `data/` 是否仍 gitignored | ✅ 是 |
| `generated/` 是否仍 gitignored | ✅ 是 |
| `artifacts/` 是否未提交 | ✅ 是（gitignored） |
| `apps/dashboard/dist/` 是否未提交 | ✅ 是（gitignored） |
| `node_modules/` 是否未提交 | ✅ 是（gitignored） |
| `.env` 是否未提交 | ✅ 是（gitignored） |
| 双门模型 | ✅ 不变（trial agent 不能 export public-data / git add public-data / git push） |
| 自动化等级 | ✅ 不变（Level 1.5 人工辅助本地更新） |
| 公开数据真实事件 | ✅ 仍是 24 events（未新增 ACT-13/13B/13C 到 public-data） |

## 19. 下一阶段建议

回到 `wait-for-real-update` 状态：

| 触发器 | 期望路径 |
| --- | --- |
| BookTrans Desk `S14+` 真实事件 | `tower.py report-phase` → Step 4-9 → ACT-12B |
| Artvee Gallery `P3C+` 真实事件 | 同上 |
| Control Tower `ACT-14+` 真实事件 | 同上 |
| 其他真实项目首次接入 | 走 ACT-6 同款 register-project → report-phase 流程 |

下一步 ACT-12B 复用 ACT-11 preflight + ACT-12 经验，新事件的中文映射在
`localized-content.ts` 加一行（`"project_id::phase_id"` → 中文）。

## 20. 文件改动清单

| 路径 | 改动 | 字节 |
| --- | --- | --- |
| `apps/dashboard/src/lib/localized-content.ts` | 新增 | +16.4 KB |
| `apps/dashboard/src/components/ProjectCard.astro` | 改 | +0.4 KB |
| `apps/dashboard/src/components/TimelineItem.astro` | 改 | +0.9 KB |
| `apps/dashboard/src/pages/index.astro` | 改 | +1.0 KB |
| `apps/dashboard/src/pages/timeline.astro` | 改 | +0.9 KB |
| `apps/dashboard/src/pages/projects/[project_id].astro` | 改 | +2.0 KB |
| `apps/dashboard/src/pages/agents/[agent_id].astro` | 改 | +0.6 KB |
| `apps/dashboard/src/pages/help.astro` | 改 | +1.4 KB |
| `templates/telegram/report-phase.txt` | 改 | +0.2 KB |
| `templates/telegram/report-phase-artvee-example.txt` | 改 | +0.7 KB |
| `README.md` | 改 | +0.7 KB |
| `docs/MVP_PLAN.md` | 改 | +0.4 KB |
| **总计** | **12 文件** | **+26 KB / -3 KB** |

## 21. commit hash

`0b1eb8a`（push 成功，`2b53023..0b1eb8a main -> main`）。
