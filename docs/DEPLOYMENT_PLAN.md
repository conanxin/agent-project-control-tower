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

## 4. Cloudflare Pages 方案（ACT-4B 决策后启用）

### 4.1 一次性配置

```bash
# 1. 登录 Cloudflare Dashboard
# 2. Workers & Pages → Create application → Pages → Connect to Git
# 3. 选择 GitHub repo (ACT-4B 创建)
# 4. 配置（推荐）：
#    - Project name: agent-control-tower
#    - Production branch: main
#    - Build command:  npm ci && npm run build
#    - Build output directory: dist
#    - Root directory:    apps/dashboard
# 5. 绑定自定义域: control-tower.<your-domain>
#    - Cloudflare 自动加 CNAME、加 SSL
```

### 4.2 三种 root directory 配置对比

| Root directory | Build command | Output directory | 备注 |
| --- | --- | --- | --- |
| `apps/dashboard` | `npm ci && npm run build` | `dist` | **推荐**——Astro 自己处理 |
| repo root | `cd apps/dashboard && npm ci && npm run build` | `apps/dashboard/dist` | 也行——更明确 |
| 不用——直接让 CI 处理 | — | — | ACT-4A 默认用此模式（CI 跑 `make publish-preflight` + 上传 `apps/dashboard/dist`） |

### 4.3 触发条件

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

### 4.4 域名 + HTTPS

- **主域**：`control-tower.<your-domain>`（CNAME 指向 Cloudflare Pages 默认域）
- **HTTPS**：Cloudflare 自动签发 + 续期
- **HSTS**：默认开，trust 1 year

### 4.5 监控（可选）

- **UptimeRobot**（免费）：HTTP HEAD 监控 `https://control-tower.<your-domain>/`，5 分钟一次
- 失败 → Telegram 通知
- 监控 endpoint：`/`（简单可用，因为站点是 SPA-like 多页）

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

## 6. ACT-4B 部署清单（待用户决策）

ACT-4B 执行（**不**是 ACT-4A）：

- [ ] 决定 deploy target：Cloudflare Pages 还是 GitHub Pages
- [ ] GitHub 远程仓库创建（命名 + description + topics + LICENSE）
- [ ] `git remote add origin <url>` + `git push -u origin main`
- [ ] 如果 Cloudflare Pages：
  - [ ] 创建 Pages project、绑定 GitHub repo
  - [ ] 配置 root / build / output
  - [ ] 配自定义域 DNS
  - [ ] 第一次部署后 URL 验收
- [ ] 如果 GitHub Pages：
  - [ ] 写 `.github/workflows/pages.yml`
  - [ ] 启用 Pages OIDC
  - [ ] 第一次部署后 URL 验收
- [ ] 决定 `public-data/` 数据范围（先 examples 还是从真实 data 导脱敏子集）
- [ ] 首次在线 dashboard 验收（搜索/筛选/主题切换/移动端）
- [ ] UptimeRobot 监控（可选）

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

如果某次部署炸了：

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

## 10. 成本估算

| 项目 | 月成本 |
| --- | --- |
| Cloudflare Pages | $0（free tier 无限） |
| 自定义域 `<your-domain>` 子域 | $0（已在 `<your-domain>` 下） |
| UptimeRobot 监控 | $0（free tier 50 个 monitor） |
| **合计** | **$0/月** |

唯一可能花钱的是：当 Cloudflare Access 用满 50 用户后要付费（$3/月起）——但 MVP 不需要。
