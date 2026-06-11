# Data Model

> 控制塔里所有"东西"长什么样。每个 schema 都有最小例子 + 完整例子。

## 0. 全局约定

- **格式**：注册表用 YAML，事件用 JSON
- **命名**：`snake_case` 字段、`kebab-case` 文件名
- **时间**：ISO 8601 字符串，**永远带时区**（建议 UTC：`2026-06-11T09:00:00Z`）
- **可选 vs 必填**：必填用 `required: true` 标记
- **未知字段**：CI 保留原样渲染（不抛错），但 schema 校验脚本会 warn
- **schema 版本**：所有 event 顶层带 `schema_version: "1.0.0"`
- **ACT-2 现场命名**：event_type 大写 snake_case（`PHASE_REPORT` / `REVIEW_REPORT` / `HANDOFF` / `RELEASE` / `AGENT_REGISTERED` / `PROJECT_REGISTERED` / `FAILURE` / `BLOCK` / `UNBLOCK` / `ARCHIVE`）

---

## 1. Project Registry — `registry/projects.yml`

### 1.1 单条记录 schema

```yaml
- id: string                     # required, kebab-case, 不可变
  name: string                   # required, 人类可读
  repo: string                   # required, 原项目仓库 URL
  scope: enum [local, cloud, mixed]  # required
  home_machine: string           # optional, 默认 primary-agent 所在机器
  primary_agent: string          # required, agent id
  description: string            # optional, 一句话
  topics: [string]               # optional, 标签
  status: enum                   # required, 默认 ACTIVE
  registered_at: datetime        # required
  homepage: string               # optional, 部署后 URL
```

### 1.2 状态枚举

| 值 | 含义 |
| --- | --- |
| `ACTIVE` | 正常追踪中 |
| `PAUSED` | 暂时不跑（个人原因 / 等待上游） |
| `ARCHIVED` | 已完成或永久放弃，不进首页 |
| `BLOCKED` | 有 blocker（应在 events 里写 `block` event） |

### 1.3 完整例子

```yaml
- id: local-book-tool
  name: "Local Book Tool"
  repo: https://github.com/xin/local-book-tool
  scope: local
  home_machine: local
  primary_agent: local-hermes
  description: "Offline EPUB → Markdown converter with knowledge sidecar"
  topics: [ebook, epub, knowledge-base]
  status: ACTIVE
  registered_at: 2026-06-11T09:05:00Z
  homepage: null
```

---

## 2. Agent Registry — `registry/agents.yml`

### 2.1 单条记录 schema

```yaml
- id: string                     # required, kebab-case, 不可变
  type: enum                     # required
  machine: enum [local, cloud, ci]  # required
  display_name: string           # required
  operator: string               # required, 人类或组织名
  capabilities: [string]         # optional, 如 [code-review, refactor, long-running]
  status: enum                   # required, 默认 ACTIVE
  registered_at: datetime        # required
  last_seen_at: datetime         # optional, 由 CI 在每次 report 时刷新
```

### 2.2 `type` 枚举（MVP）

| 值 | 含义 |
| --- | --- |
| `hermes` | Hermes Agent |
| `codex` | OpenAI Codex CLI |
| `openclaw` | OpenClaw |
| `claude-code` | Claude Code |
| `copilot` | GitHub Copilot CLI |
| `human` | 直接由人操作（不通过 agent） |
| `ci` | 由 GitHub Actions 等自动流水线触发 |

### 2.3 完整例子

```yaml
- id: local-hermes
  type: hermes
  machine: local
  display_name: "Local Hermes (notebook)"
  operator: xin
  capabilities: [scaffolding, orchestration, long-running]
  status: ACTIVE
  registered_at: 2026-06-11T09:00:00Z
  last_seen_at: 2026-06-11T16:00:00Z

- id: local-codex
  type: codex
  machine: local
  display_name: "Local Codex (notebook)"
  operator: xin
  capabilities: [refactor, code-review, batch-edit]
  status: ACTIVE
  registered_at: 2026-06-11T09:00:00Z

- id: cloud-openclaw
  type: openclaw
  machine: cloud
  display_name: "Cloud OpenClaw (VPS)"
  operator: xin
  capabilities: [long-running, scraping, deploy]
  status: ACTIVE
  registered_at: 2026-06-11T09:30:00Z
```

