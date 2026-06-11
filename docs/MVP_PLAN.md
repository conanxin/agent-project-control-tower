# MVP Plan — ACT-1 to ACT-6

> 把"建一个能用的控制塔"拆成 6 个阶段。每个阶段都有明确产出 + 验收标准 + 退出条件。
>
> 当前在 **ACT-2 ✅ COMPLETE**。这份文档定义 ACT-3 之后做什么。

## 全景时间线

```
ACT-0  ✅ 设计与架构        (2026-06-11, commit adcd937)
  ↓
ACT-1  ✅ 本地数据流原型     (2026-06-11, commit eb08bee)
  ↓
ACT-2  ✅ Tower CLI         (2026-06-11) ← ACT-3 准备接手
  ↓
ACT-3          Astro 静态 dashboard
  ↓
ACT-4          GitHub Actions CI
  ↓
ACT-5          真实在线部署 (Cloudflare Pages / GitHub Pages)
  ↓
ACT-6          接入 5 个真实项目
  ↓
ACT-7+         通知 / 统计 / 修正流 (可选)
```

每个 ACT 的预算：**1–2 周业余时间**，不超过 30 个 commit。

---

## ACT-1 — Hand-rolled Data + Manual Index

> **目标**：证明"Git + JSON + 静态生成"这个最小循环能跑。

### 状态：✅ COMPLETE (2026-06-11)

### 范围

- [x] 完成 `examples/projects.yml`、`examples/agents.yml`（2 个项目 / 3 个 agent）
- [x] 完成 3 个示例 event JSON（覆盖 PASS / FAIL / 跨 agent 场景）
- [x] **写一个零依赖的 YAML 解析器**（`scripts/lib/yaml_mini.py`）—— 不引入 PyYAML
- [x] `scripts/validate_examples.py` 校验 registry + events（schema / enum / cross-ref）
- [x] `scripts/build_index.py` 读 registry + events → 写 `generated/index.json`
- [x] `scripts/build_embedded_site.py` 把 index.json 内嵌到 `site/index.embedded.html`
- [x] `site/index.html` 提供 fetch 版本（HTTP server 下用）+ embedded fallback
- [x] `tests/smoke.py` 验收 14 项检查（counts、health 派生、timeline 顺序、内嵌数据）
- [x] `Makefile` 提供 `validate / build / site / test / all / clean` 6 个 target

### 不在范围（保持 ACT-1 极简）

- ❌ 不写任何前端框架
- ❌ 不引入 Astro / npm / Tailwind
- ❌ 不接 GitHub Actions
- ❌ 不接真实项目
- ❌ 不写 `tower` CLI
- ❌ 不做暗色主题、动画、view transitions
- ❌ 不做项目详情页 / agent 详情页（只有首页）

### 实际验收（由 `tests/smoke.py` 强制执行）

```
[ok] summary.project_count == 2
[ok] summary.agent_count == 3
[ok] summary.event_count == 3
[ok] local-book-tool current_status == FAIL
[ok] local-book-tool current_health == red
[ok] local-book-tool current_phase_id == L2
[ok] local-book-tool last_agent_id == local-codex
[ok] local-book-tool event_count == 2
[ok] cloud-art-site current_status == PASS
[ok] cloud-art-site current_health == green
[ok] cloud-art-site event_count == 1
[ok] timeline is sorted newest-first
[ok] embedded HTML contains __TOWER_DATA__ block
[ok] inline data summary.project_count == 2

SMOKE TEST PASSED
```

### 退出条件（已达成）

> ✅ "我对自己说：dashboard 长这样就够了，剩下就是把数据生成自动化。"
>
> 实际上手写 dashboard 在 ACT-1 没做——直接就是脚本 build 的；但 ACT-1 证明了"build 出来的数据 + 静态 HTML = 可双击的 dashboard"是成立的。

### 留给 ACT-2 的桥

- 现在的 event 是手写 JSON——ACT-2 把手写变成 `tower report phase`
- 现在的 YAML 解析是自家的——ACT-2 可以替换为 PyYAML（如果 ACT-3 起引入更多 YAML 字段）
- 现在的 `generated/index.json` 是平铺的——ACT-3 起如果要做项目详情页，可能要补 `generated/projects/<id>.json`

---

## ACT-2 — tower CLI (Python)

> **目标**：把 ACT-1 里的"手写"自动化，让 agent 能用 CLI 写 event。

### 状态：✅ COMPLETE (2026-06-11)

### 范围（最终）

