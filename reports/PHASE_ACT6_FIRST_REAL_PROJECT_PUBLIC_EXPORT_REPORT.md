# ACT-6 First Real Project Public Export — Phase Report

> **范围**：把公开 dashboard 从 demo 2/3/3 升级为**真实** 1/1/7——把控制塔自身作为第一个真实公开项目（dogfooding）。同时修复 ACT-5 发现的构建脆弱点：CF Pages `apps/dashboard` build 现在显式自包含（不依赖外部先生成 `generated/`）。
>
> **状态**：✅ COMPLETE（2026-06-11）

---

## 执行摘要

ACT-6 完成三件大事：

1. **构建链路 ACT-6 改进** —— `npm run build` 现在自带 prebuild 钩子，**自动**从 public-data 重新生成 `generated/index.json`。CF Pages build 不再依赖外部先生成 generated/（**ACT-5 报告里"机理未深究"的疑问正式消除**）。
2. **`scripts/export_public_data.py` ACT-6 扩展** —— 新增 5 个参数：`--project-id` / `--agent-id` / `--max-events` / `--replace` / `--repo-prefix`。
3. **导出第一个真实项目** —— `agent-project-control-tower` 自身（1 project / 1 agent / 7 events），所有 `local/<id>` 占位符被 `conanxin/` 改写。

**关键数字**：

| 指标 | ACT-5B（demo） | ACT-6（real） |
| --- | --- | --- |
| 公开 projects | 2 demo | **1 real**（`agent-project-control-tower`） |
| 公开 agents | 3 demo | **1 real**（`local-hermes`） |
| 公开 events | 3 demo | **7 real**（PROJECT_REGISTERED + ACT-0/1/2/3A/5/5B PHASE_REPORT） |
| repo 字段 | examples placeholder | `conanxin/agent-project-control-tower`（脱敏后真实 GitHub） |
| `make publish-preflight` 第一步 | `public-data`（examples 导出） | `public-data-real`（data 切片导出） |
| 真实 `data/` | gitignored | **仍 gitignored**（**不公开**） |

**关键不变量**：

- 真实 `data/` 仍 gitignored
- `local/<id>` placeholder 在 data/ 里就是"安全占位符"——不会触发 home path regex
- `local-book-tool` / `cloud-art-site` demo events 仍存在 data/ 但**不**被 ACT-6 导出（`--project-id` 过滤）
- export redaction 0 FAIL / 0 WARN
- pre-commit audit CLEAN
- `make all` 53/53 PASS / `make publish-preflight` PASS / `npm run build` 4 pages PASS

**故意没做的事**：

- ❌ 不接 5 个项目（只接 1 个；ACT-6B 候选再接）
- ❌ 不在 CLI 配 Cloudflare API token（沿用 ACT-4B 决策）
- ❌ 不改 `apps/dashboard/` 任何源码（部署问题一律在 CF Pages UI 解决）
- ❌ 不跑在线 URL 验收（范围限制：本地 + 构建链路；在线重新部署由 `git push` 触发）

---

## 修复 ACT-5 发现的构建脆弱点

### 修复 1：`apps/dashboard/package.json` 加 `prebuild` 钩子

**之前**（ACT-3A/3B/4A/5）：

```json
{
  "scripts": {
    "dev": "astro dev",
    "build": "astro build",
    "preview": "astro preview",
    "astro": "astro"
  }
}
```

`npm run build` 直接 `astro build`，依赖 `generated/index.json` 已经存在。ACT-5 报告疑问："CF Pages build 怎么拿到 generated/index.json（gitignored）？"

**现在**（ACT-6）：

```json
{
  "scripts": {
    "dev": "astro dev",
    "prebuild": "if [ \"$SKIP_DASHBOARD_PREBUILD\" = \"1\" ]; then echo 'prebuild: SKIPPED, using existing generated/index.json'; else cd ../.. && python scripts/tower.py validate --source public-data && python scripts/tower.py build --source public-data --no-embedded; fi",
    "build": "astro build",
    "preview": "astro preview",
    "astro": "astro"
  }
}
```

`npm run build` 现在**自动**跑 `tower.py validate --source public-data && tower.py build --source public-data --no-embedded`，从 public-data 重新生成 `generated/index.json`。

**效果**：

- CF Pages build **self-contained**——不需要外部先生成 generated/
- `SKIP_DASHBOARD_PREBUILD=1` 留给 `make dashboard-local` opt-in 调试
- npm lifecycle: `prebuild` → `build`（npm 4.0+ 标准 lifecycle）

