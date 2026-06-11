# Public-data Review Checklist

> Run this BEFORE `git add public-data/` and `git commit`. This is the
> second gate (after the redaction scanner) and the only gate that
> catches the kinds of mistakes the scanner is not designed for:
> mis-attribution, stale state, and "looks fine but is the wrong
> project".

## A. The diff you are about to push

- [ ] `git diff -- public-data/` is short enough to read in one
      sitting. If it is not, you are pushing too much in one commit.
- [ ] Every added/modified file is in this list:
  - `public-data/registry/projects.yml`
  - `public-data/registry/agents.yml`
  - `public-data/MANIFEST.json`
  - `public-data/events/<one or more YYYYMMDDTHHMMSSZ__*__.json>`
  No other paths under `public-data/` should be touched unless you
  have a specific reason.

## B. `public-data/registry/projects.yml` — the four-question test

For each project entry, answer in writing (in the commit message body
if you like):

1. **What is the real source repo of this project?** Open the
   project's actual GitHub repo. Confirm `repo:` here matches it.
2. **What is the latest commit in that repo right now?** Run
   `git log --oneline -5` there. The new `report-phase` event should
   reference that hash, not a stale one.
3. **What is the project's own phase numbering?** Use it. If the
   project has no phase numbering, invent `P1`/`P2`/... but do not
   borrow from a case-study page.
4. **Is the case-study page's status the same as the code's
   status?** If they disagree, the **code wins** for the tower.

The ACT-6C bug was failing #1 and #3 for `booktrans-desk`: the entry
pointed at `conanxin/conanxin-homepage` (case study) instead of
`conanxin/booktrans-desk` (code), and used `HP-33` (case study) as the
phase id instead of `S13` (code). Do not let it come back.

## C. `public-data/registry/projects.yml` — the regression check

- [ ] `booktrans-desk.repo` is `conanxin/booktrans-desk`, not
      `conanxin/conanxin-homepage` and not anything containing
      `homepage`.
- [ ] `artvee-gallery.repo` is `conanxin/artvee-library`.
- [ ] `agent-project-control-tower.repo` is
      `conanxin/agent-project-control-tower`.
- [ ] If a new project was added, its `repo` was opened and
      verified by the reviewer (not by the agent alone).

## D. `public-data/events/` — the mis-attribution check

- [ ] No file under `public-data/events/` has a `project_id` of
      `booktrans-desk` and a `source_repo` of `conanxin-homepage`.
- [ ] No file has a `project_id` of `booktrans-desk` and a
      `phase_id` of `HP-33` (unless the team has registered
      `conanxin-homepage` as a separate project and reclassified
      HP-33 to it).
- [ ] No file has a `project_id` of `<some project>` and a
      `source_repo` that does not match the project's registered
      `repo`.
- [ ] For each event, the `source_commit` actually exists in the
      `source_repo` at the time of the export. (Spot-check by
      `curl https://api.github.com/repos/<owner>/<repo>/commits/<sha>`.)

## E. `public-data/events/` — the staleness check

- [ ] The latest event per project is the one you intend to be
      "current" on the dashboard. If the dashboard would show a
      stale phase as current, **fix it before pushing**.
- [ ] If you intended to retire an old event from the public
      dataset, you removed it from **both** `data/events/` and
      `public-data/events/`. (Otherwise the next `export_public_data.py
      --replace` will put it back.)
- [ ] No file is named with a timestamp that is older than the
      latest event for that project unless there is an explanation
      (e.g. re-importing a backed-up event).

## F. `public-data/MANIFEST.json` — the receipt

- [ ] `source` is `data`. Not `examples`.
- [ ] `project_filter` lists exactly the projects you want on the
      dashboard, in the order you want.
- [ ] `event_count` matches the count of files in
      `public-data/events/`.
- [ ] `max_events_per_project` is at least the per-project event
      count. (If it is less, the oldest events are being silently
      dropped; that may be intentional but should be documented.)
- [ ] `repo_prefix` is the GitHub org you want to appear in public
      `repo` fields.

## G. Sanity check the dashboard preview locally

Before pushing, regenerate the artifacts and inspect them locally:

    make public-build
    make site-only
    make dashboard

- [ ] `generated/index.json` shows the projects, current phases, and
      commit hashes you expect.
- [ ] `site/index.embedded.html` is consistent with
      `generated/index.json` (the embedded copy is generated from
      the same source).
- [ ] `apps/dashboard/dist/projects/booktrans-desk/index.html` shows
      `S13`, `16f38b6`, `conanxin/booktrans-desk`, `PARTIAL`.
- [ ] The four pages you care about (home, timeline, project,
      agent) contain no obvious leftover from a previous deploy
      (e.g. an old project name, a removed phase, etc.).

## H. The "no go" signals — stop and fix before pushing

If you see any of these, do not push; fix and re-export:

- `redaction summary: FAIL=1` (or more) — the export refused to
  write. Find the field and rewrite.
- `booktrans-desk` `repo` is not `conanxin/booktrans-desk`.
- `booktrans-desk` current phase is not `S13`.
- `booktrans-desk` source commit is not `16f38b6`.
- Any project page references `conanxin-homepage` or `HP-33` where
  it should reference the real source repo or the project's own
  phase id.
- The diff contains a real home path, IP, token, or .env reference
  in a `summary` / `next` / `description` field.
- The commit message does not start with `ACT-N:`, `HOTFIX-N:`, or
  `<project-id>:`.

## I. Sign-off

Reviewer: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ Date: \_\_\_\_\_\_\_\_

Reviewed against:
- `docs/AGENT_USAGE_PLAYBOOK.md` §10 (export to public-data)
- `docs/PUBLIC_DATA_EXPORT_PLAYBOOK.md` §7 (mis-attribution lesson)
- `templates/checklists/redaction-checklist.md` (privacy review)
