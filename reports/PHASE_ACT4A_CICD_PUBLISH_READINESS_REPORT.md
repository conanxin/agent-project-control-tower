# ACT-4A CI/CD and Publish Readiness — Phase Report

> **范围**：为公开 GitHub 仓库 + 在线发布做准备，但**不** push。完成 public-data 出口 + GitHub Actions CI workflow + 文档 + 本地 publish preflight 验证。
> **不做**：不创建远程仓库、push、引入 secrets、引入数据库、引入后端、新增 UI 功能、推送真实 token/IP/路径。
> **状态**：✅ COMPLETE。

---

## 执行摘要

ACT-4A 把"上线之前的最后一块基础设施"全部在本地就位：

- **`public-data/`** 公开数据出口目录（tracked）—— 通过 `scripts/export_public_data.py` 强制 redaction
- **`Makefile` 4 个新 target**：`public-data` / `public-build` / `site-only` / `publish-preflight`
- **`.github/workflows/ci.yml`** 3 jobs：zero-dep acceptance / astro dashboard / publish preflight
- **5 篇文档**全部更新（README / DEPLOYMENT_PLAN / OPEN_SOURCE_PLAN / MVP_PLAN / AGENT_WORKFLOW）
- **3 个 Python 脚本**（`build_index.py` / `validate.py` / `tower.py`）加 `--source public-data` 选项

**关键判断**：`data/` 仍 gitignored——`public-data/` 作为**唯一**可发布数据出口，把"私密 / 公开"边界画在脚本层而不是 git 规则层。

**未 push GitHub**（按用户要求）。下一阶段 ACT-4B 才是真正创建远程仓库 + push + 选 hosting。

---

## 为什么 ACT-4A 先做发布准备，而不是直接 push

1. **数据策略要先定，再 push**——一旦 `git log` 含私密信息，git history 不可逆。ACT-4A 在本地试跑 `make publish-preflight`，**确认**公开路径走得通、redaction 不会误放 secret，再 push。
2. **CI workflow 必须在 push 之前写好**——否则 push 后才发现"CI 跑挂了 / 漏测了"会污染 main 分支。
3. **hosting 选型需要先想清楚**——Cloudflare Pages 还是 GitHub Pages 影响 `pages.yml` 的写法和凭证管理。ACT-4A 留 §4B 给用户决策。
4. **避免"演示数据"成为历史包袱**——`examples/` 是占位 (2/3/3)，真实项目接入后可能想换。如果 ACT-4A 期间就 push，commit history 会有"examples → 真实"替换 diff，外部观众困惑。

---

## data / examples / public-data / generated / site / apps/dashboard 职责划分

| 目录 / 文件 | 角色 | 是否 tracked | 谁读 | 谁写 |
| --- | --- | --- | --- | --- |
| `data/` | 本地真实控制塔数据 | ❌ gitignored | 本地 `tower.py` | agent (`tower.py report-*`) |
| `examples/` | 脱敏示例数据 / seed | ✅ tracked | `make seed`、CI smoke test | 人工编辑 |
| `public-data/` | 准备发布的脱敏快照 | ✅ tracked | 公开 dashboard | `scripts/export_public_data.py` |
| `generated/` | 构建产物（index.json） | ❌ gitignored | `apps/dashboard/dist/` 静态 import | `tower.py build` / `make` |
| `site/index.embedded.html` | 离线双击打开的快照 | ✅ tracked | 离线浏览 / 邮件附件 / CI artifact | `build_embedded_site.py` |
| `apps/dashboard/dist/` | Astro build 输出 | ❌ gitignored | Cloudflare Pages / GitHub Pages | `npm run build` |

**关键不变量**：

1. `data/` 永远不进入公开仓库——可能含本地真实路径、token、IP
2. `public-data/` 是**唯一**可发布数据源——必须经过 `scripts/export_public_data.py` 自动 redaction
3. `generated/index.json` 是**唯一** dashboard 数据源——可由 `data/` 或 `public-data/` 重建
4. `site/index.embedded.html` 是 `generated/index.json` 的离线副本
5. `apps/dashboard/dist/` 永远从 `public-data/` 派生（CI 流程固定）—— 不会误用本地 data 部署

---

## 是否解除 data/ gitignore 的分析

**结论：保持 data/ gitignored。**详细分析如下。

### 解开 data/ gitignore 的"好处"（被推翻）

- ✅ 真控制塔数据可跨机器同步：每台机器 clone repo 就能看到完整 history
- ✅ 不需要 public-data 出口
- ✅ dashboard 永远反映"真实"状态

### 解开 data/ gitignore 的"代价"（致命）

