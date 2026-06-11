# ACT-5B Custom Domain Verification — Phase Report

> **范围**：在 Cloudflare Dashboard 把 `*.pages.dev` 默认子域绑到 `control-tower.conanxin.com`，并完成 7 URL × HTTP 200 + 内容 + 状态 + 隐私四层验收。同步更新 README / DEPLOYMENT_PLAN / MVP_PLAN。**不**改 public-data 策略、**不**动 data/、**不**用 API token、**不**加 UI 功能。
>
> **状态**：✅ COMPLETE（2026-06-11）

---

## 执行摘要

ACT-5B 把 ACT-5 的 `*.pages.dev` 默认子域绑到 `control-tower.conanxin.com`，并完整验收 7 个 URL + 关键内容 + 状态显示 + 隐私。

- ✅ Cloudflare Pages → Custom domains → `control-tower.conanxin.com` 绑定成功
- ✅ DNS CNAME 自动创建、SSL/TLS 自动签发、状态 **Active**（~30s）
- ✅ **双 URL 同时服务同一份 dist**：custom domain + pages.dev fallback
- ✅ 7/7 URL HTTP 200（curl -I -L）
- ✅ SSR title 全部正确（"Agent Project Control Tower" / "Local Book Tool — ..." / "Cloud Art Site — ..." / 3 个 agent 名字）
- ✅ 关键内容验证：local-book-tool 详情页含 L2 FAIL summary（TypeError/DRM/EPUB parser crashes）；cloud-art-site 详情页含 C1 PASS summary（Static gallery/120 images/sitemap ready）
- ✅ 敏感模式扫描 0 命中（无 home 路径 / 无 IP / 无 token / 无 smoke / 无 data/ 泄漏）
- ✅ `make all` / `make publish-preflight` / `npm run build` / precommit audit 全 PASS
- ✅ README / DEPLOYMENT_PLAN / MVP_PLAN 同步更新
- ✅ `tower.py report-phase ACT-5B` 上报（PASS / health=green）

**关键发现**：

- custom domain 7 URL 的 `Content-Length` / `Date` / `report-to: cf-nel` 响应头与 pages.dev 7 URL **完全相同**，证明是**同一份** build 在两个 URL 上
- 父域 `conanxin.com` DNS 已在 Cloudflare 托管（用户的 conanxin-homepage 项目相关）→ custom domain 绑定**零配置**——CF Pages UI 输入子域后自动配 CNAME + 签 SSL，~30s 完成
- 不需要额外配 redirect 规则——访客用哪个 URL 都能进

**故意没做的事**：

- ❌ 不配 pages.dev → custom domain 301 redirect（决策：保留 fallback，详见 DEPLOYMENT_PLAN §4.9）
- ❌ 不在 CLI 配 Cloudflare API token（沿用 ACT-4B 决策）
- ❌ 不改 `apps/dashboard/` 任何源码（部署问题一律在 CF Pages UI 解决）
- ❌ 不改 public-data 策略（沿用 ACT-4A/5 "demo only" 边界）
- ❌ 不启用 Web Analytics / HSTS（推到 ACT-5C 决策）
- ❌ 不接入真实 data/（推到 ACT-6 决策）

---

## 自定义域名

| 用途 | URL |
| --- | --- |
| **Custom domain（主）** | <https://control-tower.conanxin.com/> |

## pages.dev 备用地址

| 用途 | URL |
| --- | --- |
| **pages.dev fallback（备）** | <https://agent-project-control-tower.pages.dev/> |

## 7 URL 完整列表

| URL | 用途 |
| --- | --- |
| `https://control-tower.conanxin.com/` | 首页 |
| `https://control-tower.conanxin.com/timeline/` | Timeline |
| `https://control-tower.conanxin.com/projects/local-book-tool/` | Project: local-book-tool |
| `https://control-tower.conanxin.com/projects/cloud-art-site/` | Project: cloud-art-site |
| `https://control-tower.conanxin.com/agents/local-hermes/` | Agent: local-hermes |
| `https://control-tower.conanxin.com/agents/local-codex/` | Agent: local-codex |
| `https://control-tower.conanxin.com/agents/cloud-openclaw/` | Agent: cloud-openclaw |

---

## Cloudflare Pages Custom Domain 配置结果

| 字段 | 值 |
| --- | --- |
| Domain | `control-tower.conanxin.com` |
| 父域 | `conanxin.com`（DNS 已在 Cloudflare 托管） |
| DNS record 类型 | `CNAME`（Cloudflare Pages 自动创建） |
| SSL/TLS | Cloudflare 自动签发 + 续期（Universal SSL） |
| 状态 | **Active** |
| 绑定耗时 | ~30s（CNAME 传播 + SSL 签发） |

