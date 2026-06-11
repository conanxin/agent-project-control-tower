# Agent Project Control Tower

> 一个统一的"项目管理控制塔"——把分散在不同机器、不同 agent 上的多个开源项目，集中到一个 Git 仓库 + 一个静态网页里。

---

## 这个项目是什么

我同时在多台机器上、用多个 agent（Hermes、Codex、OpenClaw、Claude Code……）跑多个开源项目。每个项目仍然住在它自己的代码仓库里，由不同的 agent 接续开发、复查和发布。

问题在于：

- 项目状态散落在各机器的聊天记录、commit message、私人笔记里
- 我很难一眼看出：**哪些项目在跑、谁在跑、跑到第几阶段、卡在哪、下一步是什么**
- 想在线分享进展给协作者或社区时，要手动拼接截图和 commit 链接

**Agent Project Control Tower** 就是为了解决这个问题。它本身不写代码、也不替代原项目仓库——它只是一个"进度事实源"。

```
原项目仓库  ── push 阶段成果 ──>  控制塔仓库
                                     │
                                     ▼
                              GitHub Actions / Cloudflare Pages
                                     │
                                     ▼
                              在线 Dashboard
```

## 解决什么问题

| 没有控制塔时 | 有了控制塔之后 |
| --- | --- |
| "L2 那步到底过没过？让我翻聊天记录……" | 点开项目页，时间线一目了然 |
| 跨机器状态靠记忆 | 所有阶段事件按时间顺序沉淀到 Git |
| 想展示进展只能截聊天记录 | 公开 URL，访客直接看 |
| 失败/阻塞靠口口相传 | FAIL/BLOCKED 事件自动上墙 |
| 谁接手了哪个项目 | agents.yml + 最近 events 双视角 |

## 核心约定（先记住这几条就够用）

1. **原项目仓库不搬走**——你写的所有代码、commit、PR 仍然在 `~/workspace/projects/your-project/` 里。
2. **控制塔是一个独立的 Git 仓库**——里面只放"项目元数据 + 阶段事件 + 自动生成的网页"。
3. **agent 跑完一个阶段 → 写一个 event JSON → push 控制塔仓库**。
4. **任何人都能从在线 dashboard 看到状态**——不需要数据库，不需要登录。
5. **项目只注册一次；多个 agent 可以接力同一个项目**。

## 一次完整的使用模拟（极简版）

> 完整版在 [docs/USAGE_SIMULATION.md](docs/USAGE_SIMULATION.md)。

假设你在两台机器上跑两个项目：

| 项目 | 位置 | 主 agent |
| --- | --- | --- |
| `local-book-tool` | 笔记本 | 本地 Hermes |
| `cloud-art-site` | 云端 VPS | 云端 OpenClaw |

### 一次性：注册（每台机器、每个项目各一次）

```bash
# 在本地笔记本
tower register-agent \
  --id local-hermes \
  --machine local \
  --type hermes

tower register-project \
  --id local-book-tool \
  --repo https://github.com/you/local-book-tool \
  --scope local

# 在云端 VPS（操作一样，数据落在同一个控制塔仓库的 PR/分支里，或通过 SSH 推到 origin）
tower register-agent \
  --id cloud-openclaw \
  --machine cloud \
  --type openclaw

tower register-project \
  --id cloud-art-site \
  --repo https://github.com/you/cloud-art-site \
  --scope cloud
```

> 注意：你可以在**原项目目录里**执行 `tower report ...`，但命令背后实际是写文件 + commit/push 到**控制塔仓库**——不是写回原项目仓库。

### 持续：每完成一个阶段上报

```bash
# 本地 Hermes 完成 local-book-tool 的 L1
tower report phase \
  --project local-book-tool \
  --agent local-hermes \
  --phase L1 \
  --status PASS \
  --summary "Add book import CLI; tests green" \
  --next "L2: convert EPUB to Markdown"

# 云端 OpenClaw 完成 cloud-art-site 的 C1
tower report phase \
  --project cloud-art-site \
  --agent cloud-openclaw \
  --phase C1 \
  --status PASS \
  --summary "Static gallery generated, 120 images" \
  --next "C2: add tag filter UI"
```

