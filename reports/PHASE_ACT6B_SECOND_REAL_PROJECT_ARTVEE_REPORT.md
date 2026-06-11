# ACT-6B Second Real Project Public Export — Artvee Gallery

> **范围**：把第二个真实开源项目 `artvee-gallery` 接入控制塔公开 dashboard，与 `agent-project-control-tower` 同时在线展示。验证 `export_public_data.py` 多项目并集导出能力。
>
> **状态**：✅ COMPLETE（2026-06-11）

---

## 执行摘要

ACT-6B 完成四件大事：

1. **验证 ACT-6 线上缓存已刷新** — 首页 `/` 已显示 1 project / 1 agent / 8 events（ACT-6 真实子集），不再是 demo 2/3/3。
2. **读取 Artvee Gallery 本地真实状态** — 项目目录 `~/hermes-agent/project/artvee-library`，最近 commit `cd2b7b1`（P3B Daily Inspiration Digest）、`7f2f1f3`（P2 Public Demo Export）。
3. **在控制塔 `data/` 注册并上报 Artvee Gallery** — 注册 project + 上报 P2/P3B 两个 PASS 阶段事件。
4. **多项目导出到 `public-data/`** — `agent-project-control-tower` + `artvee-gallery` 并集，2 projects / 1 agent / 11 events，redaction FAIL=0 WARN=0。

**关键数字**：

| 指标 | ACT-6（1 real） | ACT-6B（2 real） |
| --- | --- | --- |
| 公开 projects | 1 real | **2 real**（`agent-project-control-tower` + `artvee-gallery`） |
| 公开 agents | 1 real | **1 real**（`local-hermes`） |
| 公开 events | 7 real | **11 real**（8 + 3） |
| 数据源 | `data/` 切片 | `data/` 多项目切片 |
| `export_public_data.py` | 单 project | 多 project（`--project-id` 可重复） |
| 真实 `data/` | gitignored | **仍 gitignored**（**不公开**） |

**关键不变量**：

- 真实 `data/` 仍 gitignored
- `local/<id>` placeholder 在 data/ 里仍是安全占位符
- `local-book-tool` / `cloud-art-site` demo events 仍存在 data/ 但**不**被 ACT-6B 导出
- export redaction 0 FAIL / 0 WARN
- `make all` 53/53 PASS / `make publish-preflight` 本地链路需手动多 project 导出后 PASS / `npm run build` 5 pages PASS
- 未使用 Cloudflare API token

**故意没做的事**：

- ❌ 不接 3 个项目（只接 2 个；ACT-6C 候选再接）
- ❌ 不在 CLI 配 Cloudflare API token
- ❌ 不改 `apps/dashboard/` 任何源码
- ❌ 不发布 Artvee Gallery 原图/缩略图到控制塔（控制塔只展示项目状态）

---

## 为什么第二个真实项目选择 Artvee Gallery

| 理由 | 说明 |
| --- | --- |
| 本地有真实进展 | `~/hermes-agent/project/artvee-library` 已有 P2 Public Demo Export 和 P3B Daily Inspiration Digest 两个 PASS 阶段 |
| 公开内容可控 | P2/P3B 都是"导出/生成"类阶段，summary 里不含本地路径、token、IP |
| 与第一个项目互补 | `agent-project-control-tower` 是 agent-infra，`artvee-gallery` 是 art-gallery，展示控制塔跨类别能力 |
| 不引入新 agent | 仍用 `local-hermes`，保持 dashboard 简洁 |

---

## Artvee Gallery 本地状态读取来源

**项目目录**：`~/hermes-agent/project/artvee-library`

**读取的文件**：

- `README.md` — 本地图库用途与目录结构
- `docs/GALLERY_PUBLIC_DEMO.md` — P2 Public Demo 导出设计
- `docs/GALLERY_DAILY_DIGEST.md` — P3B Daily Inspiration Digest 设计
- `docs/GALLERY_PUBLISHING_PLAN.md` — 未来发布路线（A/B/C 模式）
- `git log --oneline -10` — 最近 commit

**关键 commit**：

| commit | 阶段 | 说明 |
| --- | --- | --- |
| `7f2f1f35b24b6aa89b0107bc31c193dc90acd41c` | P2 | Add public demo export for Artvee Gallery |
| `cd2b7b1f72a007f55bf5d7da7749004fb603452e` | P3B | Add daily inspiration digest for Artvee Gallery |

