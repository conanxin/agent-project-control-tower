# Online Verification Checklist

> Run this after every `git push` to `main` of the tower repo. The
> goal is to confirm the public dashboard is serving the right
> content from the right commit, with no leftover state from a
> previous deploy, and no sensitive data on the page.

## A. Wait for the deploy window

- [ ] Wait **at least 60 seconds** after `git push` for Cloudflare
      Pages to build and deploy.
- [ ] Wait **at least 90 seconds** for the custom-domain edge cache
      to refresh.
- [ ] Do NOT panic-revert during this window. The
      `pages.dev` mirror is often fresh before the custom domain is.

## B. The four core URLs return 200

    for u in / /timeline/ /projects/booktrans-desk/ /agents/local-hermes/; do
      code=$(curl -sL -o /dev/null -w "%{http_code}" "https://control-tower.conanxin.com$u")
      echo "$code  https://control-tower.conanxin.com$u"
    done

Expected:

    200  https://control-tower.conanxin.com/
    200  https://control-tower.conanxin.com/timeline/
    200  https://control-tower.conanxin.com/projects/booktrans-desk/
    200  https://control-tower.conanxin.com/agents/local-hermes/

- [ ] All four 200.

## C. The pages.dev mirror also returns 200

    curl -sL -o /dev/null -w "%{http_code}\n" https://agent-project-control-tower.pages.dev/

Expected: 200.

- [ ] `pages.dev` 200. If it is and the custom domain is not, that
      is a CDN edge cache lag, not a deploy failure. Wait longer.

## D. Content spot-checks (must match)

- [ ] `curl -sL https://control-tower.conanxin.com/projects/booktrans-desk/`
      contains all of:
  - `BookTrans Desk`
  - `S13`
  - `Blocker Fixes and Manual Validation Rerun` (or the new phase name)
  - `16f38b6` (or the new source commit)
  - `conanxin/booktrans-desk`
  - `PARTIAL` (or the new status)
- [ ] The same page does **NOT** contain:
  - `conanxin-homepage` (other than in unrelated `Repository` links)
  - `HP-33`
  - any real home path or token

- [ ] `curl -sL https://control-tower.conanxin.com/` contains
  `3 projects` and `14 events` (or the new totals after the export).

- [ ] `curl -sL https://control-tower.conanxin.com/timeline/`
      contains the latest event per project (S13 for booktrans-desk,
      ACT-6C for the tower, P3B for artvee-gallery, etc.).

## E. Project counts and dashboard totals

- [ ] The home page shows the right number of projects and events.
- [ ] The project list contains exactly:
  - `agent-project-control-tower`
  - `artvee-gallery`
  - `booktrans-desk`
  - and any new project you intended to add.
- [ ] No "ghost" project (a project that was removed but is still
  showing up because the export kept a stale file).

## F. The ACT-6C regression check (specific to this tower)

- [ ] `curl -sL https://control-tower.conanxin.com/projects/booktrans-desk/ | grep -E "conanxin-homepage|HP-33"`
      returns nothing.
- [ ] The `Repo` field on the BookTrans Desk page is
      `conanxin/booktrans-desk`.
- [ ] The current phase is `S13`, not `HP-33`.

If any of these fail, the ACT-6C hotfix regressed. See
`docs/PUBLIC_DATA_EXPORT_PLAYBOOK.md` §7 for the four-question
test that should have caught this.

## G. Live-page sensitive scan (must return nothing)

    for u in / /timeline/ /projects/booktrans-desk/ /agents/local-hermes/; do
      curl -sL "https://control-tower.conanxin.com$u" \
        | grep -nE "api_key=|token=|Authorization:|<REAL_|/home/[^/]+/|/Users/[^/]+/|\.env(\.|$)"
    done

- [ ] Empty output across all four URLs.
- [ ] If anything matches, it is either (a) an obvious false
      positive (e.g. a github.com URL with `.env` in a path that is
      not a file) — document in the deploy log, or (b) a real
      leak — roll back, do not push a fix-and-rebuild into the
      same deploy.

## H. The pages.dev fallback

If the custom domain is stuck and the deploy window has exceeded
5 minutes, check the `pages.dev` mirror:

    curl -sL https://agent-project-control-tower.pages.dev/projects/booktrans-desk/ \
      | grep -E "S13|16f38b6|conanxin/booktrans-desk"

- [ ] `pages.dev` shows the new content. If yes, the issue is the
      custom-domain edge cache; wait. If no, the deploy itself
      failed — check Cloudflare Pages' build log.

## I. Sign-off

- [ ] All four URLs return 200.
- [ ] Spot-checks pass.
- [ ] No ACT-6C regression.
- [ ] Live-page sensitive scan is clean.
- [ ] Working tree is clean (`git status` reports no changes).
- [ ] Latest commit hash is the one intended.

Verified by: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ Date: \_\_\_\_\_\_\_\_

If the deploy window has passed and any of the above still fails,
**roll back** by reverting the public-data commit on `main`. Do not
attempt to "fix forward" inside the same broken deploy; that makes
the rollback harder.
