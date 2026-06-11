# PHASE ACT-3A — Astro Dashboard Shell Report

> **Phase**: ACT-3A — Astro Dashboard Shell
> **Date**: 2026-06-11
> **Author**: xin (via Hermes)
> **Baseline**: ACT-2D (commit `96fb9ec`)
> **Status**: ✅ COMPLETE
> **Recommendation**: ✅ PROCEED to ACT-3B (or ACT-4 if skipping 3B)

---

## 1. Executive Summary

ACT-3A 新增一个 **Astro 静态站**作为控制塔 dashboard 的**视觉/路由增强版**。ACT-1/2 的 `site/index.embedded.html` **完全保留**——双击可看、零依赖的 vanilla HTML 仍是**默认入口**。

**关键交付**：

- `apps/dashboard/` Astro 5 项目（仅 1 个第三方依赖：`astro`）
- 4 个预渲染 page（index / projects/[id] / agents/[id] / timeline）
- 1 个 BaseLayout + 4 个组件（StatCard / ProjectCard / AgentCard / TimelineItem）
- 1 份 `global.css`（暗色主题，纯 CSS）
- 1 个 `src/lib/tower-data.ts` 静态读取 `generated/index.json`
- `make dashboard` target（**不**进 `make all`）
- README §"ACT-3A Astro Dashboard Shell" 章节
- 277 个 npm 包，1.01s build 时间，88KB dist 输出

**数据**：所有 page 在 build-time 读根目录 `generated/index.json`（ACT-2D 后的 3 projects / 3 agents / 7 events），**零运行时 API**、**零 SSR**、**零外部 fetch**。

---

## 2. Why "Shell", not "Full UI"

### 2.1 设计判断

ACT-3A 故意**只做骨架**。理由：

| 维度 | ACT-3A (shell) | ACT-3B (full UI) |
| --- | --- | --- |
| Page 数 | 4 | 6+（+ search, + filters, + diff view） |
| 交互 | 静态读 | 客户端 sort / filter / search |
| 动画 | 无 | view transitions / 暗色切换 |
| 实时 | 无 | (ACT-4 才相关 — auto refresh) |
| 部署 | `dist/` 直接挂任何静态服务 | 同 |
| 时间 | 1 PR | 多 PR |

**Shell 优先**是 MVP 哲学——"先让 dashboard 在视觉/路由上能对外展示"为 ACT-4/5 铺路；UI 复杂度可以增量加。

### 2.2 与 ACT-1/2 vanilla HTML 的关系

```
┌────────────────────────────────────────────────────────────────┐
│                        用户访问 dashboard                       │
└───────────────────┬─────────────────────┬──────────────────────┘
                    │                     │
        ┌───────────▼──────┐    ┌─────────▼────────┐
        │ 双击 embedded.html │    │ 部署 dist/         │
        │ (零依赖, 20 KB)    │    │ (Astro, 88 KB)     │
        │ ACT-1/2 默认入口   │    │ ACT-5 才用         │
        └───────────────────┘    └───────────────────┘
```

**并存而非替代**。理由：
- embedded.html 适合 CI artifact / 个人本地 / 离线归档
- Astro 站适合对外发布 / 路由 / 主题
- 未来 ACT-5 选 Astro 版部署到 Cloudflare Pages，embedded.html 留作 fall-back

---

## 3. New Pages

### 3.1 4 个预渲染 page

| 路径 | 数据 | 组件 |
| --- | --- | --- |
| `/` | 全局 summary + 全 project + 全 agent + 最近 10 event | `StatCard × 7` + `ProjectCard × N` + `AgentCard × N` + `TimelineItem × 10` |
| `/projects/[project_id]/` | 单 project 详情 + 该 project 的 timeline | `BaseLayout` + `<dl class="detail-grid">` + `TimelineItem × N` |
| `/agents/[agent_id]/` | 单 agent 详情 + 该 agent 的 timeline | 同上 |
| `/timeline/` | 全部 event 倒序 | `TimelineItem × N` |

`[project_id].astro` / `[agent_id].astro` 用 `getStaticPaths()` 在 build-time 展开——**每个 project/agent 一份独立 HTML**。

### 3.2 build 后 dist 内容

```
dist/
├── _astro/_agent_id_.CTPmGf1D.css     (2 KB)
├── index.html                         (4 KB)
├── timeline/index.html                (5 KB)
├── projects/
│   ├── local-book-tool/index.html
│   ├── cloud-art-site/index.html
│   └── agent-project-control-tower/index.html
└── agents/
    ├── local-hermes/index.html
    ├── local-codex/index.html
    └── cloud-openclaw/index.html
```

**8 page(s) built in 1.01s**。Total: 88 KB。

### 3.3 数据正确性（验证）