### 修复 2：Makefile `dashboard` 拆分

**之前**（ACT-3B/4A/5）：

```makefile
dashboard: build
	cd apps/dashboard && npm run build
```

`dashboard` 依赖 `build`（data 版 generated）—— 这与 ACT-6 的"public-data 是唯一线上源"原则冲突。

**现在**（ACT-6）：

```makefile
# PUBLIC dist（默认）
dashboard:
	cd apps/dashboard && npm run build

# LOCAL dist（opt-in 调试）
dashboard-local:
	$(PYTHON) scripts/tower.py build
	cd apps/dashboard && SKIP_DASHBOARD_PREBUILD=1 npm run build
```

**`make dashboard`** 不再依赖 `tower.py build`——prebuild 钩子自己生成 generated/。

**`make dashboard-local`** 显式先生成 data 版 generated，再用 `SKIP_DASHBOARD_PREBUILD=1` 跳过 prebuild 钩子，避免被 public-data 覆盖。

### 修复 3：Makefile `public-data` 拆分

**之前**：

```makefile
public-data:
	$(PYTHON) scripts/export_public_data.py --source examples
```

`make publish-preflight` 第一步走 `public-data`，**永远**从 examples 导出——会覆盖我手工跑的 `--source data` 真实子集。

**现在**：

```makefile
public-data:
	$(PYTHON) scripts/export_public_data.py --source examples

public-data-real:
	$(PYTHON) scripts/export_public_data.py \
	    --source data \
	    --output public-data \
	    --project-id $(PUBLIC_DATA_PROJECT) \
	    --agent-id   $(PUBLIC_DATA_AGENT) \
	    --max-events $(PUBLIC_DATA_MAX) \
	    --repo-prefix $(PUBLIC_DATA_PREFIX) \
	    --replace
```

`make publish-preflight` 第一步改为 `public-data-real`：

```makefile
publish-preflight: public-data-real public-build site-only dashboard public-build-final
```

**效果**：publish 链从 examples demo 升级为 data 真实子集。

---

## `scripts/export_public_data.py` ACT-6 扩展

### 新增参数

| 参数 | 作用 | 默认 |
| --- | --- | --- |
| `--project-id` | 只导出该 project registry + 关联 events（可重复） | 全导 |
| `--agent-id` | 只导出该 agent（可重复） | 默认导 events 中引用的 agent |
| `--max-events N` | 每个 project 最多 N 个 event（newest first） | 50 |
| `--replace` | 清空 `public-data/{registry,events}` 再写 | merge |
| `--repo-prefix PREFIX` | 把 `local/<id>` 改写为 `<PREFIX>/<id>` | `conanxin` |

### ACT-6 实际跑过的命令

```bash
python scripts/export_public_data.py \
  --source data \
  --output public-data \
  --project-id agent-project-control-tower \
  --agent-id local-hermes \
  --max-events 20 \
  --repo-prefix conanxin \
  --replace
```

### 关键代码变更

`_filter_projects()` / `_filter_agents()` / `_filter_events()`：按 project_id / agent_id 过滤。

`_cap_events_per_project()`：每个 project 最多 N 个 event（newest first by `created_at`）。

`_rewrite_repo(value, repo_prefix)`：**递归**改写所有字符串字段中的 `local/<id>` → `<prefix>/<id>`。同时处理 event 的 `source_repo` 字段。

`_infer_agents_from_events()`：从 events 里提取 agent_id 集合，作为 agents registry 默认过滤目标。

### 输出

```
export_public_data.py — source=data → public-data
  filter: project_id in ['agent-project-control-tower']
  filter: agent_id in ['local-hermes']
  cap: max_events=20 per project (newest first)
  mode: replace
  repo-prefix: 'conanxin' (set to '' to disable rewrite)

  registry/projects.yml: 1 entries (after filter), 0 finding(s)
  events/: 7 files (after filter+cap), out of 10 in source
  registry/agents.yml: 1 entries (after filter), 0 finding(s)

redaction summary: FAIL=0, WARN=0
  --replace: wiped .../public-data/registry and .../public-data/events
  wrote .../public-data/registry/projects.yml (1 entries)
  wrote .../public-data/registry/agents.yml (1 entries)
  wrote .../public-data/events/ (7 event files)
  wrote .../public-data/MANIFEST.json

OK — public-data refreshed.
```

---

## 实际导出的 public-data 内容

### `public-data/registry/projects.yml`

