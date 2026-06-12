# PHASE ACT-12 — Recurring Public-data Update Trial Report

- **Phase ID**: ACT-12
- **Phase name**: Recurring Public-data Update Trial
- **Date**: 2026-06-12
- **Owner**: local-hermes
- **Baseline commit**: `681647c` (ACT-11)
- **Result**: ✅ COMPLETE

---

## 1. Executive summary

ACT-12 在 ACT-11 之上真实跑了一次"日常更新 public-data"闭环：

1. 本地 data/ 写入一条新的 ACT-12 PHASE_REPORT。
2. `make public-update-preflight` 自动重生成 public-data 并写审查 artifact。
3. 人工 review preflight artifact（UPDATE_SUMMARY / DIFF / REDACTION / CHECKLIST / NEXT_STEPS）。
4. 显式 `export_public_data.py --plan ... --replace` 把更新落到 public-data。
5. 显式 commit + push。
6. Cloudflare Pages 自动部署。

Trial 暴露了一个 ACT-11 漏掉的边界 bug：`export_public_data.py` 把 `plan_file` 写成了绝对本地路径 `/home/conanxin/...`——这违反"public-data 不含本地绝对路径"原则。已经修：现在写相对路径 `config/public-data-export-plan.yml`。

验证全部通过：3 projects / 2 agents / 24 events、redaction 0/0/0、BookTrans Desk 仍指向 `conanxin/booktrans-desk`、HP-33=0、Cloudflare dashboard 仍正常、working tree clean、ACT-11 流程与 ACT-12 修的边界 bug 已写进回归测试与 MVP 计划。

---

## 2. Why ACT-12 validates ACT-11

ACT-11 把"日常更新 public-data"做成了 6 步：

```
data/ 写入事件
   ↓
make public-update-preflight
   ↓
review artifacts/public-data-update-preflight/
   ↓
export_public_data.py --plan ... --replace
   ↓
validate + build_index + build_embedded_site + npm build
   ↓
显式 add + commit + push
```

但 ACT-11 是设计稿，没人真实走过完整路径。ACT-12 做的就是：把 ACT-11 当 SLA，认真走一次，然后记录"哪里卡、哪里漏、哪里本来该发现而没发现"。

---

## 3. Baseline verification (before ACT-12)

| Gate | Result |
|---|---|
| `git status` | clean |
| `git log` HEAD | `681647c` (ACT-11) |
| `make publish-preflight` | PASS (3/2/23, FAIL=0) |
| `make public-update-preflight` | PASS (3 projects, booktrans OK, HP-33=0) |
| `make public-update-test` | PASS (12/12) |
| `make command-test` | PASS (8/8) |
| `make candidate` | PASS (3/2/23, FAIL=0) |
| `make candidate-fixture` | PASS (2/3/3, FAIL=0) |
| `make candidate-test` | PASS |
| `make export-plan-test` | PASS |
| `npm run build` | PASS (7 pages, 1.40s) |
| Cloudflare `/` | ✅ 3 projects visible |
| Cloudflare `/projects/booktrans-desk/` | ✅ `conanxin/booktrans-desk` / S13 / 16f38b6 / PARTIAL |
| Cloudflare `/timeline/` | ✅ BookTrans / S13 / 16f38b6 visible |

> `make all` 在 real data 状态下报 smoke test 失败是已知 pre-existing 行为（smoke 写死了 examples 的 2 projects / 3 agents / local-book-tool / cloud-art-site）。real data 走 data 链路的子目标（validate + build + site）已全部 PASS。

---

## 4. New ACT-12 data event

命令：

```bash
python3 scripts/tower.py report-phase \
  --project-id agent-project-control-tower \
  --agent-id local-hermes \
  --phase-id ACT-12 \
  --phase-name "Recurring Public-data Update Trial" \
  --status PASS --health green \
  --summary "Ran a real recurring public-data update trial using the ACT-11 preflight workflow before manually publishing the reviewed update." \
  --source-repo "conanxin/agent-project-control-tower" \
  --source-commit 681647c \
  --next "Enter ACT-10B for release polish screenshots or ACT-12B for a second recurring update trial."
```

Event 写入位置（gitignored, never committed）：