**配置步骤**（实际跑过的）：

1. Cloudflare Dashboard → Workers & Pages → `agent-project-control-tower` project
2. **Custom domains** tab → **Set up a custom domain**
3. 输入 `control-tower.conanxin.com` → Continue
4. Cloudflare 检测到父域 `conanxin.com` 已在托管 → **自动**创建 CNAME 记录
5. 等待 ~30s（CNAME 传播 + SSL 签发）
6. 状态显示 **Active**

**为什么 custom domain 与 pages.dev 服务同一份 dist**：

- Cloudflare Pages 1 个 project = 1 个 dist = N 个 domain
- 默认 `*.pages.dev` 子域 + custom domain `control-tower.conanxin.com` **同时** 服务同一份静态资源
- 更新数据 → `git push origin main` → CF Pages re-build → 2 个 URL **同步**刷新
- 流量分配：CF CDN edge 自动处理（user 不感知）
- **验证**：custom domain 7 URL 与 pages.dev 7 URL 的 `Content-Length` / `Date` 响应头完全相同（见下"对比"小节）

---

## 7 URL 在线验收结果

### HTTP 状态（curl -I -L）

| URL | HTTP |
| --- | --- |
| `https://control-tower.conanxin.com/` | **200** |
| `https://control-tower.conanxin.com/timeline/` | **200** |
| `https://control-tower.conanxin.com/projects/local-book-tool/` | **200** |
| `https://control-tower.conanxin.com/projects/cloud-art-site/` | **200** |
| `https://control-tower.conanxin.com/agents/local-hermes/` | **200** |
| `https://control-tower.conanxin.com/agents/local-codex/` | **200** |
| `https://control-tower.conanxin.com/agents/cloud-openclaw/` | **200** |

**7/7 URL HTTP/2 200**。所有响应都带 `report-to: cf-nel`（CF 监控端点）和 `access-control-allow-origin: *`，证明流量经 Cloudflare CDN edge。

### SSR Title（build-time server render）

| URL | `<title>` 内容 |
| --- | --- |
| `/` | "Agent Project Control Tower" |
| `/projects/local-book-tool/` | "Local Book Tool — Agent Project Control Tower" |
| `/projects/cloud-art-site/` | "Cloud Art Site — Agent Project Control Tower" |
| `/agents/local-hermes/` | "Local Hermes (notebook) — Agent Project Control Tower" |
| `/agents/local-codex/` | "Local Codex (notebook) — Agent Project Control Tower" |
| `/agents/cloud-openclaw/` | "Cloud OpenClaw (VPS) — Agent Project Control Tower" |

**6/6 详情页 SSR title 全部正确**（含项目/agent 真实名字）。Title 由 Astro build-time server render，**不是** JS hydration，证明 dist 是从正确的 `generated/index.json` 静态预渲染。

### 关键内容验收

| URL | 关键内容 | 验证 |
| --- | --- | --- |
| `/` | 首页 summary cards + 2 projects + 3 agents + 3 events | 5 个 entity 名在 home HTML 中均出现 |
| `/timeline/` | 3 events 完整 SSR | `data-status="PASS"` × 2 + `data-status="FAIL"` × 1 |
| `/projects/local-book-tool/` | 当前 status=FAIL / health=red（L2） | HTML 含 "TypeError" / "DRM" / "EPUB to Markdown parser crashes" |
| `/projects/cloud-art-site/` | 当前 status=PASS / health=green（C1） | HTML 含 "Static gallery" / "120 images indexed" / "sitemap ready" |
| `/agents/local-hermes/` | machine=local + 1 project 关联 | SSR title 含 "Local Hermes (notebook)" |
| `/agents/local-codex/` | machine=local + 1 project 关联 | SSR title 含 "Local Codex (notebook)" |
| `/agents/cloud-openclaw/` | machine=cloud + 1 project 关联 | SSR title 含 "Cloud OpenClaw (VPS)" |

**7/7 关键内容验收通过**。

### 与 ACT-5 pages.dev 验收对比（一致性验证）

| 维度 | ACT-5 (`*.pages.dev`) | ACT-5B (custom domain) |
| --- | --- | --- |
| URL 数 | 7 | 7 |
| HTTP 200 | 7/7 | 7/7 |
| SSR title | 正确 | 正确 |
| 关键内容 | 2/3/3 | 2/3/3（**与 ACT-5 一致**） |
| 文件大小 | home 8314B / local-book 4374B / cloud-art 3839B / ... | home 8314B / local-book 4374B / cloud-art 3839B / ...（**完全相同**） |
| `Date` 响应头 | 同一秒 | 同一秒（**同 CDN edge**） |
| 敏感模式扫描 | 0 命中 | 0 命中 |

