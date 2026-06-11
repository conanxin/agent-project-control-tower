# Deployment Plan

> 怎么把"Git 仓库里的 events"变成"任何浏览器都能看的 dashboard"。
> **当前（ACT-4A 之后）**：所有 CI 已写好、文档已就位。**仍未**创建远程仓库、**未** push、**未**部署。下一阶段 ACT-4B 才执行。

## 0. 设计判断

控制塔的部署是**完全静态**的：

- 没有任何 server-side 逻辑
- 没有数据库
- 没有用户系统
- 部署目标：把 `apps/dashboard/dist/` 放到一个静态托管平台

### 平台候选

| 平台 | 优点 | 缺点 | 推荐度 |
| --- | --- | --- | --- |
| **Cloudflare Pages** | 免费额度大、全球 CDN、子域名绑定简单、preview deploy 强 | 配置文件语法专属 | ⭐⭐⭐⭐⭐ |
| **GitHub Pages** | 零配置、跟仓库绑定 | 不能 preview、慢、需 public repo | ⭐⭐⭐ |
| **Netlify** | 类同 Cloudflare | 配额较少 | ⭐⭐⭐ |
| **Vercel** | 类同 Cloudflare | 偏 JS 框架导向 | ⭐⭐⭐ |
| **自托管（Caddy/Nginx）** | 完全可控 | 要自己维护 HTTPS、CDN | ⭐ |

**首选 Cloudflare Pages**——免费 + CDN + 国内访问体验好。
**备选 GitHub Pages**——如果不想再多一个 Cloudflare 账户。

## 1. 当前数据职责划分（ACT-4A 落定）

| 目录 | 角色 | 是否 tracked | 谁读 |
| --- | --- | --- | --- |
| `data/` | 本地真实控制塔数据 | ❌ gitignored | 本地 `tower.py` |
| `examples/` | 脱敏示例数据 / seed | ✅ tracked | `make seed`、CI smoke test |
| `public-data/` | 准备发布的脱敏快照 | ✅ tracked | 公开 dashboard |
| `generated/` | 构建产物（index.json） | ❌ gitignored | `apps/dashboard/dist/` 静态 import |
| `site/index.embedded.html` | 离线双击打开的快照 | ✅ tracked | 离线浏览 / 邮件附件 / CI artifact |
| `apps/dashboard/dist/` | Astro build 输出 | ❌ gitignored | Cloudflare Pages / GitHub Pages |

**关键不变量**：

1. `data/` 永远不进入公开仓库——可能含本地真实路径、token、IP
2. `public-data/` 是**唯一**可发布数据源——必须经过 `scripts/export_public_data.py` 自动 redaction
3. `generated/index.json` 是**唯一** dashboard 数据源——可由 `data/` 或 `public-data/` 重建
4. `site/index.embedded.html` 是 `generated/index.json` 的离线副本

## 2. ACT-4A 本地验证流程

在 push GitHub 之前，ACT-4A 已经把所有路径在本地验证过：

```bash
# 零依赖回归（任何机器任何时候）
make all

# 公开数据出口 + dashboard 全链路
make publish-preflight
# 内部步骤：
#   1. public-data     → export_public_data.py 从 examples 写到 public-data/
#   2. public-build    → validate + build 跑 public-data → generated/index.json
#   3. site-only       → build_embedded_site.py 读 generated/ 写 site/embedded
#   4. dashboard       → npm run build → apps/dashboard/dist/
```

`make publish-preflight` 跑完后，**不部署任何东西**——只确认"如果 push 上去、CI 跑出来会是什么样"。

## 3. GitHub Actions CI（已写）

`.github/workflows/ci.yml` 在 push / PR to `main` 触发，**3 个 job**：

| Job | 干什么 | 依赖 |
| --- | --- | --- |
| `zero-dep-acceptance` | `make all`（validate + build + testsmoke + clismoke） | — |
| `astro-dashboard` | `make dashboard`（npm ci + npm run build） | needs zero-dep-acceptance |
| `publish-preflight` | `make publish-preflight`（public-data → generated → embed → astro） | needs zero-dep-acceptance |

每个 job 上传 artifact 7 天保留——`generated/index.json` (data) / `dashboard-dist` / `public-data-manifest` / `generated/index.json` (public) / `site-embedded-public`。

**为什么** ACT-4A **不**自动部署到 Pages：

- 公开数据策略还没最终确认——examples 是占位数据
- 用户对 deploy target（Cloudflare vs GitHub Pages）还没决策
- 自动 deploy 会让 "push 一个 typo" → 公开站点行为异常

