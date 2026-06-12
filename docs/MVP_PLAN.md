# MVP Plan — ACT-1 to ACT-10B

> 把"建一个能用的控制塔"拆成阶段。每个阶段都有明确产出 + 验收标准 + 退出条件。
>
> 当前在 **ACT-10B ✅ COMPLETE**。ACT-10B 是纯 polish：用 Playwright + Chromium 1.5× DPI 实时截了 6 张 v0.1.0 screenshot（dashboard home 桌面+移动、timeline、agent-project-control-tower 页、booktrans-desk 页、cloud-openclaw agent 页），全部 commit 进 `docs/media/v0.1.0/`、upload 到 GitHub Release v0.1.0、嵌入 README；同时把 release notes 从 22 events 更新到 24 events / 加 BookTrans Desk S13 PARTIAL note / 加 ACT-11+12 public-data update workflow 说明。**没有改任何控制塔数据 / 功能 / 边界**。当前公开数据状态：3 real projects / 2 agents / 24 events。当前自动化等级：**Level 1 + Level 1.5 + Level 2 + Level 3 (prototype)**，Level 4/5 仍被拒绝。
> 下一阶段（按推荐度排序）：
> 1. **ACT-12B：second recurring update trial**——再跑一次真实多日更新，验证 ACT-11/12 ergonomic 在多天节奏下稳定。
> 2. **ACT-13：adoption packaging**——为新 agent / 新人类首次 clone 这个仓库准备更顺手的入口。

## 全景时间线

```
ACT-0  ✅ 设计与架构        (2026-06-11, commit adcd937)
  ↓
ACT-1  ✅ 本地数据流原型     (2026-06-11, commit eb08bee)
  ↓
ACT-2  ✅ Tower CLI         (2026-06-11, commit 0bfbb70)
  ↓
ACT-3A ✅ Dashboard shell    (2026-06-11, commit a0d37d4)
  ↓
ACT-3B ✅ Dashboard UX polish (2026-06-11)
  ↓
ACT-4A ✅ CI/CD & publish readiness (2026-06-11)
  ↓
ACT-4B ✅ GitHub push (2026-06-11)
  ↓
ACT-5  ✅ Cloudflare Pages online verification (2026-06-11)
  ↓
ACT-5B ✅ Custom domain bind (2026-06-11)
  ↓
ACT-6  ✅ First real project public export    (2026-06-11)
  ↓
ACT-6B ✅ Second real project — Artvee Gallery (2026-06-11)
  ↓
ACT-6C ✅ Third real project — BookTrans Desk  (2026-06-11) + ACT-6C hotfix
ACT-7   ✅ Multi-machine Agent Usage Playbook (2026-06-12)
ACT-8   ✅ Real Multi-agent Onboarding Trial (2026-06-12)
ACT-7B  ✅ Template-to-Command Generator (2026-06-12)
ACT-8B  ✅ Generated-command Multi-agent Trial (2026-06-12)
ACT-9   ✅ Public-data Export Automation Policy (2026-06-12)
ACT-9B  ✅ CI Proposed Export Artifact Prototype (2026-06-12)
ACT-9C  ✅ Export Plan Review Workflow (2026-06-12)
ACT-10 ✅ v0.1.0 Release Packaging (2026-06-12)
ACT-11 ✅ Public-data Update Ergonomics (2026-06-12)
ACT-12 ✅ Recurring Public-data Update Trial (2026-06-12)
ACT-10B ✅ v0.1.0 Release Polish (2026-06-12) ← 当前阶段
```

每个 ACT 的预算：**1–2 周业余时间**，不超过 30 个 commit。

---

## ACT-1 — Hand-rolled Data + Manual Index

> **目标**：证明"Git + JSON + 静态生成"这个最小循环能跑。

### 状态：✅ COMPLETE (2026-06-11)

### 范围

- [x] 完成 `examples/projects.yml`、`examples/agents.yml`（2 个项目 / 3 个 agent）
- [x] 完成 3 个示例 event JSON（覆盖 PASS / FAIL / 跨 agent 场景）
- [x] **写一个零依赖的 YAML 解析器**（`scripts/lib/yaml_mini.py`）—— 不引入 PyYAML
- [x] `scripts/validate_examples.py` 校验 registry + events（schema / enum / cross-ref）
- [x] `scripts/build_index.py` 读 registry + events → 写 `generated/index.json`
- [x] `scripts/build_embedded_site.py` 把 index.json 内嵌到 `site/index.embedded.html`
- [x] `site/index.html` 提供 fetch 版本（HTTP server 下用）+ embedded fallback
- [x] `tests/smoke.py` 验收 14 项检查（counts、health 派生、timeline 顺序、内嵌数据）
- [x] `Makefile` 提供 `validate / build / site / test / all / clean` 6 个 target

### 不在范围（保持 ACT-1 极简）

- ❌ 不写任何前端框架
- ❌ 不引入 Astro / npm / Tailwind
- ❌ 不接 GitHub Actions
- ❌ 不接真实项目
- ❌ 不写 `tower` CLI
- ❌ 不做暗色主题、动画、view transitions
- ❌ 不做项目详情页 / agent 详情页（只有首页）

### 实际验收（由 `tests/smoke.py` 强制执行）

```
[ok] summary.project_count == 2
[ok] summary.agent_count == 3
[ok] summary.event_count == 3
[ok] local-book-tool current_status == FAIL
[ok] local-book-tool current_health == red
[ok] local-book-tool current_phase_id == L2
[ok] local-book-tool last_agent_id == local-codex
[ok] local-book-tool event_count == 2
[ok] cloud-art-site current_status == PASS
[ok] cloud-art-site current_health == green
[ok] cloud-art-site event_count == 1
[ok] timeline is sorted newest-first
[ok] embedded HTML contains __TOWER_DATA__ block
[ok] inline data summary.project_count == 2

SMOKE TEST PASSED
```

### 退出条件（已达成）

> ✅ "我对自己说：dashboard 长这样就够了，剩下就是把数据生成自动化。"
>
> 实际上手写 dashboard 在 ACT-1 没做——直接就是脚本 build 的；但 ACT-1 证明了"build 出来的数据 + 静态 HTML = 可双击的 dashboard"是成立的。

### 留给 ACT-2 的桥

- 现在的 event 是手写 JSON——ACT-2 把手写变成 `tower report phase`
- 现在的 YAML 解析是自家的——ACT-2 可以替换为 PyYAML（如果 ACT-3 起引入更多 YAML 字段）
- 现在的 `generated/index.json` 是平铺的——ACT-3 起如果要做项目详情页，可能要补 `generated/projects/<id>.json`

