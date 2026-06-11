# Risks and Boundaries

> 哪些事会让控制塔"翻车"，以及怎么预防。
>
> 每条风险按 **风险描述 → 触发条件 → 影响 → 缓解方案 → 检测方式** 展开。

---

## R1. 多 agent 同时 push 冲突

### 风险描述

笔记本 local-hermes 和云端 cloud-openclaw 几乎同时跑完一个 phase，都试图 `git push` 到控制塔。

### 触发条件

- 两台机器的时钟差 < 1 分钟
- 同一项目的不同 phase 几乎同时上报

### 影响

- 后 push 的一方被 Git 拒绝
- 看起来"事件丢了"

### 缓解方案

- **`tower` 脚本自动 rebase**：
  ```python
  def push_with_retry(remote='origin', branch='main', max_retries=3):
      for i in range(max_retries):
          try:
              subprocess.run(['git', 'push', remote, branch], check=True)
              return
          except subprocess.CalledProcessError:
              subprocess.run(['git', 'pull', '--rebase', remote, branch], check=True)
              subprocess.run(['git', 'push', remote, branch], check=True)
              return
  ```
- **event 文件名带 UUID 而非时间戳**——同名概率几乎为零
- **写本地锁文件**（`/tmp/tower.lock`）——同一台机器上的并发由它拦截

### 检测方式

- `tower report` 退出码非零
- CI build log 显示 "merge conflict"

---

## R2. 重复注册项目

### 风险描述

`local-hermes` 在笔记本注册了 `local-book-tool`，几天后 `cloud-openclaw` 在 VPS 上也调一次 `register-project --id local-book-tool`。

### 触发条件

- 多机器协作时，agent 不知道项目已被注册
- agent 在 prompt 里被要求"确保项目已注册"，每次执行都重注册

### 影响

- `projects.yml` 出现两条同名记录
- dashboard 显示"两个项目"
- 旧 event 不知道归属哪条

### 缓解方案

- **注册时 `grep` 检测**：
  ```python
  yaml.safe_load(open('registry/projects.yml'))
  if any(p['id'] == new_id for p in projects):
      print(f"Project {new_id} already registered; skipping")
      sys.exit(0)
  ```
- **agent prompt 模板固化**："在调用 `register-project` 之前先 `tower list-projects`"
- **CI 在 build 时校验**：`projects.yml` 的 `id` 字段必须唯一

### 检测方式

- `tower register-project` 退出码 1
- CI build log: "duplicate project id"

---

## R3. event schema 不一致

### 风险描述

local-hermes 写 `event_type: "phase_done"`，local-codex 写 `event_type: "phase"`——同一概念两种名字。

### 触发条件

- 多个 agent 独立写 event
- schema 文档没读完

### 影响

- `build_index.py` 无法正确分类
- dashboard 时间线漏事件

### 缓解方案

- **Pydantic v2 enum 强制**：
  ```python
  class EventType(str, Enum):
      PHASE = "phase"
      REVIEW = "review"
      HANDOFF = "handoff"
      FAILURE = "failure"
      ...
  ```
- **CI 校验所有 event 文件**：解析失败直接拒绝 build
- **文档置顶警告**：在 [DATA_MODEL.md](DATA_MODEL.md) 顶部明文写"event_type 只接受以下值"

### 检测方式

- `python scripts/validate_events.py` 退出码非零
- CI 失败信息

---

## R4. 隐私泄露（IP / 路径 / token）

### 风险描述

agent 在 `--summary` 里写了：

```bash
tower report phase --summary "tested on http://192.168.1.42:8080, all green"
```

或：

```bash
tower report phase --commit $(cat /home/xin/.ssh/id_rsa.pub)
```

### 触发条件

- agent prompt injection
- agent 偷懒，直接把日志原文粘进去
- 人手写 event 时疏忽

### 影响

- 一旦 push 到公开仓库，**永远删不干净**（git history）
- 内网拓扑暴露
- 真实路径暴露

### 缓解方案