## 4. Cloudflare Pages 方案（**ACT-6 已上线** —— public data 升级为真实子集 1/1/7）

> ACT-4B 决策：使用 Cloudflare Pages。仓库 `conanxin/agent-project-control-tower` 已 push。
> **ACT-5 已完成**：首次部署到 `*.pages.dev`。
> **ACT-5B 已完成**：custom domain `control-tower.conanxin.com` 绑定并验收。
> **ACT-6 已完成**：公开数据从 demo `examples/` 2/3/3 升级为 `data/` 真实子集 1/1/7。
>
> - **主入口（custom domain）**：<https://control-tower.conanxin.com/>
> - **备入口（pages.dev fallback）**：<https://agent-project-control-tower.pages.dev/>
> - 两个 URL 服务**同一份** dist
> - 首次 build command：`npm ci && npm run build`（在 `apps/dashboard/` root dir）
> - **ACT-6 关键改进**：`npm run build` 现在**自动**从 public-data 重新生成 `generated/index.json`（prebuild 钩子），CF Pages build 不再依赖外部先生成 generated/
> - 部署时间：~30s（CF Pages 首次 build + deploy）

### 4.1 实际 Cloudflare Pages 配置（ACT-5 落定）

| 字段 | 值 |
| --- | --- |
| Project name | `agent-project-control-tower` |
| Git repository | `conanxin/agent-project-control-tower` |
| Production branch | `main` |
| **Root directory** | `apps/dashboard` |
| **Build command** | `npm ci && npm run build` |
| **Build output directory** | `dist` |
| Environment variables | （无必需变量） |
| Default subdomain | `agent-project-control-tower.pages.dev` |

**关键点**：

- Root directory 设 `apps/dashboard` —— 让 Cloudflare 直接在该子目录跑 npm 命令
- Build command 不需要 `cd apps/dashboard &&` —— 因为 root 已经在那
- Build output directory 是 `dist` 而不是 `apps/dashboard/dist` —— 因为是相对 root 而言

### 4.2 备选配置（如果不想用 Root directory 字段）

如果 Cloudflare Pages 的 Root directory 留空，指向 repo root：

| 字段 | 值 |
| --- | --- |
| Project name | `agent-project-control-tower` |
| Git repository | `conanxin/agent-project-control-tower` |
| Production branch | `main` |
| **Root directory** | （留空 = repo root） |
| **Build command** | `cd apps/dashboard && npm ci && npm run build` |
| **Build output directory** | `apps/dashboard/dist` |
| Environment variables | （无必需变量） |

**两种配置等价**——选你 Cloudflare 账户 UI 上更顺手的那种。

### 4.3 一次性配置（ACT-5 执行）

```bash
# 1. 登录 Cloudflare Dashboard
# 2. Workers & Pages → Create application → Pages → Connect to Git
# 3. 选择 GitHub repo: conanxin/agent-project-control-tower
# 4. 配置（按 §4.1 或 §4.2）
# 5. 绑定自定义域：control-tower.<your-domain>
#    - Cloudflare 自动加 CNAME、加 SSL
```

**ACT-4B 故意不做的**：

- ❌ 不在 CLI 配 Cloudflare API token（避免 token 泄露风险）
- ❌ 不写 `.github/workflows/pages.yml` 走 GitHub Actions → Cloudflare（增加 token 复杂度）
- ❌ 不自动 deploy（用户在 Dashboard 手动 Connect + Save & Deploy）
- ❌ 不绑自定义域（ACT-5 决策）

### 4.4 三种 root directory 配置对比

| Root directory | Build command | Output directory | 备注 |
| --- | --- | --- | --- |
| `apps/dashboard` | `npm ci && npm run build` | `dist` | **推荐**——Astro 自己处理 |
| repo root | `cd apps/dashboard && npm ci && npm run build` | `apps/dashboard/dist` | 也行——更明确 |
| 不用——直接让 CI 处理 | — | — | ACT-4A 默认用此模式（CI 跑 `make publish-preflight` + 上传 `apps/dashboard/dist`） |

### 4.5 触发条件

只让"公开数据 / dashboard 源码"变化触发部署：

```
Watch paths:
  - public-data/**
  - apps/dashboard/**
  - scripts/**
  - package.json
  - apps/dashboard/package-lock.json
```

`docs/`、`reports/`、`examples/` 变化不触发 dashboard rebuild（dashboard 不读）。

### 4.6 域名 + HTTPS

