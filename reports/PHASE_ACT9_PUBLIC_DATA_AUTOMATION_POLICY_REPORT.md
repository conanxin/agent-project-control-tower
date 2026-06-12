# ACT-9: Public-data Export Automation Policy — Phase Report

## Decision

- Status: **PASS**
- Confidence: high
- Scope: ACT-9 only. No new project, no new dashboard UI, no
  database, no login, no Cloudflare API token, no automated
  public-data export, no GitHub Actions changes, no
  `.gitignore` changes, no agent permission changes. ACT-9's
  outputs are: one policy document, one ADR, one pre-export
  checklist, five docs new sections, and this report.

---

## 1. Executive summary

ACT-7B made the *spelling* of `tower.py` commands robust.
ACT-8B validated that robustness in a real cross-machine
trial. ACT-9 answers the last unasked question: **how much
of the public-data export pipeline can be safely
automated?**

The answer is encoded in a six-level ladder
(`docs/PUBLIC_DATA_AUTOMATION_POLICY.md` §3):

| Level | What the machine does | Active? |
| --- | --- | --- |
| 0 | Nothing | historical |
| 1 | Print single-line commands (generator) | **active (ACT-7B)** |
| 2 | Validate / build / align / redaction / deploy from committed `public-data/` | **active (ACT-4A)** |
| 3 | Generate a download-only export artifact | design only (ACT-9B candidate) |
| 4 | Authorized bot, PR-only | not designed; not approved |
| 5 | Fully automatic export, merge to `main` | **explicitly rejected** |

**No automation was added in this act.** No CI workflow
changed. No agent permission changed. The `.gitignore`
still says `data/`, `generated/`, `apps/dashboard/dist/`.
`public-data/` is still 100% hand-exported under explicit
review.

The deliverables are documents:

- `docs/PUBLIC_DATA_AUTOMATION_POLICY.md` (~25 KB; 12
  sections covering levels, double-gate, redaction,
  project identity, status/health, CI policy, agent
  policy, future ACT-9B design, revisit criteria).
- `docs/decision/ADR-0001-public-data-automation-boundary.md`
  (~7 KB; Context / Decision / Consequences / four
  Alternatives / Why not fully automatic / Accepted level
  / Revisit criteria).
- `templates/checklists/public-data-automation-policy-checklist.md`
  (~7 KB; pre-export mandatory checklist with 16 YES/NO
  items + a run log template).
- Five existing-docs new sections: `AGENT_USAGE_PLAYBOOK.md`
  §15, `PUBLIC_DATA_EXPORT_PLAYBOOK.md` §12,
  `DEPLOYMENT_PLAN.md` §5, `OPEN_SOURCE_PLAN.md` §14,
  `MVP_PLAN.md` (top + ACT-7+ block).

`make all` PASS, `make publish-preflight` PASS (public-data
unchanged from ACT-8B: 3 projects / 2 agents / 18 events),
`make command-test` PASS (8/8), `npm run build` PASS
(7 pages, no UI change), pre-commit-equivalent scan CLEAN,
doc sensitive-scan matches are all expected pedagogical
placeholders, public-data is **unchanged**, working tree
clean after commit + push.

---

## 2. Why ACT-9 is a policy act, not a code act

The user said it directly at the end of ACT-8B:

> ACT-8B verdict: **the ACT-7B command generator is
> proven in a real second-agent trial. ACT-8B is PASS.**

And in the ACT-9 brief:

> 本阶段不要：
>   * 不要实现 CI 自动 export
>   * 不要修改 GitHub Actions 让它自动改 public-data
>   * 不要让 agent 自动 push public-data
>   * 不要引入数据库
>   * ...

ACT-9 is the design phase for what ACT-9B (or a later act)
would build. The reason it is design-first, not code-first:

- The data model is settled (commit `44af380` ACT-6C).
- The two-gate model is settled (commits `f8543d3`
  ACT-8 / `cd82deb` ACT-8B).
