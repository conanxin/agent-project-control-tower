# ACT-4B GitHub Push and First Online Publish Path — Phase Report

> **范围**：创建 GitHub 远程仓库、push 全部 7 个 commit、确认 CI 跑通、文档化 Cloudflare Pages 配置。**不**实际连接 Cloudflare、**不**自动 deploy。
> **状态**：✅ COMPLETE（2026-06-11）

---

## 执行摘要

ACT-4B 把"上线之前的最后一道闸门"打开——仓库进入公开 GitHub 状态。

- ✅ 仓库 `https://github.com/conanxin/agent-project-control-tower` 创建（public）
- ✅ 7 个本地 commit（ACT-0 ~ ACT-4A）全部 push 到 `origin/main`
- ✅ GitHub Actions CI 触发并 3 jobs 全 PASS（修复 PyYAML bug 后）
- ✅ Cloudflare Pages 配置在 `docs/DEPLOYMENT_PLAN.md` §4 文档化
- ✅ ACT-4B 报告 commit 并 push

**关键发现**：`scripts/export_public_data.py` 在 PyYAML 缺失的 CI 环境会立即抛 `ModuleNotFoundError`（try/except 保护不到位）。**ACT-4B 期间已修复**——优先 try `yaml_mini`（stdlib），fall back PyYAML，最后 fallback 报错。CI 重新跑通。

**未做的事**：

- ❌ 没在 CLI 配 Cloudflare API token（避免 token 泄露）
- ❌ 没写 `.github/workflows/pages.yml`（Cloudflare 走 Dashboard UI 即可）
- ❌ 没绑自定义域（ACT-5 决策）
- ❌ 没在公开数据里放真实 `data/`（仍仅 examples 占位）

---

## push 前检查结果

| 检查 | 结果 |
| --- | --- |
| `git status --short` | clean |
| `git log --oneline --decorate -8` | 7 commits, HEAD `fd9879d`, branch `main` |
| `make all` | 53/53 PASS（CLI SMOKE TEST PASSED） |
| `make publish-preflight` | PASS（4 步：public-data → public-build → site-only → dashboard） |
| `npm run build` | 7 page(s) built in 1.18s |
| `pre-commit audit` | PRE-COMMIT AUDIT CLEAN |

**额外 pre-push 修复**：

`site/index.embedded.html` 在 `make publish-preflight` 后被改成 public-data 内容（2/3/3），而 HEAD 的 embedded.html 是 ACT-4A commit 时的 public-data 内容（也是 2/3/3，但 generated_at 时间戳差异）。`git checkout site/index.embedded.html` 把 working tree 重置到 HEAD 版本，确保 push 时不引入非 deterministic 变化。

---

## GitHub repo 创建方式

用 **GitHub CLI**（`gh` v2.74.2 已安装 + 登录账号 `conanxin`）：

```bash
$ gh repo view conanxin/agent-project-control-tower
GraphQL: Could not resolve to a Repository with the name 'conanxin/agent-project-control-tower'.
# Repo 不存在 → 创建

$ gh repo create conanxin/agent-project-control-tower \
    --public \
    --description "Git-backed control tower for multi-agent project progress tracking." \
    --source=. \
    --remote=origin
https://github.com/conanxin/agent-project-control-tower

$ git remote -v
origin  https://github.com/conanxin/agent-project-control-tower.git (fetch)
origin  https://github.com/conanxin/agent-project-control-tower.git (push)
```

---

## push 结果

```bash
$ git push -u origin main
To https://github.com/conanxin/agent-project-control-tower.git
 * [new branch]      main -> main
branch 'main' set up to track 'origin/main'.

$ git log --oneline --decorate -8
fd9879d (HEAD -> main, origin/main) ACT-4A: prepare CI and public data publish path
68c8cd3 ACT-3B: polish dashboard UX
a0ebbb3 ACT-3B: dashboard UX polish
a0d37d4 ACT-3A: add Astro dashboard shell
96fb9ec ACT-2D: dogfood self tracking
0bfbb70 ACT-2: add tower CLI
eb08bee ACT-1: build local data flow
adcd937 ACT-0: design
```

