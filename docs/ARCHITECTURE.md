# Architecture

> 控制塔的"零件图"——所有目录、所有数据流、所有不变量。

## 一、顶层目录

```
agent-project-control-tower/
├── registry/                ← 真相之源（人/agent 手写；脚本只追加不删）
│   ├── projects.yml         ← 项目注册表
│   └── agents.yml           ← agent 注册表
│
├── events/                  ← append-only 阶段事件（agent 写；人可读）
│   ├── 2026-06-11/
│   │   ├── local-book-tool__L1__PASS__local-hermes.json
│   │   └── cloud-art-site__C1__PASS__cloud-openclaw.json
│   └── ...
│
├── generated/               ← CI/脚本生成（人手不直接改）
│   ├── index.json           ← 供前端用的扁平数据
│   ├── projects/
│   │   └── <project-id>.json
│   └── agents/
│       └── <agent-id>.json
│
├── site/                    ← 静态 dashboard 源（ACT-3+ 引入 Astro）
│   ├── src/
│   ├── public/
│   └── package.json
│
├── scripts/                 ← 注册和上报脚本（ACT-2 引入）
│   ├── register_agent.py
│   ├── register_project.py
│   ├── report_phase.py
│   ├── report_review.py
│   ├── report_handoff.py
│   ├── report_release.py
│   ├── report_failure.py
│   ├── build_index.py
│   └── lib/
│       ├── schema.py
│       ├── git_ops.py
│       └── redaction.py
│
├── examples/                ← 手写示例（ACT-1）
│   ├── projects.yml
│   ├── agents.yml
│   └── events/
│
├── docs/                    ← 你正在读的这些文档
│
├── reports/                 ← 阶段报告（人写）
│
├── .github/workflows/
│   └── build-dashboard.yml  ← ACT-4 引入
│
├── README.md
├── LICENSE
└── .gitignore
```

### 目录职责边界（重要）

| 目录 | 谁写 | 谁读 | 是否进 Git | 是否进 dashboard |
| --- | --- | --- | --- | --- |
| `registry/` | 脚本（人触发） | 脚本、CI | ✅ | ❌（被生成） |
| `events/` | 脚本（agent 触发） | 脚本、CI | ✅ | ❌（被生成） |
| `generated/` | CI / `build_index.py` | dashboard | ❌（被 .gitignore 排除；用 cache / artifact 替代） | ✅ |
| `site/` | 人 | CI | ✅ | — |
| `scripts/` | 人 | agent、CI | ✅ | — |
| `examples/` | 人 | 人、agent | ✅ | ❌ |

> `generated/` 之所以不进 Git：避免双源真相。dashboard 直接从 CI 构建产物读取。

## 二、核心组件

### 1. Registry（注册表）

两个 YAML 文件：

- `registry/projects.yml`：所有"被追踪的项目"清单
- `registry/agents.yml`：所有"会上报的 agent"清单

不变量：

- **每个 `id` 全局唯一、不可变**
- **注册后不修改元数据**——错就写 correction event
- **删除走 ARCHIVE 流程**（status=ARCHIVED）而不是真的删行

### 2. Events（事件流）

append-only JSON 文件，路径约定：

```
events/<YYYY-MM-DD>/<project-id>__<phase>__<status>__<agent-id>.json
```

例如：

```
events/2026-06-11/local-book-tool__L1__PASS__local-hermes.json
events/2026-06-11/local-book-tool__L2__FAIL__local-codex.json
events/2026-06-11/cloud-art-site__C1__PASS__cloud-openclaw.json
```

不变量：

- **一个事件 = 一个 JSON 文件**
- **filename 包含 project / phase / status / agent**——便于 `ls` 浏览
- **JSON body 包含完整 schema**——filename 丢失也能从 body 恢复
- **一旦写入，body 不修改**——纠错用 correction event

事件类型（按 `event_type` 字段区分）：

| type | 何时写 | 必填字段 |
| --- | --- | --- |
| `agent_registered` | 首次注册 agent | `agent_id` |
| `project_registered` | 首次注册项目 | `project_id` |
| `phase` | 完成一个阶段 | `project_id`, `agent_id`, `phase`, `status` |
| `review` | 复查别人的 phase | `project_id`, `agent_id`, `reviewed_phase`, `verdict` |
| `handoff` | 把项目交给另一个 agent | `project_id`, `from_agent`, `to_agent` |
| `failure` | 显式上报失败（区别于 `phase: FAIL`） | `project_id`, `agent_id`, `phase`, `error` |
| `release` | 项目发布版本 | `project_id`, `agent_id`, `version` |
| `block` | 阻塞 | `project_id`, `agent_id`, `blocker` |
| `unblock` | 解除阻塞 | `project_id`, `agent_id`, `ref_block` |
| `archive` | 项目归档 | `project_id`, `agent_id`, `reason` |

### 3. Generated（生成数据）

`generated/index.json` 是 dashboard 唯一消费的数据源：

```json
{
  "generated_at": "2026-06-11T21:00:00Z",
  "schema_version": "1.0.0",
  "projects": [ ... 展开的 project + 最新 event ... ],
  "agents":   [ ... 展开的 agent + 最近 events ... ],
  "timeline": [ ... 跨项目时间线，按 event_time 倒序 ... ],
  "health_summary": {
    "green": 2, "yellow": 0, "red": 0, "gray": 0
  }
}
```

