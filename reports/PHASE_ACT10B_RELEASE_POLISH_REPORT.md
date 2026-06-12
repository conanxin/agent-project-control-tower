# PHASE ACT-10B — v0.1.0 Release Polish & Demo Assets Report

- **Phase ID**: ACT-10B
- **Phase name**: v0.1.0 Release Polish and Demo Assets
- **Date**: 2026-06-12
- **Owner**: local-hermes
- **Baseline commit**: `f4457a1` (ACT-12)
- **Result**: ✅ COMPLETE

---

## 1. Executive summary

ACT-10B 是纯 polish 阶段。v0.1.0 已 release，但 GitHub 侧没有视觉材料。本阶段产出：

1. **6 张 v0.1.0 screenshot**——Playwright + Chromium 1.5× DPI 实时截自 <https://control-tower.conanxin.com/>
2. **README visual section**——Screenshots 区嵌入 5 张图
3. **Release notes 更新**——同步 22→24 events、加 BookTrans Desk S13 PARTIAL note、加 ACT-11+12 public-data update workflow 说明
4. **GitHub Release v0.1.0**——notes 同步、所有 6 张 screenshot upload 为 release asset
5. **MVP_PLAN / status line**——同步到 ACT-10B ✅

**没有改任何控制塔数据 / 功能 / 边界**：3 projects / 2 agents / 24 events、data/ 仍 gitignored、generated/ 仍 gitignored、artifacts/ 仍 gitignored、automation level 不变、public-data 未被错误修改。

---

## 2. Why ACT-10B is polish, not feature work

ACT-10B 不接项目、不改 UI、不动数据。目的只有一个：让 v0.1.0 在 GitHub 上"看起来完成"。

* README 顶部没有任何视觉线索（纯链接 + 状态文字）
* Release notes 是 ACT-10 当时写的，22 events + 缺 workflow 说明
* 没有 screenshot 让人一眼看出 dashboard 长什么样
* 没有 release asset，README 图片无法直接加载

修完这几件事后，外部访客（agents / humans）第一次打开 repo 就能在 30 秒内看出"这是个 dashboard、它在线、长这样"。

---

## 3. Screenshot generation

| Property | Value |
|---|---|
| Tool | Playwright 1.58 + Chromium (already installed) |
| DPI | 1.5× |
| Viewports | 1440×900 desktop, 390×844 mobile |
| Wait strategy | `networkidle` → fallback `domcontentloaded` → 1.5s settle |
| Capture mode | full_page (saves entire scrollable page) |
| Script location | `/tmp/capture_v010_screenshots.py` (one-shot, not committed) |
| Time to capture all 6 | ~25 seconds |

### Files captured

| File | URL | Viewport | Dimensions | Size |
|---|---|---|---|---|
| `dashboard-home.png` | `/` | 1440×900 | 2160×3657 | 789 KB |
| `dashboard-home-mobile.png` | `/` | 390×844 | 585×6729 | 951 KB |
| `dashboard-timeline.png` | `/timeline/` | 1440×900 | 2160×3867 | 1020 KB |
| `project-agent-control-tower.png` | `/projects/agent-project-control-tower/` | 1440×900 | 2160×6039 | 1148 KB |
| `project-booktrans-desk.png` | `/projects/booktrans-desk/` | 1440×900 | 2160×1958 | 309 KB |
| `agent-cloud-openclaw.png` | `/agents/cloud-openclaw/` | 1440×900 | 2160×1692 | 258 KB |

All 6 written to `docs/media/v0.1.0/` and tracked in git. Total commit footprint: ~4.5 MB.

> Vision analysis not available on current model, so I verified screenshots by file metadata (PNG header width/height, byte size) — all real PNGs, all plausible dimensions, no zero-byte files.

---

## 4. README updates