### 一段时间后：本地 Codex 接手同一个本地项目

```bash
# 本地另一台机器 / 同一台机器的另一个 agent
tower report phase \
  --project local-book-tool \
  --agent local-codex \
  --phase L2 \
  --status FAIL \
  --summary "EPUB parser crashes on DRM-protected files" \
  --next "L2-fix: graceful skip + report"
```

### 自动发生：dashboard 重新构建

```
git push  →  GitHub Actions / Cloudflare Pages  →  在线 dashboard 刷新
```

访客打开 `https://control-tower.your-domain/`，看到：

- **首页**：3 个项目、2 个 agent、最近 24h 有 1 个 FAIL
- **项目页 `local-book-tool`**：时间线 L1 PASS（local-hermes）→ L2 FAIL（local-codex），health=yellow，下一步=L2-fix
- **agent 页 `local-codex`**：参与过 1 个项目，当前在 L2-fix 阶段

## 仓库里有什么

```
agent-project-control-tower/
├── README.md                  ← 你正在读的文件
├── Makefile                   ← ACT-1: validate / build / site / test
├── docs/                      ← 设计文档
│   ├── PROJECT_VISION.md
│   ├── USAGE_SIMULATION.md
│   ├── ARCHITECTURE.md
│   ├── DATA_MODEL.md
│   ├── AGENT_WORKFLOW.md
│   ├── MVP_PLAN.md
│   ├── OPEN_SOURCE_PLAN.md
│   ├── DEPLOYMENT_PLAN.md
│   └── RISKS_AND_BOUNDARIES.md
├── examples/                  ← ACT-1 的"事实源"
│   ├── projects.yml
│   ├── agents.yml
│   ├── events/                ← 3 个事件 JSON
│   └── README.md
├── scripts/                   ← ACT-1 起填：build_index, validate, build_embedded_site
├── data/                       ← .gitignore, runtime (CLI writes here)
│   ├── registry/
│   │   ├── projects.yml        ← project registration
│   │   └── agents.yml          ← agent registration
│   └── events/                 ← append-only event JSON files
├── examples/                   ← curated seed data (git-tracked)
│   ├── registry/
│   ├── events/
│   └── README.md
├── scripts/
│   ├── tower.py                ← ACT-2: unified CLI (10 subcommands)
│   ├── validate.py             ← --source {data,examples,both}
│   ├── build_index.py          ← --source {data,examples}
│   ├── build_embedded_site.py
│   ├── validate_examples.py    ← thin wrapper for ACT-1 compat
│   └── lib/
│       ├── yaml_mini.py        ← zero-dep YAML parser
│       └── redaction.py        ← ACT-2: lightweight privacy check
├── tests/
│   ├── smoke.py                ← ACT-1 acceptance (14 checks)
│   └── cli_smoke.py            ← ACT-2 CLI smoke (39 checks, isolated temp dir)
├── generated/                  ← .gitignore, build product
│   └── index.json
├── site/                       ← static dashboard sources
│   ├── index.html              ← fetch version (needs HTTP server)
│   └── index.embedded.html     ← inlined data (double-clickable)
└── reports/
    ├── PHASE_ACT0_PROJECT_DESIGN_REPORT.md
    ├── PHASE_ACT1_LOCAL_DATA_FLOW_REPORT.md
    └── PHASE_ACT2_TOWER_CLI_REPORT.md
```

## 当前阶段

**ACT-3A：Astro Dashboard Shell** — ✅ COMPLETE

控制塔现在有**两套 dashboard**：
- `site/index.embedded.html`（ACT-1/2 零依赖版，**默认入口**）
- `apps/dashboard/dist/`（ACT-3A Astro 增强版，**可选**）

### examples/ vs data/

