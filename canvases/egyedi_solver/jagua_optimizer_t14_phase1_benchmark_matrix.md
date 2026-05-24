# JG-14 — `jagua_optimizer_t14_phase1_benchmark_matrix`

## Task identity

- **Task id:** JG-14
- **Slug:** `jagua_optimizer_t14_phase1_benchmark_matrix`
- **Phase:** Phase 1 / benchmark gate
- **Goal:** Phase 1 rectangular multi-sheet benchmark matrix: smoke/small/medium/realistic no-hole fixture-ök futtatása, baseline összevetés, exact validation gate és Phase 1 döntési report.
- **Dependency:** JG-13 — `jagua_optimizer_t13_sheet_elimination_v1`
- **Primary task report:** `codex/reports/egyedi_solver/jagua_optimizer_t14_phase1_benchmark_matrix.md`
- **Benchmark report:** `codex/reports/egyedi_solver/jagua_optimizer_phase1_rectangular_benchmark.md`
- **Benchmark JSON:** `codex/reports/egyedi_solver/jagua_optimizer_phase1_rectangular_benchmark.json`
- **Verify log:** `codex/reports/egyedi_solver/jagua_optimizer_t14_phase1_benchmark_matrix.verify.log`

## Dependency gate

JG-14 csak akkor implementálható, ha ezek bizonyítottan teljesülnek:

- `codex/reports/egyedi_solver/jagua_optimizer_t13_sheet_elimination_v1.md` létezik;
- a JG-13 report első sora `PASS`;
- a JG-13 report tartalmazza: `JG-14_STATUS: READY`;
- `rust/vrs_solver/src/optimizer/sheet_elimination.rs` létezik;
- `scripts/smoke_jagua_sheet_elimination_v1.py` létezik;
- a JG-13 report bizonyítja, hogy sheet elimination smoke és repo gate PASS.

Ha bármelyik feltétel nem teljesül, a JG-14 futás `BLOCKED`, és nem szabad benchmark eredményt vagy Phase 1 gate döntést gyártani.

## Strategic background

JG-14 a Phase 1 záró gate. Eddig a chain létrehozta az outer-only rectangular Jagua optimizer pipeline fő komponenseit:

- hole gate / outer-only contract;
- adapter contract PoC;
- rectangular sheet provider;
- item geometry store + rotation cache;
- layout state + candidate model;
- initial construction placer;
- exact validation bridge;
- repair search loop;
- score model;
- multi-sheet manager;
- sheet elimination.

JG-14 nem új solver feature-t ad hozzá. A cél az, hogy a Phase 1-re bizonyított, reprodukálható mérési mátrix készüljön. Ez alapján lehet eldönteni, hogy Phase 2 — irregular/remnant sheet irány — indítható-e, vagy Phase 1-ben még revise kell.

A benchmark csak akkor hasznos, ha minden elfogadott layout exact validation `PASS`. Invalid layout nem lehet „jó eredmény”, még akkor sem, ha a utilization vagy placed count magas.

## Out of scope

- Nem cél új construction placer, repair stratégia, ScoreModel tuning vagy sheet elimination változtatás.
- Nem cél Phase 2 irregular/remnant sheet support.
- Nem cél Phase 3 cavity-prepack vagy hole-os itemek támogatása.
- Nem cél NFP provider, Sparrow teljes átvétel vagy SA/metaheuristic implementáció.
- Nem cél real DXF pipeline cleanup; JG-14 benchmark fixture-ök rectangular/no-hole solver inputokra épüljenek.
- Nem cél az exact validator lazítása, kikapcsolása vagy megkerülése.
- Nem cél a `SolverOutput` v1 contract törése.

## Relevant current repo files

### Rust solver

