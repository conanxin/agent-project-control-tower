# Public Data Export Playbook

> How to take a private dataset in `data/` and produce a sanitized, human-
> reviewed `public-data/` snapshot that the Cloudflare Pages dashboard
> will serve. The redaction rules, the multi-project export pattern, and
> the ACT-6C "BookTrans Desk was mis-attributed" lesson are all here.

---

## 1. The two datasets

```
       agent writes                human exports
            │                            │
            ▼                            ▼
   ┌────────────────┐          ┌──────────────────────┐
   │     data/      │  ──▶     │     public-data/     │
   │                │ redact   │                      │
   │  raw events    │  scan    │  redacted snapshot   │
   │  raw registry  │          │  + MANIFEST.json     │
   │  raw agents    │          │                      │
   └────────────────┘          └──────────────────────┘
            │                            │
            │ gitignored                 │ tracked in git
            │ never online               │ served by CF Pages
            ▼                            ▼
       (private)              https://control-tower.conanxin.com/
```

`data/` is the **truth** the agents work from. It is intentionally
gitignored so a leaked clone does not leak a year of half-written events.
`public-data/` is the **subset** that has been reviewed for
correctness (right project, right phase, right source commit) and
redaction (no tokens, no IPs, no home paths).

`generated/` is **not** a data source. It is a build artifact regenerated
from `public-data/` after every export. Reading from `generated/` instead
of `public-data/` will silently let stale builds look like fresh data.

---

## 2. What can be public

| Field | OK to publish? | Why |
| --- | --- | --- |
| `project_id`, `name`, `category` | yes | identifiers, not sensitive |
| `repo` (e.g. `conanxin/booktrans-desk`) | yes | it is already public on GitHub |
| `source_commit` (a git SHA) | yes | public once a commit is pushed |
| `source_commit_url` (a github.com URL) | yes | same |
| `phase_id`, `phase_name` | yes | titles only |
| `summary` | **only if** no secrets / paths / IPs | review before commit |
| `description` | **only if** no secrets / paths / IPs | review before commit |
| `next` | **only if** no secrets / paths / IPs | review before commit |
| `release_url` (e.g. a tagged release page) | yes if the release is public | if private, mark project as `location: local` and don't export it |
| `failure_reason` | **only if** no secrets / paths / IPs | review before commit |
| `design_reason`, `impact_analysis` | **only if** no secrets / paths / IPs | review before commit |

## 3. What must NOT be public

- **Tokens, API keys, passwords, bearer tokens.** The redaction scanner
  treats any `name=secret` shape (e.g. `api_key=...`, `token=...`) as
  `FAIL` and refuses to write.
- **Real home paths.** `/home/<yourname>/...`, `/Users/<yourname>/...`,
  `C:\Users\<yourname>\...` are all `WARN` (sometimes `FAIL`). Use a
  de-sanitized tag instead (`local-wsl`, `local-mac`, `cloud-vps`).
- **Real IPv4 addresses.** `192.168.x.x`, `10.x.x.x`, public IPs —
  `WARN`. Do not include them in any summary; if a story needs a host
  reference, use a tag.
- **`.env` references** (e.g. mentioning `.env.local`) — `WARN`. Avoid
  in summaries; mention the config by name only.
- **Anything that quotes a real secret from a real system.** If the agent
  was given a token in the past hour, do not put it in the event. Use
  a placeholder like `<REDACTED>` or simply omit the value.

If you are unsure about a field, treat it as private. The exporter's
`-redaction-checklist.md` is the canonical reminder.

---

## 4. Redaction rules (what the scanner does)

The `redaction` library in `scripts/lib/redaction.py` runs a small set
of regexes over every string field in every event and registry record
that is about to be exported. The output for each field is one of:

- `PASS` — no pattern matched. Safe to write.
- `WARN` — something matched but is ambiguous. The export proceeds and
  the warning is logged. The reviewer decides.
- `FAIL` — something matched that is almost certainly sensitive. The
  export refuses to write that record and exits non-zero. The whole
  export is aborted. The reviewer must rewrite the field.

The patterns (simplified):

