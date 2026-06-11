# PHASE ACT-1 — Local Data Flow Prototype Report

> **Phase**: ACT-1 — Local Data Flow Prototype
> **Date**: 2026-06-11
> **Author**: xin (via Hermes)
> **Baseline**: ACT-0 (commit `adcd937`)
> **Status**: ✅ COMPLETE
> **Recommendation**: ✅ PROCEED to ACT-2

---

## 1. Executive Summary

ACT-1 用零外部依赖（**无 PyYAML、无 npm、无前端框架**）跑通了控制塔的最小数据流：

```
examples/{projects.yml, agents.yml, events/*.json}
   ↓  scripts/build_index.py
generated/index.json
   ↓  scripts/build_embedded_site.py
site/index.embedded.html  ← 双击可开，零 HTTP server
```

**关键交付**：

- 3 个生产脚本（`validate_examples.py`, `build_index.py`, `build_embedded_site.py`）
- 1 个零依赖 YAML 解析器（`scripts/lib/yaml_mini.py`）
- 1 个静态 dashboard（`site/index.html` + `site/index.embedded.html`）
- 1 个 smoke test（`tests/smoke.py`，14 项验收检查全过）
- 1 个 `Makefile`（6 个 target）
- 1 份本报告

**完成度**：100%（按用户给定的 12 项任务清单）。

---

## 2. Why zero-dep data flow before Astro

### 2.1 设计判断

ACT-0 阶段定下的原则是"**先证明数据流成立，再谈视觉**"。如果跳到 ACT-3 直接上 Astro，会面临：

- 一开始就写一堆组件 / 路由 / 样式，最后发现 data shape 不对
- 任何 data shape 改动要同时改 build 脚本和 Astro template
- 无法独立验证 "**build 出来的 JSON 是否正确**"——Astro 把这层黑盒化了

ACT-1 用三层分离**强制暴露每一层的契约**：

| 层 | 产物 | 谁消费 | 失败时表现 |
| --- | --- | --- | --- |
| source | `examples/*.{yml,json}` | `build_index.py` | validate 失败：打印哪条 YAML 哪行错 |
| generated | `generated/index.json` | `site/index.html` | smoke test 失败：print summary miss-match |
| site | `site/index.embedded.html` | 浏览器 | 浏览器 console error + 红色 banner |

### 2.2 为什么不引 PyYAML

YAML 1.2 规范有 200+ 页，PyYAML 是个 ~2MB 依赖。

ACT-1 实际要解析的 YAML 形态极其受限：

- 顶层是 list of mappings
- value 是 string / int / float / bool / null / inline list `[a,b,c]`
- 注释行以 `#` 开头
- 2 空格缩进

我手写一个 200 行的 `yaml_mini.py` 完整覆盖当前 examples/ 格式，且：

- **不**进 pip 依赖链——任何人 clone 仓库就能跑
- **不**是 PyYAML 的子集 hack——它有自己的 docs 解释它支持什么、不支持什么
- ACT-2 之后如果 YAML 复杂度涨了，**再**换 PyYAML（30 行替换）

这是 MVP 阶段正确的工程取舍：能晚一天引依赖就晚一天。

### 2.3 为什么不引前端框架

模板要求"零构建、零依赖、可双击打开"。任何前端框架都至少要求：

- 一个 build step（vite/astro/webpack）
- 一个 HTTP server（因为 `file://` 下 module imports 失败）
- 一份 `package.json` 治理

ACT-1 的 HTML 全部用 vanilla DOM API + 内联 CSS + 内联 JSON。代价是 200 行 JS 写点 render 逻辑——**这是值得的**。ACT-3 再决定是否换 Astro 之前，我已经知道"HTML + 内嵌 JSON 能跑出合格视觉效果"。

---

## 3. Files Created / Modified

### 3.1 新增（11 个文件 + 3 个目录）