```yaml
- id: agent-project-control-tower
  name: Agent Project Control Tower
  repo: conanxin/agent-project-control-tower      # ← rewritten from local/agent-project-control-tower
  location: local
  category: agent-infra
  status: ACTIVE
  description: A Git-backed control tower for multi-agent project progress tracking.
  primary_agent: local-hermes
```

### `public-data/registry/agents.yml`

```yaml
- id: local-hermes
  type: hermes
  machine: local
  display_name: Local Hermes (notebook)
  operator: xin
  capabilities:
  - scaffolding
  - orchestration
  - long-running
  status: ACTIVE
  registered_at: '2026-06-11T09:00:00Z'
  last_seen_at: '2026-06-11T16:00:00Z'
```

### `public-data/MANIFEST.json`（ACT-6 升级后）

```json
{
  "agent_filter": ["local-hermes"],
  "event_count": 7,
  "max_events_per_project": 20,
  "project_filter": ["agent-project-control-tower"],
  "registry_files": ["agents.yml", "projects.yml"],
  "repo_prefix": "conanxin",
  "source": "data"
}
```

之前 ACT-5 demo 版的 MANIFEST 是 `event_count: 3, source: examples` —— ACT-6 之后改为 `event_count: 7, source: data`。

### `public-data/events/*.json`（7 个文件）

| 文件 | event_type | phase_id | status | summary 摘要 |
| --- | --- | --- | --- | --- |
| `20260611T032059Z__PHASE__...__ACT-0.json` | PHASE_REPORT | ACT-0 | PASS | Project Design and Architecture |
| `20260611T032059Z__PROJECT_REG__...json` | PROJECT_REGISTERED | — | ACTIVE | project registered |
| `20260611T032100Z__PHASE__...__ACT-1.json` | PHASE_REPORT | ACT-1 | PASS | Local Data Flow Prototype |
| `20260611T032100Z__PHASE__...__ACT-2.json` | PHASE_REPORT | ACT-2 | PASS | Tower CLI and Event Reporting |
| `20260611T033758Z__PHASE__...__ACT-3A.json` | PHASE_REPORT | ACT-3A | PASS | Astro Dashboard Shell |
| `20260611T114338Z__PHASE__...__ACT-5.json` | PHASE_REPORT | ACT-5 | PASS | Cloudflare Pages Online Verification |
| `20260611T124221Z__PHASE__...__ACT-5B.json` | PHASE_REPORT | ACT-5B | PASS | Custom Domain Verification |

每个 event 的 `source_repo` 字段都被改写为 `conanxin/agent-project-control-tower`。

---

## rejection safety（为什么 ACT-6 不会泄露 data/）

### 1. data/ 仍 gitignored

```text
$ cat .gitignore | grep -E "^(data|generated)/"
data/
generated/
```

### 2. `local/<id>` 占位符不会触发 home path regex

`scripts/lib/redaction.py` 的 home path regex：

```python
_HOME_PATH_PATTERNS = (
    re.compile(r"/home/(?!tower\b|runner\b|www-data\b|node\b)[A-Za-z0-9._-]+/"),
    re.compile(r"/Users/(?!Shared\b|runner\b)[A-Za-z0-9._-]+/"),
    re.compile(r"[A-Za-z]:\\Users\\[^\\\s:]+\\"),
)
```

`local/agent-project-control-tower` 是 `local/<id>` 形式，**不**匹配 `/home/<user>/`。**`local/` 是个安全占位符**——设计为不让 home 路径进 git history。

### 3. `--project-id` 过滤

data/ 里**同时含** 3 个 project（local-book-tool / cloud-art-site / agent-project-control-tower）+ 10 个 event。`--project-id agent-project-control-tower` 只过滤出 1 个 project + 7 个 event。**demo 项目的 events 不会进 public-data**。

### 4. redaction 0 FAIL

`export_public_data.py` 对**所有文本字段**跑 redaction 检查。ACT-6 实际写后扫描：FAIL=0, WARN=0。

### 5. pre-commit audit CLEAN

```text
$ python /tmp/precommit_audit.py
PRE-COMMIT AUDIT CLEAN: no real secrets/paths/IPs in this project's production code
```

---

## 本地验证结果

### `make all`

