# Checklist — SGH-Q05R2 `sgh_q05r2_bpp_contract_score_semantics_cleanup`

## Dependency gate

- [x] SGH-Q05R report létezik.
- [x] SGH-Q05R report első sora PASS.
- [x] SGH-Q05R report tartalmazza: `SGH-Q06_STATUS: READY`.

## Preflight reads

- [x] AGENTS.md átolvasva.
- [x] docs/codex/report_standard.md átolvasva.
- [x] docs/egyedi_solver/sgh_q05_bpp_phase_loop_contract.md átolvasva — régi min() állítás azonosítva (sor 40).
- [x] canvases/egyedi_solver/sgh_q05r2_bpp_contract_score_semantics_cleanup.md átolvasva.
- [x] codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q05r2_bpp_contract_score_semantics_cleanup.yaml átolvasva.
- [x] codex/reports/egyedi_solver/sgh_q05r_bpp_phase_diagnostics_score_semantics_fix.md átolvasva.

## Implementation (docs only)

- [x] `Score vs sheet-count decision rule` szekció: régi `min(...)` bullet eltávolítva, helyes kódblokk hozzáadva.
- [x] Magyarázó mondat átírva: nem tartalmazza az exact régi formulát.
- [x] `best_seen_score` különválasztása dokumentálva (nincs PhaseResult-ben).
- [x] `BppPhaseDiagnostics.best_score` sorban **BPP-local diagnostic** megjegyzés hozzáadva.
- [x] `PhaseResult.improved()` Q05R utáni szemantika szekció hozzáadva.

## Verification

- [x] `grep "min(final_score, compression_best, exploration_best, initial_score)"` → nincs találat.
- [x] `grep "PhaseResult.best_score = PhaseResult.score.total_cost"` → sor 44.
- [x] `git diff --name-only | grep "rust/vrs_solver/src/"` → nincs találat.
- [x] verify.sh: RUN (see report AUTO_VERIFY section).

## No-production-code gate

- [x] `rust/vrs_solver/src/**` módosítás: NINCS.
- [x] `api/**` módosítás: NINCS.
- [x] `frontend/**` módosítás: NINCS.

## Documentation

- [x] `docs/egyedi_solver/sgh_q05_bpp_phase_loop_contract.md` frissítve — önellentmondás feloldva.
- [x] `codex/codex_checklist/egyedi_solver/sgh_q05r2_bpp_contract_score_semantics_cleanup.md` elkészült.
- [x] `codex/reports/egyedi_solver/sgh_q05r2_bpp_contract_score_semantics_cleanup.md` elkészült.