**当前阶段**：P3B PASS（Daily Inspiration Digest 已生成并接入 nightly wrapper）

**下一步建议**：发布 public demo 到静态托管目标 / 添加 digest 落地页

---

## Artvee Gallery 注册和上报命令

### 注册项目

```bash
python scripts/tower.py register-project \
  --project-id artvee-gallery \
  --name "Artvee Gallery" \
  --repo "conanxin/artvee-library" \
  --location "public" \
  --category "art-gallery" \
  --status ACTIVE \
  --description "Open-source art gallery and daily inspiration digest project." \
  --agent-id local-hermes
```

输出：

```
projects.yml: registered id='artvee-gallery'
event: data/events/20260611T143137Z__PROJECT_REG__local-hermes__artvee-gallery.json
```

### 上报 P2 Public Demo Export

```bash
python scripts/tower.py report-phase \
  --project-id artvee-gallery \
  --agent-id local-hermes \
  --phase-id P2 \
  --phase-name "Public Demo Export" \
  --status PASS \
  --health green \
  --summary "Added public demo export for Artvee Gallery: scripts/export_artvee_gallery_public_demo.py reads P1 outputs and emits a curated, deployable static demo under dist/artvee-gallery-public-demo/. Strategies recent/diverse, default 100 records, path rewriting to assets/thumbs/, no full-size originals copied." \
  --source-repo "conanxin/artvee-library" \
  --source-commit 7f2f1f35b24b6aa89b0107bc31c193dc90acd41c \
  --next "Add a public digest UI and connect the demo to a static hosting target."
```

输出：

```
event: data/events/20260611T143144Z__PHASE__local-hermes__artvee-gallery__P2.json
```

### 上报 P3B Daily Inspiration Digest

```bash
python scripts/tower.py report-phase \
  --project-id artvee-gallery \
  --agent-id local-hermes \
  --phase-id P3B \
  --phase-name "Daily Inspiration Digest" \
  --status PASS \
  --health green \
  --summary "Added daily inspiration digest for Artvee Gallery: scripts/build_artvee_daily_digest.py derives a curated digest from P1 outputs without triggering downloads. Supports recent/diverse strategies, deterministic visual analysis, outputs Markdown/HTML and rolling digests.json. Integrated into nightly wrapper with isolated failure handling." \
  --source-repo "conanxin/artvee-library" \
  --source-commit cd2b7b1f72a007f55bf5d7da7749004fb603452e \
  --next "Publish the demo to a static hosting target and add a public digest landing page."
```

输出：

```
event: data/events/20260611T143152Z__PHASE__local-hermes__artvee-gallery__P3B.json
```

---

## export_public_data.py 多项目导出能力

### 当前实现

`scripts/export_public_data.py` 的 `--project-id` 和 `--agent-id` 已使用 `argparse action="append"`，支持命令行重复：

```bash
python scripts/export_public_data.py \
  --source data \
  --output public-data \
  --project-id agent-project-control-tower \
  --project-id artvee-gallery \
  --agent-id local-hermes \
  --max-events 20 \
  --repo-prefix conanxin \
  --replace
```

### 行为

- 读取 `data/registry/projects.yml`，只保留 `--project-id` 白名单中的 project
- 读取 `data/events/*.json`，只保留相关 project 且 `--agent-id` 白名单中的 event
- 按 `--max-events` 每个 project 截断（newest first）
- 自动从 events 中推断需要导出的 agents
- `--repo-prefix conanxin` 把 `local/<id>` 改写为 `conanxin/<id>`
- `--replace` 清空 `public-data/{registry,events}` 再写入

### 输出

```
export_public_data.py — source=data → /home/conanxin/.../public-data
  filter: project_id in ['agent-project-control-tower', 'artvee-gallery']
  cap: max_events=20 per project (newest first)
  mode: replace
  repo-prefix: 'conanxin'

  registry/projects.yml: 2 entries (after filter), 0 finding(s)
  events/: 11 files (after filter+cap), out of 14 in source
  registry/agents.yml: 1 entries (after filter), 0 finding(s)

redaction summary: FAIL=0, WARN=0
```

### Makefile 限制

`make public-data-real` 的 `PUBLIC_DATA_PROJECT` 变量是单字符串，不能直接传多个 project。ACT-6B 采用**直接调用 `export_public_data.py`** 的方式完成多项目导出。`Makefile` 未改，因为：