---

## ACT-2 — tower CLI (Python)

> **目标**：把 ACT-1 里的"手写"自动化，让 agent 能用 CLI 写 event。

### 状态：✅ COMPLETE (2026-06-11)

### 范围（最终）

- [x] **`scripts/tower.py`** — 统一 CLI，10 个子命令（`validate / build / seed / register-agent / register-project / report-phase / report-failure / report-review / report-handoff / report-release`）
- [x] **`scripts/lib/redaction.py`** — 隐私校验（轻量规则：FAIL 拒写 / WARN 写但告警 / PASS 静默）
- [x] **`scripts/lib/yaml_mini.py`** — 零依赖 YAML（ACT-1 已有）
- [x] **`scripts/validate.py`** — `--source {data,examples,both}`（替换 ACT-1 的 `validate_examples.py`，后者变成 thin wrapper）
- [x] **`scripts/build_index.py`** — `--source` flag，默认 `data`，可被 `TOWER_ROOT` env 覆盖
- [x] **`scripts/build_embedded_site.py`** — `--index` / `--template` / `--output` 三 flag
- [x] **`data/registry/{projects,agents}.yml`** + **`data/events/*.json`** — 新运行时数据目录（`.gitignore`）
- [x] **`examples/registry/`** — 同期迁移 ACT-0 的 examples 至此对称结构
- [x] **`tests/cli_smoke.py`** — 39 项 CLI smoke（在临时目录跑，不污染真实 data/）
- [x] **`Makefile`** — `seed / validate / build / site / test / test-cli / reset / all / clean` 9 个 target

### 不在范围（保持 ACT-2 极简）

- ❌ **不**用 Click / Typer / argparse-subcommands 之外的 CLI 库——用 stdlib `argparse`
- ❌ **不**用 Pydantic / dataclasses 之外的数据模型——用 stdlib dict + 手动校验
- ❌ **不**实现 `block` / `unblock` / `archive` 子命令（ACT-3 补）
- ❌ **不**写 `git add` / `git commit` / `git push` 集成（刻意不做，详见 [AGENT_WORKFLOW.md §2.5](AGENT_WORKFLOW.md)）
- ❌ **不**做 GitHub Actions
- ❌ **不**接真实部署
- ❌ **不**做 dashboard 静态站优化
- ❌ **不**支持多控制塔仓库自动发现（`TOWER_ROOT` env var 就够）

### 实际验收（由 `tests/cli_smoke.py` 强制执行 + `make all` 一键跑通）

```
[ok]  validate clean state
[ok]  build clean state
[ok]  generated/index.json exists after build
[ok]  summary.project_count == 2
[ok]  register-agent smoke-1
[ok]  register-agent smoke-1 idempotent (no error)
[ok]  register-agent smoke-1 reports 'already exists'
[ok]  register-project smoke-proj
[ok]  register-project smoke-proj idempotent
[ok]  report-phase PASS
[ok]  report-failure (status=FAIL, health=red)
[ok]  FAILURE event file exists (1 found)
[ok]  FAILURE event status == FAIL
[ok]  FAILURE event health == red
[ok]  FAILURE event has failure_reason
[ok]  report-review
[ok]  REVIEW event_type == REVIEW_REPORT
[ok]  REVIEW event has review_target {agent_id, phase_id}
[ok]  report-handoff
[ok]  HANDOFF event_type == HANDOFF
[ok]  HANDOFF event has to_agent_id == smoke-2
[ok]  report-release
[ok]  RELEASE event status == RELEASED
[ok]  RELEASE event health == green
[ok]  RELEASE event has release.version == v0.0.1
[ok]  redaction FAIL returns exit 3 (got 3)
[ok]  redaction FAIL did NOT write event file
[ok]  redaction WARN still writes (exit 0)
[ok]  redaction WARN event file exists
[ok]  final build
[ok]  site/index.embedded.html exists
[ok]  embedded HTML contains __TOWER_DATA__
[ok]  inline data has 3+ projects (got 3)
[ok]  timeline has AGENT_REGISTERED
[ok]  timeline has PROJECT_REGISTERED
[ok]  timeline has PHASE_REPORT
[ok]  timeline has REVIEW_REPORT
[ok]  timeline has HANDOFF
[ok]  timeline has RELEASE

CLI SMOKE TEST PASSED
```

加上 ACT-1 14 项 = **总 53 项验收全过**。

### 退出条件（已达成）

> "从现在起，每个新阶段都用 tower CLI 上报，再也不手写 JSON。"

### 留给 ACT-3 的桥

- ACT-1/2 的 `site/index.html` + `site/index.embedded.html` 是**纯静态**（vanilla JS）——ACT-3 引入 Astro 时，先用现有 2 文件作为"reference"再设计组件
- `generated/index.json` schema 是 ACT-2 收敛的 `0.2` 版本——ACT-3 起所有 page 都消费这个 JSON
- 缺 `block` / `unblock` / `archive` 3 个 CLI 子命令——ACT-3 补
- `redaction` 是轻量规则——ACT-3 之前如果发现误报/漏报，**先**加测试再修规则



---

## ACT-3 — Static Dashboard (Astro)

> **目标**：把 ACT-1 的手写 HTML 替换成 Astro 项目，CI 之前能本地预览。

### 拆解

- [x] **ACT-3A**（已完成）— Dashboard shell：4 个 page + 1 个 layout + 4 个组件 + 暗色 CSS；npm install + npm run build PASS；不替代 ACT-1/2 的 embedded.html
- [x] **ACT-3B**（已完成）— UX polish：search / filter / sort / 主题切换 / view transitions / 移动端 / 数据健壮性
- [ ] **ACT-3C**（可选）— 性能 / accessibility 增强（不在当前 roadmap）

> 详细 ACT-3A 报告：[PHASE_ACT3A_ASTRO_DASHBOARD_SHELL_REPORT.md](../reports/PHASE_ACT3A_ASTRO_DASHBOARD_SHELL_REPORT.md)
> 详细 ACT-3B 报告：[PHASE_ACT3B_DASHBOARD_UX_POLISH_REPORT.md](../reports/PHASE_ACT3B_DASHBOARD_UX_POLISH_REPORT.md)

### 范围（ACT-3A 最终交付）

