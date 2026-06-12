# ADR-0001: Public-data Automation Boundary

| | |
| --- | --- |
| **Status** | Accepted |
| **Date** | 2026-06-12 |
| **Deciders** | conanxin (project owner), local-hermes (orchestrator) |
| **Scope** | All automation that could write to `public-data/` or read from `data/` for export. |

---

## Context

The Agent Project Control Tower has two data sources in one
Git repository:

- `data/` (gitignored) — the human reviewer's private view of
  every project's events. Agents write here freely.
- `public-data/` (committed) — the only thing the public
  internet sees. Every byte is the output of
  `scripts/export_public_data.py --replace` from `data/`,
  under a redaction scanner, with a `MANIFEST.json` audit
  trail.

The current pipeline (ACT-4A → ACT-6C → ACT-7 → ACT-7B →
ACT-8 → ACT-8B) is fully manual at the orchestrator level.
ACT-7B made the *command spelling* robust via
`scripts/generate_tower_command.py`; ACT-8B validated the
generator in a real cross-machine trial. ACT-6C and ACT-8B
both surfaced risks that no regex can catch (mis-attribution,
optimistic `PASS`).

The open question: **how much of the export pipeline can
be safely automated?**

## Decision

We adopt the policy in `docs/PUBLIC_DATA_AUTOMATION_POLICY.md`
(version 1, this act's commit). The current state is:

- **Active automation levels:** Level 1 (assisted command
  generation) + Level 2 (CI validation only).
- **Next considered level:** Level 3 (CI proposed export
  artifact, design-only). See §10 of the policy.
- **Explicitly rejected:** Level 5 (fully automatic
  export). Level 4 is not approved.

No CI workflow is added in this act. No agent is granted
new permissions. The only code change in this act is the
documentation of the policy.

## Consequences

### Positive

- The current two-gate model is preserved and documented
  in one place (§2 of the policy).
- A future act that wants to advance automation has a
  known target shape (§3, §10) and a known revisit
  threshold (§11).
- The ACT-6C mis-attribution lesson is codified as a
  six-point review checklist (§6.2) that any future
  automation must respect.
- "Why is the export still manual?" has a single canonical
  answer, with five levels of escape hatches.

### Negative

- The pipeline is not faster. ACT-9 makes it *clearer*,
  not *quicker*. Any act that wants to make it faster
  must explicitly argue for the level change.
- The policy is long (~800 lines). This is a feature: the
  rationale for each boundary is preserved alongside the
  boundary itself. A future contributor who wants to
  remove a level must remove the rationale, which is
  harder than removing a line.
- The §10 ACT-9B design creates a *target* that someone
  might want to implement prematurely. The §11 revisit
  criteria are the brake.

### Neutral

- This ADR does not change the data model, the schema,
  the CLI surface, or the dashboard. The control tower's
  surface area is unchanged.

## Alternatives considered

### Alternative A: Make the export fully automatic in ACT-9

**Rejected.** This is Level 5. The two-gate model exists
because the human reviewer's judgment is the only thing
that catches semantic bugs (mis-attribution, optimistic
PASS). Removing the human is not a "we'll iterate later"
decision — it is a one-way door. The cost of a mis-merge
is public; the cost of a manual reviewer's time is
private. The asymmetry alone justifies rejection.

### Alternative B: Implement Level 4 (authorized export bot) in ACT-9

**Rejected as out of scope.** The user asked for
*design, not implementation* in ACT-9. The Level 4
implementation requires branch protection rules, a
maintainer allowlist, an audit log, and a CI workflow
that does not exist today. Building all of that in one
act is exactly the kind of large change the user's
phase-based plan is designed to avoid. A future act
(ACT-9B or later) can implement Level 4 if and only if
the §10 artifact path proves itself first.

### Alternative C: Stay at Level 0 (no automation at all)

**Already superseded.** ACT-7B's generator and ACT-4A's CI
validation are both automation, and they have already
shipped. "No automation" is not a state we can return to
without reverting shipped commits. The choice is
*between Level 2 and Level 3+*, not *between automation
and no automation*.

### Alternative D: Skip the policy and just document the two-gate model

**Rejected.** The user's brief explicitly asked for a
"Public-data Export Automation Policy" with five levels.
A two-page "here is the two-gate model" document does not
satisfy the brief and does not give future acts a level
ladder to argue against. The full policy is a one-time
cost; the long-term benefit is having the debate in one
place.

## Why not fully automatic export

Three reasons, in priority order:

1. **Semantic bugs are not catchable by regex.** The ACT-6C
   mis-attribution was a real bug that the redaction
   scanner (and the alignment checker, and `make all`)
   would have happily passed. A human reading the
   dashboard noticed that `booktrans-desk` was pointing
   at `conanxin-homepage`. Replacing the human with a
   bot does not make the bot smarter; it makes the
   mis-attribution permanent.
2. **The public cost is asymmetric.** A mis-merge is
   visible to anyone who knows the URL. A manual reviewer's
   time is private. The asymmetry alone justifies a
   conservative policy.
3. **The pipeline is not slow.** ACT-7B's generator
   removed the most failure-prone step (multi-line bash
   commands). The remaining manual steps (review, stage,
   commit, push) take ~5 minutes. Optimizing 5 minutes
   at the cost of public-data integrity is a bad trade.

## Accepted automation level

**Level 1 + Level 2** (active today).

- **Level 1** is `scripts/generate_tower_command.py`:
  print a single-line command. No execution. No file
  writes. (Shipped in ACT-7B, commit `09b2be6`.)
- **Level 2** is the existing CI: validate, build, align,
  redaction, deploy from committed `public-data/`. No
  writes to `public-data/`, no reads from `data/`.
  (Shipped in ACT-4A.)

The next consideration is Level 3, gated by §11's revisit
criteria.

## Revisit criteria

A level change requires all of:

1. The previous level has been in production for at least
   30 days without a redaction FAIL or a mis-attribution
   event.
2. The previous level's *intended use* has been observed
   at least 5 times (e.g. the artifact was downloaded and
   accepted 5 times, in the Level-3 case).
3. The §6.2 mis-attribution checklist has caught at
   least one mis-attribution in the same period,
   proving the human reviewer's role is real.
4. The user explicitly approves the level change.

This ADR is not a permanent commitment. It is revisited
when the criteria are met, or when a fundamental change
to the data model or the publishing pipeline makes the
current levels obsolete.