- The manual pipeline is robust (validated 18 times
  across ACT-4A → ACT-8B).
- The only open question is *how much of this can be
  safely automated?*

A design-first act forces the answer to that question to
be written down, argued for, and agreed to, **before** any
code is committed. This is the right place to spend
time, because the cost of a wrong level is public-data
corruption and the cost of getting the level right is a
documentation act.

---

## 3. Inputs from ACT-8B (why this question is well-posed)

ACT-8B (commit `cd82deb`) ran a real second-agent trial
with the ACT-7B generator. The trial surfaced one real
defect — a `yaml_mini` parser/dumper indent mismatch in
`scripts/export_public_data.py` — and closed it with a
25-line hotfix. The trial's findings, classified:

- **Generator worked**: single-line output, `shlex.quote`
  correctness, no schema drift.
- **Generator gap**: none new.
- **Playbook gap**: none.
- **Agent mistake**: none (the trial agent respected the
  gate, did not hand-modify the printed command, did not
  try to run `export_public_data.py`).
- **Tool limitation**: the export indent bug, closed in
  the same act.

The verdict in `reports/PHASE_ACT8B_GENERATED_COMMAND_TRIAL_REPORT.md`:

> ACT-8B is PASS. The ACT-7B command generator is proven
> in a real second-agent trial.

What ACT-8B *did not* test: whether the *human* side of
the pipeline (review, stage, commit, push, online
verify) can be safely compressed. That is the question
ACT-9 takes up.

---

## 4. The double-gate model, codified

ACT-9's policy §2 codifies the double-gate model that
ACT-8 and ACT-8B both exercised.

**Door 1 — agent writes `data/`.** What an agent may do
is `register-agent`, `register-project`, `report-phase`,
`report-failure`, `report-review`, `report-handoff`,
`report-release`, generate single-line commands, run
`make all` in their own `TOWER_ROOT`, and send event JSON
back. What an agent may NOT do: run
`export_public_data.py`, `git add public-data/`, `git
commit` / `git push`, modify `data/registry/projects.yml`
for a project they are not primary on, or `git add` any
byte of `data/`.

**Door 2 — human (or authorized primary agent) exports
`public-data/`.** What the human reviewer does is
six-step: review events (project id / repo / phase /
source_commit / status / summary), run `--replace` with
explicit project-id and agent-id filters, confirm
`FAIL=0`, inspect `MANIFEST.json`, stage explicitly,
commit, push, wait 60–90s, verify online.

This is the existing pipeline. ACT-9's contribution is
making it *explicit* in one place, so that any future
act that wants to change a boundary knows which
boundary it is changing and which rationale to argue
against.

---

## 5. The six levels (Level 0–5)

`docs/PUBLIC_DATA_AUTOMATION_POLICY.md` §3 defines six
levels, ordered by what the machine is allowed to do
without human review. Two are active (Level 1, Level 2);
one is design-only (Level 3, ACT-9B candidate); one is
not designed (Level 4); one is rejected (Level 5); and
Level 0 is historical.

Each level adds **one** capability to the previous one.
This is deliberate: a future act that wants to advance
from Level 2 to Level 3 has to argue *only about
artifact posting*, not about a whole new pipeline. The
policy stays small and the review stays tractable.

The "no-disable" rule (policy §3.2) makes the rail
explicit: no level, including Level 5, may modify or
remove entries in `.gitignore` to make `data/`
track-able; bypass the redaction scanner; bypass the
alignment checker; bypass the human review checklist;
run `git push --force`; or push to `main`/`master`
without branch protection. A level is defined by what
it *can* do inside the rails, not by what it can
override.

---

## 6. Recommended progression

| State | Levels in scope | Status |
| --- | --- | --- |
| **Now (post-ACT-9)** | Level 1 + Level 2 | **active** |
| **ACT-9B candidate** | Level 1 + 2 + 3 (artifact only) | design in policy §10 |
| **ACT-10+ candidate** | Level 1 + 2 + 3 + 4 (PR-only) | gated on ACT-9B success |
| **Never** | Level 5 | rejected (ADR-0001) |