- **`examples/`** — 跟踪在 git 里的"种子数据"：示范性项目/agent/event，文档里也引用
- **`data/`** — ACT-2 起的"真实运行数据"：被 `.gitignore` 排除，由 `tower.py` 写
- 第一次 clone 后：跑 `python scripts/tower.py seed --force` 把 examples/ 复制到 data/ 作为起点
- 测试时：clone 仓库的副本（通过 `TOWER_ROOT` 环境变量）操作 data/，**不污染**你的真实 data/

### 怎么本地跑一遍

需要 Python 3.10+（**仍**只用标准库）。

```bash
# 一次性：初始化 + 跑完整流水线
make reset && make all

# 增量
make seed          # 把 examples/ 复制到 data/（首次或重置）
make validate      # 跑 validate.py
make build         # 跑 build_index + embedded site
make test          # ACT-1 14 项验收
make test-cli      # ACT-2 CLI smoke (39 项)
```

### 怎么看 dashboard

```bash
# Linux
xdg-open site/index.embedded.html
# macOS
open site/index.embedded.html
# Windows
start site/index.embedded.html
```

控制塔本身**永远不**复制原项目代码。它只存"哪个项目在跑、跑到第几阶段、谁跑的、commit 是多少"。

### ACT-3A Astro Dashboard Shell（可选增强）

ACT-1/2 的 `site/index.embedded.html` 是**双击可看**的零依赖单页——所有访客的默认入口。
ACT-3A **额外**提供 `apps/dashboard/`，是一个 Astro 静态站，**4 个预渲染 page**：

| 路径 | 内容 |
| --- | --- |
| `/` | Summary 卡片 + 项目列表 + Agent 列表 + 最近 10 条 timeline |
| `/projects/[project_id]/` | 单项目详情：repo / location / status / phase / timeline |
| `/agents/[agent_id]/` | 单 agent 详情：machine / role / last project / timeline |
| `/timeline/` | 所有事件倒序 + 事件类型颜色标签 |

数据源：所有 page **build-time** 读取 `generated/index.json`（root）——**没有运行时 API、没有 SSR、没有外部 fetch**。

```bash
# 首次：安装依赖
cd apps/dashboard
npm install

# Build
cd ..
make dashboard
# → apps/dashboard/dist/  (8 个静态 HTML + 1 个 CSS)

# 本地预览
cd apps/dashboard
npm run preview
# 浏览器打开 http://localhost:4321/
```

`make all` **不**包含 `make dashboard`——根目录的零依赖链路保持完整。**任何想用 Astro 的用户单独跑**。

**为什么 ACT-3A 不替代 ACT-1/2 的 vanilla HTML**：

- ACT-1/2 的 `site/index.embedded.html` 是**双击可看**——零安装、零网络、零运行时
- 很多场景（CI artifact / 个人本地 / 服务器静态托管 / 邮件附件）需要"开箱即用"
- Astro 站**需要** `npm install` 一次性，运行时需要 JS hydration
- 两套并存的成本：~88 KB dist vs ~20 KB embedded HTML，可接受
- 未来**真正**对外发布（ACT-5）会选 `apps/dashboard/dist/`，embedded.html 留作离线归档

### ACT-3B Dashboard UX Polish

ACT-3A 是"能看"，ACT-3B 让它变"好用"——但**仍不引入任何依赖**（无搜索库、无状态管理库、无 UI 库）。

**Home (`/`) 增强**：
- 项目搜索框：name / id / repo / summary 全文匹配
- 筛选下拉：health（green/yellow/red/gray）、status（PASS/FAIL/...）、last agent
- 排序：最近更新 / health 红优先 / 名称 A–Z
- 一键 **Clear** 按钮 + 当前匹配数量 badge
- 空筛选结果展示 `empty-state` 占位

**Timeline (`/timeline/`) 增强**：
- 搜索 summary / phase / agent
- 筛选：event_type、status、project、agent
- 排序：newest / oldest
- 默认展示全部事件倒序

**Project detail (`/projects/[project_id]/`) 增强**：
- 顶部 status pill（health · status 双色）
- 独立的 **Latest event** 卡片
- **Next actions** 区块（独立卡片 + accent 边）
- **Timeline grouped by phase**（可折叠 details/summary）
- source commit / repo 直接展示