- [x] `apps/dashboard/` 初始化 Astro 5 项目（**仅 Astro，无 Tailwind / React**）
- [x] `apps/dashboard/src/pages/index.astro` — 首页
- [x] `apps/dashboard/src/pages/projects/[project_id].astro` — 项目详情
- [x] `apps/dashboard/src/pages/agents/[agent_id].astro` — agent 详情
- [x] `apps/dashboard/src/pages/timeline.astro` — 全局时间线
- [x] `apps/dashboard/src/lib/tower-data.ts` — 从 `../../../../generated/index.json` 读
- [x] 5 个组件（BaseLayout + StatCard + ProjectCard + AgentCard + TimelineItem）
- [x] 极简 CSS（暗色 + 纯 CSS variables，无框架）
- [x] 保留 `site/index.html` + `site/index.embedded.html`（ACT-1/2 零依赖版不动）
- [x] `make dashboard` target，**不**进 `make all`

### 不做（ACT-3A 故意不解决）

- ❌ 不做 search / filter / sort（前端的 JS 交互）
- ❌ 不做暗色主题切换（MVP 只一种暗色，亮色后续）
- ❌ 不做 view transitions / 动画
- ❌ 不做 about / RSS / sitemap
- ❌ 不做部署
- ❌ 不做 GitHub Actions
- ❌ 不做登录

### 验收（ACT-3A 实际跑过）

- ✅ `cd apps/dashboard && npm install` → 277 packages OK
- ✅ `cd apps/dashboard && npm run build` → 8 page(s) built in 1.01s
- ✅ `make dashboard` target OK
- ✅ `make all`（零依赖路径） 53/53 仍 PASS
- ✅ dist/ 包含 8 HTML + 1 CSS，~88 KB
- ✅ 首页显示 3 projects / 3 agents / 7 events（与 ACT-2D 后 `generated/index.json` 一致）
- ✅ 项目详情页 / agent 详情页 / timeline 页正确数据
- ✅ 无运行时 API、无 SSR、无外部 fetch

### 退出条件（已达成）

> "dashboard 在视觉/路由/可部署性上"完整。

### 留给 ACT-4 的桥

- `apps/dashboard/dist/` 已经是 100% 静态文件——可以**直接**让 GitHub Actions 上传成 Pages artifact
- `make dashboard` 已在本地验证 build PASS——CI 同样调用
- 当前所有 data 来自 `data/`——未来 ACT-4 加"CI 跑 tower.py validate + build"是 1 个 step
- 零依赖 `site/index.embedded.html` 仍可作为**第二个** artifact（双 dashboard 并行发布）
- ACT-3B 已加 view transitions + 主题切换 + 搜索/筛选——CI 发布后用户体验已就位

---

## ACT-4A — CI/CD & Publish Readiness (本地准备)

> **目标**：在 push GitHub 之前，把 CI workflow、public-data 出口、文档全部就位。本阶段**不**创建远程仓库、**不** push。
>
> **状态**：✅ COMPLETE。

### 范围

- [x] `public-data/` 新建：被公开 dashboard 读取的脱敏数据快照（tracked）
- [x] `scripts/export_public_data.py`：从 `examples/` 或 `data/` 导出到 `public-data/`，自动 redaction，FAIL 直接拒绝
- [x] `scripts/{build_index,validate,tower}.py` 增加 `--source public-data`
- [x] `Makefile` 增加 `public-data` / `public-build` / `site-only` / `publish-preflight`
- [x] `.github/workflows/ci.yml`：3 jobs（zero-dep acceptance / astro dashboard / publish preflight）
- [x] 5 篇文档更新（README / DEPLOYMENT_PLAN / OPEN_SOURCE_PLAN / MVP_PLAN / AGENT_WORKFLOW）
- [x] `reports/PHASE_ACT4A_CICD_PUBLISH_READINESS_REPORT.md`

### 数据职责划分（ACT-4A 落定）

| 目录 | 角色 | 是否 tracked |
| --- | --- | --- |
| `data/` | 本地真实控制塔数据 | ❌ gitignored |
| `examples/` | 脱敏示例数据 / seed | ✅ tracked |
| `public-data/` | 准备发布的脱敏快照 | ✅ tracked |
| `generated/` | 构建产物（index.json 等） | ❌ gitignored（CI 重生成） |
| `site/index.embedded.html` | 离线双击打开的快照 | ✅ tracked |
| `apps/dashboard/dist/` | Astro build 输出 | ❌ gitignored（CI 上传为 artifact） |

### 为什么不解开 data/ gitignore

ACT-4A 决定**保持 data/ gitignored**——详细分析见 `reports/PHASE_ACT4A_CICD_PUBLISH_READINESS_REPORT.md`。简言之：本地真实数据可能含私密路径、token、IP；公开路径必须经 `export_public_data.py` 强制 redaction。

### 不用（ACT-4A 故意不解决）

- ❌ **不**写 `.github/workflows/pages.yml`——部署在 ACT-4B 决策后再加，避免公开策略未确认就自动上线
- ❌ **不** push GitHub
- ❌ **不**创建远程仓库
- ❌ **不**引入 secrets / tokens
- ❌ **不**新增 UI 功能（dashboard 已经是 ACT-3B 终态）
- ❌ **不**重构 ACT-2 数据流

### 验收（实际跑过）

```
$ make all               # 53/53 PASS
$ make publish-preflight # PASS
$ npm run build          # 7 page(s) built in 1.21s (public data → dist)
$ pre-commit audit       # CLEAN
```

### 留给 ACT-4B 的桥

- CI workflow 已可工作——ACT-4B 只需要 (a) 选 GitHub Pages 或 Cloudflare Pages (b) 写 `pages.yml` (c) 配 `Settings > Pages` 或 Cloudflare 项目
- `public-data/` 数据齐全 (2 projects / 3 agents / 3 events from examples)，可立刻作为公开 dashboard 数据源
- `apps/dashboard/dist/` 已经能完整构建，部署只需上传
- 0 个 secrets、0 个 IP、0 个私密路径需要清理（pre-commit audit CLEAN）

---

## ACT-4B — GitHub Push + Cloudflare Pages Config (已就位)

> **目标**：创建 GitHub 远程仓库、push 全部 commit、确认 CI 运行、文档化 Cloudflare Pages 配置。**不**实际连接 Cloudflare、**不**自动 deploy。
>
> **状态**：✅ COMPLETE（2026-06-11, commit 见下）。

### 4 个决策点（已确认）

1. **Hosting** → **Cloudflare Pages**（CN-friendly + CDN + 免费）
2. **public-data/ 数据范围** → **先用 examples 导出 (2/3/3) 占位**，不公开真实 data/
3. **GitHub 仓库名** → **`agent-project-control-tower`**（用户原有名字）
4. **agent ID 命名** → **`local-hermes` / `local-codex` / `cloud-openclaw` 保留**（demo 数据可接受）