---

## 3. Event — `events/<date>/<project>__<phase>__<status>__<agent>.json`

所有事件共享以下顶层字段：

```json
{
  "schema_version": "1.0.0",
  "event_id": "uuid-v4",
  "event_type": "<see table below>",
  "event_time": "2026-06-11T10:00:00Z",
  "project_id": "local-book-tool",
  "agent_id": "local-hermes",
  "machine": "local"
}
```

> `event_id` 在写入时由脚本生成 UUID v4，保证全局唯一。
>
> ACT-2 实际使用 `created_at` 字段（与 ACT-0 的 `event_time` 等价）。validate.py 接受任一名称。

### 3.0 ACT-2 通用字段（所有 event 共有）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `event_type` | enum | ✓ | 见 §3.0.1 |
| `event_id` | string (UUID) | ✓ | `tower.py` 自动生成 |
| `created_at` | ISO 8601 | ✓ | `tower.py` 自动生成 |
| `project_id` | string | ✓ | 例外：`AGENT_REGISTERED` 可省略 |
| `agent_id` | string | ✓ | 例外：`PROJECT_REGISTERED` 可省略 |
| `status` | enum | ✓ | `ACTIVE / PASS / FAIL / PARTIAL / BLOCKED / PAUSED / RELEASED / ARCHIVED` |
| `health` | enum | ✓ | `green / yellow / red / gray` |
| `summary` | string | ✓ | 一句话描述（redaction 扫描） |
| `next` | string \| null | ✗ | 下一步（redaction 扫描） |
| `next_extra` | string[] | ✗ | 多条 next（仅 `report-phase --next` 多次传入时） |
| `phase_id` | string | ✗ | 见各 type 要求 |
| `phase_name` | string | ✗ | human-readable |
| `source_repo` | string | ✗ | 原项目仓库（redaction 扫描） |
| `source_commit` | string (SHA) | ✗ | 原项目 commit |
| `source_commit_url` | string | ✗ | 原项目 commit URL（redaction 扫描） |
| `design_reason` | string | ✗ | 为什么这么设计（redaction 扫描） |
| `impact_analysis` | string | ✗ | 影响分析（redaction 扫描） |
| `checks` | object | ✗ | `{tests: "12/12", duration_minutes: 8}` 等 |
| `artifacts` | object | ✗ | 类似 checks，更自由 |

#### 3.0.1 event_type 枚举（ACT-2 收敛版）

| event_type | 触发场景 | CLI 子命令 |
| --- | --- | --- |
| `AGENT_REGISTERED` | 首次注册一个 agent | `register-agent` |
| `PROJECT_REGISTERED` | 首次注册一个项目 | `register-project` |
| `PHASE_REPORT` | 一个阶段完成（无论 PASS/FAIL） | `report-phase` |
| `FAILURE` | 阶段外的报错（`report-phase` 也会归到这里，**简化版下不再独立用**） | (legacy) |
| `REVIEW_REPORT` | 复查别人的 phase | `report-review` |
| `HANDOFF` | 把项目交给另一个 agent | `report-handoff` |
| `RELEASE` | 发版 | `report-release` |
| `BLOCK` | 阻塞 | (ACT-3 补 CLI) |
| `UNBLOCK` | 解除阻塞 | (ACT-3 补 CLI) |
| `ARCHIVE` | 项目归档 | (ACT-3 补 CLI) |

### 3.1 Phase Event

> 阶段完成事件。一阶段 = 一事件。

