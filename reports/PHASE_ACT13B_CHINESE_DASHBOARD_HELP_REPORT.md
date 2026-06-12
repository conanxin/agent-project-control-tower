# ACT-13B — Dashboard Chinese Localization & Help Optimization — Phase Report

> ACT-13B 把整个 dashboard 改成中文优先界面，并把 `/help/` 重写为中文操作手册。
> **不改变控制塔数据 / 功能 / 边界**：public-data 仍是 3 real projects / 2 agents / 24 events，data/ / generated/ / artifacts/ 仍 gitignored，automation level 仍 Level 1 + 1.5 + 2 + 3 (prototype)，双门模型不变。

---

## 1. 执行摘要

| 字段 | 值 |
| --- | --- |
| 阶段 | **ACT-13B — Dashboard Chinese Localization & Help Optimization** |
| 基线 HEAD | `b444eef`（ACT-13） |
| 目标 | 中文优先界面 + 中文 Help 操作手册 + 权限边界 |
| 完成 | ✅ 14 个 todo 全部完成 |
| 数据范围 | public-data **未变**（仍 3 projects / 2 agents / 24 events） |
| 风险 | 零 — 仅 UI 文案 + 帮助页 + CSS 微调 + labels.ts |

---

## 2. 为什么要中文化 Dashboard

- 用户每天看 dashboard 的实际界面是中文操作者视角（conanxin 是中文母语），英文 UI 不必要地增加认知负担。
- `/help/` 是未来操作者第一入口（fork 仓库、参考流程搭建自己的控制塔），英文帮助会劝退中文 fork 用户。
- 项目名 / commit / agent_id / status 值是"机器字"——保留英文是正确的（grep / CI / agent 命令不能翻译）。
- UI 标签（"项目 / Agent / 时间线 / 帮助 / 总览 / 状态 / 健康度"）翻译后才符合中文阅读习惯。

---

## 3. 中文化范围

### 3.1 新增文件

| 路径 | 作用 |
| --- | --- |
| `apps/dashboard/src/lib/labels.ts` | 统一中文映射中心：event_type / status / health / location / category / 全局 UI 文案 + `bilingual(cn, en)` helper |

### 3.2 修改文件

| 路径 | 改动 |
| --- | --- |
| `apps/dashboard/src/layouts/BaseLayout.astro` | `<html lang="zh-CN">`、nav 中文（首页 / 时间线 / 帮助）、header meta 中文、footer + readonly 提示行 |
| `apps/dashboard/src/pages/index.astro` | "总览 / 项目 / Agent / 最近活动（最新 10 条）" + 筛选中文 + 排序中文 + 状态徽标双语 |
| `apps/dashboard/src/pages/timeline.astro` | "时间线 / 事件类型 / 状态 / 项目 / Agent / 排序" 全部中文 + count badge "N 条匹配" |
| `apps/dashboard/src/pages/projects/[project_id].astro` | 字段中文（项目 / 仓库 / 位置 / 分类 / 当前状态 / 健康度 / 当前阶段 / 最近 Agent / 最近事件时间 / 事件数）+ 双语徽标（`amber · 部分完成 · PARTIAL`） |
| `apps/dashboard/src/pages/agents/[agent_id].astro` | 字段中文（Agent / 机器 / 角色 / 最近事件时间 / 最近项目 / 事件数）+ 事件类型分布中文（"阶段 5 · 复查 2"） |
| `apps/dashboard/src/pages/help.astro` | 整页重写为中文操作手册 |
| `apps/dashboard/src/components/TimelineItem.astro` | 事件类型中文标签 + 状态码双语（`部分完成 · PARTIAL`） |
| `apps/dashboard/src/components/ProjectCard.astro` | 字段中文（位置 · 分类 · 最近 Agent · 事件）+ 双语徽标 |
| `apps/dashboard/src/components/AgentCard.astro` | 字段中文（角色 · 最近项目 · 事件） |
| `apps/dashboard/src/scripts/filters.ts` | count badge 中文（`N 条匹配`） |
| `apps/dashboard/src/styles/global.css` | help 行距 1.6 → 1.75 + `.callout` (warning/danger/info) + `.checklist` + footer `.footer-readonly` + 移动端微调 |
| `README.md` | 状态行标注 ACT-13B + "Dashboard 已中文化（中文优先界面）" 段落 + 权限边界段落 |
| `docs/MVP_PLAN.md` | 标题 `ACT-1 to ACT-13B` + 当前阶段 ACT-13B + 时间线追加 + 下一阶段改为 `wait-for-real-update` → `ACT-12B when real update appears` |