| Pattern | Severity | Example trigger |
| --- | --- | --- |
| `Authorization: Bearer <token>` / `bearer <token>` | FAIL | `Authorization: Bearer ghp_abcdef...` |
| `name=value` where name ∈ {token, api_key, password, secret, ...} and value is 6+ chars | FAIL | `api_key=sk-123...abcdef` |
| `.env` reference (e.g. `.env.local`) | WARN | `Loaded from .env.local` |
| User home paths (`/home/<user>/...`, `/Users/<user>/...`, `C:\Users\<user>\...`) | WARN | `Built in /home/xin/workdir` |
| Any IPv4 address | WARN | `Connected to 10.0.0.5` |

The scanner is intentionally conservative. It will produce false
positives (e.g. flagging `192.168.1.1` in a paragraph explaining the
redaction rules). Review the warning context before assuming it's a
real leak.

---

## 5. Multi-project export

The current public dataset is the union of the three real projects.
The Makefile target `make public-data-real` only supports a single
project via the `PUBLIC_DATA_PROJECT` variable. For multi-project
exports, call the script directly with repeated `--project-id`:

```bash
python scripts/export_public_data.py \
  --source data \
  --output public-data \
  --project-id agent-project-control-tower \
  --project-id artvee-gallery \
  --project-id booktrans-desk \
  --max-events 50 \
  --repo-prefix conanxin \
  --replace
```

The script prints a redaction summary at the end:

```
redaction summary: FAIL=0, WARN=0
```

- `FAIL=0` is required to push.
- `WARN=0` is the goal; `WARN>0` is acceptable **only** if the
  reviewer has confirmed each warn is intentional (e.g. a docs
  example that shows the redaction pattern itself).

What the script does, in order:

1. Load registry and events from `data/`.
2. Apply the `--project-id` filter (intersection with `--agent-id` if
   given).
3. Apply `--max-events` per project, newest first by `created_at`.
4. Rewrite `local/<id>` placeholders to `<repo-prefix>/<id>` (so the
   real GitHub org appears in the public version).
5. Run the redaction scanner on every string field. Refuse to write
   if any `FAIL`.
6. With `--replace`: wipe `public-data/registry/` and
   `public-data/events/` first, then write the new snapshot and a
   fresh `MANIFEST.json`.
7. Without `--replace`: merge — keep existing files that are not in
   the new export, overwrite the ones that are.

The default mode is merge; for our use, **always use `--replace`**.
Merge mode is for one-off exports where you want to layer a new
project onto an existing dataset.

---

## 6. How to read public-data/MANIFEST.json

```json
{
  "agent_filter": null,
  "event_count": 14,
  "max_events_per_project": 50,
  "project_filter": [
    "agent-project-control-tower",
    "artvee-gallery",
    "booktrans-desk"
  ],
  "registry_files": ["agents.yml", "projects.yml"],
  "repo_prefix": "conanxin",
  "source": "data"
}
```

| Field | What it means |
| --- | --- |
| `source` | Always `data` for production exports. (Examples use `examples`.) |
| `project_filter` | The set of `project_id`s the export kept. Anything not in this list is **not** in the public dataset. |
| `event_count` | The total events written across all projects in this export. |
| `max_events_per_project` | Per-project cap. If a project has more events than this, only the newest N are kept. |
| `repo_prefix` | The prefix used to rewrite `local/<id>` placeholders. Should be your GitHub org. |
| `registry_files` | The registry files written. Almost always `agents.yml` + `projects.yml`. |
| `agent_filter` | Optional. When set, only events from that agent are kept. |

When you commit `public-data/`, the manifest is your receipt. Diffing
manifests across commits is a good way to spot accidental changes to
the export shape (e.g. a project accidentally being filtered out, or
the event count dropping unexpectedly).

---

## 7. How to avoid mis-attribution (the ACT-6C lesson)

This is the section that exists because of one real bug.

### 7.1 What happened (ACT-6C)

When `booktrans-desk` was first registered in the tower, its
`repo` was set to `conanxin/conanxin-homepage`. A `PHASE_REPORT` was
emitted with `phase_id=HP-33` ("Final Public Launch QA"), a green
status, and a `source_commit` from the homepage repo. The result was
that the public dashboard showed BookTrans Desk as:

- repo: `conanxin/conanxin-homepage` ❌ (it's actually
  `conanxin/booktrans-desk`)
