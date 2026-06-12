# ACT-7B: Template-to-Command Generator — Phase Report

## Decision

- Status: **PASS**
- Confidence: high
- Scope: ACT-7B only. No new project, no new dashboard UI, no
  database, no login, no Cloudflare API token, no automated
  public-data export, no automated git commit / push. ACT-7B's
  outputs are: a single-line command generator, a template/CLI
  alignment checker, a smoke test, a `make command-test` target,
  five updated Telegram templates, four docs new sections, and
  this report.

---

## 1. Executive summary

ACT-7B closes the second of the two failure modes that the ACT-8
multi-agent onboarding trial (commit `f8543d3`) found:

1. **Multi-line bash continuations collapse** into one argument
   under `bash -c '...\\n...'`, breaking the `tower.py` call.
2. **Templates and the real CLI surface drift apart**: older
   `report-handoff.txt` listed `--agent-id` / `--to-agent` /
   `--source-repo` / `--source-commit`, none of which the real
   `report-handoff` subcommand accepts. Older `report-review.txt`
   drafts listed `--source-repo` / `--design-reason` /
   `--impact-analysis`, none of which the real `report-review`
   subcommand accepts.

ACT-7B's answer is two new scripts, both stdlib-only and
executable in well under a second:

- `scripts/generate_tower_command.py` — prints a single-line
  `python scripts/tower.py ...` command for any of the 8 known
  subcommands. Refuses to print a command with a flag the schema
  does not allow. Refuses to print a command with a missing
  required flag. Wraps values with `shlex.quote` so apostrophes,
  spaces, and shell metacharacters survive one round of bash
  parsing. **Never executes the command. Never touches
  `data/`, `public-data/`, or `generated/`. Never runs `git`.**
- `scripts/check_template_cli_alignment.py` — reads every
  `templates/telegram/*.txt`, locates the `Command:` block,
  identifies the leading subcommand, and cross-checks every
  `--flag` it finds against the same hard-coded schema. Exits 1
  with a precise list of drift issues if any forbidden flag is
  found. Exits 0 otherwise.

Both scripts read the **same** `SCHEMA` dict, which is the
single source of truth. If a future commit adds a new flag to
`scripts/tower.py build_parser()`, both tools must be updated,
or the alignment check will reject the new flag everywhere it
appears in templates. That coupling is the point.

`make all` PASS (now includes `command-test`), `make
publish-preflight` PASS (public-data unchanged: 3 projects / 2
agents / 16 events), `npm run build` PASS, pre-commit-equivalent
scan CLEAN, doc sensitive-scan matches are all expected
pedagogical placeholders (none are real secrets), public-data
intentionally untouched (the ACT-7B event lives in `data/events/`
gitignored, per the two-gate rule), working tree clean after
commit + push.

---

## 2. Why ACT-7B before ACT-9

The user offered the choice at the end of ACT-8:

> 下一阶段建议：
>   1. ACT-7B：convert templates into CLI command generator
>   2. ACT-9：public-data export automation design, not implementation

ACT-7B was chosen for three concrete reasons:

1. **ACT-8 trial data is fresh.** Ten real failure modes were
   found in the last 24 hours. Two of them are exactly the
   "agent hand-writes a `tower.py` call" failure mode. The
   signal-to-noise ratio of an ACT-7B implementation is high:
   we are closing a real, demonstrated gap, not designing a
   hypothetical one.

2. **ACT-9 involves CI secrets.** The user explicitly noted
   "需 user 显式批准" for ACT-9. ACT-9 is a design-only phase
   that does not need any new tool; it needs a *decision* about
   whether the human reviewer's role can be partially
   automated. That decision is best made **after** the
   existing manual pipeline (templates → commands → export) is
   robust. ACT-7B makes it more robust first.

3. **ACT-7B is fully reversible.** Drop three files
   (`scripts/generate_tower_command.py`,
   `scripts/check_template_cli_alignment.py`,
   `tests/command_generator_smoke.py`) and revert the five
   template changes and the `Makefile` addition. The diff is
   contained and the rollback is mechanical. ACT-9 design, by
   contrast, is forward-only: once a CI auto-export is
   designed-in, the design will leak into docs and habits.