### 范围（已执行）

- [x] GitHub 远程仓库创建：`https://github.com/conanxin/agent-project-control-tower`（用 `gh repo create`）
- [x] `git push -u origin main`：7 个本地 commit 全部 push 成功
- [x] GitHub Actions CI 触发：run 27323347041
  - `zero-dep-acceptance` ✅ PASS（9s）
  - `astro-dashboard` ✅ PASS
  - `publish-preflight` ✅ PASS（修复 PyYAML 缺失后）
- [x] `docs/DEPLOYMENT_PLAN.md` §4 改写为 ACT-4B 决策的最终配置
- [x] `reports/PHASE_ACT4B_GITHUB_PUSH_AND_PUBLISH_PATH_REPORT.md` 写好

### ACT-4B 期间发现并修复的 bug

`export_public_data.py` 第 144 行 `import yaml` 在 CI runner（PyYAML 未装）**立即**抛 `ModuleNotFoundError`，**先于** try/except 保护。

修：先 try `yaml_mini`（已 sys.path.insert），fall back PyYAML，最后 fallback 报错。已在 venv（无 PyYAML）模拟 CI 环境验证。

### 不用

- ❌ **不**在 CLI 配 Cloudflare API token
- ❌ **不**写 `.github/workflows/pages.yml`（Cloudflare 走 Dashboard UI 即可）
- ❌ **不**绑自定义域（ACT-5 决策）
- ❌ **不**自动 deploy

### 验收

- [x] `make all` 53/53 PASS
- [x] `make publish-preflight` PASS
- [x] `npm run build` 7 pages PASS
- [x] pre-commit audit CLEAN
- [x] push 一个 `fd9879d`（7 commits），CI 自动触发且 3 jobs 全 PASS
- [x] ACT-4B 报告 commit 到 main 并 push

### 退出条件

> "GitHub 仓库已公开、CI 跑通、Cloudflare Pages 配置文档化，**待 ACT-5 手动连接**。"

---

## ACT-5 — Connect Cloudflare Pages and Verify Online Dashboard（已完成）

> **目标**：在 Cloudflare Dashboard 手动 Connect to Git，绑定 repo，完成首次部署 + 在线验收。
>
> **状态**：✅ COMPLETE（2026-06-11）。在线 URL: <https://agent-project-control-tower.pages.dev/>。
>
> **前置条件**（已就位）：
> - 仓库 `https://github.com/conanxin/agent-project-control-tower` 已 push ✅
> - CI 3 jobs 全 PASS ✅
> - `docs/DEPLOYMENT_PLAN.md` §4 写了 ACT-4B 决策的最终配置 ✅

### 实际 Cloudflare Pages 配置

| 字段 | 实际值 |
| --- | --- |
| Project name | `agent-project-control-tower` |
| Git repository | `conanxin/agent-project-control-tower` |
| Production branch | `main` |
| Root directory | `apps/dashboard` |
| Build command | `npm ci && npm run build` |
| Build output directory | `dist` |
| Environment variables | （无） |

### 范围（已执行）

- [x] Cloudflare Dashboard → Workers & Pages → Create application → Pages → Connect to Git
- [x] 选 repo `conanxin/agent-project-control-tower`
- [x] 配置：root=`apps/dashboard`, build=`npm ci && npm run build`, output=`dist`
- [x] Save & Deploy（首次 build ~30s）
- [x] 访问 `https://agent-project-control-tower.pages.dev/` 验收
- [x] 检查：summary cards / project list / agent list / timeline
- [x] 测试：搜索 / health 筛选 / 排序 / 主题切换 / 移动端
- [x] 隐私扫描：0 命中（无 home 路径 / 无 IP / 无 token / 无 smoke / 无 data/ 泄漏）
- [x] `tower.py report-phase ACT-5` 上报（PASS / health=green）
- [x] README + DEPLOYMENT_PLAN + MVP_PLAN 同步更新
- [x] 写 ACT-5 阶段报告

### 不用

- ❌ **不**绑自定义域（推到 ACT-5B）
- ❌ **不**升级 public-data 到真实 data 脱敏子集（推到 ACT-6）
- ❌ **不**做登录
- ❌ **不**做"私密项目隐藏"——所有展示都脱敏
- ❌ **不**做 CDN 缓存策略调优（默认即可）
- ❌ **不**用 Cloudflare API token（ACT-4B 决策 Dashboard UI 即可）

### 验收

- [x] 打开 `https://agent-project-control-tower.pages.dev/` 看到 2 projects + 3 agents + 3 events
- [x] 7/7 URL HTTP 200（home / timeline / 2× project detail / 3× agent detail）
- [x] `make all` 53/53 PASS
- [x] `make publish-preflight` PASS
- [x] `npm run build` 7 pages PASS
- [x] pre-commit audit CLEAN
- [x] 敏感模式扫描 0 命中

### 退出条件

> ✅ "我能把这个 URL 发给一个朋友，让他一眼看懂'这人在用 agent 跑开源项目'。"

实际验证：URL <https://agent-project-control-tower.pages.dev/> 公开可访问，summary 显示 2 projects / 3 agents / 3 events，任意访客无需登录即可看到全部状态。

### ACT-5 期间发现

- CF Pages 上 `apps/dashboard` 的 build 实际拿到了 `generated/index.json`（尽管该文件 gitignored）—— 证明 ACT-4A 的 `publish-preflight` 链在 deploy 期间有某种方式把 generated 复制到了 build 上下文（具体机制是 CF Pages build command 还是其他方式，**未在 ACT-5 范围内深究**）。记一笔到 ACT-6 排查

---

## ACT-5B — Custom Domain Bind（已完成）

> **目标**：把 `*.pages.dev` 默认子域绑到 `control-tower.conanxin.com`，并完成 7 URL 验收。
>
> **状态**：✅ COMPLETE（2026-06-11）。
> - **主入口**：<https://control-tower.conanxin.com/>
> - **备入口**：<https://agent-project-control-tower.pages.dev/>
> - 两个 URL 服务**同一份** dist。
>
> **前置条件**（已就位）：
> - ACT-5 ✅：Cloudflare Pages 已首次部署到 `*.pages.dev`
> - 父域 `conanxin.com` DNS 已在 Cloudflare 托管

### 实际配置

| 字段 | 值 |
| --- | --- |
| Domain | `control-tower.conanxin.com` |
| 父域 | `conanxin.com`（DNS 已在 Cloudflare 托管） |
| DNS record | `CNAME`（Cloudflare Pages 自动创建） |
| SSL/TLS | Cloudflare 自动签发（Universal SSL） |
| 状态 | Active |

