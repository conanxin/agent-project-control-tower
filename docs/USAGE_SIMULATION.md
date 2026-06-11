# Usage Simulation — A Day in the Life

> 这份文档用**两个项目和三个 agent** 的完整一天，把"控制塔"怎么用、event 怎么流动、dashboard 最后长什么样，全部走一遍。
>
> 读完之后，你应该能向任何新加入的 agent 讲清楚：它该在什么时机、上报什么。

---

## 0. 准备：演员表

| 角色 | ID | 在哪 | 干什么 |
| --- | --- | --- | --- |
| 本地主控 agent | `local-hermes` | 笔记本（home: `$WORKSPACE`） | 跨项目协调、写脚手架、长任务 |
| 本地专项 agent | `local-codex` | 同一台笔记本 | 重构、Code Review、批量修改 |
| 云端 agent | `cloud-openclaw` | 云端 VPS | 长跑、批量抓取、自动化部署 |
| 项目 A | `local-book-tool` | 笔记本（`~/projects/local-book-tool`） | 离线 EPUB 处理工具 |
| 项目 B | `cloud-art-site` | 云端 VPS（`/srv/cloud-art-site`） | 静态艺术作品网站 |
| 控制塔仓库 | `agent-project-control-tower` | 笔记本 + 云端 + GitHub | 进度事实源 |

控制塔仓库地址（假设）：`https://github.com/xin/agent-project-control-tower.git`
两台机器都 clone 到本地：

- 笔记本：`~/workspace/projects/agent-project-control-tower`
- 云端：`/srv/agent-project-control-tower`

---

## 1. 早上 9:00 — 注册本地 agent

我在笔记本第一次 clone 控制塔仓库后，先注册我自己常用的 agent。

```bash
cd ~/workspace/projects/agent-project-control-tower
tower register-agent \
  --id local-hermes \
  --machine local \
  --type hermes \
  --display-name "Local Hermes (notebook)" \
  --operator xin
```

这条命令在背后做了三件事：

1. **修改** `registry/agents.yml`——在 agents 列表里追加一条 `local-hermes` 记录
2. **追加** 一个 `events/agent_registered_local-hermes.json`——记录"什么时候、谁注册了这个 agent"
3. **commit + push** 到控制塔仓库

> ⚠️ 即使 `register-agent` 是在控制塔仓库目录里执行的，它也**不会**写回任何原项目仓库。这条边界是硬约束。

`registry/agents.yml` 多了这一段：

```yaml
- id: local-hermes
  type: hermes
  machine: local
  display_name: "Local Hermes (notebook)"
  operator: xin
  status: ACTIVE
  registered_at: 2026-06-11T09:00:00Z
```

## 2. 早上 9:05 — 注册本地项目

```bash
tower register-project \
  --id local-book-tool \
  --name "Local Book Tool" \
  --repo https://github.com/xin/local-book-tool \
  --scope local \
  --home-machine local \
  --primary-agent local-hermes \
  --description "Offline EPUB → Markdown converter with sidecar knowledge base"
```

背后发生：

- `registry/projects.yml` 追加 `local-book-tool`
- `events/project_registered_local-book-tool.json` 写入
- commit + push

## 3. 早上 9:10 — 第一次看到 dashboard

我打开 `https://control-tower.xin.dev/`（Cloudflare Pages 自动部署完成）：

```
┌────────────────────────────────────────────┐
│  Agent Project Control Tower               │
│                                            │
│  Projects: 1     Agents: 1     Events: 2   │
│                                            │
│  ● local-book-tool                         │
│    status: ACTIVE   health: gray            │
│    "Offline EPUB → Markdown converter"     │
└────────────────────────────────────────────┘
```

`gray` 健康度是因为注册了项目但**还没有任何 phase event**——既没成功也没失败。

## 4. 早上 9:30 — 注册云端 agent

SSH 到云端 VPS，clone 控制塔仓库，做同样的注册：

```bash
ssh vps
cd /srv/agent-project-control-tower
git pull
tower register-agent \
  --id cloud-openclaw \
  --machine cloud \
  --type openclaw \
  --display-name "Cloud OpenClaw (VPS)" \
  --operator xin
```

> 这条命令在**云端**执行，但它**写入同一个控制塔仓库**（先 commit 在云端 clone，再 git push）。

