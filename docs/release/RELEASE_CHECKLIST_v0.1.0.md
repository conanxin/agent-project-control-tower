# Release Checklist — v0.1.0

## Pre-release validation

- [x] `make all` PASS
- [x] `make publish-preflight` PASS
- [x] `make command-test` PASS
- [x] `make candidate` PASS
- [x] `make candidate-fixture` PASS
- [x] `make candidate-test` PASS
- [x] `make export-plan-test` PASS
- [x] `npm run build` PASS (apps/dashboard)
- [x] GitHub Actions green
- [x] Cloudflare dashboard reachable
- [x] Custom domain reachable
- [x] public-data verified (3 projects / 2 agents / 22 events)
- [x] `config/public-data-export-plan.yml` verified
- [x] `data/` gitignored
- [x] `generated/` gitignored
- [x] `artifacts/` gitignored
- [x] No token / IP / private path leak
- [x] BookTrans Desk regression verified (conanxin/booktrans-desk / S13 / 16f38b6 / PARTIAL)
- [x] Policy docs reachable

## Release artifacts

- [x] `VERSION` created
- [x] `CHANGELOG.md` created
- [x] `docs/release/RELEASE_NOTES_v0.1.0.md` created
- [x] `docs/release/RELEASE_CHECKLIST_v0.1.0.md` created
- [x] `reports/PHASE_ACT10_V010_RELEASE_PACKAGING_REPORT.md` created

## Documentation updates

- [x] `README.md` updated with v0.1.0 status
- [x] `docs/MVP_PLAN.md` updated with ACT-10 COMPLETE
- [x] `docs/DEPLOYMENT_PLAN.md` updated with v0.1.0 state
- [x] `docs/OPEN_SOURCE_PLAN.md` updated with v0.1.0 boundary
- [x] `docs/PUBLIC_DATA_AUTOMATION_POLICY.md` updated with v0.1.0 policy state

## Git operations

- [x] Release packaging commit created
- [x] Commit pushed to origin/main
- [x] Annotated tag `v0.1.0` created
- [x] Tag pushed to origin
- [ ] GitHub release created (deferred — `gh` CLI not available or not authenticated)

## Post-release verification

- [x] Dashboard still live after push
- [x] GitHub tag accessible
- [x] public-data not corrupted
- [x] data/ still private
- [x] generated/ still private
- [x] artifacts/ still private