**Agent detail (`/agents/[agent_id]/`) 增强**：
- 顶部 machine pill
- **Event-type breakdown**（badge 矩阵）
- **Projects touched**（health 左边色块）
- 活动 timeline（按 event_type 可分类）

**主题切换**：
- 暗色（默认）/ 亮色
- 按钮在右上角，localStorage 持久化 `tower-theme`
- 切换平滑过渡（背景色 / 边框 180ms）
- 不引入依赖，纯 CSS 变量切换

**View transitions**：
- Astro `<ClientRouter />` 启用页面间基础过渡
- 仅 fade+slide，不为动画复杂化结构
- 浏览器无 View Transitions API 时自动 fallback 到 `animate`

**数据健壮性**：
- `apps/dashboard/src/lib/tower-data.ts` 对所有字段设默认值
- `projects / agents / timeline` 缺字段时 build 不崩（`raw.x ?? []`）
- `schema_version` / `source` / `generated_at` 全部有 fallback
- `getProject / getAgent` 对空 id 静默返回 `undefined`

**零依赖路径保留**：
- `site/index.embedded.html` 仍是双击可看的 ACT-1/2 vanilla HTML
- `make all` **不**触发 npm build
- `make dashboard` 是 opt-in
- 两套独立数据流：零依赖 HTML 从 `generated/index.json` 嵌入；Astro build 同样读同一文件

**使用 Astro dashboard**：

```bash
# 1) 安装依赖（一次性）
cd apps/dashboard
npm install

# 2) 在 data/ 已 build 后：
cd ..
make dashboard
# → apps/dashboard/dist/  (8 HTML + 1 CSS + 1 client JS bundle)

# 3) 本地预览
cd apps/dashboard
npm run preview
# 浏览器打开 http://localhost:4321/
```

**零依赖 vs Astro dashboard 对比**：

| 维度 | 零依赖 HTML（ACT-1/2） | Astro dashboard（ACT-3B） |
| --- | --- | --- |
| 安装 | 0 | `npm install`（一次性） |
| 数据源 | `generated/index.json` 嵌入 | `generated/index.json` 静态 import |
| 搜索/筛选 | 无（HTML 直接展示） | 前端原生 JS（filters.ts） |
| 主题切换 | 无 | 暗/亮 + localStorage |
| View transitions | 无 | Astro ClientRouter |
| 移动端 | 基础 CSS | 媒体查询优化 |
| 适用场景 | CI artifact / 邮件附件 / 双击查看 | 真正对外发布 / 个人主页嵌入 |

### ACT-4A CI/CD and Publish Readiness

ACT-4A 在 push GitHub 之前把所有"线上之前需要就位的东西"准备好。本阶段**不**创建远程仓库、**不** push、**不**部署。

**数据职责划分**（ACT-4A 落定）：

| 目录 | 角色 | 是否 tracked |
| --- | --- | --- |
| `data/` | 本地真实控制塔数据 | ❌ gitignored |
| `examples/` | 脱敏示例数据 / seed | ✅ tracked |
| `public-data/` | 准备发布的脱敏快照 | ✅ tracked |
| `generated/` | 构建产物（index.json） | ❌ gitignored（CI 重生成） |
| `site/index.embedded.html` | 离线双击打开的快照 | ✅ tracked |
| `apps/dashboard/dist/` | Astro build 输出 | ❌ gitignored |

**新增的 4 个东西**：

1. **`public-data/`** — 公开 dashboard 唯一数据源。从 `examples/` 或 `data/` 通过 `export_public_data.py` 强制 redaction 后写入。
2. **`scripts/export_public_data.py`** — 一行命令导出，自动扫描所有 text 字段，遇到真 secret / 真实 home 路径直接 FAIL 拒绝写入。
3. **`Makefile` 新 target**：`public-data` / `public-build` / `site-only` / `publish-preflight`。
4. **`.github/workflows/ci.yml`** — 3 jobs：zero-dep acceptance + astro dashboard + publish preflight。**不**自动部署。

**本地发布前检查**（ACT-4A 起跑）：