- **主域**：`control-tower.<your-domain>`（CNAME 指向 Cloudflare Pages 默认域）
- **HTTPS**：Cloudflare 自动签发 + 续期
- **HSTS**：默认开，trust 1 year

### 4.7 监控（可选）

- **UptimeRobot**（免费）：HTTP HEAD 监控 `https://control-tower.conanxin.com/`，5 分钟一次
- 失败 → Telegram 通知
- 监控 endpoint：`/`（简单可用，因为站点是 SPA-like 多页）

### 4.8 Custom Domain 配置（ACT-5B 已落定）

> **Custom domain 已绑定**（ACT-5B 完成）。7/7 URL HTTP 200。

| 字段 | 值 |
| --- | --- |
| Domain | `control-tower.conanxin.com` |
| 父域 | `conanxin.com`（DNS 已在 Cloudflare 托管） |
| DNS record 类型 | `CNAME`（Cloudflare Pages 自动创建） |
| SSL/TLS | Cloudflare 自动签发 + 续期（Universal SSL） |
| 状态 | Active |

**配置步骤**（实际跑过的）：

1. Cloudflare Dashboard → Workers & Pages → `agent-project-control-tower` project
2. **Custom domains** tab → **Set up a custom domain**
3. 输入 `control-tower.conanxin.com` → Continue
4. Cloudflare 检测到父域 `conanxin.com` 已在托管 → **自动**创建 CNAME 记录
5. 等待 ~30s（CNAME 传播 + SSL 签发）
6. 状态显示 **Active**

**Custom domain 与 pages.dev 的关系**：

- Cloudflare Pages 1 个 project = 1 个 dist = N 个 domain
- 默认 `*.pages.dev` 子域 + custom domain `control-tower.conanxin.com` **同时** 服务同一份 dist
- 更新数据 → `git push origin main` → CF Pages re-build → 2 个 URL **同步**刷新
- 流量分配：CF CDN edge 自动处理（user 不感知）

**7 URL 验收结果**（ACT-5B 落定）：

| URL | HTTP | SSR title |
| --- | --- | --- |
| `https://control-tower.conanxin.com/` | 200 | "Agent Project Control Tower" |
| `https://control-tower.conanxin.com/timeline/` | 200 | (timeline) |
| `https://control-tower.conanxin.com/projects/local-book-tool/` | 200 | "Local Book Tool — ..." |
| `https://control-tower.conanxin.com/projects/cloud-art-site/` | 200 | "Cloud Art Site — ..." |
| `https://control-tower.conanxin.com/agents/local-hermes/` | 200 | "Local Hermes (notebook) — ..." |
| `https://control-tower.conanxin.com/agents/local-codex/` | 200 | "Local Codex (notebook) — ..." |
| `https://control-tower.conanxin.com/agents/cloud-openclaw/` | 200 | "Cloud OpenClaw (VPS) — ..." |

### 4.9 Pages.dev → Custom Domain 301 Redirect（**未配置**）

> 当前**故意不配** redirect。访问 `*.pages.dev` 直接服务（**不** 301 跳到 custom domain）。

**为什么保留两个 URL 同时服务**：

- `*.pages.dev` 是 fallback——如果 custom domain SSL 过期 / DNS 出问题，`*.pages.dev` 仍可用
- 已分享出去的旧 URL（之前用 `*.pages.dev` 发给朋友）继续工作
- 公开 dashboard 不在乎"统一入口"——访客只要能进就行

**如果未来想统一入口**（decision pending）：

Cloudflare Pages → Custom domains → 选中 `agent-project-control-tower.pages.dev` → "Set as primary" 不行（CF Pages **没有**这个选项）。两条可行路径：

1. **Cloudflare Rules**（Dashboard → Rules → Redirect Rules）：
   ```
   Source: hostname equals "agent-project-control-tower.pages.dev"
   Target: https://control-tower.conanxin.com/$1
   Status: 301
   ```
2. **`_redirects` 文件**（Astro 静态资源根）：
   ```
   https://agent-project-control-tower.pages.dev/*  https://control-tower.conanxin.com/:splat  301
   ```
   Cloudflare Pages 识别 Cloudflare-specific redirect 语法。

**为什么 ACT-5B 不配**：

- MVP 阶段不必要
- 加 redirect = 加一个 future debug 路径（什么时候被触发？会不会和 SSR 冲突？）
- 决策保留

### 4.10 ACT-6 Prebuild 钩子（自动从 public-data 生成 generated/）