`registry/agents.yml` 在远端多了一条记录，dashboard 自动重建后看到：

```
Projects: 1     Agents: 2     Events: 3
```

## 5. 早上 9:35 — 注册云端项目

```bash
tower register-project \
  --id cloud-art-site \
  --name "Cloud Art Site" \
  --repo https://github.com/xin/cloud-art-site \
  --scope cloud \
  --home-machine cloud \
  --primary-agent cloud-openclaw \
  --description "Static gallery for public-domain art"
```

> **关键边界**：这条命令在云端执行，但它**不会**改 `cloud-art-site` 这个原项目仓库。一个字都不会写过去。

## 6. 上午 10:00 — 本地 Hermes 完成 L1

我在 `~/projects/local-book-tool/` 写完 L1（CLI 解析 + 单元测试）：

```bash
cd ~/projects/local-book-tool
git add .
git commit -m "L1: EPUB CLI parser with 18 passing tests"
git push origin main
```

然后上报：

```bash
# 重要：cwd 可以是原项目目录，但命令本身在写控制塔仓库
tower report phase \
  --project local-book-tool \
  --agent local-hermes \
  --phase L1 \
  --status PASS \
  --summary "EPUB CLI parser + 18 unit tests" \
  --commit $(git rev-parse HEAD) \
  --next "L2: convert EPUB → Markdown with image extraction"
```

背后发生：

1. **原项目仓库**：`local-book-tool` 收到一个 commit（你刚 push 的）
2. **控制塔仓库**：
   - `events/2026-06-11/local-book-tool__L1__PASS__local-hermes.json` 写入
   - **可选**：自动 git pull 控制塔最新 → 写文件 → git push
3. dashboard 重新构建，刷新后看到：

```
● local-book-tool
  health: green (1 PASS)
  timeline:
    L1 ✓ PASS  local-hermes  10:00  "EPUB CLI parser + 18 unit tests"
  next: L2 — convert EPUB → Markdown
```

## 7. 中午 12:00 — 本地 Codex 接手 L2

午饭后我想用 Codex 跑重构（L2：转 Markdown 流水线）。**关键点：项目不需要重新注册**——`local-book-tool` 已经在 `projects.yml` 里，Codex 直接接手上报就行。

```bash
cd ~/projects/local-book-tool
tower report phase \
  --project local-book-tool \
  --agent local-codex \
  --phase L2 \
  --status FAIL \
  --summary "EPUB→MD parser crashes on DRM-protected files (TypeError in opf parser)" \
  --commit $(git rev-parse HEAD) \
  --next "L2-fix: graceful skip DRM files + emit warning.json"
```

> **同一项目、第二个 agent**：dashboard 不会因为是新的 agent 而创建新项目条目，而是在 `local-book-tool` 的时间线里追加一条事件，标记为 `local-codex` 完成。

dashboard 立刻变：

```
● local-book-tool
  health: yellow (1 PASS, 1 FAIL)
  timeline:
    L1     ✓ PASS   local-hermes  10:00
    L2     ✗ FAIL   local-codex   12:00  "DRM-protected files crash"
  blocked_by: L2
  next: L2-fix
```

## 8. 下午 14:00 — Codex 修好 L2-fix 并上报

```bash
tower report phase \
  --project local-book-tool \
  --agent local-codex \
  --phase L2-fix \
  --status PASS \
  --summary "Skip DRM-protected EPUBs gracefully, emit warnings.json" \
  --commit $(git rev-parse HEAD) \
  --next "L3: knowledge-base sidecar (entities + relations)"
```

dashboard：

```
● local-book-tool
  health: green
  timeline:
    L1       ✓ PASS   local-hermes
    L2       ✗ FAIL   local-codex
    L2-fix   ✓ PASS   local-codex
  next: L3
```

## 9. 下午 15:00 — 云端 OpenClaw 完成 C1

在云端 VPS 上：

```bash
cd /srv/cloud-art-site
tower report phase \
  --project cloud-art-site \
  --agent cloud-openclaw \
  --phase C1 \
  --status PASS \
  --summary "Static gallery generated, 120 images indexed, sitemap ready" \
  --commit $(git rev-parse HEAD) \
  --next "C2: tag filter UI + lazy load"
```