```json
{
  "schema_version": "1.0.0",
  "event_id": "9f1a0c12-...-...",
  "event_type": "phase",
  "event_time": "2026-06-11T10:00:00Z",
  "project_id": "local-book-tool",
  "agent_id": "local-hermes",
  "machine": "local",
  "phase": "L1",
  "status": "PASS",
  "summary": "EPUB CLI parser + 18 unit tests",
  "commit": "abc1234",
  "commit_url": "https://github.com/xin/local-book-tool/commit/abc1234",
  "next": "L2: convert EPUB → Markdown with image extraction",
  "artifacts": {
    "tests": "18/18 passing",
    "duration_minutes": 42
  },
  "tags": ["cli", "tests"]
}
```

`status` 枚举：

| 值 | 含义 | health 颜色 |
| --- | --- | --- |
| `PASS` | 阶段完成且自测通过 | green |
| `FAIL` | 阶段未完成 / 测试失败 | red |
| `PARTIAL` | 部分完成（混合通过/失败） | yellow |
| `BLOCKED` | 因外部原因无法推进 | red |
| `PAUSED` | 主动暂停 | gray |
| `SKIPPED` | 阶段跳过（已 merge / 弃用） | gray |

`phase` 字段是自由字符串，但建议按项目类型用前缀：

- 本地项目：`L1`, `L2`, `L2-fix`, `L3` …
- 云端项目：`C1`, `C2`, `C3` …
- 通用：`P0` 概念验证 / `MVP` 最小可用 / `R1.0` 首个 release

### 3.2 Review Event

> 复查别人的 phase。

```json
{
  "schema_version": "1.0.0",
  "event_id": "...",
  "event_type": "review",
  "event_time": "2026-06-11T16:00:00Z",
  "project_id": "cloud-art-site",
  "agent_id": "local-hermes",
  "machine": "local",
  "reviewed_phase": "C1",
  "reviewed_agent": "cloud-openclaw",
  "verdict": "PASS",
  "summary": "Cross-checked sitemap.xml; 120 images reachable, 0 broken links",
  "next": "C2 can proceed",
  "issues": []
}
```

`verdict` 枚举：`PASS` / `FAIL` / `COMMENT_ONLY`（仅评论，不影响 health）

### 3.3 Handoff Event

> 把项目交给另一个 agent。

```json
{
  "schema_version": "1.0.0",
  "event_id": "...",
  "event_type": "handoff",
  "event_time": "2026-06-12T08:00:00Z",
  "project_id": "local-book-tool",
  "agent_id": "local-hermes",
  "machine": "local",
  "from_agent": "local-hermes",
  "to_agent": "local-codex",
  "phase": "L2",
  "summary": "Handing off L2 refactor; see notes in commit abc1234",
  "context_url": "https://github.com/xin/local-book-tool/issues/12"
}
```

### 3.4 Failure Event

> 显式失败上报（区别于 `phase: FAIL`——这个是阶段外的报错，比如 CI 跑挂了）。

```json
{
  "schema_version": "1.0.0",
  "event_id": "...",
  "event_type": "failure",
  "event_time": "2026-06-11T11:30:00Z",
  "project_id": "local-book-tool",
  "agent_id": "local-hermes",
  "machine": "local",
  "phase": "L1.5",
  "error_class": "RuntimeError",
  "error_message": "EPUB parser timeout on >500MB file",
  "stack_first_50_lines": "...",
  "recovery_hint": "Increase timeout or stream chunks"
}
```

### 3.5 Release Event

> 项目发布版本。

```json
{
  "schema_version": "1.0.0",
  "event_id": "...",
  "event_type": "release",
  "event_time": "2026-06-15T10:00:00Z",
  "project_id": "local-book-tool",
  "agent_id": "local-hermes",
  "machine": "local",
  "version": "0.1.0",
  "tag": "v0.1.0",
  "release_url": "https://github.com/xin/local-book-tool/releases/tag/v0.1.0",
  "highlights": [
    "EPUB → Markdown CLI",
    "18 unit tests",
    "Knowledge sidecar stub"
  ]
}
```

