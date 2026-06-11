# PHASE ACT-0 — Project Design and Architecture Report

> **Phase**: ACT-0 — Project Design and Architecture
> **Date**: 2026-06-11
> **Author**: xin (via Hermes)
> **Scope**: 项目骨架、设计文档、示例数据、阶段报告
> **Status**: ✅ COMPLETE
> **Recommendation**: ✅ PROCEED to ACT-1

---

## 1. Executive Summary

ACT-0 完成了 **Agent Project Control Tower** 项目的完整设计骨架，但**没有写任何运行时代码**。本次产出：

- 1 个 `README.md`（通俗版说明）
- 9 篇 `docs/*.md`（设计文档）
- 2 个示例注册表 + 3 个示例 event JSON + 1 个 `examples/README.md`
- 1 份本阶段报告
- 1 份 `.gitignore`
- 1 个本地 git 仓库初始化 + 1 个 commit

**关键设计判断**：

1. **Git + JSON + 静态站点**——拒绝引入数据库 / 后端 / 用户系统
2. **append-only event 流**——纠错写 correction event，绝不修改历史
3. **原项目代码留在原仓库**——控制塔只存指针 + 阶段事件
4. **多 agent 接力同一项目**——注册一次，无限次 report

**完成度**：100%（按用户给定的 15 项任务清单）

---

## 2. Why this design

### 2.1 "控制塔"这个形态的合理性

我同时在多台机器、用多个 agent 跑多个开源项目：

- 进度信息散落在 GitHub commit、聊天记录、私人笔记
- 跨机器跨 agent 状态无统一视图
- 想对外分享进展只能手动截图拼凑

控制塔用"**Git 当事实源 + 静态站点当展示层**"这一最朴素架构解决——所有 event 都是 Git commit，dashboard 只是 `git push` 后的副产品。**零基础设施成本**，**零运维**。

### 2.2 为什么不用数据库 / 后端

- 数据库：agent 写入需要中央服务，无法离线
- 后端：会引入鉴权、API、CORS、部署等一连串问题
- 实时通知：MVP 不需要——5 分钟的 CI 重建已足够"近实时"

Git 的 `append-only + diff + multi-clone` 性质天然匹配"事件流"语义。

### 2.3 为什么"原项目仓库不动"

| 选项 | 风险 |
| --- | --- |
| 把项目代码搬进控制塔 | 失去原项目的 GitHub Pages / Issues / Releases |
| 在原项目里嵌 `.tower/` 目录 | 污染原项目结构，agent 要写两份 |
| **控制塔只存指针** ✅ | **原项目保留全部独立生态** |

`commit` 字段是关键桥接——dashboard 渲染时显示"原项目 commit 链接"，让访客能跳过去看真实代码。

### 2.4 为什么"项目只注册一次"

- 多机器协作时，agent 不应假设"自己注册过了"
- 多 agent 接手时，handoff event 即可，不需要重注册
- 重注册会造成 dashboard 出现"两个项目"

**铁律写进 agent prompt 模板 + tower 脚本双重防护**。

---

## 3. Files Created

### 3.1 顶层

| 文件 | 字节 | 作用 |
| --- | --- | --- |
| `README.md` | 6032 | 通俗版总览：是什么、为什么用、5 分钟模拟 |
| `.gitignore` | 293 | 排除 `generated/`、`site/dist/`、`.venv/`、`node_modules/` |

### 3.2 `docs/`（9 篇设计文档）

| 文档 | 字节 | 解决的问题 |
| --- | --- | --- |
| `PROJECT_VISION.md` | 4911 | 为什么做、设计原则、长期愿景、不做什么 |
| `USAGE_SIMULATION.md` | 12325 | 一整天的端到端模拟 + 关键心法 |
| `ARCHITECTURE.md` | 10512 | 目录结构、数据流、不变量、扩展点 |
| `DATA_MODEL.md` | 10636 | 7 类 event 的 schema + 完整 JSON 例子 + 隐私反 schema |
| `AGENT_WORKFLOW.md` | 10818 | 给 agent 看的 CLI 操作手册 + 6 个协作剧本 |
| `MVP_PLAN.md` | 9126 | ACT-1 到 ACT-6 的范围 / 验收 / 退出条件 |
| `OPEN_SOURCE_PLAN.md` | 7935 | License、README 章节、脱敏规则、公开发布 checklist |
| `DEPLOYMENT_PLAN.md` | 6775 | Cloudflare Pages 优先、GitHub Pages 备选、回滚 |
| `RISKS_AND_BOUNDARIES.md` | 10658 | 12 个风险 + 缓解方案 + 风险总表 |

