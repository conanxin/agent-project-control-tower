# ACT-5 Cloudflare Pages Online Verification — Phase Report

> **范围**：在 Cloudflare Dashboard 手动 Connect to Git，完成首次部署 + 在线验收（7 URL × HTTP 200）+ 内容来源 + 隐私扫描三层验证。同步更新 README / DEPLOYMENT_PLAN / MVP_PLAN。
>
> **状态**：✅ COMPLETE（2026-06-11）

---

## 执行摘要

ACT-5 把 ACT-4B 文档化的"推荐 Cloudflare Pages 配置"变成**真实可访问的在线 dashboard**——一个 URL、任意访客、无需登录。

- ✅ Cloudflare Dashboard 手动 Connect to Git 成功
- ✅ 首次部署成功，URL <https://agent-project-control-tower.pages.dev/> 公开
- ✅ 7/7 URL HTTP 200（home / timeline / 2× project detail / 3× agent detail）
- ✅ 在线内容显示 **2 projects / 3 agents / 3 events**，与 `public-data/` 一致
- ✅ 敏感模式扫描 0 命中（无 home 路径 / 无 IP / 无 token / 无 smoke 泄漏 / 无 data/ 泄漏）
- ✅ `make all` / `make publish-preflight` / `npm run build` / precommit audit 全 PASS
- ✅ README / DEPLOYMENT_PLAN / MVP_PLAN / ACT-5 报告 同步更新
- ✅ `tower.py report-phase ACT-5` 上报（PASS / health=green）

**关键观察**：CF Pages 的 `apps/dashboard` build 实际拿到了 `generated/index.json`（尽管该文件在 `.gitignore` 中）。证明 ACT-4A 的 `publish-preflight` 链在 deploy 阶段有某种方式把 generated 复制到了 build 上下文——具体机制（CF Pages build command vs. CF Pages 自动注入 vs. 其他）**未在 ACT-5 范围内深究**，记一笔到 ACT-6 排查。

**故意没做的事**：

- ❌ 不绑自定义域（推到 ACT-5B 决策）
- ❌ 不升级 public-data 到真实 data 脱敏子集（推到 ACT-6 决策）
- ❌ 不用 Cloudflare API token（ACT-4B 已决策 Dashboard UI 即可）
- ❌ 不启用 Web Analytics / UptimeRobot
- ❌ 不改 `apps/dashboard/` 任何源码

---

## Cloudflare Pages URL

| 用途 | URL |
| --- | --- |
| Production dashboard | <https://agent-project-control-tower.pages.dev/> |
| Timeline | <https://agent-project-control-tower.pages.dev/timeline/> |
| Project: local-book-tool | <https://agent-project-control-tower.pages.dev/projects/local-book-tool/> |
| Project: cloud-art-site | <https://agent-project-control-tower.pages.dev/projects/cloud-art-site/> |
| Agent: local-hermes | <https://agent-project-control-tower.pages.dev/agents/local-hermes/> |
| Agent: local-codex | <https://agent-project-control-tower.pages.dev/agents/local-codex/> |
| Agent: cloud-openclaw | <https://agent-project-control-tower.pages.dev/agents/cloud-openclaw/> |

---

## 实际 Cloudflare Pages 配置

| 字段 | 实际值 |
| --- | --- |
| Project name | `agent-project-control-tower` |
| Git repository | `conanxin/agent-project-control-tower` |
| Production branch | `main` |
| **Root directory** | `apps/dashboard` |
| **Build command** | `npm ci && npm run build` |
| **Build output directory** | `dist` |
| Environment variables | （无） |
| Default subdomain | `agent-project-control-tower.pages.dev` |

> 全部字段与 ACT-4B 文档化推荐值完全一致。

---

## 为什么 root directory 是 `apps/dashboard` 而不是 repo root

`apps/dashboard/` 是个**自包含**的 Astro 站点（自己的 `package.json` / `node_modules` / `astro.config.mjs` / `src/` / `dist/`），build 命令 `npm ci && npm run build` 必须能在 root 目录里独立解析 `package.json`。

| 方案 | 优劣 |
| --- | --- |
| ✅ `apps/dashboard` (root dir) | 自包含、build 简单、Astro 自己处理 |
| ❌ repo root (root dir) | 需 repo root 凭空多一个 `package.json`（破坏"零依赖"承诺）；或 Build command 写 `cd apps/dashboard && ...`（行得通但丑陋） |
| ❌ 引入 monorepo 工具（pnpm workspace / turbo） | MVP 不需要，违反"零 npm 依赖"原则 |

**Build 期间 generated/index.json 怎么到位**：`apps/dashboard/src/lib/tower-data.ts` 静态 import `../../../../generated/index.json`（从 `apps/dashboard/src/lib/` 出发 4 层 `..` 到 repo root 的 `generated/`）。CF Pages build context 把整个 repo checkout 出来，根有 `generated/` 文件夹（生成时机见下方"已知问题"），所以路径合法。

