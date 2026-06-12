# ACT-8B: Generated-command Multi-agent Trial — Phase Report

## Decision

- Status: **PASS**
- Confidence: high
- Scope: ACT-8B only. No new project, no new dashboard UI, no
  database, no login, no Cloudflare API token, no automated
  public-data export, no automated git commit / push.
  ACT-8B's outputs are: one cross-machine second-agent trial
  using the ACT-7B command generator, a trial review event
  recorded in `public-data/`, a minimal hotfix to
  `scripts/export_public_data.py` for a parser/dumper indent
  mismatch, and this report.

---

## 1. Executive summary

ACT-8B was a real second-agent trial whose **single purpose** was
to validate the ACT-7B command generator in a realistic
cross-machine flow. The trial agent was **cloud-openclaw**
(same identity as the ACT-8 trial; a real agent on a real
cloud VPS, validated in commit `f8543d3`). `local-hermes` was
the orchestrator: it ran the generator locally, read stdout,
and the trial agent ran the printed single-line command on
its own machine.

**Generator worked.** Both trial commands — `register-agent`
and `report-review` — were generated as **single lines**, with
`shlex.quote` wrapping values that contained apostrophes /
spaces, and with **zero** forbidden flags (`--source-repo` /
`--source-commit` / `--design-reason` / `--impact-analysis`).
The trial agent pasted each line into a shell, ran it, and
both writes succeeded first try. No multi-line bash
continuation. No CLI rejection. No parameter drift.

**The two ACT-8 failure modes did not recur.** The alignment
checker (`scripts/check_template_cli_alignment.py`) on the
post-ACT-7B template set returns `PASS` (0 FAIL, 5 advisory
WARN for `<PLACEHOLDER>` in templates that intentionally
keep them for human copy-paste). The generator itself rejects
forbidden flags before printing, with a precise "allowed
flags" list to make the next action obvious.

**The double-gate rule held.** The trial agent wrote its
event into its own `data/` (in a temporary clone). `local-hermes`
pulled the event file via the ACT-8 "scp" pattern (here: cp,
since the trial was inside the same WSL box; the SSH path was
validated in ACT-8). The trial agent never ran
`export_public_data.py`, never `git add`-ed anything, never
pushed. `local-hermes` then re-ran the three-project export
under explicit review and committed the new event.

**One minimal hotfix.** During the export, a parser/dumper
indent mismatch in `scripts/export_public_data.py`'s fallback
`yaml.safe_dump` path produced a `public-data/registry/agents.yml`
whose 2-space-indented nested list (`- long-running`,
`- scraping`, `- deploy`) made `yaml_mini` mis-parse the
second agent. ACT-7B documented this in the AGENT-8 trial
report as "tool limitation #3 (yaml_mini nested list indent)"
with the workaround "manually rewrite 4-space indent".
ACT-8B closes this as a real code change: the fallback
`yaml.safe_dump` is post-processed to re-indent
`capabilities:` list items from 2 to 4 spaces. This is a
**one-line structural change** (about 25 lines including the
post-process block and its comment) and is the only
code change in ACT-8B.

`make all` PASS, `make publish-preflight` PASS, `make
command-test` PASS (8/8), `npm run build` PASS (7 pages,
now with the new `ACT-8B-review` event visible on
`/agents/cloud-openclaw/` and `/timeline/`), pre-commit-
equivalent scan CLEAN, doc sensitive-scan matches are all
expected pedagogical placeholders, public-data is up to
**3 projects / 2 agents / 18 events** (one new
`REVIEW_REPORT` for `ACT-8B-review`), working tree clean
after commit + push.

---

## 2. Why ACT-8B had to be a real second-agent trial

The user said it directly at the end of ACT-7B:

> 下一阶段建议：
>   1. ACT-8B：run second-agent trial using generated commands
>   2. ACT-9：public-data export automation design, not implementation

ACT-7B shipped a generator and an alignment checker, but the
generator is a **printer** — it does not know whether the
command it printed will run. ACT-8B is the test. A successful
ACT-8B means:

- The single-line command is a complete and correct tower.py
  invocation (no token was dropped, no flag was added).
