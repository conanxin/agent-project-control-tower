# Public-data Automation Policy

> **Status**: ACT-9 ✅ COMPLETE. Adopted. Currently operating at
> **Level 1 (assisted command generation) + Level 2 (CI
> validation only) + Level 3 (prototype available)**.
> **Level 4/5 is explicitly rejected.** See §3 for the level definitions, §4 for the
> recommended progression, and §10 for the ACT-9B
> proposal that introduced a Level-3 "CI proposed export
> artifact" with no automatic commit.
>
> **ACT-10 update**: v0.1.0 released (2026-06-12). Automation levels unchanged.
> Level 1 + Level 2 active, Level 3 prototype available, Level 4/5 not allowed.
>
> **ACT-11 update**: v0.1.1 added **Level 1.5 — assisted local
> update** (2026-06-12). `make public-update-preflight` is a
> human-only tool that regenerates `public-data/` and writes a
> reviewable artifact directory. It does **not** `git add`,
> `git commit`, or `git push`. It is **not** Level 4 (PR-only
> bot) and **not** Level 5 (auto-merge). See
> `docs/PUBLIC_DATA_EXPORT_PLAYBOOK.md` §14.
>
> This document is a **policy**, not a code change. No CI was
> modified in ACT-9. No public-data automation was turned on
> in ACT-9. The next time automation is *considered*, the
> answer must reference this document.

---

## 1. Why a policy is needed

`public-data/` is the only thing the public internet ever sees.
`data/` is the only thing the human reviewer ever trusts. The
two live in the same Git repository, on the same branch, and
the only thing keeping them separate is:

1. `data/` is in `.gitignore`. It is never committed.
2. `public-data/` is committed, but every byte of it was
   produced by `scripts/export_public_data.py --replace` from
   `data/`, under a redaction scanner, with a `MANIFEST.json`
   audit trail.

If we ever let CI or an agent run `export_public_data.py`
and `git add` the result, two failure modes become possible:

- **Accidental disclosure.** A redacted token slips through
  the redaction scanner (the scanner is a regex, not a
  semantic analyzer), or a `summary` field references a real
  home path, and CI commits it.
- **Mis-attribution.** A new agent persona writes a phase
  event with a wrong `project_id` or a wrong `source_repo`
  (the **ACT-6C** regression), and CI exports the
  mis-attributed event into the public timeline.

ACT-8 (commit `f8543d3`) and ACT-8B (commit `cd82deb`) both
exercised the manual two-gate pipeline and proved it works
when humans are paying attention. The open question is: **how
much of that pipeline can be safely automated?** The rest of
this document is the answer.

---

## 2. The current two-gate model

The control tower has exactly two privilege boundaries. They
are simple, and they have held in every act so far.

### 2.1 Door 1 — agent writes `data/`

**What an agent may do:**

