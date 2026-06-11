# MVP Plan — ACT-1 to ACT-6

> 把"建一个能用的控制塔"拆成 6 个阶段。每个阶段都有明确产出 + 验收标准 + 退出条件。
>
> 当前在 **ACT-0**（设计）。这份文档定义 ACT-1 之后做什么。

## 全景时间线

```
ACT-0  (现在)   设计与架构        ← 你在这里
  ↓
ACT-1          示例数据 + 手写 index
  ↓
ACT-2          tower CLI (Python)
  ↓
ACT-3          静态 dashboard (Astro)
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

### 范围

- [ ] 完成 `examples/projects.yml`、`examples/agents.yml`（3 个项目 / 3 个 agent）
- [ ] 完成 3 个示例 event JSON（覆盖 PASS / FAIL / 跨 agent 场景）
- [ ] 写一个**手写**的 `examples/generated/index.json`——不跑脚本，纯手写
- [ ] 写一个**手写**的 `examples/site/index.html`——静态 HTML + 内联 JSON 渲染
- [ ] 在 `examples/README.md` 里说明"打开 index.html 就能看 dashboard 效果"

### 不在范围

- ❌ 不写任何 Python 脚本
- ❌ 不引入 Astro / npm
- ❌ 不接 GitHub Actions
- ❌ 不接真实项目

### 验收

- [ ] `xdg-open examples/site/index.html` 能看到至少 2 个项目 + 1 个失败事件
- [ ] 离线、零依赖、双击就能开
- [ ] 整个 `examples/` 目录 < 200 KB

### 退出条件

> 我对自己说："哦，dashboard 长这样就够了，剩下就是把数据生成自动化。"

---

## ACT-2 — tower CLI (Python)

> **目标**：把 ACT-1 里的"手写"自动化，让 agent 能用 CLI 写 event。

### 范围

- [ ] `scripts/lib/schema.py` — Pydantic v2 数据模型
- [ ] `scripts/lib/git_ops.py` — `git pull --rebase` + commit + push 包装
- [ ] `scripts/lib/redaction.py` — 隐私校验
- [ ] `scripts/register_agent.py`
- [ ] `scripts/register_project.py`
- [ ] `scripts/report_phase.py`
- [ ] `scripts/report_review.py`
- [ ] `scripts/report_handoff.py`
- [ ] `scripts/report_release.py`
- [ ] `scripts/report_failure.py`
- [ ] `scripts/report_block.py` / `scripts/report_unblock.py`
- [ ] `scripts/build_index.py` — 读 `registry/*.yml` + `events/**/*.json` → 写 `generated/index.json`
- [ ] `scripts/tower` — 入口 shell wrapper（PATH 友好）
- [ ] `scripts/requirements.txt` — `pydantic>=2`, `pyyaml`, `click`（或 `typer`）
- [ ] `scripts/tests/` — 至少 6 个单测（schema / redaction / build_index）

### 不在范围

- ❌ 不做 GitHub Actions
- ❌ 不接真实部署
- ❌ 不做 dashboard 静态站
- ❌ 不支持多控制塔仓库切换（一个 env var 就够）

### 验收

- [ ] `tower register-project --id X ...` → 真的写文件 + commit + push
- [ ] `tower report phase --status FAIL` → 真的写 `events/<date>/...FAIL....json`
- [ ] `tower build` → 生成 `generated/index.json`，与 ACT-1 手写版结构一致
- [ ] 故意写一个含 `192.168.1.1` 的 summary → 被 redaction 拒绝
- [ ] 故意重复 `register-agent --id same` → 被拒绝
- [ ] `pytest scripts/tests/` → 6+ 测试全绿

### 退出条件

> 我能对自己说："从现在起，每个新阶段都用 tower CLI 上报，再也不手写 JSON。"

---

## ACT-3 — Static Dashboard (Astro)

> **目标**：把 ACT-1 的手写 HTML 替换成 Astro 项目，CI 之前能本地预览。

### 范围

- [ ] `site/` 目录初始化 Astro 项目（**仅 Astro + 内置 markdown**，不引入 Tailwind / React）
- [ ] `site/src/pages/index.astro` — 首页（项目卡片 + agent 卡片 + 最近活动）
- [ ] `site/src/pages/projects/[id].astro` — 项目详情
- [ ] `site/src/pages/agents/[id].astro` — agent 详情
- [ ] `site/src/pages/timeline.astro` — 全局时间线
- [ ] `site/src/pages/about.astro` — 关于页
- [ ] `site/src/components/HealthDot.astro` — 复用组件
- [ ] `site/src/lib/render.ts` — 从 `generated/index.json` 读数据
- [ ] `site/public/data/index.json` — `build_index.py` 写到此处（CI 之前手动 cp）
- [ ] 极简 CSS（裸 CSS variables，无框架）

### 不用

- ❌ 不引入 Tailwind / UnoCSS / Styled Components
- ❌ 不引入 React / Vue / Svelte
- ❌ 不引入 TypeScript 严格模式（`tsconfig.json` 留 loose 即可）
- ❌ 不做暗色主题切换（MVP 只一种浅色）

### 验收

- [ ] `cd site && npm run dev` 本地起服务，访问 `localhost:4321` 看到至少 2 个项目
- [ ] `cd site && npm run build` 生成 `site/dist/`
- [ ] Lighthouse 性能分 ≥ 90
- [ ] 首屏 < 50KB（不引外部资源）

### 退出条件

> 我能对自己说："dashboard 在视觉上能对外展示了，可以部署了。"

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