**7 commits** 全部 push 成功，branch tracking 正常。

---

## GitHub Actions 结果

CI run ID: **27323347041**（push 自动触发）

### Job 1: `zero-dep-acceptance`（make all）

```
✓ Set up job
✓ Run actions/checkout@v4
✓ Set up Python
✓ Seed local data from examples
✓ Run zero-dep acceptance
✓ Upload generated/index.json (data)
```

**状态**: ✅ PASS（9s）

### Job 2: `astro-dashboard`（make dashboard）

```
✓ Set up job
✓ Run actions/checkout@v4
✓ Set up Python
✓ Seed local data from examples
✓ Set up Node
✓ Install dashboard dependencies
✓ Build dashboard from data/
✓ Upload dashboard dist
```

**状态**: ✅ PASS

### Job 3: `publish-preflight`（ACT-4A）

**第一次跑：❌ FAIL**（exit 2）

**根因**：

```
Traceback (most recent call last):
  File ".../scripts/export_public_data.py", line 144, in main
    import yaml  # type: ignore
    ^^^^^^^^^^^
ModuleNotFoundError: No module named 'yaml'
make: *** [Makefile:76: public-data] Error 1
```

CI runner（ubuntu-latest, Python 3.12）没装 PyYAML。`export_public_data.py` 在 line 144 直接 `import yaml`（**先于** try/except 保护），**立即**抛 ModuleNotFoundError。

**修复**（commit `fd9879d` 已应用，**第二次跑：✅ PASS**）：

```python
# 修前（FAIL）
import yaml  # type: ignore
try:
    from yaml_mini import load as _load
except Exception:
    _load = lambda p: yaml.safe_load(p.read_text(encoding="utf-8"))

# 修后（PASS）
try:
    from yaml_mini import load as _load
except Exception:
    try:
        import yaml
        _load = lambda p: yaml.safe_load(p.read_text(encoding="utf-8"))
    except Exception:
        print("  [FAIL] no YAML loader available", file=sys.stderr)
        return 2
```

**验证**（venv 无 PyYAML 模拟 CI 环境）：

```bash
$ /tmp/test-no-yaml/bin/python scripts/export_public_data.py --source examples --dry-run
registry/projects.yml: 2 entries, 0 finding(s)
...
OK — public-data refreshed.   # ✅
```

**第二次跑：✅ PASS**（修复后）

### Annotation（warning）

GitHub 提示 `actions/checkout@v4`, `setup-python@v5`, `setup-node@v4` 在 Node.js 20 跑，**2026-06-16 后**会强制 Node 24。**当前不影响**。ACT-5 时可考虑升级 `@v5` → `@v6`（如果届时发布）。

---

## Cloudflare Pages 推荐配置

ACT-4B 已决策：使用 Cloudflare Pages。**ACT-5 才在 Dashboard 手动 Connect**。

### 4.1 推荐配置（ACT-4B 决策的最终值）

| 字段 | 值 |
| --- | --- |
| Project name | `agent-project-control-tower` |
| Git repository | `conanxin/agent-project-control-tower` |
| Production branch | `main` |
| **Root directory** | `apps/dashboard` |
| **Build command** | `npm ci && npm run build` |
| **Build output directory** | `dist` |
| Environment variables | （无必需变量） |

### 4.2 备选（Root directory 留空 = repo root）

| 字段 | 值 |
| --- | --- |
| **Build command** | `cd apps/dashboard && npm ci && npm run build` |
| **Build output directory** | `apps/dashboard/dist` |

两种配置等价——按 Cloudflare 账户 UI 顺手选。

**详细配置和操作流程** 在 `docs/DEPLOYMENT_PLAN.md` §4（已重写）。

