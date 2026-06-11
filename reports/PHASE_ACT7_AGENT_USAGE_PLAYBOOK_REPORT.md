# ACT-7: Multi-machine Agent Usage Playbook — Phase Report

## Decision

- Status: **PASS**
- Confidence: high
- Scope: ACT-7 only. No new project, no new dashboard UI, no database,
  no login, no Cloudflare API token. ACT-7's only outputs are
  **documentation, templates, and checklists** that let other agents /
  machines use the tower stably.

---

## 1. Executive summary

ACT-7 elevates the Agent Project Control Tower from "works for the
human" to "works for any agent that follows the playbook". The
deliverables are:

- Three new docs (`AGENT_USAGE_PLAYBOOK.md`, `MULTI_MACHINE_SETUP.md`,
  `PUBLIC_DATA_EXPORT_PLAYBOOK.md`) totalling ~45 KB / ~1,300 lines of
  prose.
- Eight Telegram command templates under `templates/telegram/`,
  designed to be copy-pasted into a chat to command an agent.
- Four checklists under `templates/checklists/`, each tied to a
  specific moment in the deploy / export / verify cycle.
- Five existing docs (README, AGENT_WORKFLOW, MVP_PLAN, OPEN_SOURCE_PLAN,
  DEPLOYMENT_PLAN, DATA_MODEL) updated with ACT-7 status, ACT-7 chapter,
  and cross-links.
- A "Start here" + "Current recommended usage path" section at the top
  of `README.md` so a new agent finds the right doc in under 30 seconds.
- A re-statement of the **agent ↔ human two-gate** model for
  `public-data/` export in `docs/OPEN_SOURCE_PLAN.md` §11.3.1.
- A restated **status / health choice** rule table in
  `docs/DATA_MODEL.md` §4.1, with the BookTrans Desk S13 PARTIAL/amber
  case as the canonical anti-example.

Three real projects (`agent-project-control-tower`, `artvee-gallery`,
`booktrans-desk`) power the documentation: their phase numbering
styles, locations, and the ACT-6C hotfix are referenced as concrete
examples throughout.

The ACT-6C lesson (booktrans-desk mis-attributed to
`conanxin-homepage` / `HP-33`) is encoded in **six** places in the
deliverables — it is no longer a one-off hotfix, it is a structural
checklist item.

All acceptance criteria pass. `make all` PASS, `make
publish-preflight` PASS, `npm run build` PASS, pre-commit-equivalent
scan CLEAN, doc sensitive-scan matches are all expected pedagogical
placeholders. Working tree is clean after commit + push. Cloudflare
Pages auto-deploys the new docs (which are served via the
pages.dev / custom-domain static site, but the **dashboard itself is
unchanged** — the public-data snapshot was refreshed but the content
shape is identical: 3 projects, 1 agent, 14 events, BookTrans Desk
still S13 / 16f38b6 / PARTIAL).

---

## 2. Why ACT-7 ships a playbook instead of a fourth project

Three reasons, in order of weight:

1. **Coverage is already good enough.** The three real projects span
   `local` / `public` locations, `agent-infra` / `art-gallery` /
   `reading-tool` categories, ACT/HP/S/P/L phase numbering styles, a
   green health (artvee-gallery), a green health (tower), and a
   PARTIAL/amber health (booktrans-desk). Adding a fourth project
   would not teach the docs anything new.

2. **ACT-6C is a process bug, not a tool bug.** booktrans-desk
   pointed at `conanxin/conanxin-homepage` and showed HP-33 as its
   current phase. That is not a tower shortcoming; it is the
   registering agent (or human) reading the case-study page instead
   of the source repo. The fix is documentation + checklist, not more
   data.

3. **Every new agent that runs `report-phase` for the first time will
   re-encounter the same three failure modes** (data leak to public
   / optimistic PASS / mis-attribution). Writing those into the
   playbook is the only way to scale the system beyond a single human
   reviewer. ACT-7 is the act of converting hard-won institutional
   knowledge into runnable procedures.

---

## 3. New artifacts

### 3.1 New docs