- **CI 强校验**：`redaction.py` 拒绝匹配隐私模式的 event
- **本地 pre-commit hook**（ACT-2+）：commit 前跑一次 redaction
- **agent prompt 模板自带提醒**：
  > ⚠️ 写 summary 之前先确认：不含 IP、不含 /home/xxx/、不含 token
- **git history 改写工具**：`git filter-repo` + 强制 push（紧急时用，但要通知所有协作者）

### 检测方式

- `python scripts/redaction_check.py --strict` 退出码 1
- GitHub secret scanning 自动报警
- 月度审计：`git log --all -p | grep -E '(192\.168|/home/xin|sk-)'`

---

## R5. agent 把失败隐藏不报

### 风险描述

agent 跑挂后直接退出，不调 `tower report failure`，dashboard 还显示上一个 PASS。

### 触发条件

- agent 没有"失败时必须 report"的硬契约
- 错误处理逻辑只 `print` 不上报
- 进程被 kill -9

### 影响

- 失真：项目卡了 3 天，dashboard 仍 green
- 信任崩塌：访客看到的状态不可靠

### 缓解方案

- **MVP 不解决**——这是已知缺陷
- **缓解措施 1**：agent 启动时开 watchdog，超时未 report → 写一条 `heartbeat_lost` event
- **缓解措施 2**：CI 每天跑一次"上次 phase 到现在 > 7 天 → 自动写 `stale` event"
- **缓解措施 3**：把"上报"作为 agent 任务模板的最后一步，LLM 很难漏掉

### 检测方式

- 每周人工 audit
- 自动"长期无 event"检测

---

## R6. generated 文件被 agent 手动修改

### 风险描述

agent 看到 `generated/index.json` 里有错（比如 health 算错），直接编辑文件。

### 触发条件

- `generated/` 被 commit 进 Git（错误！）
- 文档没说清"generated 是 CI 产物"

### 影响

- 下次 CI 跑的时候又生成一遍，把手改的覆盖
- 出现"git diff 显示 generated 有未提交改动"困惑

### 缓解方案

- **`generated/` 加入 `.gitignore`**
- **CI 构建时把 generated/ 当 artifact，不 commit**
- **文档强调**（[ARCHITECTURE.md](ARCHITECTURE.md)）："永远不要 commit generated/"

### 检测方式

- `git status` 永远不应该显示 `generated/`
- CI log 显示 "generated files present, removing before build"

---

## R7. 项目状态和原项目 commit 不一致

### 风险描述

控制塔显示 `local-book-tool L1 PASS`，但原项目仓库其实没有对应 commit（agent 上报后撤销了 / force push 了）。

### 触发条件

- 原项目用 force push
- agent 写完 event 但 push 失败
- 私有分支被 squash 后 commit SHA 变了

### 影响

- dashboard 上的 commit 链接 404
- 跟踪失去真实性

### 缓解方案

- **CI 校验 commit 链接存在**（HEAD request）
- **event 写"实际 commit URL"而非"SHA"**——让原项目 CI 决定 SHA
- **重大变更写 correction event** 指向原 event
- **agent 强制契约**：先 `git push`，看到 "pushed successfully" 再 `tower report`

### 检测方式

- dashboard 每次 build 时 HEAD check 所有 commit_url
- 失败 → 在 build log warn，dashboard 标记该 phase 为 "unverifiable"

---

## R8. 私有项目意外公开

### 风险描述

我有个未发布项目 `secret-saas`，我误以为它还在 `local-xxx` 路径下，把它加进 `projects.yml` 并 push 到公开控制塔。

### 触发条件

- 写 `tower register-project` 时没注意 scope
- 复制粘贴其他项目配置时漏改

### 影响

- 公开了未发布项目的存在 + repo URL

### 缓解方案

- **`register-project` 时强制确认**：
  ```
  ⚠ Warning: this project will be PUBLIC if you push to a public control-tower.
  Confirm? [y/N]
  ```
- **CI 校验 `repo` 是 public**（HEAD request + 期望 200）
- **ACT-6 接入 checklist 必填**："确认 repo 是 public"
- **任何 `private repo` 都会在 build 时被红牌警告**

