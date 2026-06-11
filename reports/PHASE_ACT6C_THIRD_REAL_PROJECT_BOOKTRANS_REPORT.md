# ACT-6C Third Real Project Public Export — BookTrans Desk

> **范围**：把第三个真实项目 `booktrans-desk` 接入控制塔公开 dashboard，与 `agent-project-control-tower`、`artvee-gallery` 同时在线展示。验证 3 项目并集导出的稳定性。
>
> **状态**：✅ COMPLETE（2026-06-11）
>
> **公开 dashboard**：<https://control-tower.conanxin.com/>

---

## 执行摘要

ACT-6C 完成了控制塔公开 dashboard 的第三次真实项目接入。BookTrans Desk 作为第三个真实项目被注册到本地 `data/`，上报了 HP-33 Final Public Launch QA 阶段事件，并通过 `export_public_data.py` 的三项目并集导出功能同步到 `public-data/`。构建链路全部通过，dashboard 成功生成 6 个静态页面（home + timeline + 3 project detail + 1 agent detail）。

---

## 为什么第三个真实项目选择 BookTrans Desk

| 维度 | 理由 |
| --- | --- |
| 项目成熟度 | HP-33 已完成 Final Public Launch QA，有明确的 PASS 状态 |
| 公开性 | 项目页和案例研究已发布在 `conanxin.com/projects/booktrans-desk/`，无敏感内容 |
| 多样性 | 补充了控制塔的项目类型多样性（agent-infra + art-gallery + reading-tool） |
| 可验证性 | 有真实 GitHub commit `db3825d` 可查，source_repo 可公开 |
| 无敏感信息 | 项目 summary 不含 home 路径、IP、token |

---

## BookTrans Desk 本地状态读取来源

- **项目目录**：`/home/conanxin/workspace/projects/conanxin-homepage/projects/booktrans-desk`
- **项目页**：`index.html`（PDF/EPUB 阅读、翻译、结构化抽取和导出工具）
- **案例研究**：`case-study/index.html`（完整复盘：把阅读从消费变成生产）
- **最近 commit**：`db3825d437d8b0e4b13c0dd7f022bafe5978ea6e`（Phase HP-33: Final public launch QA）
- **当前阶段**：HP-33 PASS（Final public launch QA）
- **下一步**：稳定 EPUB 支持、优化大文档性能、探索更多导出格式

---

## BookTrans Desk 注册和上报命令

```bash
# 注册项目
python scripts/tower.py register-project \
  --project-id booktrans-desk --name "BookTrans Desk" \
  --repo "conanxin/conanxin-homepage" --location "public" \
  --category "reading-tool" --status ACTIVE \
  --description "PDF / EPUB reading, translation, structured extraction and export tool with layout-aware content processing." \
  --agent-id local-hermes

# 上报阶段
python scripts/tower.py report-phase \
  --project-id booktrans-desk --agent-id local-hermes \
  --phase-id HP-33 --phase-name "Final Public Launch QA" --status PASS \
  --summary "Completed final public launch QA for BookTrans Desk: project page and case study published at conanxin.com/projects/booktrans-desk/, layout-aware PDF/EPUB reading, translation, structured extraction and Markdown export verified." \
  --source-repo "conanxin/conanxin-homepage" \
  --source-commit db3825d437d8b0e4b13c0dd7f022bafe5978ea6e \
  --next "Stabilize EPUB support, optimize large-document performance, and explore export formats beyond Markdown."
```

---

## public-data 三项目导出结果

```bash
python scripts/export_public_data.py \
  --source data --output public-data \
  --project-id agent-project-control-tower \
  --project-id artvee-gallery \
  --project-id booktrans-desk \
  --agent-id local-hermes --max-events 20 \
  --repo-prefix conanxin --replace
```

**导出结果**：

```
registry/projects.yml: 3 entries (after filter), 0 finding(s)
events/: 14 files (after filter+cap), out of 17 in source
registry/agents.yml: 1 entries (after filter), 0 finding(s)

redaction summary: FAIL=0, WARN=0
```

**public-data 统计**：

```yaml
projects:
  - agent-project-control-tower  (category=agent-infra)
  - artvee-gallery               (category=art-gallery)
  - booktrans-desk               (category=reading-tool)
agents:
  - local-hermes                 (machine=local, type=hermes)
events:
  - agent-project-control-tower: 9 events (PROJECT_REGISTERED + ACT-0~ACT-6B)
  - artvee-gallery:              3 events (PROJECT_REGISTERED + P2 + P3B)
  - booktrans-desk:              2 events (PROJECT_REGISTERED + HP-33)
```