> **ACT-6 解决了 ACT-5 报告的疑问**："CF Pages build 怎么拿到 generated/index.json（gitignored）？"

**答案**：`npm run build` 现在**自带** prebuild 钩子，在 build 期间从 public-data 重新生成 generated/。**不再依赖**外部先生成。

`apps/dashboard/package.json`：

```json
{
  "scripts": {
    "prebuild": "if [ \"$SKIP_DASHBOARD_PREBUILD\" = \"1\" ]; then echo 'prebuild: SKIPPED, using existing generated/index.json'; else cd ../.. && python scripts/tower.py validate --source public-data && python scripts/tower.py build --source public-data --no-embedded; fi",
    "build": "astro build"
  }
}
```

**两种 build 模式**：

| 模式 | 触发方式 | 数据源 | 用途 |
| --- | --- | --- | --- |
| **PUBLIC**（默认） | `make dashboard` / `cd apps/dashboard && npm run build` | public-data/ | CF Pages build、make publish-preflight |
| **LOCAL** | `make dashboard-local` / `cd apps/dashboard && SKIP_DASHBOARD_PREBUILD=1 npm run build` | data/ | opt-in 调试（先生成 data 版 generated，再跳过 prebuild） |

**Makefile 拆分**（ACT-6 落地）：

| Target | 行为 |
| --- | --- |
| `make dashboard` | PUBLIC dist（prebuild 钩子从 public-data 重写 generated/） |
| `make dashboard-local` | LOCAL dist（opt-in 调试；先 `tower.py build` 写 data 版 generated，再 `SKIP_DASHBOARD_PREBUILD=1 npm run build`） |
| `make public-data` | ACT-4A 默认：examples → public-data/（CI seed） |
| `make public-data-real` | ACT-6 新增：data → public-data/ 脱敏切片（`make publish-preflight` 默认走这条） |
| `make publish-preflight` | ACT-6 升级：第一步走 `public-data-real`（不是 `public-data`） |

**`scripts/export_public_data.py` ACT-6 新增参数**：

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

| 参数 | 作用 |
| --- | --- |
| `--project-id` | 只导出该 project registry + 关联 events（可重复） |
| `--agent-id` | 只导出该 agent（可重复） |
| `--max-events N` | 每个 project 最多 N 个 event（默认 50，newest first） |
| `--replace` | 清空 `public-data/{registry,events}` 再写（默认 merge） |
| `--repo-prefix` | 把 `local/<project-id>` 改写为 `<prefix>/<project-id>`（默认 `conanxin`） |

**为什么 ACT-6 把控制塔自身作为第一个真实项目**：

- `agent-project-control-tower` 自身就是 ACT-0 ~ ACT-5B 全部阶段 event 的产生者（dogfooding）
- 真实 events 里没有 home 路径 / token / IP —— data/ 的 `local/<id>` placeholder 是**预先设计**的安全占位符
- 公开这个项目能直接告诉访客"这个 dashboard 是怎么诞生的"

**当前 public-data 统计**（ACT-6 落定，1/1/7）：

```
projects: 1  (agent-project-control-tower)
agents:   1  (local-hermes)
events:   7  (PROJECT_REGISTERED + ACT-0/1/2/3A/5/5B PHASE_REPORT)
repo:     conanxin/agent-project-control-tower  (rewritten from local/...)
```

> **注**：ACT-3B / ACT-4A / ACT-4B 这 3 个阶段没有 PHASE_REPORT 上报到 data/（只更新 docs/），所以 timeline 共 7 个 event 而不是 10 个。**这是真实的控制塔状态**。

## 5. GitHub Pages 方案（备选）

如果不想用 Cloudflare：

### 5.1 启用 Pages

```bash
# Settings → Pages → Source = "GitHub Actions"
```

### 5.2 写 deploy workflow（ACT-4B 时再加）

参考 ACT-4A 的 `ci.yml` 模板，加一个 deploy job：

```yaml
# .github/workflows/pages.yml  (ACT-4B 才会写)
name: pages
on:
  push:
    branches: [main]
permissions:
  pages: write
  id-token: write
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: make publish-preflight
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - uses: actions/configure-pages@v4
      - uses: actions/upload-pages-artifact@v3
        with:
          path: apps/dashboard/dist
      - id: deployment
        uses: actions/deploy-pages@v4
```

### 5.3 访问地址

`https://<user>.github.io/<repo>/`

## 6. ACT-6 部署清单（**已完成** —— public data 升级为真实子集 1/1/7、prebuild 钩子生效）

