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
