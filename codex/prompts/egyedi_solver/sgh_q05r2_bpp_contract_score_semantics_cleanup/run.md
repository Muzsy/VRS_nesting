# Runner — SGH-Q05R2 BPP contract score semantics cleanup

Hajtsd végre a `canvases/egyedi_solver/sgh_q05r2_bpp_contract_score_semantics_cleanup.md` canvas és a hozzá tartozó goal YAML alapján a Q05R2 dokumentációs javítást.

## Fontos

Ez nem Q06 implementáció. Ez nem production Rust task.

A Q05R kódszintű javítás után a `docs/egyedi_solver/sgh_q05_bpp_phase_loop_contract.md` dokumentumban maradt egy régi, ellentmondó állítás:

```text
PhaseResult.best_score = min(final_score, compression_best, exploration_best, initial_score)
```

Ezt Q06 előtt ki kell takarítani, mert a LossModel task a score/diagnostics szerződésre fog építeni.

## Engedélyezett módosítások

```text
docs/egyedi_solver/sgh_q05_bpp_phase_loop_contract.md
codex/codex_checklist/egyedi_solver/sgh_q05r2_bpp_contract_score_semantics_cleanup.md
codex/reports/egyedi_solver/sgh_q05r2_bpp_contract_score_semantics_cleanup.md
codex/reports/egyedi_solver/sgh_q05r2_bpp_contract_score_semantics_cleanup.verify.log
```

## Tiltott módosítások

```text
rust/vrs_solver/src/**
api/**
frontend/**
Q06 LossModel
Q07 RotationPolicy
Q08 CDE backend
```

## Kötelező eredmény

A contract dokumentum egyértelműen ezt mondja:

```text
PhaseResult.score = ScoreModel::score(final_returned_layout)
PhaseResult.best_score = PhaseResult.score.total_cost
```

És sehol nem marad benne ez:

```text
PhaseResult.best_score = min(final_score, compression_best, exploration_best, initial_score)
```

Dokumentáld:

```text
best_seen_score jelenleg nincs a PhaseResult-ben;
ha később kell, külön mezőként kell bevezetni.
BppPhaseDiagnostics.best_score BPP-local diagnostic, nem globális best-seen score.
PhaseResult.improved() Q05R után final_score < initial_score szemantikájú.
```

## Verify

Futtasd:

```bash
grep -n "min(final_score, compression_best, exploration_best, initial_score)" docs/egyedi_solver/sgh_q05_bpp_phase_loop_contract.md
# elvárt: nincs találat

grep -n "PhaseResult.best_score = PhaseResult.score.total_cost" docs/egyedi_solver/sgh_q05_bpp_phase_loop_contract.md
# elvárt: van találat

git diff --name-only
# elvárt: nincs rust/vrs_solver/src/**

./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q05r2_bpp_contract_score_semantics_cleanup.md
```

Ha minden zöld:

```text
report első sora: PASS
report vége: SGH-Q06_STATUS: READY
```

Ha bármi fail:

```text
report első sora: REVISE vagy BLOCKED
ne legyen SGH-Q06_STATUS marker
```
