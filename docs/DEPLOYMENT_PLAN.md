# Deployment Plan

> 怎么把"Git 仓库里的 events"变成"任何浏览器都能看的 dashboard"。

## 0. 设计判断

控制塔的部署是**完全静态**的：

- 没有任何 server-side 逻辑
- 没有数据库
- 没有用户系统
- 部署目标：把 `site/dist/` 放到一个 CDN 上

候选部署平台对比：

| 平台 | 优点 | 缺点 | 推荐度 |
| --- | --- | --- | --- |
| **Cloudflare Pages** | 免费额度大、全球 CDN、子域名绑定简单、preview deploy 强 | 配置文件语法专属 | ⭐⭐⭐⭐⭐ |
| **GitHub Pages** | 零配置、跟仓库绑定 | 不能 preview、慢、需 public repo | ⭐⭐⭐ |
| **Netlify** | 类同 Cloudflare | 配额较少 | ⭐⭐⭐ |
| **Vercel** | 类同 Cloudflare | 偏 JS 框架导向 | ⭐⭐⭐ |
| **自托管（Caddy/Nginx）** | 完全可控 | 要自己维护 HTTPS、CDN | ⭐ |

**推荐 Cloudflare Pages**，理由：

1. 已有 Cloudflare 账户（子域名管理顺手）
2. Free plan 包含 unlimited bandwidth + unlimited requests
3. 与 GitHub 集成简单，push 触发 deploy
4. 每次 PR 自动生成 preview URL（适合 ACT-3+ 测试 dashboard 改动）
5. 国内访问体验比 GitHub Pages 好

**次选 GitHub Pages**（如果不想再开 Cloudflare 账户）。

## 1. Cloudflare Pages 方案

### 1.1 一次性配置

```bash
# 1. 登录 Cloudflare Dashboard
# 2. Workers & Pages → Create application → Pages → Connect to Git
# 3. 选择 xin/agent-project-control-tower 仓库
# 4. 配置：
#    - Project name: agent-control-tower
#    - Production branch: main
#    - Build command: (留空，由 GitHub Actions 处理，见 §1.2)
#    - Build output directory: site/dist
# 5. 绑定自定义域：control-tower.xin.dev
#    - Cloudflare 自动加 CNAME、加 SSL
```

### 1.2 Build 在哪跑

**两条路**：

| 方案 | 优点 | 缺点 |
| --- | --- | --- |
| **A. Cloudflare 直接 build** | 配置最少、UI 友好 | 不能跑 Python（要预生成 `site/public/data/index.json`） |
| **B. GitHub Actions 跑全链路，artifact 推到 Cloudflare** | 灵活、可加测试 | 配置多一步 |

**推荐方案 A**（简化），但需要在 `package.json` 里加一个 `prebuild` 步骤：

```json
{
  "scripts": {
    "build:data": "python ../scripts/build_index.py --output public/data/index.json",
    "prebuild": "npm run build:data",
    "build": "astro build"
  }
}
```

> Cloudflare Pages 支持 build command 链式调用；Python 3 默认在 build 环境里。

### 1.3 触发条件

只让"event / registry 变化"触发部署，避免无意义的 rebuild：

```
Settings → Builds → Configure build → Watch paths:
  - registry/**
  - events/**
  - site/**
  - scripts/**
  - package.json
```

`docs/`、`reports/`、`examples/` 变化不触发 dashboard rebuild（它们是给人看的，dashboard 不读）。

### 1.4 域名 + HTTPS

- **主域**：`control-tower.xin.dev`（CNAME 指向 Cloudflare Pages 默认域）
- **HTTPS**：Cloudflare 自动签发 + 续期
- **HSTS**：默认开，trust 1 year

### 1.5 监控

- **UptimeRobot**（免费）：HTTP HEAD 监控 `https://control-tower.xin.dev/`，5 分钟一次
- 失败 → Telegram 通知到我个人 chat
- 监控 endpoint：`/healthz`（ACT-3 加一个静态 HTML 返回 200，仅用于探活）

## 2. GitHub Pages 方案（备选）

如果不想用 Cloudflare：

### 2.1 配置

```yaml
# .github/workflows/deploy-pages.yml
name: deploy-pages
on:
  push:
    branches: [main]
    paths:
      - 'registry/**'
      - 'events/**'
      - 'site/**'
      - 'scripts/**'

permissions:
  pages: write
  id-token: write

jobs:
  build-deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r scripts/requirements.txt
      - run: python scripts/build_index.py --output site/public/data/index.json
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: cd site && npm ci && npm run build
      - uses: actions/configure-pages@v4
      - uses: actions/upload-pages-artifact@v3
        with:
          path: site/dist
      - id: deployment
        uses: actions/deploy-pages@v4
```

### 2.2 访问地址

`https://xin.github.io/agent-project-control-tower/`

## 3. 部署清单（Deployment Checklist）

ACT-5 阶段执行：

- [ ] 选 Cloudflare Pages 或 GitHub Pages
- [ ] 仓库 Settings → Pages → Source = GitHub Actions（如果是 Pages）
- [ ] Cloudflare Pages 项目创建，绑定 GitHub repo
- [ ] 自定义域 DNS 配好（CNAME）
- [ ] `prebuild` 脚本在 `package.json` 配置
- [ ] Watch paths 配置正确
- [ ] 第一次 push 触发部署，等待 2 分钟
- [ ] 访问 `https://control-tower.xin.dev/` 看到 dashboard
- [ ] UptimeRobot 监控配好
- [ ] 写一篇 `docs/INCIDENT_RESPONSE.md`：站点挂了怎么办

## 4. 不在 MVP 部署里的

明确**不做**：

- ❌ **数据库**：永远不引入。event 数据全在 Git
- ❌ **用户系统 / 登录**：MVP 公开访问
- ❌ **服务端渲染**：所有页面都 pre-render
- ❌ **API**：dashboard 拉的是静态 JSON，不是 fetch 实时数据
- ❌ **WebSocket / Server-Sent Events**：实时性不是 MVP 目标
- ❌ **CDN 缓存策略调优**：默认缓存即可
- ❌ **多 region 部署**：Cloudflare 自动全球

## 5. 未来扩展：Private Dashboard

如果某天有商业项目想用控制塔追踪，但又不能公开：

### 方案

- 第二个控制塔仓库（私有）`xin-private/agent-project-control-tower-private`
- 第二个 Cloudflare Pages 项目，绑定 `control-tower-private.xin.dev`
- 启用 Cloudflare Access（zero-trust 登录）—— 输入邮箱 → 收到一次性链接 → 进入

### 代价

- 每月多花 $0（Cloudflare Access free tier 支持 50 个用户）
- 每次更新要维护 2 份 deploy
- 跨 dashboard 没有统一搜索

**不推荐同时维护公开 + 私有两份**——除非真的有必要。

## 6. 回滚

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

## 7. 成本估算

| 项目 | 月成本 |
| --- | --- |
| Cloudflare Pages | $0（free tier 无限） |
| 自定义域 `xin.dev` 子域 | $0（已在 xin.dev 下） |
| UptimeRobot 监控 | $0（free tier 50 个 monitor） |
| **合计** | **$0/月** |

唯一可能花钱的是：当 Cloudflare Access 用满 50 用户后要付费（$3/月起）——但 MVP 不需要。
