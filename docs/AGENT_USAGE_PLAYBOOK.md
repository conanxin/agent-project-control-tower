# Agent Usage Playbook

> The single entry point for any agent (local or cloud) that wants to use the
> Agent Project Control Tower. Read this first. Then follow the recipe that
> matches your situation.

---

## 1. What this system is

The Agent Project Control Tower is a small, zero-dependency control plane for
multi-agent project progress tracking. It is **not** a database, **not** a CI
service, **not** a login system. It is:

- a **Git repository** that holds metadata and event history for every
  project an agent works on;
- a **stdlib Python CLI** (`scripts/tower.py`) that lets agents register
  themselves, register projects, and append events;
- a **build step** (`make all` / `make publish-preflight`) that turns those
  events into a static, redacted dataset;
- a **public dashboard** served by Cloudflare Pages from the redacted
  dataset.

The mental model is intentionally simple:

| Layer | Lives in | Git tracked? | Visible online? |
| --- | --- | --- | --- |
| Source code of your project | The project's own Git repo (e.g. `conanxin/<project>`) | yes | not via this system |
| Local agent state, raw events | `data/` in **this** repo | **no** (gitignored) | **never** |
| Sanitized public dataset | `public-data/` in **this** repo | yes | yes — Cloudflare Pages serves it |
| Build artifacts (index, embedded HTML) | `generated/`, `site/index.embedded.html` | mostly no (`generated/` gitignored); `site/index.embedded.html` tracked | only via Astro dashboard |
| Public Astro dashboard | `apps/dashboard/dist/` | no (gitignored) | yes |

The cardinal rule: **agents write to `data/`; humans (or an explicitly
authorized agent) export to `public-data/`.** Public-data is the only thing
the internet ever sees.

If you are an agent, your job ends at `data/`. If you are a human reviewer,
your job starts at `public-data/`.

---

## 2. First-time machine setup

### Prerequisites

- Python 3.10+ (stdlib only; no pip install required)
- Node.js 18+ (only for the optional Astro dashboard build)
- `git` (obviously)
- `make` (for the zero-dep build chain)

### Steps

```bash
# 1. Clone the tower
git clone https://github.com/conanxin/agent-project-control-tower.git
cd agent-project-control-tower

# 2. Bootstrap local data/ (gitignored, fresh clone has no data/)
#    Pick ONE of these two:
#      (a) start from the curated examples/ seed (sanitized demo data):
#            python scripts/tower.py seed --force
#      (b) start from a real local project — register your agent, then
#          your project, then start reporting.
#
#    Without this step, `python scripts/tower.py validate` will fail
#    with "source dir missing: .../data", and so will `make all` (which
#    runs validate first). ACT-8 onboarding trial hit this on a fresh
#    cloud box; the playbook now calls it out explicitly.

# 3. Verify the local data path
python scripts/tower.py validate
# expected: OVERALL: PASS

# 4. Verify the public data path
python scripts/export_public_data.py --dry-run
# expected: prints a planned diff, exits 0, writes nothing

# 5. Run the full zero-dep build
make all
# expected: CLI SMOKE TEST PASSED

# 6. (Optional) Build the public Astro dashboard
make publish-preflight
cd apps/dashboard && npm run build && cd ../..
```

> **`make publish-preflight` is opt-in.** It is not part of `make all`,
> and a new agent should not run it as part of onboarding. Only the
> human reviewer (or a designated "exporter" agent) runs it, and only
> when there is a real `public-data/` change to ship. ACT-8 onboarding
> trial hit the assumption "publish-preflight is part of preflight";
> it is not.

> **The `python` command on Debian/Ubuntu.** `tests/smoke.py` hard-codes
> the literal `python` while the rest of the build uses `$(PYTHON)=python3`.
> On a box that does not have `/usr/bin/python` (most modern Debian /
> Ubuntu), `make test` will fail with `FileNotFoundError: 'python'`.
> Fix: `sudo ln -s /usr/bin/python3 /usr/local/bin/python` (or use a
> user-level venv). This is a known tool limitation; ACT-8 trial
> surfaced it. The recommended fix in the playbook is to add the
> symlink during machine bootstrap.