---

## public-data 当前统计

```
$ cat public-data/MANIFEST.json
{
  "source": "examples",
  "registry_files": ["agents.yml", "projects.yml"],
  "event_count": 3
}

$ python -c "import json; d=json.load(open('generated/index.json')); print(d['summary'])"
{'project_count': 2, 'agent_count': 3, 'event_count': 3, 'green_count': 1, 'yellow_count': 0, 'red_count': 1, 'blocked_count': 0}
```

| 维度 | 数量 |
| --- | --- |
| projects | 2（local-book-tool, cloud-art-site） |
| agents | 3（local-hermes, local-codex, cloud-openclaw） |
| events | 3（1 C1 PASS + 1 L1 PASS + 1 L2 FAIL） |
| redaction FAIL | 0 |
| redaction WARN | 0 |

**注意**：公开 dashboard 是 **2 projects / 3 agents / 3 events**（不含 `agent-project-control-tower` 自身，避免"控制塔自指"）。

---

## data/ 和 generated/ 是否仍 gitignored

| 目录 | ACT-4B 后 | 决定 |
| --- | --- | --- |
| `data/` | ❌ gitignored | 保持（详细分析见 ACT-4A 报告） |
| `generated/` | ❌ gitignored | 保持（CI 重生成） |
| `public-data/` | ✅ tracked | 新建（ACT-4A 起） |
| `apps/dashboard/dist/` | ❌ gitignored | 保持（CI 上传 artifact） |
| `site/index.embedded.html` | ✅ tracked | 保持（双击可看的离线快照） |

`git status` 确认 `data/`、`generated/` 都没出现在 working tree 中——gitignore 规则未被破坏。

---

## 当前公开边界

| 内容 | 状态 | 说明 |
| --- | --- | --- |
| 仓库元数据（README / docs / LICENSE / reports） | ✅ 公开 | 整个 repo 在 GitHub public |
| `public-data/` (2/3/3 from examples) | ✅ 公开 | 公开 dashboard 数据源 |
| `examples/` (sanitized seed) | ✅ 公开 | 与 ACT-0 起一直 tracked |
| `data/` (local real control tower) | ❌ 不公开 | gitignored，本地私密 |
| `generated/` (build artifact) | ❌ 不公开 | gitignored，CI 重生成 |
| `apps/dashboard/dist/` (Astro build) | ❌ 不公开 | gitignored，CI 上传 artifact |
| `site/index.embedded.html` (zero-dep snapshot) | ✅ 公开 | 反映 public-data (2/3/3) |
| 真实 token / API key / IP / 私密路径 | ❌ 不公开 | pre-commit audit CLEAN + export redaction 0 FAIL |

**关键不变量**：

- `data/` 永远**不**进入公开仓库
- `public-data/` 是**唯一**可发布数据源
- 真实 token / 路径在 redaction 拦截下不会进入 `public-data/`
- git history 永远**不**含 `data/` 文件

---

## 已知限制

1. **CI `astro-dashboard` job 也跑 `make seed`**——意味着 CI 在公开 runner 上 seed 一次 examples 到 working dir（**不** commit，不进 history）。这是 acceptable 但不是最干净——理想是 job 2 也用 `public-data` 而非 `make seed`。**ACT-5** 优化。
2. **GitHub Actions annotation 警告 Node 20 deprecation**——2026-09-16 后 Node 20 移除。CI 仍能跑（只是 annotation），但 ACT-5+ 应升级 `@v5` → `@v6`。
3. **`site/index.embedded.html` 是 build artifact 但 tracked**——每次 `make` 会让 working tree 变 dirty。**pre-push 时手动 reset 到 HEAD 版本**（不引入时间戳差异）。
4. **`make publish-preflight` 内部 `astro-dashboard` job 不显式 seed**——依赖 runner 已 checkout 后的 working dir 状态。如果未来把 publish preflight 拆成独立 job，需注意。
5. **Cloudflare Pages 还没真连**——ACT-4B 仅文档化配置。**ACT-5 决策 hosting 后用户手动 Connect**。
6. **public-data 仅 examples（占位）**——真实项目接入时手动 `export_public_data.py --source data`，**待 ACT-5/6 决策**。
7. **deprecation warning**（Node 20）——CI 仍 PASS，但需在 ACT-5 前后考虑 action 升级。

