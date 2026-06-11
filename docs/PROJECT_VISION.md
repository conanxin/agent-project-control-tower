# Project Vision

> 写给未来的自己，以及任何想用控制塔管理 agent 化项目的人。

## 一句话愿景

**让"我在用 N 个 agent 跑 M 个开源项目"这件事，对我自己和外部观察者来说，都是可看、可查、可信任的。**

## 为什么需要"控制塔"这种形态

### 1. 项目和人都在分裂

我的工作流是：

- **机器分裂**：笔记本、台式机、云端 VPS，每台机器跑不同的 agent
- **agent 分裂**：本地 Hermes、本地 Codex、云端 OpenClaw、云端 Claude Code……每个 agent 擅长不同任务（脚手架 / 重构 / 长跑 / 复查）
- **项目分裂**：每个项目都住在自己的 GitHub 仓库里，commit 历史互不相关

但"项目状态"是一个**跨维度的概念**——它不归属任何单一仓库，而是横跨 N 台机器 × M 个 agent × K 个项目。

控制塔就是给这个横跨维度一个**统一的事实源**。

### 2. 进度汇报的痛点

没控制塔的时候，我汇报"今天干了啥"只能：

- 翻聊天记录找最新的 phase 报告
- 把多个项目的 commit 列表手动拼起来
- 写一篇"今天总结" markdown，发到 GitHub Pages

这套流程**每周要花 1–2 小时**，且**容易遗漏**——尤其是失败、阻塞、换 agent 这种"反常事件"。

### 3. "Git 作为进度事实源"是这个项目最关键的设计判断

我曾经想过：

- 写一个 SaaS 后端（Notion API、Airtable……）
- 起一个数据库（Postgres + Adminer）
- 用 webhook + 实时推送

全部否掉了。理由：

| 候选方案 | 致命问题 |
| --- | --- |
| Notion / Airtable | 数据在我控制之外，agent 写入需要 API token，且无法 git diff |
| Postgres + 后端 | 多机器写入要中央服务，agent 必须能连；schema 演化痛苦 |
| Webhook + 实时 | 没有"事件日志"语义，失败难回放 |
| **Git 仓库 + JSON 文件** | **天然 append-only、天然可 diff、天然支持多机写** |

Git 仓库 + JSON 文件的额外好处：

- **可离线**：agent 不联网也能写，等联网再 push
- **可重放**：想知道"两周前 L2 到底为什么失败"，翻那个 JSON 就行
- **可审计**：每个 event 都有 author + commit
- **可迁移**：换 SaaS？把所有 JSON 倒过去就行，没有锁定

## 设计原则

1. **静态优先，动态兜底**
   - 优先用 Git + 静态站点（Cloudflare Pages / GitHub Pages）
   - 任何"必须有后端"的需求都先打回，重新设计成"生成静态文件"

2. **进度是 append，不是 replace**
   - event 永远只追加
   - "修改一个事件" = 写一个"correction event"指向原 event
   - dashboard 渲染时按时间线合并

3. **真实项目代码仍在原仓库**
   - 控制塔永远不存代码、永远不存构建产物
   - 控制塔只存"指针"：项目在哪个仓库、最近 commit 是什么、PR 链接是什么

4. **agent 友好，人类也友好**
   - event JSON 字段名要 `snake_case` 且自带说明（`phase`、`status`、`summary`、`next`）
   - 任何 field 都可以省略（最小可写 = 项目 ID + agent ID + 阶段 + 状态）

5. **隐私和安全默认开启**
   - 公开仓库 = 只能写脱敏后的 event
   - 任何想写本地路径、IP、token 的尝试都被前置脚本拒绝（见 [RISKS_AND_BOUNDARIES.md](RISKS_AND_BOUNDARIES.md)）

## 不做什么（明确边界）

- ❌ 不做用户系统、登录、权限
- ❌ 不做实时通知（Slack / Discord webhook 留给 ACT-7+）
- ❌ 不做代码 review、CI 触发
- ❌ 不替代原项目仓库的 README、CHANGELOG、Release
- ❌ 不写"项目管理"功能（任务分解、燃尽图、Sprint）——那是上层工具的活
- ❌ 不接企业内部网络、不做端到端加密

## 长期愿景

如果这个项目真的用起来，我希望它能长成：

```
Year 0  ← 你在这里（ACT-0）
  只有设计文档 + 1 个本地项目 + 1 个云端项目

Year 1
  3–5 个 agent、5–10 个项目、事件时间线稳定
  README 一打开就有人能看懂"这人在用 agent 跑开源"

Year 2
  其他"多 agent 跑开源项目"的人 fork 出去自用
  开始收到 issue："能不能加个跨项目的统计页？"

Year 3+
  也许有人写一个 web-based editor：拖拽生成 event
  也许有人接 Linear / GitHub Issues
  也许变成一个 "agent-native project management" 范式
```

但**这都是猜想**。**ACT-0 的目标只是：把第一块砖放对位置。**

## 成功的定义

- **最低限度**：ACT-3 时打开 `https://control-tower.xxx/` 能看到至少 2 个项目的真实时间线
- **理想**：有外部访客发邮件问"你这个控制塔是怎么搭的？"
- **失败信号**：写到 ACT-3 之后只有我自己看、且每次维护要超过 30 分钟/周

如果出现"失败信号"，我会**回退**到"每周手写一份 status report"——控制塔不该比手动更累。
