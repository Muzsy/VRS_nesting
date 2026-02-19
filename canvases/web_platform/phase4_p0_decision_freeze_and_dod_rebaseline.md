# canvases/web_platform/phase4_p0_decision_freeze_and_dod_rebaseline.md

# Phase 4 P0 decision freeze + DoD rebaseline

## Funkcio
A feladat celja a Phase 4 inditasa elotti kotelezo dontesek formalis rogzitese es a master checklist
Phase 4 blokkjanak atalllitasa a jovahagyott keretrendszerre.

## Scope
- Benne van:
  - P4.0 dontesi pontok explicit rogzitese (rate limit split, quota atomic, cleanup orchestration, CI auth strategy);
  - Phase 4 feladatpontok pontositasa (E2E stable/async szetvalasztas, observability/security minimum);
  - Phase 4 DoD ujraalapozasa (p95 es Sentry kotelezoseg kivetele).
- Nincs benne:
  - konkret Phase 4 implementacio.

## Erintett fajlok
- `canvases/web_platform/phase4_p0_decision_freeze_and_dod_rebaseline.md`
- `codex/goals/canvases/web_platform/fill_canvas_phase4_p0_decision_freeze_and_dod_rebaseline.yaml`
- `codex/codex_checklist/web_platform/phase4_p0_decision_freeze_and_dod_rebaseline.md`
- `codex/reports/web_platform/phase4_p0_decision_freeze_and_dod_rebaseline.md`
- `codex/reports/web_platform/phase4_p0_decision_freeze_and_dod_rebaseline.verify.log`
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`

## DoD
- [ ] A master checklist tartalmazza a P4.0 dontesi blokkot.
- [ ] Phase 4 feladatpontok a jovahagyott strategiat tukrozik (gateway+app split, atomic quota, stable/async E2E, cron->edge cleanup).
- [ ] Phase 4 DoD-bol kikerul a kotelezo p95 es kotelezo Sentry kovetelmeny.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/phase4_p0_decision_freeze_and_dod_rebaseline.md` PASS.