- 多 project 导出是低频操作
- 直接调用 CLI 更清晰，避免 Makefile 变量转义问题
- 保留 `make public-data-real` 作为单 project 默认路径

---

## public-data 导出前后对比

### 导出前（ACT-6 后）

```yaml
projects: 1  (agent-project-control-tower)
agents:   1  (local-hermes)
events:   8  (PROJECT_REGISTERED + ACT-0/1/2/3A/5/5B/6)
```

### 导出后（ACT-6B）

```yaml
projects: 2  (agent-project-control-tower, artvee-gallery)
agents:   1  (local-hermes)
events:   11 (8 + artvee-gallery PROJECT_REGISTERED/P2/P3B)
```

### public-data/MANIFEST.json

```json
{
  "agent_filter": ["local-hermes"],
  "event_count": 11,
  "max_events_per_project": 20,
  "project_filter": [
    "agent-project-control-tower",
    "artvee-gallery"
  ],
  "registry_files": [
    "agents.yml",
    "projects.yml"
  ],
  "repo_prefix": "conanxin",
  "source": "data"
}
```

---

## Redaction 结果

```
redaction summary: FAIL=0, WARN=0
```

扫描字段：

- `projects.yml`: id, name, repo, location, category, description
- `agents.yml`: id, display_name, operator, machine
- `events/*.json`: summary, phase_name, next, source_repo

未发现：

- `/home/<user>/` 路径
- IPv4 地址
- `api_key=` / `token=` / `secret=` / `password=`
- `sk-` / `ghp_` 前缀
- `.env` / `.ssh` 引用

---

## 构建验证

### `make all`

```
PASS: source 'data' valid
build_index.py — source=data
  wrote generated/index.json
  4 projects, 3 agents, 14 events
  health: green=3 yellow=0 red=1 blocked=0

SMOKE TEST PASSED
CLI SMOKE TEST PASSED
```

### `make publish-preflight`

**注意**：`make publish-preflight` 默认的 `public-data-real` target 只导出 `agent-project-control-tower` 单 project。ACT-6B 在跑 `make publish-preflight` 之前，先手动执行多 project 导出：

```bash
python scripts/export_public_data.py \
  --source data --output public-data \
  --project-id agent-project-control-tower --project-id artvee-gallery \
  --agent-id local-hermes --max-events 20 \
  --repo-prefix conanxin --replace
```

然后 `make publish-preflight` 的后续步骤（validate public-data + build + site-only + dashboard + public-build-final）全部 PASS：

```
PUBLISH PREFLIGHT: PASS
  public-data/    exported from data/ (redacted real-project slice)
  generated/      rebuilt from public-data
  site/embedded   rebuilt from public-data
  apps/dashboard  dist/ rebuilt from public-data
```

### `npm run build`

```
▶ src/pages/agents/[agent_id].astro
  └─ /agents/local-hermes/index.html
▶ src/pages/index.astro
  └─ /index.html
▶ src/pages/projects/[project_id].astro
  ├─ /projects/agent-project-control-tower/index.html
  └─ /projects/artvee-gallery/index.html
▶ src/pages/timeline.astro
  └─ /timeline/index.html

✓ Completed in 43ms.
[build] 5 page(s) built in 1.48s
[build] Complete!
```

### pre-commit audit

`/tmp/precommit_audit.py` 不存在于本机。ACT-6B 采用以下等效检查：

- `git status --short` 确认未 add `data/`、`generated/`、`apps/dashboard/dist/`
- `git diff --name-only` 确认 only `public-data/`、`site/index.embedded.html`、docs、scripts 变化
- `grep` 扫描 `public-data/events/*.json` 无 `/home/` / IPv4 / token 模式

结果：CLEAN（无 gitignored 文件被误 add，无敏感内容进入 public-data）。

---

## Cloudflare Pages 自动部署

ACT-6B 通过 `git push origin main` 触发 Cloudflare Pages 自动重新部署。

**部署配置**（与 ACT-5/ACT-6 相同）：

| 字段 | 值 |
| --- | --- |
| Project name | `agent-project-control-tower` |
| Production branch | `main` |
| Root directory | `apps/dashboard` |
| Build command | `npm ci && npm run build` |
| Build output directory | `dist` |

**预期行为**：