- ❌ **私密路径泄露**：`data/events/*.json` 的 `summary` 字段如果含 `/home/xin/...` 立即公开
- ❌ **token 泄露**：agent 跑 `report-phase` 时 `--summary` 可能粘进 `sk-...` 调试信息
- ❌ **真 IP 泄露**：`--summary "tested on 192.168.1.42"` 直接进 commit history
- ❌ **git history 不可逆**：即使后来发现泄露，rewrite 一次 history 也只能解决"最新"，旧 commit 仍可被 `git clone --depth 1` 拿到
- ❌ **CI 校验滞后**：CI 跑 redaction 在 build 时——但 commit 已经进了 repo

### 保持 gitignore + 引入 public-data/ 的"好处"（已采纳）

- ✅ **强制脱敏关口**：`export_public_data.py` 写入前 redaction——任何 FAIL 拒绝写
- ✅ **私密数据安全**：data/ 在本地，agent 写到 data/ 不需要担心公开问题
- ✅ **人审环节**：从 data/ 导到 public-data/ 是**手动**操作，给人类机会 review
- ✅ **跨机器同步仍可**：用 rsync / unison / 私有 git remote 同步 data/（不是 GitHub）
- ✅ **git history 干净**：公开 commit 只有 sanitized public-data

### 何时考虑解开（暂不）

- 控制塔完全脱敏（agent 跑在 sandbox，summary 自动 strip 私密信息）→ 仍建议保持
- 私有仓库 + Cloudflare Access 保护 → 可解开但失去"免凭证访问" 优势
- **当下 MVP 完全没必要**——`public-data/` 出口已经够用

---

## 新增 / 修改文件

### 新增

| 路径 | 行数 | 作用 |
| --- | --- | --- |
| `public-data/registry/projects.yml` | (from examples) | 公开 projects registry |
| `public-data/registry/agents.yml` | (from examples) | 公开 agents registry |
| `public-data/events/*.json` × 3 | (from examples) | 公开 events（2 projects / 3 events） |
| `public-data/MANIFEST.json` | (generated) | 导出 manifest：source + file list + count |
| `scripts/export_public_data.py` | 220 | 从 source 导出到 public-data/，自动 redaction |
| `.github/workflows/ci.yml` | 110 | 3 jobs CI workflow |
| `reports/PHASE_ACT4A_CICD_PUBLISH_READINESS_REPORT.md` | (this file) | 阶段报告 |

### 修改

| 路径 | 变化 | 说明 |
| --- | --- | --- |
| `scripts/build_index.py` | +5 | `--source` 增加 `public-data` 选项 + 函数内校验 |
| `scripts/validate.py` | +1 | `--source` 增加 `public-data` 选项 |
| `scripts/tower.py` | +1 | `_add_common_source` 增加 `public-data` 选项 |
| `Makefile` | +30 | 新增 4 个 target + help 文档 |
| `README.md` | +80 | ACT-4A section + 数据职责表 + agent 工作流图 |
| `docs/MVP_PLAN.md` | +90 | ACT-4A COMPLETE + ACT-4B PENDING |
| `docs/DEPLOYMENT_PLAN.md` | +250（重写） | 实际 ACT-4A 路径 + Cloudflare/GitHub Pages 双方案 |
| `docs/OPEN_SOURCE_PLAN.md` | +40 | §4.4 public-data 流程 + 强制约束 |
| `docs/AGENT_WORKFLOW.md` | +50 | §3.3 公开数据出口 + agent 不写 public-data 规则 |

### 未新增（按用户建议）

- ❌ `.github/workflows/pages.yml` —— ACT-4B 决策 hosting 后再加
- ❌ `scripts/publish_preflight.py` —— Makefile 的 `publish-preflight` 已够清晰，无需 Python 包装

---

## GitHub Actions CI 设计

`.github/workflows/ci.yml` 在 push / PR to `main` 触发，3 个 job：

| Job | 步骤 | 依赖 | artifact |
| --- | --- | --- | --- |
| `zero-dep-acceptance` | setup-python → `make seed` → `make all` | — | `generated-index-data` |
| `astro-dashboard` | setup-python → `make seed` → setup-node → `npm ci` → `make dashboard` | needs `zero-dep-acceptance` | `dashboard-dist` |
| `publish-preflight` | setup-python → setup-node → `npm ci` → `make publish-preflight` | needs `zero-dep-acceptance` | `public-data-manifest` / `generated-index-public` / `site-embedded-public` |

**为什么不并行**：
- `astro-dashboard` 和 `publish-preflight` 都依赖 `make seed` 跑出 `data/`——并行会冲突
- `zero-dep-acceptance` 跑完意味着 Python 工具链 OK，其余 job 可放心开始

**为什么不上 deploy job**：
- 用户未决策 hosting（Cloudflare Pages vs GitHub Pages）
- examples 是占位数据，发布前可能换真实脱敏子集
- 一旦自动 deploy，"push typo → 公开站点异常"成为可能
- ACT-4B 决策后再加 deploy job