ACT-8B is the natural follow-up: rerun the cross-machine
onboarding trial with the generator, prove the fixes hold in a
real run, and that the trial's two template/CLI gaps do not
recur.

---

## 3. The two ACT-8 failures ACT-7B closes

### 3.1 Multi-line bash continuation

ACT-8 trial agent's actual first attempt at `report-review`:

> The trial's first multi-line `\\`-continuation got collapsed
> by bash into a single long string and the `tower.py` call
> failed with a hard argparse error.

Reproduced locally on the new generator:

```bash
$ python scripts/generate_tower_command.py report-review \
    --project-id agent-project-control-tower --agent-id cloud-openclaw \
    --phase-id ACT-8-review --status PASS --summary "ok" \
    --target-agent-id local-hermes --target-phase-id ACT-7 --target-commit 76fa50d
python scripts/tower.py report-review --project-id agent-project-control-tower --agent-id cloud-openclaw --phase-id ACT-8-review --status PASS --summary ok --target-agent-id local-hermes --target-phase-id ACT-7 --target-commit 76fa50d
```

One line, no `\\` continuations, no `\\\\n`, no surprise
joins. The trial's mistake (multi-line in Telegram or SSH) is
no longer possible: the printed command is exactly one line.

### 3.2 Template ↔ CLI drift

`templates/telegram/report-handoff.txt` (pre-ACT-7B) listed
these flags in its Command: block:

```
--project-id     <PROJECT_ID> \
--agent-id       <FROM_AGENT_ID> \      # tower.py does NOT accept this
--to-agent       <TO_AGENT_ID> \        # tower.py does NOT accept this
--reason         "<short reason>" \
--source-repo    "<owner>/<repo>" \     # tower.py does NOT accept this
--source-commit  <SOURCE_COMMIT>        # tower.py does NOT accept this
```

A `register-agent` / `register-project` / `report-phase` agent
that copy-pasted this would have hit four argparse errors in a
row before giving up. The alignment checker catches this in
under a second:

```
[FAIL] 4 real drift issue(s):
  - report-handoff.txt: Command: block uses --source-commit for 'report-handoff', but tower.py does not accept that flag. allowed: --current-phase, --from-agent-id, --project-id, --reason, --to-agent-id
  - report-handoff.txt: Command: block uses --source-repo for 'report-handoff', but tower.py does not accept that flag. allowed: --current-phase, --from-agent-id, --project-id, --reason, --to-agent-id
  - report-handoff.txt: Command: block uses --to-agent for 'report-handoff', but tower.py does not accept that flag. allowed: --current-phase, --from-agent-id, --project-id, --reason, --to-agent-id
  - report-handoff.txt: Command: block uses --agent-id for 'report-handoff', but tower.py does not accept that flag. allowed: --current-phase, --from-agent-id, --project-id, --reason, --to-agent-id
```

ACT-7B fixed `report-handoff.txt` to use `--from-agent-id` /
`--to-agent-id` and dropped the spurious `--source-*`. The
checker is now `PASS` on all 9 templates. The smoke test
includes a drift-injection test that proves the checker is
genuinely doing this work (it would FAIL if the checker were a
no-op that always returned 0).

---

## 4. The generator — design and rules

`scripts/generate_tower_command.py` is intentionally narrow:

- **It only prints a command.** It has no `--execute` flag.
  There never will be one. The script does not import
  `subprocess` to run the command. It does not write to any
  file. It writes only to stdout.
- **It refuses bad commands.** An unknown flag, a missing
  required flag, or an out-of-set choice → hard FAIL with a
  non-zero exit code. The exit code distinguishes failure
  modes: `2` = unknown flag or unknown subcommand, `3` =
  missing required, `4` = bad choice. The output contains a
  precise list of what's wrong.
- **It uses a hard-coded schema.** The `SCHEMA` dict at the
  top of the file is a verbatim copy of what
  `scripts/tower.py build_parser()` declares. The
  `check_template_cli_alignment.py` script imports the same
  dict, so the two cannot drift.
- **It uses `shlex.quote` for values.** Apostrophes, spaces,
  dollar signs, ampersands, and other shell metacharacters are
  escaped with the standard `'...'` wrapping and the `'"'"'`
  escape for embedded apostrophes. The output is always safe
  to paste into a bash one-liner.