- [x] **`scripts/tower.py`** — 统一 CLI，10 个子命令（`validate / build / seed / register-agent / register-project / report-phase / report-failure / report-review / report-handoff / report-release`）
- [x] **`scripts/lib/redaction.py`** — 隐私校验（轻量规则：FAIL 拒写 / WARN 写但告警 / PASS 静默）
- [x] **`scripts/lib/yaml_mini.py`** — 零依赖 YAML（ACT-1 已有）
- [x] **`scripts/validate.py`** — `--source {data,examples,both}`（替换 ACT-1 的 `validate_examples.py`，后者变成 thin wrapper）
- [x] **`scripts/build_index.py`** — `--source` flag，默认 `data`，可被 `TOWER_ROOT` env 覆盖
- [x] **`scripts/build_embedded_site.py`** — `--index` / `--template` / `--output` 三 flag
- [x] **`data/registry/{projects,agents}.yml`** + **`data/events/*.json`** — 新运行时数据目录（`.gitignore`）
- [x] **`examples/registry/`** — 同期迁移 ACT-0 的 examples 至此对称结构
- [x] **`tests/cli_smoke.py`** — 39 项 CLI smoke（在临时目录跑，不污染真实 data/）
- [x] **`Makefile`** — `seed / validate / build / site / test / test-cli / reset / all / clean` 9 个 target

### 不在范围（保持 ACT-2 极简）

- ❌ **不**用 Click / Typer / argparse-subcommands 之外的 CLI 库——用 stdlib `argparse`
- ❌ **不**用 Pydantic / dataclasses 之外的数据模型——用 stdlib dict + 手动校验
- ❌ **不**实现 `block` / `unblock` / `archive` 子命令（ACT-3 补）
- ❌ **不**写 `git add` / `git commit` / `git push` 集成（刻意不做，详见 [AGENT_WORKFLOW.md §2.5](AGENT_WORKFLOW.md)）
- ❌ **不**做 GitHub Actions
- ❌ **不**接真实部署
- ❌ **不**做 dashboard 静态站优化
- ❌ **不**支持多控制塔仓库自动发现（`TOWER_ROOT` env var 就够）

### 实际验收（由 `tests/cli_smoke.py` 强制执行 + `make all` 一键跑通）

```
[ok]  validate clean state
[ok]  build clean state
[ok]  generated/index.json exists after build
[ok]  summary.project_count == 2
[ok]  register-agent smoke-1
[ok]  register-agent smoke-1 idempotent (no error)
[ok]  register-agent smoke-1 reports 'already exists'
[ok]  register-project smoke-proj
[ok]  register-project smoke-proj idempotent
[ok]  report-phase PASS
[ok]  report-failure (status=FAIL, health=red)
[ok]  FAILURE event file exists (1 found)
[ok]  FAILURE event status == FAIL
[ok]  FAILURE event health == red
[ok]  FAILURE event has failure_reason
[ok]  report-review
[ok]  REVIEW event_type == REVIEW_REPORT
[ok]  REVIEW event has review_target {agent_id, phase_id}
[ok]  report-handoff
[ok]  HANDOFF event_type == HANDOFF
[ok]  HANDOFF event has to_agent_id == smoke-2
[ok]  report-release
[ok]  RELEASE event status == RELEASED
[ok]  RELEASE event health == green
[ok]  RELEASE event has release.version == v0.0.1
[ok]  redaction FAIL returns exit 3 (got 3)
[ok]  redaction FAIL did NOT write event file
[ok]  redaction WARN still writes (exit 0)
[ok]  redaction WARN event file exists
[ok]  final build
[ok]  site/index.embedded.html exists
[ok]  embedded HTML contains __TOWER_DATA__
[ok]  inline data has 3+ projects (got 3)
[ok]  timeline has AGENT_REGISTERED
[ok]  timeline has PROJECT_REGISTERED
[ok]  timeline has PHASE_REPORT
[ok]  timeline has REVIEW_REPORT
[ok]  timeline has HANDOFF
[ok]  timeline has RELEASE

CLI SMOKE TEST PASSED
```

加上 ACT-1 14 项 = **总 53 项验收全过**。

### 退出条件（已达成）

> "从现在起，每个新阶段都用 tower CLI 上报，再也不手写 JSON。"

### 留给 ACT-3 的桥