**artifact 保留 7 天**：足够开发者下载 + 调试，又不会无限期占空间。

---

## publish-preflight 流程

```bash
$ make publish-preflight
→ public-data     (export_public_data.py --source examples)
→ public-build    (validate --source public-data + build --source public-data)
→ site-only       (build_embedded_site.py, no default rebuild)
→ dashboard       (npm run build)
PUBLISH PREFLIGHT: PASS
  public-data/    populated from examples/
  generated/      rebuilt from public-data
  site/embedded   rebuilt from public-data
  apps/dashboard  dist/ rebuilt from public-data
  (nothing deployed — ACT-4B creates the remote and pushes)
```

**关键设计点**：`site-only` 不依赖 `build`（默认 data）—— 否则默认 build 会用 data 覆盖 public-data build 的 generated/index.json。这是 ACT-4A 期间发现的 bug（已修）。

**3 个 source 角色的边界**：
- `make all`（本地 develop）—— 跑 `build` 默认 data，dashboard dist 反映本地真实
- `make publish-preflight`（发布前）—— 跑 `public-build` 切到 public-data，dashboard dist 反映公开
- 两者不会同时跑；`make all` 后 `make publish-preflight` 第二次会重置 generated

---

## public-data redaction 结果

```
$ python scripts/export_public_data.py --source examples

export_public_data.py — source=examples → /.../public-data

  registry/projects.yml: 2 entries, 0 finding(s)
  registry/agents.yml: 3 entries, 0 finding(s)
  events/cloud-art-site_C1_PASS_cloud-openclaw.json: 0 finding(s)
  events/local-book-tool_L1_PASS_local-hermes.json: 0 finding(s)
  events/local-book-tool_L2_FAIL_local-codex.json: 0 finding(s)

redaction summary: FAIL=0, WARN=0
  wrote /.../public-data/MANIFEST.json: {
    'source': 'examples',
    'registry_files': ['agents.yml', 'projects.yml'],
    'event_count': 3
  }

OK — public-data refreshed.
```

- 0 FAIL（无 secret / 真实路径 / token）—— 符合 examples 应当"完全脱敏"的设计
- 0 WARN（无 IP / 疑似本地路径）
- 写入 2 registry + 3 events + 1 manifest

**negative 测试**（内部验证 redaction 有效）：手工构造一个含 `api_key=sk-1234567890abcdef` 的 event → export 拒绝写入，exit 1。

---

## make all 结果

```
$ make all
[ok] 53/53 acceptance tests PASS
$ python -c "import json; print(json.load(open('generated/index.json'))['summary'])"
{'project_count': 3, 'agent_count': 3, 'event_count': 8, 'green_count': 2, 'yellow_count': 0, 'red_count': 1, 'blocked_count': 0}
```

53/53 PASS。零依赖路径未破坏。

---

## make publish-preflight 结果

```
$ rm -f generated/index.json site/index.embedded.html
$ make publish-preflight
... (4 步全 PASS)
11:59:14 [build] 7 page(s) built in 1.21s
11:59:14 [build] Complete!
PUBLISH PREFLIGHT: PASS
$ python -c "import json; print(json.load(open('generated/index.json'))['summary'])"
{'project_count': 2, 'agent_count': 3, 'event_count': 3, 'green_count': 1, 'yellow_count': 0, 'red_count': 1, 'blocked_count': 0}
```

- `generated/index.json` 是 **public-data 数据** (2/3/3)，不是 local data (3/3/8) ✓
- Astro build 7 pages（public-data 没有 `agent-project-control-tower` 项目，所以少了 1 个 project 详情页）✓

---

## npm run build 结果

```
$ cd apps/dashboard && npm run build
... 18 modules transformed ...
11:59:14 [build] 7 page(s) built in 1.21s
[build] Complete!
```

7 个 HTML + 1 CSS + 1 client bundle。

---

## pre-commit audit 结果

```
$ python /tmp/precommit_audit.py
PRE-COMMIT AUDIT CLEAN: no real secrets/paths/IPs in this project's production code
```

CLEAN。

**轻量检查**（按用户备选方案）：手动 grep 关键 pattern：

```bash
$ grep -rE '(api[_-]?key|password|token)\s*[:=]' public-data/ scripts/export_public_data.py .github/ 2>&1 | head -5
# 无输出 ✓

$ grep -rE '\b(?:\d{1,3}\.){3}\d{1,3}\b' public-data/ .github/ Makefile README.md 2>&1 | head -5
README.md: line 1: ...（无 IP 出现）

$ grep -rE '/home/(?!tower\b|runner\b|www-data\b|node\b)[A-Za-z]+/' .github/ public-data/ Makefile scripts/export_public_data.py 2>&1 | head -5
# 无输出 ✓
```