### 6.1 ACT-6 已完成 ✅

- [x] **`apps/dashboard/package.json` 加 `prebuild` 钩子**（自动从 public-data 重写 generated/）
- [x] **Makefile `dashboard` target 改为 PUBLIC 模式**（不再依赖 `tower.py build` 即 data 版 generated）
- [x] **Makefile 新增 `dashboard-local` target**（opt-in 调试用 data/ + `SKIP_DASHBOARD_PREBUILD=1`）
- [x] **Makefile 新增 `public-data-real` target**（data → public-data/ 脱敏切片）
- [x] **Makefile `publish-preflight` 第一步改为 `public-data-real`**（不再走 examples）
- [x] **`scripts/export_public_data.py` 新增 5 个参数**：`--project-id` / `--agent-id` / `--max-events` / `--replace` / `--repo-prefix`
- [x] **导出真实子集**：1 project / 1 agent / 7 events
- [x] **rejection safety**：`data/` 仍 gitignored；`local/<id>` 占位符被 `conanxin/` 改写；0 FAIL / 0 WARN
- [x] `make all` PASS（53/53，data/ 链路）
- [x] `make publish-preflight` PASS（1/1/7，public-data 链路）
- [x] `cd apps/dashboard && npm run build` PASS（4 pages，prebuild 钩子从 public-data 重写 generated/）
- [x] pre-commit audit CLEAN
- [x] `tower.py report-phase ACT-6` 上报（PASS / health=green）
- [x] README / DEPLOYMENT_PLAN / MVP_PLAN 同步更新
- [x] 写 ACT-6 阶段报告

### 6.2 ACT-6 已知限制

- ❌ **未跑在线 URL 验收**（custom domain + pages.dev）—— ACT-6 范围只验证本地 + 构建链路；在线重新部署由 `git push` 触发
- ❌ **多 project export 合并语义不明确** —— ACT-6 用 `--replace` 整体覆盖；想"添加而不删"需新设计
- ❌ **`make public-data-real` 默认只导 1 个 project** —— 接入第 2 个项目需修改 `PUBLIC_DATA_PROJECT` 变量
- ❌ **`make publish-preflight` 第一步 hardcode 走 `public-data-real`** —— 想切回 examples demo 链需手工跑 `make public-data && make publish-preflight`
- ❌ **未配 pages.dev → custom domain 301 redirect** — 沿用 ACT-5B 决策
- ❌ **HSTS / Web Analytics / UptimeRobot 未配** — 沿用 ACT-5B 限制
- ❌ **无自定义 404 页** — CF Pages 默认 404
- ❌ **demo 数据 local-book-tool / cloud-art-site 仍存在 data/ 但不导出**（--project-id 过滤）

### 6.3 ACT-6 故意不做的

- ❌ **不**在 CLI 配 Cloudflare API token（沿用 ACT-4B 决策）
- ❌ **不**改 `apps/dashboard/` 任何源码（部署问题一律在 CF Pages UI 解决）
- ❌ **不**改 public-data 边界（仍 gitignore `data/` 和 `generated/`，仍只暴露 `public-data/`）
- ❌ **不**接 5 个项目（只接 1 个；ACT-6B 候选再接）
- ❌ **不**配 redirect / HSTS / Analytics（推到 ACT-5C 或更后）

### 6.4 ACT-6 完整 deploy 流程（已跑通）

**Step 1**: 真实事件上报到 data/
1. `python scripts/tower.py register-project --project-id ...`（如未注册）
2. `python scripts/tower.py report-phase --project-id ... --phase-id ... --status PASS ...`

**Step 2**: 导出 public-data 真实子集
1. `make public-data-real`（或 `python scripts/export_public_data.py --source data --project-id ... --replace`）
2. 验证 redaction 0 FAIL

**Step 3**: 验证构建链
1. `make all` — data 链路 53/53
2. `make publish-preflight` — public-data 链路 PASS
3. `cd apps/dashboard && npm run build` — prebuild 钩子从 public-data 重写 generated/
4. `python /tmp/precommit_audit.py` — CLEAN