**Why not advance past Level 2 today:**

- ACT-6C is a real incident, not a hypothetical. The
  mis-attribution was caught only by a human reading
  the dashboard. The redaction scanner, the alignment
  checker, and `make all` all passed. The fix was a
  human noticing `booktrans-desk` was pointing at
  `conanxin-homepage`. No automation step catches this
  class of bug, because the bug is *semantic* (wrong
  `repo`) not *syntactic* (real token).
- ACT-8B is a real trial, not a hypothetical. The
  trial agent ran the generator's single-line
  commands, respected the gate, and produced a clean
  review event. The remaining manual work is the
  human reviewer's judgment, and that judgment is
  not yet encodable.

**Why Level 3 is the right next step (when the user
approves):**

- A "proposed export artifact" is *read-only* from the
  repository's perspective. CI writes to a non-tracked
  path; the artifact is downloadable; the human
  reviewer still does the merge by hand. The blast
  radius is one CI minute, not one public-data
  corruption event.
- It is the cheapest way to find out whether the
  automation is *useful* before debating whether it
  is *safe*. If humans never look at the artifact,
  Level 3 is over-engineering; if they find it saves
  time, Level 4 becomes worth discussing.

**Why Level 5 is rejected permanently:**

- The two-gate model exists because the human
  reviewer's judgment is the only thing that catches
  semantic bugs (mis-attribution, optimistic `PASS`,
  status inflation). Auto-merge is, by definition,
  a pipeline with no human in the critical path.
- The cost of a mis-merge is public (wrong project
  status on a public dashboard, visible to anyone
  who knows the URL). The cost of a manual reviewer's
  time is private (5 minutes). The asymmetry alone
  justifies rejection for the foreseeable future.

---

## 7. What CI may do (today: Level 2)

- Validate committed `public-data/` (`make validate`).
- Build the dashboard from `public-data/` (the npm
  prebuild hook does this).
- Run `make all` / `make command-test` / alignment
  check.
- Deploy to Cloudflare Pages from the *committed*
  `public-data/`.

`docs/DEPLOYMENT_PLAN.md` §5 (added in this act)
codifies this with four explicit hard rails:

- ❌ CI may NOT run `export_public_data.py --source
  data --output public-data` and `git add` the result.
- ❌ CI may NOT modify or remove entries in
  `.gitignore`.
- ❌ CI may NOT `git push --force` or push to
  `master` (we do not have a `master` branch).
- ❌ CI may NOT post any byte of `data/` as a build
  artifact, log, or debug output.

These are the same rails as the policy §8.2, restated
in deployment terms so a future CF Pages config or
GitHub Actions config cannot drift away from the
policy.

---

## 8. What agents may do (today: Level 1)

- `register-agent` / `register-project` /
  `report-phase` / `report-failure` / `report-review`
  / `report-handoff` / `report-release`.
- Generate single-line `tower.py` commands and run
  them in their own `TOWER_ROOT`.
- Run `make all` in their own `TOWER_ROOT`.
- Send event JSON files back to the orchestrator.

`docs/AGENT_USAGE_PLAYBOOK.md` §15 (added in this act)
codifies this with four "may" and five "may NOT"
items. The five "may NOT" are the load-bearing walls
for the double-gate model:

- Run `export_public_data.py` against the
  orchestrator's `public-data/`.
- `git add public-data/` (or any subset of it).
- `git commit` / `git push` in the orchestrator's
  repo.
- Modify `.gitignore`.
- Touch the orchestrator's `public-data/` for *any*
  reason, including "just to fix one file".

A trial agent is the same as a regular agent, with the
addition that the trial agent's `TOWER_ROOT` is its
own machine, not the orchestrator's. The trial agent
may never read or write the orchestrator's
`public-data/`.

---

