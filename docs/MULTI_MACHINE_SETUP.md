# Multi-machine Setup

> How to bring a second machine — or a second agent on the same machine —
> into the Agent Project Control Tower without stepping on anyone else's
> work. The key insight: the **project is not registered to a machine**;
> it is registered to the tower. Any agent on any machine can advance it.

---

## 1. The mental model

```
              ┌────────────────────────────────────────┐
              │  Agent Project Control Tower (repo)    │
              │  https://github.com/conanxin/          │
              │  agent-project-control-tower           │
              └────────────────────────────────────────┘
                       ▲           ▲           ▲
                       │           │           │
              git pull │  │ pull   │  │ pull   │
                       │           │           │
        ┌──────────────┴┐  ┌───────┴──────┐  ┌─┴────────────┐
        │ local-hermes  │  │ local-codex  │  │ cloud-openclaw│
        │ (notebook,    │  │ (notebook,   │  │ (VPS,         │
        │  primary)     │  │  secondary)  │  │  unattended)  │
        └───────────────┘  └──────────────┘  └───────────────┘
            writes to           writes to          writes to
            data/events/        data/events/       data/events/
            (its own files)     (its own files)    (its own files)
```

- A **project** lives in the tower, not in any machine.
- A **machine** is one or more **agents** running on the same hardware.
- An **agent** has a stable `agent_id`, a `machine` tag, a `role`, and an
  `operator`. Once registered, never renamed.
- A **phase event** is always `(project_id, agent_id, phase_id)`. The
  agent_id tells you who did the work; the phase_id tells you what stage
  it is at.

---

## 2. Agent personas we already have

| `agent_id` | `machine` | `role` | When to use |
| --- | --- | --- | --- |
| `local-hermes` | `local` | `primary-coding-agent` (notebook) | the default for the human's primary coding session |
| `local-codex` | `local` | `secondary-coding-agent` (notebook) | for work the user delegates to a Codex/Claude session on the same machine |
| `cloud-openclaw` | `cloud` | `unattended-agent` (VPS) | for the cloud-side agent that does scheduled work |

The exact tags are not load-bearing — they appear in the registry and the
timeline. Pick a tag that is **not** a real hostname or IP, and is
**stable** so future grep on the timeline still works.

---

## 3. Naming conventions for new agents

| Field | Format | Examples | Anti-examples |
| --- | --- | --- | --- |
| `agent_id` | kebab-case, immutable | `local-hermes`, `cloud-openclaw`, `local-claude` | `hermes-v2`, `agent_1`, `MyLaptop` |
| `name` | free text | "Local Hermes (notebook)" | "John's MacBook Pro" |
| `machine` | de-sanitized tag | `local`, `local-wsl`, `cloud-vps`, `cloud-railway` | `conanxin-notebook`, `192.168.1.10` |
| `role` | free text | `primary-coding-agent`, `reviewer`, `telegram-bridge`, `unattended` | "the one that broke prod" |
| `operator` | handle, not real name/email | `xin`, `conanxin` | `John Smith <john@example.com>` |

The reason: `machine` and `operator` end up in `public-data/` and the
dashboard. A hostname leaks your network; a real name+email is PII. Tags
do neither.

---

## 4. Scenarios

### 4.1 First agent on a new machine

```bash
# On the new machine
git clone https://github.com/conanxin/agent-project-control-tower.git
cd agent-project-control-tower

# Bootstrap local data/ (gitignored; fresh clone has none).
# Pick ONE:
#   (a) start from curated examples/ seed:
#         python scripts/tower.py seed --force
#   (b) start clean — register your agent and project next.
# ACT-8 trial: without this step, `make all` fails at validate
# with "source dir missing: .../data".

# Fix the python / python3 mismatch on Debian / Ubuntu:
#   tests/smoke.py hardcodes the literal `python`; if the box only has
#   python3, `make test` will fail with FileNotFoundError.
#   ACT-8 trial surfaced this. Add a symlink once per machine:
sudo ln -sf /usr/bin/python3 /usr/local/bin/python
# (or, on a box you cannot sudo, do it under ~/.local/bin and add
#  ~/.local/bin to PATH; the goal is "python" must resolve to a
#  Python 3.10+ interpreter).

# Sanity check
python scripts/tower.py validate     # OVERALL: PASS
make all                            # CLI SMOKE TEST PASSED

# Register yourself ONCE
python scripts/tower.py register-agent \
  --agent-id <NEW_AGENT_ID> \
  --name "<display name>" \
  --machine "<machine-tag>" \
  --role "<role>" \
  --operator "<handle>"

# You're done. From now on, only report-* commands.
```