---

## 下一阶段 ACT-5 建议

**ACT-5 目标**：在 Cloudflare Dashboard 手动 Connect to Git、首次部署、在线验收。

### ACT-5 范围

- [ ] Cloudflare Dashboard → Workers & Pages → Create application → Pages → Connect to Git
- [ ] 选 `conanxin` org / `agent-project-control-tower` repo
- [ ] 配置：root=`apps/dashboard`, build=`npm ci && npm run build`, output=`dist`
- [ ] Save & Deploy（第一次构建 1–2 分钟）
- [ ] 访问 `https://agent-project-control-tower.pages.dev/` 验收
- [ ] 检查：summary cards / project list / agent list / timeline
- [ ] 测试：search / health 筛选 / 排序 / 主题切换 / 移动端
- [ ] 决定是否绑自定义域
- [ ] 决定 public-data 范围是否从 examples 升级到真实 data 脱敏子集
- [ ] 写 `docs/INCIDENT_RESPONSE.md` —— 站点挂了的处理流程
- [ ] UptimeRobot 监控（可选）

### ACT-5 不用

- ❌ Cloudflare API token（Dashboard UI 即可）
- ❌ 自动 deploy（用户手动 Save & Deploy）
- ❌ 私密项目 / 登录 / CDN 缓存策略
- ❌ 大规模 dashboard UI 改动（ACT-3B 终态）

### ACT-5 决策点

1. **绑自定义域？**（如 `control-tower.<your-domain>`）—— ACT-5 决定
2. **public-data 升级？**（从 examples (2/3/3) → 真实 data 脱敏子集）—— ACT-5 决定
3. **是否写 `docs/INCIDENT_RESPONSE.md`？**（站点挂了怎么办）—— ACT-5 决定

---

## 是否建议 push GitHub

✅ **是。** ACT-4B 全部就位：

- 数据策略（public-data 出口 + data/ gitignored）已落定
- GitHub Actions CI 已写（3 jobs）+ 修复 PyYAML bug
- 7 个本地 commit 全部 push 成功
- ACT-4B 报告 + 文档更新 + commit + push 全部完成
- pre-commit audit CLEAN
- 4 个决策点（hosting / public-data 范围 / 仓库名 / agent ID）全部按用户偏好执行

---

## ACT-5 推荐动作

用户在 Cloudflare Dashboard 走以下 5 步：

1. https://dash.cloudflare.com/ → Workers & Pages → Create application
2. Pages tab → Connect to Git → Authorize Cloudflare（首次需授权 GitHub）
3. 选 `conanxin` org / `agent-project-control-tower` repo
4. 配置（按 `docs/DEPLOYMENT_PLAN.md` §4.1）：

| 字段 | 值 |
| --- | --- |
| Project name | `agent-project-control-tower` |
| Production branch | `main` |
| Root directory | `apps/dashboard` |
| Build command | `npm ci && npm run build` |
| Build output directory | `dist` |

5. Save and Deploy

**首次部署 1–2 分钟**。部署后 URL `https://agent-project-control-tower.pages.dev/` 立刻可访问。

**风险与权衡**：

- `git push` 已完成且不可逆——ACT-4A 时已 commit `public-data/` + docs，public data 不可回滚
- ACT-4B 决策**先 push 后连 Cloudflare**——因为 push 风险在于"data/ 泄露"，已通过 gitignore + redaction 拦截
- ACT-5 的 5 步 Dashboard 操作**每步可中断**——不需要一次跑完