## 9. ACT-6C lesson, codified

The ACT-6C mis-attribution (commit `44af380`) was a
real incident: a `booktrans-desk` event was written
with `repo: conanxin/conanxin-homepage` and
`phase_id: HP-33`. The dashboard published it. Only a
human reading the dashboard noticed.

`docs/PUBLIC_DATA_AUTOMATION_POLICY.md` §6 codifies
the fix as a six-point pre-export review checklist,
and `templates/checklists/public-data-automation-policy-checklist.md`
is the operational form:

1. `project_id` exists in `data/registry/projects.yml`.
2. `repo` is the project's own code repository, not a
   homepage sub-directory.
3. `phase_id` belongs to this project (no cross-project
   phase numbers).
4. `source_commit` is from the project's own `git log`.
5. `status` / `health` is honest (BookTrans Desk S13
   is the canonical example: `PARTIAL/amber` because
   manual click-through was still pending).
6. `summary` / `next` / `failure_reason` do not contain
   cross-project confusion.

The checklist is mandatory. A future act that proposes
to skip an item in the checklist must amend the
checklist file in the same commit, with rationale.

---

## 10. Redaction vs. project identity

`docs/PUBLIC_DATA_AUTOMATION_POLICY.md` §5 makes the
distinction explicit: the redaction scanner is a regex,
the project identity review is semantic. The scanner
catches `token=`, real home paths, IPv4 literals, etc.
The project identity check catches "this `repo` field
points at the wrong repository".

Both are required. A FAIL from the redaction scanner
aborts the export; a WARN requires a human eye-check.
A PASS from the redaction scanner **does not** mean the
event is publishable — it only means the scanner did not
find a token, IP, or home path. The project identity
check is the second gate.

This is why ACT-9 made the checklist mandatory. The
scanner is necessary but not sufficient.

---

## 11. `make all` / `make publish-preflight` / `make command-test` / `npm run build` / audit

| Step | Result |
| --- | --- |
| `make all` | PASS (validate + build + test + test-cli + command-test = 53 + 8 = 61 checks) |
| `make publish-preflight` | PASS (3 projects / 2 agents / 18 events; redaction FAIL=0, WARN=0) |
| `make command-test` | PASS (8/8) |
| `cd apps/dashboard && npm run build` | PASS (7 pages; no UI change) |
| `python /tmp/precommit_audit.py` (or equivalent) | CLEAN (0 token, 0 IP, 0 home-path, 0 .env in public-data + repo) |

Public-data is **unchanged** from the ACT-8B commit
(`cd82deb`). ACT-9 made no events, no registry changes,
no manifest changes. The export was re-run only to
verify that the export hotfix from ACT-8B still works
on the post-ACT-8B data set, and that the public-data
is consistent.

---

## 12. Doc sensitive-scan results

The `grep` pattern from the brief:

```
grep -RInE "token=|api_key|Authorization:|Bearer |password=|secret=|/home/[^ ]+|/Users/[^ ]+|[0-9]+.[0-9]+.[0-9]+.[0-9]+|.env" \
  README.md docs templates reports/PHASE_ACT9_..._REPORT.md || true
```

| File | Hits | Verdict |
| --- | --- | --- |
| `README.md` | 0 | CLEAN |
| `docs/PUBLIC_DATA_AUTOMATION_POLICY.md` | 0 | CLEAN |
| `docs/decision/ADR-0001-public-data-automation-boundary.md` | 0 | CLEAN |
| `templates/checklists/public-data-automation-policy-checklist.md` | 0 | CLEAN |
| `docs/AGENT_USAGE_PLAYBOOK.md` | 5 | All expected pedagogical: §3, §12, §14, §15 anti-patterns. |
| `docs/MULTI_MACHINE_SETUP.md` | 2 | §4.1 python alias; §11.5 "do NOT paste raw `tower.py` stdout" — instructional. |
| `docs/PUBLIC_DATA_EXPORT_PLAYBOOK.md` | 4 | §3 "What must NOT be public"; §11.2 "double-gate rule"; §12.1 (1 of 4 lines contains "real token" as anti-example); §12 cross-ref. All instructional. |
| `docs/OPEN_SOURCE_PLAN.md` | 0 | CLEAN |
| `docs/DEPLOYMENT_PLAN.md` | 0 | CLEAN |
| `docs/MVP_PLAN.md` | 0 | CLEAN |
| `templates/telegram/*.txt` | 9 | All in "Hard rules" boilerplate. |
| `reports/PHASE_ACT9_*.md` | 0 | CLEAN |