- ACT-1/2 的 `site/index.html` + `site/index.embedded.html` 是**纯静态**（vanilla JS）——ACT-3 引入 Astro 时，先用现有 2 文件作为"reference"再设计组件
- `generated/index.json` schema 是 ACT-2 收敛的 `0.2` 版本——ACT-3 起所有 page 都消费这个 JSON
- 缺 `block` / `unblock` / `archive` 3 个 CLI 子命令——ACT-3 补
- `redaction` 是轻量规则——ACT-3 之前如果发现误报/漏报，**先**加测试再修规则



---

## ACT-3 — Static Dashboard (Astro)

> **目标**：把 ACT-1 的手写 HTML 替换成 Astro 项目，CI 之前能本地预览。

### 拆解

- [x] **ACT-3A**（已完成）— Dashboard shell：4 个 page + 1 个 layout + 4 个组件 + 暗色 CSS；npm install + npm run build PASS；不替代 ACT-1/2 的 embedded.html
- [ ] **ACT-3B**（待规划）— 视觉/交互增强：search / filter / sort / 暗色主题切换 / view transitions
- [ ] **ACT-3C**（可选）— SEO + 暗色主题切换 + accessibility

> 详细 ACT-3A 报告：[PHASE_ACT3A_ASTRO_DASHBOARD_SHELL_REPORT.md](../reports/PHASE_ACT3A_ASTRO_DASHBOARD_SHELL_REPORT.md)

### 范围（ACT-3A 最终交付）

- [x] `apps/dashboard/` 初始化 Astro 5 项目（**仅 Astro，无 Tailwind / React**）
- [x] `apps/dashboard/src/pages/index.astro` — 首页
- [x] `apps/dashboard/src/pages/projects/[project_id].astro` — 项目详情
- [x] `apps/dashboard/src/pages/agents/[agent_id].astro` — agent 详情
- [x] `apps/dashboard/src/pages/timeline.astro` — 全局时间线
- [x] `apps/dashboard/src/lib/tower-data.ts` — 从 `../../../../generated/index.json` 读
- [x] 5 个组件（BaseLayout + StatCard + ProjectCard + AgentCard + TimelineItem）
- [x] 极简 CSS（暗色 + 纯 CSS variables，无框架）
- [x] 保留 `site/index.html` + `site/index.embedded.html`（ACT-1/2 零依赖版不动）
- [x] `make dashboard` target，**不**进 `make all`

### 不做（ACT-3A 故意不解决）

- ❌ 不做 search / filter / sort（前端的 JS 交互）
- ❌ 不做暗色主题切换（MVP 只一种暗色，亮色后续）
- ❌ 不做 view transitions / 动画
- ❌ 不做 about / RSS / sitemap
- ❌ 不做部署
- ❌ 不做 GitHub Actions
- ❌ 不做登录

### 验收（ACT-3A 实际跑过）

- ✅ `cd apps/dashboard && npm install` → 277 packages OK
- ✅ `cd apps/dashboard && npm run build` → 8 page(s) built in 1.01s
- ✅ `make dashboard` target OK
- ✅ `make all`（零依赖路径） 53/53 仍 PASS
- ✅ dist/ 包含 8 HTML + 1 CSS，~88 KB
- ✅ 首页显示 3 projects / 3 agents / 7 events（与 ACT-2D 后 `generated/index.json` 一致）
- ✅ 项目详情页 / agent 详情页 / timeline 页正确数据
- ✅ 无运行时 API、无 SSR、无外部 fetch

### 退出条件（已达成）

> "dashboard 在视觉/路由/可部署性上"完整。

### 留给 ACT-3B 的桥

- 当前 `tower-data.ts` 写死读 `generated/index.json`——如果未来想支持"读自 examples" 切换，加 `BUILD_TARGET` env var 即可
- `project_id` 维度是 `getStaticPaths()` 展开——新增项目后**必须**重新 build（不破坏 schema）
- 暗色 CSS 变量已抽出——ACT-3B 加 `prefers-color-scheme` 媒体查询是 5 行 CSS
- timeline 用 `sort by created_at desc`——已 build-time 排好，client 无需重排

---

## ACT-4 — GitHub Actions CI

> **目标**：每次 push 自动 build + 部署到 staging。

### 范围

- [ ] `.github/workflows/build-dashboard.yml`
- [ ] 触发条件：`push` to `main`，`paths: [registry/**, events/**, scripts/**, site/**]`
- [ ] 步骤：`checkout` → `setup-python` → `pip install` → `build_index.py` → `setup-node` → `npm ci` → `npm run build`
- [ ] 产物上传为 artifact（30 天保留）
- [ ] 失败时通过 issue comment 通知（用 `peter-evans/create-or-update-comment`）
- [ ] `docs/CI_GUIDE.md` — 怎么改 workflow 不会炸