- `register-agent` (themselves)
- `register-project` (a project they are working on)
- `report-phase` (a phase completion)
- `report-failure` (a blocker)
- `report-review` (a review of someone else's work)
- `report-handoff` (transferring a project to another agent)
- `report-release` (a public release)
- generate single-line commands via
  `scripts/generate_tower_command.py`
- run `make all` to validate their own `data/`
- copy event JSON files back to a different `data/` via
  `scp` / `cp`

**What an agent may NOT do by default:**

- run `export_public_data.py` (this is the privilege escalation)
- `git add public-data/` (this is the publish step)
- `git commit` and `git push` (this is the production step)
- modify `data/registry/projects.yml` for a *different* project
  than the one they are reporting on (this is the
  mis-attribution vector)
- `git add` anything under `data/` (which is gitignored, but
  the act of trying is logged in `git status --short` and
  should be treated as a near-miss)

### 2.2 Door 2 — human (or authorized primary agent) exports `public-data/`

**What a human reviewer (or pre-authorized exporter agent) does:**

1. Review every event file in `data/events/` for:
   - `project_id` plausibility
   - `repo` matches the project's real code repository
     (not a homepage sub-directory — see §6)
   - `source_commit` is a real commit hash from the project's
     own `git log`
   - `status` / `health` are honest (e.g. `PARTIAL/amber`
     when manual click-through is still pending — see §7)
   - `summary` / `next` / `failure_reason` are free of real
     home paths, IPs, tokens, and `.env` references
2. Run `python3 scripts/export_public_data.py --source data
   --output public-data --project-id <each> ... --replace`.
3. Confirm the redaction summary is `FAIL=0`. (WARNs are
   allowed only after a human eye-check; see §5.)
4. Inspect `public-data/MANIFEST.json` to confirm the
   exported scope matches the intent (project filter, agent
   filter, max-events cap).
5. `git add public-data/registry/projects.yml
   public-data/registry/agents.yml
   public-data/MANIFEST.json
   public-data/events/<new event files>` — **explicitly**,
   never `git add .`.
6. `git status --short` to review the staged set.
7. `git commit -m "<phase-id>: <what changed in public-data>"`.
8. `git push` (no `--force`, never to `master`).
9. Wait 60–90s for Cloudflare Pages + CDN cache.
10. Curl the public URLs and verify the new state.

This sequence is the ACT-4A / ACT-6 / ACT-7B / ACT-8B
pipeline. It is **manual** at the orchestrator level. ACT-7B
and ACT-8B made step 1's *command spelling* robust (single
line, no `\` continuations, no schema drift). ACT-9 is about
deciding which of steps 1–10 can be safely delegated to a
machine, and on what conditions.

---

## 3. Automation levels

Six levels, ordered by how much of the export pipeline a
machine is allowed to perform without human review.

|| Level | Name | Machine does | Machine does NOT | Current? |
|| --- | --- | --- | --- | --- |
|| 0 | **Manual only** | nothing | anything in the export pipeline | historical; superseded by Level 1 |
|| 1 | **Assisted command generation** | print single-line `tower.py` commands (`scripts/generate_tower_command.py`) | run the printed commands, modify `data/`, modify `public-data/`, push | **active** (ACT-7B) |
|| 1.5 | **Assisted local update** (ACT-11) | run `scripts/public_data_update_preflight.py` to regenerate `public-data/` from `data/` (plan-driven, with regression checks) and write a reviewable artifact directory | `git add public-data/`, `git commit`, `git push`, modify `data/`, touch Cloudflare | **active** (ACT-11) — human-only trigger, no auto-promote |
|| 2 | **CI validation only** | validate `public-data/`, build the dashboard, run `make command-test`, run the alignment checker, run the redaction scanner, deploy to Cloudflare Pages from the *committed* `public-data/` | write to `data/`, write to `public-data/`, `git add`, `git commit`, `git push`, disable `.gitignore` | **active** (ACT-4A) |
|| 3 | **CI proposed export artifact** | run `scripts/build_public_data_candidate.py` to a *non-tracked* path (`artifacts/public-data-candidate/`, gitignored), redaction-scan the result, post the tarball as a GitHub Actions build artifact (download-only) | `git add public-data/`, `git commit`, `git push`, modify `.gitignore` | **prototype available** (ACT-9B) — see §10 |
|| 4 | **Authorized export bot** | run the full pipeline, commit to a `proposed/public-data` branch, open a PR | merge to `main`, push to `master`, disable the branch protection rule, modify `.gitignore` | not designed; not approved |
|| 5 | **Fully automatic export** | run the full pipeline, merge to `main`, push, deploy | n/a | **explicitly rejected** |

### 3.1 Why these levels, in this order

Each level adds **one** capability to the previous one, and
each capability is independently auditable. A future act that
wants to advance from Level 2 to Level 3 has to argue **only
about artifact posting**, not about a whole new pipeline.
This makes the policy small and the review tractable.

### 3.2 The "no-disable" rule

No level, including Level 5, is allowed to:

- modify or remove entries in `.gitignore` to make `data/`
  track-able
- bypass the redaction scanner
- bypass the alignment checker
- bypass the human review checklist (§6)
- run `git push --force`
- push to `main` or `master` without branch protection

These are the *fixed rails*. A level is defined by what it
*can* do inside the rails, not by what it can override.

---

## 4. Recommended progression

The current state and the next two states are:

| State | Levels in scope | When |
| --- | --- | --- |
| **Now (post-ACT-9)** | Level 1 + Level 2 | already active |
| **ACT-9B candidate** | Level 1 + Level 2 + Level 3 (artifact only) | next act, if user approves |
| **ACT-10 candidate** | Level 1 + Level 2 + Level 3 + Level 4 (PR-only) | only after ACT-9B proves the artifact path is usable |
| **Never (in this project)** | Level 5 | rejected |

**Why not advance past Level 2 today:**

- ACT-6C (commit `44af380`) proved that mis-attribution is
  not a theoretical risk — it happened. The mis-attribution
  was caught only because a human read the dashboard
  and noticed `booktrans-desk` was pointing at
  `conanxin-homepage`. No automated check would have caught
  it; the redaction scanner does not look at `repo` fields.
  See §6 for the mis-attribution review checklist that
  any future automation must respect.
- ACT-8B (commit `cd82deb`) proved that the *agent* side
  of the pipeline is robust. The trial agent ran the
  generator's single-line commands, respected the gate, and
  produced a clean review event. The remaining manual work
  is the *human reviewer's* judgment, and that judgment
  is not yet encodable.

**Why Level 3 is the right next step:**

- A "proposed export artifact" is a *read-only* operation
  from the perspective of the repository. CI writes to
  a non-tracked path; the artifact is downloadable; the
  human reviewer still does steps 5–10 by hand.
- This is the cheapest possible way to find out whether
  the automation is *useful* before debating whether it is
  *safe*. If humans never look at the artifact, Level 3
  is over-engineering. If humans find it saves time, Level 4
  becomes worth discussing.
- It contains the blast radius. A bad artifact is a wasted
  CI minute. A bad auto-merge is a public-data corruption.

**Why Level 4 is not in this act's scope:**

- A bot that opens PRs requires branch protection rules,
  a maintainer allowlist, and a documented review path. None
  of those exist for this repo today.
- The user has explicitly asked for "design, not
  implementation" in ACT-9, and the same caution should
  apply to Level 4.

**Why Level 5 is rejected permanently:**

- The two-gate model exists because the human reviewer's
  judgment is the only thing that catches semantic bugs
  (mis-attribution, optimistic PASS, status inflation).
  An auto-merge pipeline is, by definition, a pipeline
  with no human in the critical path.
- The cost of a mis-merge is public: a wrong project
  status on a public dashboard, visible to anyone who
  knows the URL. The cost of a manual reviewer's time is
  private. The asymmetry alone justifies rejecting Level 5
  for the foreseeable future.

---

## 5. Redaction policy

The redaction scanner (in `scripts/export_public_data.py`
and `scripts/validate.py`) is a **necessary floor**, not a
**sufficient gate**.

| Severity | Examples | Behavior |
| --- | --- | --- |
| **FAIL** | `token=`, `api_key=`, `Authorization:`, `Bearer `, `password=`, `secret=`, real home path (`/home/<x>/`), real macOS path (`/Users/<x>/`), IPv4-looking literals, `.env` references | export **refuses to write** if any FAIL is found in any `data/` event. The export is aborted. |
| **WARN** | plausible-but-not-certain patterns; e.g. a kebab-case string that looks like a private hostname, or a path that *could* be a public bucket | export writes a `WARN=<n>` count to stdout. A human reviewer must check each WARN and decide. |
| **PASS** | everything else | export proceeds normally. |

**Important:** the scanner is regex-based and
**non-semantic**. It does not understand that
`booktrans-desk`'s `repo` field pointing at
`conanxin-homepage` is a *mis-attribution* (the
ACT-6C regression). Both `conanxin-homepage` and
`conanxin/booktrans-desk` are public-looking strings; the
scanner passes both. **A PASS from the redaction scanner
does not mean the event is publishable** — it only means
the scanner did not find a token, IP, or home path.

This is why §6 (project identity review) is a separate gate
that no automation can replace.

---

## 6. Project identity review (the ACT-6C gate)

The ACT-6C hotfix was a real incident. A real event file
with a wrong `project_id` / `repo` pairing was published to
`public-data/`, and only a human reading the dashboard
caught it. This checklist is the post-mortem codified.

### 6.1 The mis-attribution that happened

```
event file:
  project_id: booktrans-desk
  repo:       conanxin/conanxin-homepage    ← WRONG
  phase_id:   HP-33                        ← WRONG (this is the
                                             homepage's phase id,
                                             not booktrans-desk's)

public dashboard showed:
  BookTrans Desk
  repo: conanxin/conanxin-homepage           ← looked plausible
  current phase: HP-33                       ← seemed normal at
                                                a glance
  source commit: (some real homepage commit) ← not booktrans-desk
```

The dashboard was technically functional. Every value was a
public-looking string. The redaction scanner was happy. The
event was a `PHASE_REPORT`, the schema was right, the
`status` was reasonable. **It was wrong anyway.**

### 6.2 The six review checks (human must verify all six)

Before any `export --replace` that includes a new project or
a new event for an existing project, the human reviewer
must check:

1. **`project_id` plausibility.** Is the `project_id` the
   kebab-case name of a real, currently-tracked project?
   Run `cat data/registry/projects.yml` and confirm the
   project exists. If it does not, register it first via
   `register-project` (a new event should not be the first
   place a project appears).
2. **`repo` is the project's own code repository.** Not a
   homepage sub-directory, not a portfolio entry, not a
   case-study. For `booktrans-desk`, the correct `repo` is
   `conanxin/booktrans-desk`. For a project that has both
   a tool repo and a homepage, register the homepage as a
   *separate* project (e.g. `conanxin-homepage`), not as a
   sub-claim on the tool.
3. **`phase_id` belongs to this project.** A homepage's
   `HP-N` phase is not a tool's `S-N` phase. A tool's
   `S-N` phase is not a homepage's `HP-N` phase. Check
   against the project's own phase numbering convention.
4. **`source_commit` is from the project's own `git log`.**
   For `booktrans-desk`, the commit must come from
   `git -C /path/to/booktrans-desk log --oneline -5`. A
   commit from the homepage's `git log` is not valid for
   the tool.
5. **`status` / `health` is honest.** BookTrans Desk S13
   used `status=PARTIAL health=amber` because automated
   checks passed but the real Windows click-through was
   `BLOCKED_MANUAL`. The honest status is not `PASS/green`.
   See §7.
6. **`summary` / `next` / `failure_reason` do not contain
   project-identity confusions.** A summary that says
   "HP-33 homepage launch" inside a `booktrans-desk` event
   is a mis-attribution signal even if the `repo` is right.

### 6.3 What automation can and cannot do

- **Can:** the alignment checker can verify that the
  `report-*` subcommand in a template's `Command:` block
  is schema-consistent. It can catch a `report-review`
  template that lists `--source-repo`. It cannot tell
  whether a particular event's `repo` is the right one.
- **Cannot:** any of the six checks above. They require
  cross-referencing the event with the project's own
  repository, the project's own phase numbering, and the
  dashboard's prior state. These are human-only in
  Level 1 / Level 2 and remain human-only in Level 3+.

---

## 7. Status / health policy

`status` and `health` are the dashboard's headline. A
dishonest headline is worse than a missing event. The
mapping is enforced by `scripts/tower.py build_parser()`:

| `status` | auto `health` | meaning |
| --- | --- | --- |
| `PASS` | `green` | all verifications complete; nothing pending |
| `PARTIAL` | `amber` | automated verifications complete; **one or more** manual or external verifications still pending |
| `FAIL` | `red` | a critical verification failed |
| `BLOCKED` | `red` | work cannot proceed; an external condition is required |
| `PAUSED` | `gray` | work deliberately suspended; no verdict |
| `SKIPPED` | `gray` | work not done in this phase; no verdict |

### 7.1 The anti-pattern: optimistic `PASS`

The most common misuse is `status=PASS health=green` when
the truth is `PARTIAL/amber`. The pattern looks like:

- All CI checks pass.
- "We haven't run the manual click-through yet, but we're
  confident it will pass."
- → "Let's mark it green for now."

This is wrong. The dashboard's headline is a *commitment*
to a public reader. The honest value is `PARTIAL/amber`.
ACT-5B codified this lesson in `docs/AGENT_USAGE_PLAYBOOK.md`
§5; ACT-6C re-codified it in §12; BookTrans Desk S13 (commit
`16f38b6`) is the canonical example.

**Rule:** if a reasonable human reader would look at the
dashboard and say "the headline does not match the body",
the status is wrong. It is almost always `PARTIAL/amber`
when the body says "manual click-through still pending".

### 7.2 What automation can and cannot do

- **Can:** default-derive `health` from `status` (already
  done by `tower.py`).
- **Cannot:** upgrade `PARTIAL` to `PASS` based on absence
  of red in the test output. The judgment that
  "all manual items are also done" is a human judgment.
  A future ACT-9B artifact can *display* the
  manual-checklist state, but it cannot *consume* it.

---

## 8. CI policy

### 8.1 What CI is allowed to do (current: Level 2)

- Run `python3 scripts/tower.py validate --source
  public-data` on the *committed* `public-data/`. If it
  fails, the build fails.
- Run `python3 scripts/tower.py build --source public-data`
  to regenerate `generated/index.json` and
  `site/index.embedded.html` from the *committed*
  `public-data/`.
- Run `make command-test` (the alignment checker + the
  generator smoke test). If it fails, the build fails.
- Run `make all` and `make publish-preflight` for a full
  local rehearsal (the latter is opt-in and does not push).
- Build the Astro dashboard from `public-data/` (the npm
  prebuild hook already does this).
- Deploy to Cloudflare Pages from the *committed*
  `public-data/`. The CF Pages build pulls from the Git
  branch; it does not touch `data/`.

### 8.2 What CI is NOT allowed to do (ever)

- Run `export_public_data.py --source data --output
  public-data` and `git add` the result. This is the
  mis-attribution vector and the redaction-bypass vector.
- Modify or remove entries in `.gitignore`. The
  `.gitignore` is the load-bearing wall between `data/`
  and `public-data/`; a CI step that disables it is the
  single most catastrophic thing the pipeline could do.
- Run `git push --force` or push to `master` (we do not
  have a `master` branch; the primary branch is `main`).
- Re-run a failed CI export automatically. A failure means
  the human reviewer must look. Auto-retry would paper over
  mis-attribution.
- Disable the redaction scanner with an env-var override.
  There is no such override and there will not be one.
- Read `data/` and post any byte of it as a CI artifact.
  `data/` is the human's private state. The control tower
  has zero "share my data with CI" features and that is
  deliberate.

### 8.3 What CI may do in Level 3 (design only)

- Run `export_public_data.py --source data --output
  $RUNNER_TEMP/proposed-public-data` (a non-tracked path).
- Run the redaction scanner on the proposed artifact and
  fail the build if `FAIL > 0`.
- Upload the proposed artifact as a *download-only* build
  artifact (e.g. a zip of `proposed-public-data/`).
- **May NOT** `git add`, `git commit`, or `git push` the
  artifact. The human reviewer downloads it, inspects it
  on their own machine, and does the export-and-push by
  hand if they accept it.

---

## 9. Agent policy

This section is the agent-side mirror of §8. Agents
interact with the pipeline in the opposite direction of CI.

### 9.1 What an agent is allowed to do (current: Level 1)

- `register-agent` (themselves).
- `register-project` (a project they are working on).
- `report-phase` / `report-failure` / `report-review` /
  `report-handoff` / `report-release` for a project they
  are explicitly responsible for.
- Generate single-line `tower.py` commands via
  `scripts/generate_tower_command.py` and run them in their
  own `TOWER_ROOT`.
- Run `make all` in their own `TOWER_ROOT` to validate
  their own `data/`.
- Send event JSON files back to the orchestrator via
  `scp` / `cp` / Telegram.

### 9.2 What an agent is NOT allowed to do (ever, by default)

- Run `export_public_data.py` against the orchestrator's
  `public-data/`. This is the privilege escalation.
- `git add public-data/` (or any subset of it) in the
  orchestrator's repo. Even `git add
  public-data/MANIFEST.json` is a publish step.
- `git commit` / `git push` in the orchestrator's repo
  without explicit human authorization for *this* push.
  Authorization is per-push, not per-agent.
- Modify `data/registry/projects.yml` for a project they
  are not the primary agent of. (The primary agent is the
  `agent_id` passed to `register-project`; if the agent is
  not the primary, they may report events but not change
  the registry.)
- Attempt to add `data/` to the commit set. `data/` is
  gitignored; any attempt to `git add data/` should be
  treated as a near-miss and logged in
  `templates/checklists/redaction-checklist.md`.

### 9.3 Trial agents (ACT-8 / ACT-8B model)

A *trial agent* is an agent on a different machine running
a fresh `git clone` with a separate `TOWER_ROOT`. The trial
agent's `data/` is *not* the orchestrator's `data/`. The
trial agent's permissions (§9.1) apply to its own
`TOWER_ROOT`. The orchestrator's permissions (§9.2) apply
to the orchestrator's repo.

The trial agent may **never**:

- Read or write the orchestrator's `public-data/`.
- `git push` to the orchestrator's remote.
- Re-use a public-data filter it received from a previous
  trial. Each trial is a fresh export.

### 9.4 Authorization tokens (for future use, not implemented)

If Level 4 is ever approved, an authorization model would
need at minimum:

- A per-agent `AGENT_EXPORT_TOKEN` checked into the
  orchestrator's repo as a GitHub Actions secret (or
  equivalent), with no `git:` scope, only `contents:write`
  on a *single* `proposed/*` branch.
- A branch protection rule on `main` that requires the
  `human-review` label and at least one human approval
  before any PR can merge.
- An audit log of every export, including the SHA of
  the source `data/` event, the redaction summary, and
  the human reviewer's GitHub handle.

ACT-9 explicitly does **not** implement any of this. It is
listed here so that the Level 4 design is not invented
under pressure in a future act.

---

## 10. ACT-9B prototype (Level 3 — implemented, gate still required)

ACT-9B has been implemented. The Level 3 prototype is
**available**; it is **not an automatic publisher**. The
human gate from §2 still applies in full.

### 10.1 What was added

| Component | Path | Purpose |
|---|---|---|
| Candidate script | `scripts/build_public_data_candidate.py` | Builds a candidate artifact under `artifacts/public-data-candidate/` (gitignored) |
| Candidate test | `tests/candidate_artifact_smoke.py` | 22 assertions across 4 source modes |
| GitHub Actions workflow | `.github/workflows/proposed-export.yml` | `workflow_dispatch` only; uploads the tarball as a build artifact |
| Makefile targets | `make candidate`, `make candidate-fixture`, `make candidate-test` | Local reproduction of the same pipeline |

### 10.2 What the workflow does

On `workflow_dispatch` (manual trigger only — never on push,
never on PR), the workflow:

1. Verifies `data/` and `generated/` are still in `.gitignore`
   (defense-in-depth check).
2. Runs `scripts/build_public_data_candidate.py` with
   `--source public-data` by default (a no-op reference
   run that proves the pipeline works). The user can also
   select `--source examples` (CI fixture).
3. Verifies the candidate directory contains the four
   expected reports (`CANDIDATE_SUMMARY.md`,
   `MANIFEST_DIFF.md`, `REDACTION_REPORT.md`,
   `REVIEW_CHECKLIST.md`) and a tarball, and that
   the tarball does **not** contain `data/`, `generated/`,
   `.git`, `node_modules`, or `.env`.
4. Uploads the tarball + the four reports as a build
   artifact (`public-data-candidate-<source>-<run_id>`,
   14-day retention).

The workflow has `permissions: contents: read` (no write
access to the repo). It does **not** use any secrets. It
does **not** commit, push, or deploy anything.

### 10.3 What the human reviewer does

1. Opens the Actions run page.
2. Downloads the artifact.
3. Inspects `CANDIDATE_SUMMARY.md`,
   `MANIFEST_DIFF.md`, `REDACTION_REPORT.md`, and
   `REVIEW_CHECKLIST.md`.
4. Verifies the ACT-6C project identity checks (§6).
5. If the candidate is acceptable, on **local-hermes**
   (which is the only machine that has `data/`), runs:

   ```bash
   python scripts/export_public_data.py \
       --source data --replace \
       --project-id agent-project-control-tower \
       --project-id artvee-gallery \
       --project-id booktrans-desk
   ```

6. Reviews the diff, then **explicitly** `git add`s the
   files in `public-data/` (never `git add .`), commits,
   and pushes. Cloudflare Pages picks up the new public
   data automatically.

### 10.4 What ACT-9B explicitly is NOT

- It is not a "approve with one click" workflow. The
  reviewer still runs `git add`, `git commit`, and
  `git push` themselves.
- It is not an auto-merge to `main`. There is no path
  from the artifact to `main` that does not pass through
  a human working tree.
- It is not a hook for "auto-export when `data/` changes".
  The trigger is "human triggered the workflow manually".
  It never watches `data/` (it can't; `data/` is gitignored
  and CI cannot see it).
- It does not remove the "single project only" Makefile
  default. That default still applies to `make
  publish-preflight`. ACT-9B introduced **separate**
  targets (`make candidate`, `make candidate-fixture`).

### 10.5 Open questions still tracked

- The Makefile `publish-preflight` target still
  hard-codes a single project (`agent-project-control-tower`)
  for the actual export step. A 3-project version lives
  in the post-ACT-9B commit history (see `git log -p
  public-data/MANIFEST.json`) and is reproducible via
  `scripts/export_public_data.py` directly. ACT-9C
  (manual review workflow polish) is the natural place
  to wire the 3-project default into the Makefile.
- The CI workflow has 14-day artifact retention. If a
  reviewer needs the artifact for longer, they should
  download and store it locally. There is no remote
  artifact store (CF Pages, R2, S3) wired up.
- `cloudflare-verify` (a separate `tower.py` subcommand)
  is **not** invoked by this workflow. It is a local
  convenience only.

### 10.5 ACT-9C: the export plan is the contract

ACT-9C added a tracked plan file
(`config/public-data-export-plan.yml`) that both
`export_public_data.py` and `build_public_data_candidate.py`
read via `--plan PATH`. The plan is the single source of
truth for:

- which project IDs may appear in public-data/
- which agent IDs may appear in public-data/
- the export source (`data`) and output dir (`public-data`)
- the policy block (mirrors §8.2 hard rails)

**Hard rule**: `--plan` and `--project-id` / `--agent-id` are
mutually exclusive. If you find yourself wanting to override
the plan with CLI flags, the right answer is to update the
plan file (so the change is reviewed in a PR), not to pass
flags on the command line.

**Hard rule**: `make publish-preflight` MUST NOT silently
degrade to a 1-project export. The ACT-9B-era Makefile had
`PUBLIC_DATA_PROJECT=agent-project-control-tower` as a
default, which meant every local rebuild that didn't pass
explicit `--project-id` flags would silently overwrite
`public-data/` with a 1-project slice. ACT-9C removed that
default; `make publish-preflight` now uses the plan file
exclusively, and `make export-plan-test` pins the
non-degradation as a CI-runnable test.

The artifact review checklist at
`templates/checklists/proposed-export-artifact-review-checklist.md`
was updated to require plan-alignment verification (§1) as
the first review step.

---

## 11. Revisit criteria

This policy is not a permanent commitment. It is
revisitable when **all** of the following are true:

1. ACT-9B has run a Level-3 artifact in production for
   at least 30 days without a redaction FAIL or a
   mis-attribution event.
2. The artifact has been downloaded and accepted by the
   human reviewer at least 5 times across at least 2
   different events.
3. The mis-attribution rate (events caught by the
   §6.2 checklist and rewritten before export) is
   non-zero in the same period — proving the checklist
   is doing real work, not just sitting in a markdown
   file.
4. The user explicitly approves the move to Level 4.

Until then, this document is the answer to "why is the
export manual, and why is that good?".