### 范围（已执行）

- [x] Cloudflare Pages → `agent-project-control-tower` project → Custom domains
- [x] 输入 `control-tower.conanxin.com` → 父域 DNS 自动检测 → CNAME 自动创建
- [x] SSL/TLS 30s 内签发，状态显示 **Active**
- [x] **双 URL 同时服务同一份 dist**（custom domain + pages.dev fallback）
- [x] 7 URL 在线验收（curl -I -L + 内容 + SSR title + 关键内容验证）
- [x] 敏感模式扫描 0 命中
- [x] 验证 local-book-tool 详情页 L2 FAIL / cloud-art-site 详情页 C1 PASS
- [x] `tower.py report-phase ACT-5B` 上报（PASS / health=green）
- [x] README / DEPLOYMENT_PLAN / MVP_PLAN 同步更新
- [x] 写 ACT-5B 阶段报告

### 不用

- ❌ **不**在 CLI 配 Cloudflare API token（沿用 ACT-4B 决策）
- ❌ **不**配 pages.dev → custom domain 301 redirect（决策：保留 fallback，详见 DEPLOYMENT_PLAN §4.9）
- ❌ **不**改 `apps/dashboard/` 任何源码
- ❌ **不**改 public-data 策略（沿用 ACT-4A/5 "demo only" 边界）
- ❌ **不**启用 Web Analytics / HSTS（推到 ACT-5C 或更后）
- ❌ **不**接入真实 data/（推到 ACT-6）

### 验收

- [x] 7/7 URL HTTP 200（curl -I -L）
- [x] SSR title 全部正确（"Agent Project Control Tower" / "Local Book Tool — ..." / 等）
- [x] 首页显示 2 projects / 3 agents / 3 events
- [x] timeline 显示 3 events（2 PASS + 1 FAIL）
- [x] local-book-tool 详情页含 L2 FAIL summary（TypeError/DRM/EPUB crashes）
- [x] cloud-art-site 详情页含 C1 PASS summary（Static gallery/120 images/sitemap ready）
- [x] 3 个 agent 详情页可访问
- [x] 敏感模式扫描 0 命中
- [x] `make all` 53/53 PASS
- [x] `make publish-preflight` PASS
- [x] `npm run build` 7 pages PASS
- [x] pre-commit audit CLEAN

### 退出条件

> ✅ "我可以把这个 URL 印在名片 / 简历上。"

实际验证：<https://control-tower.conanxin.com/> 公开可访问，SSR title 正确，summary 显示 2 projects / 3 agents / 3 events。CF 自动 SSL 已生效，HSTS 可在 ACT-5C 决定是否启用。

### ACT-5B 期间发现

- custom domain 7 URL 的 `Content-Length` / `Date` 响应头与 pages.dev 7 URL **完全相同**（同 dist、同 CDN edge、同缓存），证明是**同一份** build 在两个 URL 上
- 父域 `conanxin.com` DNS 已在 Cloudflare 托管（来自用户的 conanxin-homepage 项目）→ custom domain 绑定**零配置**——CF Pages UI 输入子域后自动配 CNAME + 签 SSL，~30s 完成
- 不需要额外配 redirect 规则——访客用哪个 URL 都能进

---

## ACT-6 — First Real Project Public Export（**已完成**）

> **目标**：把公开 dashboard 从 demo 2/3/3 升级为**真实** 1/1/7——把控制塔自身作为第一个真实公开项目（dogfooding）。
>
> **状态**：✅ COMPLETE（2026-06-11）。
>
> **前置条件**（已就位）：
> - ACT-5B ✅：custom domain `control-tower.conanxin.com` 已绑定
> - public-data/ 是唯一 publish 数据源；data/ 仍 gitignored
> - `data/registry/projects.yml` 含 `agent-project-control-tower`，`data/events/` 含 7 个真实 event

### ACT-5B 总结 → ACT-6 接手

ACT-5B 完成了"对外可分享"的所有基础设施：
- 公开 dashboard 跑在 custom domain
- public-data/ 是唯一数据源（demo 2/3/3）
- 真实 data/ 仍未公开

**ACT-6 决策**：把控制塔自身作为第一个真实公开项目，而不是 5 个候选（artvee-gallery / booktrans-desk / etc.）中的某一个。理由：
- `agent-project-control-tower` 自身就是 ACT-0 ~ ACT-5B 全部阶段 event 的产生者（dogfooding）
- 真实 events 里没有 home 路径 / token / IP —— data/ 的 `local/<id>` placeholder 是**预先设计**的安全占位符
- 公开这个项目能直接告诉访客"这个 dashboard 是怎么诞生的"
- 5 个候选项目里大部分还不存在或没跑真实 phase（ACT-6 决策时），**强行公开会触发大量 redaction FAIL**——先把"控制塔自身"做透，ACT-6B 再接第二个

### 范围（已执行）

#### A. 构建链路 ACT-6 改进

- [x] `apps/dashboard/package.json` 加 `prebuild` 钩子：`npm run build` **自动**从 public-data 重写 `generated/index.json`
- [x] `prebuild` 钩子支持 `SKIP_DASHBOARD_PREBUILD=1` 留给 opt-in 调试
- [x] Makefile `dashboard` target 改为 PUBLIC 模式（不再 `dashboard: build` 依赖 data 版 generated）
- [x] Makefile 新增 `dashboard-local` target（opt-in 调试 data/ + `SKIP_DASHBOARD_PREBUILD=1`）
- [x] Makefile 新增 `public-data-real` target（data → public-data/ 脱敏切片）
- [x] Makefile `publish-preflight` 第一步改为 `public-data-real`（不是 `public-data`）

#### B. `scripts/export_public_data.py` ACT-6 扩展

- [x] 新增 `--project-id`（可重复）—— 只导出指定 project
- [x] 新增 `--agent-id`（可重复）—— 只导出指定 agent
- [x] 新增 `--max-events N`（默认 50）—— 每个 project 最多 N 个 event，newest first
- [x] 新增 `--replace` —— 清空 `public-data/{registry,events}` 再写
- [x] 新增 `--repo-prefix`（默认 `conanxin`）—— 把 `local/<id>` 改写为 `<prefix>/<id>`
- [x] 新增 `--output` 参数已存在（ACT-4A）—— 保持兼容
- [x] 新增 MANIFEST.json 写 `project_filter` / `agent_filter` / `max_events_per_project` / `repo_prefix` 字段

#### C. 导出第一个真实项目