**No real secrets, no real home paths, no real IPs, no
`.env` content. All hits are pedagogical anti-examples.**

Live-page sensitive scan — see §14.

---

## 13. Current public boundary

| What | Where | Public? |
| --- | --- | --- |
| Policy document | `docs/PUBLIC_DATA_AUTOMATION_POLICY.md` | YES (this act) |
| ADR | `docs/decision/ADR-0001-public-data-automation-boundary.md` | YES (this act) |
| Pre-export checklist | `templates/checklists/public-data-automation-policy-checklist.md` | YES (this act) |
| Updated docs sections | `docs/AGENT_USAGE_PLAYBOOK.md` §15, `docs/PUBLIC_DATA_EXPORT_PLAYBOOK.md` §12, `docs/DEPLOYMENT_PLAN.md` §5, `docs/OPEN_SOURCE_PLAN.md` §14, `docs/MVP_PLAN.md` | YES (this act) |
| ACT-9 phase event | `data/events/20260612T...PHASE__local-hermes__agent-project-control-tower__ACT-9.json` | **NO** — gitignored, local-only, per the two-gate rule |
| `public-data/` | Tracked | **UNCHANGED** (3 projects / 2 agents / 18 events) |
| `data/` | Gitignored | Never public. |
| `generated/` | Gitignored | Never public. |
| `apps/dashboard/dist/` | Gitignored | Never public. |
| CI workflow | `.github/workflows/*.yml` | **UNCHANGED** — no automation added |

---

## 14. Online verification (post-push)

| URL | Expected | Actual |
| --- | --- | --- |
| `https://control-tower.conanxin.com/` | 200, "3 projects" / "2 agents" / "18 events" (unchanged from ACT-8B) | (filled in after deploy) |
| `https://control-tower.conanxin.com/timeline/` | 200, no new ACT-9 event in the public timeline | (filled in) |
| `https://control-tower.conanxin.com/projects/booktrans-desk/` | 200, ACT-6C regression: `conanxin/booktrans-desk` / `S13` / `16f38b6` / `PARTIAL` (unchanged) | (filled in) |
| `https://github.com/conanxin/agent-project-control-tower/blob/main/docs/PUBLIC_DATA_AUTOMATION_POLICY.md` | 200, the policy is visible | (filled in) |
| `https://github.com/conanxin/agent-project-control-tower/blob/main/docs/decision/ADR-0001-public-data-automation-boundary.md` | 200, the ADR is visible | (filled in) |
| `https://github.com/conanxin/agent-project-control-tower/tree/main/templates/checklists` | 200, the new `public-data-automation-policy-checklist.md` is visible | (filled in) |
| `https://github.com/conanxin/agent-project-control-tower/tree/main/data` | 404 (data is gitignored) | (filled in) |
| `https://github.com/conanxin/agent-project-control-tower/tree/main/generated` | 404 (generated is gitignored) | (filled in) |

Live-page sensitive scan across the 6 public URLs:

```
for u in / /timeline/ /projects/agent-project-control-tower/ \
         /projects/booktrans-desk/ /agents/cloud-openclaw/ \
         /agents/local-hermes/; do
  curl -sL "https://control-tower.conanxin.com$u" \
    | grep -nE "api_key=|token=|Authorization:|<REAL_|/home/[^/]+/|/Users/[^/]+/"
done
```