由 `scripts/build_index.py` 读 `registry/*.yml` + `events/**/*.json` 一次性生成。

### 4. Scripts（脚本）

MVP 阶段只暴露 7 个命令：

```
tower register-agent ...
tower register-project ...
tower report phase ...
tower report review ...
tower report handoff ...
tower report release ...
tower report failure ...
```

设计原则：

- **每个命令背后只做一件事**：写一个 JSON + 一次 git commit
- **可幂等**：同命令跑两次，第二次是 no-op（用 content-hash 检测）
- **不联网**：脚本只读写本地控制塔仓库
- **CI 友好**：可加 `--no-commit` / `--no-push` 让 CI 自己处理 git

### 5. Dashboard

静态站点（Astro 起步，可换 Eleventy / Hugo / 纯 HTML+JS）。

页面：

- `/` 首页：项目卡片 + agent 卡片 + 最近活动
- `/projects/<id>/` 项目详情：时间线 + 涉及 agent + health
- `/agents/<id>/` agent 详情：参与的项目 + 最近 phase
- `/timeline` 全局时间线
- `/about` 关于页（指向 GitHub README）

### 6. CI（GitHub Actions）

单个 workflow：

```yaml
name: build-dashboard
on:
  push:
    branches: [main]
    paths:
      - 'registry/**'
      - 'events/**'
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r scripts/requirements.txt
      - run: python scripts/build_index.py
      - run: cd site && npm ci && npm run build
      - uses: cloudflare/pages-action@v1
        with:
          apiToken: ${{ secrets.CF_API_TOKEN }}
          accountId: ${{ secrets.CF_ACCOUNT_ID }}
          projectName: agent-control-tower
          directory: site/dist
```

## 三、完整数据流

```
┌─────────────────┐
│  原项目仓库      │  (local-book-tool, cloud-art-site, ...)
│  写代码、commit │
└────────┬────────┘
         │ git push (人类/agent 在原项目目录)
         ▼
   GitHub 主仓库    ←── 原项目 CI 跑（与控制塔无关）
         │
         │
         │ tower report phase --commit <sha>
         │
┌────────▼──────────────────────────────────────┐
│ 控制塔仓库 (agent-project-control-tower)       │
│                                                │
│  scripts/report_phase.py 写入                  │
│    events/2026-06-11/local-book-tool__L1__...  │
│                                                │
│  git add events/                               │
│  git commit -m "phase L1 PASS local-hermes"   │
│  git push origin main                          │
└────────┬──────────────────────────────────────┘
         │ webhook / push
         ▼
┌──────────────────────────────────────────────┐
│  GitHub Actions (build-dashboard.yml)         │
│                                              │
│  1. checkout                                 │
│  2. python scripts/build_index.py            │
│     → generated/index.json                   │
│  3. cd site && npm run build                 │
│     → site/dist/                             │
│  4. deploy to Cloudflare Pages               │
└────────┬──────────────────────────────────────┘
         │
         ▼
   https://control-tower.xin.dev/
         │
         ▼
   任何浏览器 → 看到最新状态
```

## 四、不变量（系统级）

无论谁、什么 agent、什么时候写，**这些规则永远成立**：

1. **append-only**：events/ 下的文件一旦 push，绝不修改
2. **唯一来源**：dashboard 只读 `generated/`，不直接读 `events/`
3. **注册表不可改**：projects.yml / agents.yml 的 `id` 字段一旦写入就 freeze
4. **commit 链接必填**：任何 phase 事件都应有 `commit` 字段指向原项目仓库
5. **路径无关**：脚本不假设 cwd，所有路径以 `$TOWER_REPO` 环境变量或 `--repo` 参数解析
6. **脱敏强制**：任何 event body 不能包含内网 IP、`/home/xxx/` 私有路径、API token
7. **多机可写**：每台机器独立 clone + push；冲突只可能发生在同名 event 文件

## 五、扩展点（不写 MVP 但留位置）

| 扩展 | 触发条件 | 实现思路 |
| --- | --- | --- |
| 跨项目统计 | ACT-7 | `generated/stats.json` + dashboard 增统计页 |
| Webhook 通知 | ACT-7 | GitHub Actions 末尾加 Discord/Telegram 推送 |
| Private dashboard | 当有商业项目时 | 第二个 Cloudflare Pages 项目，绑定密码 |
| 错误修正 | schema 演化 | 写 `correction` event 指向原 event，CI 在生成时按 correction 重写视图 |
| 多视角 | 团队用 | `view` 字段支持"按客户/按里程碑"过滤 |

## 六、不在架构里的东西

- ❌ 中央数据库
- ❌ API 服务（无 REST/GraphQL）
- ❌ 用户认证
- ❌ 实时 WebSocket
- ❌ 任务调度器（Cron 用 GitHub Actions 即可）

这些**全部不做**。任何阶段如果出现"看起来需要后端"的需求，先回到 [PROJECT_VISION.md](PROJECT_VISION.md) 重新审视。