- `rust/vrs_solver/src/adapter.rs` — Phase 1 profile dispatch: `jagua_optimizer_phase1_outer_only`.
- `rust/vrs_solver/src/io.rs` — `SolverInput`, `SolverOutput`, `Metrics` v1 contract; `sheet_count_used` mező.
- `rust/vrs_solver/src/item.rs` — part/instance expansion, hole gate helpers, rotation normalization.
- `rust/vrs_solver/src/sheet.rs` — rectangular sheet expansion and sheet shape handling.
- `rust/vrs_solver/src/optimizer/initializer.rs` — initial construction placer.
- `rust/vrs_solver/src/optimizer/repair.rs` — repair search loop and violation checks.
- `rust/vrs_solver/src/optimizer/score.rs` — score breakdown / sheet penalty.
- `rust/vrs_solver/src/optimizer/multisheet.rs` — multi-sheet coordination, `compute_sheet_count_used`.
- `rust/vrs_solver/src/optimizer/sheet_elimination.rs` — sheet elimination V1 pass.
- `rust/vrs_solver/Cargo.toml` — build/test entry point.

### Python runner and validation

- `vrs_nesting/runner/vrs_solver_runner.py` — canonical runner entry. It writes `runner_meta.json`, computes `placements_count`, `unplaced_count`, `sheet_count_used`, `utilization`, and sets `validation_status=pass|fail|skipped_unsupported`.
- `vrs_nesting/nesting/instances.py` — exact multi-sheet output validation bridge.
- `scripts/smoke_jagua_exact_validation_bridge.py` — proves invalid overlap/boundary outputs are rejected.
- `scripts/smoke_jagua_sheet_elimination_v1.py` — JG-13 regression anchor.

### Existing QA wrappers

- `scripts/check.sh` — repo standard gate.
- `scripts/verify.sh` — report-aware wrapper; must be used as the final repo gate.

## Benchmark design requirements

Create:

```text
scripts/bench_jagua_optimizer_phase1_rectangular.py
```

The benchmark script must be deterministic and offline-friendly. It should use the existing Python runner boundary, not reimplement solver execution:

```text
vrs_nesting.runner.vrs_solver_runner.run_solver_in_dir
```

The matrix must cover at least:

1. **smoke** — tiny no-hole fixture, fast, all items should fit.
2. **small** — few rectangular item types, rotations included, all or most fit.
3. **medium** — enough quantity to exercise multi-sheet behavior.
4. **realistic_no_hole** — larger rectangular/no-hole synthetic fixture, or explicit blocker if a meaningful fixture cannot be created safely from current code.

Each case must record:

- fixture id/name;
- seed;
- time limit;
- solver profile;
- allowed rotations summary;
- backend/solver binary path or resolver source if available from runner meta;
- placed count;
- unplaced count;
- used sheets;
- utilization;
- runtime / duration;
- validation status;
- error details, if any;
- baseline comparison result, if baseline is meaningful.

## Baseline compare policy

The benchmark must compare Phase 1 against a baseline **where meaningful and repo-supported**.

Allowed baseline candidates:

- the existing non-Phase1 solver path in `adapter.rs` by omitting `solver_profile` or using the repo-supported default profile, if this is confirmed by code;
- an already-existing script/profile if the repo provides one.

Do not invent a baseline backend. If no meaningful baseline exists, the benchmark report must explicitly state:

```text
baseline_status: unavailable
baseline_reason: <evidence>
```

Baseline compare is advisory. Exact validation is mandatory for both Phase 1 and baseline runs. A baseline run with invalid output must be reported as `FAIL`, not as comparison data.

## Phase 1 gate decision

JG-14 must produce:

```text
codex/reports/egyedi_solver/jagua_optimizer_phase1_rectangular_benchmark.json
codex/reports/egyedi_solver/jagua_optimizer_phase1_rectangular_benchmark.md
```

The benchmark MD must contain a clear gate decision:

```text
PHASE1_GATE_DECISION: PASS | REVISE | STOP
```

Minimum decision policy:

- `PASS`: all required fixtures ran, all accepted layouts exact validation PASS, metrics complete, no invalid layout accepted, no blocker on realistic no-hole fixture.
- `REVISE`: benchmark infrastructure works, but one or more metrics/fixtures/performance qualities require improvement.
- `STOP`: invalid layout accepted, exact validation bypassed, serious contract violation, or Phase 1 cannot produce reliable benchmark evidence.