> **Note on `make publish-preflight`.** It is opt-in and is **not** part
> of `make all`. Do not run it during onboarding. Only the human
> reviewer (or a designated "exporter" agent) runs it, and only when
> there is a real `public-data/` change to ship. ACT-8 trial hit the
> assumption that publish-preflight is part of preflight; it is not.

### 4.2 A second agent persona on the same machine

Same as 4.1, but with a new `--agent-id` and the same `--machine` tag.
There is no need to re-clone. The two agents write to `data/events/`
side-by-side; their timestamped filenames never collide.

### 4.3 A cloud-side agent on a VPS

Same as 4.1, but tag `--machine cloud` (or `cloud-<provider>`) and
`--role unattended-agent`. The VPS-side agent typically:
- registers itself;
- runs scheduled work via cron;
- writes `data/events/*.json` via `tower.py report-phase` etc.;
- never runs the public-data export;
- never pushes to GitHub (a human or a designated "exporter" agent does).

### 4.4 Two machines both editing `data/`

This is the dangerous one. `data/` is **not** in git, so two machines
each have their own private copy of it. They do **not** merge
automatically. The safe pattern is:

- One machine at a time owns the active `data/` directory.
- Other machines read-only the tower repo; they only `git pull` and
  `python scripts/tower.py validate` for context.
- When an agent on machine B has new events, machine B commits and
  pushes them; the human (or a designated merge agent) on machine A
  pulls and re-validates.

In the future we may add a per-agent sub-directory under `data/` so each
agent commits only its own slice. That is **out of scope** for ACT-7.

### 4.5 Push rejected on a multi-machine checkout

```text
! [rejected]        main -> main (non-fast-forward)
```

Cause: another machine (or another agent) pushed while you were
preparing yours. **Do not force-push.** Do not push to a feature branch
and then merge. Instead:

```bash
git fetch origin
git rebase origin/main    # if your local commits are linear
# or
git merge --no-ff origin/main  # if you prefer merge commits

# If a merge conflict appears inside public-data/registry/projects.yml,
# resolve it by hand: usually the conflict is "both sides added the same
# field" and the resolution is "keep both". Then re-validate:
python scripts/tower.py validate
make all

# Now push normally
git push
```

If you rebase and your local commit history changes (commit hashes
change), the events you already pushed (e.g. S13 with source_commit
`16f38b6`) still point at the **real** BookTrans Desk commit, which is
unaffected. The control tower's events are not keyed by tower commit
hashes, so this is safe.

---

## 5. The "who can do what" matrix

| Action | Allowed from | Notes |
| --- | --- | --- |
| `git clone` the tower | any machine | read-only access to the registry, the public dataset, and the embedded HTML |
| `python scripts/tower.py validate` | any machine | zero side effects |
| `python scripts/tower.py register-agent` | any agent on any machine | one-time, idempotent |
| `python scripts/tower.py register-project` | the first agent that touches a project | idempotent on `project_id` |
| `python scripts/tower.py report-phase` (etc.) | any agent on any machine | writes to `data/events/` on **that** machine |
| `python scripts/export_public_data.py` | only the human reviewer (or a designated "exporter" agent) | this is the gate to the public internet |
| `git add public-data/` and `git commit` | only the human reviewer | this is the second gate |
| `git push` to `main` | only the human reviewer (or CI) | never `--force`, never to `master` |
| read the public dashboard | the whole world | https://control-tower.conanxin.com/ |

**Two-gate model:** the agent that writes events **cannot** push public
data. The human (or a designated exporter) **can**. This is the simplest
separation of concerns that keeps `data/` private and `public-data/`
audited.

---

## 6. Avoid the git-conflict footguns

Most multi-machine pain is `git push` failing because of a non-fast-
forward. The rules below are designed to make that rare.

1. **Always `git pull --ff-only` before editing.** If you can't fast-
   forward, your local history diverged. Resolve it before writing new
   events.
2. **Don't rebase a commit that has already been pushed.** Rebasing
   rewrites commit hashes, which is fine for the local repo but breaks
   anyone who has already pulled.