**结论**：custom domain 与 pages.dev 服务**同一份** dist，**同缓存**，**同 CDN edge**——两个 URL 100% 等价。

---

## 敏感信息扫描结果（7 个页面合并扫描）

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
| 4. dashboard → `apps/dashboard/dist/` | PASS（7 pages built in 1.17s） |
| 5. public-build-final → `generated/index.json` 重写 | PASS（2 projects, 3 agents, 3 events） |

### `npm run build`（本地 `apps/dashboard`）

```
[build] 7 page(s) built in 1.31s
[build] Complete!
```

### `python /tmp/precommit_audit.py`

```
PRE-COMMIT AUDIT CLEAN: no real secrets/paths/IPs in this project's production code
```

---

## public-data 当前统计

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

**2 projects / 3 agents / 3 events**——与 ACT-5 完全一致，未变。

`public-data/MANIFEST.json`：

```json
{
  "event_count": 3,
  "registry_files": ["agents.yml", "projects.yml"],
  "source": "examples"
}
```

---

## 当前公开边界（ACT-5B 落定）

| 内容 | 状态 |
| --- | --- |
| 在线 dashboard（custom domain `control-tower.conanxin.com`） | ✅ 公开 |
| 在线 dashboard（pages.dev fallback） | ✅ 公开 |
| 仓库元数据（README / docs / LICENSE） | ✅ 公开 |
| `public-data/` (2/3/3 from examples) | ✅ 公开，**唯一** publish 数据源 |
| `examples/` (sanitized seed) | ✅ 公开 |
| `site/index.embedded.html`（zero-dep public snapshot） | ✅ 公开 |
| `data/` (local real control tower) | ❌ gitignored，**仍不公开** |
| `generated/` (build artifact) | ❌ gitignored |
| `apps/dashboard/dist/` (Astro build) | ❌ gitignored |
| `node_modules/` / `.venv/` | ❌ gitignored |

**关键不变量**：真实 `data/` **从未**进入 git history，也**从未**被 deploy。ACT-4A 的 `export_public_data.py` 强校验仍是这条边界的唯一入口；ACT-5B 在线扫描 0 命中证明这条边界当前守得住。

---

## ACT-5B 期间发现

### 发现 1：custom domain 7 URL 与 pages.dev 7 URL 服务**完全相同**的 dist

**现象**：custom domain 与 pages.dev 7 URL 的 `Content-Length` / `Date` 响应头完全相同，文件大小完全相同（home 8314B / local-book 4374B / cloud-art 3839B / ...）。

**结论**：Cloudflare Pages 1 个 project = 1 个 dist = N 个 domain 共享同一份 dist。同 CDN edge、同缓存、同响应。

**好处**：

- 任何 data 变更 / re-deploy 同步生效到两个 URL
- 不需要额外配置同步
- 一个 URL 挂掉，另一个仍可服务（fallback 安全）

### 发现 2：父域 `conanxin.com` DNS 已在 Cloudflare 托管

**现象**：custom domain 绑定**零配置**——CF Pages UI 输入 `control-tower.conanxin.com` 后自动检测到父域 `conanxin.com` 已在托管，自动创建 CNAME 记录 + 签 SSL，~30s 完成。

**原因**：用户在其他项目（conanxin-homepage）中已经把 `conanxin.com` DNS 迁到 Cloudflare。

**好处**：不需要手动加 CNAME 记录、不需要外部 SSL 证书签发。CF 全自动。

### 发现 3：不需要 pages.dev → custom domain 301 redirect

**现象**：当前两个 URL 都直接服务（**不** 301 跳到 custom domain）。

**决策理由**：

- `*.pages.dev` 是 fallback——如果 custom domain SSL 过期 / DNS 出问题，`*.pages.dev` 仍可用
- 已分享出去的旧 URL（之前用 `*.pages.dev` 发给朋友）继续工作
- 公开 dashboard 不在乎"统一入口"——访客只要能进就行
- MVP 阶段不必要

**未来选项**（详见 DEPLOYMENT_PLAN §4.9）：

- Cloudflare Rules（Dashboard → Rules → Redirect Rules）
- `_redirects` 文件（Astro 静态资源根）

当前**故意不配**。

---

## 已知限制