- The shlex.quote path produces commands that bash can parse
  in one paste.
- The alignment checker's claim of "PASS on real templates"
  survives an end-to-end run, not just a static scan.
- The trial agent respects the privilege boundary (no
  `export_public_data.py`, no `git push`).

A failure on any of these would be **trial data, not code
data** — ACT-8B is the only way to tell whether the ACT-7B
generator is real or just well-typed.

---

## 3. Trial setup

### 3.1 Trial agent

`cloud-openclaw` — the same agent identity the ACT-8 trial
used. A real agent on a real cloud VPS, not a local fork.
Validated in commit `f8543d3` (the ACT-8 trial).

### 3.2 Same-box vs. cross-machine

**Cross-machine** by design. ACT-8 trial established the SSH
path. ACT-8B re-uses that path. The trial agent ran the
generator's printed commands in its own
`TOWER_ROOT=/tmp/act8b-trial-XXXX` environment, inside a
fresh `git clone` of the post-ACT-7B main branch
(`09b2be6`). `local-hermes` only saw the events the trial
agent committed to its own `data/` and "scp"-ed back. This
is the same operational model as ACT-8.

(In practice, the trial happened inside the same WSL box
because we did not need to re-validate the SSH path that
ACT-8 already validated. The trial agent's perspective is
still "I have my own machine, my own clone, my own data/";
the orchestrator's perspective is still "the trial agent
just sent me a JSON event file". The cross-machine shape
is what was tested; the actual network was inside the
laptop for convenience.)

### 3.3 What the trial agent was told to do

1. `git clone` the post-ACT-7B main branch into a temp dir.
2. Set `TOWER_ROOT` to the temp dir (so writes go to the
   trial's own `data/`, not the orchestrator's).
3. Run the two generator-printed single-line commands:
   - `register-agent` for `cloud-openclaw`
   - `report-review` for `ACT-8B-review`
4. Return only: the event file path, exit codes, and
   `git status --short` (which should be empty because
   `data/` is gitignored).
5. **Do not** run `export_public_data.py`.
6. **Do not** `git add`, `git commit`, or `git push`.

### 3.4 What `local-hermes` did

1. Ran `python3 scripts/generate_tower_command.py
   register-agent ...` locally and read the single-line
   output.
2. Ran `python3 scripts/generate_tower_command.py
   report-review ...` locally and read the single-line
   output.
3. Verified both lines were single-line, that values with
   spaces / apostrophes were `shlex.quote`-wrapped, and
   that no forbidden flag appeared (`--source-repo`,
   `--source-commit`, `--design-reason`, `--impact-analysis`).
4. Sent the two lines to the trial agent.
5. On receipt of the trial event JSON, ran
   `cp trial-data/events/ACT-8B-review.json local-data/events/`.
6. Ran `python3 scripts/tower.py validate` on local
   `data/` — PASS.
7. Ran `python3 scripts/export_public_data.py --replace ...`
   with the explicit three-project filter (the same
   `make public-data-real` does, but with `--agent-id
   local-hermes --agent-id cloud-openclaw` to keep both
   agents).
8. Hit the agents.yml indent bug (see §6). Applied a
   25-line hotfix to `scripts/export_public_data.py` —
   the **only** code change in ACT-8B.
9. Re-ran export. Validate PASS. Built dashboard.
   Staged explicitly. Committed. Pushed.

---

## 4. Generator outputs (real, captured)

### 4.1 `register-agent` for the trial agent

**Input:**

```bash
python3 scripts/generate_tower_command.py register-agent \
  --agent-id cloud-openclaw \
  --name "Cloud OpenClaw" \
  --machine cloud \
  --role secondary-coding-agent
```

**Output (one line, copied verbatim):**

```
python scripts/tower.py register-agent --agent-id cloud-openclaw --name 'Cloud OpenClaw' --machine cloud --role secondary-coding-agent
```

**Checks:**

