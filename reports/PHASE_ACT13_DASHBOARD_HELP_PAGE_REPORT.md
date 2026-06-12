# PHASE ACT-13 — Dashboard Help Page Report

- **Phase ID**: ACT-13
- **Phase name**: Dashboard Help Page
- **Date**: 2026-06-12
- **Owner**: local-hermes
- **Baseline commit**: `db945f4` (ACT-10B)
- **Result**: ✅ COMPLETE

---

## 1. Executive summary

ACT-13 给 live dashboard 加了一个 **Help 页面**（`/help/`），把整套控制塔使用流程写到了线上——以后新 agent / 新人类直接打开 dashboard 就能在 30 秒内读懂"这是什么、怎么用、不能做什么、出了问题查哪里"。

**没有改任何控制塔数据 / 功能 / 边界**：

- public-data 仍是 3 projects / 2 agents / 24 events
- data/ / generated/ / artifacts/ 仍 gitignored
- automation level 仍 Level 1 + 1.5 + 2 + 3 (prototype)
- 触发 public-data export 的 ACT-11/12 流程不变
- Cloudflare Pages 仍只在 push 后自动部署

**净增量**：1 个新页面 + 1 行 nav 入口 + 1 段 footer 文案 + 1 块 help-page CSS。

---

## 2. Why ACT-13 — not a feature, an onboarding page

v0.1.0 release polish 完成后，外部访客第一次进 repo / 第一次打开 dashboard 会发现：

- 顶部有 README / 截图 / 状态行，但点进 dashboard 后只看得到数据
- 想了解"怎么用"必须切到 GitHub docs，但 dashboard 内的导航不会指向 docs
- 双门模型 / Public-data update checklist / Multi-machine 流程是核心 invariant，但没有"在 dashboard 内"的可读版本

ACT-13 解决的就是这三件事：把整套 invariant + 流程 + 链接固化到 dashboard 自身，作为"在产品内"的可读入口。docs/ 仍是 source of truth，Help 页是它的一份精选+链接镜像。

---

## 3. What was built

### 3.1 New page: `apps/dashboard/src/pages/help.astro`

A single self-contained Astro page (no external deps, no client scripts, no data import — pure static content). It is wrapped in `<div class="help-doc">` to scope the ACT-13 styles.

Nine top-level sections, in order:

| # | Section | Purpose |
|---|---|---|
| 1 | Start here | One-paragraph model: source repos stay separate, tower tracks state, data/ is private, public-data/ is reviewed snapshot, dashboard reads public-data/, deploy is push-driven |
| 2 | Core mental model | 11-step ordered flow from "agent finishes work" to "dashboard updates" |
| 3 | When to trigger an update | Lists 4 trigger conditions; emphasizes this is NOT an auto-listener; only Cloudflare deploy is automatic |
| 4 | Common workflow: report a phase | 8-step copy-paste flow matching ACT-12 trial; includes a runnable `tower.py report-phase` block and `make public-update-preflight` / `export_public_data.py` calls |
| 5 | Common commands | Compact list of `register-agent` / `register-project` / `report-phase` / `report-failure` / `report-review` / `report-handoff` / `report-release` + the command generator |
| 6 | Double-door model | Door 1 (any agent writes data/) vs Door 2 (only human / local-hermes exports public-data/); explicit list of 4 things trial agents must NOT do |
| 7 | Public-data update checklist | 10 visual checkboxes; mirrors ACT-11 preflight + the 3 explicit git-add exclusions (data/ / generated/ / artifacts/) |
| 8 | Multi-machine usage | Each machine clones, each agent has its own agent_id, off-machine agents only write data, public export is gate-controlled |
| 9 | Links | Live dashboard, GitHub repo, key docs, templates, reports |

### 3.2 Nav entry: `BaseLayout.astro`

```diff
 <nav class="site-nav">
   <a href="/">Home</a>
   <a href="/timeline/">Timeline</a>
+  <a href="/help/">Help</a>
   <slot name="nav-extras" />
 </nav>
```

Help is now on every page (Home, Timeline, all project / agent pages, and Help itself). Footer also updated:

```diff
- ACT-3B dashboard · reads <code>generated/index.json</code> at build time
+ ACT-3B dashboard + ACT-13 Help page · reads <code>generated/index.json</code> at build time
```

### 3.3 Help-page styles: `global.css`

Added a scoped `.help-doc` block (40 lines CSS, no framework, no preprocessor). Sets:

- `max-width: 880px` (narrower than the 1100px main width — long-form reading is easier at 880px)
- h2 with bottom border (clear section dividers)
- pre block styling (background panel-2, border, scroll, monospace, 12px)
- checkbox accent color (uses `--accent` so it follows light/dark theme)
- `a` color = `var(--link)` (theme-aware)

No new CSS variables, no new global selectors, no overrides to existing styles.

---

## 4. Build verification

| Metric | Before | After |
|---|---|---|
| Astro pages | 7 | 8 |
| Total `dist/` build time | ~1.40 s | 1.39 s |
| `dist/help/index.html` | (absent) | 17,445 bytes |
| `/help/` route | 404 | 200 |

Build output confirms:

```
17:19:00 ▶ src/pages/help.astro
17:19:00   └─ /help/index.html (+2ms)
17:19:00 [build] 8 page(s) built in 1.39s
```