```bash
# 零依赖回归（必须 PASS）
make all

# 公开数据 → dashboard 全链路验证（不部署任何东西）
make publish-preflight
# 内部 4 步：
#   1. public-data     → export_public_data.py 从 examples 写 public-data/
#   2. public-build    → validate + build 跑 public-data → generated/index.json
#   3. site-only       → build_embedded_site.py 读 generated/ 写 site/embedded
#   4. dashboard       → npm run build → apps/dashboard/dist/
```

**为什么 ACT-4A 仍不 push GitHub**：

- examples 是占位数据（2 projects / 3 events）——发布前用户可能想用真实项目脱敏子集替换
- deploy target（Cloudflare Pages vs GitHub Pages）还没决策
- 自动 deploy 会让 "push typo → 公开站点异常" 成为可能
- ACT-4B 才是真正创建远程 + push + 选 hosting

**为什么 data/ 仍 gitignored**：

- 本地真实 event 可能含 `/home/xin/...`、`sk-...` token、真实 IP
- 即使有意写"纯净"data，agent 自动写入时仍可能泄露
- 公开路径必须**显式**经过 `export_public_data.py` 强校验——git history 一旦 push 不可逆
- ACT-4A 提供 `public-data/` 作为安全的"出口"——既保留本地真实数据私密，又能让公开 dashboard 工作

**CI 公开运行时会跑什么**（.github/workflows/ci.yml）：

```
zero-dep-acceptance       → make all
astro-dashboard           → make dashboard
publish-preflight         → make publish-preflight
```

跑通后才算 CI green。**artifact**（7 天保留）：

- `generated/index.json`（data 版）
- `dashboard-dist`（Astro dist/）
- `public-data-manifest`（MANIFEST.json）
- `generated/index.json`（public 版）
- `site-embedded-public`（embedded HTML）

**agent 工作流**（在 `docs/AGENT_WORKFLOW.md` 详述）：

```
agent  → tower report-phase  →  data/         (private, gitignored)
human  → export_public_data  →  public-data/  (sanitized, tracked)
CI     → tower build public  →  generated/    (build artifact)
CF/GP  → astro build         →  apps/dashboard/dist/  (deployed)
```

**绝不**让 agent 直接写 `public-data/`——把"判断哪些可公开"留给人类。

### ACT-2 关键命令

```bash
# 1) 注册自己（每台机器 / 每个 agent 一次）
python scripts/tower.py register-agent \
  --agent-id local-hermes \
  --name "Local Hermes" \
  --machine "local-wsl" \
  --role "primary-coding-agent"

# 2) 注册项目（每个项目一次）
python scripts/tower.py register-project \
  --project-id local-book-tool \
  --name "Local Book Tool" \
  --repo "conanxin/local-book-tool" \
  --location "local" \
  --category "reading-tool" \
  --status "ACTIVE" \
  --description "A local open-source reading tool" \
  --agent-id local-hermes

# 3) 完成阶段后上报（每次阶段都跑）
python scripts/tower.py report-phase \
  --project-id local-book-tool \
  --agent-id local-hermes \
  --phase-id L2 \
  --phase-name "First runnable command" \
  --status PASS \
  --summary "Added the first runnable CLI command." \
  --source-repo conanxin/local-book-tool \
  --source-commit abc2222 \
  --next "Enter L3: config file support"

# 4) 失败时用快捷命令
python scripts/tower.py report-failure \
  --project-id local-book-tool \
  --agent-id local-codex \
  --phase-id L3 \
  --summary "Config fallback failed when config file is missing." \
  --failure-reason "Missing config file did not fall back to defaults." \
  --next "Fix default config fallback."

# 5) 复查别人
python scripts/tower.py report-review \
  --project-id cloud-art-site \
  --agent-id local-hermes \
  --phase-id C1-review \
  --status PASS \
  --summary "Reviewed cloud-openclaw C1 result. Build and homepage passed." \
  --target-agent-id cloud-openclaw \
  --target-phase-id C1 \
  --target-commit def1111

# 6) 交接给另一个 agent
python scripts/tower.py report-handoff \
  --project-id local-book-tool \
  --from-agent-id local-hermes \
  --to-agent-id local-codex \
  --current-phase L2 \
  --reason "L2 requires coding implementation."

# 7) 发版
python scripts/tower.py report-release \
  --project-id cloud-art-site \
  --agent-id cloud-openclaw \
  --version v0.1.0 \
  --summary "Released first public static site." \
  --source-commit def3333 \
  --release-url "https://github.com/conanxin/cloud-art-site/releases/tag/v0.1.0"
```