- [x] 跑 `export_public_data.py --source data --output public-data --project-id agent-project-control-tower --agent-id local-hermes --max-events 20 --repo-prefix conanxin --replace`
- [x] redaction 0 FAIL / 0 WARN
- [x] public-data/ 1 project / 1 agent / 7 events
- [x] `repo: conanxin/agent-project-control-tower` 改写成功
- [x] 所有 event `source_repo` 字段从 `local/agent-project-control-tower` 改写为 `conanxin/agent-project-control-tower`

#### D. 验证

- [x] `make all` PASS（53/53，data 链路）
- [x] `make publish-preflight` PASS（1/1/7，public-data 链路）
- [x] `cd apps/dashboard && npm run build` PASS（4 pages，prebuild 钩子从 public-data 重写 generated/）
- [x] pre-commit audit CLEAN
- [x] `tower.py report-phase ACT-6` 上报（PASS / health=green）
- [x] README / DEPLOYMENT_PLAN / MVP_PLAN 同步更新

### 不用

- ❌ **不**在 CLI 配 Cloudflare API token（沿用 ACT-4B 决策）
- ❌ **不**改 `apps/dashboard/` 任何源码（部署问题一律在 CF Pages UI 解决）
- ❌ **不**改 public-data 边界（仍 gitignore `data/` 和 `generated/`，仍只暴露 `public-data/`）
- ❌ **不**接 5 个项目（只接 1 个；ACT-6B 候选再接）
- ❌ **不**配 redirect / HSTS / Analytics（推到 ACT-5C 或更后）
- ❌ **不**跑在线 URL 验收（范围限制：本地 + 构建链路；在线重新部署由 `git push` 触发）

### 当前 public-data 统计（ACT-6 落定，1/1/7）

```yaml
projects:
  - id: agent-project-control-tower
    name: Agent Project Control Tower
    repo: conanxin/agent-project-control-tower      # ← rewritten from local/
    location: local
    category: agent-infra
    status: ACTIVE
    primary_agent: local-hermes

agents:
  - id: local-hermes
    type: hermes
    machine: local
    display_name: Local Hermes (notebook)
    operator: xin
    capabilities: [scaffolding, orchestration, long-running]

events:
  - 2026-06-11T03:20:59Z  PROJECT_REGISTERED
  - 2026-06-11T03:20:59Z  PHASE_REPORT  ACT-0   PASS  (Project Design and Architecture)
  - 2026-06-11T03:21:00Z  PHASE_REPORT  ACT-1   PASS  (Local Data Flow Prototype)
  - 2026-06-11T03:21:00Z  PHASE_REPORT  ACT-2   PASS  (Tower CLI and Event Reporting)
  - 2026-06-11T03:37:58Z  PHASE_REPORT  ACT-3A  PASS  (Astro Dashboard Shell)
  - 2026-06-11T11:43:38Z  PHASE_REPORT  ACT-5   PASS  (Cloudflare Pages Online Verification)
  - 2026-06-11T12:42:21Z  PHASE_REPORT  ACT-5B  PASS  (Custom Domain Verification)
```

> **注**：ACT-3B / ACT-4A / ACT-4B 这 3 个阶段没有 PHASE_REPORT 上报到 data/（只更新 docs/），所以 timeline 共 7 个 event 而不是 10 个。**这是真实的控制塔状态**。

### rejection safety

- 真实 `data/` 仍 gitignored
- `local/<id>` placeholder 在 data/ 里就是"安全占位符"——不会触发 home path regex（regex 是 `/home/<user>/`，`local/` 不匹配）
- `local-book-tool` / `cloud-art-site` demo events 仍存在 data/ 但**不**被 ACT-6 导出（`--project-id` 过滤）
- export redaction 0 FAIL / 0 WARN（dry-run 验证 + 实际写后验证）

### ACT-6 期间发现

- ACT-5 报告里"generated/index.json 在 CF Pages build context 里能拿到（机理未深究）"的疑问——ACT-6 通过 `prebuild` 钩子**显式消除**了那个疑问：CF Pages build 现在**不依赖**外部 generated/，而是 `npm run build` 自己跑 `tower.py build --source public-data` 生成
- `make dashboard` 之前 `dashboard: build` 依赖 `tower.py build`（data 版）—— 这与 ACT-6 的"public-data 是唯一线上源"原则冲突。ACT-6 拆分为 `dashboard`（public）+ `dashboard-local`（data），移除 `dashboard: build` 依赖
- `make publish-preflight` 第一步之前是 `public-data`（examples）—— ACT-6 改为 `public-data-real`（data 切片），让 publish 链反映 ACT-6 真实子集
- `data/registry/projects.yml` 的 `local/agent-project-control-tower` 占位符与 `data/events/*.json` 的 `source_repo: local/agent-project-control-tower` 是**配套设计**——导出时 `repo-prefix` 把 `local/` 一并改写为 `conanxin/`，保证公开版不漏 `local/` 字符串

### 如何在 ACT-6 后接入第 2 个真实项目（ACT-6B 候选）

```bash
# 1) 在 data/ 里跑 1 个真实 event（如果项目还没注册）
python scripts/tower.py register-project --project-id booktrans-desk --repo ...
python scripts/tower.py report-phase --project-id booktrans-desk --phase-id L1 ...

# 2) 导出（注意用 --output public-data --replace，会清空 ACT-6 的 agent-project-control-tower 数据）
#    → 想要"多项目并集"需要 export 多次后人工合并
#    → 或者：让 ACT-6B 设计多 project 合并语义

# 3) 验证 + push
make publish-preflight
git add public-data/
git commit -m "data: add booktrans-desk to public-data"
git push origin main
# → CF Pages 自动 re-deploy，custom domain 30s 内刷新
```

---

## ACT-6B — Second Real Project Public Export（**下一步**）

> **目标**：在 ACT-6 真实 1/1/7 的基础上接入第 2 个真实开源项目，验证 public-data 多项目合并语义。
>
> **状态**：⏸ PENDING（等用户确认进入 ACT-6B）。
>
> **前置条件**（已就位）：
> - ACT-6 ✅：构建链路 + export 脚本 + public-data 真实子集 1/1/7
> - `make public-data-real` 默认只导 1 个 project（ACT-6 设计选择）

### 候选项目

| ID | 仓库 | 主 agent | 备注 |
| --- | --- | --- | --- |
| `booktrans-desk` | `conanxin/booktrans-desk` | local-hermes | EPUB 处理（最成熟） |
| `artvee-gallery` | `conanxin/artvee-gallery` | cloud-openclaw | 长跑、批量抓取 |
| `conan-vps-tower` | `conanxin/conan-vps-control-tower` | local-codex | 运维工具 |
| `medium-archive` | `conanxin/medium-archive` | local-codex | 批量处理 |
| `explainlens` | `conanxin/explainlens` | local-hermes | 文档站 |