### Hard rules on first-time setup

- **Do not un-gitignore `data/`.** It is private by design.
- **Do not commit `generated/`.** It is regenerated on every build.
- **Do not run `git add .` in this repo.** Always list files explicitly.
- **Do not push to `master`.** The main branch is `main`.
- **Do not use a Cloudflare API token.** Deploys are triggered by pushing
  to `main`; the GitHub integration handles the rest.

---

## 3. Register a new agent

Each machine (and each distinct agent persona on the same machine) registers
itself once. After that, only `report-*` events are written.

### Command

```bash
python scripts/tower.py register-agent \
  --agent-id <AGENT_ID> \
  --name "<Human Readable Name>" \
  --machine "<machine-tag>" \
  --role "<role-tag>" \
  --operator "<your-handle>"
```

### Field guidance

| Field | Guidance |
| --- | --- |
| `--agent-id` | Stable kebab-case id. Once chosen, **never rename**. The whole event history is keyed by this. |
| `--name` | Display name. |
| `--machine` | A **de-sanitized tag**, not a real hostname or IP. Examples: `local`, `local-wsl`, `cloud-vps`, `cloud-railway`. Never `conanxin-notebook.local` or similar. |
| `--role` | Free text: `primary-coding-agent`, `reviewer`, `telegram-bridge`, etc. |
| `--operator` | Your handle, not your real name or email. |

### Idempotency

Re-running `register-agent` with the same `--agent-id` is a no-op. The
registry is keyed by id, so a duplicate call does not write a second agent
entry. It may, however, write a duplicate AGENT_REGISTERED event (one per
call) — that is intentional and harmless.

### Multiple agents on one machine

Yes, this is supported. Just give each a distinct `--agent-id` and the same
`--machine` tag. They will share `data/events/` (each writes its own
timestamped files; filenames never collide).

---

## 4. Register a new project

Projects are registered **once** per tower, by the first agent that touches
them. Other agents that work on the same project later just call
`report-phase` — they do **not** re-register.

### Command

```bash
python scripts/tower.py register-project \
  --project-id <PROJECT_ID> \
  --name "<Project Name>" \
  --repo "<owner>/<repo>" \
  --location public|local \
  --category <category> \
  --status ACTIVE \
  --description "<one-line description>" \
  --agent-id <AGENT_ID>
```

### Field guidance

| Field | Guidance |
| --- | --- |
| `--project-id` | Stable kebab-case id. Immutable. |
| `--name` | Display name. |
| `--repo` | **`owner/repo` of the real source repository** (e.g. `conanxin/booktrans-desk`). This is the **single most important field**. See "ACT-6C lesson" below. |
| `--location` | `public` if you intend to export it to `public-data/`, `local` if not. |
| `--category` | Free text, e.g. `reading-tool`, `art-gallery`, `agent-infra`. |
| `--description` | One sentence. Avoid quoting real home paths, IPs, or tokens. |

### ACT-6C lesson: the `repo` field is the ground truth

The most common registration mistake is pointing `repo` at the wrong
repository — typically at a *case-study page* or a *subdirectory* of another
repo. The dashboard then shows the wrong `source_commit` and the wrong
phase history.

**The rule is: `repo` must be the GitHub repository that holds the actual
source code of the project, full stop.**

- ❌ Wrong: pointing a desktop tool's tower entry at the homepage repo's
  sub-directory (`conanxin/conanxin-homepage`, sub-path
  `/projects/<tool>/`) just because there is a case-study page there.
- ✅ Right: pointing it at the tool's own standalone repo
  (`conanxin/<tool>`).

If the project is described in a case study on `conanxin.com` but lives in
its own repo, **the case study does not own the tower entry**. If you want
the case study represented in the tower, register it as a separate
`conanxin-homepage` project — do not co-mingle.