- current phase: HP-33 ("Final Public Launch QA") ❌ (it's actually
  S13, "Blocker Fixes and Manual Validation Rerun")
- source commit: a homepage commit ❌ (it's actually `16f38b6` from
  the BookTrans Desk repo)

The mis-attribution survived several commits because the homepage
case-study page **does** contain a "BookTrans Desk" section, and a
cursory read of the homepage could convince you that BookTrans Desk
is "shipped" (HP-33). But the actual source code lives elsewhere.

### 7.2 Why this kind of mistake is easy to make

- A project has both a **case study** (text on a website) and a
  **codebase** (a Git repo). The case study is easy to find and
  looks authoritative.
- The case-study author sometimes also works on the codebase, so
  recent commits in the case-study repo can include references to
  the project. That makes the mis-attribution feel plausible.
- `report-phase` accepts any `phase_id` you give it. The CLI does
  not check whether the phase exists in the project's own repo.

### 7.3 The rule

> **A homepage's project showcase page is not the same thing as the
> project's real source repository. If a project has its own GitHub
> repo, the tower's `repo` field must point at that repo — never at
> a sub-directory of another repo (homepage or otherwise).**

If you want a homepage's case-study represented in the tower,
register the **homepage** as its own project (`conanxin-homepage`),
not as a sub-claim on the underlying tool.

### 7.4 The four questions to answer before registering a project

1. **What is the source-code repo of this project?** Open the actual
   repo on GitHub. If you cannot, the project is not ready to be
   registered.
2. **What is the most recent commit in that repo?** Run `git log
   --oneline -5` there. That is what `source_commit` will be for
   the next phase event.
3. **What is the project's own phase numbering?** Use the project's
   own phase ids (e.g. `S13`), not the homepage's case-study
   numbers (e.g. `HP-33`). If the project has no phase numbering,
   invent a simple one (`P1`, `P2`, ...).
4. **Is the case-study page's status the same as the code's
   status?** If they disagree, the **code wins** for the tower. The
   case study is decoration.

### 7.5 The four things to check on every export

After `export_public_data.py` returns `OK`, before you commit:

1. `cat public-data/registry/projects.yml` — every `repo` points at
   the real source repo, not a homepage sub-directory.
2. `cat public-data/MANIFEST.json` — `event_count` matches what you
   expect; `project_filter` is exactly the projects you intended to
   include.
3. `ls public-data/events/ | grep -E "booktrans-desk"` — only
   events that **belong** to BookTrans Desk. No HP-33 lurking.
4. `grep -RE "conanxin-homepage|HP-33" public-data/projects/booktrans-desk/` —
   if anything matches, the mis-attribution came back. Re-read
   `data/events/`, find the stray file, and remove or reclassify it
   before pushing.

---

## 8. How to handle old / stale events

The tower treats events as **append-only history** in the data model,
but that does not mean every old event belongs in the public snapshot.

Common cases and the recommended response:

### 8.1 Old event for the **same** project, but a wrong phase

- Keep the event in `data/events/` (it is real history).
- The latest event for the project wins on the dashboard. Just emit
  the correct one.
- If the old event is also in `public-data/events/`, it will still
  appear in the timeline (it is history), but it will not be the
  "current phase". That is correct.

### 8.2 Old event for a **different** project that was mis-attributed

- The ACT-6C case: an event whose `project_id` is `booktrans-desk`
  but whose `source_repo` is `conanxin/conanxin-homepage`.
- **Delete the file** from both `data/events/` and
  `public-data/events/`. It was never a real BookTrans Desk event;
  it was a homepage event that got the wrong `project_id`.
- The git history of `public-data/` still has the file (in a prior
  commit). That is fine. It is the audit trail.

### 8.3 Old PROJECT_REG event that you want to "re-register" cleanly

- The CLI is idempotent on `project_id`; re-running
  `register-project` does **not** write a second registry entry.
  It may write a fresh `PROJECT_REGISTERED` event.
- If you want a single clean `PROJECT_REGISTERED` event, just
  delete the old one from `data/events/` and `public-data/events/`
  and re-run.

### 8.4 Old event with a now-private `source_repo`

- If the source repo was made private, the `source_repo` field on
  the event no longer points to anything public.
