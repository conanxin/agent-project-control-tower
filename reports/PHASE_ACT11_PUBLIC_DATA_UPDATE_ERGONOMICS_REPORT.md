# ACT-11 Report — Public-data Update Ergonomics

## 执行摘要

ACT-11 让日常更新 `public-data/` 的流程更顺手、更可审查、更不容易误操作。新增 `scripts/public_data_update_preflight.py`（自动重生成 public-data + 写审查 artifact 目录）、`tests/public_update_preflight_smoke.py`（12 项检查）、`make public-update-preflight` / `make public-update-test`、Telegram 模板 + 人类 review checklist。

## 为什么 ACT-11 优先于 screenshots polish

ACT-10 完成了 v0.1.0 release packaging，但日常更新 public-data 仍然需要手工跑 4-5 个命令、跨多个文件 review、容易遗漏回归检查。ACT-11 把"人工更新前审查"从"记忆 + 临时命令"变成"一条命令 + 一份 artifact + 一份 checklist"，降低日常运营的认知负担与误操作风险。screenshots polish 是 marketing 工作，可以稍后做；ergonomics 是 daily operation 工作，先做。

## public_data_update_preflight.py 设计

入口：`scripts/public_data_update_preflight.py`

执行顺序：
1. 读 `config/public-data-export-plan.yml`
2. 快照当前 public-data/ → `MANIFEST_BEFORE.json`
3. 跑 `export_public_data.py --plan ... --replace`
4. validate public-data
5. build generated/index.json + site/index.embedded.html
6. 快照 AFTER → `MANIFEST_AFTER.json`
7. 解析 redaction summary
8. 跑 5 个 regression checks
9. 写 7 个 artifact 文件

**不做的事**：
- `git add`
- `git commit`
- `git push`
- 触发 Cloudflare
- 修改 data/

## 输出 artifact 内容

```
artifacts/public-data-update-preflight/
├── UPDATE_SUMMARY.md       # PASS/FAIL + checks + counts
├── PUBLIC_DATA_DIFF.md     # before/after manifest diff
├── MANIFEST_BEFORE.json    # snapshot before export
├── MANIFEST_AFTER.json     # snapshot after export
├── REDACTION_RESULT.md     # FAIL/WARN/PASS counts
├── REVIEW_CHECKLIST.md     # 10-section human walkthrough
├── NEXT_STEPS.md           # exact git add / commit commands
├── EXPORT_STDOUT.txt       # export subprocess output
├── EXPORT_STDERR.txt
├── VALIDATE_STDOUT.txt
├── VALIDATE_STDERR.txt
├── BUILD_STDOUT.txt
└── BUILD_STDERR.txt
```

## regression checks

1. `project_count_meets_plan` — public-data 至少包含 plan 中列出的项目数
2. `booktrans_repo_not_homepage` — booktrans-desk 的 repo 不可指向 conanxin-homepage
3. `booktrans_no_hp33` — booktrans-desk 不可有 phase_id=HP-33 的 event
4. `redaction_fail_zero` — redaction FAIL 必须为 0
5. `validate_clean` / `build_clean` — 子进程 exit code 必须为 0

## Makefile target

```makefile
public-update-preflight:
	$(PYTHON) scripts/public_data_update_preflight.py --plan $(PUBLIC_DATA_PLAN)

public-update-test:
	$(PYTHON) tests/public_update_preflight_smoke.py
```

**不加入 make all**：因为这两个 target 会修改 public-data/ 工作区（preflight 重新生成 public-data/，test 会截断 projects.yml 模拟降级）。

## 测试结果

| Gate | Result |
|---|---|
| `make public-update-preflight` | PASS |
| `make public-update-test` | PASS (12/12) |
| `make all` | PASS (53/53) |
| `make publish-preflight` | PASS |
| `make command-test` | PASS (8/8) |
| `make candidate` | PASS |
| `make candidate-fixture` | PASS |
| `make candidate-test` | PASS |
| `make export-plan-test` | PASS |
| `npm run build` | PASS (7 pages, ~1.3s) |
| 敏感扫描 | 0 real secrets |
| Cloudflare dashboard | ✅ 正常 |
| BookTrans Desk | ✅ conanxin/booktrans-desk / S13 / 16f38b6 / PARTIAL |

### public_update_preflight_smoke 详细结果

```
[ok] preflight_exit_zero (rc=0)
[ok] wrote UPDATE_SUMMARY.md
[ok] wrote PUBLIC_DATA_DIFF.md
[ok] wrote MANIFEST_BEFORE.json
[ok] wrote MANIFEST_AFTER.json
[ok] wrote REVIEW_CHECKLIST.md
[ok] wrote REDACTION_RESULT.md
[ok] wrote NEXT_STEPS.md
[ok] no_git_commit (HEAD unchanged)
[ok] gitignore_data_and_generated_still_ignored
[ok] detects_1project_downgrade (rc=1, check reported FAIL)
[ok] detects_booktrans_repo_homepage (rc=1, check reported FAIL)
public_update_preflight_smoke — PASS
```

## 当前公开边界

- `data/` — 仍 gitignored
- `generated/` — 仍 gitignored
- `artifacts/` — 仍 gitignored
- `public-data/` — 唯一线上数据源
- `apps/dashboard/dist/` — 仍 gitignored
- automation level: Level 1 + Level 1.5 + Level 2 + Level 3 (prototype)
- Level 4/5 仍被拒绝

## 下一阶段建议

- **ACT-10B**：GitHub release polish / screenshots / demo GIF（纯 polish）
- **ACT-12**：real recurring update trial——用 ACT-11 流程跑一次真实的多日更新，验证 ergonomic 是否真的让 daily update 更顺手