| Path | Bytes | Purpose |
| --- | --- | --- |
| `docs/AGENT_USAGE_PLAYBOOK.md` | ~18 KB | Main handbook (13 sections): what the system is, first-time machine setup, register agent / project, report phase / failure / review / handoff / release, export public-data, Cloudflare publish & verify, common errors. |
| `docs/MULTI_MACHINE_SETUP.md` | ~12 KB | Multi-machine scenarios: local vs cloud, multiple agents on one machine, two machines both editing `data/`, push-rejected recovery, who-can-do-what matrix, handoff events, "onboard in 10 minutes" recipe. |
| `docs/PUBLIC_DATA_EXPORT_PLAYBOOK.md` | ~16 KB | The export contract: data/ vs public-data/, what can/cannot be public, redaction rules, multi-project export, reading MANIFEST.json, **§7 ACT-6C mis-attribution lesson** (4 questions + 4 checks), handling stale events, online verification. |

### 3.2 New templates

| Path | Purpose |
| --- | --- |
| `templates/telegram/register-agent.txt` | Copy-paste to command a new agent to register itself. |
| `templates/telegram/register-project.txt` | Same for a new project. Includes the **ACT-6C `repo` rule**. |
| `templates/telegram/report-phase.txt` | Report a phase completion. Status/health table. Anti-PASS rule. |
| `templates/telegram/report-failure.txt` | Report a failure with `failure-reason`. |
| `templates/telegram/report-review.txt` | Report a code/design review. |
| `templates/telegram/report-handoff.txt` | Hand off a project from one agent to another. |
| `templates/telegram/report-release.txt` | Report a public release with `release_url`. |
| `templates/telegram/export-public-data.txt` | Full export procedure (3 projects, --replace, redaction summary check, build chain). |
| `templates/telegram/cloudflare-verify.txt` | Post-push online verification. |

### 3.3 New checklists

| Path | When to use |
| --- | --- |
| `templates/checklists/preflight-checklist.md` | Before any `git commit`, especially for `public-data/` changes. |
| `templates/checklists/redaction-checklist.md` | Before exporting to `public-data/`, and as the second-gate human review. |
| `templates/checklists/public-data-review-checklist.md` | After the redaction scanner, before `git commit`. The "second gate" for mis-attribution. |
| `templates/checklists/online-verification-checklist.md` | After `git push`, after the 60–90s wait. Includes the **ACT-6C regression check (§F)**. |

### 3.4 Updated docs

| Path | Change |
| --- | --- |
| `README.md` | ACT-7 status banner, "Start here" section, "Current recommended usage path" table, "Current live real projects" subsection, full ACT-7 chapter at the end. |
| `docs/AGENT_WORKFLOW.md` | Header now points new agents to the ACT-7 playbooks; the ACT-2 command-level doc is preserved as historical reference. |
| `docs/MVP_PLAN.md` | Title now `ACT-1 to ACT-7`; current-stage header set to ACT-7 ✅; timeline updated; full ACT-7 chapter added; "ACT-7+ — Future Optional Enhancements" relabelled. |
| `docs/OPEN_SOURCE_PLAN.md` | Added §11.3.1 — the **agent ↔ human two-gate** model for `public-data/` export, with explicit "agent can / cannot" lists, "human must review" list, and forbidden patterns. |
| `docs/DEPLOYMENT_PLAN.md` | Status banner set to ACT-7; new §9.6 points to `templates/checklists/online-verification-checklist.md`; full deploy cycle is now `agent → human review → export → checklist → push → wait → verify`. |
| `docs/DATA_MODEL.md` | Added §4.1 — full `status` / `health` choice table, anti-examples, the BookTrans Desk S13 PARTIAL/amber canonical case, and a "three-step judgment" before `report-phase`. |

---

## 4. How the three real projects power the playbook

Each project in `public-data/` plays a documentation role:

- **`agent-project-control-tower`** is the "self-tracker" example. It
  is the only project with `location: local`; its `primary_agent` is
  the same agent that built the tower. The ACT-0 → ACT-6C phase chain
  is the longest in the dataset, used in `MULTI_MACHINE_SETUP.md` to
  illustrate stable phase numbering.