### 不用

- ❌ 不做 release workflow
- ❌ 不做 staging / production 分支分离
- ❌ 不做 PR preview（Cloudflare Pages 那侧做）

### 验收

- [ ] push 一个 event JSON → 2 分钟内 CI 跑完
- [ ] CI 失败 → issue 里能看到日志
- [ ] artifact 下载后 `unzip` 能直接 serve

### 退出条件

> 我能对自己说："CI 是个可观察、可回滚的系统。"

---

## ACT-5 — Public Deployment

> **目标**：dashboard 上线，所有人都能看。

### 范围

- [ ] 选 Cloudflare Pages 或 GitHub Pages（见 [DEPLOYMENT_PLAN.md](DEPLOYMENT_PLAN.md)）
- [ ] 绑定 `control-tower.xin.dev` 子域名
- [ ] Cloudflare Access 关闭（公开访问）
- [ ] 写一个 `docs/INCIDENT_RESPONSE.md` —— 站点挂了的处理流程

### 不用

- ❌ 不做登录
- ❌ 不做"私密项目隐藏"——所有展示都脱敏
- ❌ 不做 CDN 缓存策略调优（默认即可）

### 验收

- [ ] 打开 `https://control-tower.xin.dev/` 看到 2+ 项目
- [ ] 手机浏览器能看
- [ ] UptimeRobot 监控配置好（5 分钟检测一次）

### 退出条件

> 我能把这个 URL 发给一个朋友，让他一眼看懂"这人在用 agent 跑开源"。

---

## ACT-6 — Real Project Integration

> **目标**：把 5 个真实开源项目接入控制塔。

### 候选项目

| ID | 仓库 | 主 agent | 备注 |
| --- | --- | --- | --- |
| `artvee-gallery` | `xin/artvee-gallery` | cloud-openclaw | 长跑、批量抓取 |
| `booktrans-desk` | `xin/booktrans-desk` | local-hermes | EPUB 处理 |
| `conan-vps-tower` | `xin/conan-vps-control-tower` | local-codex | 运维工具 |
| `medium-archive` | `xin/medium-archive` | local-codex | 批量处理 |
| `explainlens` | `xin/explainlens` | local-hermes | 文档站 |

### 流程

每个项目独立一阶段（ACT-6a 到 ACT-6e），避免一次性爆炸：

- **ACT-6a：booktrans-desk**
  - 注册项目
  - 跑 1 个真实 phase
  - 确认 redaction 校验通过
  - 写一篇接入复盘

### 验收

- [ ] 5 个项目全部出现在 dashboard
- [ ] 至少 3 个项目有 ≥ 3 个 phase event
- [ ] 至少 1 个项目经历过 PASS → FAIL → PASS 的完整循环

### 退出条件

> 我不再需要"每周手写 status report"——直接分享 URL。

---

## ACT-7+ — Optional Enhancements

> ACT-6 完成后再讨论的扩展。**不要提前做**。

- **ACT-7**：通知（Discord / Telegram webhook 在 CI 末尾）
- **ACT-8**：统计（`generated/stats.json`、跨项目聚合页）
- **ACT-9**：错误修正流（`correction` event 真正被 build_index 消费）
- **ACT-10**：第二份控制塔（私密项目）—— 独立仓库 + 独立域名
- **ACT-11**：Astro 升级到 v5，引入 view transitions
- **ACT-12**：被其他人 fork → 写 CONTRIBUTING.md

## 风险控制

每个 ACT 开始前必须自问：

1. **这个 ACT 失败的话，我能直接 revert 吗？**
   - ACT-2 失败：删 `scripts/`，回 ACT-1
   - ACT-3 失败：删 `site/`，ACT-2 仍可用
   - ACT-4 失败：删 `.github/workflows/`

2. **这个 ACT 依赖上游的什么不可逆状态？**
   - ACT-3 依赖 ACT-2 的 schema 稳定
   - ACT-5 依赖 ACT-4 的 artifact

3. **这个 ACT 完成后，能跑多久不维护？**
   - 目标：每个 ACT 完成后能"半年不碰也不挂"

## 不在 MVP 里的

- 多视图 / 多 dashboard
- 用户系统 / 登录
- 实时 WebSocket
- 移动端 App
- 国际化（i18n）

这些**全部不做**。如果某个阶段出现"看起来需要 X"的需求，先回到 [PROJECT_VISION.md](PROJECT_VISION.md) 重新审视是否要纳入新的 ACT-7+ 候选。