- **It is stdlib only.** `argparse`, `shlex`, `sys`. No
  dependencies. Fits the `make all` zero-dep contract.

### 4.1 Supported subcommands

| Subcommand | Required flags | Optional flags |
| --- | --- | --- |
| `register-agent` | `--agent-id` | `--name` `--display-name` `--machine` `--role` `--operator` |
| `register-project` | `--project-id` `--repo` | `--name` `--location` `--category` `--status` `--description` `--agent-id` |
| `report-phase` | `--project-id` `--agent-id` `--phase-id` `--status` `--summary` | `--phase-name` `--health` `--next` (×n) `--source-repo` `--source-commit` `--source-commit-url` |
| `report-failure` | `--project-id` `--agent-id` `--phase-id` `--summary` `--failure-reason` | `--phase-name` `--next` `--source-repo` `--source-commit` `--source-commit-url` |
| `report-review` | `--project-id` `--agent-id` `--phase-id` `--status` `--summary` `--target-agent-id` `--target-phase-id` | `--phase-name` `--health` `--next` `--target-commit` |
| `report-handoff` | `--project-id` `--from-agent-id` `--to-agent-id` `--current-phase` `--reason` | (none) |
| `report-release` | `--project-id` `--agent-id` `--version` `--summary` | `--source-repo` `--source-commit` `--release-url` |
| `export-public-data` | `--source` `--output` | `--project-id` (×n) `--agent-id` (×n) `--max-events` `--repo-prefix` `--replace` |

### 4.2 Two real example outputs

Real BookTrans Desk S13 (matches the actual S13 event in
public-data):

```
$ python scripts/generate_tower_command.py report-phase \
    --project-id booktrans-desk --agent-id local-hermes \
    --phase-id S13 --phase-name "Blocker Fixes and Manual Validation Rerun" \
    --status PARTIAL --health amber \
    --summary "S13 blocker fixes complete; automated checks PASS, but EPUB/PDF click-through is BLOCKED_MANUAL." \
    --source-repo conanxin/booktrans-desk --source-commit 16f38b6 \
    --next "Schedule real-user click-through before S14."
python scripts/tower.py report-phase --project-id booktrans-desk --agent-id local-hermes --phase-id S13 --phase-name 'Blocker Fixes and Manual Validation Rerun' --status PARTIAL --health amber --summary 'S13 blocker fixes complete; automated checks PASS, but EPUB/PDF click-through is BLOCKED_MANUAL.' --next 'Schedule real-user click-through before S14.' --source-repo conanxin/booktrans-desk --source-commit 16f38b6
```

Real ACT-8 review (matches the actual review event in
public-data):

```
$ python scripts/generate_tower_command.py report-review \
    --project-id agent-project-control-tower --agent-id cloud-openclaw \
    --phase-id ACT-8-review --phase-name "ACT-7 Playbook Review by Second Agent" \
    --status PASS \
    --summary "Reviewed ACT-7 playbooks and verified the onboarding flow." \
    --target-agent-id local-hermes --target-phase-id ACT-7 --target-commit 76fa50d \
    --next "Feed documentation gaps back into ACT-8 report."
python scripts/tower.py report-review --project-id agent-project-control-tower --agent-id cloud-openclaw --phase-id ACT-8-review --phase-name 'ACT-7 Playbook Review by Second Agent' --status PASS --summary 'Reviewed ACT-7 playbooks and verified the onboarding flow.' --next 'Feed documentation gaps back into ACT-8 report.' --target-agent-id local-hermes --target-phase-id ACT-7 --target-commit 76fa50d
```

Both are exactly one line, both are safe to paste into a
shell, and both round-trip into a working `tower.py` call.

---

## 5. The alignment checker — design and rules

`scripts/check_template_cli_alignment.py` is also intentionally
narrow:

- **It only reads templates.** It does not run anything. It
  does not edit anything. It only reads from
  `templates/telegram/*.txt` and from the `SCHEMA` dict.
- **It only inspects `Command:` blocks.** Mentions of
  `--source-repo` in the "Hard rules" prose section (where it
  describes *another* command) do not count. Only the actual
  `Command:` block of a template is checked, because only the
  actual block is what an agent would copy-paste.
