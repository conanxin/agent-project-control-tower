# Data Model

> 控制塔里所有"东西"长什么样。每个 schema 都有最小例子 + 完整例子。

## 0. 全局约定

- **格式**：注册表用 YAML，事件用 JSON
- **命名**：`snake_case` 字段、`kebab-case` 文件名
- **时间**：ISO 8601 字符串，**永远带时区**（建议 UTC：`2026-06-11T09:00:00Z`）
- **可选 vs 必填**：必填用 `required: true` 标记
- **未知字段**：CI 保留原样渲染（不抛错），但 schema 校验脚本会 warn
- **schema 版本**：所有 event 顶层带 `schema_version: "1.0.0"`

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