- Recommendation: set the project's `location` to `local` in
  `data/registry/projects.yml` and stop exporting it to
  `public-data/`. The history of events in `public-data/` is
  already published; the dashboard will simply stop showing the
  project as "current". This is acceptable.

---

## 9. How to verify the live result

After `git push` and a 60–90s wait for Cloudflare Pages' CDN:

```bash
# 1. Home page
curl -L https://control-tower.conanxin.com/ \
  | grep -E "agent-project-control-tower|Artvee|BookTrans|projects|events" -n

# 2. Project detail page
curl -L https://control-tower.conanxin.com/projects/booktrans-desk/ \
  | grep -E "BookTrans|S13|16f38b6|PARTIAL|conanxin/booktrans-desk" -n

# 3. Timeline
curl -L https://control-tower.conanxin.com/timeline/ \
  | grep -E "BookTrans|S13|16f38b6" -n

# 4. Agent page
curl -L https://control-tower.conanxin.com/agents/local-hermes/ \
  | grep -E "BookTrans|S13" -n

# 5. Sensitive scan on the live site
for u in / /timeline/ /projects/booktrans-desk/ /agents/local-hermes/; do
  curl -sL "https://control-tower.conanxin.com$u" \
    | grep -nE "api_key=|token=|Authorization:|<REAL_"
done
# expected: no output
```

A full checklist is in
`templates/checklists/online-verification-checklist.md`.

---

## 10. Quick-reference: the three real projects

The current public dataset is the union of:

- `agent-project-control-tower` — repo
  `conanxin/agent-project-control-tower`, location `local`,
  category `agent-infra`. Tracks the tower itself.
- `artvee-gallery` — repo `conanxin/artvee-library`, location
  `public`, category `art-gallery`. An open-source art gallery
  + daily inspiration digest.
- `booktrans-desk` — repo `conanxin/booktrans-desk`, location
  `public`, category `reading-tool`. An open-source desktop tool
  for structured PDF and EPUB translation. Current phase: **S13
  (Blocker Fixes and Manual Validation Rerun)**, source commit
  `16f38b6`, status **PARTIAL/amber** (real Windows click-through
  still BLOCKED_MANUAL).

The ACT-6C hotfix is the reason `booktrans-desk` now points at
`conanxin/booktrans-desk`. Before the hotfix, it pointed at
`conanxin/conanxin-homepage`. Do not let that regression come back.

---

## 11. The double-gate and the ACT-7B generator

ACT-7B added `scripts/generate_tower_command.py` and
`scripts/check_template_cli_alignment.py`. Both live next to the
double-gate rule, and the rule still applies. This section makes
the relationship explicit so future contributors do not relax the
gate under the impression that the generator is "the new export".

### 11.1 What the generator does

`generate_tower_command.py export-public-data ...` prints, on
stdout, a single-line command such as:

```bash
python scripts/export_public_data.py --source data --output public-data --project-id agent-project-control-tower --project-id artvee-gallery --project-id booktrans-desk --replace
```

That is the **whole** effect of the generator for export. It is
indistinguishable from a careful human hand-writing the line.
The privilege boundary does not move.

### 11.2 What the generator does not do

- It does **not** call `subprocess.run(...)` against
  `export_public_data.py`. There is no `--execute` flag. There
  will never be one.
- It does **not** touch `data/`, `public-data/`, or `generated/`.
  It only writes to stdout.
- It does **not** commit, push, or open a PR. That is the
  human reviewer's job.
- It does **not** bypass the trial-agent rule. A trial agent that
  *runs* the printed command is still in violation of the
  double-gate rule. The generator does not change who is allowed
  to run the command, only how the command is *spelled*.

### 11.3 Who is allowed to run the export

The double-gate rule (see §5 for the operational definition)
remains:

- **Gate 1 (write):** The trial agent that wrote the events into
  `data/` does not run `export_public_data.py`. Period.
- **Gate 2 (publish):** The export is a redacted snapshot of
  `data/`. Pushing it is a human reviewer's action, possibly
  assisted by a designated exporter agent that has been
  pre-authorized. Trial agents are not exporters.

The generator's role in this is **only** to make Gate 1's
command-line spelling robust. It does not give any agent the
authority to run Gate 2.