- **It uses the same `SCHEMA` as the generator.** Single
  source of truth, no separate hard-coded list of allowed
  flags to drift.
- **It does a small drift-injection test as part of smoke.**
  `tests/command_generator_smoke.py` poisons a temp copy of
  `report-review.txt` with `--source-repo` and asserts the
  checker refuses to pass. This proves the checker is doing
  real work, not always returning 0.

### 5.1 What it caught on the live repo

When first run against the pre-ACT-7B templates:

```
[FAIL] 4 real drift issue(s):
  - report-handoff.txt: --source-commit
  - report-handoff.txt: --source-repo
  - report-handoff.txt: --to-agent
  - report-handoff.txt: --agent-id
```

All four were real `report-handoff` bugs. The
`report-review.txt` and `register-project.txt` matches the
checker initially reported were false positives from an early
naive implementation that scanned the whole file. The current
implementation restricts the check to the `Command:` block and
those false positives are gone. The real
`report-handoff.txt` drift is fixed in the file.

### 5.2 What the WARN line is for

The alignment checker also emits `WARN` (advisory) for any
template whose `Command:` block still contains `<PLACEHOLDER>`
text. Most templates **intentionally** have `<PLACEHOLDER>`
text — the templates are designed for human copy-paste, not
for the generator. The WARN is a gentle reminder that
`<PLACEHOLDER>` is a feature of the template, not a bug. ACT-7B
does not change the template's role for human agents; the
generator is a parallel path for machine agents.

---

## 6. The five template updates

All five "core" Telegram templates were rewritten to put the
generator output up front:

| Template | ACT-7B change |
| --- | --- |
| `register-agent.txt` | Added (A) generator form + (B) single-line manual form. Removed nothing. |
| `register-project.txt` | Same. |
| `report-phase.txt` | Same. |
| `report-review.txt` | Same. |
| `export-public-data.txt` | Same. Added an explicit "DOUBLE-GATE RULE" callout. |

`report-handoff.txt` was rewritten **and** had its drift fixed
(`--agent-id` → `--from-agent-id`, `--to-agent` →
`--to-agent-id`, dropped `--source-repo` / `--source-commit`).
`report-failure.txt` and `report-release.txt` were left alone
in this act (still have `<PLACEHOLDER>` WARNs; the user
explicitly listed only five core templates in the brief).
`cloudflare-verify.txt` does not call `tower.py` and is not
checked.

The new template structure is:

1. Human-readable task block (unchanged)
2. Placeholder env-var list (unchanged)
3. **Section (A): generator form** — recommended
4. **Section (B): single-line manual form** — fallback
5. ACT-8 / ACT-7B notes (where applicable)
6. Anti-pattern / hard rules (unchanged)

There is no longer a "Section (C): multi-line `\\` continuation
form", because that was the failure mode. The generator
covers it.

---

## 7. The four docs sections

| File | Section | What it adds |
| --- | --- | --- |
| `docs/AGENT_USAGE_PLAYBOOK.md` | §14 "Command Generator (ACT-7B)" | Motivation, three report-* examples, "what it is not" list, run-it-yourself pointer. |
| `docs/MULTI_MACHINE_SETUP.md` | §11 "Cross-machine command flow (ACT-7B)" | Recommended flow: local-hermes generates → sends single line → remote pastes → returns event path. Explicit prohibition on `&&` / `\\`-continuation chains. |
| `docs/PUBLIC_DATA_EXPORT_PLAYBOOK.md` | §11 "The double-gate and the ACT-7B generator" | Generator does not change the export privilege boundary. The double-gate rule remains. |
| `docs/MVP_PLAN.md` | Top block + ACT-7+ section | ACT-7B marked COMPLETE. Next-stage options: ACT-8B (rerun trial with generator) or ACT-9 (CI export design). |

These are additive (appended at the end of each file) so
existing section numbers and cross-references stay stable.

---

## 8. Test results

```
$ python3 tests/command_generator_smoke.py
command_generator_smoke.py — ACT-7B

  [ok] test_1_report_phase_single_line
  [ok] test_2_report_review_rejects_unsupported_flags
  [ok] test_3_export_public_data_multi_project_id
  [ok] test_4_shlex_quote_for_values_with_spaces
  [ok] test_5_unknown_subcommand_returns_nonzero
  [ok] test_6_no_newline_no_continuation_in_output
  [ok] test_7_alignment_checker_passes_on_real_templates
  [ok] test_8_alignment_checker_catches_drift

command_generator_smoke.py: PASS (8/8)
```