### 检测方式

- CI 警告 "private repo in public control tower"

---

## R9. 部署站点挂掉

### 风险描述

Cloudflare Pages 罢工 / DNS 挂 / 我的子域名过期。

### 触发条件

- 第三方故障
- 账户欠费

### 影响

- 公开 dashboard 不可访问
- 不会影响 event 写入（因为 event 写 Git，不写 dashboard）

### 缓解方案

- **UptimeRobot 监控 + Telegram 报警**
- **fallback**：在 README 写"如果 dashboard 挂了，看 `registry/projects.yml` 和 `events/` 也是真相"
- **不依赖单一 CDN**：MVP 阶段可以同时部署到 Cloudflare Pages + GitHub Pages

### 检测方式

- UptimeRobot 5 分钟一次探活
- 失败 → Telegram bot 通知

---

## R10. 事件数量爆炸

### 风险描述

1 个项目跑 1 年，每天 5 个 phase event → 1825 个 JSON。`build_index.py` 越跑越慢。

### 触发条件

- 长期使用 + 高频 phase
- agent 错误地"每个小步骤"都报 phase

### 影响

- dashboard build 时间超过 5 分钟
- 仓库 size 增长

### 缓解方案

- **agent 模板明确**：phase 是"工作单元"，不是"commit"
- **每事件压缩**：`build_index.py` 期间 streaming 写入
- **dashboard 懒加载**：只渲染最近 100 个 event
- **归档旧 event**：`events/2025/` 这种老目录可以 git subtree split 到 archive 仓库

### 检测方式

- CI build duration > 5 分钟 → 报警
- 仓库 size > 100MB → 报警

---

## R11. 多个 agent 改名后指向混乱

### 风险描述

`local-hermes` 改名为 `notebook-primary`，但 event 里的 `agent_id` 仍是 `local-hermes`，dashboard 时间线无法关联。

### 缓解方案

- **`agent_id` 不可变**（已在 [DATA_MODEL.md](DATA_MODEL.md) 写明）
- 改名 = 新注册一条 + 写 handoff event
- 旧 id 在 `agents.yml` 里保留但 `status: DEPRECATED`

---

## R12. 引入"看起来需要"的复杂度

### 风险描述

写着写着觉得"这里要加数据库"或"加个 API"。

### 触发条件

- 某个新功能没法用纯静态实现
- 想做实时通知

### 缓解方案

- **强约束**：任何"看起来需要后端"的需求，先在 [PROJECT_VISION.md §不做什么](PROJECT_VISION.md) 那里投票
- **默认拒绝**：MVP 阶段只允许"再加一个 event type"
- **如有例外**：写一篇 ADR（Architecture Decision Record）放进 `docs/adr/`

---

## 风险总表

| ID | 风险 | 严重度 | MVP 是否解决 | 缓解方案 |
| --- | --- | --- | --- | --- |
| R1 | 多机 push 冲突 | 中 | ✅ 自动 rebase | 脚本 |
| R2 | 重复注册 | 中 | ✅ grep 检测 | 脚本 |
| R3 | schema 不一致 | 高 | ✅ Pydantic enum | 脚本 |
| R4 | 隐私泄露 | **极高** | ✅ 强校验 | CI + 文档 |
| R5 | 失败隐藏 | 中 | ❌（已知） | MVP 之后再说 |
| R6 | 手动改 generated | 中 | ✅ .gitignore | 文档 |
| R7 | commit 链接失效 | 低 | ⚠️ 部分 | HEAD check |
| R8 | 私有项目公开 | **极高** | ✅ CI 校验 | 强制 confirm |
| R9 | 部署挂 | 低 | ⚠️ 监控 | UptimeRobot |
| R10 | event 数量爆炸 | 低 | ❌（已知） | ACT-7+ |
| R11 | agent 改名 | 低 | ✅ 不可变 | 文档 |
| R12 | 引入复杂度 | 中 | ✅ ADR 流程 | 治理 |