## 10. 下午 16:00 — 本地 Hermes 复查云端结果

我想在本地笔记本上"复查"云端的 C1 输出。注意：

- 复查**不需要改控制塔注册**——`cloud-art-site` 已经被云端 OpenClaw 注册过了
- 我直接 `tower report review` 即可

```bash
cd /srv  # 任意位置都行
tower report review \
  --project cloud-art-site \
  --agent local-hermes \
  --reviewed-phase C1 \
  --verdict PASS \
  --summary "Cross-checked sitemap.xml, all 120 images reachable, 0 broken links" \
  --next "C2 can proceed"
```

`local-hermes` 第一次出现在 `cloud-art-site` 的时间线上：

```
● cloud-art-site
  health: green
  timeline:
    C1       ✓ PASS    cloud-openclaw  15:00
    C1.review ✓ PASS   local-hermes    16:00  (reviewed)
```

## 11. 晚上 21:00 — 一天结束的 dashboard

```
┌─────────────────────────────────────────────────────┐
│  Agent Project Control Tower           2026-06-11   │
│                                                     │
│  Projects: 2   Agents: 3   Events: 8               │
│  Health: 1 green, 1 green, 0 yellow, 0 red         │
│                                                     │
│  Recent activity                                    │
│  ──────────────────────────────────────────────     │
│  16:00  local-hermes  review  cloud-art-site  C1   │
│  15:00  cloud-openclaw phase  cloud-art-site  C1 ✓ │
│  14:00  local-codex   phase  local-book-tool L2fx ✓│
│  12:00  local-codex   phase  local-book-tool L2 ✗  │
│  10:00  local-hermes  phase  local-book-tool L1 ✓  │
│                                                     │
│  ● local-book-tool                                  │
│    health: green                                    │
│    agents involved: local-hermes, local-codex       │
│    next: L3 — knowledge-base sidecar                │
│                                                     │
│  ● cloud-art-site                                   │
│    health: green                                    │
│    agents involved: cloud-openclaw, local-hermes    │
│    next: C2 — tag filter UI                         │
└─────────────────────────────────────────────────────┘
```

## 12. 关键心法（请重读）

> **进展最终写入控制塔文件夹，而不是只写在原项目文件夹中。可以在原项目目录里执行 report 命令，但命令背后仍然写入控制塔仓库。**

这一句话是整个系统的**反直觉点**。再次展开：

| 你以为会这样 | 实际是这样 |
| --- | --- |
| "我在 `local-book-tool/` 执行 `tower report`，那它应该在那个目录里建个文件吧" | 命令**始终**在控制塔仓库目录下写文件。如果 cwd 是原项目目录，命令会先 `cd $TOWER_REPO` 再写 |
| "那原项目仓库就没进度记录了？" | **有**——通过 `commit` 字段：event JSON 里存 commit SHA，dashboard 会展示原项目 commit 链接 |
| "agent 失败不写 event，dashboard 不就骗人了吗？" | 是的，这是已记录的风险（见 [RISKS_AND_BOUNDARIES.md](RISKS_AND_BOUNDARIES.md)）。MVP 不做"心跳缺失告警"，但**所有 phase 完成后必须 report** 是 agent 的硬契约 |
| "我手动 git pull 控制塔，会不会和别人冲突？" | 几乎不会——因为写的是不同 event 文件。冲突预案见 [RISKS_AND_BOUNDARIES.md](RISKS_AND_BOUNDARIES.md) |
| "注册一次以后还能改吗？" | **永远不要修改已注册的元数据**（项目 ID、repo URL）。如果要"改"——写一个 `correction` event 指向原 event |

## 13. 第二个项目失败时的样子

假设第二天 `local-codex` 在 L3 又栽了：

```bash
tower report phase \
  --project local-book-tool \
  --agent local-codex \
  --phase L3 \
  --status FAIL \
  --summary "Knowledge-base sidecar: out-of-memory on 800MB Markdown" \
  --blocker "chunking strategy must change before L3 retry" \
  --next "L3-retry: streaming chunker + reduce memory footprint"
```

`blocker` 字段会让 dashboard 在首页显示一个红色横幅：

```
⚠ BLOCKED: local-book-tool L3 — chunking strategy must change
```

并且项目 health 变 red。