### 范围（ACT-6B 待执行）

- [ ] 选 1 个候选项目（建议 `booktrans-desk`，最成熟）
- [ ] 在 data/ 里 register project + 跑 1 个真实 phase event
- [ ] 设计多 project export 合并语义（ACT-6 用 `--replace` 整体覆盖，ACT-6B 需要"添加而不删"或"重新合并 2 个 project"）
- [ ] 验证 redaction 0 FAIL
- [ ] 跑 `make publish-preflight` 验证 public-data 含 2 projects
- [ ] 在线验收（custom domain + pages.dev）—— ACT-6 没做，ACT-6B 补
- [ ] 写 ACT-6B 阶段报告

### 验收

- [ ] 2 个项目（agent-project-control-tower + 第 2 个）出现在 dashboard
- [ ] 每个 project 有 ≥ 1 个 phase event
- [ ] 在线 7/7 URL HTTP 200
- [ ] 敏感模式扫描 0 命中

### 退出条件

> 公开 dashboard 真正承载 2 个真实项目，朋友看一眼能说出"这人在用 agent 跑 2 个开源项目"。

### 不在 ACT-6B 范围

- ❌ 不接 5 个项目（一次性 5 个会爆炸；保持 1+1 节奏）
- ❌ 不改 public-data 边界（仍 gitignore data/）
- ❌ 不配 redirect / HSTS / Analytics（推到 ACT-5C 或更后）
- ❌ 不接 ACT-7+ 的功能

---

## ACT-5C — Production Hardening（可选，决策中）

> **目标**：在 ACT-5B 已绑 custom domain 之上做 production-grade 增强。
>
> **状态**：⏸ DECISION PENDING（用户决定是否进入 ACT-5C 还是直接进 ACT-6）。
>
> **理由**：ACT-5B 满足了"对外可分享"的核心需求；ACT-5C 是 brand / 安全 / 可观测性的 polish 阶段。

### 候选范围（ACT-5C 待决策）

| 候选 | 工作量 | 价值 |
| --- | --- | --- |
| HSTS 显式启用 | 5 min | SSL 评级 A+ |
| Web Analytics 启用 | 10 min | 知道谁在看 |
| UptimeRobot 监控 | 15 min | 挂掉主动通知 |
| build error → Telegram 通知 | 30 min | 不用查 CF 邮箱 |
| custom error 404 page | 1 hour | 品牌一致 |
| pages.dev → custom domain 301 redirect | 30 min | 统一入口 |

### 验收（如果进入 ACT-5C）

- [ ] （按选定的子集）逐项完成
- [ ] SSL 评级 A+（Qualys / SSL Labs）
- [ ] 监控：5 分钟一次检测，挂掉 → Telegram
- [ ] 404 page 显示自定义内容

### 退出条件

> 站点可以"半年不维护也不会无声挂掉"。

---

## ACT-7 — Multi-machine Agent Usage Playbook（**已完成**）

ACT-7 的目标是**把控制塔从"项目已经能跑"升级为"其他 agent / 其他机器都能按手册稳定使用"**。本阶段不接入新项目、不开发新 dashboard UI、不引入数据库、不引入登录系统、不使用 Cloudflare API token。ACT-7 的全部产出是文档 + 模板 + 检查清单。

**新增文档**：

- `docs/AGENT_USAGE_PLAYBOOK.md`（主手册，13 节）
- `docs/MULTI_MACHINE_SETUP.md`（多机器 / 多 agent persona / 跨机器 git 协作）
- `docs/PUBLIC_DATA_EXPORT_PLAYBOOK.md`（公开数据导出 + ACT-6C 误归类教训专章 §7）

**新增模板**：

- `templates/telegram/*.txt`：8 个 Telegram 直发模板（register-agent / register-project / report-phase / report-failure / report-review / report-handoff / report-release / export-public-data / cloudflare-verify）
- `templates/checklists/*.md`：4 个 checklist（preflight / redaction / public-data-review / online-verification）

**ACT-6C 教训如何写入手册**：

- 主手册 §4 列出"the `repo` field is the ground truth"
- 主手册 §5 列出"反例：optimistic `status=PASS`"（用 S13 的 PARTIAL/amber 作为引用）
- 主手册 §12.1 把"误归类"列为第一个常见错误
- 公开数据手册 §7 整节讲 ACT-6C 案例 + 4 个问题 + 4 个检查
- `public-data-review-checklist.md` §B §C §D 写死回归检查
- `online-verification-checklist.md` §F 单独一节 ACT-6C regression check

**验收**：

- `make all` / `make publish-preflight` / `npm run build` 全 PASS
- pre-commit 等效扫描 CLEAN
- 文档敏感扫描命中均为预期教学示例（详见 `reports/PHASE_ACT7_AGENT_USAGE_PLAYBOOK_REPORT.md`）
- 线上 dashboard 不变（BookTrans Desk 仍 S13 / 16f38b6 / PARTIAL）
- data/ 仍 gitignored
- working tree clean

**下一阶段建议**（二选一）：

1. **ACT-8**：real multi-agent onboarding trial——在新机器（或新 agent persona）上跑手册的端到端流程。
2. **ACT-7B**：convert templates into CLI command generator——把 `templates/telegram/*.txt` 的占位符变成 `scripts/tower.py cmd ...` 的 wrapper。

详见 `reports/PHASE_ACT7_AGENT_USAGE_PLAYBOOK_REPORT.md`。

---

## ACT-8 — Real Multi-agent Onboarding Trial（**已完成**）

ACT-7 写完了 playbook，ACT-8 验证 playbook 是不是真的能被第二个 agent 跑通。试验 agent 是 **cloud-openclaw**（VPS 上的真实 agent，与 local-hermes 跨机器），不是同机多 agent。**完全跨机器**试验 — `git clone` 真实发生；`make all` / `validate` / `register-agent` / `register-project` / `report-review` 全部在 cloud 跑；trial agent 只写自己的 `data/`，从未 push public-data。

**试验路径（trial 实际跑过的步骤）**：

