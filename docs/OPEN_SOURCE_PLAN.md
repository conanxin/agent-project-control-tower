# Open Source Plan

> 让这个控制塔可以"安全地公开"——README、license、命名、隐私脱敏，全部提前定好。

## 1. 仓库命名建议

主仓库名候选（按偏好顺序）：

| 候选 | 理由 |
| --- | --- |
| `agent-project-control-tower` | 直白、与 docs 对齐 |
| `apct` | 短，难搜 |
| `agent-tower` | 短，但太泛 |
| `open-tower` | 暗示多项目，但"open"会与 OpenClaw 混淆 |

**推荐**：`agent-project-control-tower`（你已经在用这个名字了，保留）。

`examples/` 里的项目名都使用占位符：`local-book-tool`, `cloud-art-site`——这些不是真实项目名，但足够有"具体感"。

## 2. License

**推荐：MIT**。

理由：

- 控制塔本身不写代码（运行时只有 ~500 行 Python），版权风险低
- MIT 让别人可以随便 fork、自用、商用
- 配套 Apache-2.0 的可选性：如果有第三方贡献，加 `LICENSE` + `CONTRIBUTING.md` 说明

候选 LICENSE 文本（标准）：

```
MIT License

Copyright (c) 2026 Xin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

ACT-2 阶段正式提交 LICENSE 文件。

## 3. README 结构

> README 是陌生人第一眼看到的东西。结构 = "5 句话让他懂 + 1 段代码让他能用 + 1 张图让他信"。

### 推荐章节

1. **标题 + 一句话定位**（<= 80 字符）
2. **Demo 图 / GIF**（dashboard 截图，ACT-3 后加）
3. **Why**（3 条 bullet，解决什么问题）
4. **How it works**（ASCII 数据流图）
5. **Quick start**（5 行内能用）
6. **Concepts**（registry / events / generated 三件套）
7. **Commands**（CLI 速查）
8. **Architecture**（链向 `docs/ARCHITECTURE.md`）
9. **Roadmap**（链向 `docs/MVP_PLAN.md`）
10. **Contributing**（怎么做 PR，TODO）
11. **License**

### 当前 README 状态

ACT-0 的 README 已经覆盖了 1 / 3 / 4 / 5 / 6 / 8 / 9。ACT-3 后补 Demo 图，ACT-2 后补 Commands。

## 4. 隐私脱敏（最重要）

控制塔一旦 push 到公开 GitHub，**任何写进 event / registry 的内容都自动公开**。

### 4.1 强制脱敏规则

CI 在 build 前跑 `scripts/lib/redaction.py`，**任何**匹配下表的内容都直接拒绝构建：

| 类别 | 模式 | 例子（禁止） |
| --- | --- | --- |
| 内网 IP | `\b(?:\d{1,3}\.){3}\d{1,3}\b` | `192.168.1.1`, `10.0.0.5` |
| 公网 IP | 同上（特例白名单：loopback） | `8.8.8.8` ❌ |
| Linux home | `/home/[^/]+/` | `/home/xin/` |
| macOS home | `/Users/[^/]+/` | `/Users/xin/` |
| Windows home | `C:\\Users\\[^\\]+\\` | `C:\Users\xin\` |
| SSH key block | `-----BEGIN .* PRIVATE KEY-----` | — |
| API tokens | `(?i)(api[_-]?key\|token\|password).{0,3}[:=]\s*['"]?[A-Za-z0-9_\-]{16,}` | `api_key=sk-...` |
| 邮箱（建议） | `\S+@\S+\.\S+` | `xin@gmail.com`（可白名单：项目 issue 链接里的） |
| 云厂商账号 ID | `\b\d{12}\b` | AWS account ID |

### 4.2 正确写法 vs 错误写法

| 场景 | ❌ 错 | ✅ 对 |
| --- | --- | --- |
| 写机器名 | `machine: xin-thinkpad-t480` | `machine: local` |
| 写 commit 信息 | `summary: "fixed on 192.168.1.42:8080"` | `summary: "fixed dev server crash"` |
| 写路径 | `commit_url: file:///home/xin/projects/x/src/main.py` | `commit_url: https://github.com/xin/x/commit/abc123` |
| 写 token | `summary: "GH_TOKEN=ghp_xxx triggered CI"` | `summary: "CI triggered after secret rotate"` |
| 写邮箱 | `operator: xin@gmail.com` | `operator: xin` |
| 写 IP | `artifacts.endpoint: "http://10.0.0.5:8080"` | `artifacts.endpoint: "internal"` |

### 4.3 真实项目接入前的 checklist

ACT-6 接入任何真实项目前，必须跑：

```bash
python scripts/redaction_check.py --strict
```

退出码非零 = 不能 push 到公开仓库。

如果发现必须保留私密信息但又想公开 dashboard：

- **方案 A**：脱敏 + 公开（绝大多数情况）
- **方案 B**：第二份私有控制塔（见 [DEPLOYMENT_PLAN.md §5](DEPLOYMENT_PLAN.md)）
- **方案 C**：原项目用 private repo，控制塔用 public（控制塔只存 commit SHA + status，不存代码）

### 4.4 ACT-4A 公开数据出口：public-data/ 流程

`public-data/` 是**唯一**可发布的数据源——所有写入都强制经过 redaction：

```bash
# 默认：从 examples/ 导出（占位数据，无任何真实信息）
python scripts/export_public_data.py

# 或：从本地 data/ 导出（先 redaction 检查）
python scripts/export_public_data.py --source data

# dry-run：扫描但不写文件
python scripts/export_public_data.py --dry-run
```

工具行为：

- 读源 `registry/*.yml` 的 `id / display_name / operator / machine / repo / location / description` 等字段
- 读源 `events/*.json` 的 `summary / phase_name / next / source_repo / release_url / reason / failure_reason` 等字段
- 每个字段过 `scripts/lib/redaction.py` 的 `check_text()`
- **FAIL**（明显 secret / 真实 home 路径 / 真 token）：直接拒绝写入，返回 exit 1
- **WARN**（疑似本地路径 / IP）：写入但打印警告
- **PASS**：静默通过

写入后产出 `public-data/MANIFEST.json` 记录来源 + 文件清单——CI 验证时一眼能看出用了哪份数据。

**关键约束**：

- `data/` 仍 gitignored——本地真实数据**不**进入仓库
- `public-data/` 提交进仓库——公开 dashboard 直接读它
- `generated/` 仍由 CI 重建——dashboard dist 永远从 `public-data/` 派生
- 真实项目接入时，先在 `data/` 调试，确认 redaction 通过，**手动**执行 `export_public_data.py --source data` 把脱敏子集写入 `public-data/`，再 commit

**绝不** 出现：

- `data/` 文件名出现在 `public-data/`
- `data/` 的 event 摘要原样进 `public-data/`
- 任何 `data/` 的私密路径 / IP / token 出现在 `public-data/`（被 redaction 拦截）

## 5. 示例数据必须脱敏

ACT-1 的 `examples/` 目录：

- 项目名用 `local-book-tool` / `cloud-art-site` —— **不是**真实项目名
- agent id 用 `local-hermes` / `local-codex` / `cloud-openclaw` —— **不是**真实凭据
- commit SHA 用明显假的（如 `abc1234`、`deadbeef`）
- summary 字符串避免任何 `192.168.x.x`、`/home/xin/` 等模式
- repo URL 用 `https://github.com/xin/...` —— 这是占位符，**真实接入时替换**

## 6. CONTRIBUTING.md（ACT-7+ 写）

暂未写。ACT-7 之后如果有人提 issue 再补，结构：

- "How to file a bug"
- "How to add a new event type"（修改 schema → 加 migration → 写测试）
- "How to add a new dashboard view"
- "Code of conduct"（简化版）

## 7. CODE_OF_CONDUCT.md

暂未写。ACT-7 之后用 Contributor Covenant v2.1 标准模板。

## 8. SECURITY.md

ACT-1 之后写：

- "If you find a privacy leak in examples/, please open a private issue"
- "If you find a security bug in tower CLI, email security@xin.dev"
- "We do NOT accept PRs that add network calls to tower CLI"

## 9. 公开 vs 私有的边界

| 公开（GitHub public） | 私有（GitHub private） |
| --- | --- |
| 控制塔仓库 | 第二份控制塔（商业项目用） |
| `examples/` 全部 | 真实项目的 `events/` |
| `docs/` 全部 | 真实项目的 `registry/` |
| `scripts/` 全部 | （脚本本身可公开） |
| `site/dist/` 部署到 Cloudflare Pages | 部署到 Cloudflare Access 后面的 Pages |

## 10. 公开发布的"那一刻"

ACT-5 阶段把仓库从 private 转 public 的 checklist：

- [ ] `LICENSE` 文件已存在
- [ ] `SECURITY.md` 存在
- [ ] `CONTRIBUTING.md` 存在（哪怕只是占位）
- [ ] 跑 `python scripts/redaction_check.py --strict` 全绿
- [ ] 所有 commit 的 author 邮箱是公开邮箱（不是 `xin@localhost`）
- [ ] README 的 Demo 图是干净的（不含真实 IP / 路径）
- [ ] `.github/workflows/` 不打印 secrets
- [ ] 一次 `git log --all -p | grep -E '(192\.168|/home/xin|sk-)'` 必须为空

## 11. ACT-6 真实项目脱敏导出策略（2026-06-11）

ACT-6 起，公开数据从 `examples/` 示范数据升级为 `data/` 脱敏切片。**`public-data/` ≠ `data/`**：
`public-data/` 是人工确认后的"公开快照"，由 `scripts/export_public_data.py` 从 `data/` 脱敏生成。

### 11.1 公开 vs 私有数据源（边界重申）

| 公开（`public-data/`） | 私有（`data/`） |
| --- | --- |
| `--project-id` 过滤后的项目 registry | 所有项目的完整 registry |
| `--agent-id` 过滤后的 agent registry | 所有 agent |
| `--max-events N` 截断后的 event 列表 | 所有 event（含敏感内容） |
| `repo-prefix` 改写后的真实 GitHub 路径 | `local/<project-id>` 占位符 |
| 公开 commit hash 列表 | 完整 source_commit / 内部路径 |

### 11.2 真实项目脱敏导出流程

1. **人类判断**：该项目/agent/event 是否适合公开？默认**否**。
2. **白名单导出**：
   ```bash
   python scripts/export_public_data.py \
     --source data \
     --output public-data \
     --project-id <project1> --project-id <project2> \
     --agent-id <agent1> --agent-id <agent2> \
     --max-events 20 \
     --repo-prefix conanxin \
     --replace
   ```
3. **人工 review 输出**：检查 `public-data/events/*.json` 和 `public-data/registry/*.yml`，确认无 home 路径 / token / IP。
4. **redaction 校验**：`make publish-preflight` 内置 `export_public_data.py` redaction summary（FAIL=0, WARN=0）。
5. **commit + push**：CF Pages 自动 re-deploy，custom domain 30s 内刷新。

### 11.3 `public-data/` 是"人工确认后的公开快照"

- `public-data/` **不能**直接由 `tower.py` 写，只能由 `export_public_data.py` 从 `data/` 生成
- 导出有 5 个**白名单参数**：`--project-id` / `--agent-id` / `--max-events` / `--repo-prefix` / `--replace`
- `data/` 仍 gitignored；`public-data/` 在 git 里
- 任何 commit `public-data/` 之前必须 review diff（**不能** `git add .`）

### 11.3.1 ACT-7 明确化"人工审核 public-data"的职责边界（2026-06-12）

控制塔采用 **agent ↔ 人工双门**模型。`data/` 那一侧由 agent 自治，`public-data/` 那一侧由人工（或被显式授权的"导出 agent"）守门。ACT-7 把这条边界显式地写进文档，避免后续 act 模糊化它。

**agent 可以做的（默认在 `data/` 上）**：

- `git clone` 控制塔仓库
- `python scripts/tower.py validate` / `build`（零副作用或仅写 `generated/`）
- `register-agent` / `register-project`（一次性，幂等）
- `report-phase` / `report-failure` / `report-review` / `report-handoff` / `report-release`（写 `data/events/`，gitignored）
- 在自己的机器上 `git pull --ff-only`

**agent 不应该默认做的（除非被显式授权为"导出 agent"）**：

- `python scripts/export_public_data.py`（写 `public-data/`，是上公开的闸门）
- `git add public-data/` 并 `git commit`（第二道闸门）
- `git push` 到 `main`（第三道闸门）

**人工（或导出 agent）必须 review 的清单**（详见 `templates/checklists/public-data-review-checklist.md`）：

1. `public-data/registry/projects.yml` 中每个 `repo` 指向**真实代码仓库**，不是 homepage 子目录（**ACT-6C 教训**）
2. `public-data/events/` 中每个 event 的 `project_id` 与该项目历史相符（没有 `booktrans-desk` event 错挂 `source_repo=conanxin-homepage`）
3. `public-data/MANIFEST.json` 中 `event_count` / `project_filter` / `max_events_per_project` 符合预期
4. 文档敏感扫描 CLEAN（详见 `templates/checklists/redaction-checklist.md`）
5. 上线后再做 `templates/checklists/online-verification-checklist.md`

**为什么是双门而不是单门**：

- 单门 = agent 既写事件又导出，公共数据是 agent 自动行为的副产物 → 错归类（ACT-6C）、乐观虚标（ACT-5B 之前）、误提交私密路径（ACT-4A）都会无声发生。
- 双门 = agent 看不到 `public-data/`，人类（或"导出 agent"）只为正确性负责 → 错归类会被人类 catch（`booktrans-desk.repo` 一眼看出不对），redaction 也会被人类二审。
- 未来如果某个 act 引入"自动化 export"，它必须以一个独立的、可被关闭的 agent 身份（`local-exporter` / `cloud-exporter` 等）注册，并在 `docs/PUBLIC_DATA_EXPORT_PLAYBOOK.md` 中显式记录它的边界。

**禁止模式**：

- ❌ agent 在自己机器上跑 `export_public_data.py` 后**直接** `git push`（绕过人工）
- ❌ agent 用 `git add .` 一次性 stage（容易把 `data/` 错误带入）
- ❌ 任何人（agent 或人）`--force` push 到 `main`

### 11.4 ACT-6B 多项目公开导出策略

ACT-6B 起，`export_public_data.py` 支持一次导出多个真实项目的并集：

```bash
python scripts/export_public_data.py \
  --source data \
  --output public-data \
  --project-id agent-project-control-tower \
  --project-id artvee-gallery \
  --agent-id local-hermes \
  --max-events 20 \
  --repo-prefix conanxin \
  --replace
```

行为：

- `--project-id` 可重复；最终导出所有指定 project 的 registry + 关联 events
- `--agent-id` 可重复；只导出指定 agent（如省略，则导出 events 中出现的所有 agent）
- `--replace` 会先清空 `public-data/{registry,events}`，再写入本次导出结果
- 默认（无 `--replace`）为 merge 模式：保留已有文件，只覆盖/新增本次导出的文件

多项目并集导出时，`public-data/` 不会保留未在本次 filter 中的 project/agent/event——这是预期行为，确保公开数据是**人工确认后的精确快照**。

### 11.5 一个真实项目进入 public-data 前的审核清单

在把任何新真实项目加入 `public-data/` 之前，必须完成以下检查：

- [ ] 该项目在 `data/` 中已有 registry 和至少一个 event
- [ ] 已review 该项目的所有 event `summary` / `phase_name` / `next` / `source_repo`，确认无本地路径 / IP / token
- [ ] 已确认 `source_repo` 使用 `local/<project-id>` 占位符或真实公开 GitHub 路径
- [ ] 已运行 `python scripts/export_public_data.py --source data --output public-data --project-id <id> --dry-run`，redaction 无 FAIL
- [ ] 已检查 `--max-events` 截断后仍保留最近关键阶段
- [ ] 已检查 `public-data/registry/projects.yml` 的 `repo` 字段被正确改写为 `conanxin/<project-id>`
- [ ] 已运行 `make publish-preflight` 全链路通过
- [ ] 已人工 `git diff public-data/` 并显式 `git add`（不用 `git add .`）
- [ ] 未把 `data/`、`generated/`、`apps/dashboard/dist/` 加入 commit

### 11.6 ACT-6C 当前 public-data 统计

```json
{
  "source": "data",
  "event_count": 14,
  "project_filter": [
    "agent-project-control-tower",
    "artvee-gallery",
    "booktrans-desk"
  ],
  "agent_filter": ["local-hermes"],
  "max_events_per_project": 20,
  "repo_prefix": "conanxin"
}
```

14 个 event = agent-project-control-tower 9 个（PROJECT_REGISTERED + ACT-0/1/2/3A/5/5B/6/6B）+ artvee-gallery 3 个（PROJECT_REGISTERED + P2 + P3B）+ booktrans-desk 1 个（S13；ACT-6C hotfix 后 HP-33 已剔除，repo 改为 conanxin/booktrans-desk）。注：原始 ACT-6C 计数包含 PROJECT_REG + HP-33 共 2 个，hotfix 后为 1 个 S13。

### 11.7 3+ 项目公开导出的审核清单

当 `public-data/` 中已有 2 个或以上真实项目时，新增第 3 个及后续项目需额外关注：

- [ ] 确认新项目的 `category` 与已有项目不重复（或重复是预期行为，如多个 `reading-tool`）
- [ ] 确认新项目的 `repo` 字段不与已有项目冲突
- [ ] 确认 `--max-events` 截断不会意外删除其他项目的早期关键事件
- [ ] 确认 `--replace` 模式下，旧项目的 event 文件不会被意外删除
- [ ] 确认 `public-data/MANIFEST.json` 的 `project_filter` 包含所有预期项目
- [ ] 确认 dashboard 首页能正确显示 3+ 个项目卡片（无布局溢出）
- [ ] 确认 timeline 页能正确显示所有项目的 event（无时间线断裂）
- [ ] 确认每个项目详情页的 URL 可访问（`curl -L` HTTP 200）

### 11.8 多项目并集导出的 Makefile 改进建议

当前 `make public-data-real` 的 `PUBLIC_DATA_PROJECT` 变量只支持单 project。建议 ACT-7 时改为支持多 project：

```makefile
# 当前（单 project）
PUBLIC_DATA_PROJECT ?= agent-project-control-tower

# 建议（多 project，空格分隔）
PUBLIC_DATA_PROJECTS ?= agent-project-control-tower artvee-gallery booktrans-desk
```

或保持现状，继续使用 `export_public_data.py` 的直接调用（已支持 `--project-id` 重复参数）。

## 12. 公开发布后的运营

- **不要在 issue 里贴真实 IP / 路径**——回 issue 时再脱敏
- **issue 模板里加一条**："提交前请确认没有粘贴私人信息"
- **监控**：GitHub 的 "secret scanning" 会自动检测，如果推送了 token 会发邮件——收到后立即 rotate
- **每月一次**：跑 `git log --all -p | grep -E '(api[_-]?key|password|token)'` 审计

## 13. 不开源的备选

- 仍可作为个人"内部工具"长期使用
- 跳过 ACT-5（不上 Cloudflare Pages）
- 跳过 ACT-6 接入真实项目时的脱敏 checklist（但仍建议做）

> 但**建议保持开源**——理由：控制塔本身是 meta-tool，没有真正的"商业价值"需要保护；公开反而能让别人 fork、自用、提 issue。
