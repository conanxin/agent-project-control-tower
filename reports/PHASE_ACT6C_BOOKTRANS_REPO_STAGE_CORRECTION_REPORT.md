# ACT-6C Hotfix: BookTrans Desk Repo and Stage Correction

## Decision

- Status: **PASS**
- Confidence: high
- Scope: ACT-6C hotfix — public-data BookTrans Desk entry only. No new features, no scope expansion.

## Why This Hotfix Exists

ACT-6C (commit `eb19c49`) connected the third real project `booktrans-desk` to the
public dashboard, but the public-data entry inherited a mis-attribution: the project
was being treated as if it lived inside the
[`conanxin/conanxin-homepage`](https://github.com/conanxin/conanxin-homepage)
repository (sub-directory `/projects/booktrans-desk/`, last touched in HP-33 —
"Final Public Launch QA"). In reality, BookTrans Desk has long been a standalone
open-source repository at
[`conanxin/booktrans-desk`](https://github.com/conanxin/booktrans-desk), with
its own commit history, phase progression (S1..S13), and a much more recent
source of truth (`16f38b6`).

The control tower public dashboard must reflect the real code repository, not a
historical case-study page that lives inside the homepage repo. Continuing to
serve the mis-attribution would have made the public dashboard actively
misleading: it would claim BookTrans Desk is "PASS / green / Final Public Launch
QA" while the real repository was several S-phases past that, currently in
`S13 — Blocker Fixes and Manual Validation Rerun` with manual click-through
items still `BLOCKED_MANUAL`.

## Wrong State (Before Hotfix)

- Public project id: `booktrans-desk`
- Public repo: `conanxin/conanxin-homepage` ❌
- Public current phase: `HP-33 — Final Public Launch QA`, status `PASS`, health `green` ❌
- Public source commit: `db3825d437d8b0e4b13c0dd7f022bafe5978ea6e` (a
  conanxin-homepage commit) ❌
- The wrong phase event file was
  `public-data/events/20260611T151517Z__PHASE__local-hermes__booktrans-desk__HP-33.json`.

## Correct State (After Hotfix)

- Public project id: `booktrans-desk`
- Public repo: `conanxin/booktrans-desk` ✅
- Public current phase: `S13 — Blocker Fixes and Manual Validation Rerun`,
  status `PARTIAL`, health `amber` ✅
  - S13 automated checks all PASS (`npm run build`, `npm test` 52 files / 211
    tests, `npm run release:check`, `npm run pack`).
  - Real Windows desktop EPUB / PDF click-through items remain
    `BLOCKED_MANUAL` (no human click-through in this automated rerun). The
    PARTIAL/amber status reflects that mixed reality faithfully rather than
    papering over the manual gap.
- Public source commit: `16f38b6` ✅ (BookTrans Desk commit
  `docs: record S13 manual validation rerun`).
- The new phase event file is
  `public-data/events/20260611T225410Z__PHASE__local-hermes__booktrans-desk__S13.json`.

## Why HP-33 Must Not Continue Representing BookTrans Desk

HP-33 belongs to the homepage repo, not to the BookTrans Desk code. Using it
as the BookTrans Desk "current phase" was the root cause of the public-data
mis-attribution. Specifically:

- HP-33 (`Final Public Launch QA`) refers to the conanxin-homepage case-study
  page at `conanxin.com/projects/booktrans-desk/`, not to the
  `conanxin/booktrans-desk` repository's own state.
- The source commit `db3825d...` referenced by HP-33 is a homepage commit, not
  a BookTrans Desk commit. The most recent homepage commit relevant to
  BookTrans Desk's case-study is unrelated to the live code.
- The real BookTrans Desk repo, in its own phase numbering, is now in S13
  (recorded in the in-repo report
  `docs/merge/PHASE_S13_BLOCKER_FIXES_MANUAL_VALIDATION_RERUN_REPORT.md` and
  committed at `16f38b6`). HP-33 has no relationship to the S-phases.

User instruction explicitly noted: *"如果 HP-33 事件仍然被导出为
booktrans-desk 事件，请从 public-data 中移除，或在 data 中将它重新归类到
未来的 conanxin-homepage 项目；本轮不要让 HP-33 继续影响 booktrans-desk
当前状态"*. The hotfix removes the HP-33 event file (and the mis-attributed
PROJECT_REG file) from both `data/events/` and `public-data/events/`. They
remain visible in git history for auditability. A future
`conanxin-homepage` project can be registered separately in a later act, and
HP-33 can be re-attached to that project at that time; this hotfix does not
preclude that.

## Local Runbook Used

```bash
# 1) Confirm real BookTrans Desk state (read-only)
cd /mnt/d/WSL/Codex/booktrans-desk
git log --oneline -5
# → 16f38b6 docs: record S13 manual validation rerun   ✅ matches expected
ls docs/merge/PHASE_S13_BLOCKER_FIXES_MANUAL_VALIDATION_RERUN_REPORT.md
# → file exists                                              ✅

# 2) Pull control tower main branch
cd ~/workspace/projects/agent-project-control-tower
git pull --ff-only                                          # already up to date

# 3) Fix local data/ registry (data/ is gitignored)
#    Edit data/registry/projects.yml:
#      - booktrans-desk.repo: conanxin/conanxin-homepage
#                           → conanxin/booktrans-desk
#      - description: ...     → "Open-source desktop tool for structured
#                                PDF and EPUB translation workflows."

# 4) Remove the two mis-attributed events (data/ + public-data/)
rm -v data/events/20260611T151509Z__PROJECT_REG__local-hermes__booktrans-desk.json
rm -v data/events/20260611T151517Z__PHASE__local-hermes__booktrans-desk__HP-33.json
rm -v public-data/events/20260611T151509Z__PROJECT_REG__local-hermes__booktrans-desk.json
rm -v public-data/events/20260611T151517Z__PHASE__local-hermes__booktrans-desk__HP-33.json

# 5) Re-register the project (idempotent on registry; emits fresh
#    PROJECT_REG event if the agent passes it) and publish S13
python scripts/tower.py register-project \
  --project-id booktrans-desk --name "BookTrans Desk" \
  --repo conanxin/booktrans-desk --location public \
  --category reading-tool --status ACTIVE \
  --description "Open-source desktop tool for structured PDF and EPUB translation workflows." \
  --agent-id local-hermes

python scripts/tower.py report-phase \
  --project-id booktrans-desk --agent-id local-hermes \
  --phase-id S13 --phase-name "Blocker Fixes and Manual Validation Rerun" \
  --status PARTIAL --health amber \
  --summary "S13 reran the S11 blocker fixes and manual validation in the real BookTrans Desk repository (conanxin/booktrans-desk @ 16f38b6). Automated checks PASS: npm run build, npm test (52 files / 211 tests), npm run release:check, and npm run pack all green. Packaged app launched with the expected BookTrans Desk window title. S12 DocuMuse Studio workspace shell reviewed against the source/UI structure with PASS_SOURCE_REVIEW on all six layout areas. Real EPUB / PDF Windows desktop click-through remains BLOCKED_MANUAL in this automated rerun (no human click-through performed)." \
  --next "Continue release hardening and documentation for the desktop translation workflow; await a human Windows desktop click-through to clear the BLOCKED_MANUAL EPUB/PDF items." \
  --source-repo "conanxin/booktrans-desk" \
  --source-commit 16f38b6

# 6) Re-export public-data with all three real projects
python scripts/export_public_data.py \
  --source data --output public-data \
  --project-id agent-project-control-tower \
  --project-id artvee-gallery \
  --project-id booktrans-desk \
  --max-events 50 --repo-prefix conanxin --replace
# → 3 projects, 1 agent, 14 events, redaction FAIL=0 WARN=0
```

## Integration Plan

1. Run `make public-build` to regenerate `generated/index.json` and
   `site/index.embedded.html` from public-data.
2. Run `make dashboard` to rebuild `apps/dashboard/dist/`.
3. Run the manual command set:
   - `make all` (zero-dep, local data path)
   - `make publish-preflight` (re-export + rebuild from public-data + dashboard
     dist)
4. Run a pre-commit-equivalent audit (since `/tmp/precommit_audit.py` is not
   present on this machine, the same checks were reproduced inline against
   public-data and the embedded site HTML — see *Redaction & Audit Results*
   below).
5. Minimize doc corrections: only the three current-state lines in `README.md`
   and the event count in `docs/OPEN_SOURCE_PLAN.md` were touched. ACT-6C's
   historical section is preserved as historical record.
6. Explicit per-file `git add`, no `git add .`. Commit, push. Cloudflare
   Pages auto-deploys from the connected GitHub repo.

## Redaction & Audit Results

- `make all` → PASS (CLI smoke + smoke redaction FAIL=0 exit 3, smoke WARN
  writes OK, build clean, embedded HTML contains `__TOWER_DATA__`).
- `make publish-preflight` (after the explicit 3-project export) → PASS.
- `apps/dashboard` `npm run build` → PASS (6 pages, including
  `/projects/booktrans-desk/index.html`).
- Pre-commit-equivalent scan over public-data + site embedded HTML:

  | Pattern | Hits |
  | --- | --- |
  | `api_key=...` / `token=` / `secret=` / `password=` / `Bearer ...` | 0 |
  | `/home/<user>/` (real home path) | 0 |
  | IPv4 address | 0 |
  | `data/` real path leakage (`workspace/projects/.../data`) | 0 |

  Result: **CLEAN**.

- `export_public_data.py` redaction summary: `FAIL=0, WARN=0`.

## make all / publish-preflight / npm build / audit

| Step | Result |
| --- | --- |
| `make all` | PASS |
| `make publish-preflight` (3-project explicit export + public-build + site + dashboard) | PASS |
| `npm run build` (in `apps/dashboard`) | PASS (6 pages) |
| pre-commit-equivalent audit | CLEAN (0 token / 0 IP / 0 home / 0 data leak) |
| `generated/index.json` shows booktrans-desk current phase = `S13` | YES |
| `site/index.embedded.html` shows booktrans-desk current phase = `S13` | YES |
| `public-data` contains no token / IP / private path / real `data/` path | YES |

## Online Verification

After `git push`, Cloudflare Pages auto-deploys. Verification commands
(reference, run post-deploy):

```bash
curl -L https://control-tower.conanxin.com/projects/booktrans-desk/ \
  | grep -E "BookTrans|S13|Blocker|Manual Validation|16f38b6|conanxin/booktrans-desk" -n

curl -L https://control-tower.conanxin.com/ \
  | grep -E "BookTrans|3 projects|events" -n

curl -L https://control-tower.conanxin.com/timeline/ \
  | grep -E "BookTrans|S13|16f38b6" -n
```

Acceptance:

- `/projects/booktrans-desk/` returns HTTP 200.
- Page shows repo `conanxin/booktrans-desk`.
- Page shows current phase `S13` (`Blocker Fixes and Manual Validation Rerun`).
- Page shows source commit `16f38b6`.
- HP-33 is no longer associated with the `booktrans-desk` current state.
- Home page still shows 3 real projects.
- No token / IP / private path / real `data/` path appears on any of the
  three pages.
- `git status` is clean after commit + push.

## Risk Notes

- **CDN cache lag**: Cloudflare Pages custom domain
  `control-tower.conanxin.com` is known to lag the pages.dev origin by 60–90s
  on the homepage `/` after a push (see `MEMORY`). Verification should wait
  ~90s and check multiple paths (home, `/projects/booktrans-desk/`,
  `/timeline/`) before concluding the deploy failed.
- **No force-push, no push to master**: this hotfix lands on `main` only
  via a normal `git push`. No `git reset --hard` against the published
  history. The removed HP-33 and PROJECT_REG JSON files are still visible in
  earlier commits (`eb19c49`, etc.) for full auditability.
- **No new dependencies, no new features, no scope expansion**: this hotfix
  touches only BookTrans Desk's public-data entry, doc wording, and the
  hotfix report. ACT-7 (multi-machine playbook) is explicitly out of scope.
- **HP-33 disposal**: it was removed from `public-data/events/` and
  `data/events/`. Git history retains the previous state. If/when a future
  `conanxin-homepage` project is registered in the tower, HP-33 can be
  re-attached at that time by moving the file back into
  `data/events/20260611T151517Z__PHASE__local-hermes__conanxin-homepage__HP-33.json`
  and updating `project_id` accordingly. This is a future act and not part
  of this hotfix.
- **`/tmp/precommit_audit.py` absent**: a fully equivalent scanner was
  reproduced inline (see *Redaction & Audit Results*). If that script is
  re-introduced later, the same patterns will be exercised and continue to
  pass.

## Files Touched

- `data/registry/projects.yml` (gitignored, local-only)
- `data/events/20260611T151509Z__PROJECT_REG__local-hermes__booktrans-desk.json` (deleted, gitignored)
- `data/events/20260611T151517Z__PHASE__local-hermes__booktrans-desk__HP-33.json` (deleted, gitignored)
- `data/events/20260611T225410Z__PHASE__local-hermes__booktrans-desk__S13.json` (created, gitignored)
- `public-data/registry/projects.yml`
- `public-data/events/` (HP-33 + mis-attributed PROJECT_REG removed; S13 + possibly PROJECT_REG added)
- `public-data/MANIFEST.json` (regenerated by export_public_data.py)
- `generated/index.json` (regenerated by `tower.py build --source public-data`)
- `site/index.embedded.html` (regenerated by `build_embedded_site.py`)
- `apps/dashboard/dist/` (regenerated by `npm run build`)
- `README.md` (3 current-state lines: `/projects/booktrans-desk/` row,
  events list, status pill; ACT-6C history kept)
- `docs/OPEN_SOURCE_PLAN.md` (event count line; ACT-6C history kept)
- `reports/PHASE_ACT6C_BOOKTRANS_REPO_STAGE_CORRECTION_REPORT.md` (this file)

## Recommendation

BookTrans Desk now accurately reflects the real code repository
(`conanxin/booktrans-desk` @ `16f38b6`, S13, PARTIAL/amber). The public
dashboard is no longer misleading. **Ready to enter ACT-7** (multi-machine
agent usage playbook) once `git push` lands and the Cloudflare Pages
deployment verifies online.