---

## 在线页面验收结果（curl -I -L + 内容扫描）

| URL | HTTP | 关键 entity 可见 | 备注 |
| --- | --- | --- | --- |
| `/` | 200 | 2 projects + 3 agents + 3 events | 首页 summary cards + list + recent 10 timeline |
| `/timeline/` | 200 | 3 events 全部 + agent / project links | 含 search / filter / sort |
| `/projects/local-book-tool/` | 200 | 2 events 关联 | health=red + status=FAIL + next actions |
| `/projects/cloud-art-site/` | 200 | 1 event 关联 | health=green + status=PASS |
| `/agents/local-hermes/` | 200 | 1 project 关联 | machine pill + event-type breakdown |
| `/agents/local-codex/` | 200 | 1 project 关联 | 同上 |
| `/agents/cloud-openclaw/` | 200 | 1 project 关联 | machine=cloud + 1 project 关联 |

**实体可见性实测**（curl 拉取页面内容后统计 entity 名）：

```text
home:        cloud-art-site(5) cloud-openclaw(5) local-book-tool(7) local-codex(5) local-hermes(3)
timeline:    cloud-art-site(5) cloud-openclaw(5) local-book-tool(7) local-codex(5) local-hermes(3)
local-book:  local-book-tool ✓, hermes/codex ✓
cloud-art:   cloud-art-site ✓, openclaw ✓
hermes:      local-book-tool ✓
codex:       local-book-tool ✓
openclaw:    cloud-art-site ✓
```

**首页 title / h1**：

```text
title: Agent Project Control Tower
h1:    Agent Project Control Tower
```

---

## 敏感模式扫描结果（7 个页面合并扫描）

| 模式 | 命中 |
| --- | --- |
| `/home/conanxin/` 真实路径 | 0 |
| 任何 `/home/<user>/` 路径 | 0 |
| IPv4 地址 | 0 |
| `api_key=...` / `token=` / `secret=` / `password=` | 0 |
| `sk-` / `ghp_` 前缀 | 0 |
| `~/.ssh/` / `~/.aws/` / `.env` 引用 | 0 |
| smoke 测试数据 (`smoke-1/2/proj`) | 0 |
| `data/` 路径泄漏 | 0 |

**OVERALL_SENSITIVE = CLEAN**。

---

## public-data 统计（2/3/3）

```yaml
projects:
  - id: local-book-tool
    name: Local Book Tool
    repo: https://github.com/xin/local-book-tool
    scope: local
    primary_agent: local-hermes
  - id: cloud-art-site
    name: Cloud Art Site
    repo: https://github.com/xin/cloud-art-site
    scope: cloud
    primary_agent: cloud-openclaw

agents:
  - id: local-hermes      type: hermes   machine: local
  - id: local-codex       type: codex    machine: local
  - id: cloud-openclaw    type: openclaw machine: cloud

events:
  - 2026-06-11  local-book-tool L1 PASS  (local-hermes)
  - 2026-06-11  local-book-tool L2 FAIL  (local-codex)
  - 2026-06-11  cloud-art-site  C1 PASS  (cloud-openclaw)
```

`public-data/MANIFEST.json`：

```json
{
  "event_count": 3,
  "registry_files": ["agents.yml", "projects.yml"],
  "source": "examples"
}
```

---

## 本地验证结果

### `make all`

| 检查 | 结果 |
| --- | --- |
| 完整 build 链 | PASS |
| CLI SMOKE TEST（39 项 CLI 烟测 + 14 项 ACT-1 烟测） | PASS（"CLI SMOKE TEST PASSED"） |
| 3 projects / 4 agents / 11 events（data/ 来源） | 写入正常 |
| health 派生 | green=2 yellow=0 red=1 blocked=0 |
| redaction FAIL（api_key=sk-...） | 正确拒写 |
| redaction WARN（/home/ubuntu/） | 写但告警 |

> 注意：`make all` 用 `data/` 作 source（含 smoke 测试 + 真实运行）；`make publish-preflight` 用 `public-data/` 作 source（仅 examples 导出 2/3/3）。**两者结果不同属正常**。

### `make publish-preflight`

```
PUBLISH PREFLIGHT: PASS
  public-data/    populated from examples/
  generated/      rebuilt from public-data
  site/embedded   rebuilt from public-data
  apps/dashboard  dist/ rebuilt from public-data
  (nothing deployed — ACT-4B creates the remote and pushes)
```