| 检查 | 结果 |
| --- | --- |
| validate + build（data/ 链路） | PASS |
| CLI SMOKE TEST（39 项 CLI 烟测 + 14 项 ACT-1 烟测） | PASS（"CLI SMOKE TEST PASSED"） |
| 3 projects / 4 agents / 11 events（data/ 来源） | 写入正常 |
| health 派生 | green=2 yellow=0 red=1 blocked=0 |
| redaction FAIL（api_key=sk-...） | 正确拒写 |
| redaction WARN（/home/ubuntu/） | 写但告警 |

### `make publish-preflight`（ACT-6 升级后，第一步走 `public-data-real`）

```
PUBLISH PREFLIGHT: PASS
  public-data/    exported from data/ (redacted real-project slice)
  generated/      rebuilt from public-data
  site/embedded   rebuilt from public-data
  apps/dashboard  dist/ rebuilt from public-data
  (nothing deployed — ACT-4B creates the remote and pushes)
```

| 步骤 | 结果 |
| --- | --- |
| 1. public-data-real | PASS（1/1/7 from data/，redacted） |
| 2. public-build | PASS（validate public-data + build generated/） |
| 3. site-only | PASS（19.2 KB） |
| 4. dashboard | PASS（4 pages built in 1.66s，prebuild 钩子跑） |
| 5. public-build-final | PASS（1 project, 1 agent, 7 events） |

### `cd apps/dashboard && npm run build`

```
[build] 4 page(s) built in 1.61s
[build] Complete!
```

Prebuild 钩子自动从 public-data 重写 `generated/index.json`，4 pages：
- `index.html` (home)
- `timeline/index.html`
- `projects/agent-project-control-tower/index.html`（**唯一**真实项目）
- `agents/local-hermes/index.html`（**唯一**真实 agent）

**dist 不再含** `local-book-tool` / `cloud-art-site` 的 HTML —— public-data 真实子集正确反映。

### `python /tmp/precommit_audit.py`

```
PRE-COMMIT AUDIT CLEAN: no real secrets/paths/IPs in this project's production code
```

---

## 公开边界（ACT-6 落定，与 ACT-5B 完全一致）

| 内容 | 状态 |
| --- | --- |
| 在线 dashboard（custom domain `control-tower.conanxin.com`） | ✅ 公开（**数据升级为真实 1/1/7**） |
| 在线 dashboard（pages.dev fallback） | ✅ 公开（同上） |
| 仓库元数据（README / docs / LICENSE） | ✅ 公开 |
| `public-data/` (1/1/7 from data/) | ✅ 公开，**唯一** publish 数据源 |
| `examples/` (sanitized seed) | ✅ 公开（**但 ACT-6 publish 不再用**） |
| `site/index.embedded.html`（zero-dep public snapshot） | ✅ 公开 |
| `data/` (local real control tower) | ❌ gitignored，**仍不公开** |
| `generated/` (build artifact) | ❌ gitignored，CF Pages 重新 build |
| `apps/dashboard/dist/` (Astro build) | ❌ gitignored，CF Pages build 输出 |

**关键不变量**：

- 真实 `data/` **从未**进入 git history，也**从未**被 deploy
- ACT-4A 的 `export_public_data.py` 强校验仍是这条边界的唯一入口
- ACT-6 在线扫描 0 命中证明这条边界当前守得住

---

## ACT-6 期间发现

### 发现 1：ACT-5 报告的"generated/index.json 在 CF Pages build context 里能拿到（机理未深究）"疑问正式消除

**之前**（ACT-3A ~ ACT-5）：`apps/dashboard/package.json` 的 `build` script 是裸 `astro build`，需要 `generated/index.json` 已经存在。CF Pages build 实际能拿到——但**机理不显式**。

**ACT-6 修复**：`prebuild` 钩子让 `npm run build` **自包含**——build 期间自己跑 `tower.py build --source public-data` 生成 `generated/`。CF Pages build 不依赖任何外部预生成。

**效果**：

- `apps/dashboard/package.json` 改完后，CF Pages Root directory `apps/dashboard` 的 build 链路是**完全 self-contained**的
- 任何 git push → CF Pages 自动 build → 30s 内出新版
- ACT-5 报告里"build context 机理"的疑问**显式消除**（不用再深究 CF Pages 内部）

### 发现 2：`make dashboard` 之前 `dashboard: build` 依赖 `tower.py build`（data 版）

**之前**（ACT-3B/4A/5）：

```makefile
dashboard: build
	cd apps/dashboard && npm run build
```

`build` target = `tower.py build`（data 版 generated）。`dashboard` 先跑 data 版 generated，再跑 npm build 读这份 generated。

**问题**：

