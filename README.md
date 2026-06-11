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
├── examples/                  ← 可直接复制的注册表 + 示例事件
│   ├── projects.yml
│   ├── agents.yml
│   └── events/
├── scripts/                   ← ACT-2 开始填：register_*, report_*, build_index
├── reports/                   ← 阶段报告
│   └── PHASE_ACT0_PROJECT_DESIGN_REPORT.md
└── (未来) site/ 或 dashboard/ ← ACT-3 起的静态站点源
```

## 当前阶段

**ACT-0：Project Design and Architecture**——只做设计，不写运行时。

下一阶段 **ACT-1** 会先在 `examples/` 里跑通"手写 YAML/JSON → 渲染成一张静态总览页"的全链路。

## License

TBD（计划 MIT，见 [docs/OPEN_SOURCE_PLAN.md](docs/OPEN_SOURCE_PLAN.md)）。
