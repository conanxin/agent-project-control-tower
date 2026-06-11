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

## 11. 公开发布后的运营

- **不要在 issue 里贴真实 IP / 路径**——回 issue 时再脱敏
- **issue 模板里加一条**："提交前请确认没有粘贴私人信息"
- **监控**：GitHub 的 "secret scanning" 会自动检测，如果推送了 token 会发邮件——收到后立即 rotate
- **每月一次**：跑 `git log --all -p | grep -E '(api[_-]?key|password|token)'` 审计

## 12. 不开源的备选

如果某天决定**不公开**控制塔仓库：

- 仍可作为个人"内部工具"长期使用
- 跳过 ACT-5（不上 Cloudflare Pages）
- 跳过 ACT-6 接入真实项目时的脱敏 checklist（但仍建议做）

> 但**建议保持开源**——理由：控制塔本身是 meta-tool，没有真正的"商业价值"需要保护；公开反而能让别人 fork、自用、提 issue。