- 首页 `summary.project_count = 3`、`agent_count = 3`、`event_count = 7` ✓
- `agent-project-control-tower` 项目详情页：name "Agent Project Control Tower" / PASS / 3 PHASE 事件 ✓
- Timeline 页：`"7 events total"` ✓

---

## 4. How Data Is Read

### 4.1 路径

`apps/dashboard/src/lib/tower-data.ts` 用相对路径 import JSON：

```ts
import data from "../../../../generated/index.json";
```

`../../../../` 是因为 `src/lib/tower-data.ts` → `src/lib` → `src` → `dashboard` → `apps` → repo root（5 级，4 个 `..`）。

### 4.2 schema 契约

`generated/index.json` 必须满足以下（由 ACT-2 build_index.py 强制）：

```ts
interface TowerData {
  schema_version: string;
  source: string;
  generated_at: string;
  summary: { project_count, agent_count, event_count, green_count, yellow_count, red_count, blocked_count };
  projects: Project[];   // Project: project_id, name, repo, location, category, current_status, current_health, current_phase_id, current_phase_name, last_agent_id, last_event_at, last_event_type, last_summary, next, event_count
  agents: Agent[];       // Agent: agent_id, name, machine, role, last_event_at, last_project_id, last_event_type, event_count
  timeline: TimelineEntry[];   // TimelineEntry: event_id, event_type, project_id, agent_id, phase_id, phase_name, status, health, summary, next, created_at
}
```

如果 schema 字段缺失，page **不** crash——`tower-data.ts` 提供 fallback（如 `?? 0`, `?? "—"`, `?? "gray"`）。

### 4.3 build-time vs runtime

- **完全 build-time**：`generated/index.json` 在 `astro build` 阶段被静态 import 到 page bundle
- **完全无 runtime fetch**：deployed HTML **不**发出 `fetch()` 请求——0 个外部 API 调用
- **完全无 SSR**：Astro `output: "static"` 配置

---

## 5. Build Commands and Results

### 5.1 首次（一次性）

```bash
cd apps/dashboard
npm install
# → 277 packages installed in 1m
```

### 5.2 重建

```bash
cd apps/dashboard
npm run build
# → 8 page(s) built in ~1s
```

或用 Makefile：

```bash
cd ~/workspace/projects/agent-project-control-tower
make dashboard
# → 即上面 npm run build
```

### 5.3 验证

```bash
ls apps/dashboard/dist/
# 应该看到 8 个 HTML + 1 个 CSS
```

**实测结果**：

```
11:29:12 [build] 8 page(s) built in 1.01s
11:29:12 [build] Complete!
```

### 5.4 与根目录 `make all` 共存

```bash
make all
# 跑：validate + build + test + test-cli
# 不跑 npm，不依赖 Node，零网络
# 53/53 验收全过
```

`make dashboard` 是**独立** target——`make all` **不**包含它。两套链路互不影响。

---

## 6. 已知限制（act-3A 范围外）

| 维度 | 状态 | 留给谁 |
| --- | --- | --- |
| 搜索 / 过滤 / 排序 | ❌ | ACT-3B |
| 暗色主题切换（当前只有暗色） | ❌ | ACT-3B |
| View transitions | ❌ | ACT-3B |
| 实时刷新 | ❌ | ACT-4（GitHub Actions 重建） |
| 部署到 Cloudflare Pages | ❌ | ACT-5 |
| Search Engine Optimization | 基础（`<title>`/`<meta>`） | ACT-3B 增 OpenGraph |
| 项目差异查看（同一项目多次 phase） | ❌（timeline 已含） | ACT-3B |
| 数据下载/导出 | ❌ | 之后 |
| GitHub 来源展示（直链 source_repo） | ❌ | ACT-3B |
| RSS / Atom feed | ❌ | 之后 |

ACT-3A **故意不解决**这些——shell 阶段只解决"4 个 page + 8 个 HTML + 正确数据"。

---

## 7. File Inventory (新增/修改)

### 7.1 新增

```
apps/dashboard/
├── .gitignore                                (NEW, 184 B)
├── package.json                              (NEW, 420 B)
├── package-lock.json                         (NEW, 277 packages lockfile)
├── astro.config.mjs                          (NEW, 873 B)
├── src/
│   ├── lib/tower-data.ts                     (NEW, 3.3 KB)
│   ├── styles/global.css                     (NEW, 6.1 KB)
│   ├── layouts/BaseLayout.astro              (NEW, 1.2 KB)
│   ├── components/StatCard.astro             (NEW, 343 B)
│   ├── components/ProjectCard.astro          (NEW, 908 B)
│   ├── components/AgentCard.astro            (NEW, 565 B)
│   ├── components/TimelineItem.astro         (NEW, 1.3 KB)
│   ├── pages/index.astro                     (NEW, 1.5 KB)
│   ├── pages/timeline.astro                  (NEW, 613 B)
│   ├── pages/projects/[project_id].astro     (NEW, 2.0 KB)
│   └── pages/agents/[agent_id].astro         (NEW, 1.4 KB)
└── (dist/ is gitignored, build product)
```