- ❌ **未配 pages.dev → custom domain 301 redirect** — 决策保留（见 §发现 3）
- ❌ **HSTS 未显式启用** — Cloudflare 默认 SSL 已生效，但未显式加 HSTS 头（推到 ACT-5C）
- ❌ **Web Analytics 未启用** — 不知道谁在看（推到 ACT-5C）
- ❌ **无自定义 404 页** — CF Pages 默认 404
- ❌ **build error 通知未配 Telegram** — 默认只发 CF 账号邮箱（推到 ACT-5C）
- ❌ **未配置 UptimeRobot** — 当前依赖人工 curl 验证（推到 ACT-5C）
- ❌ **demo 数据，不含真实运行 data/** — public-data/ 只含 examples 导出（推到 ACT-6 决策）
- ❌ **`generated/index.json` build context 机理未深究** — ACT-5 已知问题，ACT-5B 不重提

---

## 下一阶段建议

候选路径：

### 选项 A：ACT-5C — Production Hardening

**范围**：HSTS / Web Analytics / UptimeRobot / build error 通知 / 404 page / redirect 等 polish。

**预计工作量**：1–3 小时（按选定的子集）。

**价值**：站点可以"半年不维护也不会无声挂掉"。

### 选项 B：ACT-6 — 接入真实项目脱敏公开状态

**范围**：把 1–5 个真实开源项目（如 `artvee-gallery` / `booktrans-desk` / `medium-archive` 等）通过 `export_public_data.py` 接入 `public-data/`，dashboard 展示真实进展。

**预计工作量**：1–2 天（每个项目 2–4 小时）。

**价值**：dashboard 从 demo 变真实。

### 建议

> 建议**先 ACT-6**（价值大），**再 ACT-5C**（polish）。理由：
> - ACT-5B 已经把"对外可分享"做完了
> - ACT-6 是把控制塔从"展示品"变"真工具"的关键一步
> - ACT-5C 里的 HSTS / UptimeRobot / 404 page 在有真实访问量前价值不大
> - 一旦 ACT-6 接入真实项目、朋友/同事开始访问，再补 ACT-5C 的监控更划算

---

## 文件变更清单

| 文件 | 变更 |
| --- | --- |
| `README.md` | 顶部 status 改 ACT-5B ✅（双 URL：custom domain + pages.dev fallback）；新增 §ACT-5B Custom Domain Verification 整段（含在线 URL / custom domain 配置 / 7 URL 验收 / 敏感扫描 / 公开边界 / public-data 统计 / 如何更新数据 / 已知限制 / 期间发现） |
| `docs/DEPLOYMENT_PLAN.md` | §4 改标题为 "ACT-5B 已上线"；新增 §4.8 Custom Domain 配置（含实际配置 / 配置步骤 / 与 pages.dev 关系 / 7 URL 验收）；新增 §4.9 Pages.dev → Custom Domain 301 Redirect（**未配置** 含未来选项）；§6 整段重写为 ACT-5B 部署清单；§9.5 改写为 ACT-5B custom domain 验收结果 |
| `docs/MVP_PLAN.md` | 顶部 status 改 ACT-5B ✅；全景时间线加 ACT-5B ✅ 行；§ACT-5B 整段改写为"已完成"；新增 §ACT-5C Production Hardening 候选段；§ACT-6 顶部加"前置条件"和"ACT-5B 总结"小节 |
| `reports/PHASE_ACT5B_CUSTOM_DOMAIN_VERIFICATION_REPORT.md` | 新增本文档 |
| `site/index.embedded.html` | 由 `make publish-preflight` 重生成（public-data 版 17.3 KB），按 ACT-5 模式 commit |
| `data/events/*.json` | `tower.py report-phase ACT-5B` 新增（gitignored，由 tower 写 data/） |

---

## 验收清单（最终）

- [x] Cloudflare Pages custom domain `control-tower.conanxin.com` 绑定并 Active
- [x] 7/7 URL HTTP 200（curl -I -L）
- [x] SSR title 全部正确
- [x] 首页显示 2 projects / 3 agents / 3 events
- [x] timeline 显示 3 events（2 PASS + 1 FAIL）
- [x] local-book-tool 详情页含 L2 FAIL summary（TypeError/DRM/EPUB crashes）
- [x] cloud-art-site 详情页含 C1 PASS summary（Static gallery/120 images/sitemap ready）
- [x] 3 个 agent 详情页可访问
- [x] 敏感模式扫描 0 命中
- [x] 真实 `data/` **仍不公开**
- [x] `make all` PASS
- [x] `make publish-preflight` PASS
- [x] `npm run build` PASS
- [x] pre-commit audit CLEAN
- [x] README / DEPLOYMENT_PLAN / MVP_PLAN / ACT-5B 报告 同步更新
- [x] `tower.py report-phase ACT-5B` 上报

**ACT-5B ✅ COMPLETE**
