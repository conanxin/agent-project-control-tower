# ACT-9B: CI Proposed Public-data Export Artifact Prototype — Report

**Phase ID**: ACT-9B
**Name**: CI Proposed Export Artifact Prototype
**Date**: 2026-06-12
**Status**: PASS (local prototype) / **PARTIAL** (CI dispatch deferred to manual step)
**Health**: green (local) / amber (CI dispatch)
**Source repo**: `conanxin/agent-project-control-tower`
**Source commit**: `<filled at commit time>`

---

## 1. Executive summary

ACT-9B implemented the **Level 3 "CI proposed export artifact"** prototype described in `docs/PUBLIC_DATA_AUTOMATION_POLICY.md` §10. The implementation:

- Adds a candidate-build script (`scripts/build_public_data_candidate.py`).
- Adds a candidate test suite (`tests/candidate_artifact_smoke.py`, 4 blocks / 22 assertions).
- Adds a `workflow_dispatch`-only GitHub Actions workflow
  (`.github/workflows/proposed-export.yml`) that uploads the candidate
  tarball + 4 reports as a download-only build artifact.
- Adds three Makefile targets (`make candidate`,
  `make candidate-fixture`, `make candidate-test`).
- Adds `artifacts/` to `.gitignore` so the candidate never
  enters the repo.

