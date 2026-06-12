# Public-data Automation Policy — Pre-Export Checklist

> **Use this checklist every time you run
> `export_public_data.py --replace`.** ACT-9 made it
> mandatory. A "yes" on every item is the only condition
> under which the export may proceed.
>
> This checklist is the human-side mirror of
> `docs/PUBLIC_DATA_AUTOMATION_POLICY.md`. The policy says
> *what* the rules are; this checklist says *how* to verify
> them in 5 minutes.

---

## How to use this

1. Open the checklist in your editor.
2. For each item, mark `[x]` only after you have *personally
   verified* the answer, not after you have assumed it.
3. If any item is unchecked, **do not run `--replace`**. Fix
   the underlying issue first, then re-run the checklist.
4. After export, paste the redaction summary and your
   `git status --short` output at the bottom of the run
   log. They are the audit trail.

---

## A. Boundary checks (must all be YES)

- [ ] **`data/` is still gitignored.** Run `git check-ignore
      data/`. It must report a path (meaning `data/` is
      ignored). If it does not, **stop** and investigate
      before any export.
- [ ] **No CI step is configured to write `public-data/`
      automatically.** Open `.github/workflows/*.yml` (or
      your CI config). Confirm that no workflow runs
      `export_public_data.py --source data --output
      public-data` and `git add`s the result. The only
      workflows that touch `public-data/` are the ones
      that *validate* and *deploy from committed
      `public-data/`*.
- [ ] **No `.gitignore` change is in the staged set.** Run
      `git status --short` and confirm `.gitignore` is not
      listed. If it is, **stop** and inspect the diff.
- [ ] **`public-data/` change is explicitly staged.** Run
      `git status --short public-data/` and confirm every
      file is listed with `M ` or `A ` (modified/added,
      space-then). If any path is missing, add it
      explicitly. Never `git add .`.

## B. Redaction (must all be YES)

- [ ] **Redaction summary shows `FAIL=0`.** Look at the
      last line of the export output. It must say
      `redaction summary: FAIL=0`. If `FAIL > 0`, the
      export was aborted by the scanner. **Do not
      bypass**; find the offending event, fix the source
      field, and re-export.
- [ ] **Any `WARN` is justified by a human eye-check.** A
      WARN is not a fail, but it is also not a pass. For
      each WARN, open the offending event and decide: is
      this a real secret, a real path, or a false
      positive? If false positive, document the
      justification in the run log. If real secret, fix
      the source.
- [ ] **No `data/` event references a real home path, IP,
      or token.** Even if the scanner passed, eyeball
      `data/events/*.json` for any string that looks like
      `/home/<yourname>/` or `192.168.x.x` or
      `sk-...`. The scanner is regex; you are the
      semantic check.

## C. Project identity (the ACT-6C gate)

This is the section that catches the bug the redaction
scanner cannot. All six items must be YES.

- [ ] **`project_id` exists in `data/registry/projects.yml`.**
      For each new event, confirm its `project_id` is a
      key in the projects registry. If not, run
      `register-project` first and re-export.
- [ ] **`repo` is the project's own code repository, not a
      homepage sub-directory.** For `booktrans-desk`,
      `repo` must be `conanxin/booktrans-desk`, not
      `conanxin/conanxin-homepage`. A homepage is a
      *separate* project (`conanxin-homepage`), not a
      sub-claim on the tool.
- [ ] **`phase_id` belongs to this project.** A homepage's
      `HP-N` phase is not a tool's `S-N` phase. A tool's
      `S-N` is not a homepage's `HP-N`. Cross-check the
      project's own phase numbering convention.
- [ ] **`source_commit` is from the project's own `git
      log`.** Run `git -C <project-path> log --oneline -5`
      and confirm the `source_commit` appears. A commit
      from a different repo (a homepage, a portfolio, a
      case-study) is invalid.
- [ ] **`status` / `health` is honest, not optimistic.**
      If a manual click-through or external integration is
      still pending, the status is `PARTIAL / amber`, not
      `PASS / green`. BookTrans Desk S13 (commit
      `16f38b6`) is the canonical example.
- [ ] **`summary` / `next` / `failure_reason` do not
      contain cross-project confusion.** A summary that
      mentions a different project's phase id or commit
      hash is a mis-attribution signal even if the
      structured fields are right.

## D. Manifest and dashboard

- [ ] **`public-data/MANIFEST.json` diff is reviewed.** Run
      `git diff public-data/MANIFEST.json`. Confirm
      `project_filter`, `agent_filter`, `max_events_per_project`,
      and `event_count` match the intent. An
      unexpected change in `event_count` means a new event
      slipped through the filter; investigate before
      pushing.
- [ ] **Online verification is run after push.** Within
      60–90s of `git push`, curl the four core URLs:

      ```bash
      for u in / /timeline/ /projects/<id>/ /agents/<id>/; do
        code=$(curl -sL -o /dev/null -w "%{http_code}" \
          "https://control-tower.conanxin.com$u")
        echo "$code  $u"
      done
      ```

      All four must be 200. If `pages.dev` is fresh and
      the custom domain is lagging, wait 60–90s and
      retry; do not panic-revert.
- [ ] **ACT-6C regression spot-check.** Curl
      `https://control-tower.conanxin.com/projects/booktrans-desk/`
      and confirm it shows `conanxin/booktrans-desk` /
      `S13` / `16f38b6` / `PARTIAL`. If `conanxin-homepage`
      or `HP-33` reappears, the mis-attribution regression
      is back. Revert the export and investigate.

## E. Run log (paste after export)

```text
date:           <YYYY-MM-DD>
actor:          <your handle or agent id>
export command: <the exact export_public_data.py invocation>
redaction:      FAIL=<n> WARN=<n>
event_count:    <before> → <after>
project_filter: <list>
agent_filter:   <list>
git status:     <paste the git status --short output here>
online check:   <paste the curl results>
notes:          <anything you want the next reviewer to know>
```

The run log is the audit trail. It is the only artifact
that lets a future act reconstruct *why* a particular
export was accepted.

---

## F. What this checklist is NOT

- It is not a substitute for reading the policy in
  `docs/PUBLIC_DATA_AUTOMATION_POLICY.md`. The policy
  is the *what*; this checklist is the *how*.
- It is not enforced by automation. The redaction scanner
  is a regex; the alignment checker is a static scan;
  neither one implements this checklist. This checklist
  is human-only.
- It is not optional. ACT-9 made it mandatory. A future
  act that proposes to skip an item in the checklist
  must amend this file (with rationale) in the same
  commit.