3. **Don't `git add .` in the tower repo.** List files explicitly. The
   `.gitignore` for this repo is opinionated: `data/`, `generated/`,
   `site/dist/`, `apps/dashboard/dist/` are all gitignored. Accidentally
   adding one of them is an information leak.
4. **Don't push to `master`.** The main branch is `main`. A `master`
   branch would orphan the public deployment.
5. **Tag your agent's commits in the message.** Convention: start every
   commit message with `ACT-N:` or `HOTFIX-N:` (or `booktrans-desk:`
   for project-scoped commits). This makes `git log --oneline` self-
   documenting across many agents.

---

## 7. The handoff event (for cross-agent work)

When agent A passes a project to agent B (because A is being shut down,
or B has the right context), emit a HANDOFF event from A:

```bash
python scripts/tower.py report-handoff \
  --project-id <PROJECT_ID> \
  --agent-id <FROM_AGENT_ID> \
  --to-agent <TO_AGENT_ID> \
  --reason "<short reason>" \
  --source-repo "<owner>/<repo>" \
  --source-commit <real commit hash>
```

This creates a permanent record in the timeline: "this project moved
from A to B on date X because of Y." Future readers (human or agent)
can reconstruct the chain of custody.

---

## 8. If a project has multiple agents working on it

That is fine. The tower was designed for it. The model is:

- A project is registered once. Its `primary_agent` field is a
  **suggestion** of who is most often on it, not a lock.
- Multiple agents can emit events for the same project. The timeline
  shows who did what when.
- The "current phase" is whichever event is **latest by `created_at`**
  for that project. It is not weighted by `agent_id`.

If two agents emit events for the same phase at almost the same time,
the later one wins. If you want to be safe, do not start a new phase
while another agent is mid-work on the same project. If you must, emit
`status=SKIPPED` for the older one before emitting your new one.

---

## 9. How to onboard a brand-new machine in 10 minutes

```bash
# 0. Prerequisites: Python 3.10+, Node 18+ (for dashboard), git, make

# 1. Clone
git clone https://github.com/conanxin/agent-project-control-tower.git
cd agent-project-control-tower

# 2. Verify
python scripts/tower.py validate
make all

# 3. Pick a stable agent_id (e.g. cloud-railway-1, local-mac-m2, ...)
#    and a de-sanitized machine tag (cloud, local, local-wsl, ...)

# 4. Register yourself
python scripts/tower.py register-agent \
  --agent-id <NEW_AGENT_ID> \
  --name "<display name>" \
  --machine "<machine-tag>" \
  --role "<role>" \
  --operator "<handle>"

# 5. You are now an active agent in the tower.
#    Pull regularly:
git pull --ff-only
#    When you finish work, run one of the report-* commands from
#    docs/AGENT_USAGE_PLAYBOOK.md.
#    When the human reviewer asks, they will run the public-data
#    export and push. You do not push public-data.
```

That's it. The only thing you should not do is push to `main` with
`public-data/` changes that you did not personally review.

---

## 10. What to read next

- Want the full event-reporting reference? → `docs/AGENT_USAGE_PLAYBOOK.md`
- Want the public-data export details? → `docs/PUBLIC_DATA_EXPORT_PLAYBOOK.md`
- Want a copy-pasteable command for the next agent? → `templates/telegram/`
- Want a pre-push review checklist? → `templates/checklists/`

---

## 11. Cross-machine command flow (ACT-7B)

ACT-8 trial (commit `f8543d3`) found that the cross-machine handoff
of `tower.py` commands is fragile in three concrete ways:

1. **Multi-line bash continuations break.** Sending a long
   `python scripts/tower.py report-phase \\\n  --project-id ...`
   block over SSH or Telegram, then having the remote shell
   collapse it into one argument. The CLI rejects the call.
2. **Hand-written commands drift from the CLI surface.** Templates
   that list `--source-repo` on `report-review` (which argparse
   rejects) made it into trial agents' actual runs.
3. **Trial agents tried to send back raw command output, leaking
   token-shaped strings or paths.** Output was not always
   pre-filtered for secrets.

ACT-7B fixes the first two. ACT-8's `cloud-openclaw` trial is the
template; ACT-8B (next) will rerun it with the new generator to
prove the fixes work end-to-end.

### 11.1 Why the generator