This was the ACT-6C hotfix: `booktrans-desk` had been pointing at
`conanxin/conanxin-homepage` and showing HP-33 ("Final Public Launch QA")
as its current phase. In reality the tool lives in
`conanxin/booktrans-desk` and was at S13 (commit `16f38b6`).

---

## 5. Report a phase completion

After finishing meaningful work on a project, append a `PHASE_REPORT` event.

### Command

```bash
python scripts/tower.py report-phase \
  --project-id <PROJECT_ID> \
  --agent-id <AGENT_ID> \
  --phase-id <PHASE_ID> \
  --phase-name "<short name>" \
  --status PASS|PARTIAL|FAIL|BLOCKED|PAUSED|SKIPPED \
  --summary "<1–2 sentence summary>" \
  --next "<what's next>" \
  --source-repo "<owner>/<repo>" \
  --source-commit <real commit hash from that repo>
```

### Status / health rules

The CLI derives a default `health` from `status`. The defaults are:

| `status` | default `health` |
| --- | --- |
| `PASS` | `green` |
| `PARTIAL` | `amber` |
| `FAIL` | `red` |
| `BLOCKED` | `red` |
| `PAUSED` | `gray` |
| `SKIPPED` | `gray` |

You can override `health` with `--health`, but only do so with a reason.

### Anti-pattern: optimistic `status=PASS`

If the automated checks all pass **but** a real human click-through or
external integration is still missing, the truth is **PARTIAL/amber**, not
PASS/green. Marking it PASS makes the public dashboard lie. We did this once
with BookTrans Desk S13 (commit `16f38b6`): all `npm` checks were green,
but the real Windows desktop click-through was `BLOCKED_MANUAL`. The
correct event used `status=PARTIAL health=amber`.

A 1–2 line rule of thumb:

> If a reasonable human reviewer would look at the dashboard and say "the
> headline does not match the body", the status is wrong. It is almost
> always `PARTIAL` when the body says "click-through still pending".

### `source_commit` is non-negotiable

`--source-commit` must be a real commit hash from the project's own `git
log`. If you don't have one, stop and run `git log --oneline -5` in the
project repo. If the project does not use git, this system is not the
right place to track it.

---

## 6. Report a failure

A failure is a phase that did **not** achieve its goal. Reporting it is
**not** optional — silent blockers are the most expensive thing in a
multi-agent system.

```bash
python scripts/tower.py report-failure \
  --project-id <PROJECT_ID> \
  --agent-id <AGENT_ID> \
  --phase-id <PHASE_ID> \
  --phase-name "<short name>" \
  --summary "<1–2 sentence summary>" \
  --failure-reason "<root cause, no secret / path / IP>" \
  --next "<what's next>" \
  --source-repo "<owner>/<repo>" \
  --source-commit <real commit hash>
```

`failure-reason` is auto-redacted: it runs through the same scanner as
`summary`. Do not paste real tokens, real home paths (`/home/yourname/`),
or real IPs in there. Refer to the failure by phase id and a short tag.

---

## 7. Report a review

For checkpoints that are neither a phase pass nor a failure: a code review, a
design review, an audit.

```bash
python scripts/tower.py report-review \
  --project-id       <PROJECT_ID> \
  --agent-id         <AGENT_ID> \
  --phase-id         <PHASE_ID> \
  --phase-name       "<short name>" \
  --status           PASS|FAIL|COMMENT_ONLY \
  --summary          "<what was reviewed and the verdict>" \
  --next             "<what comes next>" \
  --target-agent-id  <AGENT_ID_BEING_REVIEWED> \
  --target-phase-id  <PHASE_ID_BEING_REVIEWED> \
  --target-commit    <commit hash of the work being reviewed>