| 文件 | 字节 | 作用 |
| --- | --- | --- |
| `Makefile` | 876 | 6 个 target：`validate / build / site / test / all / clean` |
| `scripts/lib/__init__.py` | 191 | 让 `lib/` 成为合法 Python package（LSP 友好） |
| `scripts/lib/yaml_mini.py` | 7367 | 零依赖 YAML 解析器（~200 行） |
| `scripts/validate_examples.py` | 6951 | registry + events 预校验 |
| `scripts/build_index.py` | 8694 | registry + events → `generated/index.json` |
| `scripts/build_embedded_site.py` | 2331 | 把 index.json 内嵌到 HTML |
| `site/index.html` | 12115 | fetch 版本 + embedded fallback |
| `site/index.embedded.html` | 14916 | build 产物：双击可看 |
| `tests/smoke.py` | 4824 | 14 项验收检查 |
| `generated/index.json` | 3140 | build 产物（**不**进 Git） |
| `reports/PHASE_ACT1_LOCAL_DATA_FLOW_REPORT.md` | (本文件) | ACT-1 报告 |

### 3.2 修改（3 个文件）

| 文件 | 变更 |
| --- | --- |
| `README.md` | 新增 ACT-1 章节（怎么跑、怎么看、证明了什么、没做什么）+ 仓库结构图更新 |
| `docs/MVP_PLAN.md` | ACT-1 标记 ✅ COMPLETE，附实际验收输出 + 留给 ACT-2 的桥 |
| `.gitignore` | （已包含 `generated/`、`site/dist/`）—— 不需修改 |

### 3.3 总规模

```
新增源码:  ~57 KB
build 产物: ~18 KB（generated/index.json + site/index.embedded.html）
新增目录:  generated/, site/, tests/
修改文件:  3 个
新增/修改文件总计: 14 个
```

---

## 4. Data Flow Walkthrough

完整流程（以 `make all` 为入口）：

```
$ make all
   ↓
[1/4] python scripts/validate_examples.py
   ↓
   读 examples/projects.yml      → 解析为 list[dict]     (yaml_mini)
   读 examples/agents.yml        → 解析为 list[dict]     (yaml_mini)
   读 examples/events/*.json     → 解析为 list[dict]     (json stdlib)
   ↓
   校验: 必填字段 / status enum / project_id 交叉引用 / agent_id 交叉引用
   ↓
   输出: PASS / FAIL

[2/4] python scripts/build_index.py
   ↓
   对每个 project: 找匹配 events → 排序 → 取最新 → 派生 health
   对每个 agent:   找匹配 events → 排序 → 取最新 → 派生 role
   timeline:       所有 event 按 event_time 倒序
   summary:        计数 + health 分布
   ↓
   写 generated/index.json (3140 字节)

[3/4] python scripts/build_embedded_site.py
   ↓
   读 generated/index.json + site/index.html
   在 <script> 标记前插入 `window.__TOWER_DATA__ = {...}`
   ↓
   写 site/index.embedded.html (14916 字节)

[4/4] python tests/smoke.py
   ↓
   重新跑 [1][2][3]（保证不是 stale artifact）
   解析 generated/index.json + 提取 __TOWER_DATA__
   14 项断言全过 → SMOKE TEST PASSED
```

---

## 5. Verification Results

### 5.1 完整 `make all` 输出（节选）