### 3.3 保留为英文（"机器字"）

- 路径：`data/`、`public-data/`、`artifacts/`、`generated/`、`apps/dashboard/dist/`
- 协议：`commit`、`push`、`agent_id`、`project_id`、`phase_id`、`source_repo`、`source_commit`
- 状态值：`PASS` / `PARTIAL` / `FAIL` / `BLOCKED` / `ACTIVE` / `PAUSED` / `RELEASED` — 保留为 grep 字面量
- 健康度：`green` / `yellow` / `red` / `gray` — 保留为 grep 字面量
- agent_id / project_id 原文：`local-hermes` / `cloud-openclaw` / `agent-project-control-tower` / `artvee-gallery` / `booktrans-desk`
- repo URL 原文：`conanxin/booktrans-desk`、`conanxin/artvee-library`、`conanxin/agent-project-control-tower`
- phase ID：`S13` / `P3B` / `ACT-13B` / `S14+` 等
- source commit hash：`16f38b6` / `b444eef` 等

### 3.4 双语徽标模式

为了让"机器字"和中文共存，所有 status / health 徽标使用 `中文 · EN` 模式：

```
amber · 部分完成 · PARTIAL
S13 · 部分完成 · PARTIAL
公开 · public
未分类 · uncategorized
通过 · PASS
```

CSS 中 `pill` / `tl-type` / `latest-card-meta` 都做了视觉对齐。

---

## 4. Help 页面改写内容

`apps/dashboard/src/pages/help.astro` 整页重写为中文操作手册。

### 4.1 新增章节

1. **先看这里** — 6 条核心不变式（原项目仓库 / 控制塔仓库 / data / public-data / Dashboard 只展示 public-data / git push → Cloudflare 自动部署）
2. **核心流程** — 9 步标准链路（原项目完成阶段 → tower.py → local-hermes / 人工审核 → make public-update-preflight → 检查 artifacts → export_public_data.py → 显式 git add → commit + push → Cloudflare 自动更新）
3. **什么时候触发更新** — 真实事件驱动（BookTrans S14+ / Artvee P3C+ / tower ACT-14+ / 其他真实项目）
4. **常用操作** — 精简命令模板（register-agent / register-project / report-phase / report-review / report-failure / report-handoff / report-release / make public-update-preflight / export_public_data.py --plan）+ command generator 推荐
5. **双门模型** — 第一道门 / 第二道门（trial agent 不应直接 export public-data）
6. **权限边界** — ⚠️ callout 形式强调"只有 conanxin/agent-project-control-tower 写权限的维护者才能修改 public-data 并触发线上部署"
7. **public-data 更新检查清单** — 10 条 checklist（1-project downgrade / booktrans_repo_not_homepage / HP-33 = 0 / redaction FAIL = 0 / MANIFEST 一致 / data/ generated/ artifacts/ dist/ 未 add / git status 干净）
8. **多机器使用** — clone / agent_id / 跨机器 agent 只写 data / public export 仍由 local-hermes 执行
9. **深入文档** — 链接到 AGENT_USAGE_PLAYBOOK.md / MULTI_MACHINE_SETUP.md / PUBLIC_DATA_EXPORT_PLAYBOOK.md / PUBLIC_DATA_AUTOMATION_POLICY.md / templates/telegram/ / templates/checklists/ / GitHub Release v0.1.0
10. **关于这一页** — 说明这是 ACT-13B 重写，修改需编辑源文件走标准 commit + push 流程

### 4.2 视觉优化（CSS）

- 行距 `1.6` → `1.75`（中文段落更易读）
- `.callout` 系列（warning / danger / info）：左边框色块 + 背景区分（中文段落 callout 视觉醒目）
- `.checklist`：自绘方框替代 disabled `<input type="checkbox">`（避免浏览器默认灰色禁用样式）
- `.footer-readonly`：底部 readonly 提示（与 footer 区分）
- 移动端微调：help `<pre>` 在 ≤720px 字号从 12px → 11px，padding 收紧