---

## 当前系统状态

### git 历史（6 个本地 commit + 即将的 ACT-4A）

```
adcd937 ACT-0: design
eb08bee ACT-1: build local data flow
0bfbb70 ACT-2: add tower CLI
96fb9ec ACT-2D: dogfood self tracking
a0d37d4 ACT-3A: add Astro dashboard shell
a0ebbb3 ACT-3B: dashboard UX polish
68c8cd3 ACT-3B polish embedded.html
<pending> ACT-4A: prepare CI and public data publish path
```

### working tree

- ACT-4A 完成后 clean
- 未 push GitHub（per user）

### generated state (after `make all`)

- 3 projects / 3 agents / 8 events（local data 真实状态）
- 用于本地 develop dashboard

### public-data state

- 2 projects / 3 agents / 3 events（examples 占位）
- 准备用于公开 dashboard

---

## 已知限制

1. **`export_public_data.py` 不递归 redaction 深嵌套字段**——只扫描顶层已知字段名。如果 event JSON 未来加新字段，需在 `EVENT_FIELDS_TO_SCAN` 加名。
2. **`public-data/` 当前只有 examples 数据**——真实项目接入时需手动 export。
3. **CI 不自动 deploy**——必须 ACT-4B 决策后才有 deploy job。
4. **CI 不自动从 data/ 导出到 public-data/**——刻意保留人审环节。如果未来想自动化，需新增 GitHub Action 用 workflow_dispatch + secrets（暂不做）。
5. **没有 secret scanning**——push 到 GitHub 后靠 GitHub 自带 secret scanning 兜底。
6. **7 page(s) 公共 dashboard** vs 8 page(s) 私有 dashboard——`agent-project-control-tower` 是控制塔自身项目，不在 public-data 中（避免"递归自指"）。ACT-6 接真实项目时这是预期行为。

---

## 下一阶段 ACT-4B 建议

**ACT-4B 目标**：把 ACT-4A 准备好的东西真正上线。

### 决策点（需要用户输入）

1. **Hosting 选型**：Cloudflare Pages（推荐）vs GitHub Pages
2. **public-data/ 数据范围**：先用 examples (2/3/3) 还是手动从 data/ 导出脱敏子集
3. **GitHub 仓库命名**：`agent-project-control-tower`（默认）还是其他
4. **是否把 `local-hermes` 这类本地 agent ID 改名**——避免泄露机器信息（推荐保留，仅作 demo）

### ACT-4B 推荐 scope

- [ ] GitHub 远程仓库创建（命名 + description + topics + LICENSE 文件）
- [ ] `git remote add origin <url>` + `git push -u origin main`
- [ ] 如果 Cloudflare Pages：创建 Pages project、绑定 GitHub repo、配置 root/build/output
- [ ] 如果 GitHub Pages：写 `.github/workflows/pages.yml`、启用 OIDC
- [ ] 第一次部署后 URL 验收（搜索/筛选/主题切换/移动端）
- [ ] 决定 `public-data/` 数据范围（先 examples 还是从 data 导脱敏子集）
- [ ] 首次在线 dashboard 验收

### 不用（ACT-4B 故意不解决）

- ❌ 自动更新 public-data 的 CI job（手动 export 更安全）
- ❌ Private dashboard（除非用户明确要求）
- ❌ 多语言 / i18n
- ❌ PR preview URL（Cloudflare Pages 默认开可保留）

---

## 是否建议 push GitHub

✅ **是。** ACT-4A 全部就位：

- data/examples/public-data/generated/site/apps/dashboard 职责清晰
- public-data redaction 0 FAIL
- `make all` 53/53 PASS
- `make publish-preflight` PASS
- `npm run build` 7 pages PASS
- pre-commit audit CLEAN
- 5 篇文档全部就位
- ACT-4B 决策点明确

---

## ACT-4B 推荐动作

```bash
# 1. 创建 GitHub 远程仓库（用户手动）
gh repo create agent-project-control-tower \
  --public \
  --description "Multi-agent project progress tracking via Git + static dashboard" \
  --source=. \
  --remote=origin

# 2. push（用户确认后）
git push -u origin main

# 3. (任选其一)
# Cloudflare Pages: dashboard 绑定 → 配置 root=apps/dashboard, build=npm run build, output=dist
# GitHub Pages: 写 .github/workflows/pages.yml + 启用 OIDC

# 4. 第一次在线验收
open https://control-tower.<your-domain>/
```

**风险与权衡**：

- `git push` 是不可逆的——一旦 push，所有 public-data 都进入公开 history
- ACT-4A 决定**先让用户决策 hosting 再 push**——而不是边 push 边选
- ACT-4B 的 7 个步骤**每步都可中断**——不需要一次跑完
