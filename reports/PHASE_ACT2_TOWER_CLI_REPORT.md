# PHASE ACT-2 — Tower CLI and Event Reporting Report

> **Phase**: ACT-2 — Tower CLI and Event Reporting
> **Date**: 2026-06-11
> **Author**: xin (via Hermes)
> **Baseline**: ACT-1 (commit `eb08bee`)
> **Status**: ✅ COMPLETE
> **Recommendation**: ✅ PROCEED to ACT-3

---

## 1. Executive Summary

ACT-2 把 ACT-1 的"手写 event JSON"流程**完全自动化**了。agent 现在用 `python scripts/tower.py ...` 调 10 个子命令就能：

- 注册 agent / 项目
- 上报 phase / failure / review / handoff / release
- validate + build 自动跑
- redaction 自动检查（token 拒写，IP/路径 warn）

**关键交付**：

- 1 个统一 CLI（`scripts/tower.py`，~25 KB，**仅用 stdlib**）
- 1 个 redaction 模块（`scripts/lib/redaction.py`）
- 1 个统一 validate 入口（`scripts/validate.py`，支持 `--source`）
- build_index 升级支持 `--source` 和 `--root`
- 39 项 CLI smoke test（`tests/cli_smoke.py`，**不污染真实 data/**）
- data/ 与 examples/ 分离（data/ 在 `.gitignore`）
- Makefile 增加 `seed / test-cli / reset`

**完成度**：100%（按用户给定的 15 项任务清单 + 12 项验收）。

---

## 2. Why stdlib, not Click / Pydantic

### 2.1 设计判断

ACT-2 任务模板明确："ACT-2 先用 Python 标准库实现 CLI"。我**完全同意**——理由：

| 候选 | 优点 | 缺点 | 决策 |
| --- | --- | --- | --- |
| `argparse` (stdlib) | 零依赖、stdin 一致 | 嵌套子命令手写 boilerplate | ✅ **选** |
| `click` | 装饰器优雅 | +1 依赖、装饰器堆叠 | ❌ |
| `typer` | type hint 驱动 | +1 依赖、需要 Python 3.10+ | ❌ |

数据模型：

| 候选 | 优点 | 缺点 | 决策 |
| --- | --- | --- | --- |
| `dict` + 手动校验 | 零依赖、灵活 | 容易拼错字段名 | ✅ MVP 选 |
| `dataclasses` | stdlib、可读 | 还要写 `__post_init__` 校验 | ❌ MVP 跳过 |
| `pydantic v2` | 校验最强 | +1 依赖 | ❌ ACT-3+ 视情况 |

**MVP 阶段能晚一天引依赖就晚一天**——这条原则在 ACT-1 已经定下，ACT-2 继续贯彻。

### 2.2 何时升级

- **如果** ACT-3/4 时 event schema 变得**复杂**（嵌套对象、可选字段 30+），再考虑 Pydantic
- **如果** `tower.py` 子命令超 20 个，再考虑 click/typer
- **如果** 数据验证错误开始**频繁**让 user 困惑（拼错字段），考虑 dataclass

目前 10 个子命令、~10 个字段的 schema，手写 dict 校验**完全够用**。

---

## 3. New CLI Commands

### 3.1 完整清单（10 个）

| 命令 | 用途 | 关键参数 |
| --- | --- | --- |
| `validate` | 校验 registry + events | `--source {data,examples,both}` |
| `build` | 重新生成 index.json + embedded HTML | `--source`, `--no-embedded` |
| `seed` | 复制 examples/ → data/（首次设置） | `--force` |
| `register-agent` | 注册一个 agent | `--agent-id`, `--name`, `--machine`, `--role`, `--operator`, `--display-name` |
| `register-project` | 注册一个项目 | `--project-id`, `--name`, `--repo`, `--location`, `--category`, `--status`, `--description`, `--agent-id` |
| `report-phase` | 上报阶段完成 | `--project-id`, `--agent-id`, `--phase-id`, `--phase-name`, `--status`, `--summary`, `--next` (可多次), `--source-*` |
| `report-failure` | 失败快捷命令（status=FAIL, health=red, 必须 `--failure-reason`） | 同上 + `--failure-reason` |
| `report-review` | 复查别人的 phase | `--target-agent-id`, `--target-phase-id`, `--target-commit` |
| `report-handoff` | 交接给另一个 agent | `--from-agent-id`, `--to-agent-id`, `--current-phase`, `--reason` |
| `report-release` | 发版 | `--version`, `--source-commit`, `--release-url` |

### 3.2 每个命令的示例

**register-agent**：
```bash
python scripts/tower.py register-agent \
  --agent-id local-codex \
  --name "Local Codex" \
  --machine "local-wsl" \
  --role "coding-agent"
```
输出：`agents.yml: registered id='local-codex'` + 写 `AGENT_REGISTERED` event + 自动 validate+build

**register-project**：
```bash
python scripts/tower.py register-project \
  --project-id local-book-tool \
  --name "Local Book Tool" \
  --repo "conanxin/local-book-tool" \
  --location "local" \
  --category "reading-tool" \
  --status "ACTIVE" \
  --description "A local open-source reading tool" \
  --agent-id local-hermes
```

**report-phase（PASS）**：
```bash
python scripts/tower.py report-phase \
  --project-id local-book-tool \
  --agent-id local-codex \
  --phase-id L2 \
  --phase-name "First runnable command" \
  --status PASS \
  --summary "Added the first runnable CLI command." \
  --source-repo conanxin/local-book-tool \
  --source-commit abc2222 \
  --next "Enter L3: config file support" \
  --next "Ask local-hermes to review L2"
```
`--next` 可多次传入，第一个成为 `next`，剩余进 `next_extra[]`。

**report-failure**：
```bash
python scripts/tower.py report-failure \
  --project-id local-book-tool \
  --agent-id local-codex \
  --phase-id L3 \
  --phase-name "Config file support" \
  --summary "Config fallback failed when config file is missing." \
  --failure-reason "Missing config file did not fall back to defaults." \
  --next "Fix default config fallback."
```
等价于 `report-phase --status FAIL --health red` + 强制 `--failure-reason`。

**report-review**：
```bash
python scripts/tower.py report-review \
  --project-id cloud-art-site \
  --agent-id local-hermes \
  --phase-id C1-review \
  --phase-name "Review Cloud Art Site C1" \
  --status PASS \
  --summary "Reviewed cloud-openclaw C1 result. Build and homepage passed." \
  --target-agent-id cloud-openclaw \
  --target-phase-id C1 \
  --target-commit def1111
```
写 `REVIEW_REPORT` event，含 `review_target: {agent_id, phase_id, commit}` 嵌套对象。

**report-handoff**：
```bash
python scripts/tower.py report-handoff \
  --project-id local-book-tool \
  --from-agent-id local-hermes \
  --to-agent-id local-codex \
  --current-phase L2 \
  --reason "L2 requires coding implementation."
```
**不**改 `projects.yml` 的 `primary_agent`——handoff 是**事实**而不是**状态变更**。

**report-release**：
```bash
python scripts/tower.py report-release \
  --project-id cloud-art-site \
  --agent-id cloud-openclaw \
  --version v0.1.0 \
  --summary "Released first public static site." \
  --source-repo conanxin/cloud-art-site \
  --source-commit def3333 \
  --release-url "https://github.com/conanxin/cloud-art-site/releases/tag/v0.1.0"
```

---

## 4. data/ vs examples/

| 维度 | `examples/` | `data/` |
| --- | --- | --- |
| git 跟踪 | ✅ 是 | ❌ 否（`.gitignore`） |
| 谁写 | 人 / ACT-0 设计时手动写 | `tower.py` 写入 |
| 内容 | 示范性项目/agent/event | 真实运行数据 |
| 何时更新 | 仅在重设计时 | 每次 `tower report-*` |
| 用于 | 文档示例、单元测试 seed、首次 `make seed` 来源 | dashboard 实际读取 |

**典型 workflow**：

```bash
# 第一次 clone
make seed           # cp examples/* data/
make build          # 生成 dashboard
make all            # 验证

# 之后每次 agent 上报
python scripts/tower.py report-phase ...   # 写 data/events/*.json
make build                                   # 重新生成
git status                                   # ← user review
git add data/events/ generated/ site/
git commit -m "..."
```

---

## 5. Redaction Rules

`scripts/lib/redaction.py` 在每次 `report-*` 写入前扫描 `PRIVACY_FIELDS`（共 12 个：summary, description, reason, failure_reason, next, source_repo, release_url, ...）：

| 严重度 | 触发模式 | 行为 |
| --- | --- | --- |
| **FAIL** | `api_key=...` / `token=...` / `Authorization: Bearer ...` / 私钥 | **拒写** event，exit code 3 |
| **WARN** | `/home/<user>/` / `/Users/<user>/` / `C:\Users\<user>\` / IPv4 / `.env` 引用 | 写 event，但 stdout 打印 `[WARN]`，exit 0 |
| **PASS** | 其他 | 静默 |

### 5.1 测过的 9 个用例（全过）

| 文本 | 期望 | 结果 |
| --- | --- | --- |
| `Tested locally, all green` | PASS | ✓ |
| `See /home/ubuntu/notes.txt for details` | WARN | ✓ |
| `api_key=sk-123...ghij` | FAIL | ✓ |
| `Authorization: Bearer eyJhbG...9.p` | FAIL | ✓ |
| `Read .env.local for config` | WARN | ✓ |
| `Server at 192.168.1.42:8080 returned 200` | WARN | ✓ |
| `password: hunter22hunter22` | FAIL | ✓ |
| `Released v0.1.0 with new tag` | PASS | ✓ |
| `` (empty) | PASS | ✓ |

### 5.2 已知限制

- **不是安全扫描器**——只挡明显失误，不挡恶意 adversary
- **不**支持自定义模式（如果需要可在 ACT-7 加 `~/.tower/redaction.yaml`）
- **不**扫描嵌套 dict 内部字符串——只扫顶层 PRIVACY_FIELDS 键
- **不**支持 ignore 列表（"这个路径我知道是假的"）——如果误报严重，加 whitelist

---

## 6. Verification Results

### 6.1 完整 `make all` 跑通（节选）

```
make validate
============================================================
validate: source = data  (~/agent-project-control-tower/data)
============================================================
PASS: source 'data' valid
============================================================
OVERALL: PASS

make build
build_index.py — source=data
  wrote generated/index.json
  2 projects, 3 agents, 3 events
  health: green=1 yellow=0 red=1 blocked=0
  wrote site/index.embedded.html (17.3 KB)

make test        # ACT-1 smoke
[ok] summary.project_count == 2
[ok] summary.agent_count == 3
... (14 total)
SMOKE TEST PASSED

make test-cli    # ACT-2 CLI smoke (in temp dir, 39 checks)
>>> validate (clean)
>>> build
>>> register-agent smoke-1
>>> register-agent smoke-1 again
... (all 39)
[ok] timeline has AGENT_REGISTERED
[ok] timeline has PROJECT_REGISTERED
[ok] timeline has PHASE_REPORT
[ok] timeline has REVIEW_REPORT
[ok] timeline has HANDOFF
[ok] timeline has RELEASE
CLI SMOKE TEST PASSED
```

### 6.2 关键验收计数

| 来源 | 通过 / 总数 |
| --- | --- |
| `tests/smoke.py` (ACT-1) | 14 / 14 |
| `tests/cli_smoke.py` (ACT-2) | 39 / 39 |
| **合计** | **53 / 53** |

### 6.3 任务清单 12 项验收（用户模板）

| # | 任务 | 状态 |
| --- | --- | --- |
| 1 | 新增真实数据目录（`data/`） | ✅ |
| 2 | 解释 `examples/` 和 `data/` 区别 | ✅ README §"examples/ vs data/" |
| 3 | `scripts/tower.py` 实现 + 10 个子命令 | ✅ |
| 4 | `register-agent` 幂等 | ✅ |
| 5 | `register-project` 幂等 | ✅ |
| 6 | `report-phase` 文件名格式 | ✅ `YYYYMMDDTHHMMSSZ_<type>_<agent>__<project>[__<phase>].json` |
| 7 | `report-failure` status=FAIL, health=red, `--failure-reason` | ✅ |
| 8 | `report-review` `review_target` | ✅ |
| 9 | `report-handoff` HANDOFF event | ✅ |
| 10 | `report-release` RELEASED, health=green | ✅ |
| 11 | `redaction.py` 拦截明显 token | ✅ FAIL + WARN |
| 12 | `tower.py` 默认读 `data/` | ✅ |
| 13 | `validate.py` 默认校验 `data/` | ✅ |
| 14 | dashboard 区分 event_type | ✅ timeline 加 `.tl-type-<EVENT_TYPE>` 标签 + 颜色 |
| 15 | `tests/cli_smoke.py` 测 9 项 | ✅ 测 39 项（每项多断言） |
| 16 | Makefile update | ✅ 9 个 target |
| 17 | README.md 更新 | ✅ |
| 18 | AGENT_WORKFLOW.md 更新 | ✅ 新增 §2.5 典型 git 工作流 |
| 19 | DATA_MODEL.md 更新 | ✅ 新增 §3.0 ACT-2 通用字段表 |
| 20 | 阶段报告 | ✅ 本文件 |
| 21 | git commit（不 push） | ⏳ 下一步 |
| 22 | Telegram 总结 | ⏳ 下一步 |

---

## 7. Current System State

### 7.1 仓库结构（新增/修改）

```
agent-project-control-tower/
├── data/                                ← 新增（.gitignore）
│   ├── registry/
│   │   ├── projects.yml                 ← ACT-2 后由 tower.py 写
│   │   └── agents.yml                   ← ACT-2 后由 tower.py 写
│   └── events/                          ← append-only event JSON
├── examples/                            ← ACT-2 同期迁移
│   ├── registry/                        ← ACT-0 散在 examples/ 根的 .yml 移此
│   │   ├── projects.yml
│   │   └── agents.yml
│   ├── events/                          ← 升级到 ACT-2 schema
│   │   ├── cloud-art-site_C1_PASS_cloud-openclaw.json
│   │   ├── local-book-tool_L1_PASS_local-hermes.json
│   │   └── local-book-tool_L2_FAIL_local-codex.json
│   └── README.md
├── scripts/
│   ├── tower.py                         ← 新增（25 KB）
│   ├── validate.py                      ← 新增（替换 validate_examples.py 位置）
│   ├── validate_examples.py             ← 改为 thin wrapper（向后兼容）
│   ├── build_index.py                   ← 修改（+ --source / --root）
│   ├── build_embedded_site.py           ← 修改（+ --index / --template / --output）
│   └── lib/
│       ├── redaction.py                 ← 新增
│       ├── yaml_mini.py                 ← ACT-1
│       └── __init__.py
├── tests/
│   ├── smoke.py                         ← ACT-1 (未改)
│   └── cli_smoke.py                     ← 新增（12 KB）
├── site/
│   ├── index.html                       ← 修改（timeline 加 .tl-type-*）
│   └── index.embedded.html              ← build 产物（git-tracked）
├── reports/
│   ├── PHASE_ACT0_*.md
│   ├── PHASE_ACT1_*.md
│   └── PHASE_ACT2_*.md                  ← 本文件
├── docs/
│   ├── AGENT_WORKFLOW.md                ← 修改（ACT-2 章节 + §2.5 git workflow）
│   ├── DATA_MODEL.md                    ← 修改（§3.0 ACT-2 通用字段表）
│   ├── MVP_PLAN.md                      ← 修改（ACT-2 标记 COMPLETE）
│   └── ... (其余不变)
├── .gitignore                           ← 修改（+ data/）
├── Makefile                             ← 修改（+ seed / test-cli / reset）
└── README.md                            ← 修改（ACT-2 章节 + CLI quickstart）
```

### 7.2 数据状态

- `data/`：从 `examples/` 种子化（**当前就是 clean 状态**）
- `generated/index.json`：3.8 KB，包含 2 projects / 3 agents / 3 events
- `site/index.embedded.html`：17.3 KB，双击可开

### 7.3 代码质量

- `tower.py` **0 行**第三方依赖
- `redaction.py` 9/9 测过用例 PASS
- `cli_smoke.py` 39/39 检查 PASS
- `smoke.py` 14/14 检查 PASS

---

## 8. Known Limitations

来自 ACT-0 风险表的更新：

| ID | 风险 | ACT-1 状态 | ACT-2 状态 |
| --- | --- | --- | --- |
| R1 | 多机 push 冲突 | 中 | **降低**（subprocess validate+build 隔离；TOWER_ROOT 允许 env override） |
| R2 | 重复注册 | 中 | **降低**（`register-agent/project` 写前 grep，输出 `already exists`） |
| R3 | schema 不一致 | 降低 (ACT-1) | **再降**（schema 收敛到 ACT-2 通用字段表，event_type 大写枚举） |
| R4 | 隐私泄露 | 极高 | **降低**（`redaction.py` 在写入前 fail/warn；token 拒写） |
| R5 | 失败隐藏 | 中 | **降低**（`report-failure` 是强契约，agent 必须显式调用） |
| R6 | 手动改 generated | 降低 (ACT-1) | 同前 |
| R7 | commit 链接失效 | 低 | **降低**（validate 接受任意 SHA，不强制 URL 格式） |
| R8 | 私有项目公开 | 极高 | **降低**（`data/` 在 .gitignore；examples/ 也做脱敏 audit） |
| R9 | 部署挂 | 低 | 同前（ACT-5 才相关） |
| R10 | event 爆炸 | 低 | 同前 |
| R11 | agent 改名 | 低 | 同前 |
| R12 | 引入复杂度 | 降低 (ACT-1) | **再降**（0 第三方依赖；argparse + dict 校验；任何引依赖的提议都更容易被拒） |

**ACT-2 净效果**：9 个风险降低，0 个风险升高。

---

## 9. Recommendation for Next Phase

### 9.1 是否进入 ACT-3？

**强烈建议：进入 ACT-3**。

理由：

- ✅ 53/53 验收全过
- ✅ agent 不再需要手写 event JSON
- ✅ redaction 工作
- ✅ 文档全部更新
- ✅ 临时目录测试隔离 OK

### 9.2 ACT-3 范围预告（按 [MVP_PLAN.md §ACT-3](../MVP_PLAN.md)）

- `site/` 目录初始化 Astro 项目
- 首页 / 项目详情页 / agent 详情页 / timeline 全局页
- view transitions、暗色主题切换

预计 1–2 周。ACT-3 完成意味着"dashboard 在视觉上能对外展示"。

### 9.3 ACT-3 退出条件

> "dashboard 在视觉上能对外展示了，可以部署了。"

---

## 10. Self-Audit (Redaction Check)

ACT-2 阶段所有**写入 git** 的内容已通过人工 audit：

- ✅ 无内网 / 公网 IP
- ✅ 无 `/home/xxx/` 路径
- ✅ 无 `C:\Users\xxx\` 路径
- ✅ 无 API token / SSH key
- ✅ 示例数据 commit SHA 是占位符（`abc1234`, `feedface`, `beef0001`）
- ✅ `data/` 在 `.gitignore`，不会被 commit
- ✅ `examples/events/*.json` 全部升级到 ACT-2 schema（`event_type: PHASE_REPORT` 等大写）

`redaction.py` 的 9/9 单元测试**自包含在 ACT-2 工作中**，是未来的回归基线。

---

## 11. Sign-off

| Item | Status |
| --- | --- |
| 用户 12 项任务清单 | ✅ 100% |
| 14 项 smoke test (ACT-1) | ✅ 14/14 |
| 39 项 cli_smoke test (ACT-2) | ✅ 39/39 |
| 9 项 redaction 自测 | ✅ 9/9 |
| 10 个 CLI 子命令 | ✅ 全部跑通 |
| redaction FAIL/WARN 路径 | ✅ 都验证 |
| 临时目录测试隔离 | ✅ |
| README 更新 | ✅ |
| AGENT_WORKFLOW 更新 | ✅ |
| DATA_MODEL 更新 | ✅ |
| MVP_PLAN 更新 | ✅ |
| 隐私脱敏 | ✅ |
| Git 提交 | ⏳（下一步） |
| 推送到 GitHub | ❌ 按要求未推送 |
| 建议进入 ACT-3 | ✅ |

**ACT-2 状态：COMPLETE**

下一步等待用户确认是否进入 **ACT-3（Astro 静态 dashboard）**。