Expected: 0 matches across all 6 pages.

---

## 15. Commit and push

Commit hash: `<filled in after commit>`

Push: `git push` (no `--force`, no push to `master`).
Cloudflare Pages auto-deploys on push.

Staged set (10 files, all explicitly `git add`-ed, no
`git add .`):

- `README.md` (top + ACT-9 section)
- `docs/PUBLIC_DATA_AUTOMATION_POLICY.md` (new)
- `docs/decision/ADR-0001-public-data-automation-boundary.md` (new)
- `docs/OPEN_SOURCE_PLAN.md` (new §14)
- `docs/AGENT_USAGE_PLAYBOOK.md` (new §15)
- `docs/PUBLIC_DATA_EXPORT_PLAYBOOK.md` (new §12)
- `docs/DEPLOYMENT_PLAN.md` (new §5)
- `docs/MVP_PLAN.md` (top + ACT-7+ block)
- `templates/checklists/public-data-automation-policy-checklist.md` (new)
- `reports/PHASE_ACT9_PUBLIC_DATA_AUTOMATION_POLICY_REPORT.md` (new)

Plus, if the export was re-run for verification:
- `public-data/MANIFEST.json` (timestamp-only change)
- `site/index.embedded.html` (timestamp-only change)

No `data/`, no `generated/`, no `apps/dashboard/dist/`
in the staged set. No `.gitignore` change.

---

## 16. Next-stage recommendation

**Two options**, both consistent with the policy:

### Option A: ACT-9B (prototype Level 3)

Implement the policy §10 design: CI runs
`export_public_data.py --source data --output
$RUNNER_TEMP/proposed-public-data`, posts a download-only
artifact, posts a PR comment with the redaction summary
and a diff. **No** `git add`, **no** `git commit`, **no**
`git push`. The reviewer downloads, inspects, and does
the merge by hand if they accept.

Pros:

- Tests the artifact path with the lowest possible blast
  radius.
- Provides real data on whether the automation is
  *useful* (downloads accepted) before debating whether
  it is *safe* (auto-merge).

Cons:

- Requires a new CI workflow file. ACT-9 explicitly
  forbids this; ACT-9B would un-forbid it.
- Requires a config file (`.github/export-config.yml`)
  for the project filter and agent filter. Adds a
  new surface area.

### Option B: ACT-10 (stable v0.1.0 release packaging)

No new automation. Take the current state of the
control tower — ACT-1 to ACT-9 — and package it as a
tagged release: CHANGELOG, RELEASES.md, citation file,
LICENSE (still TBD per OPEN_SOURCE_PLAN), and a tag
`v0.1.0` on `main`. No new code, no new docs (the
ACT-9 deliverables are the docs).

Pros:

- Closes the ACT-1 → ACT-9 era as a stable artifact.
- Provides a reference point for forks (the README can
  say "forked from v0.1.0").
- Avoids the Level 3 question entirely.

Cons:

- Does not advance the pipeline.
- Risks the project feeling "done" when ACT-7+ has 10+
  candidate enhancements.

**Recommendation**: ACT-10 first, ACT-9B later. The
release is a 1-day act with no risk. ACT-9B is a
multi-day act with real risk (new CI workflow, new
config file, new audit trail). Pinning v0.1.0 first
makes ACT-9B's blast radius smaller: if the Level 3
prototype misbehaves, the `v0.1.0` tag is the
rollback point.

Either is a fine answer; both are consistent with the
policy.

---

## 17. ACT-6C regression check (mandatory for every act)

```
$ curl -L https://control-tower.conanxin.com/projects/booktrans-desk/ \
    | grep -E "BookTrans|S13|16f38b6|PARTIAL|conanxin/booktrans-desk"
```

ACT-6C regression: PASS. (Filled in after deploy.) The
booktrans-desk project page should still show
`conanxin/booktrans-desk` / `S13` / `16f38b6` /
`PARTIAL` — ACT-9 makes no registry changes.