Added a new top-level section `## 📸 Screenshots (v0.1.0)` between "Current live agents" and "这个项目是什么". Includes 5 embedded images (home / timeline / booktrans-desk / cloud-openclaw / mobile) + 2 callouts:

- "All assets in `docs/media/v0.1.0/` are tracked in git (small PNGs). Source: <https://control-tower.conanxin.com/>. Capture method and refresh instructions: `docs/media/README.md`."
- "⚠️ The dashboard renders a **reviewed public snapshot** of `public-data/`. The local `data/` event store is private and never published. BookTrans Desk shows `PARTIAL/amber` because the Windows desktop click-through remains `BLOCKED_MANUAL` (real-machine QA pending)."

Also updated the top status line:

- 状态: ACT-11 → ACT-10B
- public-data events: 22 → 24
- 新增 `📸 v0.1.0 screenshots` 行（指向 `docs/media/v0.1.0/`）
- 下一步: ACT-10B/12 → ACT-12B/13
- 日常更新 public-data 注明 "ACT-12 已真实验证"

---

## 5. Release notes updates

`docs/release/RELEASE_NOTES_v0.1.0.md` 改动：

| Section | Before | After |
|---|---|---|
| Current public-data status | "3 projects / 2 agents / 22 events / 0 redaction FAILs" | "3 projects / 2 agents / 24 events (cap 50 per project)" + 项目/agent 名称列表 |
| (new) BookTrans Desk status note | (absent) | S13 / 16f38b6 / PARTIAL/amber / repo 正确性说明 |
| (new) Public-data update workflow | (absent) | 7 步 ACT-11+12 流程 + ACT-12 plan_file leak fix 说明 |
| (new) Screenshots & demo assets | (absent) | 6 PNGs + capture method + demo-flow.gif deferred |
| Recommended next phase | "ACT-10B + ACT-11" | "ACT-12B + ACT-13" |

---

## 6. GitHub release polish

`gh release v0.1.0` 是 ACT-10 创建的（2026-06-12T06:08:24Z）。ACT-10B 改动：

```bash
gh release edit v0.1.0 --notes-file docs/release/RELEASE_NOTES_v0.1.0.md
gh release upload v0.1.0 \
  docs/media/v0.1.0/dashboard-home.png \
  docs/media/v0.1.0/dashboard-home-mobile.png \
  docs/media/v0.1.0/dashboard-timeline.png \
  docs/media/v0.1.0/project-agent-control-tower.png \
  docs/media/v0.1.0/project-booktrans-desk.png \
  docs/media/v0.1.0/agent-cloud-openclaw.png \
  --clobber
```

Both succeeded. Verified via `gh release view v0.1.0 --json assets` — all 6 assets present, sizes match local files.

URL: <https://github.com/conanxin/agent-project-control-tower/releases/tag/v0.1.0>

---

## 7. Public boundary (unchanged)

| Path | Status | Notes |
|---|---|---|
| `data/` | gitignored, never committed | ✅ unchanged |
| `generated/` | gitignored, regenerated | ✅ unchanged |
| `artifacts/` | gitignored, review-only | ✅ unchanged |
| `apps/dashboard/dist/` | gitignored | ✅ unchanged |
| `apps/dashboard/node_modules/` | gitignored | ✅ unchanged |
| `public-data/` | only public data source | ✅ unchanged (3/2/24, same as ACT-12) |
| `docs/media/v0.1.0/*.png` | **new, tracked in git** | intentional release assets |

---

## 8. Validation results

| Gate | Result |
|---|---|
| `make publish-preflight` | PASS (3/2/24, FAIL=0) |
| `make public-update-preflight` | PASS (3 projects, booktrans OK, HP-33=0) |
| `make public-update-test` | PASS (12/12) |
| `make command-test` | PASS (8/8) |
| `make candidate` | PASS (3/2/24, FAIL=0) |
| `make candidate-fixture` | PASS (2/3/3, FAIL=0) |
| `make candidate-test` | PASS |
| `make export-plan-test` | PASS |
| `cd apps/dashboard && npm run build` | PASS (7 pages, 1.36s) |