```

### `report-review` specific notes (ACT-8 trial)

- `report-review` is the **only** `report-*` command that does **not**
  accept `--source-repo` / `--source-commit`. The work being reviewed
  is described by `--target-agent-id` / `--target-phase-id` /
  `--target-commit` instead.
- It also does **not** accept `--design-reason` or `--impact-analysis`.
  Put that content inside the `--summary` field. (The earlier playbook
  draft listed those fields; the CLI was simpler. ACT-8 trial caught
  the mismatch and the template is now aligned with the CLI.)
- It does **not** require a pre-existing `register-project` for the
  target project to succeed — but `validate` will fail after the
  write if the project is not in `data/registry/projects.yml`. If
  you are reviewing a project that you have not registered locally,
  run `register-project` first.
- `--status` accepts `PASS`, `FAIL`, and `COMMENT_ONLY`. `COMMENT_ONLY`
  is for reviews that do not pass-or-fail (a "noted, no verdict"
  review).

### Anti-pattern: writing the wrong field shape

`report-review` mirrors the structure of a "review" of someone else's
work. The reviewer is `agent_id`; the reviewee is `target_agent_id`;
the work under review is identified by `target_phase_id` and
`target_commit`. Do **not** put the reviewee's commit in
`--source-commit` (that field does not exist on `report-review`).
Do **not** put the design rationale in `--design-reason` (that field
does not exist either). Put the design rationale at the tail of
`--summary`.

---

## 8. Report a handoff

Use this when one agent passes a project (or a sub-task) to another agent.
The handoff event lives forever in the timeline and tells future readers
where the work went.

```bash
python scripts/tower.py report-handoff \
  --project-id <PROJECT_ID> \
  --agent-id <FROM_AGENT_ID> \
  --to-agent <TO_AGENT_ID> \
  --reason "<short reason>" \
  --source-repo "<owner>/<repo>" \
  --source-commit <real commit hash>
```

---

## 9. Report a release

When a project ships a public artifact (a packaged binary, a vX.Y.Z tag, a
public deployment), record it as a release. This is what powers the
"Latest release" card on the dashboard.

```bash
python scripts/tower.py report-release \
  --project-id <PROJECT_ID> \
  --agent-id <AGENT_ID> \
  --version <vX.Y.Z> \
  --release-url "<public URL>" \
  --summary "<1–2 sentence summary>" \
  --source-repo "<owner>/<repo>" \
  --source-commit <real commit hash>