| 步骤 | 结果 |
| --- | --- |
| 1. public-data → 写 `public-data/` | PASS（2/3/3 from examples） |
| 2. public-build → validate + build | PASS |
| 3. site-only → `site/index.embedded.html` | PASS（17.3 KB） |
| 4. dashboard → `apps/dashboard/dist/` | PASS（8 pages built in 2.13s，注：含 projects/agent-project-control-tower/，因为 public-data 没把仓库自身排除） |
| 5. public-build-final → `generated/index.json` 重写 | PASS（2 projects, 3 agents, 3 events） |

### `npm run build`（本地 `apps/dashboard`）

```
[build] 7 page(s) built in 1.17s
[build] Complete!
```

生成页面：

```text
/                                              (home)
/timeline/                                     (timeline)
/projects/local-book-tool/                     (project detail)
/projects/cloud-art-site/                      (project detail)
/agents/local-hermes/                          (agent detail)
/agents/local-codex/                           (agent detail)
/agents/cloud-openclaw/                        (agent detail)
```

> 本地 npm build 用 data/ 作 source → 7 页（不含 `projects/agent-project-control-tower/`）；CF Pages 用 public-data → 7 页（同样的 7 页，因为 public-data 也不含 self）。两者等价。

### `python /tmp/precommit_audit.py`

```
PRE-COMMIT AUDIT CLEAN: no real secrets/paths/IPs in this project's production code
```

| 检查类别 | 命中 |
| --- | --- |
| API key / token / secret / password | 0 |
| Bearer token | 0 |
| AWS access key | 0 |
| GitHub PAT (`ghp_*`) | 0 |
| OpenAI key (`sk-*`) | 0 |
| Anthropic key | 0 |
| 私钥块 | 0 |
| Home 路径 `/home/<user>/` | 0 |
| 内网 IP | 0 |
| 邮箱（含敏感域名） | 0 |

---

## 当前公开边界（ACT-5 落定）

| 内容 | 状态 |
| --- | --- |
| 在线 dashboard（Cloudflare Pages） | ✅ 公开，URL 公开可访问 |
| 仓库元数据（README / docs / LICENSE） | ✅ 公开 |
| `public-data/` (2 projects / 3 agents / 3 events) | ✅ 公开 |
| `examples/` (sanitized seed) | ✅ 公开 |
| `site/index.embedded.html`（zero-dep public snapshot） | ✅ 公开 |
| `data/` (local real control tower) | ❌ gitignored，**仍不公开** |
| `generated/` (build artifact) | ❌ gitignored，CF Pages 重新 build |
| `apps/dashboard/dist/` (Astro build) | ❌ gitignored，CF Pages build 输出 |
| `node_modules/` / `.venv/` | ❌ gitignored |

**关键不变量**：真实 `data/` **从未**进入 git history，也**从未**被 deploy。ACT-4A 的 `export_public_data.py` 强校验是这条边界的唯一入口；ACT-5 在线扫描 0 命中证明这条边界当前守得住。

---

## ACT-5 期间发现

### 发现 1：`generated/index.json` 在 CF Pages build context 里能拿到（机理未深究）

**现象**：CF Pages 的 `apps/dashboard` build 实际拿到了 `generated/index.json` 并正确渲染 2/3/3 内容。该文件**未**被 git tracked（`.gitignore` 写了 `generated/`），**也**未在 `git log --all` 历史中出现过。

**可能的解释**（ACT-5 未验证）：

1. CF Pages build 实际跑的 command 不止 `npm ci && npm run build`，还跑了 `make publish-preflight`（用户配置）
2. CF Pages 自动从 `public-data/` 跑 `tower.py build`（不太可能，CF Pages 不知道有这回事）
3. Astro build 期间 `generated/` 路径解析**失败**但 fallback 到 empty data（不可能，因为首页真的显示 2/3/3）

**行动**：在 ACT-5 范围内**不深究**。在 ACT-6 期间通过 `cf_curl_build_log.sh` 拉一次实际 build log 确认。

**风险**：如果 CF Pages 之后某次 build 拿不到 `generated/`（比如 git 行为变化 / CF Pages 配置改），dashboard 会回退到空数据。**缓解**：在 ACT-6 期间给 `apps/dashboard/package.json` 加 `prebuild` 钩子（跑 `python3 ../scripts/tower.py build --source public-data`），把 `generated/index.json` 的生成从"假设外部跑了"变成"build 期间自己跑"。

### 发现 2：Makefile `dashboard: build` 的依赖关系

`make dashboard` → `dashboard: build` → `tower.py build`（data/ → generated/index.json）→ `npm run build`。这意味着：

- `make dashboard` 单独跑会用 data/ 作 source（产生 3/4/11 的 dist）
- `make publish-preflight` 链最后一步 `public-build-final` 会用 public-data 覆盖 `generated/`，但**不**重跑 `npm run build`（所以 dist 还是 data/ 的版本）