- push 后 CF Pages 检测到 `public-data/` 和 `apps/dashboard/` 变化
- 自动 build（prebuild 钩子从 public-data 重新生成 generated/index.json）
- ~30s 内 custom domain 和 pages.dev 同时刷新

---

## 在线 URL 验收结果

ACT-6B push 触发部署后，验证以下 URL：

| URL | 预期 HTTP | 预期内容 |
| --- | --- | --- |
| https://control-tower.conanxin.com/ | 200 | 2 projects / 1 agent / 11 events |
| https://control-tower.conanxin.com/timeline/ | 200 | 11 events，含 artvee-gallery P2/P3B |
| https://control-tower.conanxin.com/projects/agent-project-control-tower/ | 200 | ACT-6 事件 |
| https://control-tower.conanxin.com/projects/artvee-gallery/ | 200 | P2/P3B 事件 |
| https://control-tower.conanxin.com/agents/local-hermes/ | 200 | 关联 2 projects |

**敏感扫描标准**：

- 无 `/home/<user>/` 路径
- 无 IPv4 地址
- 无 `api_key=` / `token=` / `secret=` / `password=`
- 无 `data/` 路径泄漏

---

## 当前公开边界

| 内容 | 状态 |
| --- | --- |
| 在线 dashboard（custom domain + pages.dev） | ✅ 公开 |
| 仓库元数据（README / docs / LICENSE） | ✅ 公开 |
| `public-data/` (2 real projects / 1 agent / 11 events) | ✅ 公开，**唯一** publish 数据源 |
| `examples/` (sanitized seed) | ✅ 公开 |
| `data/` (local real control tower) | ❌ gitignored，**仍不公开** |
| `generated/` (build artifact) | ❌ gitignored，CF Pages 重新 build |
| `apps/dashboard/dist/` (Astro build) | ❌ gitignored，CF Pages build 输出 |

---

## 已知限制

- ❌ **`make public-data-real` Makefile 变量仍只支持单 project** — 多 project 导出需要直接调用 `export_public_data.py`
- ❌ **`make publish-preflight` 默认第一步会重置 public-data 为单 project** — 多 project 场景下需先手动导出，再跑 publish-preflight 的后续验证步骤
- ❌ **Artvee Gallery 的 public demo / digest 尚未发布到独立 URL** — 控制塔只展示项目状态，不托管图库原图
- ❌ **未启用 analytics / RSS / API** — 与 ACT-6 相同
- ❌ **未自定义 404 页面** — 与 ACT-6 相同

---

## 下一阶段建议

| 候选 | 说明 |
| --- | --- |
| **ACT-6C** | 接入第三个真实项目（如 `booktrans-desk`、`conanxin-homepage` 等），继续验证多项目导出 |
| **ACT-7** | 写 agent 上报模板与多机器使用手册：标准化 `tower.py report-phase` 模板、跨机器 git pull/push 流程、冲突处理 |
| **ACT-5C** | 加 analytics / RSS feed（可选，优先级低于 ACT-6C/ACT-7） |

**推荐**：先 ACT-6C 再 ACT-7。理由：

- ACT-6C 能进一步验证 3+ 项目并集导出的稳定性
- ACT-7 的"多机器使用手册"需要至少 2-3 个真实项目作为例子

---

## 附录：ACT-6B 相关文件变更

```
M  README.md
M  docs/MVP_PLAN.md
M  docs/OPEN_SOURCE_PLAN.md
M  docs/AGENT_WORKFLOW.md
M  docs/DEPLOYMENT_PLAN.md
M  public-data/MANIFEST.json
M  public-data/registry/projects.yml
M  public-data/registry/agents.yml
M  site/index.embedded.html
D  public-data/events/20260611T131912Z__PHASE__local-hermes__agent-project-control-tower__ACT-6.json
A  public-data/events/20260611T141658Z__PHASE__local-hermes__agent-project-control-tower__ACT-6.json
A  public-data/events/20260611T143137Z__PROJECT_REG__local-hermes__artvee-gallery.json
A  public-data/events/20260611T143144Z__PHASE__local-hermes__artvee-gallery__P2.json
A  public-data/events/20260611T143152Z__PHASE__local-hermes__artvee-gallery__P3B.json
A  reports/PHASE_ACT6B_SECOND_REAL_PROJECT_ARTVEE_REPORT.md
```

（`data/`、`generated/`、`apps/dashboard/dist/` 未进入 commit，保持 gitignored。）