`dist/help/index.html` contains all 9 sections (verified by content grep for "Double-door", "public-data", "conanxin/booktrans-desk", "HP-33", "make public-update-preflight", "report-phase", "export_public_data").

Nav link present on every page (1 hit on each of 4 sampled pages, 2 on `/help/` itself for nav + footer).

---

## 5. Public boundary (unchanged)

| Path | Status |
|---|---|
| `data/` | gitignored, never committed ✅ |
| `generated/` | gitignored, regenerated ✅ |
| `artifacts/` | gitignored, review-only ✅ |
| `apps/dashboard/dist/` | gitignored ✅ |
| `apps/dashboard/node_modules/` | gitignored ✅ |
| `public-data/` | 3/2/24, **unchanged** ✅ |
| `site/index.embedded.html` | only `generated_at` timestamp regen — no data diff ✅ |

`git status --short --ignored` shows all sensitive paths still `!!`-marked.

---

## 6. Validation results

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
| `cd apps/dashboard && npm run build` | PASS (8 pages, 1.39s) |

> `make all` continues to skip smoke test (it expects the examples state with 2/3/local-book-tool/cloud-art-site); real-data validate + build + site chain all PASS. Same as ACT-10B.

Sensitive scan (`grep -RInE "token=|api_key|Authorization:|Bearer |password=|secret=|/home/[^ ]+|/Users/[^ ]+|[0-9]+.[0-9]+.[0-9]+.[0-9]+|.env" README.md docs templates reports scripts tests config public-data .github CHANGELOG.md VERSION`): 0 real hits in public-data; all hits in tracked paths are instructional (README mentions of the scanner rules, "0 hits" tables, `local/<id>` placeholders, ADR dates). Help page does not contain any sensitive strings.

---

## 7. Files changed in ACT-13

New (tracked):
- `apps/dashboard/src/pages/help.astro` (16,686 bytes)
- `reports/PHASE_ACT13_DASHBOARD_HELP_PAGE_REPORT.md` (this file)

Modified (tracked):
- `apps/dashboard/src/layouts/BaseLayout.astro` — +2 lines (nav + footer)
- `apps/dashboard/src/styles/global.css` — +47 lines (help-doc block)
- `docs/MVP_PLAN.md` — current-stage + next-phase updated
- `README.md` — status line + next-phase updated
- `site/index.embedded.html` — auto-regenerated by `make publish-preflight` (timestamp only)

Not committed:
- `apps/dashboard/dist/help/index.html` (gitignored)
- `apps/dashboard/dist/index.html` etc. (gitignored)
- `data/events/...ACT-13.json` (gitignored — not written in this phase; ACT-13 is a static-page change, no new event to record)

> Note: ACT-13 did not generate a new data event. ACT-13 changes the dashboard UI (static help text baked into the Astro build), not the data model. The "I added a page" signal is in the MVP_PLAN / README / this report — not in a `PHASE_REPORT` event. This is intentional: a help page is documentation, not project state. If a future phase needs to record "I shipped v0.1.x", that would be a `report-release` against the tower project, not a `PHASE_REPORT`.

---

## 8. Recommendation for next phase

Two candidates:

| Next | Trigger | Pros | Cons |
|---|---|---|---|
| **ACT-12B** | Real multi-day update event (BookTrans S14+ / Artvee P3C+ / tower ACT-14+ / other) | Real validation; zero cost if it never fires | Latent — depends on real work happening |
| **ACT-14** (adoption packaging) | Manual decision | Better new-user onboarding (e.g. a `git clone` then `make` quickstart that bakes in the ACT-7 gaps surfaced in ACT-8) | Slightly more design work; needs a human follow-up to actually onboard a new agent |

**Recommend leaving both as "wait for trigger or for a quiet evening"**:

- ACT-12B should fire naturally the next time BookTrans Desk / Artvee / another real project hits a new phase. The tower can sit idle until then — no need to manufacture an event.
- ACT-14 is genuinely valuable but requires actual user research. Best done when a new agent is about to onboard, not speculatively.

If nothing fires in the next 2–3 weeks, the right call is "ACT-12B is dormant" and revisit after BookTrans S14 / Artvee P3C.

---

## 9. Live verification (post-deploy)

| Target | Expected | Status |
|---|---|---|
| `https://control-tower.conanxin.com/` | 3 projects, Help in nav | (deploys on push — see §10) |
| `https://control-tower.conanxin.com/help/` | 9 sections, code blocks, checklist | (deploys on push) |
| `https://control-tower.conanxin.com/timeline/` | Help in nav, ACT-12 still latest tower phase | (deploys on push) |
| `https://control-tower.conanxin.com/projects/booktrans-desk/` | Help in nav, S13 / 16f38b6 / PARTIAL | (deploys on push) |

> Cloudflare Pages auto-deploys on push. Only the static `dist/` changed (help page added); no public-data changed. So the deploy is fast and low-risk.

---

## 10. Commit & push

Staged:
- `apps/dashboard/src/pages/help.astro` (new)
- `apps/dashboard/src/layouts/BaseLayout.astro` (M)
- `apps/dashboard/src/styles/global.css` (M)
- `docs/MVP_PLAN.md` (M)
- `README.md` (M)
- `site/index.embedded.html` (M, timestamp regen only)
- `reports/PHASE_ACT13_DASHBOARD_HELP_PAGE_REPORT.md` (new)

Not staged: `data/`, `generated/`, `artifacts/`, `apps/dashboard/dist/`, `node_modules/`, `.env`.