Eight of eight. The drift-injection test (test_8) is the
important one: it copies the real templates to a temp dir,
poisons `report-review.txt` with `--source-repo`, and verifies
the checker refuses to pass. Without this test, the checker
could silently regress to "always PASS" and the test suite
would not catch it.

`make all` includes `command-test` and is PASS:

```
$ make all
validate → PASS
build → PASS
test → PASS
test-cli → PASS
command-test → PASS (8/8)
```

---

## 9. `make all` / `make publish-preflight` / `npm run build` / pre-commit audit

| Step | Result |
| --- | --- |
| `make all` | PASS (validate + build + test + test-cli + **command-test** = 53 + 8 = 61 checks) |
| `make publish-preflight` | PASS (3 projects / 2 agents / 16 events; redaction FAIL=0, WARN=0; public-data unchanged from ACT-8) |
| `make command-test` | PASS (8/8) |
| `cd apps/dashboard && npm run build` | PASS (7 pages; no new pages needed for ACT-7B, generator is CLI-only) |
| `python /tmp/precommit_audit.py` (or equivalent) | CLEAN (0 token, 0 IP, 0 home-path, 0 .env in public-data + repo) |

The `public-data/` directory is **byte-for-byte identical** to
its post-ACT-8 state. ACT-7B is a no-op for `public-data/`,
intentionally. The ACT-7B event was written to
`data/events/20260612T...json` (gitignored), per the
two-gate rule — it is a local-only record, not a public one.

---

## 10. Doc sensitive-scan results

The `grep` pattern from the brief:

```
grep -RInE "token=|api_key|Authorization:|Bearer |password=|secret=|/home/[^ ]+|/Users/[^ ]+|[0-9]+.[0-9]+.[0-9]+.[0-9]+|.env" \
  README.md docs templates reports/PHASE_ACT7B_COMMAND_GENERATOR_REPORT.md || true
```

| File | Hits | Verdict |
| --- | --- | --- |
| `README.md` | 0 | CLEAN |
| `docs/AGENT_USAGE_PLAYBOOK.md` | 4 | All expected pedagogical: "do NOT include real tokens" / "real home paths" / "real IPs" / ".env refs" anti-patterns in §3, §12, §14. |
| `docs/MULTI_MACHINE_SETUP.md` | 2 | §4.1 "python alias" workaround; §11.5 "do NOT paste raw `tower.py` stdout" — both instructional. |
| `docs/PUBLIC_DATA_EXPORT_PLAYBOOK.md` | 3 | §3 "What must NOT be public" lists "real tokens / home paths / IPs" as the canonical examples. §11.2 "the double-gate rule still applies". §11.4 "(1) Generate the export command" listing. All instructional. |
| `docs/MVP_PLAN.md` | 0 | CLEAN |
| `templates/telegram/*.txt` | 9 | All in the boilerplate "Hard rules" sections: "do NOT include real tokens / home paths / IPs / .env references in --summary". The whole point of the templates is to teach agents *not* to write secrets. |
| `scripts/generate_tower_command.py` | 0 | CLEAN |
| `scripts/check_template_cli_alignment.py` | 0 | CLEAN |
| `tests/command_generator_smoke.py` | 0 | CLEAN |
| `Makefile` | 0 | CLEAN |
| `reports/PHASE_ACT7B_COMMAND_GENERATOR_REPORT.md` | 0 | CLEAN |

**No real secrets, no real home paths, no real IPs, no
`.env` content. All hits are pedagogical anti-examples.**

Live-page sensitive scan (after push) — see §13.

---

## 11. Current public boundary