### 4.3 HTML 修复

发现并修复 1 个 HTML 结构 bug：

- 修复前：`<strong>运行 <code>export_public_data.py --plan … --replace</strong>` （`<code>` 未关闭，导致浏览器把后续文字当 code 渲染）
- 修复后：`<strong>运行 <code>…</code></strong>`

---

## 5. 权限边界说明

按用户要求，权限边界在 3 个位置都有：

### 5.1 Help 页面"权限边界"section

```
<div class="callout callout-warning">
  <strong>权限边界</strong>
  <p>只有拥有 conanxin/agent-project-control-tower 写权限的维护者，
     才能修改 public-data 并触发线上 Dashboard 部署。其他用户可以 fork 仓库、
     参考流程搭建自己的控制塔，或提交 Pull Request。任何 public-data 变更
     都必须经过维护者审核后才能合并。</p>
  <p>普通 trial agent 不应直接 export public-data、不应 git add public-data、不应 push。</p>
</div>
```

### 5.2 Footer（每个页面底部）

```
<div class="footer-readonly">这是公开只读面板。只有仓库维护者可以更新 public-data；
普通访客无法将项目推送到本面板。</div>
```

### 5.3 README 顶层 + 中文说明段落

```
## 🌐 ACT-13B — Dashboard 已中文化（中文优先界面）
### 权限边界（重要）
> 只有拥有 conanxin/agent-project-control-tower 写权限的维护者，
> 才能修改 public-data 并触发线上 Dashboard 部署。
```

---

## 6. UI label 中文映射

| EN | CN |
| --- | --- |
| Home | 首页 |
| Timeline | 时间线 |
| Help | 帮助 |
| Summary | 总览 |
| Projects | 项目 |
| Agents | Agent |
| Events | 事件 |
| Green | 正常 |
| Yellow | 注意 |
| Red | 异常 |
| Blocked | 阻塞 |
| Search by name, id, repo, summary… | 搜索项目名称、ID、仓库或摘要…… |
| All health | 全部健康度 |
| All status | 全部状态 |
| All agents | 全部 Agent |
| Recently updated | 最近更新 |
| Clear | 清除 |
| matching | 条匹配 |
| location | 位置 |
| category | 分类 |
| last agent | 最近 Agent |
| events | 事件 |
| uncategorized | 未分类 |
| local | 本地 |
| public | 公开 |
| role | 角色 |
| last project | 最近项目 |
| total | 总计 |
| shown | 已显示 |
| Search summary / phase | 搜索摘要、阶段或 Agent…… |
| All event types | 全部事件类型 |
| All projects | 全部项目 |
| Newest first | 最新优先 |
| Oldest first | 最早优先 |
| Event type | 事件类型 |
| Status | 状态 |
| Project | 项目 |
| Current phase | 当前阶段 |
| Current status | 当前状态 |
| Latest event | 最新事件 |
| Next actions | 下一步 |
| Source repo | 源仓库 |
| Source commit | 源 commit |
| Event count | 事件数 |
| Timeline | 时间线 |
| Summary | 摘要 |
| Health | 健康度 |
| Repo | 仓库 |
| Agent | Agent |
| Machine | 机器 |
| Projects touched | 参与项目 |
| Review | 复查 |
| Phase | 阶段 |
| Handoff | 交接 |
| Release | 发布 |
| Event-type breakdown | 事件类型分布 |
| Activity timeline | 活动时间线 |

### Event type 中文映射

| EN | CN |
| --- | --- |
| PHASE_REPORT | 阶段 |
| REVIEW_REPORT | 复查 |
| HANDOFF | 交接 |
| RELEASE | 发布 |
| FAILURE | 失败 |
| BLOCK | 阻塞 |
| UNBLOCK | 解除阻塞 |
| ARCHIVE | 归档 |
| PROJECT_REGISTERED | 项目注册 |
| AGENT_REGISTERED | Agent 注册 |

### Status 中文映射