### 11.4 The three commands around the export

The full sequence of `tower.py` invocations for an export cycle
is unchanged by ACT-7B. The generator just makes each invocation
robust:

```bash
# (1) Generate the export command (local reviewer only)
python scripts/generate_tower_command.py export-public-data \
  --source data --output public-data \
  --project-id agent-project-control-tower \
  --project-id artvee-gallery \
  --project-id booktrans-desk \
  --replace

# (2) Run the printed command (local reviewer only)
#     → redaction summary must show FAIL=0, WARN=0
#     → inspect public-data/registry/ and public-data/events/

# (3) Build the public artifacts
make public-build
make site-only
make dashboard

# (4) Review the diff
git status --short
git diff public-data/

# (5) Stage explicitly (no git add .)
git add public-data/registry/projects.yml \
        public-data/registry/agents.yml \
        public-data/MANIFEST.json \
        public-data/events/<new event file>

# (6) Commit and push
git commit -m "ACT-7B: <summary of public-data change>"
git push
```

If you are tempted to chain these into a single one-liner, the
generator will not help you. ACT-7B addresses command *spelling*,
not command *chaining*. The export pipeline is still a human
operation with explicit stages.

---

## 12. Automation levels (Level 0–5) and the ACT-9 policy

ACT-9 added `docs/PUBLIC_DATA_AUTOMATION_POLICY.md` as the
**single source of truth for what can be automated and what
cannot**. This section is the cross-reference; the policy
itself is the spec.

| Level | Name | Active? | Where documented |
| --- | --- | --- | --- |
| 0 | Manual only | historical | policy §3 |
| 1 | Assisted command generation | **active (ACT-7B)** | policy §3, generator source |
| 2 | CI validation only | **active (ACT-4A)** | policy §8, `DEPLOYMENT_PLAN.md` §5 |
| 3 | CI proposed export artifact | **prototype (ACT-9B)** | policy §10, this section §12.1 below |
| 4 | Authorized export bot | not designed; not approved | policy §3 |
| 5 | Fully automatic export | **explicitly rejected** | ADR-0001 "Why not fully automatic" |

### 12.1 ACT-9B prototype: build a candidate, then decide

The ACT-9B prototype lets you build a candidate artifact
locally (or via GitHub Actions) **without** writing to
`public-data/`. Use it when you want to preview what the
next real `export_public_data.py --source data --replace`
would do.

**Build it locally**:

```bash
# Default: reference mode (no-op, uses current public-data)
make candidate

# CI-safe fixture mode
make candidate-fixture

# Real mode (only on local-hermes, where data/ exists)
python scripts/build_public_data_candidate.py \
    --source data \
    --output artifacts/public-data-candidate \
    --project-id agent-project-control-tower \
    --project-id artvee-gallery \
    --project-id booktrans-desk
```

**Inspect the result**:

```bash
cd artifacts/public-data-candidate
ls -la
cat reports/CANDIDATE_SUMMARY.md
cat reports/MANIFEST_DIFF.md
cat reports/REDACTION_REPORT.md
cat reports/REVIEW_CHECKLIST.md
tar -tzf public-data-candidate.tar.gz
```

**Build it via CI** (no local clone needed):

1. Open the [Actions tab](../../actions/workflows/proposed-export.yml)
   of the repository.
2. Click **Run workflow** (right side).
3. Leave `source` at `public-data` (default; no-op) or pick
   `examples` (CI-safe fixture).
4. Wait for the run to finish.
5. Download the artifact
   `public-data-candidate-<source>-<run_id>` from the
   run page.

**If the candidate is acceptable**, promote it to the real
export (this is still a manual step on local-hermes):

```bash
python scripts/export_public_data.py \
    --source data --replace \
    --project-id agent-project-control-tower \
    --project-id artvee-gallery \
    --project-id booktrans-desk

# review the diff
git diff public-data/

# explicit add (never `git add .`)
git add public-data/registry/projects.yml \
        public-data/registry/agents.yml \
        public-data/events/*.json \
        public-data/MANIFEST.json
git commit -m "ACT-N: refresh public-data"
git push
```