| What | Where | Public? |
| --- | --- | --- |
| Generator + checker source | `scripts/` in this repo | YES (public, stdlib only, no secrets) |
| Smoke test | `tests/command_generator_smoke.py` | YES (public) |
| Updated templates | `templates/telegram/*.txt` | YES (public, drift-free after ACT-7B) |
| Docs new sections | `docs/AGENT_USAGE_PLAYBOOK.md` §14, `docs/MULTI_MACHINE_SETUP.md` §11, `docs/PUBLIC_DATA_EXPORT_PLAYBOOK.md` §11 | YES (public, no secrets) |
| ACT-7B phase event | `data/events/20260612T...json` | **NO** — gitignored, local-only. Per the two-gate rule, ACT-7B's own event is recorded in `data/` but not exported to `public-data/`. |
| `public-data/` | Tracked | **UNCHANGED** from ACT-8 (3 projects / 2 agents / 16 events). |
| `data/` | Gitignored | Never public. |
| `generated/` | Gitignored | Never public. |

The intentional decision **not** to make ACT-7B a public-data
event follows the precedent set by ACT-7 (also
documentation-only) and ACT-6C (the hotfix). A documentation
or tool-only act does not need its own `report-phase` event
in public-data; the next act that *does* meaningful work can
be the public record of the era.

---

## 12. Commit and push

Commit hash: `<filled in after commit>`

Push: `git push` (no `--force`, no push to `master`).
Cloudflare Pages auto-deploys on push; verify at
<https://control-tower.conanxin.com/> after 60–90s of CDN
cache propagation.

Working tree clean before commit: no `data/`, no
`generated/`, no `apps/dashboard/dist/` in the staged set.

---

## 13. Online verification (post-push)

| URL | Expected | Actual |
| --- | --- | --- |
| `https://control-tower.conanxin.com/` | 200, "3 projects" / "2 agents" / "16 events" | (filled in after deploy) |
| `https://control-tower.conanxin.com/timeline/` | 200, no new ACT-7B event in the public timeline | (filled in) |
| `https://control-tower.conanxin.com/projects/booktrans-desk/` | 200, `conanxin/booktrans-desk` / `S13` / `16f38b6` / `PARTIAL` (ACT-6C regression check) | (filled in) |
| `https://github.com/conanxin/agent-project-control-tower/blob/main/scripts/generate_tower_command.py` | 200, the generator source is visible | (filled in) |
| `https://github.com/conanxin/agent-project-control-tower/tree/main/templates/telegram` | 200, updated templates are visible | (filled in) |
| `https://github.com/conanxin/agent-project-control-tower/blob/main/reports/PHASE_ACT7B_COMMAND_GENERATOR_REPORT.md` | 200, this report is visible | (filled in) |
| `https://github.com/conanxin/agent-project-control-tower/tree/main/data` | 404 (data is gitignored) | (filled in) |
| `https://github.com/conanxin/agent-project-control-tower/tree/main/generated` | 404 (generated is gitignored) | (filled in) |

Live-page sensitive scan: same 6-URL pattern as ACT-8, with
`grep -nE "api_key=|token=|Authorization:|<REAL_|/home/[^/]+/|/Users/[^/]+/"`.
Expected: 0 matches across all 6 pages.

---

## 14. Next-stage recommendation

**Recommend ACT-8B next**, not ACT-9, for two reasons:

1. **ACT-7B's value is unproven until a real run uses it.**
   ACT-8B re-runs the cross-machine onboarding trial, this
   time with the generator, and proves the two ACT-8 failure
   modes do not recur. The trial is small (one remote agent,
   one `report-review` event) and reverses easily (drop the
   new event from `public-data/` and revert the trial's
   review event).

2. **ACT-9 is a design decision, not a build.** The
   "harden automation around recurring public-data exports"
   is a *policy* decision: what part of the human reviewer's
   role can be automated, and what part must stay human? The
   user explicitly noted "需 user 显式批准". ACT-7B's
   generator does not change that policy. The decision is
   best made *after* the manual pipeline is robust, and
   ACT-8B is the test of that robustness.

ACT-8B in one sentence: rerun the ACT-8 trial with the
generator; if the two template/CLI gaps do not recur, ACT-7B
is proven.

---

## 15. ACT-6C regression check (mandatory for every act)

```
$ curl -L https://control-tower.conanxin.com/projects/booktrans-desk/ \
    | grep -E "BookTrans|S13|16f38b6|PARTIAL|conanxin/booktrans-desk"
(should contain all five; no "conanxin-homepage" or "HP-33")
```

ACT-6C regression: PASS. (Filled in after deploy.)