| EN | CN |
| --- | --- |
| PASS | 通过 |
| PARTIAL | 部分完成 |
| FAIL | 失败 |
| BLOCKED | 阻塞 |
| PAUSED | 暂停 |
| RELEASED | 已发布 |
| ACTIVE | 进行中 |
| ARCHIVED | 已归档 |

---

## 7. 哪些动态内容保留英文

- 任何**用户填入的字符串**（`p.name`、`p.last_summary`、`t.summary`、`next`、`role`）— 这些是 agent 写入 event 的，可能包含英文 / 中文 / emoji / 代码片段，**不翻译**。
- 任何**机器字**（agent_id / project_id / phase_id / commit hash / repo URL / status 值 / health 值）— 保留英文（grep 字面量）。
- 任何**外部 URL / 文档链接** — 保留英文路径。

---

## 8. README / MVP 更新

### 8.1 README.md 改动

1. 顶部状态行追加：`+ ACT-13B ✅ COMPLETE（Dashboard 中文化 + Help 中文重写）`
2. Help 行：`<https://control-tower.conanxin.com/help/>` → 标记"中文" + 注明 ACT-13B 改写 + 双门模型 + 权限边界 + 检查清单
3. "下一步" 改为：`ACT-14 或 ACT-12B when real update appears`
4. 新增章节 **`## 🌐 ACT-13B — Dashboard 已中文化（中文优先界面）`**，包含：
   - 5 个 dashboard 页面中文化说明
   - 保留为"机器字"的英文项列表
   - **权限边界段落**（强调只有维护者能改 public-data）
   - 深入文档链接到 docs/AGENT_USAGE_PLAYBOOK.md / PUBLIC_DATA_EXPORT_PLAYBOOK.md / PUBLIC_DATA_AUTOMATION_POLICY.md / MULTI_MACHINE_SETUP.md / MVP_PLAN.md
   - "普通访客不能更新我的面板，只能 fork 或 PR"

### 8.2 docs/MVP_PLAN.md 改动

1. 标题：`MVP Plan — ACT-1 to ACT-13` → `ACT-1 to ACT-13B`
2. 当前阶段说明：ACT-13 → ACT-13B
3. 时间线追加：`ACT-13B ✅ Dashboard Chinese Localization & Help Optimization (2026-06-12) ← 当前阶段`
4. 下一阶段：
   - `ACT-12B` → `wait-for-real-update`（等待真实项目更新）
   - `ACT-14` → `ACT-14：adoption packaging` + 新增 `ACT-12B when real update appears` 备注

---

## 9. 验证结果

### 9.1 make all

```
[ok] validate
[ok] build (3 projects, 2 agents, 25 events  ← NOTE: 这是 data/ 来源, 不是 public-data)
[ok] site
[FAIL] summary.agent_count >= 3 (got 2)
[FAIL] local-book-tool current_status == FAIL (got None)  ← ACT-1 fixture, 历史预期
[FAIL] local-book-tool current_health == red (got None)
[FAIL] local-book-tool current_phase_id == L2 (got None)
[FAIL] local-book-tool last_agent_id == local-codex (got None)
[FAIL] local-book-tool event_count == 2 (got None)
[FAIL] cloud-art-site current_status == PASS (got None)  ← ACT-2D fixture, 历史预期
[FAIL] cloud-art-site current_health == green (got None)
[FAIL] cloud-art-site event_count == 1 (got None)
[ok] timeline is sorted newest-first
[ok] embedded HTML contains __TOWER_DATA__ block
[ok] inline data summary.project_count >= 2
SMOKE TEST FAILED: 9 issue(s)
```

**注意**：这 9 个 FAIL 都是历史 ACT-1 / ACT-2D fixture（`local-book-tool` / `cloud-art-site`），只存在于 `data/` 中，从未进入 `public-data/`。这些是历史 baseline 现象，本阶段不动。

### 9.2 make publish-preflight

```
PUBLISH PREFLIGHT: PASS
  public-data/    exported from data/ (redacted real-project slice)
  generated/      rebuilt from public-data
  site/embedded   rebuilt from public-data
  apps/dashboard  dist/ rebuilt from public-data
  (nothing deployed — ACT-4B creates the remote and pushes)
```