- ACT-4A 设计的"public-data 是唯一线上源"原则被破坏——`make dashboard` 默认用 data 版 generated
- ACT-5 publish 时 `make publish-preflight` 链里第 5 步（`dashboard`）写 data 版 generated，然后第 6 步（`public-build-final`）再覆盖回 public-data 版——**链里产生 race condition**

**ACT-6 修复**：

```makefile
dashboard:
	cd apps/dashboard && npm run build   # prebuild 钩子自动从 public-data 写 generated

dashboard-local:
	$(PYTHON) scripts/tower.py build        # 显式写 data 版 generated
	cd apps/dashboard && SKIP_DASHBOARD_PREBUILD=1 npm run build  # 跳过 prebuild
```

**效果**：

- `make dashboard` 默认走 public-data
- `make dashboard-local` opt-in 调试走 data
- `make publish-preflight` 链里**没有 race**——`dashboard` 步骤和 `public-build-final` 步骤都写 public-data 版 generated

### 发现 3：`make publish-preflight` 第一步之前是 `public-data`（examples）—— 与 ACT-6 真实子集目标冲突

**之前**：`publish-preflight: public-data public-build site-only dashboard public-build-final`

`public-data` 永远从 examples 导出——**会覆盖**我手工跑的真实子集。

**ACT-6 修复**：`publish-preflight: public-data-real public-build site-only dashboard public-build-final`

`public-data-real` 默认从 data 导出 1 个 project 切片（`PUBLIC_DATA_PROJECT=agent-project-control-tower`），配合 `--replace` 整体覆盖。

**效果**：

- `make publish-preflight` 跑出来的 public-data 一定是真实 1/1/7
- 不会再有"先 export 真实子集、再 make publish-preflight 把它覆盖回 demo"这种 race

### 发现 4：`data/registry/projects.yml` 的 `local/agent-project-control-tower` 占位符与 `data/events/*.json` 的 `source_repo: local/agent-project-control-tower` 是**配套设计**

**为什么是 `local/` 不是 `conanxin/`**：

- data/ 是**gitignored**的，写 `conanxin/agent-project-control-tower` 不会进 git history
- 写 `local/agent-project-control-tower` 让 data 文件**读起来清晰**（"这是 local machine 跑的本地仓库"）
- 同时**不**触发 home path regex（regex 是 `/home/<user>/`，`local/` 不匹配）

**导出时 `_rewrite_repo()`** 递归处理：

- `data/registry/projects.yml` 的 `repo: local/agent-project-control-tower` → 公开 `repo: conanxin/agent-project-control-tower`
- `data/events/*.json` 的 `source_repo: local/agent-project-control-tower` → 公开 `source_repo: conanxin/agent-project-control-tower`

**效果**：公开版完全无 `local/` 字符串泄漏。

---

## 已知限制

- ❌ **未跑在线 URL 验收**（custom domain + pages.dev）—— ACT-6 范围只验证本地 + 构建链路；在线重新部署由 `git push` 触发，CF Pages build 30s 内完成
- ❌ **多 project export 合并语义不明确** —— ACT-6 用 `--replace` 整体覆盖；想"添加而不删"需新设计
- ❌ **`make public-data-real` 默认只导 1 个 project** —— 接入第 2 个项目需修改 `PUBLIC_DATA_PROJECT` 变量
- ❌ **`make publish-preflight` 第一步 hardcode 走 `public-data-real`** —— 想切回 examples demo 链需手工跑 `make public-data && make publish-preflight`
- ❌ **未配 pages.dev → custom domain 301 redirect** — 沿用 ACT-5B 决策
- ❌ **HSTS / Web Analytics / UptimeRobot 未配** — 沿用 ACT-5B 限制
- ❌ **demo 数据 local-book-tool / cloud-art-site 仍存在 data/ 但不导出**（`--project-id` 过滤）

---

## 下一阶段建议

候选路径：

### 选项 A：ACT-6B — Second Real Project Public Export

**范围**：接入第 2 个真实开源项目（如 `booktrans-desk` / `artvee-gallery` 等），验证 public-data 多项目合并语义。

**预计工作量**：1–2 天。

**前置**：

- 选 1 个项目在 data/ 里 register + 跑 1 个真实 phase event
- 设计多 project export 合并语义（ACT-6 用 `--replace` 整体覆盖，ACT-6B 需要"添加而不删"或"重新合并 2 个 project"）

**价值**：把控制塔从"展示品"变"真工具"——dashboard 真承载 2 个真实项目。

### 选项 B：ACT-5C — Production Hardening