If `PASS`, the JG-14 task report may mark:

```text
JG-15_STATUS: READY
```

If not PASS, JG-15 must not be marked ready.

## Required implementation steps

1. Read repo rules and JG plan documents.
2. Verify dependency gate from JG-13.
3. Audit the current runner, validator, solver IO, and benchmark/smoke patterns.
4. Implement `scripts/bench_jagua_optimizer_phase1_rectangular.py`.
5. Ensure the script writes both JSON and MD summaries under `codex/reports/egyedi_solver/`.
6. Include at least smoke, small, medium, and realistic no-hole benchmark cases, or document an explicit blocker for realistic no-hole.
7. Include baseline compare only when supported by actual repo code.
8. Run the benchmark script.
9. Run regressions:
   - `python3 scripts/smoke_jagua_sheet_elimination_v1.py`
   - `python3 scripts/smoke_jagua_exact_validation_bridge.py`
10. Run Rust tests:
   - `cargo test --manifest-path rust/vrs_solver/Cargo.toml`
11. Run repo gate:
   - `./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t14_phase1_benchmark_matrix.md`
12. Update:
   - `codex/codex_checklist/egyedi_solver/jagua_optimizer_t14_phase1_benchmark_matrix.md`
   - `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md`
   - `codex/reports/egyedi_solver/jagua_optimizer_t14_phase1_benchmark_matrix.md`

## Hard rules

```text
REAL_CODE_ONLY:
- Work only from actual repository files.
- Do not invent files, modules, APIs, functions, schemas, or test commands.
- If the expected element does not exist, report it as mismatch/blocker.
```

```text
NO_SILENT_GEOMETRY_LOSS:
- Do not drop holes, contours, item identities, quantities, transforms, or validation data silently.
- Phase 1 benchmark inputs must be rectangular/no-hole fixtures.
- Hole-containing fixtures must not be silently converted into outer-only fixtures.
```

```text
EXACT_VALIDATION_REQUIRED:
- Every benchmark result must carry exact validation status from the existing runner/validator path.
- Any run with validation_status other than pass must be marked FAIL/UNSUPPORTED/BLOCKED explicitly.
- Invalid layout cannot be accepted as success.
```

```text
CHECKLIST_REQUIRED:
- Update the task-specific checklist entries in jagua_optimizer_task_progress_checklist.md.
- A task cannot be PASS unless the relevant checklist items are checked or explicitly marked BLOCKED/DEVIATION with evidence.
```

## Acceptance criteria

JG-14 is complete only if:

- `scripts/bench_jagua_optimizer_phase1_rectangular.py` exists and runs.
- Smoke benchmark fixture runs.
- Small benchmark fixture runs.
- Medium benchmark fixture runs.
- Realistic no-hole fixture runs or is explicitly blocked with evidence.
- Baseline compare runs where meaningful; otherwise baseline unavailability is documented.
- Every accepted layout has `validation_status=pass`.
- Invalid layout cannot appear as successful benchmark.
- Metrics are recorded: placed, unplaced, used_sheets, utilization, runtime.
- Seed/profile/rotations/backend metadata are recorded.
- Summary JSON exists.
- Summary MD benchmark report exists.
- JG-14 implementation report exists.
- Task-specific checklist and global task progress checklist are updated.
- Repo verify wrapper runs and writes `.verify.log`.
- Phase 1 gate decision is explicit: `PASS`, `REVISE`, or `STOP`.

## Failure / rollback policy

If the benchmark script reveals invalid accepted layouts:

- mark the benchmark and JG-14 report as `STOP`;
- do not mark `JG-15_STATUS: READY`;
- preserve logs and JSON evidence;
- do not hide the bad run by filtering it out of summary results.

If dependency gate fails:

- mark JG-14 as `BLOCKED`;
- do not create benchmark claims;
- do not modify solver code.

If environment dependencies are missing:

- mark as `REVISE` or `BLOCKED` depending on severity;
- record the exact missing dependency and command output;
- do not convert environment failure into a solver-quality conclusion.