```
============================================================
validate_examples.py — pre-flight check
============================================================
[1/3] Loading projects registry …  ok: 2 projects, 2 unique ids
[2/3] Loading agents registry …    ok: 3 agents, 3 unique ids
[3/3] Validating event files …     scanned 3 event file(s)
============================================================
PASS: all examples valid

build_index.py — generating dashboard data layer …
  wrote generated/index.json
  2 projects, 3 agents, 3 events
  health: green=1 yellow=0 red=1 blocked=0

build_embedded_site.py
  wrote site/index.embedded.html (14.6 KB)
  open with: xdg-open site/index.embedded.html

=== Acceptance checks ===
  [ok] summary.project_count == 2 (got 2)
  [ok] summary.agent_count == 3 (got 3)
  [ok] summary.event_count == 3 (got 3)
  [ok] local-book-tool current_status == FAIL (got FAIL)
  [ok] local-book-tool current_health == red (got red)
  [ok] local-book-tool current_phase_id == L2 (got L2)
  [ok] local-book-tool last_agent_id == local-codex (got local-codex)
  [ok] local-book-tool event_count == 2 (got 2)
  [ok] cloud-art-site current_status == PASS (got PASS)
  [ok] cloud-art-site current_health == green (got green)
  [ok] cloud-art-site event_count == 1 (got 1)
  [ok] timeline is sorted newest-first
  [ok] embedded HTML contains __TOWER_DATA__ block
  [ok] inline data summary.project_count == 2

SMOKE TEST PASSED
```

### 5.2 关键验收（来自任务清单 §9）

| 验收项 | 状态 |
| --- | --- |
| validate examples PASS | ✅ |
| `generated/index.json` 生成成功 | ✅ (3140 字节) |
| `site/index.embedded.html` 生成成功 | ✅ (14.6 KB) |
| 看到 **2 个项目** | ✅ (local-book-tool, cloud-art-site) |
| 看到 **3 个 agent** | ✅ (local-hermes, local-codex, cloud-openclaw) |
| 看到 **3 条事件** | ✅ (L1 PASS, C1 PASS, L2 FAIL) |
| `local-book-tool` 当前状态 FAIL/red | ✅ (L2 是最新) |
| `cloud-art-site` 当前状态 PASS/green | ✅ (C1 是唯一) |

### 5.3 已知限制（不在 ACT-1 范围）

- **WSL 环境下无法 GUI 验证**：当前环境无 `DISPLAY`，`xdg-open` 不能弹窗。
  - 缓解：`html.parser` 解析 embedded HTML + JSON 提取双校验通过
  - 真机打开验证在 ACT-5（部署到 Cloudflare Pages）会再次发生
- **YAML 解析器能力受限**：不支持 multi-doc `---`、flow mapping `{a: b}`、anchors `&`。
  - 当前 examples 格式不受影响
  - ACT-2 之后如果引入更复杂 YAML，可换 PyYAML
- **timeline 列表未分页**：MVP 阶段 3 条事件不存在分页需求；ACT-3+ 如果上 100+ 事件需要 lazy load
- **没有项目详情页 / agent 详情页**：ACT-1 只有首页
- **没有暗色主题切换**：硬编码深色背景（`#0f172a`）

---

## 6. What ACT-1 Didn't Do (deliberate)

按 MVP_PLAN 设计，ACT-1 严格保持极简：

| 推迟到 | 内容 |
| --- | --- |
| ACT-2 | `tower register-project` / `tower report phase` CLI；redaction check；PyYAML 替换 |
| ACT-3 | Astro 静态站（首页 + 项目详情页 + agent 详情页）；view transitions |
| ACT-4 | GitHub Actions CI（自动跑 validate + build + deploy） |
| ACT-5 | Cloudflare Pages 部署；自定义域；UptimeRobot 监控 |
| ACT-6 | 接入 5 个真实开源项目 |

这些**全部不在 ACT-1 范围**——本阶段唯一目标是"最小数据流能跑"。

---

## 7. Risk Status Update (vs ACT-0)

来自 [RISKS_AND_BOUNDARIES.md](../RISKS_AND_BOUNDARIES.md)：