`scripts/generate_tower_command.py`:

- Emits exactly **one line** of output. There are no `\\\n`
  continuations to send or to mis-paste.
- Refuses to print a command that includes a flag the CLI does
  not accept for that subcommand. Catches drift before the remote
  agent runs anything.
- Quotes values with `shlex.quote`. Apostrophes, spaces, dollar
  signs, and ampersands survive one round of bash parsing.
- Does not execute. Does not touch `data/`, `public-data/`, or
  `generated/`. The remote agent runs the printed command
  itself; the privilege boundary is unchanged.

### 11.2 Recommended flow (local → remote)

When `local-hermes` needs a remote agent (e.g. `cloud-openclaw`)
to run a `tower.py` command:

1. **`local-hermes` generates the command locally:**

   ```bash
   python scripts/generate_tower_command.py report-review \
     --project-id agent-project-control-tower \
     --agent-id cloud-openclaw \
     --phase-id ACT-8B-review \
     --phase-name "ACT-7B Generator Re-test" \
     --status PASS \
     --summary "Re-tested the command generator end-to-end." \
     --target-agent-id local-hermes \
     --target-phase-id ACT-7B \
     --next "Confirm pipeline still green."
   ```

   The output is one line. Copy it.

2. **`local-hermes` sends the single line** to `cloud-openclaw`
   over SSH or via Telegram. Do not paste multi-line shell
   scripts. Do not paste bash heredocs that span messages.

3. **`cloud-openclaw` pastes the line into a shell and runs it.**
   It returns the tower.py exit code, a short summary, and
   (optionally) the path of the new event file in `data/events/`.
   It does **not** return raw `tower.py` output that might
   contain redaction noise.

4. **`local-hermes` reviews the event file** (path: `data/events/`).
   `local-hermes` then runs the public-data export itself, with
   human review, per the double-gate rule.

5. **`local-hermes` commits and pushes the public-data change**
   if and only if the redaction summary is `FAIL=0`. The remote
   agent never pushes `public-data/`.

### 11.3 If you must send a multi-line command

Three options, in order of preference:

1. **Generate it.** Even for a 10-flag command, the generator
   keeps it on one line. This is almost always the right answer.
2. **Write a small shell script file**, then send the
   `bash ./do-it.sh` line. The remote agent writes the script
   to a temp file with a here-doc (allowed), then runs it.
3. **Write a here-doc directly to a file**, then run the file:

   ```bash
   cat > /tmp/tower-cmd.sh <<'EOF'
   python scripts/tower.py report-phase --project-id p ...
   EOF
   bash /tmp/tower-cmd.sh
   ```

   The single-quoted `<<'EOF'` is important — it prevents the
   local shell from expanding variables before the script even
   reaches the remote machine.

**Do not** chain with `&&` and `\`-continuations to fake
"multi-line in one paste". ACT-8 trial agents tried that. The
shells joined the lines into one argument and the CLI rejected
the call. The generator is the fix; everything else is a
workaround.

### 11.4 The handoff event itself

If `local-hermes` is passing a project to `cloud-openclaw`
(permanent transfer, not just one command), use the handoff
template — `templates/telegram/report-handoff.txt`. The
generator covers it: `report-handoff` is a first-class
subcommand.

`report-handoff` flags are **different from `report-phase`**.
Do not copy a `report-phase` command and assume it works for
handoff. The checker (`scripts/check_template_cli_alignment.py`)
specifically catches the old bug where `report-handoff.txt`
listed `--agent-id` and `--to-agent` instead of the real
`--from-agent-id` / `--to-agent-id`.

### 11.5 What the remote agent returns

Recommended: **only the event file path** (or the JSONL line),
nothing else. Example:

```json
{"path": "data/events/20260612T001500Z__REVIEW__cloud-openclaw__agent-project-control-tower__ACT-8B-review.json", "exit": 0}
```

`local-hermes` then:

- `cat data/events/20260612T001500Z__REVIEW__...json | jq .`
- if redaction `FAIL=0`, continue
- if redaction `FAIL>0`, fix the source summary and have the
  remote agent re-emit

The remote agent does **not**:

- Run `export_public_data.py`. (The double-gate rule.)
- Run `git add`, `git commit`, or `git push`. (Local review
  only.)
- Paste raw `tower.py` stdout into Telegram. (Could leak.)
