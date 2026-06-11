# Redaction Checklist

> Run this before any change to `public-data/`, and as a final pass
> before `git push`. The redaction scanner catches obvious mistakes
> automatically (it is wired into `export_public_data.py`), but a
> human review is still the second gate. This checklist is the
> minimum that human review should walk.

## A. Let the scanner do the first pass

- [ ] `python scripts/export_public_data.py` printed
      `redaction summary: FAIL=0, WARN=0` (or `WARN > 0` only if
      every warn was reviewed and confirmed intentional).
- [ ] If `FAIL > 0`, the export did **not** write. Find the offending
      field (the CLI lists which), rewrite it, and re-run.

## B. Manually scan the public-data files for the patterns

For each file under `public-data/`, run:

    grep -nE "api_key=|token=|Authorization:|<REAL_|/home/[^/]+/|/Users/[^/]+/|\b[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+\b|\.env(\.|$)"

- [ ] No real match. (`-nE` is the same as `-E` here; the `n` just
      adds line numbers for context.)
- [ ] Any match is either (a) intentional placeholder text in a
      docs-style field, or (b) an obvious false positive (e.g. a
      GitHub permalink that contains a numeric path). Document each
      match in the commit message body so the next reviewer can
      verify.

## C. Field-by-field check (high-risk fields only)

For each event file in `public-data/events/`, confirm:

| Field | Sensitive? | Check |
| --- | --- | --- |
| `summary` | yes | no real home path, IP, token, .env reference |
| `description` | yes | same |
| `next` | yes | same |
| `failure_reason` | yes | same; only the short root cause, not the raw error |
| `design_reason` | yes | same |
| `impact_analysis` | yes | same |
| `release_url` | low | should be a github.com / public URL; if private, do not export |
| `source_repo` | low | `owner/repo` shape; should be the real source repo |
| `source_commit` | low | a git SHA; ok to be public |
| `source_commit_url` | low | github.com URL; ok to be public |
| `project_id`, `agent_id`, `phase_id` | none | identifiers only |

For each registry file in `public-data/registry/`:

- `projects.yml`: `repo`, `description`, `name`. All three reviewed.
- `agents.yml`: `name`, `display_name`, `operator`, `machine`. All
  four should be de-sanitized tags, not real names/hosts/IPs.

## D. The five patterns the scanner is opinionated about

The scanner uses the patterns in `scripts/lib/redaction.py`. Be aware
of them when writing summaries:

1. `Authorization: Bearer *** / `bearer <token>` → **FAIL**.
2. `name=value` where name ∈ {token, api_key, password, secret, ...}
   and value is 6+ chars → **FAIL**.
3. `.env` reference (e.g. `.env.local`) → **WARN**.
4. User home paths (`/home/<user>/...`, `/Users/<user>/...`,
   `C:\Users\<user>\...`) → **WARN** (sometimes **FAIL**).
5. Any IPv4 address (`\b\d+\.\d+\.\d+\.\d+\b`) → **WARN**.

If you have a reason to include a pattern that would trigger, **do not
work around the scanner**; rewrite the summary to avoid the pattern.
The scanner exists to prevent accidents, not to be argued with.

## E. The one pattern the scanner does NOT catch

- Real **usernames** (e.g. your operator handle, if it is also your
  GitHub login). The scanner treats these as legitimate. The
  reviewer is responsible for confirming that the chosen handle is
  one you are happy to publish. Use a stable handle, not your real
  name.
- Real **GitHub org names** in `repo` fields. These are public
  already; including them is the point. The reviewer is
  responsible for confirming the org is the one you intend (not a
  typo to your personal account, etc.).

## F. Before you sign off

- [ ] `cat public-data/MANIFEST.json` shows the project filter and
      event count you expect.
- [ ] `cat public-data/registry/projects.yml` shows the right `repo`
      for every project.
- [ ] `ls public-data/events/` only contains events that belong to
      the project they claim to belong to. In particular, no
      `booktrans-desk` event should have `source_repo=conanxin-homepage`
      (and no `conanxin-homepage` event should be filed under
      `booktrans-desk`).
- [ ] You can describe in one sentence why each `WARN` (if any) is
      intentional. If you cannot, treat it as a `FAIL` and rewrite
      the field.

## G. When in doubt

Cut the field. A short summary that says "Fixed blocker" is better
than a long one that triggers a redaction warn. The dashboard is for
progress tracking, not for telling the full story.
