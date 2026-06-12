# ACT-10 Report — v0.1.0 Release Packaging

## 执行摘要

ACT-10 将 ACT-0 到 ACT-9C 的成果打包成 v0.1.0 稳定版本。本阶段不做新功能，只做 release packaging、文档收口、版本标记、验收和发布记录。

## 为什么 ACT-10 在 ACT-9C 后执行

ACT-9C 完成了 export plan review workflow 的收口，但系统缺少正式的版本标记。v0.1.0 的发布意味着 ACT-0 到 ACT-9C 的成果已经稳定，可以作为基线供后续开发参考。

## v0.1.0 release 边界

### 包含

1. Git-backed project control tower
2. data/ private local event store
3. public-data/ reviewed public export
4. config/public-data-export-plan.yml as export scope contract
5. generated/index.json build pipeline
6. static embedded HTML dashboard
7. Astro dashboard on Cloudflare Pages
8. custom domain: https://control-tower.conanxin.com/
9. tower.py CLI (10 subcommands)
10. Command generator
11. Template alignment checker
12. Proposed export artifact prototype
13. Export plan workflow
14. Multi-machine playbooks
15. Public-data automation policy
16. 3 real public projects + 2 public agents

### 不包含

- automatic public-data export
- CI auto commit / push public-data
- database
- login / auth
- Cloudflare API automation
- full hosted service for other users
- auto discovery of projects
- secret management beyond lightweight redaction
- real-time monitoring

## 新增/修改文件

### 新增

- `VERSION`
- `CHANGELOG.md`
- `docs/release/RELEASE_NOTES_v0.1.0.md`
- `docs/release/RELEASE_CHECKLIST_v0.1.0.md`
- `reports/PHASE_ACT10_V010_RELEASE_PACKAGING_REPORT.md`

### 修改

- `README.md` — 更新状态为 v0.1.0 RELEASED
- `docs/MVP_PLAN.md` — 标记 ACT-10 COMPLETE
- `docs/DEPLOYMENT_PLAN.md` — 增加 v0.1.0 deployment state
- `docs/OPEN_SOURCE_PLAN.md` — 增加 v0.1.0 public release boundary
- `docs/PUBLIC_DATA_AUTOMATION_POLICY.md` — 增加 v0.1.0 policy state

## 验证结果

| Gate | Result |
|---|---|
| `make all` | PASS (53/53) |
| `make publish-preflight` | PASS (3 projects / 2 agents / 22 events) |
| `make command-test` | PASS (8/8) |
| `make candidate` | PASS |
| `make candidate-fixture` | PASS |
| `make candidate-test` | PASS |
| `make export-plan-test` | PASS |
| `npm run build` | PASS (7 pages, ~1.3s) |
| Sensitive scan | 0 real secrets (all instructional) |

## public-data 当前状态

- 3 projects
- 2 agents
- 22 events
- 0 redaction FAILs
- 0 WARNs

## export plan 当前状态

- `config/public-data-export-plan.yml` 已验证
- 导出范围：3 projects / 2 agents / max 50 events per project

## proposed export artifact 当前状态

- `scripts/build_public_data_candidate.py` 可用
- `.github/workflows/proposed-export.yml` 可用
- CI 可生成 candidate tarball（download-only，不自动 commit）

## Cloudflare dashboard 状态

- ✅ https://control-tower.conanxin.com/ — HTTP 200
- ✅ https://control-tower.conanxin.com/timeline/ — HTTP 200
- ✅ https://control-tower.conanxin.com/projects/booktrans-desk/ — HTTP 200
- BookTrans Desk 显示：conanxin/booktrans-desk / S13 / 16f38b6 / PARTIAL

## GitHub Actions 状态

- CI workflow `.github/workflows/ci.yml` 3 jobs 全 PASS
- `zero-dep-acceptance` ✅
- `astro-dashboard` ✅
- `publish-preflight` ✅

## tag 创建结果

- Annotated tag `v0.1.0` created
- Tag pushed to origin
- Verified: `git ls-remote --tags origin v0.1.0`

## GitHub release 创建结果

- **Deferred** — `gh` CLI 未配置或不可用
- 建议手动创建：GitHub → Releases → New release → Choose tag `v0.1.0` → Paste content from `docs/release/RELEASE_NOTES_v0.1.0.md`

## 已知限制

- No automatic public-data export
- data/ remains local and gitignored
- public-data export requires human / authorized primary agent review
- dashboard is static
- no authentication
- no database

## 下一阶段建议

- **ACT-10B**: GitHub release polish / screenshots / demo GIF
- **ACT-11**: public-data update ergonomics（更快的手动刷新工作流）