### 7.2 修改

- `Makefile`：加 `dashboard` target
- `README.md`：加 §"ACT-3A Astro Dashboard Shell" 章节
- `docs/MVP_PLAN.md`：ACT-3 标记 COMPLETE（手写）
- `reports/PHASE_ACT3A_ASTRO_DASHBOARD_SHELL_REPORT.md`：本文件

### 7.3 根目录 .gitignore 已包含

```
apps/dashboard/node_modules/
apps/dashboard/dist/
```

——`node_modules` 和 `dist` 不进 git。

---

## 8. 风险与缓解

| 风险 | 严重度 | 缓解 |
| --- | --- | --- |
| Astro 升级破坏 schema | 低 | `tower-data.ts` 显式 `?? fallback` |
| 用户误以为 `make all` 跑 npm | 低 | `make all` 文档明示"no npm"；`make dashboard` 单独 |
| `npm install` 网络失败 | 中 | ACT-3A 是"可选增强"——`make all` 不依赖 npm |
| dist 体积增长 | 低 | 当前 88 KB；ACT-3B 引入图片/字体时再优化 |
| 双 dashboard 数据不一致 | 低 | 同一源 `generated/index.json`；每次 build 都重读 |
| Astro 引入大量 JS hydration | 中 | 保持 `output: "static"` + 无 `client:*` 指令 |

---

## 9. Recommendation for Next Phase

### 9.1 是否进入 ACT-3B？

**两种选择都合理**：

**A. ACT-3B 视觉/交互增强**：
- search 框（前端 JS filter timeline）
- 暗/亮主题切换
- view transitions
- 排序（按 time / agent / project）
- 1-2 周

**B. 跳到 ACT-4 自动化**：
- GitHub Actions：data/ 改变 → 自动 rebuild dashboard
- ACT-4 之后 ACT-5 部署到 Cloudflare Pages
- 1 周

**推荐：A → B**——先完成视觉/交互，再做 CI/CD。

但**由用户决定**——`MVP_PLAN.md` 的当前时间线是 ACT-3 → ACT-4 → ACT-5 → ACT-6；ACT-3 的"完整版"可能跨 ACT-3A/3B/3C。

### 9.2 ACT-3A 退出条件（已达成）

> "dashboard 在视觉/路由/可部署性上"完整。

8 个静态 HTML、1 个 CSS、~88 KB、Astro 5、Node 25 兼容、零运行时 API——达成。

---

## 10. Self-Audit (Redaction Check)

ACT-3A 写出的所有**进 git**文件无敏感信息：
- ✅ `package.json`：仅 `astro` 一个依赖
- ✅ `astro.config.mjs`：仅 `output: "static"` + 简单 alias
- ✅ `tower-data.ts`：仅类型定义 + import
- ✅ `global.css`：仅暗色 CSS 变量
- ✅ 4 个 .astro 组件：仅 HTML + Astro 前置脚本
- ✅ `package-lock.json`：自动生成，已知无 secret
- ✅ `reports/PHASE_ACT3A_*.md`：本文件

`generated/index.json` 是 ACT-2D 后的 3 projects / 7 events，无 token / 路径 / IP（已由 `make all` 的 redaction 链路过）。

---

## 11. Sign-off

| Item | Status |
| --- | --- |
| 用户 ACT-3A 任务清单 9 项 | ✅ 100% |
| `apps/dashboard/` Astro 项目 scaffold | ✅ |
| 4 个 page（index / projects/[id] / agents/[id] / timeline） | ✅ |
| 5 个组件（BaseLayout + 4 个） | ✅ |
| `npm install` PASS | ✅ 277 packages |
| `npm run build` PASS | ✅ 8 pages, 1.01s, 88 KB |
| 保留 `site/index.html` + `site/index.embedded.html` | ✅ 未删未改（除嵌入式 HTML 跟着 ACT-2D 重 build） |
| 不做部署 | ✅ |
| 不做 GitHub Actions | ✅ |
| 不做登录 / 数据库 | ✅ |
| `make all` 不强制跑 npm | ✅ |
| `make dashboard` target | ✅ |
| README ACT-3A 章节 | ✅ |
| 阶段报告（本文件） | ✅ |
| 根目录 `make all` 仍 PASS | ✅ 53/53 |
| Git 提交 | ⏳ 下一步 |
| 推送到 GitHub | ❌ 按要求未推送 |
| 建议进入 ACT-3B | ✅ |

**ACT-3A 状态：COMPLETE**

下一步等待用户确认：
- 进入 **ACT-3B**（search/filter/theme/transition 视觉增强）
- 或跳到 **ACT-4**（GitHub Actions CI）