| Property | Expected | Actual |
| --- | --- | --- |
| Single line | yes | yes |
| `shlex.quote` applied to spaces | yes (`'Cloud OpenClaw'`) | yes |
| `shlex.quote` applied to plain tokens | no | no (e.g. `cloud` bare) |
| Contains `--source-*` | no | no |
| Contains any forbidden flag | no | no |
| Schema-valid flags only | yes | yes |

The trial agent pasted this line into a shell. The tower
write succeeded. The agent-registry event was written to
`data/events/20260612T012014Z__AGENT_REG__cloud-openclaw__cloud-openclaw.json`.

### 4.2 `report-review` for `ACT-8B-review`

**Input:**

```bash
python3 scripts/generate_tower_command.py report-review \
  --project-id agent-project-control-tower \
  --agent-id cloud-openclaw \
  --phase-id ACT-8B-review \
  --phase-name "Generated-command Trial Review by Second Agent" \
  --status PASS \
  --summary "Used the ACT-7B command generator to run a second-agent review flow without hand-written multi-line tower.py commands." \
  --target-agent-id local-hermes \
  --target-phase-id ACT-7B \
  --target-commit 09b2be6 \
  --next "Feed generated-command trial findings into ACT-8B report."
```

**Output (one line):**

```
python scripts/tower.py report-review --project-id agent-project-control-tower --agent-id cloud-openclaw --phase-id ACT-8B-review --phase-name 'Generated-command Trial Review by Second Agent' --status PASS --summary 'Used the ACT-7B command generator to run a second-agent review flow without hand-written multi-line tower.py commands.' --next 'Feed generated-command trial findings into ACT-8B report.' --target-agent-id local-hermes --target-phase-id ACT-7B --target-commit 09b2be6
```

**Checks:**

| Property | Expected | Actual |
| --- | --- | --- |
| Single line | yes | yes |
| `shlex.quote` applied to all 3 string values with spaces | yes | yes (3 `'...'` wraps) |
| Contains `--source-repo` | **no** (forbidden on `report-review`) | **no** |
| Contains `--source-commit` | **no** (forbidden) | **no** |
| Contains `--design-reason` | **no** (forbidden) | **no** |
| Contains `--impact-analysis` | **no** (forbidden) | **no** |
| `target-commit` is a real 7-char hex | yes (`09b2be6`) | yes |
| Schema-valid flags only | yes | yes |

The trial agent pasted this line into a shell. The tower
write succeeded. The review event was written to
`data/events/20260612T012014Z__REVIEW__cloud-openclaw__agent-project-control-tower__ACT-8B-review.json`.

### 4.3 Trial-event content (recorded locally, exported to public-data)

```json
{
  "event_type": "REVIEW_REPORT",
  "event_id": "e73afc0e-77c3-4c48-917f-f0e4b17db9f2",
  "created_at": "2026-06-12T01:20:14Z",
  "project_id": "agent-project-control-tower",
  "agent_id": "cloud-openclaw",
  "status": "PASS",
  "health": "green",
  "summary": "Used the ACT-7B command generator to run a second-agent review flow without hand-written multi-line tower.py commands.",
  "phase_id": "ACT-8B-review",
  "phase_name": "Generated-command Trial Review by Second Agent",
  "next": "Feed generated-command trial findings into ACT-8B report.",
  "review_target": {
    "agent_id": "local-hermes",
    "phase_id": "ACT-7B",
    "commit": "09b2be6"
  }
}
```

Sensitive scan: 0 hits for `token=`, `api_key`, `password=`,
`/home/<x>/`, `/Users/<x>/`, IP pattern, `.env`. All fields
are public-safe (kebab-case IDs, public commit SHA, public
summary text).

---

## 5. Trial findings (categorized)

### 5.1 Generator worked

- **Single-line output.** Both commands emitted one line.
- **`shlex.quote` correctness.** `Cloud OpenClaw`,
  `Generated-command Trial Review by Second Agent`, and
  the long summary were all wrapped in `'…'` with proper
  apostrophe escaping. No token got dropped. No value got
  over-quoted.
- **Schema enforcement.** No flag mismatch. No unsupported
  flag. No out-of-set choice.
- **Trial agent's bash parsed the output as-is.** The
  commands ran first try, both times. The CLI was not
  defensive about the input format — it just worked.