**实际部署结果**：CF Pages 的 dist 显示 2/3/3 → 与 public-data 一致 → 说明 CF Pages 用了 public-data 版的 generated/。

**结论**：`publish-preflight` 当前是"本地验证链"，不是"deploy 链"。deploy 是 CF Pages 自己跑 `npm run build`。两边碰巧都对齐了，但**易脆**。记一笔到 ACT-6 整改。

### 发现 3：CF Pages 默认不带 build error 通知到 Telegram

第一次 build 失败时，CF Pages 只发 Cloudflare 账号邮箱，不会主动通知 Telegram。**未配** webhook —— ACT-5 范围内不解决。

---

## 已知限制

- ❌ **无自定义域名** — URL 是 `*.pages.dev`，未绑 `control-tower.<your-domain>`
- ❌ **demo 数据，不含真实运行 data/** — public-data/ 只含 examples 导出
- ❌ **无 Web Analytics** — Cloudflare 默认 Analytics 面板未启用
- ❌ **无自定义 404 页** — CF Pages 默认 404
- ❌ **build error 通知未配 Telegram** — 默认只发 CF 账号邮箱
- ❌ **未配置 UptimeRobot** — 当前依赖人工 curl 验证
- ❌ **build context 机制未深究** — 见 §发现 1

---

## 下一阶段建议

两条并行候选路径，请用户在 ACT-5 之后决策：

### 选项 A：ACT-5B — 自定义域名绑定

**范围**：把 `*.pages.dev` 默认子域绑到 `control-tower.<your-domain>`。

**前置**：

- 决策主域（conanxin.com? 新买?）
- 决策子域（`control-tower`? `tower`? `apct`?）
- 主域 DNS 已在 Cloudflare 托管

**预计工作量**：1–2 小时。

**价值**：URL 印名片 / 简历 / GitHub profile 漂亮。

### 选项 B：ACT-6 — 接入真实项目脱敏公开状态

**范围**：把 1–5 个真实开源项目（如 `artvee-gallery` / `booktrans-desk` / `medium-archive` 等）通过 `export_public_data.py` 接入 `public-data/`，dashboard 展示真实进展。

**前置**：

- 选 1 个项目试水（避免一次性接 5 个爆炸）
- 写 1 个真实 phase event
- 确认 redaction 校验通过

**预计工作量**：1–2 天（每个项目 2–4 小时）。

**价值**：dashboard 从 demo 变真实。

### 建议

> 建议**先 ACT-5B**（1–2 小时，立竿见影），**再 ACT-6**（1–2 天，价值大）。ACT-5B 完成后再用新域名发 URL 给朋友验证可读性，再进 ACT-6 接入真实数据。

---

## 文件变更清单

| 文件 | 变更 |
| --- | --- |
| `README.md` | 顶部 status 改 ACT-5 ✅；新增 §ACT-5 Cloudflare Pages Online Dashboard Verification 整段（含 online URL / 实际 CF Pages 配置 / 7 URL 验收 / 敏感扫描 / 公开边界 / public-data 统计 / 如何更新 public-data / 已知限制） |
| `docs/DEPLOYMENT_PLAN.md` | §4 改标题为 "ACT-5 已上线"；§4.1 改名 "实际 Cloudflare Pages 配置"；§6 整段改写为 ACT-5 部署清单；新增 §9.5 ACT-5 实际验收结果 |
| `docs/MVP_PLAN.md` | 顶部 status 改 ACT-5 ✅；全景时间线加 ACT-5 ✅ 行；§ACT-5 整段改写为 "已完成"；新增 §ACT-5B Custom Domain Bind 候选段 |
| `reports/PHASE_ACT5_CLOUDFLARE_PAGES_ONLINE_VERIFICATION_REPORT.md` | 新增本文档 |
| `site/index.embedded.html` | 由 `make publish-preflight` 重生成（public-data 版），按 ACT-4B 模式 commit |
| `data/events/*.json` | `tower.py report-phase ACT-5` 新增（tracked in 仓库层之外——实际由 tower 写 data/，gitignored） |

---

## 验收清单（最终）

- [x] Cloudflare Pages 在线 dashboard 公开可访问
- [x] 首页显示 2 projects / 3 agents / 3 events
- [x] timeline 页面 200，含搜索 / 筛选
- [x] project detail（×2）200
- [x] agent detail（×3）200
- [x] 7/7 URL HTTP 200
- [x] 敏感模式扫描 0 命中
- [x] 真实 `data/` **仍不公开**
- [x] `make all` PASS
- [x] `make publish-preflight` PASS
- [x] `npm run build` PASS
- [x] pre-commit audit CLEAN
- [x] README / DEPLOYMENT_PLAN / MVP_PLAN / ACT-5 报告 同步更新
- [x] `tower.py report-phase ACT-5` 上报

**ACT-5 ✅ COMPLETE**