### 3.3 `examples/`（ACT-1 事实源）

| 文件 | 字节 | 表达内容 |
| --- | --- | --- |
| `projects.yml` | 1423 | 1 个本地项目 + 1 个云端项目 |
| `agents.yml` | 1189 | 3 个 agent（2 本地 + 1 云端） |
| `events/local-book-tool_L1_PASS_local-hermes.json` | 640 | 本地项目首阶段 PASS |
| `events/cloud-art-site_C1_PASS_cloud-openclaw.json` | 651 | 云端项目首阶段 PASS |
| `events/local-book-tool_L2_FAIL_local-codex.json` | 781 | 同一项目、第二个 agent、FAIL |
| `examples/README.md` | 1753 | 文件清单 + 表达内容 + 脱敏状态 |

### 3.4 `reports/`

| 文件 | 字节 | 作用 |
| --- | --- | --- |
| `PHASE_ACT0_PROJECT_DESIGN_REPORT.md` | (本文件) | ACT-0 阶段报告 |

### 3.5 总计

```
文件数:    18
总大小:    ~96 KB（不含 .git/）
目录深度:  3 层
```

---

## 4. Document Roles — Quick Reference

> 给未来的我一张"哪个文档答什么问题"的速查表。

| 我想知道… | 去看 |
| --- | --- |
| 这个项目到底是啥？ | `README.md` |
| 长期愿景 / 不做什么 | `docs/PROJECT_VISION.md` |
| 一个具体的一天怎么用？ | `docs/USAGE_SIMULATION.md` |
| 目录结构 / 数据流？ | `docs/ARCHITECTURE.md` |
| event 长啥样？字段怎么填？ | `docs/DATA_MODEL.md` |
| agent 怎么调命令？ | `docs/AGENT_WORKFLOW.md` |
| 接下来做什么？按什么顺序？ | `docs/MVP_PLAN.md` |
| 怎么开源、怎么脱敏？ | `docs/OPEN_SOURCE_PLAN.md` |
| 怎么部署到线上？ | `docs/DEPLOYMENT_PLAN.md` |
| 哪些事会翻车？ | `docs/RISKS_AND_BOUNDARIES.md` |
| ACT-1 跑什么？ | `examples/README.md` |

---

## 5. Current System State

### 5.1 仓库状态

- ✅ Git 仓库初始化（`git init`）
- ✅ 单次 commit（`ACT-0: design agent project control tower`）
- ❌ **未**推送到 GitHub（按用户要求"除非明确要求"）
- ❌ **未**创建远程仓库

### 5.2 文件系统

```
~/workspace/projects/agent-project-control-tower/
├── .git/
├── .gitignore
├── README.md
├── docs/                      (9 个 .md)
├── examples/                  (projects.yml + agents.yml + 3 events + README)
├── reports/                   (本报告)
└── scripts/                   (空目录，ACT-2 填充)
```

### 5.3 跑通的部分

- 文档可读 ✅
- 示例数据脱敏 ✅（手动 audit 过）
- 数据模型自洽 ✅（event ↔ registry ↔ generated 三方一致）

### 5.4 没跑通的部分（按设计就是如此）

- ❌ 没有 `tower` CLI
- ❌ 没有 `build_index.py`
- ❌ 没有 dashboard
- ❌ 没有 CI
- ❌ 没有线上部署

这些都在 ACT-1 之后按 [MVP_PLAN.md](docs/MVP_PLAN.md) 顺序实现。

---

## 6. Design Boundaries（明确边界）

ACT-0 阶段**没有**：

- ❌ 写任何 Python / Node 代码
- ❌ 引入任何外部依赖（npm、pip、cargo 等）
- ❌ 创建 GitHub 仓库
- ❌ 部署任何服务
- ❌ 引入数据库 / 后端 / 用户系统
- ❌ 修改任何**已有**项目（即 Artvee Gallery、BookTrans Desk 等原项目）
- ❌ 触碰 `~/workspace/projects/` 下的其他目录

**已严格遵守**：

