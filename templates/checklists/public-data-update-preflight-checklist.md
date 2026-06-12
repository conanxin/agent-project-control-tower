# Public-data Update Preflight — Human Review Checklist

Use this checklist after running `make public-update-preflight` (or
`python3 scripts/public_data_update_preflight.py --plan ...`) and
before any `git add` / `git commit` / `git push` that touches
`public-data/`.

## 1. Preflight result

- [ ] `artifacts/public-data-update-preflight/UPDATE_SUMMARY.md` says
      **PASS** (not FAIL).
- [ ] If FAIL, the failing check name is in the summary. Do **not**
      proceed. Fix the underlying issue and re-run.

## 2. Export plan sanity

- [ ] `config/public-data-export-plan.yml` is the plan you intend.
- [ ] The `projects:` list still matches what the public dashboard
      should show.
- [ ] The `agents:` list still matches who should appear publicly.

## 3. Counts match the plan

- [ ] `PUBLIC_DATA_DIFF.md` shows `project_count` ≥ the number of
      projects in the plan.
- [ ] `project_count` is **not** 1 (the pre-ACT-9C regression).
- [ ] `agent_count` matches the number of agents in the plan.
- [ ] `event_count` looks reasonable (not zero, not exploded).

## 4. BookTrans Desk regression (the ACT-6C gate)

- [ ] `booktrans-desk` `repo` is `conanxin/booktrans-desk`.
- [ ] It is **not** `conanxin-homepage`.
- [ ] Current phase is `S13`.
- [ ] It is **not** `HP-33`.
- [ ] `source_commit` is `16f38b6` (or a newer booktrans-desk commit
      with a documented reason).

## 5. Redaction

- [ ] `REDACTION_RESULT.md` shows `FAIL=0`.
- [ ] If `WARN > 0`, each WARN has been eyeballed and judged safe.

## 6. MANIFEST diff

- [ ] `MANIFEST_BEFORE.json` and `MANIFEST_AFTER.json` differ in the
      way you expected (added events, updated timestamps, etc.).
- [ ] No surprise project_id appeared or disappeared.

## 7. Git diff scope

- [ ] `git status --short` shows only `public-data/`, `site/`, and
      possibly `reports/` as modified.
- [ ] `data/` is **not** in the diff (it should be gitignored).
- [ ] `generated/` is **not** in the diff (it should be gitignored).
- [ ] `artifacts/` is **not** in the diff (it should be gitignored).
- [ ] `apps/dashboard/dist/` is **not** in the diff (gitignored).

## 8. Stage explicitly (never `git add .`)

When the diff looks right, stage **only** what you reviewed:

```bash
git add public-data/registry/projects.yml \
        public-data/registry/agents.yml \
        public-data/MANIFEST.json \
        public-data/events/
git add site/index.embedded.html
```

Then verify:

```bash
git status --short
git diff --cached --stat
```

## 9. Commit and push

```bash
git commit -m "<phase-id>: <what changed in public-data>"
git push
```

Wait 60–90 seconds for Cloudflare Pages + CDN cache, then run the
online verification checklist at
`templates/checklists/online-verification-checklist.md`.

## 10. Online verification (after deploy)

- [ ] `https://control-tower.conanxin.com/` shows the new counts.
- [ ] `https://control-tower.conanxin.com/timeline/` shows the new
      events.
- [ ] `https://control-tower.conanxin.com/projects/booktrans-desk/`
      still shows `conanxin/booktrans-desk` / `S13` / `16f38b6` /
      `PARTIAL`.
- [ ] No token / IP / home path / data-leak strings appear in any
      page.