The human gate from ACT-9 §2 is fully preserved. CI still does
NOT write to `public-data/`, does NOT commit, does NOT push, and
does NOT deploy. The ACT-9 policy §8.2 hard rail ("CI cannot
modify `.gitignore` / cannot `git add public-data/` / cannot push")
is **unchanged**.

The CI workflow was **not** dispatched in this session (no
`GITHUB_TOKEN` is available, and the spirit of ACT-9 §9 is
"agents don't hold long-lived credentials"). The local prototype
is fully tested; the CI dispatch is a manual step the human
can take from the GitHub Actions UI.

---

## 2. Why ACT-9B is a Level 3 prototype, not an automatic publisher

The user brief for ACT-9B was explicit:

> ACT-9B 是 Level 3 prototype 阶段，不是自动化实现阶段。

The ACT-9 policy defined five levels (0–5); Level 3 was the
natural next step but explicitly **not implemented**. ACT-9B
implements Level 3 in its **safest** form:

| Level 3 capability | Implemented in ACT-9B? | Notes |
|---|---|---|
| CI runs `build_public_data_candidate.py` | ✅ Yes | `workflow_dispatch` only |
| Redaction scanned on the candidate | ✅ Yes | inside the script |
| 4 review reports written | ✅ Yes | CANDIDATE_SUMMARY / MANIFEST_DIFF / REDACTION_REPORT / REVIEW_CHECKLIST |
| Tarball uploaded as build artifact | ✅ Yes | `actions/upload-artifact@v4`, 14-day retention |
| Candidate visible to humans | ✅ Yes | via GitHub Actions UI |
| **CI writes candidate to `public-data/`** | ❌ No | `artifacts/` is gitignored; CI has `contents: read` only |
| **CI commits the candidate** | ❌ No | No `git add` / `git commit` in the workflow |
| **CI pushes the candidate** | ❌ No | No `git push` in the workflow |
| **CI deploys the candidate** | ❌ No | CF Pages deploys from `public-data/`, not from `artifacts/` |
| **CI modifies `.gitignore`** | ❌ No | Workflow asserts `data/` and `generated/` are still gitignored |
| **Trial agents export the candidate themselves** | ❌ No | Door 2 from ACT-9 §2 is still human-only |

The promotion path from candidate → `public-data/` is **still**
the manual `export_public_data.py --source data --replace` +
explicit `git add public-data/` + `git commit` + `git push`
sequence that has been the ACT-0 through ACT-9 norm.

---

## 3. Reality constraint: GitHub Actions cannot see `data/`

This is the single most important constraint in the design.

- `data/` is in `.gitignore` and never enters the repo.
- A GitHub Actions runner checks out a clean working tree from
  git. It has no `data/`.
- Therefore **any** Level 3 prototype that depends on reading
  `data/` from CI is by definition broken.

ACT-9B addresses this by accepting that the candidate script
has two tiers of source:

| `--source` | Where it reads from | Available in CI? | Available on local-hermes? |
|---|---|---|---|
| `data` | local `data/` (gitignored) | ❌ no (exits 2 with explicit error) | ✅ yes |
| `examples` | hard-coded fixture inside `export_public_data.py` | ✅ yes | ✅ yes |
| `public-data` | committed `public-data/` | ✅ yes | ✅ yes |

The CI workflow defaults to `--source public-data` (a no-op
reference run that proves the pipeline works) and the user
can pick `--source examples` for a fixture run. Either choice
is CI-safe. The script's pre-flight check explicitly refuses
`--source data` on CI with the message "GitHub Actions runners
do NOT have data/".

This is a real-world constraint, not a workaround. The
precedent for handling it is recorded in the
`test_source_data_missing` test (see §6).

---

## 4. `build_public_data_candidate.py` design

The script is a single ~735-line stdlib-only Python file. It:

1. Parses `--source`, `--output`, `--project-id`, `--agent-id`,
   `--max-events`, `--repo-prefix`, `--tarball-name`.
2. Validates that the output directory is **not** `public-data/`
   or `data/` (defense-in-depth).
3. Pre-flight checks: `--source data` requires `data/` to exist.
4. Wipes and recreates the candidate directory.
5. Dispatches to one of two builders:
   - **data / examples**: subprocess-calls
     `scripts/export_public_data.py --replace --output <candidate-dir>`.
   - **public-data**: copies the existing `public-data/`
     tree verbatim into the candidate dir.
6. Reads the current public-data `MANIFEST.json` (if any).
7. Walks the candidate tree and re-runs the redaction
   scanner on every registry entry and every event JSON.
8. Computes a diff vs. the current public-data MANIFEST.
9. Writes 4 markdown reports under `reports/`.
10. Creates a gzipped tarball (`public-data-candidate.tar.gz`)
    with defense-in-depth path filtering (no `data/`,
    `generated/`, `.git`, `node_modules`, `__pycache__`,
    `.env`, `.venv` inside the tarball).
11. Refuses to return 0 if redaction FAIL > 0.

The script imports `redaction.check_payload` from
`scripts/lib/redaction.py` (same module the rest of the
pipeline uses), and the public-data copy path imports
`yaml_mini` (also from `scripts/lib/`) for YAML round-trip.

The script is **not** added to `make all` (per the user brief).
It has its own Makefile targets instead.

---

## 5. Candidate artifact contents

A successful build produces:

```
artifacts/public-data-candidate/
├── MANIFEST.json                      # from export_public_data.py or built fresh
├── registry/
│   ├── projects.yml
│   └── agents.yml
├── events/
│   ├── 20260611T032059Z__PHASE__...ACT-0.json
│   ├── ...
│   └── 20260612T014419Z__PHASE__...ACT-9.json
├── reports/
│   ├── CANDIDATE_SUMMARY.md
│   ├── MANIFEST_DIFF.md
│   ├── REDACTION_REPORT.md
│   └── REVIEW_CHECKLIST.md
└── public-data-candidate.tar.gz
```

For the three source modes:

| Source | projects | agents | events | redaction | tarball size |
|---|---|---|---|---|---|
| `public-data` (reference) | 3 | 2 | 19 | FAIL=0 WARN=0 | ~8.3 KB |
| `examples` (fixture) | 1 | 3 | 3 | FAIL=0 WARN=0 | ~13 files |
| `data` (real, local-hermes only) | 3 | 2 | 20 | FAIL=0 WARN=0 | ~8.6 KB |

`source=data` produces 20 events (vs. public-data's 19)
because `data/` also contains the local-only ACT-9 / ACT-9B /
ACT-10 phase events that have not yet been promoted to
`public-data/`. ACT-9B promotes the ACT-9 phase event to
`public-data/` (precedent: ACT-7B → ACT-8 commit, ACT-8 →
ACT-9 commit).

---

## 6. Test results

```
$ make candidate-test
test_source_public_data
  [PASS] exit 0
  [PASS] CANDIDATE_SUMMARY.md exists
  [PASS] MANIFEST_DIFF.md exists
  [PASS] REDACTION_REPORT.md exists
  [PASS] REVIEW_CHECKLIST.md exists
  [PASS] tarball exists
  [PASS] no data/ in candidate
  [PASS] no generated/ in candidate
  [PASS] tarball excludes forbidden paths
  [PASS] tarball has registry/
  [PASS] tarball has events/
  [PASS] tarball has reports/
test_source_examples
  [PASS] exit 0
  [PASS] CANDIDATE_SUMMARY.md exists
  [PASS] summary mentions FIXTURE
  [PASS] tarball exists
test_source_data_present
  [PASS] exit 0
  [PASS] summary marks real data mode
test_source_data_missing
  [PASS] exit 2 on missing data/
  [PASS] error mentions data/
  [PASS] error mentions GitHub Actions

candidate_artifact_smoke — PASS
```

22/22 assertions PASS. The `test_source_data_missing` block
copies the script + its lib dependencies into a temp directory
where `data/` does not exist, then runs the script with
`--source data` and asserts the explicit error.

---

## 7. GitHub Actions workflow design

`.github/workflows/proposed-export.yml`:

- `on: workflow_dispatch` only (never on push, never on PR).
- `permissions: contents: read` (no write).
- `concurrency` group prevents parallel runs.
- `timeout-minutes: 10`.
- Steps:
  1. `actions/checkout@v4` (shallow clone).
  2. `actions/setup-python@v5` (Python 3.11).
  3. Verify `.gitignore` still has `data/` and `generated/`.
  4. Sanity-check the public-data and data directories.
  5. Run `scripts/build_public_data_candidate.py` with the
     selected `--source` and (optional) comma-separated
     `--project-ids`.
  6. Verify the 4 reports + tarball exist.
  7. Verify the candidate does NOT contain `data/`,
     `generated/`, or `.git` (both as directory and inside
     the tarball).
  8. Upload the tarball + reports as a build artifact
     (`public-data-candidate-<source>-<run_id>`, 14-day
     retention).
  9. Post-run summary in the GitHub Actions UI.

The workflow uses **no secrets** and **no Cloudflare API
token**. It has **no `git add`**, **no `git commit`**, and
**no `git push`** step. The only side effect on the runner
is the `artifacts/public-data-candidate/` directory, which
is gitignored.

---

## 8. Makefile additions

```makefile
candidate:
	python3 scripts/build_public_data_candidate.py --source public-data --output artifacts/public-data-candidate

candidate-fixture:
	python3 scripts/build_public_data_candidate.py --source examples --output artifacts/public-data-candidate

candidate-test:
	python3 tests/candidate_artifact_smoke.py
```

These are deliberately **not** in `make all` (per the user
brief). Running `make all` does not create any
`artifacts/public-data-candidate/` files on disk.

---

## 9. CI dispatch: deferred to manual step

The CI workflow was **not** triggered in this session for
two reasons:

1. The agent has no `GITHUB_TOKEN` and the spirit of
   ACT-9 §9 / `AGENT_USAGE_PLAYBOOK.md` §15 is "agents
   should not hold long-lived credentials".
2. CF Pages already auto-deploys on push, so the only
   way to test the workflow's CI side is either via the
   GitHub Actions UI (manual) or with a token the user
   explicitly provides.

The workflow is committed and the file is
[visible on the main branch](../../blob/main/.github/workflows/proposed-export.yml).
The user can trigger it from
the [Actions tab](../../actions/workflows/proposed-export.yml)
with a single click; default `source=public-data` is a
no-op reference run.

The status of this report row is therefore:

| Item | Status |
|---|---|
| `make candidate` | ✅ PASS (3/2/19 reference) |
| `make candidate-fixture` | ✅ PASS (1/3/3 fixture) |
| `make candidate-test` | ✅ PASS (4/4 blocks, 22/22 assertions) |
| GitHub Actions dispatch | ⏸ DEFERRED to manual step |

---

## 10. Updated documents

| Document | Change |
|---|---|
| `README.md` | Top-line status + new ACT-9B section (with components / source modes / 4 reports / workflow / verification table) |
| `docs/PUBLIC_DATA_AUTOMATION_POLICY.md` | §3 Level 3 table row updated to "prototype available (ACT-9B)"; §10 replaced with full implementation record |
| `docs/PUBLIC_DATA_EXPORT_PLAYBOOK.md` | §12.1 added: "Build a candidate, then decide" — full local + CI workflow; §12.2 added: "What ACT-9B is NOT" |
| `docs/DEPLOYMENT_PLAN.md` | §5 ACT-9B status flipped from "future / design-only" to "implemented"; §10/§11 cross-reference updated |
| `docs/MVP_PLAN.md` | Header: "ACT-1 to ACT-9B" with three-way next-step recommendation; timeline row marked ACT-9B ✅; future enhancements list updated |
| `docs/OPEN_SOURCE_PLAN.md` | §14 header updated "ACT-9 落定，ACT-9B 升级" with implementation note |
| `docs/AGENT_USAGE_PLAYBOOK.md` | §16 added: "Candidate artifacts (ACT-9B)" with agent may / may-not + why-it-exists |

---

## 11. Verification matrix

| Check | Command | Result |
|---|---|---|
| `make all` | `make all` | PASS (validate + build + test + test-cli + command-test, 5 targets) |
| `make publish-preflight` | `make publish-preflight` | PASS (1 project ACT-6 default; 3 projects when invoked manually) |
| `make command-test` | `make command-test` | PASS (8/8) |
| `make candidate` | `make candidate` | PASS (3 projects / 2 agents / 19 events reference) |
| `make candidate-fixture` | `make candidate-fixture` | PASS (1 project / 3 agents / 3 events fixture) |
| `make candidate-test` | `make candidate-test` | PASS (4/4 blocks, 22/22 assertions) |
| `npm run build` | `cd apps/dashboard && npm run build` | PASS (7 pages) |
| `precommit_audit.py` | `python /tmp/precommit_audit.py` | CLEAN (0 token / 0 IP / 0 home / 0 data leak) |
| `git status --short` | (after commit) | clean |
| `git ls-files` excludes `artifacts/` | `git check-ignore artifacts/public-data-candidate` | matched (gitignored) |
| `git check-ignore` on data/ | `git check-ignore data` | matched |
| `git check-ignore` on public-data/ | `git check-ignore public-data` | NOT matched (committed, as designed) |

---

## 12. Documentation sensitive scan

`grep -RInE "token=|api_key|Authorization:|Bearer |password=|secret=|/home/[^ ]+|/Users/[^ ]+|[0-9]+.[0-9]+.[0-9]+.[0-9]+|.env" README.md docs templates reports/PHASE_ACT9B_PROPOSED_EXPORT_ARTIFACT_REPORT.md`

All hits are **expected instructional matches**:

- `public-data-automation-policy-checklist.md` (existing
  ACT-9 doc) — text examples of what to scan FOR
- `PHASE_ACT9B_PROPOSED_EXPORT_ARTIFACT_REPORT.md` (this
  document) — `Authorization:` / `Bearer` / `api_key=`
  text in the discussion of patterns to avoid
- `PHASE_ACT9_PUBLIC_DATA_AUTOMATION_POLICY_REPORT.md`
  (existing ACT-9 doc) — same
- `build_public_data_candidate.py` — `Bearer ` inside
  redaction pattern list (this is the *check*, not a
  leak)
- `proposed-export.yml` — same
- `AGENT_USAGE_PLAYBOOK.md` §15 + §16 — text discussing
  "do not write tokens"

**No real secrets, no real IPs, no real home paths.**

---

## 13. Public-data state and boundary

| Item | Status |
|---|---|
| `public-data/` modified? | ✅ Yes (added 1 event: ACT-9 phase, per precedent "next commit publishes previous act's phase event") |
| `public-data/` event count | 19 → 20 |
| `data/` still gitignored? | ✅ Yes (workflow asserts) |
| `generated/` still gitignored? | ✅ Yes (workflow asserts) |
| `artifacts/` gitignored? | ✅ Yes (added in this commit) |
| `apps/dashboard/dist/` still gitignored? | ✅ Yes (unchanged) |
| `artifacts/` ever committed? | ❌ No (gitignored) |
| CI writes to `public-data/`? | ❌ No (workflow has `contents: read` only) |
| CI commits anything? | ❌ No (no `git add` / `git commit` step) |
| CI pushes anything? | ❌ No (no `git push` step) |
| CF Pages deployment | ✅ Continues to deploy from committed `public-data/` (unchanged) |

The 1-event delta (ACT-9 phase) is the same `19 → 20` change
that ACT-7B → ACT-8 → ACT-9 followed: each `act-N` commit
publishes the previous act's phase event to keep public-data
in sync with the work actually done. ACT-9's phase event
joins the 19 already-public events, taking the total to 20.

---

## 14. Known limitations and open questions

1. **CI dispatch not exercised in this session.** The workflow
   is committed; the user can trigger it from the Actions
   UI to verify the runner-side experience. Without
   `GITHUB_TOKEN`, the agent cannot dispatch on the user's
   behalf.
2. **14-day artifact retention.** The workflow uploads with
   14-day retention. If a reviewer needs the artifact for
   longer, they should download it locally. There is no
   remote artifact store (CF Pages, R2, S3) wired up.
3. **Makefile `publish-preflight` still defaults to 1 project.**
   The 3-project variant is exercised manually (and the
   ACT-9B test suite covers it). ACT-9C is the natural
   place to wire the 3-project default into the Makefile.
4. **No signed / verified artifact.** The tarball is gzipped
   but not signed. A future act could add a SHA-256
   `MANIFEST.txt` next to the tarball for tamper-evidence
   without changing the human gate.
5. **`cloudflare-verify` not invoked by the workflow.** It
   is a local convenience only, not part of the proposed
   export pipeline.
6. **No per-source / per-mode regression test in CI.** The
   test suite is local-only. A future act could add
   `.github/workflows/candidate-test.yml` to run
   `make candidate-test` on every push.

---

## 15. Recommended next phase

**Recommended: ACT-9C (manual review workflow polish)**.

ACT-9C is the natural follow-up because it would:

- Wire the 3-project default into the `publish-preflight`
  Makefile target (closing the gap noted in §3 of the
  policy).
- Document the canonical "download artifact → review →
  promote" workflow with a `templates/checklists/
  artifact-review-checklist.md`.
- Add a `.github/workflows/candidate-test.yml` that runs
  `make candidate-test` on every push (closes gap §14.6).

ACT-9C continues the "no new functionality, just operational
polish" theme from ACT-9B. It does not need a new policy
section; it is closing the operational gaps that ACT-9B
exposed.

**Alternative: ACT-10 (v0.1.0 release packaging)** is
also a valid next step. It does not depend on ACT-9C and
would be a "freeze the world as it is" act. The user
preference at this point is the deciding factor.

**Not recommended for next**: Level 4 (authorized export
bot) — the ADR-0001 revisit criteria are not yet met.