**Step 4**: 提交 + push
1. `git add public-data/ Makefile apps/dashboard/package.json scripts/export_public_data.py docs/ README.md reports/`
2. `git commit -m "ACT-6: ..."
3. `git push origin main` → CF Pages 自动 re-deploy，custom domain 30s 内刷新

## 7. 不在 MVP 部署里的

明确**不做**：

- ❌ **数据库**：永远不引入。event 数据全在 Git
- ❌ **用户系统 / 登录**：MVP 公开访问
- ❌ **服务端渲染**：所有页面都 pre-render
- ❌ **API**：dashboard 拉的是静态 JSON，不是 fetch 实时数据
- ❌ **WebSocket / SSE**：实时性不是 MVP 目标
- ❌ **CDN 缓存策略调优**：默认缓存即可
- ❌ **多 region 部署**：Cloudflare 自动全球
- ❌ **PR preview**：MVP 不开（Cloudflare Pages 自动开的话可保留）

## 8. 未来扩展：Private Dashboard

如果某天有商业项目想用控制塔追踪，但又不能公开：

### 方案

- 第二个控制塔仓库（私有）`<user>-private/agent-project-control-tower-private`
- 第二个 Cloudflare Pages 项目，绑定 `control-tower-private.<your-domain>`
- 启用 Cloudflare Access（zero-trust 登录）—— 输入邮箱 → 收到一次性链接 → 进入

### 代价

- 每月多花 $0（Cloudflare Access free tier 支持 50 个用户）
- 每次更新要维护 2 份 deploy
- 跨 dashboard 没有统一搜索

**不推荐同时维护公开 + 私有两份**——除非真的有必要。

## 9. 回滚

### Cloudflare Pages

```
Dashboard → Deployments → 找到上一个 working build → "Rollback to this deploy"
```

10 秒回滚。

### GitHub Pages

```bash
git revert <bad-commit-sha>
git push origin main
# 等 CI 重新跑（2–3 分钟）
```

## 9.5 ACT-5B custom domain 实际验收结果（7 URL × HTTP 200）

| URL | HTTP | SSR title | 关键内容 |
| --- | --- | --- | --- |
| `https://control-tower.conanxin.com/` | 200 | "Agent Project Control Tower" | 2 projects + 3 agents + 3 events |
| `https://control-tower.conanxin.com/timeline/` | 200 | (timeline) | 3 events 完整 SSR（2 PASS + 1 FAIL） |
| `https://control-tower.conanxin.com/projects/local-book-tool/` | 200 | "Local Book Tool — ..." | L2 FAIL + TypeError/DRM/EPUB crashes summary |
| `https://control-tower.conanxin.com/projects/cloud-art-site/` | 200 | "Cloud Art Site — ..." | C1 PASS + Static gallery/120 images/sitemap ready |
| `https://control-tower.conanxin.com/agents/local-hermes/` | 200 | "Local Hermes (notebook) — ..." | machine pill + 1 project 关联 |
| `https://control-tower.conanxin.com/agents/local-codex/` | 200 | "Local Codex (notebook) — ..." | 同上 |
| `https://control-tower.conanxin.com/agents/cloud-openclaw/` | 200 | "Cloud OpenClaw (VPS) — ..." | machine=cloud + 1 project 关联 |

**与 ACT-5 pages.dev 验收对比**：

| 维度 | ACT-5 (`*.pages.dev`) | ACT-5B (custom domain) |
| --- | --- | --- |
| URL 数 | 7 | 7 |
| HTTP 200 | 7/7 | 7/7 |
| SSR title | 正确 | 正确 |
| 关键内容 | 2/3/3 | 2/3/3（**与 ACT-5 一致**） |
| Content-Length | 完全相同 | 完全相同（**同 dist**） |
| Date 响应头 | ~同一秒 | ~同一秒（**同 CDN edge**） |
| 敏感模式扫描 | 0 命中 | 0 命中 |

**敏感模式扫描结果（0 命中）**：

| 模式 | 命中 |
| --- | --- |
| `/home/conanxin/` | 0 |
| 任何 `/home/<user>/` 路径 | 0 |
| IPv4 | 0 |
| `api_key=...` / `token=` / `secret=` / `password=` | 0 |
| `sk-` / `ghp_` 前缀 | 0 |
| `~/.ssh/` / `~/.aws/` / `.env` 引用 | 0 |
| smoke 测试数据 (`smoke-1/2/proj`) | 0 |
| `data/` 路径泄漏 | 0 |

## 10. 成本估算

| 项目 | 月成本 |
| --- | --- |
| Cloudflare Pages | $0（free tier 无限） |
| 自定义域 `<your-domain>` 子域 | $0（已在 `<your-domain>` 下） |
| UptimeRobot 监控 | $0（free tier 50 个 monitor） |
| **合计** | **$0/月** |

唯一可能花钱的是：当 Cloudflare Access 用满 50 用户后要付费（$3/月起）——但 MVP 不需要。
