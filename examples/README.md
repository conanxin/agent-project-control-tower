# Examples — Agent Project Control Tower

> ACT-1 的"事实源"——这一目录的 YAML 和 JSON 会被手写渲染成一个静态 HTML，**证明数据流能跑通**。

## 文件

| 文件 | 作用 |
| --- | --- |
| `projects.yml` | 项目注册表（含 `local-book-tool` 和 `cloud-art-site`） |
| `agents.yml` | agent 注册表（含 `local-hermes`、`local-codex`、`cloud-openclaw`） |
| `events/local-book-tool_L1_PASS_local-hermes.json` | 第一个本地项目第一个阶段，PASS |
| `events/cloud-art-site_C1_PASS_cloud-openclaw.json` | 第一个云端项目第一个阶段，PASS |
| `events/local-book-tool_L2_FAIL_local-codex.json` | 同一项目、第二个 agent、第二个阶段、FAIL |

## 表达的内容

- **一个本地项目**：`local-book-tool`
- **一个云端项目**：`cloud-art-site`
- **同一项目多个 agent**：`local-book-tool` 同时有 `local-hermes`（L1 PASS）和 `local-codex`（L2 FAIL）
- **成功事件**：L1 / C1 都是 PASS
- **失败事件**：L2 FAIL，且 `summary` 解释了原因 + `next` 给出修复方向
- **下一步建议**：每个 event 的 `next` 字段就是 dashboard 上的"next action"

## 脱敏状态

- 所有项目 ID、agent ID 都是占位符
- commit SHA 用明显假的（`abc1234`、`feedface`、`beef0001`）
- repo URL 用 `https://github.com/xin/...` 占位
- 不含 IP、home path、token

跑 `python ../../scripts/redaction_check.py`（ACT-2 实现）应全绿。

## ACT-1 任务清单

- [ ] 写一个手写 `generated/index.json`（聚合 registry + events）
- [ ] 写一个手写 `site/index.html`（读 index.json 渲染）
- [ ] `xdg-open site/index.html` 能看到 2 个项目 + 1 个 FAIL
- [ ] 把整套 examples/ 拷到 README "Quick start" 区块