---

## redaction 结果

| 检查项 | 结果 |
| --- | --- |
| FAIL（拒写） | 0 |
| WARN（写但告警） | 0 |
| `/home/<user>/` 路径 | 0 |
| IPv4 地址 | 0 |
| `api_key=` / `token=` / `secret=` / `password=` | 0 |
| `sk-` / `ghp_` 前缀 | 0 |

---

## make all 结果

```
PASS: source 'data' valid
build_index.py — source=data
  wrote generated/index.json
  5 projects, 3 agents, 17 events
  health: green=4 yellow=0 red=1 blocked=0

SMOKE TEST PASSED
CLI SMOKE TEST PASSED
```

---

## make publish-preflight 结果

```
PUBLISH PREFLIGHT: PASS
  public-data/    exported from data/ (redacted real-project slice)
  generated/      rebuilt from public-data
  site/embedded   rebuilt from public-data
  apps/dashboard  dist/ rebuilt from public-data
```

---

## npm run build 结果

```
build_index.py — source=public-data
  wrote generated/index.json
  3 projects, 1 agents, 14 events

> agent-project-control-tower-dashboard@0.1.0 build
> astro build

 generating static routes
   ├─ /agents/local-hermes/index.html
   ├─ /index.html
   ├─ /projects/agent-project-control-tower/index.html
   ├─ /projects/artvee-gallery/index.html
   ├─ /projects/booktrans-desk/index.html
   └─ /timeline/index.html

6 page(s) built in 1.31s
```

---

## pre-commit audit 结果

```
CLEAN
```

---

## Cloudflare Pages 自动部署结果

- **部署触发**：`git push origin main` 后 Cloudflare Pages 自动检测新 commit
- **build 时间**：~30s
- **build 命令**：`npm ci && npm run build`（在 `apps/dashboard/` root）
- **prebuild 钩子**：自动从 `public-data/` 重写 `generated/index.json`
- **输出目录**：`dist/`
- **自定义域名**：`control-tower.conanxin.com`
- **fallback**：`agent-project-control-tower.pages.dev`

---

## 在线 URL 验收结果

| URL | HTTP | 关键内容 |
| --- | --- | --- |
| `/` | 200 | 3 projects + 1 agent + 14 events |
| `/timeline/` | 200 | 14 events 倒序 |
| `/projects/agent-project-control-tower/` | 200 | 9 events |
| `/projects/artvee-gallery/` | 200 | 3 events |
| `/projects/booktrans-desk/` | 200 | 2 events |
| `/agents/local-hermes/` | 200 | 关联 3 projects |

---

## 当前公开边界

| 内容 | 状态 |
| --- | --- |
| 在线 dashboard（Cloudflare Pages） | ✅ 公开 |
| 仓库元数据（README / docs / LICENSE） | ✅ 公开 |
| `public-data/` (3 real projects / 1 agent / 14 events) | ✅ 公开，**唯一** publish 数据源 |
| `examples/` (sanitized seed) | ✅ 公开 |
| `data/` (local real control tower) | ❌ gitignored，**仍不公开** |
| `generated/` (build artifact) | ❌ gitignored |
| `apps/dashboard/dist/` (Astro build) | ❌ gitignored |

---

## 已知限制

- ❌ **`make public-data-real` Makefile 变量仍只支持单 project** — 多 project 导出需要直接调用 `export_public_data.py`
- ❌ **artvee-gallery 的 public demo / digest 尚未发布到独立 URL**
- ❌ **booktrans-desk 的公开 demo 未独立部署**
- ❌ **未配 pages.dev → custom domain 301 redirect**
- ❌ **HSTS / Web Analytics / UptimeRobot 未配**
- ❌ **无自定义 404 页**

---

## 下一阶段建议

**推荐进入 ACT-7：agent 上报模板与多机器使用手册**

理由：
- 3 个真实项目已验证控制塔的核心价值（多项目状态聚合）
- 当前只有一个 agent（`local-hermes`）在 dashboard 中展示
- ACT-7 可以定义：
  - 多机器 agent 注册标准流程
  - agent 间 handoff 模板
  - 跨机器数据同步策略（通过 Git 还是其他方式）
  - 新 agent 接入控制塔的 onboarding checklist

替代方案：
- ACT-6D：接入第 4 个真实项目（如需更多项目多样性验证）
- ACT-5C：配置 HSTS / Web Analytics / UptimeRobot（运维增强）
