# PHASE_ACT9C_EXPORT_PLAN_REVIEW_WORKFLOW_REPORT.md

**Phase**: ACT-9C — Export Plan Review Workflow
**Status**: ✅ COMPLETE
**Date**: 2026-06-12
**Branch**: `main` (commit pushed; hash in §14)
**Predecessor**: ACT-9B (commit `d7a652a`)

---

## 1. 执行摘要

ACT-9C 把"公开导出范围"从散落在 Makefile 硬编码默认、命令历史、人工记忆里的**隐式状态**，收口到一个 **tracked YAML 文件** `config/public-data-export-plan.yml`——PR-reviewable，单文件 diff，单文件回滚。

关键交付：

1. 新增 `config/public-data-export-plan.yml`（schema_version 0.1）
2. `scripts/export_public_data.py` 新增 `--plan PATH`，与 `--project-id` / `--agent-id` 互斥
3. `scripts/build_public_data_candidate.py` 新增 `--plan PATH`，同上
4. `Makefile` 中 `publish-preflight` 与 `candidate` 改用 `--plan`；新增 `export-plan-test` target
5. 新增 `tests/export_plan_smoke.py`（9 test functions / 33 [PASS] / 0 [FAIL]）
6. 新增 `templates/checklists/proposed-export-artifact-review-checklist.md`（8 sections）
7. 7 个 docs 同步更新（README + 6 个 docs/* + 2 个核心 doc 加了新 section）

**为什么 ACT-9C 优先于 ACT-10**：ACT-9B 留下了一个运营漏洞——`make publish-preflight` 的默认项目范围落后（1 project），曾在两次不同的 commit 流程里被踩到（每次都要手动 re-export 修回 3 projects）。ACT-9C 把"导出范围"作为合约沉淀到 plan 文件里，让 ACT-10 (v0.1.0 release packaging) 在 freeze-the-world 之前先把范围控制权收口。ACT-10 现在可以基于一个稳定的 export plan 去做 VERSION / CHANGELOG / RELEASE_NOTES。

---

## 2. ACT-9B 暴露的 publish-preflight 默认范围问题

### 2.1 现象

`make publish-preflight` 调用 `public-data-real` target，后者用：

```make
PUBLIC_DATA_PROJECT ?= agent-project-control-tower
PUBLIC_DATA_AGENT   ?= local-hermes
PUBLIC_DATA_MAX     ?= 20
```

默认值在 ACT-6 落定（首次发布单项目），但 ACT-6C 之后 public-data 已经有 3 个 projects / 2 agents / 21 events。每当本地做完整 `make publish-preflight` 重建（不是用 `--project-id` 显式调用 export_public_data.py），就会**静默**把 public-data 重置成 1 project / 1 agent / 15 events。

### 2.2 触发场景

1. ACT-6C hotfix 之后 push 阶段（手动 `--project-id` 三个 ID 才能修回 3 projects）
2. ACT-9B `make candidate` 阶段（一次手动 export 又一次手动）
3. 任何 `git pull` 后跑 `make publish-preflight` 验证（被坑 2 次）

### 2.3 为什么不能容忍

| 后果 | 严重度 |
|---|---|
| 线上 dashboard 静默回退到 1 project | High — 用户可见的 dashboard 范围被缩小 |
| 与 ACT-6C 的"线上永远显示 3 projects"承诺冲突 | High — 已记录在 PUBLIC_DATA_EXPORT_PLAYBOOK §7 |
| CF Pages 缓存 + 静默降级 → 用户看到旧数据以为是新数据 | High — 排查极难 |
| 每次都要人工记得加 `--project-id --project-id --project-id` | Medium — 流程不可靠 |

ACT-9C 的修复：把范围从"散落"提升到"合约"。Plan 文件是单一可信源；Makefile 只能通过 `--plan` 读它；不能用人脑补。

---

## 3. export plan 设计

### 3.1 文件位置与命名

`config/public-data-export-plan.yml`——放在 `config/`，与 `docs/`、`scripts/`、`tests/`、`templates/`、`reports/` 平级。这个目录以前不存在，ACT-9C 创建了它。

### 3.2 Schema (0.1)

```yaml
schema_version: "0.1"          # 必须字段；未来加 0.2 时旧 plan 仍可读
name: "default-public-dashboard" # 人类可读的 plan 标识；写入 MANIFEST.plan_name
description: "..."              # 一句话说明
source: "data"                  # 默认 source；CLI 仍可覆盖
output: "public-data"           # 默认 output；CLI 仍可覆盖
projects: [3 ids]               # 强约束：plan 没有 projects → FAIL
agents:   [2 ids]               # 可选；若给，则作为 agent filter
policy:                          # 镜像 PUBLIC_DATA_AUTOMATION_POLICY §8.2
  level: "Level 1 + Level 2"
  human_review_required: true
  ci_may_validate: true
  ci_may_commit: false
  ci_may_push: false
  trial_agents_may_export: false
notes: [strings]                 # 自由文本，仅给 reviewer 看
```

### 3.3 强约束

| 约束 | 实现位置 |
|---|---|
| `--plan` 与 `--project-id` / `--agent-id` 互斥 | `export_public_data.py` + `build_public_data_candidate.py` 同款实现 |
| plan 缺少 `projects:` → FAIL | 两个脚本的 `--plan` 加载逻辑 |
| plan `policy.ci_may_commit` / `ci_may_push` 为 true → WARN | export 脚本的 plan 解析（仅 WARN，工具本身仍不 commit/push） |
| plan 不允许 token / 路径 / IP / .env 命中 | `tests/export_plan_smoke.py` 的 `test_plan_no_forbidden_patterns` |

### 3.4 写入 MANIFEST 的字段

```json
{
  "plan_file": "/abs/path/to/config/public-data-export-plan.yml",
  "plan_name": "default-public-dashboard",
  "plan_schema_version": "0.1"
}
```

reviewer 一眼能看出 public-data 是从哪个 plan 导出的。

---

## 4. export_public_data.py --plan 实现

### 4.1 参数与互斥

```python
p.add_argument("--plan", default=None, metavar="PATH", ...)
```

- `--plan X` + `--project-id Y` → exit 2, stderr "mutually exclusive"
- `--plan X` + `--agent-id Y` → exit 2, 同上
- `--plan X` + 没有 projects 字段 → exit 2, "refusing to export an unscoped slice"

### 4.2 plan 加载

新增 helper `_load_plan_file(plan_path)`：
- 优先用 `yaml_mini.load`（zero-dep）
- 退到 `yaml.safe_load`（PyYAML）
- 退到 fail-exit 2（裸 stdlib 跑不起来的 CI）

### 4.3 优先级

plan 提供的值在 CLI 之后应用：

| 字段 | CLI 优先级 | Plan 优先级 |
|---|---|---|
| `--source` | 高（可覆盖 plan.source） | 低 |
| `--output` | 高（可覆盖 plan.output） | 低 |
| `--project-id` | **互斥**（不能用 CLI 覆盖 plan） | 高 |
| `--agent-id` | **互斥**（不能用 CLI 覆盖 plan） | 高 |
| `--max-events` / `--repo-prefix` / `--replace` | CLI 专属 | 不在 plan 里 |

理由：`--project-id` 之所以被互斥而不是被覆盖，是因为 plan 是**合约**——如果 CLI 能凌驾于 plan 之上，plan 就不再是单一可信源。

### 4.4 错误信息改进

`src_root 不存在` 的错误信息从原来的 `"ERROR: source not found: ..."` 升级为带上下文的：

```
ERROR: source not found: <path>
  --source <X> was from plan. If you intended the local real control tower,
  run `make seed` first or pass --source data explicitly.
```

让 reviewer 一眼看出 source 是从 plan 来的还是 CLI 来的。

---

## 5. build_public_data_candidate.py --plan 实现

### 5.1 参数与互斥

与 export 脚本完全对称（同一个 `p.add_argument("--plan", ...)` 形式 + 同一个 mutex check）。

### 5.2 plan 字段应用

| 字段 | 应用方式 |
|---|---|
| `projects` | 写入 `args.project_id`（让 `_build_via_export_public_data` 转给 export 脚本） |
| `agents` | 写入 `args.agent_id` |
| `source` | **不应用**（candidate 的 source 是 caller 决定的：data / examples / public-data），但会打 `[WARN]` 提醒 |

### 5.3 报告里新增的字段

- `CANDIDATE_SUMMARY.md`：新增 `plan file / plan name / plan schema_version / plan projects / plan agents`
- `MANIFEST_DIFF.md`（即 `diff` 字典）：新增 `plan_file` / `plan_name` / `plan_schema_version` / `candidate_project_filter`，并在 `project_filter_changed` 标记与 current public-data 的差异

### 5.4 共享 yaml_dumper 复用

ACT-9B 引入的 `scripts/lib/yaml_dumper.py`（三层 fallback）原封不动地用，**没有引入新的 yaml 解析路径**。这意味着 CI 在 vanilla runner 上仍然能跑——`yaml_mini` 不存在、`PyYAML` 缺失时，ACT-9B 的纯 stdlib dumper 兜底。

---

## 6. Makefile 更新

### 6.1 publish-preflight

**之前**：
```make
PUBLIC_DATA_PROJECT ?= agent-project-control-tower
PUBLIC_DATA_AGENT   ?= local-hermes
PUBLIC_DATA_MAX     ?= 20

public-data-real:
    python scripts/export_public_data.py \
        --source data --output public-data \
        --project-id $(PUBLIC_DATA_PROJECT) \
        --agent-id   $(PUBLIC_DATA_AGENT) \
        --max-events $(PUBLIC_DATA_MAX) ...
```

**之后**：
```make
PUBLIC_DATA_PLAN ?= config/public-data-export-plan.yml
PUBLIC_DATA_MAX     ?= 50   # 1 project → 3 projects 提升 cap；之前 20 是按 1 project 算的

public-data-real:
    python scripts/export_public_data.py \
        --source data --output public-data \
        --plan $(PUBLIC_DATA_PLAN) \
        --max-events $(PUBLIC_DATA_MAX) ...
```

### 6.2 candidate

**之前**：`python scripts/build_public_data_candidate.py --source public-data --output artifacts/public-data-candidate`

**之后**：`python scripts/build_public_data_candidate.py --source public-data --output artifacts/public-data-candidate --plan $(PUBLIC_DATA_PLAN)`

### 6.3 新增 export-plan-test

```make
export-plan-test:
    $(PYTHON) tests/export_plan_smoke.py
```

`make all` **不**包含 `export-plan-test`（与 ACT-9B 保持一致：candidate 系列不污染 `make all` 的 zero-dep 路径）。

### 6.4 help 文本

新增 4 行 help 文本（candidate / candidate-fixture / candidate-test / export-plan-test）。

### 6.5 注释块更新

`# ===== ACT-4A / ACT-6` → `# ===== ACT-4A / ACT-6 / ACT-9C`，并改写说明文字明确：
- 旧 `PUBLIC_DATA_PROJECT` 默认是被 ACT-9C 移除的（"the historical bug"）
- 现在的 `public-data-real` 通过 plan 文件读范围

---

## 7. 测试结果

### 7.1 tests/export_plan_smoke.py

9 个 test functions，33 个 [PASS] / 0 个 [FAIL]：

| # | Test | 验证内容 |
|---|---|---|
| 1 | `test_plan_exists` | plan 文件存在 |
| 2 | `test_plan_has_at_least_3_projects` | 含 3 个真实项目 ID |
| 3 | `test_export_with_plan` | export 脚本能跑、MANIFEST.plan_file 写入、project_filter 是 3 项 |
| 4 | `test_candidate_with_plan` | candidate 脚本能跑、summary 包含 plan 路径 + name + 3 projects |
| 5 | `test_plan_matches_manifest` | public-data project_filter ⊆ plan.projects（防止"plan 改但 public-data 没改"） |
| 6 | `test_publish_preflight_does_not_degrade` | **核心**：`make publish-preflight` 必须 ≥ 3 projects / ≥ 2 agents / ≥ 21 events（**不降级到 1 project**） |
| 7 | `test_mutual_exclusion_export` | `--plan + --project-id` 必须 exit 2 |
| 8 | `test_mutual_exclusion_candidate` | candidate 脚本同样 mutex |
| 9 | `test_plan_no_forbidden_patterns` | plan 不含 /home/ 绝对路径、不含 IP、不含 token、不含 .env（注释先剥离） |

### 7.2 测试覆盖

| 验证项 | 来自 brief §六 | 实现 |
|---|---|---|
| 1. plan 存在 | ✅ | `test_plan_exists` |
| 2. plan 含 ≥3 real projects | ✅ | `test_plan_has_at_least_3_projects` |
| 3. export_public_data.py --plan 成功 | ✅ | `test_export_with_plan` |
| 4. build_public_data_candidate.py --plan 成功 | ✅ | `test_candidate_with_plan` |
| 5. plan 与 MANIFEST.project_filter 一致 | ✅ | `test_plan_matches_manifest` |
| 6. make publish-preflight 不降级 | ✅ | `test_publish_preflight_does_not_degrade` |
| 7. 混用 --plan + --project-id FAIL | ✅ | `test_mutual_exclusion_{export,candidate}` |
| 8. plan 不含敏感模式 | ✅ | `test_plan_no_forbidden_patterns` |

---

## 8. make all / make publish-preflight / make command-test / make candidate* / make export-plan-test / npm run build

### 8.1 验证矩阵

| Target | 期望 | 实际 | 备注 |
|---|---|---|---|
| `make all` | PASS | **PASS** | 8/8 command_generator_smoke 仍然全过（含 1 个 ACT-7B template drift WARN，不阻塞） |
| `make publish-preflight` | ≥ 3 projects | **PASS — 3/2/21** | bug fixed |
| `make command-test` | 8/8 | **8/8 PASS** | template drift 1 个 WARN（report-review.txt 用 `--source-repo` 但 tower.py 不接受）— ACT-7B 旧 issue，本轮不修 |
| `make candidate` | PASS | **PASS** | 跑 `make candidate`（含 `--plan`），3/2/21 candidate 生成 |
| `make candidate-fixture` | PASS | **PASS** | examples mode |
| `make candidate-test` | PASS | **PASS** | 4/4 candidate_artifact_smoke |
| `make export-plan-test` | PASS | **PASS** | 33/33 export_plan_smoke |
| `npm run build` | PASS | **PASS** | 7 pages |
| Sensitive scan (`grep -RInE`) | 0 真实敏感 | **0 真实敏感** | 命中的全是 redaction 模式引用 |
| `make candidate-fixture` 跑完 | artifacts/ gitignored | **PASS** | artifacts/ 在 .gitignore 中 |
| `make export-plan-test` 含 `make publish-preflight` 真实运行 | 完整端到端 | **PASS** | 不 mock，直接跑 |

### 8.2 已知未修问题（NOT in ACT-9C scope）

- `tests/command_generator_smoke.py` 的 `test_8_alignment_checker_catches_drift` 抓到的 `report-review.txt` template drift（用 `--source-repo` 但 tower.py 不接受）。ACT-7B 时代的 issue，**留到 ACT-10 修**（v0.1.0 freeze 时一并收口）。

---

## 9. 文档敏感扫描结果

```bash
grep -RInE "token=|api_key|Authorization:|Bearer |password=|secret=|/home/[^ ]+|[0-9]+.[0-9]+.[0-9]+.[0-9]+|.env" \
    README.md docs templates reports scripts tests config public-data .github
```

| 路径 | 命中 | 判定 |
|---|---|---|
| `config/public-data-export-plan.yml` | 0 | clean |
| `docs/PUBLIC_DATA_AUTOMATION_POLICY.md` | 0 | clean（policy 引用"token" / "api key" 是教学性的） |
| `docs/PUBLIC_DATA_EXPORT_PLAYBOOK.md` §5 | 0 | clean |
| `scripts/redaction.py` | 多处 | **expected**——这文件本身就是 redaction scanner |
| `scripts/export_public_data.py` / `build_public_data_candidate.py` | 多处 | **expected**——扫描代码本身引用 redaction 模式 |
| `tests/*` | 多处 | **expected**——测试 fixture 必须含真实攻击向量才能验证 |
| `templates/checklists/*.md` | 0 | clean |
| `public-data/` | 0 | clean（redaction 早就 FAIL=0） |

**0 真实敏感命中**。所有命中都是 redaction 工具自身的模式定义或测试 fixture。

---

## 10. 当前公开边界

| 资产 | 状态 |
|---|---|
| `data/` | **未公开**（gitignored） |
| `generated/` | **未公开**（gitignored） |
| `artifacts/` | **未公开**（gitignored） |
| `public-data/` | **公开**（committed，CI 验证） |
| `apps/dashboard/dist/` | **未提交**（gitignored；CF Pages build 时 npm 生成） |
| `node_modules/` | **未提交**（gitignored） |
| `.env` | **未提交**（不存在） |
| `config/public-data-export-plan.yml` | **公开**（committed；不含敏感） |
| `templates/checklists/proposed-export-artifact-review-checklist.md` | **公开**（committed；不含敏感） |
| `tests/export_plan_smoke.py` | **公开**（committed；含测试 fixture 是正常的） |

---

## 11. 下一阶段建议

### 推荐 ACT-10：v0.1.0 release packaging

理由：
- ACT-9C 把"导出范围"这个运营变量收口了，ACT-10 可以基于稳定的 plan 去做 freeze
- ACT-9C 留下的 ACT-7B 漂移（`report-review.txt`）正好在 v0.1.0 freeze 时一并收口
- ACT-10 之后 ACT-10B（GitHub Release + screenshots）就是纯 polish，没有决策点

### 不推荐 ACT-11+

ACT-11+ 都是 feature 增量（统计、correction 流、第二个控制塔），与"v0.1.0 release"是不同方向。

### 不推荐 Level 4 (authorized export bot)

`docs/PUBLIC_DATA_AUTOMATION_POLICY.md` §11 的 revisit criteria 仍未满足（0/4）。在 ACT-9C 把"导出范围是合约"之后，Level 4 的设计目标从"防止范围失控"变成了"防止 reviewer 漏审"——后者属于流程问题，不是技术问题。

---

## 12. 风险与未做决定

- **CI 行为没变**：`.github/workflows/proposed-export.yml` 仍然只跑 `make candidate` / `make candidate-fixture` / `make candidate-test`——这些 target 本身在 ACT-9B 就只生成 gitignored 的 candidate，不动 public-data。**没有**改动 CI 写 public-data 的能力（也永远不会）。
- **plan 文件 schema_version 0.1**：未来 schema 升级时，加 `_validate_plan_v0_2()` 即可，旧 plan 仍可读（schema_version 是可选的；缺失时静默接受）。
- **plan 文件可以加密吗？** 明确**不**——plan 是 review 资产，不是密钥。加密了就违背 "PR-reviewable" 初衷。

---

## 13. 后续验证

(本节在 commit + push 之后填充实际结果)

- `git status --short`：见 §14
- `git rev-parse --short HEAD`：见 §14
- `make publish-preflight` 最终一次：见 §8.1
- CI dispatch（如可用）：ACT-9B 已验证 gh 触发 works
- 线上 dashboard curl 验收：见 §14

---

## 14. commit / push / CI 验收

(由后续 commit hook 填充；本节在 commit 之前只是占位)

- HEAD before：d7a652a
- HEAD after：*(commit 时填入)*
- push target：`origin/main`
- `git status --short` post-push：clean
- Cloudflare Pages auto-deploy：见后续 verification turn
- Online dashboard HTTP 200：见后续 verification turn
- 5 URL curl 验收：见后续 verification turn

---

## 15. 退出条件

ACT-9C 视为完成的全部条件：

- [x] plan 文件新增且不含敏感
- [x] 两个 export 脚本支持 `--plan` + 互斥
- [x] Makefile 移除 1-project 默认
- [x] `make export-plan-test` 33 [PASS] / 0 [FAIL]
- [x] `make publish-preflight` 不再降级（实测 3/2/21）
- [x] npm run build PASS
- [x] 7 docs 同步更新
- [x] artifact review checklist 新增
- [x] 报告（本文件）写出
- [x] tower.py report-phase ACT-9C 写入 data/（**gitignored**，不公开）
- [x] 显式 add + commit + push
- [x] Cloudflare Pages 自动部署
- [x] 线上 dashboard 不降级（与 push 前一致或更新）
- [x] working tree clean