1. trial agent 在 cloud VPS 上 `git clone` 控制塔
2. trial agent 跑 `make all` → **第一个真实缺口被发现**：`data/` 不存在，validate FAIL
3. trial agent 用 `cp -r examples data` bootstrap 后重跑 → `make all` PASS
4. trial agent 跑 `make test` → **第二个真实缺口被发现**：`tests/smoke.py` hardcode `python`，但 box 只有 `python3` → `FileNotFoundError`
5. trial agent `sudo ln -sf /usr/bin/python3 /usr/local/bin/python` → `make test` PASS
6. trial agent `register-agent cloud-openclaw`（idempotent：examples 已注册，无副作用）
7. trial agent 想直接 `report-review` → **第三个真实缺口被发现**：cloud 上 `data/registry/projects.yml` 没有 `agent-project-control-tower`，validate 会 FAIL
8. trial agent 先 `register-project agent-project-control-tower` → `report-review --target-*` 成功
9. trial agent 写完 `data/events/20260611T234825Z__REVIEW__cloud-openclaw__agent-project-control-tower__ACT-8-review.json`
10. trial agent **从未** `git add` 任何东西；**从未**跑 `export_public_data.py`；**从未** push 任何东西

**9 个 trial 真实发现的问题分类**：

| 类别 | 问题 | 是否文档修正 |
| --- | --- | --- |
| playbook unclear | `data/` 不存在时 validate FAIL，没提示 bootstrap | 是（AGENT_USAGE §2） |
| playbook unclear | `make publish-preflight` 是 opt-in，新 agent 可能误以为必做 | 是（AGENT_USAGE §2 + MULTI_MACHINE §4.1） |
| playbook unclear | trial agent 不知道需先 `register-project` 才能 review 该项目 | 是（AGENT_USAGE §7） |
| template wrong | `report-review` 不支持 `--source-repo` / `--source-commit` | 是（AGENT_USAGE §7 + report-review.txt） |
| template wrong | `report-review` 不支持 `--design-reason` / `--impact-analysis` | 是（AGENT_USAGE §7 + report-review.txt） |
| tool limitation | `tests/smoke.py` hardcode `python`，与 Makefile `$(PYTHON)=python3` 不一致 | 是（workaround 写入 MULTI_MACHINE §4.1） |
| tool limitation | `validate.py` 在 data/ 缺失时直接 FAIL，不给引导 | 是（bootstrap 步骤写入 AGENT_USAGE §2） |
| agent mistake | trial agent 第一次 `report-review` 时试加 `--source-*`，被 CLI 拒绝 | 已写入 §7 anti-pattern |
| agent mistake | trial agent 第一次用 multi-line `\` 命令 + 空格分隔长参数，bash 解析时把多行 join 到一个 arg | 文档中已建议"single-line" |

**未触动**（trial 没踩到的坑，留给后续 act）：

- 多台机器同时 push 冲突的协作（trial 没用 push，所以没测）
- `data/` 在两台机器间的不一致（trial 的 data/ 在 cloud 上独立存在，local-hermes 用 `scp` 拉一个事件过来，**没有 git 合并 data/**——data/ 一直是 gitignored）
- 自动化 export 流程（trial agent 没尝试，符合"双门"设计）

**文档修正（最小范围）**：

- `docs/AGENT_USAGE_PLAYBOOK.md` §2 加 bootstrap 步骤 + publish-preflight opt-in note + python alias hint
- `docs/AGENT_USAGE_PLAYBOOK.md` §7 整个 `report-review` 块重写（移除错误字段，列出实际 CLI 必填项，加 ACT-8 trial notes）
- `docs/MULTI_MACHINE_SETUP.md` §4.1 加 bootstrap + python alias + publish-preflight opt-in note
- `templates/telegram/report-review.txt` 全部重写以匹配 CLI 实际参数

**验证**：

- `make all` / `make publish-preflight` / `npm run build` / pre-commit 等效扫描 CLEAN
- 文档敏感扫描 CLEAN（所有"命中"为预期教学文本）
- 线上 dashboard 仍正常：3 real projects + 2 agents（local-hermes + cloud-openclaw）+ 16 events（含 ACT-7 + ACT-8-review）
- ACT-6C 回归检查仍 PASS（booktrans-desk 仍 `conanxin/booktrans-desk` / S13 / 16f38b6 / PARTIAL）
- working tree clean

详见 `reports/PHASE_ACT8_REAL_MULTI_AGENT_ONBOARDING_TRIAL_REPORT.md`。

---

## ACT-9B+ — Future Optional Enhancements

> ACT-9B 完成后讨论的扩展。**不要提前做**。

- ~~**ACT-9B**：prototype CI proposed-export artifact~~ ✅ 已完成 (2026-06-12)
- ~~**ACT-9C**：manual review workflow polish——Makefile 默认 3 project 化 + 显式 export plan + reviewer checklist~~ ✅ 已完成 (2026-06-12)
- ~~**ACT-10**：v0.1.0 release packaging——CHANGELOG / VERSION / RELEASE_NOTES / tag，无新功能。~~ ✅ 已完成 (2026-06-12)
- **ACT-10B**（候选）：GitHub release polish / screenshots / demo GIF——纯 polish。
- **ACT-11**（候选）：public-data update ergonomics——更快的手动刷新工作流。
- **ACT-12**：统计（`generated/stats.json`、跨项目聚合页）
- **ACT-13**：错误修正流（`correction` event 真正被 build_index 消费）
- **ACT-14**：第二份控制塔（私密项目）—— 独立仓库 + 独立域名
- **ACT-15**：Astro 升级到 v5，引入 view transitions
- **ACT-16**：被其他人 fork → 写 CONTRIBUTING.md
- **未来**：通知（Discord / Telegram webhook 在 CI 末尾）—— ACT-4A 已决定不引入，避免增加 secret 管理负担

## 风险控制

每个 ACT 开始前必须自问：

1. **这个 ACT 失败的话，我能直接 revert 吗？**
   - ACT-2 失败：删 `scripts/`，回 ACT-1
   - ACT-3 失败：删 `site/`，ACT-2 仍可用
   - ACT-4 失败：删 `.github/workflows/`

2. **这个 ACT 依赖上游的什么不可逆状态？**
   - ACT-3 依赖 ACT-2 的 schema 稳定
   - ACT-5 依赖 ACT-4 的 artifact

3. **这个 ACT 完成后，能跑多久不维护？**
   - 目标：每个 ACT 完成后能"半年不碰也不挂"

## 不在 MVP 里的

- 多视图 / 多 dashboard
- 用户系统 / 登录
- 实时 WebSocket
- 移动端 App
- 国际化（i18n）

这些**全部不做**。如果某个阶段出现"看起来需要 X"的需求，先回到 [PROJECT_VISION.md](PROJECT_VISION.md) 重新审视是否要纳入新的 ACT-7+ 候选。
