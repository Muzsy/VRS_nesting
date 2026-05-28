# Runner — SGH-Q18A-R1 phase timing and report consistency fix

Feladat: hajtsd végre a `canvases/egyedi_solver/sgh_q18a_r1_phase_timing_report_consistency_fix.md` canvas és a hozzá tartozó goal YAML alapján a Q18A korrekciós taskot.

## Lényeg

Q18A nagy része elkészült, de a per-phase timing követelmény nincs teljesítve, miközben a checklist kipipálta. Ez nem quality solver munka, hanem observability/contract javítás.

Nem haladunk Q20/Q21-re, amíg ez nincs rendben.

## Kötelező olvasás

```text
codex/reports/egyedi_solver/sgh_q18a_cde_correctness_runtime_observability.md
codex/codex_checklist/egyedi_solver/sgh_q18a_cde_correctness_runtime_observability.md
docs/egyedi_solver/sgh_q18a_cde_correctness_runtime_observability.md
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/optimizer/phase.rs
rust/vrs_solver/src/optimizer/explore.rs
rust/vrs_solver/src/optimizer/compress.rs
rust/vrs_solver/src/optimizer/bpp_phase.rs
scripts/smoke_sgh_q18a_cde_observability.py
```

## Javítandó konkrétum

A Q18A eredeti runner minimumként kérte:

```text
final_commit_validation_runtime
phase_optimizer_exploration_runtime
phase_optimizer_compression_runtime
phase_optimizer_bpp_runtime
phase_optimizer_final_commit_runtime
legacy_multisheet_cde_final_commit_runtime
```

A jelenlegi kód/report csak a final commit timingot kezeli, env flaggel. A PhaseOptimizer exploration/compression/bpp runtime nincs outputban, nincs smoke assertion, és a checklist mégis késznek jelöli. Ezt javítsd.

## Kötelező implementációs szabályok

- Timing csak `VRS_CDE_OBSERVABILITY_TIMING=1` vagy explicit diagnostics módban serializálódhat.
- Alapértelmezett SolverOutput JSON ne tartalmazzon wall-clock runtime mezőket.
- A meglévő CDE számlálók és Q16/Q18A backend proof ne sérüljön.
- `bbox_fallback_queries == 0` CDE alatt továbbra is invariant.
- Ne csinálj CDE session/cache rewrite-ot.
- Ne csinálj Q19/Q20/Q21 solver quality munkát ebben a taskban.

## Elvárt tesztek/parancsok

Futtasd legalább:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::phase
cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q18a_cde_observability.py
VRS_CDE_OBSERVABILITY_TIMING=1 python3 scripts/smoke_sgh_q18a_cde_observability.py
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q18a_r1_phase_timing_report_consistency_fix.md
```

## Report

Hozd létre:

```text
codex/reports/egyedi_solver/sgh_q18a_r1_phase_timing_report_consistency_fix.md
codex/reports/egyedi_solver/sgh_q18a_r1_phase_timing_report_consistency_fix.verify.log
```

A report első sora csak `PASS`, `REVISE` vagy `BLOCKED` lehet.

PASS végén legyen:

```text
SGH-Q18A_R1_STATUS: READY_FOR_AUDIT
SGH-Q20_STATUS: READY|HOLD
Q18B_RECOMMENDATION: REQUIRED|NOT_REQUIRED_NOW|INCONCLUSIVE_NEEDS_BIGGER_FIXTURE
```