**If the candidate is NOT acceptable**, delete the
`artifacts/public-data-candidate/` directory and re-run
after fixing the upstream issue. Nothing was published.

### 12.2 What ACT-9B is NOT

- It is not a "approve with one click" workflow. The
  reviewer still runs `git add`, `git commit`, and
  `git push` themselves.
- It is not an auto-merge to `main`. There is no path
  from the artifact to `main` that does not pass through
  a human working tree.
- It is not a hook for "auto-export when `data/` changes".
  CI cannot see `data/`.

**The seven questions ACT-9 answered (in priority order)**:

1. **Can CI auto-export public-data?** No (Level 2 max).
2. **Can an agent trigger the export?** No (Door 2 is
   human-only; trial agents are explicitly forbidden from
   running `export_public_data.py`).
3. **What must be human-confirmed?** §6's six-point
   project identity check + §7's status/health honesty +
   §5's redaction WARN judgment.
4. **How do we preserve the two-gate model?** §2 codifies
   it. Any future automation must keep Door 1 (agent
   writes `data/`) and Door 2 (human exports `public-data/`)
   separate.
5. **How do we avoid leaking `data/`?** `.gitignore` is
   load-bearing; no automation step may touch it. The
   policy §8.2 makes this a hard rail.
6. **How do we prevent the ACT-6C mis-attribution
   regression?** §6's checklist is mandatory pre-export.
   No automation, no matter how smart, can replace it.
7. **How do we handle redaction WARN/FAIL?** §5. FAIL
   aborts the export. WARN is human-judged.

**Pre-export checklist (mandatory)**:
`templates/checklists/public-data-automation-policy-checklist.md`.

**Architectural decision**: `docs/decision/ADR-0001-public-data-automation-boundary.md`.

## 13. ACT-9C: the export plan is the contract

Before ACT-9C, the export scope lived in three implicit
places: a Makefile variable (`PUBLIC_DATA_PROJECT=...`),
command history, and the human's head. ACT-9C moves it into
a single tracked file:

  `config/public-data-export-plan.yml`

That file is the **single source of truth** for what the
public dashboard is allowed to show. Both
`export_public_data.py` and `build_public_data_candidate.py`
now accept `--plan PATH` to read it. Mixing `--plan` with
`--project-id` / `--agent-id` is a hard error — the plan
file is the contract; ad-hoc flags cannot augment it.

### 13.1 Plan file shape

```yaml
schema_version: "0.1"
name: "default-public-dashboard"
source: "data"
output: "public-data"
projects:
  - agent-project-control-tower
  - artvee-gallery
  - booktrans-desk
agents:
  - local-hermes
  - cloud-openclaw
policy:
  level: "Level 1 + Level 2"
  human_review_required: true
  ci_may_validate: true
  ci_may_commit: false
  ci_may_push: false
  trial_agents_may_export: false
```

### 13.2 What changed in the toolchain

- `make publish-preflight` now invokes
  `export_public_data.py --plan config/public-data-export-plan.yml`.
  The historical `PUBLIC_DATA_PROJECT=agent-project-control-tower`
  Makefile default (which silently truncated public-data to 1
  project on every local rebuild) is gone.
- `make candidate` now invokes
  `build_public_data_candidate.py --plan ...` so the candidate
  artifact uses the same scope as `publish-preflight`.
- Both scripts record the plan's `plan_file` and `plan_name`
  in the produced `MANIFEST.json` so reviewers can verify
  provenance at a glance.
- A new test (`make export-plan-test`) pins the contract:
  9 test functions, ~33 assertions, all stdlib.

### 13.3 The artifact review checklist

For every candidate artifact (local tarball or GitHub Actions
artifact), use:

  `templates/checklists/proposed-export-artifact-review-checklist.md`

It walks through provenance, plan alignment, counts, project
identity, redaction, CI behavior, and the publish step. ACT-9C
made the plan-alignment step (§1) mandatory.

### 13.4 Why not just put the projects list in code?

Because the export scope is a **business decision**, not a
technical one. Adding a fourth project to the public
dashboard should be a tracked, reviewable change — a PR that
touches one YAML file and is reviewed by a human — not a
"remember to also update the Makefile / the script / the
candidate test" scramble. ACT-9C makes the diff one file, the
review one file, and the rollback one file.