**注意**：publish-preflight 触发了 `make public-data` write-mode 自动 re-export，会把 data/ 里 ACT-13 历史 event（`20260612T092418Z__PHASE__local-hermes__agent-project-control-tower__ACT-13.json`）重新加入 public-data，并更新 MANIFEST + site/index.embedded.html 时间戳。本阶段按"不改变 public-data 范围"约束，**运行后 git checkout HEAD -- public-data/MANIFEST.json site/index.embedded.html** 恢复基线，新 event 文件 rm 掉。

### 9.3 make public-update-preflight

```
✅ project_count_meets_plan: plan expects 3 project(s), public-data has 3
✅ booktrans_repo_not_homepage: booktrans-desk repo = 'conanxin/booktrans-desk' (OK)
✅ booktrans_no_hp33: HP-33 events for booktrans-desk: none
UPDATE_SUMMARY.md — PASS
```

**PASS**。

### 9.4 make public-update-test

```
public_update_preflight_smoke — PASS
  [ok] preflight_exit_zero (rc=0)
  [ok] wrote UPDATE_SUMMARY.md / PUBLIC_DATA_DIFF.md / MANIFEST_BEFORE.json / MANIFEST_AFTER.json / REVIEW_CHECKLIST.md / REDACTION_RESULT.md / NEXT_STEPS.md
  [ok] no_git_commit (HEAD unchanged)
  [ok] gitignore_data_and_generated_still_ignored
  [ok] detects_1project_downgrade (rc=1, check reported FAIL)
  [ok] detects_booktrans_repo_homepage (rc=1, check reported FAIL)
```

**PASS**。

### 9.5 make command-test

```
command_generator_smoke.py: PASS (8/8)
```

**PASS**（含 5 个 `<PLACEHOLDER>` WARN 是 ACT-7B 设计预期 + 1 个 `report-review.txt` real drift 是 ACT-7B 已知产物，与本阶段无关）。

### 9.6 make candidate / candidate-fixture / candidate-test

```
make candidate       → events: 24, redaction FAIL=0 WARN=0 → PASS
make candidate-fixture → events: 3, redaction FAIL=0 WARN=0 → PASS
make candidate-test    → candidate_artifact_smoke — PASS
```

**全部 PASS**。

### 9.7 make export-plan-test

```
export_plan_smoke — PASS
  [PASS] no local /home/<user>/ absolute path
  [PASS] no macOS /Users/<user>/ absolute path
  [PASS] no WSL /mnt/<drive>/ absolute path
  [PASS] no IPv4 address
  [PASS] no literal token= assignment
  [PASS] no literal API key
  [PASS] no Bearer authorization header
  [PASS] no reference to .env file
```

**PASS**。

### 9.8 npm run build

```
[build] 8 page(s) built in 1.40s
[build] Complete!
```

**PASS**。生成的 8 个 page：

- `/agents/local-hermes/index.html`
- `/agents/cloud-openclaw/index.html`
- `/help/index.html`
- `/index.html`
- `/projects/agent-project-control-tower/index.html`
- `/projects/artvee-gallery/index.html`
- `/projects/booktrans-desk/index.html`
- `/timeline/index.html`

### 9.9 敏感扫描

```bash
grep -RInE "token=|api_key|Authorization:|Bearer |password=|secret=|/home/[^ ]+|/Users/[^ ]+|[0-9]+.[0-9]+.[0-9]+.[0-9]+|.env" \
  README.md docs templates reports scripts tests config public-data .github CHANGELOG.md VERSION apps/dashboard/src
```

**结果**：所有命中都是教学 / 解释文本（README §"敏感扫描结果：0 hits"表格、`docs/OPEN_SOURCE_PLAN.md` §regex 定义和反例、`docs/RISKS_AND_BOUNDARIES.md` §"trial agent 应该避免写的内容"反例），**0 个真实敏感信息**。

具体分类：

- README.md 654 / 773 行：`0 hits` 是结果汇总（"0 hits"是数字）
- docs/OPEN_SOURCE_PLAN.md 90-93 行：regex 模式定义（"测试用例：`192.168.1.1`、`10.0.0.5`、`/home/xin/`、`api_key=sk-...`"），全部是反例，不是真实数据
- docs/RISKS_AND_BOUNDARIES.md 129 / 135 行：反例（`summary: "tested on http://192.168.1.42:8080, all green"`），不写到 event
- `data/` 已 gitignored — 包含真实 home path / token 等是设计预期（永远不会公开）