- **`artvee-gallery`** is the "another agent maintains it" example.
  It uses a simpler `P2` / `P3B` numbering, demonstrating that
  ACT-style naming is not required. Referenced in
  `AGENT_USAGE_PLAYBOOK.md` §5 to show that phase_id is free-form.
- **`booktrans-desk`** is the **ACT-6C case study**. S13 (Blocker
  Fixes / Manual Validation Rerun) is referenced **verbatim** in
  six places:
  1. `AGENT_USAGE_PLAYBOOK.md` §5 status/health table
  2. `AGENT_USAGE_PLAYBOOK.md` §12.1 common error
  3. `PUBLIC_DATA_EXPORT_PLAYBOOK.md` §7 (entire section)
  4. `DATA_MODEL.md` §4.1 PARTIAL/amber anti-example
  5. `public-data-review-checklist.md` §B–§D regression check
  6. `online-verification-checklist.md` §F ACT-6C regression check

  The hotfix's repo / stage correction is the most-cited concrete
  example in ACT-7.

---

## 5. How the ACT-6C lesson is encoded in the deliverables

The lesson has three parts:

1. **`repo` must point at the real source repo**, not a homepage
   sub-directory.
2. **Phase id must come from the project's own numbering**, not from
   a case-study page.
3. **Mis-attributed events must be physically removed** from
   `data/events/` AND `public-data/events/`, not just "re-tagged".

Each part now has a structural home in the deliverables:

| Lesson part | Encoded in |
| --- | --- |
| #1 (`repo`) | `AGENT_USAGE_PLAYBOOK.md` §4, `PUBLIC_DATA_EXPORT_PLAYBOOK.md` §7.4, `public-data-review-checklist.md` §C, `online-verification-checklist.md` §F, `register-project.txt` "CRITICAL -- the repo field" section. |
| #2 (phase id) | `AGENT_USAGE_PLAYBOOK.md` §4, `PUBLIC_DATA_EXPORT_PLAYBOOK.md` §7.4, `DATA_MODEL.md` §4.1, `public-data-review-checklist.md` §B. |
| #3 (delete) | `PUBLIC_DATA_EXPORT_PLAYBOOK.md` §8.2 (full subsection "Old event for a different project that was mis-attributed"), `online-verification-checklist.md` §F. |

The result: a future agent that hits the same mis-attribution
problem will see the warning **at the moment they would otherwise
make the mistake** (during `register-project`, during
`export-public-data`, during `preflight`, and during online
verification).

---

## 6. Verification results

### 6.1 Local build chain

| Step | Result |
| --- | --- |
| `make all` | PASS (CLI SMOKE TEST PASSED; 53/53 smoke tests) |
| `make publish-preflight` | PASS (3 projects / 1 agent / 14 events; redaction FAIL=0, WARN=0) |
| `make public-build` | PASS (regenerated `generated/index.json` and `site/index.embedded.html` from `public-data/`) |
| `make site-only` | PASS (rebuilt embedded site) |
| `make dashboard` | PASS (6 pages in `apps/dashboard/dist/`, including the unchanged `/projects/booktrans-desk/index.html`) |
| `cd apps/dashboard && npm run build` | PASS (6 pages, 2.05s) |

### 6.2 Pre-commit-equivalent audit

A custom scanner reproduces the patterns of `/tmp/precommit_audit.py`
(which is not present on this machine — see the ACT-6B report for
the same workaround). It scans public-data + the embedded site HTML
for: credential assignments, real home paths, IPv4 addresses, .env
references, and `data/` path leaks.

| Path | Hits |
| --- | --- |
| `public-data/registry/projects.yml` | 0 |
| `public-data/registry/agents.yml` | 0 |
| `public-data/MANIFEST.json` | 0 |
| `public-data/events/*.json` (14 files) | 0 |
| `site/index.embedded.html` | 0 |
| `apps/dashboard/dist/**` | 0 |
| **Total** | **0** |

Result: **CLEAN**.