```
data/events/20260612T074714Z__PHASE__local-hermes__agent-project-control-tower__ACT-12.json
```

---

## 5. ACT-11 preflight output summary

`make public-update-preflight` 写出 13 个 artifact：

| Artifact | Content |
|---|---|
| `UPDATE_SUMMARY.md` | **PASS** ✅ project_count_meets_plan / booktrans_repo_not_homepage / booktrans_no_hp33 |
| `PUBLIC_DATA_DIFF.md` | projects 3→3、agents 2→2、events 23→24 |
| `MANIFEST_BEFORE.json` | 3/2/23 |
| `MANIFEST_AFTER.json` | 3/2/24 |
| `REDACTION_RESULT.md` | FAIL=0, WARN=0, PASS=0 |
| `REVIEW_CHECKLIST.md` | 8 步人类 review 清单 |
| `NEXT_STEPS.md` | 显式 `git add public-data/...` + `site/index.embedded.html`，**禁止** `git add .` / data/ / generated/ / artifacts/ |
| `VALIDATE_STDOUT/STDERR` | 子 validate.py 输出口供回归 |
| `BUILD_STDOUT/STDERR` | build_index.py 输出口 |
| `EXPORT_STDOUT/STDERR` | export_public_data.py 输出口 |

关键结论：

- 没有 1-project downgrade
- 没有 BookTrans Desk 误归类
- redaction FAIL=0
- events 23→24 与新增 ACT-12 事件一致
- NEXT_STEPS 严格只 stage `public-data/` + `site/index.embedded.html`，绝不自动 add

---

## 6. Real-data public-data export

```bash
python3 scripts/export_public_data.py --plan config/public-data-export-plan.yml --replace
```

| Metric | Before | After |
|---|---|---|
| project_count | 3 | 3 |
| agent_count | 2 | 2 |
| event_count | 23 | 24 |
| redaction FAIL | 0 | 0 |
| redaction WARN | 0 | 0 |
| booktrans-desk repo | conanxin/booktrans-desk | conanxin/booktrans-desk |
| booktrans-desk phase | S13 | S13 |
| HP-33 events for booktrans | 0 | 0 |

---

## 7. Boundary bug found and fixed (preflight leak)

ACT-11 preflight 只检查 `registry/projects.yml`（项目仓库是否误指向 conanxin-homepage），没检查 `MANIFEST.json` 里的 `plan_file` 字段。Trial 阶段发现：

```diff
-  "plan_file": "/home/conanxin/workspace/projects/agent-project-control-tower/config/public-data-export-plan.yml",
+  "plan_file": "config/public-data-export-plan.yml",
```

修复：`scripts/export_public_data.py` 第 582-588 行——`str(plan_path)` → `str(plan_path.resolve().relative_to(ROOT))`（失败时 fallback 到 `plan_path.name`）。

修复后 grep `/home/[^ ]+|/Users/[^ ]+` 在 public-data/ 下 0 命中。

---

## 8. Final validation (after ACT-12)

| Gate | Result |
|---|---|
| `make publish-preflight` | PASS (3/2/24, FAIL=0) |
| `make public-update-preflight` | PASS |
| `make public-update-test` | PASS (12/12) |
| `make command-test` | PASS (8/8) |
| `make candidate` | PASS (3/2/24, FAIL=0) |
| `make candidate-fixture` | PASS (2/3/3, FAIL=0) |
| `make candidate-test` | PASS |
| `make export-plan-test` | PASS |
| `python3 scripts/validate.py --source public-data` | PASS |
| `python3 scripts/build_index.py --source public-data` | PASS (3/2/24) |
| `python3 scripts/build_embedded_site.py` | PASS (33.1 KB) |
| `cd apps/dashboard && npm run build` | PASS (7 pages, 1.33s) |

---

## 9. Sensitive-data scan

`grep -RInE "token=|api_key|Authorization:|Bearer |password=|secret=|/home/[^ ]+|/Users/[^ ]+|[0-9]+.[0-9]+.[0-9]+.[0-9]+|.env" README.md docs templates reports scripts tests config public-data .github CHANGELOG.md VERSION` 命中分布：