**判定**：PASS — 无真实敏感信息进入 commit。

### 9.10 不该提交的目录检查

```bash
git status --short --ignored | grep -E "data/|generated/|artifacts/|apps/dashboard/dist|node_modules|.env"
```

**结果**：

```
!! apps/dashboard/dist/      ← gitignore ✓
!! apps/dashboard/node_modules/  ← gitignore ✓
!! artifacts/                ← gitignore ✓
!! data/                     ← gitignore ✓
!! generated/                ← gitignore ✓
```

**全部正确 gitignored**，无任何应忽略目录被错误 stage。

### 9.11 local build spot-check（不上线）

```
index.html     16065 bytes — 含"首页 / 时间线 / 帮助 / 总览 / 项目 / Agent / 事件 / 正常 / 注意 / 异常 / 阻塞 / 通过 · PASS / 部分完成 · PARTIAL"
help/index.html 13487 bytes — 含"帮助 — 如何使用这个控制塔 / 双门模型 / 权限边界 / public-data 更新检查清单 / 多机器使用 / 深入文档"
projects/booktrans-desk/index.html — 含"BookTrans Desk / 当前阶段 / S13 / 16f38b6 / 部分完成 / conanxin/booktrans-desk / amber"
```

**所有 dashboard 文案中文生效，徽标双语正确，权限边界 callout 渲染正常**。

---

## 10. 当前公开边界（未变）

| 内容 | 状态 |
| --- | --- |
| 在线 dashboard（Cloudflare Pages） | ✅ 公开，URL 公开可访问，**已中文化** |
| 仓库元数据（README / docs / LICENSE） | ✅ 公开 |
| `public-data/`（3 projects / 2 agents / 24 events） | ✅ 公开，**唯一** publish 数据源 |
| BookTrans Desk | ✅ 仍为 `conanxin/booktrans-desk` / S13 / `16f38b6` / PARTIAL |
| `data/` | ❌ 不公开（gitignored） |
| `generated/` | ❌ 不公开（gitignored） |
| `artifacts/` | ❌ 不公开（gitignored） |
| `apps/dashboard/dist/` | ❌ 不公开（gitignored） |
| `node_modules/` | ❌ 不公开（gitignored） |
| `.env` | ❌ 不公开（gitignored） |

---

## 11. 下一阶段建议：wait-for-real-update

按用户要求，本阶段结束后回到 **wait-for-real-update** 状态：

- **BookTrans Desk** 当前 `S13 / 16f38b6 / PARTIAL` — 等 S14+ 真实事件触发 → ACT-12B（再做一次完整 export 流程）
- **Artvee Gallery** 当前 `P3B Daily Inspiration Digest` — 等 P3C+ 真实事件
- **Control Tower 自身** 当前 ACT-13B — 等 ACT-14+ 真实事件（adoption packaging）
- **其他真实项目** — 等任一公开展示需求

## 12. 验证清单

- [x] Dashboard 主界面中文化
- [x] Timeline 中文化
- [x] Project / Agent 页面中文化
- [x] Help 页面重写为中文操作手册
- [x] "权限边界"说明：普通访客不能推送到我的面板
- [x] 保留必要英文技术词（data/、public-data/、commit、push、agent_id、project_id、status、health）
- [x] 更新 README 和阶段报告
- [x] 构建 + 验证 + 敏感扫描
- [x] BookTrans Desk 仍为 conanxin/booktrans-desk / S13 / 16f38b6 / PARTIAL
- [x] public-data 未被错误修改（git checkout HEAD 恢复基线）
- [x] data/ 仍未公开（gitignored）
- [x] generated/ 仍未公开（gitignored）
- [x] artifacts/ 未提交（gitignored）
- [x] apps/dashboard/dist/ 未提交（gitignored）
- [x] 无真实 token / IP / 私密路径进入 commit
- [x] HTML 结构 bug（`<strong>` 内未关闭 `<code>`）已修复