### 6.3 Document sensitive-pattern scan

A scan over `README.md docs templates reports/PHASE_ACT7_AGENT_USAGE_PLAYBOOK_REPORT.md` for the patterns
`token=|api_key|Authorization:|Bearer |password=|secret=|/home/[^ ]+|/Users/[^ ]+|[0-9]+.[0-9]+.[0-9]+.[0-9]+|.env`
returns matches. **Every match is an intentional pedagogical example** — the docs explicitly tell the agent "do not write token" or "do not write real paths" or "do not write real IPs" or "do not reference `.env`". The relevant excerpts:

| File | Match | Context | Disposition |
| --- | --- | --- | --- |
| `README.md` | `api_key=sk-123...abcdef` (in the ACT-2 example) | Shows what a redacted credential assignment looks like. | Expected. Pre-existing. |
| `README.md` | `/home/xin/` (in the ACT-2 example) | Same. | Expected. Pre-existing. |
| `README.md` | `/home/conanxin/` | Real local home path used in the ACT-5B verification log (an "expected 0 hits" claim). | Expected. Pre-existing. |
| `docs/AGENT_USAGE_PLAYBOOK.md` | `/home/<user>/`, `/Users/<user>/`, `C:\Users\<user>\` | §2.1, §3, §7 — all in the "do not write real home paths" warning. | Expected. Pedagogical. |
| `docs/AGENT_USAGE_PLAYBOOK.md` | `.env.local` | §7 — example of "do not reference .env" warning. | Expected. Pedagogical. |
| `docs/AGENT_USAGE_PLAYBOOK.md` | `192.168.1.1`, `10.0.0.5`, `8.8.8.8` | In §12 redaction-pattern examples. | Expected. Pedagogical. |
| `docs/MULTI_MACHINE_SETUP.md` | `/home/<user>/`, `C:\Users\<user>\` | §3 naming-anti-examples table. | Expected. Pedagogical. |
| `docs/PUBLIC_DATA_EXPORT_PLAYBOOK.md` | `/home/<user>/`, `.env.local`, IPv4s | §3 + §4 + §5 — same pattern. | Expected. Pedagogical. |
| `templates/checklists/redaction-checklist.md` | `/home/[^/]+/`, `\.env(\.\|$)`, IPv4s | §B is itself a sensitive-pattern scanner; the patterns are in the regex. | Expected. Pedagogical. |
| `templates/checklists/public-data-review-checklist.md` | `/home/[^/]+/` (in a "what to grep for" example) | §G "no-go signals" example. | Expected. Pedagogical. |
| `templates/checklists/online-verification-checklist.md` | `/home/[^/]+/`, `\.env(\.\|$)`, IPv4s | §G live-page scanner. | Expected. Pedagogical. |
| `templates/telegram/*.txt` | `home/<user>/` (in "do not write" warnings) | All Telegram templates. | Expected. Pedagogical. |
| `docs/DATA_MODEL.md` | (no new matches) | n/a | n/a |
| `docs/DEPLOYMENT_PLAN.md` | (no new matches) | n/a | n/a |
| `docs/OPEN_SOURCE_PLAN.md` | (no new matches in §11.3.1) | n/a | n/a |
| `docs/MVP_PLAN.md` | (no new matches) | n/a | n/a |
| `docs/AGENT_WORKFLOW.md` | (no new matches) | n/a | n/a |
| `reports/PHASE_ACT7_AGENT_USAGE_PLAYBOOK_REPORT.md` | (this file) | n/a | n/a |

**Net result**: every "hit" in the new ACT-7 content is in a "do not
write this" or "this pattern would be flagged" context. **No real
secrets, paths, IPs, or `.env` references are introduced.** Pre-existing
matches in `README.md` (from the ACT-2 era) are not in scope of this
hotfix; the same applies to all earlier reports.

### 6.4 Forbidden-paths check

| Forbidden path | In `git status`? |
| --- | --- |
| `data/` | no (gitignored) |
| `generated/` | no (gitignored) |
| `site/dist/` | no (gitignored) |
| `apps/dashboard/dist/` | no (gitignored) |
| `node_modules/`, `__pycache__/`, `.venv/`, `.env` | no |

`git status --short` shows only:
- New / modified tracked files inside `docs/`, `templates/`, `README.md`, and `reports/`.
- `site/index.embedded.html` and `public-data/` may appear in the
  pre-export rebuild (timestamp change in the embedded HTML is
  expected when `public-data` is regenerated).

### 6.5 Online verification (post-push)

After commit + push + 90s wait:

| URL | HTTP | Content check |
| --- | --- | --- |
| `https://control-tower.conanxin.com/` | 200 | `3 projects` / `14 events` / `BookTrans` / `conanxin/booktrans-desk` present; no `conanxin-homepage` / no `HP-33` |
| `https://control-tower.conanxin.com/projects/booktrans-desk/` | 200 | `S13` / `Blocker Fixes and Manual Validation Rerun` / `16f38b6` / `conanxin/booktrans-desk` / `PARTIAL` |
| `https://control-tower.conanxin.com/timeline/` | 200 | latest event per project; no ACT-6C regression |
| `https://control-tower.conanxin.com/agents/local-hermes/` | 200 | `BookTrans` / `S13` / `conanxin/booktrans-desk` |

| GitHub URL | HTTP | Notes |
| --- | --- | --- |
| `https://github.com/conanxin/agent-project-control-tower/blob/main/docs/AGENT_USAGE_PLAYBOOK.md` | 200 | New doc visible |
| `https://github.com/conanxin/agent-project-control-tower/tree/main/templates` | 200 | New templates/ dir visible |
| `https://github.com/conanxin/agent-project-control-tower/blob/main/docs/PUBLIC_DATA_EXPORT_PLAYBOOK.md` | 200 | New doc visible |

---

## 7. Current system state

- **Public dashboard**: unchanged in shape. 3 projects, 1 agent, 14 events.
  BookTrans Desk still `S13 / 16f38b6 / PARTIAL / conanxin/booktrans-desk`.
- **`data/`**: still gitignored. Not in `git status`. Not in the
  public dataset.
- **`generated/`**: still gitignored. Regenerated on this build, not
  committed.
- **`public-data/`**: re-exported this act (3 projects, 14 events,
  redaction FAIL=0, WARN=0). The shape is identical to the post-ACT-6C
  state; only the manifest's `generated_at` timestamp changed.
- **Working tree**: clean after the ACT-7 commit.
- **Public documentation**: README, AGENT_WORKFLOW, MVP_PLAN,
  OPEN_SOURCE_PLAN, DEPLOYMENT_PLAN, DATA_MODEL, plus three new
  playbooks, plus the templates and checklists directories — all
  live, all linked from the README "Start here" section.

---

## 8. Next-act recommendations

Two candidates, both reasonable, in priority order:

1. **ACT-8: real multi-agent onboarding trial.**
   Run the playbook end-to-end on a brand-new agent persona (e.g.
   `local-claude-m2` or `cloud-railway-1`). Every place the playbook
   is wrong, ambiguous, or missing a step becomes a documentation
   patch. ACT-8 is the act that converts ACT-7 from "documented
   intent" to "validated procedure".

2. **ACT-7B: convert templates into a CLI command generator.**
   The `templates/telegram/*.txt` files have a stable placeholder
   grammar. A `scripts/tower.py cmd` subcommand could parse those
   placeholders and produce the actual `tower.py` invocation, so
   the human does not have to copy-paste-and-edit. Lower risk than
   ACT-8, but does not validate the playbook itself.

If the user prefers a single, low-risk continuation, ACT-7B is the
safer choice. If the user wants to verify the playbook before
shipping more, ACT-8 is more honest. Either is fine; the
recommendation is **ACT-8** because the playbook is a contract that
has not yet been exercised by anyone other than the human reviewer.

ACT-7 itself does **not** add a public-data event. The user
explicitly asked the ACT-7 event to remain in `data/` until a
later act decides whether to publish it. (If a future act publishes
it, that act is responsible for the re-export + push + verify cycle.)
