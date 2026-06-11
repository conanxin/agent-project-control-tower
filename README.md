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

**ACT-2：Tower CLI and Event Reporting** — ✅ COMPLETE

agent 现在可以用命令直接写进展，**不再**需要手写 event JSON。

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

embedded.html 是双击可看的；如果你用 `python -m http.server`，可以打开 `site/index.html`（fetch 版本）体验另一种风格。

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