### 隐私保护（redaction）

任何 `report-*` 写入前都会扫文本字段：

- **FAIL（拒写）**：明显 token / API key / Authorization Bearer / 私钥 / 私路径
- **WARN（写但告警）**：`/home/xxx/`、`/Users/xxx/`、`C:\Users\xxx\`、IPv4、`.env` 引用
- **PASS（静默）**：其他

例子：

```bash
# 这会 FAIL，不写 event
python scripts/tower.py report-phase ... \
  --summary "Tested with api_key=sk-123...abcdef, all ok"
#  → [FAIL] privacy check failed: [summary] FAIL: credential-like assignment

# 这会 WARN，写 event 但 user 看到警告
python scripts/tower.py report-phase ... \
  --summary "Built in /home/ubuntu/notes, all green"
#  → [WARN] privacy warnings: [summary] WARN: local home path detected
```

### 上报后为什么需要 git add / git commit

**`tower.py` 永远不会自动 commit 或 push**。设计原因：

- agent 写完 event **不等于** event 正确——可能忘了填 `next`、可能 summary 写错、可能 health 算错
- 让 agent（或者人）**先** `git status` / `git diff` 看看写了什么，**再**决定 commit
- 一旦 commit 进 git，就成了"事实"——dashboard 也会显示

典型 git 工作流（agent 完成代码后）：

```bash
# 1) 在原项目目录：写代码、commit、push
cd ~/projects/local-book-tool
git add . && git commit -m "L2: first runnable command"
git push

# 2) 在控制塔目录：写 event、build、commit、push
cd ~/workspace/projects/agent-project-control-tower
python scripts/tower.py report-phase ...     # 写 data/events/*.json
git status                                   # ← user 必看
git add data/events/ generated/ site/        # ← 显式 add
git commit -m "status(local-book-tool): L2 PASS"
git push
```

### ACT-2 证明了什么

- ✅ agent 不再需要手写 event JSON——10 个 `tower.py` 子命令覆盖全流程
- ✅ 隐私检查自动跑：token 拒写、IP/路径 warn-but-write
- ✅ 项目只注册一次，多个 agent 可以接力同一项目（`report-handoff`）
- ✅ validate + build 在每次写入后自动跑（user 立即看到新数据）
- ✅ 临时目录测试不污染真实 data/（`TOWER_ROOT=tmpdir` 模式）
- ✅ `make all` 一键跑通：validate + build + 14 (smoke) + 39 (cli_smoke) = 53 个验收全过

### ACT-2 还没有做什么

- ❌ GitHub Actions——dashboard 不会"自动更新"（ACT-4）
- ❌ Cloudflare Pages 部署——只能本地看（ACT-5）
- ❌ 真正的 `git add` / `git commit` 集成——脚本刻意**不**做（见上）
- ❌ 项目详情页、agent 详情页——ACT-1/2 仍只有首页
- ❌ 自动 schema migration——如果未来 event_type 改名，老 event 需手动 migration

### 关键心法（再读一次）

> **原项目目录负责保存真实代码 commit。控制塔目录负责保存项目进展 event。**
>
> **agent 可以在原项目目录完成代码任务，但进展最终要写入控制塔 data/events/。**

控制塔本身**永远不**复制原项目代码。它只存"哪个项目在跑、跑到第几阶段、谁跑的、commit 是多少"。

## License

TBD（计划 MIT，见 [docs/OPEN_SOURCE_PLAN.md](docs/OPEN_SOURCE_PLAN.md)）。