### 3.6 Block / Unblock Event

```json
{
  "schema_version": "1.0.0",
  "event_id": "...",
  "event_type": "block",
  "event_time": "2026-06-12T14:00:00Z",
  "project_id": "local-book-tool",
  "agent_id": "local-codex",
  "machine": "local",
  "phase": "L3",
  "blocker": "Need streaming chunker before L3 retry",
  "blocks_until": "L3-retry"
}
```

```json
{
  "schema_version": "1.0.0",
  "event_id": "...",
  "event_type": "unblock",
  "event_time": "2026-06-13T09:00:00Z",
  "project_id": "local-book-tool",
  "agent_id": "local-codex",
  "machine": "local",
  "ref_block": "<event_id of the block event>",
  "summary": "Streaming chunker implemented in commit def5678"
}
```

---

## 4. Health 派生规则

`health` 字段**不在 event / project 文件中**——由 `build_index.py` 派生。

```python
def derive_health(project, recent_events):
    if project.status == "ARCHIVED":
        return "gray"
    if any(e.event_type == "block" for e in recent_events):
        return "red"
    last_phase = next(
        (e for e in recent_events if e.event_type == "phase"),
        None
    )
    if last_phase is None:
        return "gray"  # 注册了但还没 phase
    return {
        "PASS": "green",
        "FAIL": "red",
        "BLOCKED": "red",
        "PARTIAL": "yellow",
        "PAUSED": "gray",
        "SKIPPED": "gray",
    }[last_phase.status]
```

颜色到 CSS 变量（dashboard 消费）：

```css
--health-green:  #16a34a;
--health-yellow: #eab308;
--health-red:    #dc2626;
--health-gray:   #9ca3af;
```

### 4.1 ACT-7 强化 status / health 选择原则（2026-06-12）

ACT-6C 暴露了一个反复出现的失误：**自动化全 PASS 但手动项未完成时，被错记为 `PASS/green`**。BookTrans Desk S13（`16f38b6`）就是这种情况：所有 `npm` 检查都绿，但 Windows 桌面真实 click-through 仍是 `BLOCKED_MANUAL`。ACT-7 之后，`status` / `health` 的选择有了下面的明确原则。

| `status` | 派生 `health` | 何时使用 | 反例（什么时候**不要**用） |
| --- | --- | --- | --- |
| `PASS` | `green` | 阶段目标 100% 达成，包括所有手动项。**Dashboard 上的绿色 = "可以放心对外宣布"**。 | 自动化 PASS 但手动 click-through / 真实集成 / 人工审查还没做。 |
| `PARTIAL` | `amber`（dashboard 中显示为 "amber / PARTIAL"；CSS 内部仍叫 `--health-yellow`）| 阶段部分达成：部分 PASS 部分 pending；或主流程 PASS 但次流程有 blocker。**这是 ACT-6C 之后"最常被低估"的 status**。 | 不要用它来回避报告"还差什么"——`summary` 和 `next` 必须明确写"pending"项。 |
| `FAIL` | `red` | 阶段目标未达成，存在可重现的失败。`report-failure` 命令会把 status 写死为 `FAIL`、health 写死为 `red`，并要求 `--failure-reason`。 | 不要在 `report-phase` 里手写 `status=FAIL`——请用 `report-failure` 以保证 `failure_reason` 字段被结构化记录。 |
| `BLOCKED` | `red` | 阶段被外部因素阻塞（依赖未就绪、被人/平台/事件等）。可以使用 `report-phase` 写 `status=BLOCKED`，并用 `summary` / `next` 写清楚阻塞点。 | 不要把"我自己没时间做"写成 `BLOCKED`。`BLOCKED` 的语义是"想做但做不了"，不是"不想做"。 |
| `PAUSED` | `gray` | 主动暂停：项目 / 阶段被故意放下一段时间。不期待近期恢复。 | 不要把"等用户回复"写成 `PAUSED`——这是 `BLOCKED`（被外部阻塞）。 |
| `SKIPPED` | `gray` | 阶段在原计划中存在但决定跳过（变更了路线图）。 | 不要把"忘了做"写成 `SKIPPED`。 |