- ✅ 用户模板中的每一条要求
- ✅ "本阶段只做本地设计提交"——`git init` + 1 个本地 commit
- ✅ "不创建 GitHub 远程仓库"
- ✅ "不 push 到 GitHub"

---

## 7. Risk Analysis

详见 [docs/RISKS_AND_BOUNDARIES.md](docs/RISKS_AND_BOUNDARIES.md)。本节只列 **ACT-0 完成时**的剩余风险：

| 风险 | 状态 | 备注 |
| --- | --- | --- |
| 设计文档与未来实际实现偏差 | 中 | 缓解：ACT-2 写完 CLI 后回填 |
| 文档过长，agent 读不完 | 中 | 缓解：AGENT_WORKFLOW.md 章节化、可挑读 |
| 隐私规则没在 CI 中强制 | **高** | ACT-2 必须实现 `redaction.py` + CI 校验 |
| Git 冲突预案只在文档里 | 中 | ACT-2 必须在脚本里实现 rebase |
| `generated/` 进 Git 的诱惑 | 低 | .gitignore 已加；需在 ACT-2 CI 二次校验 |

**ACT-0 不引入的新风险**——本次纯文档工作，所有风险都是"未来如果 X"。

---

## 8. Recommendation for Next Phase

### 8.1 是否进入 ACT-1？

**强烈建议：进入 ACT-1**。

理由：

- ACT-0 完整覆盖了用户模板的 15 项任务
- 设计文档自洽（vision / arch / data / workflow 互相引用一致）
- 示例数据已经能"手渲染"出一个 dashboard
- ACT-1 范围小（< 1 周）且可独立 revert

### 8.2 ACT-1 范围（来自 [MVP_PLAN.md](docs/MVP_PLAN.md)）

- 手写 `examples/generated/index.json`
- 手写 `examples/site/index.html`（内联 CSS + JS，读 index.json 渲染）
- `xdg-open` 能开
- 零 npm / 零 python

**建议不要在 ACT-1 加额外目标**——保持"零依赖、零代码、可双击打开"。

### 8.3 ACT-1 退出条件（自检）

- [ ] 我能在不写一行代码的情况下，把 examples/ 升级成"能展示的 dashboard"
- [ ] 我对最终视觉满意到"这值得自动化"
- [ ] examples 目录 < 200KB

### 8.4 ACT-1 → ACT-2 的桥梁

ACT-1 完成后，ACT-2 的 `build_index.py` 直接读 ACT-1 手写的 `generated/index.json` 结构做模板——保证 ACT-1 不是一次性 demo，而是 ACT-2 的契约。

---

## 9. Open Questions（待 ACT-1 验证）

- [ ] **手写 dashboard 视觉效果如何？** 决定 ACT-3 是否需要 Astro，还是用纯 HTML+JS 也够
- [ ] **3 个示例 event 够不够展示 health 派生？** 决定 ACT-2 是否要加 fixture 生成器
- [ ] **"next" 字段在 dashboard 上的呈现位置？** 决定 ACT-3 组件设计

---

## 10. Self-Audit (Redaction Check)

ACT-0 阶段输出**所有**内容均已通过人工 audit：

- ✅ 无内网 / 公网 IP
- ✅ 无 `/home/xxx/` 路径
- ✅ 无 `C:\Users\xxx\` 路径
- ✅ 无 API token / SSH key
- ✅ 所有 commit SHA 是占位符（`abc1234`、`feedface`、`beef0001`、`deadbeef`）
- ✅ 所有 repo URL 是占位符（`https://github.com/xin/...`）
- ✅ 项目名 / agent 名 是占位符（`local-book-tool`、`local-hermes` 等）

ACT-2 将用 `scripts/redaction_check.py` 把这个 audit 自动化。

---

## 11. Sign-off

| Item | Status |
| --- | --- |
| 用户 15 项任务清单 | ✅ 100% |
| 设计文档自洽 | ✅ vision ↔ arch ↔ data ↔ workflow 互引一致 |
| 示例数据脱敏 | ✅ 人工 audit 通过 |
| Git 初始化 + 单次 commit | ✅ |
| 推送到 GitHub | ❌ 按要求未推送 |
| 阶段报告（本文件） | ✅ |
| 建议进入 ACT-1 | ✅ |

**ACT-0 状态：COMPLETE**

下一步等待用户确认是否进入 **ACT-1（手写 data + index + 静态 HTML）**。