| 风险 | ACT-0 状态 | ACT-1 后状态 |
| --- | --- | --- |
| R1 多机 push 冲突 | 中 | 同前（ACT-2 实现 rebase） |
| R2 重复注册 | 中 | 同前（ACT-2 写 CLI） |
| R3 schema 不一致 | 高 | **降低**（`validate_examples.py` 已检查 enum） |
| R4 隐私泄露 | 极高 | 同前（ACT-2 写 redaction.py） |
| R5 失败隐藏 | 中 | 同前（CLI 落地后再做 watchdog） |
| R6 手动改 generated | 中 | **降低**（`generated/` 已在 .gitignore；smoke test 强制重 build） |
| R7 commit 链接失效 | 低 | 同前 |
| R8 私有项目公开 | 极高 | 同前 |
| R9 部署挂 | 低 | 同前（ACT-5 部署后才相关） |
| R10 event 爆炸 | 低 | 同前 |
| R11 agent 改名 | 低 | 同前 |
| R12 引入复杂度 | 中 | **降低**（ACT-1 证明 zero-dep 完全可行；任何"需要 npm"的提议都更容易被拒） |

**ACT-1 净效果**：3 个风险降低（R3, R6, R12），0 个风险升高。

---

## 8. Recommendation for Next Phase

### 8.1 是否进入 ACT-2？

**强烈建议：进入 ACT-2**。

理由：

- ✅ 14 项 smoke test 全部 PASS
- ✅ 数据流全链路已被实测
- ✅ 零外部依赖，无需任何环境准备
- ✅ 文档（README + MVP_PLAN）已更新
- ✅ 示例数据保留 ACT-0 原状，未被污染

### 8.2 ACT-2 范围预告

按 [MVP_PLAN.md §ACT-2](../MVP_PLAN.md)：

- `tower` CLI（Python + `click` / `typer`）
- `scripts/lib/schema.py`（Pydantic v2 数据模型）
- `scripts/lib/git_ops.py`（rebase + commit + push）
- `scripts/lib/redaction.py`（隐私校验）
- `register_agent.py` / `register_project.py` / `report_*.py`
- `build_index.py` 升级（支持更多字段、PyYAML、可选 CI 模式）
- 真实 unit tests（替换 smoke test）

预期 1–2 周完成。ACT-2 完成后，整个 tower 才能真正"agent 友好"。

### 8.3 ACT-2 退出条件（来自 MVP_PLAN）

> "我能对自己说：从现在起，每个新阶段都用 tower CLI 上报，再也不手写 JSON。"

---

## 9. Self-Audit (Redaction Check)

ACT-1 阶段输出**所有**内容已通过人工 audit：

- ✅ 无内网 / 公网 IP
- ✅ 无 `/home/xxx/` 路径（除 ACT-0 文档内的反模式示例）
- ✅ 无 `C:\Users\xxx\` 路径
- ✅ 无 API token / SSH key
- ✅ 三个 example event 的 commit SHA 是占位符（`abc1234`, `feedface`, `beef0001`）
- ✅ build 输出 (`generated/index.json`, `site/index.embedded.html`) 只引用占位符

注：ACT-2 才会写自动 `redaction_check.py`。当前依赖人工 audit。

---

## 10. Sign-off

| Item | Status |
| --- | --- |
| 用户 12 项任务清单 | ✅ 100% |
| 14 项 smoke test | ✅ 14/14 PASS |
| 2 项目 / 3 agent / 3 event 数据正确 | ✅ |
| local-book-tool → FAIL/red | ✅ |
| cloud-art-site → PASS/green | ✅ |
| 零外部依赖 | ✅ |
| `make all` 一键跑通 | ✅ |
| 双击 `site/index.embedded.html` 可看 | ✅ (WSL 无 GUI，但 HTML/JSON 解析通过) |
| README 更新 | ✅ |
| MVP_PLAN 更新 | ✅ |
| 隐私脱敏 | ✅ |
| Git 提交 | ⏳（下一步） |
| 推送到 GitHub | ❌ 按要求未推送 |
| 建议进入 ACT-2 | ✅ |

**ACT-1 状态：COMPLETE**

下一步等待用户确认是否进入 **ACT-2（tower CLI + Pydantic + git_ops）**。
