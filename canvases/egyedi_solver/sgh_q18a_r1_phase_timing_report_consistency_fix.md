# SGH-Q18A-R1 — Phase timing and report consistency fix

## Státusz

Korrekciós task az SGH-Q18A audit után.

SGH-Q18A nagy része kódszinten rendben van: CDE számlálók, final commit backend proof, unsupported diagnosztika és bbox-fallback invariáns működik. Viszont a Q18A eredeti acceptance követelményei között szerepelt a PhaseOptimizer per-phase runtime mérhetősége:

```text
phase_optimizer_exploration_runtime
phase_optimizer_compression_runtime
phase_optimizer_bpp_runtime
phase_optimizer_final_commit_runtime
legacy_multisheet_cde_final_commit_runtime
```

A friss Q18A report ezt részben hiányzóként dokumentálta, miközben a checklistben ezek a sorok kipipált állapotban vannak. Ez report/contract inkonzisztencia és observability hiány. Emiatt Q20/Q21-re még nem szabad továbbmenni.

## Előfeltétel

Kötelező:

```text
codex/reports/egyedi_solver/sgh_q18a_cde_correctness_runtime_observability.md
```

Az első sor lehet `PASS`, de a report tartalmazza:

```text
Q18B_RECOMMENDATION: INCONCLUSIVE_NEEDS_BIGGER_FIXTURE
```

és a reportban legyen látható, hogy a per-phase breakdown még nem elérhető. Ha a repo már tartalmazza a per-phase timingot és a checklist is konzisztens, akkor a task legyen `PASS_NOOP` jellegű dokumentált reporttal.

## Cél

A Q18A-R1 célja nem CDE session/cache rewrite és nem quality solver munka. A cél:

1. A PhaseOptimizer exploration/compression/BPP/final commit timing mérhető legyen explicit diagnostics módban.
2. A legacy_multisheet CDE final commit timing továbbra is mérhető maradjon.
3. A timing ne kerüljön be alapértelmezett SolverOutput JSON-ba.
4. A determinisztikus output ne sérüljön.
5. A Q18A report, checklist és docs ne állítsanak olyat, ami nincs implementálva.
6. A Q18B döntés adatokra épüljön, ne checklist-fikcióra.

## Nem cél

Ne csináld most:

```text
CDE session/cache rewrite
CDE default backend bekapcsolása
Q19 LV8 acceptance benchmark gate
Q20 continuous rotation refinement
Q21 exact/CDE-aware loss rewrite
bbox fallback visszahozása CDE alá
main solver hole-aware CDE collision
```

## Implementációs követelmények

### 1. Pre-audit

Olvasd el és auditáld:

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

Reportold pontosan:

```text
- mely timing mezők vannak most ténylegesen implementálva;
- mely checklist sorok voltak hamisan kipipálva;
- mely output struktúrában érdemes a timingot kezelni;
- milyen env flag / diagnostics mód védi a determinisztikát.
```

### 2. Phase timing implementation

Mérhetővé kell tenni legalább ezeket:

```text
phase_optimizer_exploration_runtime_ms
phase_optimizer_compression_runtime_ms
phase_optimizer_bpp_runtime_ms
phase_optimizer_final_commit_runtime_ms
legacy_multisheet_cde_final_commit_runtime_ms
```

Elnevezés igazodhat a repo stílusához, de legyen egyértelmű.

Elfogadható megoldás:

- A PhaseOptimizer belső `PhaseDiagnostics` vagy új diagnostics struct tartalmazza az opcionális timing mezőket.
- A wall-clock timing csak akkor legyen kitöltve/serializálva, ha `VRS_CDE_OBSERVABILITY_TIMING=1` vagy explicit diagnostics mód aktív.
- Alapértelmezett futásban ezek a mezők ne jelenjenek meg a SolverOutput JSON-ban.
- A determinisztikus counter mezők változatlanul maradhatnak alapértelmezetten.

Fontos: a final commit timing ne legyen összekeverve a teljes PhaseOptimizer runtime-mal. A reportban külön szerepeljen:

```text
exploration
compression
bpp
final_commit
```

### 3. Output és docs

Frissítsd backward-compatible módon:

```text
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/optimizer/phase.rs
```

Ha új output mezőket vezetsz be, azok legyenek `Option` + `skip_serializing_if = "Option::is_none"` jellegűek.

Frissítsd:

```text
docs/egyedi_solver/sgh_q18a_cde_correctness_runtime_observability.md
codex/codex_checklist/egyedi_solver/sgh_q18a_cde_correctness_runtime_observability.md
codex/reports/egyedi_solver/sgh_q18a_cde_correctness_runtime_observability.md
```

A checklistben csak az legyen kipipálva, ami ténylegesen implementált és tesztelt.

### 4. Smoke script bővítés

Bővítsd:

```text
scripts/smoke_sgh_q18a_cde_observability.py
```

A timing env flaggel futtatott PhaseOptimizer fixture assertelje legalább:

```text
phase/exploration runtime field present and >= 0
phase/compression runtime field present and >= 0
phase/bpp runtime field present and >= 0
phase/final_commit runtime field present and >= 0
legacy final_commit runtime field present and >= 0
```

Ne exact értéket assertelj.

Alapértelmezett, timing env nélküli futásban asserteld, hogy wall-clock mezők nem jelennek meg.

### 5. Tesztek

Adj vagy frissíts célzott teszteket legalább erre:

```text
cde_timing_fields_absent_by_default
cde_timing_fields_present_when_env_enabled
phase_optimizer_timing_fields_present_when_env_enabled
phase_optimizer_timing_fields_absent_by_default
legacy_multisheet_final_commit_timing_present_when_env_enabled
determinism_not_broken_by_default_output
q18a_report_checklist_consistency
```

A testnevek eltérhetnek, de a reportban mapeld őket ezekre a követelményekre.

### 6. Verify

Futtasd legalább:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::phase
cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q18a_cde_observability.py
VRS_CDE_OBSERVABILITY_TIMING=1 python3 scripts/smoke_sgh_q18a_cde_observability.py
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q18a_r1_phase_timing_report_consistency_fix.md
```

Ha bármelyik környezeti okból nem fut, nem lehet hamis PASS. Dokumentáld pontosan.

## Report

Hozd létre:

```text
codex/reports/egyedi_solver/sgh_q18a_r1_phase_timing_report_consistency_fix.md
codex/reports/egyedi_solver/sgh_q18a_r1_phase_timing_report_consistency_fix.verify.log
```

A report első sora csak `PASS`, `REVISE` vagy `BLOCKED` lehet.

PASS report tartalmazza:

```text
- pre-audit megállapítások;
- pontosan mely Q18A timing/checklist inkonzisztenciák voltak;
- módosított fájlok;
- új vagy javított timing mezők listája;
- default output determinism bizonyíték;
- env-flag timing output bizonyíték;
- legacy_multisheet és phase_optimizer fixture output összefoglaló;
- smoke script output;
- cargo és verify eredmények;
- Q18B döntés újraértékelése.
```

PASS report végén legyen:

```text
SGH-Q18A_R1_STATUS: READY_FOR_AUDIT
SGH-Q20_STATUS: READY|HOLD
Q18B_RECOMMENDATION: REQUIRED|NOT_REQUIRED_NOW|INCONCLUSIVE_NEEDS_BIGGER_FIXTURE
```

`SGH-Q20_STATUS: READY` csak akkor megengedett, ha a timing hiány és checklist inkonzisztencia ténylegesen javítva van.