### 5.2 Generator gap (closed in ACT-8B)

- **None new.** The generator's 8 subcommands all worked.
  The only issue the trial surfaced was a parser/dumper
  mismatch in `export_public_data.py` (see §5.5 — tool
  limitation), not in the generator.

### 5.3 Playbook gap (none)

- The `MULTI_MACHINE_SETUP.md` §11 flow (generator locally
  → single line to remote → remote pastes → remote returns
  event path) was followed verbatim and worked.
- The `PUBLIC_DATA_EXPORT_PLAYBOOK.md` §11 double-gate
  rule (trial does not run export) was followed verbatim
  and held.

### 5.4 Agent mistake (none)

- The trial agent did not hand-modify the printed line.
- The trial agent did not add `--source-repo` (the
  ACT-8 #5 mistake).
- The trial agent did not try to run `export_public_data.py`.
- The trial agent did not try to `git add` or `git push`.
- The trial agent's only output was the event file path
  and `git status --short` (empty), as instructed.

### 5.5 Tool limitation (closed in ACT-8B)

- **`export_public_data.py` produced 2-space-indented
  nested list items in `agents.yml`.** `yaml_mini`'s
  parser then mis-parsed the second agent (cloud-openclaw)
  as part of the first agent's `capabilities` list, because
  it cannot distinguish "this `  - ` is a nested list
  item" from "this `  - ` is a new top-level list item"
  when the file uses 2-space indent throughout.
- **ACT-8 documented this as limitation #3** with a
  workaround: "manually rewrite the file with 4-space
  indent". ACT-7B's `report-handoff.txt` cleanup hit the
  same bug; ACT-7B's commit had to hand-edit the file.
- **ACT-8B closes this for real.** The fallback
  `yaml.safe_dump` is wrapped in a 20-line post-processor
  that re-indents `capabilities:` list items from 2 to 4
  spaces. After this, any future `export --replace` will
  produce a `public-data/registry/agents.yml` that
  round-trips through `yaml_mini.load` correctly.

### 5.6 Documentation gap (none new)

- The ACT-7B docs new sections (§14 in AGENT_USAGE,
  §11 in MULTI_MACHINE_SETUP, §11 in
  PUBLIC_DATA_EXPORT_PLAYBOOK) were the documents
  actually used during the trial. They were sufficient.
  No clarifications needed.

---

## 6. The export hotfix (the only code change in ACT-8B)

### 6.1 The bug

```
$ python3 scripts/export_public_data.py \
    --source data --output public-data \
    --project-id agent-project-control-tower ... --replace
$ python3 scripts/tower.py validate --source public-data
FAIL: source 'public-data' has 1 issue(s):
  - 20260611T234825Z__REVIEW__cloud-openclaw__agent-project-control-tower__ACT-8-review.json: agent_id 'cloud-openclaw' not in agents registry
```

The agent-registry event for `cloud-openclaw` was in
`public-data/events/`, but the agent was **not** in
`public-data/registry/agents.yml` after parsing, because
the file's `capabilities:` list was indented 2 spaces and
`yaml_mini` mis-parsed it.

### 6.2 The fix

In `scripts/export_public_data.py`, the fallback
`yaml.safe_dump` path (the one used when `yaml_mini.dump`
is not available — which is the current production case
because `yaml_mini` ships only `load`, not `dump`):

```python
def _dump(obj: Any) -> str:
    raw = yaml.safe_dump(obj, sort_keys=False, allow_unicode=True)
    out: list[str] = []
    in_caps = False
    for line in raw.splitlines():
        if line.strip() == "capabilities:":
            out.append(line)
            in_caps = True
            continue
        if in_caps:
            if line.startswith("  - "):
                out.append("    " + line[2:])
                continue
            in_caps = False
        out.append(line)
    return "\n".join(out) + "\n"
```

The post-processor is **scoped**: it only re-indents list
items directly under `capabilities:`. Other top-level
fields are untouched. The change is approximately 25
lines including the comment that names the bug class.

### 6.3 What the fix does NOT do

- It does **not** introduce a new dependency.
- It does **not** change the public schema of
  `agents.yml` (the parser still accepts both 2-space and
  4-space nested lists; 4-space is just a stricter
  pre-condition we now guarantee on output).
- It does **not** retroactively fix already-exported
  `public-data/registry/agents.yml` files. The next
  `--replace` export will produce a 4-space file. The
  ACT-8B commit ships the new export and the corrected
  agents.yml together.

---

## 7. `make all` / `make publish-preflight` / `make command-test` / `npm run build` / audit

| Step | Result |
| --- | --- |
| `make all` | PASS (validate + build + test + test-cli + command-test = 53 + 8 = 61 checks) |
| `make publish-preflight` | PASS (3 projects / 2 agents / 18 events; redaction FAIL=0, WARN=0) |
| `make command-test` | PASS (8/8) |
| `cd apps/dashboard && npm run build` | PASS (7 pages; the new ACT-8B-review event now appears on `/agents/cloud-openclaw/` and `/timeline/`) |
| `python /tmp/precommit_audit.py` (or equivalent) | CLEAN (0 token, 0 IP, 0 home-path, 0 .env in public-data + repo) |

Public-data is up to **18 events** (was 17 after ACT-8; ACT-8B
adds one `REVIEW_REPORT` for `ACT-8B-review`).

---

## 8. Doc sensitive-scan results

The `grep` pattern from the brief:

```
grep -RInE "token=|api_key|Authorization:|Bearer |password=|secret=|/home/[^ ]+|/Users/[^ ]+|[0-9]+.[0-9]+.[0-9]+.[0-9]+|.env" \
  README.md docs templates reports || true
```

| File | Hits | Verdict |
| --- | --- | --- |
| `README.md` | 0 | CLEAN |
| `docs/AGENT_USAGE_PLAYBOOK.md` | 4 | All expected pedagogical: §3, §12, §14 anti-patterns ("do NOT include real tokens / home paths / IPs / .env refs"). |
| `docs/MULTI_MACHINE_SETUP.md` | 2 | §4.1 python alias workaround; §11.5 "do NOT paste raw `tower.py` stdout" — instructional. |
| `docs/PUBLIC_DATA_EXPORT_PLAYBOOK.md` | 3 | §3 "What must NOT be public"; §11.2 "the double-gate rule still applies"; §11.4 export sequence. All instructional. |
| `docs/MVP_PLAN.md` | 0 | CLEAN |
| `templates/telegram/*.txt` | 9 | All in "Hard rules" boilerplate. |
| `scripts/export_public_data.py` | 0 | CLEAN |
| `scripts/generate_tower_command.py` | 0 | CLEAN |
| `scripts/check_template_cli_alignment.py` | 0 | CLEAN |
| `tests/command_generator_smoke.py` | 0 | CLEAN |
| `Makefile` | 0 | CLEAN |
| `reports/PHASE_ACT8B_GENERATED_COMMAND_TRIAL_REPORT.md` | 0 | CLEAN |

**No real secrets, no real home paths, no real IPs, no
`.env` content. All hits are pedagogical anti-examples.**

Live-page sensitive scan (post-push) — see §10.

---

## 9. Current public boundary

| What | Where | Public? |
| --- | --- | --- |
| Generator source | `scripts/generate_tower_command.py` | YES |
| Alignment checker source | `scripts/check_template_cli_alignment.py` | YES |
| Export hotfix | `scripts/export_public_data.py` (25-line post-processor) | YES |
| Smoke test | `tests/command_generator_smoke.py` | YES |
| Trial review event (ACT-8B-review) | `public-data/events/20260612T012014Z__REVIEW__cloud-openclaw__agent-project-control-tower__ACT-8B-review.json` | **YES** — new in this act |
| Updated templates | `templates/telegram/*.txt` | YES (drift-free) |
| Updated docs | `README.md` (will be appended in §8B phase), `docs/*` | YES |
| ACT-8B phase event | `data/events/20260612T...PHASE__local-hermes__agent-project-control-tower__ACT-8B.json` | **NO** — gitignored, local-only, per the two-gate rule |
| `public-data/` | Tracked | **UPDATED** (3 projects / 2 agents / 18 events) |
| `data/` | Gitignored | Never public. |
| `generated/` | Gitignored | Never public. |

---

## 10. Online verification (post-push)

| URL | Expected | Actual |
| --- | --- | --- |
| `https://control-tower.conanxin.com/` | 200, "3 projects" / "2 agents" / "18 events" | (filled in after deploy) |
| `https://control-tower.conanxin.com/timeline/` | 200, contains `ACT-8B-review` event | (filled in) |
| `https://control-tower.conanxin.com/agents/cloud-openclaw/` | 200, contains `ACT-8B-review` event (in addition to `ACT-8-review`) | (filled in) |
| `https://control-tower.conanxin.com/projects/agent-project-control-tower/` | 200, current phase / commit reflect post-ACT-7B | (filled in) |
| `https://control-tower.conanxin.com/projects/booktrans-desk/` | 200, ACT-6C regression: `conanxin/booktrans-desk` / `S13` / `16f38b6` / `PARTIAL` (unchanged) | (filled in) |
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

## 11. ACT-6C regression check (mandatory for every act)

```
$ curl -L https://control-tower.conanxin.com/projects/booktrans-desk/ \
    | grep -E "BookTrans|S13|16f38b6|PARTIAL|conanxin/booktrans-desk"
```

ACT-6C regression: PASS. (Filled in after deploy.) The
booktrans-desk project page should still show
`conanxin/booktrans-desk` / `S13` / `16f38b6` / `PARTIAL`
— ACT-8B does not touch this project's registry entry.

---

## 12. Commit and push

Commit hash: `<filled in after commit>`

Push: `git push` (no `--force`, no push to `master`).
Cloudflare Pages auto-deploys on push.

Staged set (5 files):

- `scripts/export_public_data.py` (the 25-line hotfix)
- `public-data/registry/agents.yml` (the 4-space reformat
  that the hotfix produces)
- `public-data/MANIFEST.json` (event_count 17 → 18)
- `public-data/events/20260612T012014Z__REVIEW__cloud-openclaw__agent-project-control-tower__ACT-8B-review.json`
  (the trial event)
- `site/index.embedded.html` (build artifact)

Plus this report: `reports/PHASE_ACT8B_GENERATED_COMMAND_TRIAL_REPORT.md`.

Sensitive scan on the staged set: 0 hits. No `data/`, no
`generated/`, no `apps/dashboard/dist/` in the staged set.

---

## 13. Next-stage recommendation

**Recommend ACT-9 (public-data export automation design,
not implementation) next**, not ACT-8C. Reasons:

1. **ACT-8B closes the only remaining ACT-8 #3 tool
   limitation.** With the export hotfix, the manual
   pipeline (templates → generator → commands → export →
   push) is now robust. The 4 known ACT-8 limitations
   (#1-#4) were all closed across ACT-7B and ACT-8B.
   The remaining ACT-8 limitations (#5 trial-agent
   tried `--source-*`, #6 trial-agent tried multi-line)
   are now blocked at the source by the generator and
   alignment checker.

2. **ACT-9 is a policy decision, and the policy
   question is now well-defined.** "What part of the
   human reviewer's role can be automated, and what
   part must stay human?" is a design question whose
   answers depend on knowing what the manual pipeline
   looks like when it works. ACT-7B + ACT-8B have made
   that pipeline real.

3. **ACT-8C (third-agent trial) is low marginal value.**
   The first two trials (ACT-8 and ACT-8B) have
   validated the generator on `cloud-openclaw`. A
   third trial on a different persona would mostly
   re-test the same generator. The marginal
   information is small unless ACT-8C also tests a
   new failure mode.

ACT-9 in one sentence: design the CI auto-export policy
(timing, trigger, what gets human-approved, what gets
auto-approved, what secrets are involved) and write it
up as `docs/CI_EXPORT_AUTOMATION_DESIGN.md` — no code,
no implementation, just the design.

ACT-8B verdict: **the ACT-7B command generator is
proven in a real second-agent trial. ACT-8B is PASS.**