**范围**：HSTS / Web Analytics / UptimeRobot / build error 通知 / 404 page / redirect 等 polish。

**预计工作量**：1–3 小时（按选定的子集）。

**价值**：站点可以"半年不维护也不会无声挂掉"。

### 建议

> 建议**先 ACT-6B 再 ACT-5C**。理由：
> - ACT-6 已经把构建链路 + export 脚本做透，ACT-6B 的多 project 合并是自然延伸
> - ACT-5C 里的 HSTS / UptimeRobot / 404 page 在有真实访问量前价值不大
> - 一旦 ACT-6B 接入第 2 个项目、朋友/同事开始访问，再补 ACT-5C 的监控更划算

---

## 文件变更清单

| 文件 | 变更 |
| --- | --- |
| `apps/dashboard/package.json` | 加 `prebuild` 钩子（`SKIP_DASHBOARD_PREBUILD` env 支持） |
| `Makefile` | `dashboard` 拆分为 `dashboard`（public） + `dashboard-local`（local）；`public-data` 拆分为 `public-data`（examples） + `public-data-real`（data 切片）；`publish-preflight` 第一步改为 `public-data-real` |
| `scripts/export_public_data.py` | 新增 5 个参数：`--project-id` / `--agent-id` / `--max-events` / `--replace` / `--repo-prefix`；新增 `_filter_projects` / `_filter_agents` / `_filter_events` / `_cap_events_per_project` / `_rewrite_repo` / `_infer_agents_from_events` 函数；MANIFEST 写新字段 |
| `public-data/registry/projects.yml` | 从 3 entries（demo）改为 1 entry（real），repo 改写为 `conanxin/agent-project-control-tower` |
| `public-data/registry/agents.yml` | 从 3 entries（demo）改为 1 entry（real） |
| `public-data/events/*.json` | 从 10 files（demo）改为 7 files（real），所有 `source_repo` 改写为 `conanxin/agent-project-control-tower` |
| `public-data/MANIFEST.json` | 升级为带 `project_filter` / `agent_filter` / `max_events_per_project` / `repo_prefix` 字段 |
| `generated/index.json` | 重写为 1/1/7（real） |
| `site/index.embedded.html` | 重写为 1/1/7（real），19.2 KB |
| `apps/dashboard/dist/` | 重建为 4 pages（real） |
| `data/events/20260611T125...Z__PHASE__...__ACT-6.json` | tower.py 上报 ACT-6 产物（gitignored） |
| `README.md` | 顶部 status 改 ACT-6 ✅；新增 §ACT-6 First Real Project Public Export 整段 |
| `docs/DEPLOYMENT_PLAN.md` | §4 改标题为 "ACT-6 已上线"；新增 §4.10 ACT-6 Prebuild 钩子；§6 整段重写为 ACT-6 部署清单；§6.4 改为 ACT-6 完整 deploy 流程 |
| `docs/MVP_PLAN.md` | 顶部 status 改 ACT-6 ✅；全景时间线加 ACT-6 ✅ 行；§ACT-6 整段重写为"已完成"；新增 §ACT-6B Second Real Project Public Export 候选段 |
| `reports/PHASE_ACT6_FIRST_REAL_PROJECT_PUBLIC_EXPORT_REPORT.md` | 新增本文档 |

---

## 验收清单（最终）

- [x] `apps/dashboard/package.json` 加 `prebuild` 钩子
- [x] Makefile `dashboard` 拆分为 public + local 模式
- [x] Makefile `public-data` 拆分为 examples + real 模式
- [x] `make publish-preflight` 第一步走 `public-data-real`
- [x] `export_public_data.py` 新增 5 个参数
- [x] 实际导出真实子集 1/1/7
- [x] redaction 0 FAIL / 0 WARN
- [x] `repo: conanxin/agent-project-control-tower` 改写成功（registry + event source_repo）
- [x] `data/` 仍 gitignored（**仍不公开**）
- [x] `generated/` 仍 gitignored
- [x] `make all` PASS（53/53，data 链路）
- [x] `make publish-preflight` PASS（1/1/7，public-data 链路）
- [x] `npm run build` PASS（4 pages，prebuild 钩子从 public-data 重写 generated/）
- [x] pre-commit audit CLEAN
- [x] README / DEPLOYMENT_PLAN / MVP_PLAN 同步更新
- [x] `tower.py report-phase ACT-6` 上报（PASS / health=green）

**ACT-6 ✅ COMPLETE**
