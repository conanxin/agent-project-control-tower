# Proposed Export Artifact — Human Review Checklist (ACT-9C)

**Use this checklist every time you review a `public-data-candidate.tar.gz` artifact** (locally, or downloaded from a GitHub Actions run).

The candidate artifact is a **proposal only**. It has NOT been published,
committed, or pushed. Publishing is a separate, human-gated step.

---

## 0. Provenance

- [ ] Artifact was produced by `make candidate` (NOT by writing to `public-data/` directly)
- [ ] CANDIDATE_SUMMARY.md shows the **plan file path** (e.g. `config/public-data-export-plan.yml`)
- [ ] CANDIDATE_SUMMARY.md shows the **plan name** (`default-public-dashboard`)
- [ ] CANDIDATE_SUMMARY.md's `source mode` matches the intent:
  - `data` = real candidate (local-hermes only)
  - `examples` = fixture (CI-safe)
  - `public-data` = reference / no-op

## 1. Plan alignment (ACT-9C)

- [ ] Open `config/public-data-export-plan.yml` from this repo
- [ ] Confirm the candidate's `project_filter` matches the plan's `projects:` list (set-equal)
- [ ] Confirm the candidate's `agent_filter` matches the plan's `agents:` list (set-equal)
- [ ] Confirm the plan's `policy:` block is still aligned with the latest
      `docs/PUBLIC_DATA_AUTOMATION_POLICY.md` (CI may validate; CI may NOT commit or push)

## 2. Counts

- [ ] `project_count` in CANDIDATE_SUMMARY.md is what you expect (currently 3)
- [ ] `agent_count` is what you expect (currently 2)
- [ ] `event_count` matches the **delta** you intended
- [ ] No unexpected `registry_files_added` / `registry_files_removed` in MANIFEST_DIFF.md

## 3. Project identity (per project)

For each project in the candidate (`registry/projects.yml`):

- [ ] `repo` is the **real** GitHub repo (e.g. `conanxin/booktrans-desk`, NOT `conanxin/conanxin-homepage`)
- [ ] `location` is `public` (not `local`)
- [ ] `status` matches the live project's status
- [ ] The most recent PHASE_REPORT event's `phase_id` matches the live project's current phase
- [ ] The most recent PHASE_REPORT event's `source_commit` matches the live project's HEAD

## 4. Redaction

- [ ] Open `reports/REDACTION_REPORT.md`
- [ ] `FAIL` count is **0** (if not, refuse to publish)
- [ ] `WARN` count is 0, OR each WARN is explicitly accepted in writing
- [ ] No token-shaped strings (Bearer, api_key=, token=) in any registry/event file
- [ ] No IP addresses (raw `x.y.z.w` patterns) in any registry/event file
- [ ] No `data/` or `generated/` absolute paths leaked
- [ ] No `.env` references or literal secrets

## 5. CI behavior

- [ ] The proposed-export workflow ran with `source=public-data` OR `source=examples`
      (CI MUST NEVER run with `source=data` — data/ is gitignored on runners)
- [ ] The artifact's `public-data-candidate.tar.gz` was uploaded, NOT committed to a branch
- [ ] The workflow did NOT push to a branch or trigger a deployment
- [ ] No Cloudflare API tokens, GitHub tokens, or other secrets are visible in the run logs

## 6. Diff vs current public-data

- [ ] `MANIFEST_DIFF.md` shows the expected delta
- [ ] No project appeared that the plan does not list
- [ ] No project disappeared that the plan still lists
- [ ] `delta_events` is positive and bounded by what you expected

## 7. Decision

- [ ] **APPROVED** — proceed to step 8
- [ ] **REJECTED** — file an issue / describe the blocker, do NOT publish
- [ ] **APPROVED WITH CHANGES** — describe required changes, request a new candidate, re-review

## 8. Publish (only after APPROVED)

Run on `local-hermes` (the only machine that has `data/`):

```bash
# Refresh public-data/ from data/ using the tracked plan
python scripts/export_public_data.py \
    --plan config/public-data-export-plan.yml \
    --replace

# Sanity-check the regenerated tree
make all
make publish-preflight

# Verify there is exactly one diff against main (the public-data refresh)
git status --short
git diff --stat

# Explicit per-file add (never `git add .`); see ACT-9C commit policy
git add public-data/MANIFEST.json \
        public-data/registry/projects.yml \
        public-data/registry/agents.yml \
        public-data/events/*.json \
        site/index.embedded.html

git commit -m "ACT-N: refresh public-data from data/ (see reports/...)"
git push
```

Cloudflare Pages will auto-deploy from `main`. Wait 60–90 s, then
re-verify with `curl -L https://control-tower.conanxin.com/`.

## Why this checklist exists

Pre-ACT-9C, every artifact review was ad-hoc: the reviewer trusted
their memory of which projects should be in public-data/, and the
export was driven by a Makefile default (`PUBLIC_DATA_PROJECT=...`)
that was easy to forget. ACT-9C added the tracked plan file so the
"what is allowed in public-data?" question has a single, reviewable
answer — and this checklist is the human-facing surface of that
contract.