```

---

## 10. Export to public-data

This is the **only** step that puts anything on the public internet. It is
deliberately separated from agent work. Agents should not run it
unattended.

### Command (three real projects)

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

The CLI prints a redaction summary at the end:

```
redaction summary: FAIL=0, WARN=0
```

- `FAIL=0` is required. If you see `FAIL=1`, the export did **not** write
  anything to `public-data/`. Find the offending field (the CLI lists
  which), rewrite it, and re-run.
- `WARN` is informational. A common warn is a user-home path inside a
  long summary; review it and decide whether the path is real or fictional.

### What to check after a successful export

1. `public-data/registry/projects.yml` — `repo` fields point at the **real**
   source repos. No homepage sub-paths masquerading as standalone projects.
2. `public-data/MANIFEST.json` — `project_filter`, `event_count`,
   `max_events_per_project` look right.
3. `public-data/events/*.json` — the latest event per project is the one
   you expect to see on the dashboard. No stale "current phase" events.
4. `grep -RE "HP-33|conanxin-homepage" public-data/projects/<id>/` should
   return nothing for projects whose current state has nothing to do with
   the homepage case studies.

### What does **not** go into public-data

- Anything from `data/` that wasn't filtered into a project's events list.
- Local agent home paths (`/home/<user>/...`), real IPs, real tokens.
- `generated/index.json` is a build artifact, not a data source. It is
  regenerated from `public-data/` after export, not the other way round.

---

## 11. Cloudflare Pages publish & verification

```bash
# 1. Commit the regenerated public-data
git add public-data/registry/projects.yml \
        public-data/registry/agents.yml \
        public-data/MANIFEST.json \
        public-data/events/<new event file>
git status --short   # review before commit
git commit -m "ACT-X: <what changed in public-data>"

# 2. Push
git push   # never --force, never to master

# 3. Wait for Cloudflare Pages auto-deploy
#    Build is typically <30s. CDN cache lag is 60–90s on the custom domain.

# 4. Verify online
curl -L https://control-tower.conanxin.com/ \
  | grep -E "agent-project-control-tower|Artvee|BookTrans|projects|events" -n

curl -L https://control-tower.conanxin.com/projects/booktrans-desk/ \
  | grep -E "BookTrans|S13|16f38b6|PARTIAL|conanxin/booktrans-desk" -n

curl -L https://control-tower.conanxin.com/timeline/ \
  | grep -E "BookTrans|S13|16f38b6" -n

# 5. Sensitive-pattern scan
grep -RInE "token=|api_key=|Authorization:|Bearer |password=|secret=|[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" \
  public-data/ || true
```

Acceptance:

- All four URLs return HTTP 200.
- BookTrans Desk page shows `conanxin/booktrans-desk`, `S13`,
  `16f38b6`, `PARTIAL`.
- The grep at step 5 returns nothing (or only intentional placeholder
  text like `<YOUR_TOKEN>`).

---

## 12. Common errors and how to avoid them

These are the errors that have actually cost us time. Treat them as a
checklist, not as a theoretical list.

### 12.1 Mis-attributing a project to a case-study page

- **Symptom**: a project's public `repo` is the homepage repo (or a
  sub-directory of it), and the public `current phase` is some
  "Final Public Launch QA" or "shipped on conanxin.com" event.
- **Cause**: the agent that registered the project looked at the
  case-study page, not at the project's own repo.
- **Fix**: edit `data/registry/projects.yml` to point `repo` at the
  project's real GitHub repo, delete the mis-attributed events from
  `data/events/` and `public-data/events/`, and re-export. Use
  `status=PARTIAL/amber` if manual checks are still pending.

### 12.2 Writing `PASS` when the body says "still pending"

- **Symptom**: status is PASS/green, but the summary or `next` line
  mentions "click-through pending", "manual validation", "awaiting
  human review", or "BLOCKED_MANUAL".
- **Cause**: agent auto-completes the call without reading the report.
- **Fix**: re-run `report-phase` with `status=PARTIAL` and `health=amber`.
  Delete the wrong PASS event from `data/events/` and `public-data/events/`
  before re-exporting.

### 12.3 Stale public-data event file

- **Symptom**: dashboard shows an old phase as "current", even though a
  newer event exists in `data/events/`.
- **Cause**: the agent wrote the new event into `data/` but did not
  re-run the export, **or** the export used a project filter that
  excluded the new event.
- **Fix**: re-run the three-project `export_public_data.py` command with
  `--replace` and the explicit `--project-id` list.

### 12.4 Forgot to push

- **Symptom**: local `git status` is clean, online dashboard still shows
  the previous commit's state.
- **Cause**: `git commit` succeeded but `git push` was forgotten (or
  failed silently).
- **Fix**: `git push`, wait 60–90s, re-curl.

### 12.5 Local `generated/index.json` correct, online stale

- **Symptom**: the local file shows the new state; the online dashboard
  still shows the old state even after `git push`.
- **Cause**: Cloudflare Pages' CDN caches the homepage at the edge for
  ~60–90s. The `pages.dev` mirror also lags.
- **Fix**: wait 60–90s, then re-curl. Verify on multiple paths
  (`/`, `/projects/<id>/`, `/timeline/`) before concluding the deploy
  failed. Do not panic-revert during this window.

### 12.6 Cloudflare deploy "succeeded" but dashboard still serves an old build

- **Symptom**: Cloudflare Pages shows the latest commit as deployed, but
  the served HTML still references old assets.
- **Cause**: same CDN cache lag as 12.5, compounded by the `_astro/`
  hashed asset filenames. The HTML may be fresh while a referenced JS
  chunk is cached.
- **Fix**: wait, then re-curl. If it persists >5 min, check
  `https://<project>.pages.dev/` (the `pages.dev` mirror) to see whether
  the origin is fresh and only the custom-domain edge is lagging.

### 12.7 `data/` accidentally committed

- **Symptom**: a `git log -- data/` shows commit history that should not
  exist.
- **Cause**: someone ran `git add .`, or someone deleted the `data/`
  entry from `.gitignore`.
- **Fix**: this is an information leak. Treat it as an incident.
  Coordinate with the project owner before re-writing history. Going
  forward, list files explicitly and never `git add .`.

---

## 13. What to read next

- New machine or new agent persona? → `docs/MULTI_MACHINE_SETUP.md`
- Public dashboard / data export questions? → `docs/PUBLIC_DATA_EXPORT_PLAYBOOK.md`
- Day-to-day event reporting? → `templates/telegram/*.txt` (copy-paste
  into Telegram to command an agent)
- Pre-deploy review? → `templates/checklists/preflight-checklist.md`
  and `templates/checklists/online-verification-checklist.md`
- Re-checking privacy before commit? → `templates/checklists/redaction-checklist.md`
- Reviewing a public-data change before push? →
  `templates/checklists/public-data-review-checklist.md`

---

## 14. Command Generator (ACT-7B)

This is the ACT-7B answer to the two real failure modes that the
ACT-8 multi-agent trial (commit `f8543d3`) hit:

1. **Hand-written long multi-line `\` continuations.** Bash collapses
   them into a single argument; argparse rejects the call. The
   generator emits exactly one line, no continuations.
2. **Template ↔ CLI drift.** Older drafts of
   `templates/telegram/report-review.txt` listed
   `--source-repo` / `--design-reason`, which tower.py does not
   accept on `report-review`. Older `report-handoff.txt` listed
   `--agent-id` and `--to-agent`, which tower.py does not accept
   on `report-handoff` either. The checker
   (`scripts/check_template_cli_alignment.py`) catches the class
   of bug, not just the known instances.

### 14.1 What the generator does

`scripts/generate_tower_command.py` is a **single-line command
printer**. It has no `--execute` flag, by design:

- It reads a hard-coded **schema** for every tower.py subcommand
  (and the `export_public_data.py` subcommand). The schema is the
  same dict that `check_template_cli_alignment.py` reads — single
  source of truth.
- You pass flags. Any flag not in the schema → hard FAIL with a
  list of the flags that **are** allowed for that subcommand.
- Missing required flags → FAIL with a list of what's missing.
- String values with whitespace, quote characters, or shell
  metacharacters are wrapped via `shlex.quote`, so the printed
  command is always one safe line, no matter what you put in the
  values.
- The output is printed to stdout, **never** executed. The
  generator does not touch `data/`, `public-data/`, or `generated/`.
  It does not run `git`. It does not push. It does not export.

### 14.2 What the alignment checker does

`scripts/check_template_cli_alignment.py`:

- Reads every `templates/telegram/*.txt`.
- For each template's `Command:` block, identifies the leading
  subcommand and cross-checks every `--flag` it finds against the
  schema.
- Exits 0 if all real `Command:` blocks use only allowed flags.
- Exits 1 with a list of drift issues otherwise.
- Also enforces a few static rules (no `git add .` anywhere).

This is `make command-test`'s primary coverage. The smoke test
also includes a **drift-injection** test: it copies the real
templates to a temp dir, poisons `report-review.txt` with a
forbidden `--source-repo`, and verifies the checker refuses to
pass. This proves the checker is doing real work, not always
returning 0.

### 14.3 Three reports — using the generator

**Report a phase** (BookTrans Desk S13 — real example):

```bash
python scripts/generate_tower_command.py report-phase \
  --project-id booktrans-desk \
  --agent-id local-hermes \
  --phase-id S13 \
  --phase-name "Blocker Fixes and Manual Validation Rerun" \
  --status PARTIAL --health amber \
  --summary "S13 blocker fixes complete; automated checks PASS, but EPUB/PDF click-through is BLOCKED_MANUAL." \
  --source-repo conanxin/booktrans-desk --source-commit 16f38b6 \
  --next "Schedule real-user click-through before S14."
```

The generator prints **one** line. Copy it. Paste it. Run it.

**Report a review** (the ACT-8 cloud-openclaw trial review — real
example):

```bash
python scripts/generate_tower_command.py report-review \
  --project-id agent-project-control-tower \
  --agent-id cloud-openclaw \
  --phase-id ACT-8-review \
  --phase-name "ACT-7 Playbook Review by Second Agent" \
  --status PASS \
  --summary "Reviewed ACT-7 playbooks and verified the onboarding flow." \
  --target-agent-id local-hermes \
  --target-phase-id ACT-7 \
  --target-commit 76fa50d \
  --next "Feed documentation gaps back into ACT-8 report."
```

If you accidentally pass `--source-repo` here, the generator
refuses to print anything. The CLI does not accept that flag on
`report-review` and argparse would have rejected your call
mid-execution. ACT-7B catches it **before** you run anything.

**Export to public-data** (the three real projects):

```bash
python scripts/generate_tower_command.py export-public-data \
  --source data --output public-data \
  --project-id agent-project-control-tower \
  --project-id artvee-gallery \
  --project-id booktrans-desk \
  --replace
```

The generator emits the equivalent `python scripts/export_public_data.py ...`
single-line command. The **double-gate** still applies: the
generator does not change who is allowed to run the printed
command. Trial agents do not run export — that is for the human
reviewer (or the explicitly authorized exporter agent). See
`docs/PUBLIC_DATA_EXPORT_PLAYBOOK.md` for the full rule.

### 14.4 Other subcommands

The generator also covers:

- `register-agent`
- `register-project`
- `report-failure`
- `report-handoff`
- `report-release`

For all of them, use the same pattern: pass flags, copy the
printed line, paste it into the shell.

### 14.5 When to use the generator vs. write a single line manually

- **Use the generator** when the command has more than 3 flags, or
  when one of the values contains a space, apostrophe, or shell
  metacharacter. The generator saves you from quoting bugs.
- **Write a single line manually** when the command is short and
  the values are simple (kebab-case ids, plain status, plain
  commit hashes). The template's "manual" section is fine.
- **Never** use `\` continuations. The whole point of the
  generator is that bash collapses them and breaks the call.
  ACT-8 caught this; ACT-7B encoded the lesson.

### 14.6 Multi-machine and Telegram use

When `local-hermes` is sending a command to a different machine
(e.g. `cloud-openclaw` over SSH or via Telegram):

1. `local-hermes` runs the generator locally and reads stdout.
2. `local-hermes` sends the **single line** to the other agent.
3. The other agent pastes it into a shell, runs it.
4. The other agent returns only the event file or a short
   summary, never the raw command output.
5. `local-hermes` reviews the event and (if human is in the loop)
   runs the export.

This is the recommended flow documented in
`docs/MULTI_MACHINE_SETUP.md` §4. The generator is what makes
the cross-machine handoff safe: the printable command is the
contract between `local-hermes` and the remote agent.

### 14.7 What the generator is NOT

- It is **not** a wizard. It will not invent flags for you.
  Anything you do not pass is omitted.
- It is **not** an execution engine. There is no `--execute`
  flag, and there never will be.
- It is **not** a template renderer. Templates remain literal
  for human copy-paste; the generator is a parallel path for
  agents that need machine-precise commands.
- It is **not** a public-data authorization. The double-gate
  rule still applies. See
  `docs/PUBLIC_DATA_EXPORT_PLAYBOOK.md` §11.

### 14.8 Run the alignment check yourself

```bash
make command-test
# or, for just the alignment check:
python scripts/check_template_cli_alignment.py
```

The command is fast (< 1 second) and depends only on Python
stdlib plus the templates on disk. It is safe to add to any
pre-commit hook.