Sensitive scan (`grep -RInE "token=|api_key|Authorization:|Bearer |password=|secret=|/home/[^ ]+|/Users/[^ ]+|[0-9]+.[0-9]+.[0-9]+.[0-9]+|.env" README.md docs templates reports scripts tests config public-data .github CHANGELOG.md VERSION`) 命中：

- All hits are instructional (README mentions of what the scanner checks for, "0 hits" tables, `local/<id>` placeholders, ADR dates)
- Zero hits in `public-data/` (the ACT-12 fix held — `plan_file` still repo-relative)
- Zero real secrets, IPs, tokens, or home paths

---

## 9. Online verification (after deploy)

| Target | Expected | Status |
|---|---|---|
| `https://control-tower.conanxin.com/` | 3 projects, 24 events | (deploys on push — see below) |
| `https://github.com/.../README.md` | screenshot section visible | ✅ committed |
| `https://github.com/.../docs/release/RELEASE_NOTES_v0.1.0.md` | updated content | ✅ committed |
| `https://github.com/.../tree/main/docs/media/v0.1.0` | 6 PNGs + README | ✅ committed |
| `https://github.com/.../releases/tag/v0.1.0` | updated notes + 6 assets | ✅ uploaded |

> Cloudflare Pages auto-deploys on push. The dashboard itself didn't change content (no new events, no new public-data) — only the GitHub-side release materials changed. So no public-data side verification needed beyond confirming `control-tower.conanxin.com/` still serves the same 3/2/24 state.

---

## 10. Files changed in ACT-10B

New (tracked):
- `docs/media/README.md`
- `docs/media/v0.1.0/dashboard-home.png`
- `docs/media/v0.1.0/dashboard-home-mobile.png`
- `docs/media/v0.1.0/dashboard-timeline.png`
- `docs/media/v0.1.0/project-agent-control-tower.png`
- `docs/media/v0.1.0/project-booktrans-desk.png`
- `docs/media/v0.1.0/agent-cloud-openclaw.png`
- `reports/PHASE_ACT10B_RELEASE_POLISH_REPORT.md`

Modified (tracked):
- `README.md` — added Screenshots section + top status line
- `docs/release/RELEASE_NOTES_v0.1.0.md` — added 4 sections
- `docs/MVP_PLAN.md` — current-stage + next-phase updated

Not committed:
- `data/events/...ACT-10B.json` (gitignored, see §11)
- `/tmp/capture_v010_screenshots.py` (one-shot, outside repo)

---

## 11. ACT-10B data event (in data/, not committed)

Reported via `tower.py report-phase` after the polish commit, so the public record of "ACT-10B happened" arrives in a future ACT-12B/13 export. This keeps ACT-10B strictly a polish phase with zero new public events.

(Recorded locally, gitignored. The actual commit hash and summary live in this report and the MVP_PLAN timeline.)

---

## 12. Recommendation for next phase

| Next | Pros | Cons |
|---|---|---|
| **ACT-12B** (second recurring update trial) | Validates ACT-11/12 workflow over multi-day cadence | Short-term low marginal value |
| **ACT-13** (adoption packaging) | Lower friction for new agents / humans cloning the repo | Slightly more design work |

**推荐 ACT-12B 先于 ACT-13**。理由：

- ACT-12B 是低风险验证——每多日更新自然就验证一次 ACT-11/12 流程，跑一次正式 trial 把"已经发生的日常更新"攒下来
- ACT-13 涉及"为新用户重写 onboarding"的设计判断，不适合连着做
- 真实节奏：下一个自然的多阶段项目（BookTrans Desk S14? Artvee next milestone? control tower 自己的 ACT-13 起步？）会自然产生下一波 data events，那时顺手把 ACT-12B 跑完最经济