**反例：乐观虚标 → ACT-6C 的真实案例**

| 时间 | 错误做法（before ACT-6C） | 正确做法（after ACT-6C hotfix） |
| --- | --- | --- |
| S13 完成时 | `status=PASS health=green` | `status=PARTIAL health=amber` |
| 报告 `summary` | "S13 done" | "S13 automated PASS (build/test/release:check/pack all green); real Windows desktop click-through remains BLOCKED_MANUAL" |
| 报告 `next` | "ship" | "Continue release hardening; await a human Windows desktop click-through to clear BLOCKED_MANUAL" |

**三步判断法**（每次 `report-phase` 之前）：

1. **如果把这条事件公开贴到项目主页上，读者会不会觉得"自动化都过了 = 全过了"？** 如果会，而你又知道有手动项没做，**用 `PARTIAL/amber`**。
2. **如果有 `report-failure` 应该用 `report-failure` 吗？** 如果阶段彻底没达成，**用 `report-failure`** 而不是 `report-phase` 写 `status=FAIL`。
3. **`summary` 和 `next` 字段是否诚实地反映了真实状态？** 如果 `summary` 写"all green"而 `next` 写"click-through pending"——状态一定是 `PARTIAL/amber`，不是 `PASS/green`。

**对 `health=amber` 的 CSS 变量名**：

`build_index.py` 内部用 `yellow`，CSS 变量用 `--health-yellow`，但 dashboard UI 文案统一显示 `amber`（与状态枚举名对齐）。这是历史遗留命名分歧，**不要修改**——除非同时改 `scripts/build_index.py` 和 `apps/dashboard/` 所有 CSS / 文案。

---

## 5. ID 命名约束

| 对象 | 规则 | 示例 |
| --- | --- | --- |
| `project_id` | `kebab-case`，≤ 40 字符 | `local-book-tool` |
| `agent_id` | `<scope>-<tool>`，≤ 32 字符 | `local-hermes`, `cloud-openclaw` |
| `phase` | 自由字符串，建议 `<scope-prefix><n>` | `L1`, `C2`, `MVP` |
| `event_id` | UUID v4 | — |

冲突检测：

- `register-project` 写入前必须 `grep` `id:`，重复则报错退出
- `register-agent` 同上
- `report` 不创建新 ID，只引用已有 project / agent

---

## 6. Schema 演进

- **minor**（`1.0.0` → `1.1.0`）：新增 optional 字段——所有老 event 仍可读
- **major**（`1.x` → `2.0`）：删字段、改字段名——CI 必须先跑 `migrate_v1_to_v2.py` 把老 event 转换
- **脚本侧**：`scripts/lib/schema.py` 用 `pydantic` v2 做校验，未知字段 warn 不报错

---

## 7. 反 schema（绝对不能出现）

任何 event / 配置文件都**禁止**包含以下字段，CI 校验脚本会直接拒绝：

```yaml
forbidden_patterns:
  - field: "*_token"
  - field: "*_api_key"
  - field: "*_password"
  - field: "private_key"
  - field: "ssh_key"

forbidden_content_regex:
  - pattern: "\\b(?:[0-9]{1,3}\\.){3}[0-9]{1,3}\\b"  # IPv4
    message: "raw IP address detected"
  - pattern: "/home/[^/]+/"  # Linux user home path
    message: "private home path detected"
  - pattern: "/Users/[^/]+/"  # macOS user home path
    message: "private home path detected"
  - pattern: "C:\\\\Users\\\\[^\\\\]+\\\\"
    message: "Windows user home path detected"
```

详见 [OPEN_SOURCE_PLAN.md](OPEN_SOURCE_PLAN.md) 和 [RISKS_AND_BOUNDARIES.md](RISKS_AND_BOUNDARIES.md)。
