# Pre-flight Checklist

> Run this before `git commit` on the tower repo, especially before any
> change to `public-data/`. The goal is to catch the small set of
> mistakes that have actually cost us time: mis-attribution, leaking
> `data/`, leaking `generated/`, optimistic `PASS`, and missing
> redaction review.

## A. Working tree state

- [ ] `git status --short` shows only the files you intend to change.
- [ ] No line begins with `?? data/` or `M data/`. `data/` is
      gitignored and **must not** appear in `git status` as a tracked
      or staged change.
- [ ] No line begins with `?? generated/` or `M generated/`.
      `generated/` is gitignored.
- [ ] No line begins with `?? site/dist/` or `M site/dist/`. The Astro
      dashboard dist is gitignored.
- [ ] No `.env`, `*.local`, `node_modules/`, `__pycache__/`, or `.venv/`
      lines.

## B. What you are about to add

For each `A ` (added) line in `git status --short`, confirm the file
belongs in this commit. Be especially careful with:

- `public-data/registry/projects.yml` — every `repo` field must point
  at the **real source repo** for that project, not a homepage
  sub-directory. See `docs/PUBLIC_DATA_EXPORT_PLAYBOOK.md` §7.
- `public-data/events/*.json` — every event's `project_id` must match
  the project whose history it should belong to. If you see an event
  whose `source_repo` is a homepage, it does not belong to the
  underlying tool's current state.
- `public-data/MANIFEST.json` — `event_count` should be what you
  expect. A drop without an explanation is a sign that a project
  got filtered out accidentally.
- `README.md`, `docs/*.md` — the changes you are about to push are
  what you think they are.
- `reports/*.md` — the new report is the right one for this phase.

For each `M ` (modified) line, run `git diff -- <file>` and confirm
the change is intentional.

For each `D ` (deleted) line, confirm the file is actually stale
(`public-data/events/HP-33.json` is a fine delete after the ACT-6C
hotfix; deleting `public-data/MANIFEST.json` is not).

## C. No `git add .` was used

- [ ] You can list every file you `git add`-ed by hand. If you used
      `git add .`, the previous step (`git status --short`) was
      not enough — undo with `git reset HEAD -- .` and re-add
      explicitly.
- [ ] No untracked files were pulled in by accident.

## D. No secrets / paths / IPs in the diff

Run:

    git diff --cached | grep -nE "api_key=|token=|Authorization:|<REAL_|/home/[^/]+/|/Users/[^/]+/|\b[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+\b"

- [ ] Output is empty **or** every match is intentional placeholder
      text (e.g. a docs example that explicitly says "do not write
      token" — those are fine).

## E. Re-confirm the data / public-data split

- [ ] `data/` is still gitignored. `cat .gitignore | grep ^data/$`.
- [ ] `generated/` is still gitignored. `cat .gitignore | grep ^generated/$`.
- [ ] `public-data/` is the only online data source. There is no other
      committed JSON/HTML being served by the dashboard.

## F. Commit message

- [ ] The first line starts with `ACT-N:`, `HOTFIX-N:`, or
      `<project-id>:` (kebab-case project, e.g. `booktrans-desk:`).
- [ ] The body briefly explains **what changed and why**, not just
      what files were touched.
- [ ] No secrets in the commit message.

## G. Push target

- [ ] `git branch --show-current` is `main`. Never push to `master`.
- [ ] No `--force` flag. Force-push on the public repo orphans every
      other agent's local clone.

## H. After push

- [ ] Wait 60-90s for Cloudflare Pages + CDN edge cache to refresh.
- [ ] Run `templates/checklists/online-verification-checklist.md`.
- [ ] If the custom-domain edge is lagging while `pages.dev` is
      fresh, that is a CDN glitch — do not panic-revert.