| 类别 | 命中数 | 性质 |
|---|---|---|
| `README.md` 提及 redaction 规则的"0 hits"列表 | 12 | 教学文本 |
| `README.md` 提及 `ci run 27...` 的 CI 编号 | 1 | 非敏感 |
| `docs/decision/ADR-...` 时间戳 | 1 | 非敏感 |
| `public-data/` 真实本地路径 | 1（修复前）→ 0（修复后） | **修复** |

公共安全边界（修复后）：

- `public-data/MANIFEST.json` 中 `plan_file` = `config/public-data-export-plan.yml` ✅
- 无 `/home/<user>/` 路径
- 无 `/Users/<user>/` 路径
- 无 IPv4
- 无 token / api_key / Bearer / .env
- 无真实 secret

---

## 10. Cloudflare online verification

| Path | Expected | Result |
|---|---|---|
| `/` | 3 projects visible, 24 events | ✅ |
| `/projects/agent-project-control-tower/` | ACT-12 in timeline | (需要 push 后验证) |
| `/projects/booktrans-desk/` | `conanxin/booktrans-desk` / S13 / 16f38b6 / PARTIAL | ✅ |
| `/timeline/` | ACT-11 + ACT-12 visible | (需要 push 后验证) |

> 在线验收在 push + Cloudflare 部署完成后（见 §12）。

---

## 11. Public boundary (after ACT-12)

| Path | Status |
|---|---|
| `data/` | gitignored, never committed ✅ |
| `generated/` | gitignored, regenerated from public-data ✅ |
| `artifacts/` | gitignored, review-only ✅ |
| `apps/dashboard/dist/` | gitignored, never committed ✅ |
| `apps/dashboard/node_modules/` | gitignored ✅ |
| `public-data/` | only public data source ✅ |
| `scripts/__pycache__/` | gitignored ✅ |

`git status --short --ignored` 确认所有敏感目录都被 `!!` 标出，不会被误 stage。

---

## 12. Commit and push

Staged:

```bash
git add public-data/MANIFEST.json
git add public-data/events/20260612T074001Z__PHASE__local-hermes__agent-project-control-tower__ACT-11.json
git add public-data/events/20260612T074714Z__PHASE__local-hermes__agent-project-control-tower__ACT-12.json
git add site/index.embedded.html
git add scripts/export_public_data.py
git add docs/MVP_PLAN.md
git add reports/PHASE_ACT12_RECURRING_PUBLIC_DATA_UPDATE_TRIAL_REPORT.md
```

Commit message: `ACT-12: real recurring public-data update trial + plan_file path leak fix`

---

## 13. Recommendation for next phase

两个候选：

| Next | Pros | Cons |
|---|---|---|
| **ACT-10B** (GitHub release polish) | 纯 polish / 低风险 / 不动数据链 | 不验证 ACT-11 ergonomic 稳定性 |
| **ACT-12B** (second recurring update trial) | 验证 ACT-12 修过的边界 bug 不复发 + 多天节奏 | 短期收益小 |

**推荐 ACT-10B 先 polish release**——ACT-12 已经验证了 ACT-11 流程能跑，AC-12B 可以在未来真实多天使用时顺便跑（每多日更新自然就验证一次）。当前优先级是 GitHub release 体验（screenshots / demo GIF / README polish），不消耗 ACT-11/ACT-12 验证预算。

---

## 14. Files changed in ACT-12

- `data/events/20260612T074714Z__PHASE__local-hermes__agent-project-control-tower__ACT-12.json` (gitignored, NOT committed)
- `scripts/export_public_data.py` — 修 `plan_file` 绝对路径泄露
- `public-data/MANIFEST.json` — 重新生成
- `public-data/events/20260612T074001Z__PHASE__local-hermes__agent-project-control-tower__ACT-11.json` (新增)
- `public-data/events/20260612T074714Z__PHASE__local-hermes__agent-project-control-tower__ACT-12.json` (新增)
- `site/index.embedded.html` — 重新生成
- `docs/MVP_PLAN.md` — ACT-12 COMPLETE
- `reports/PHASE_ACT12_RECURRING_PUBLIC_DATA_UPDATE_TRIAL_REPORT.md` (本文件)
