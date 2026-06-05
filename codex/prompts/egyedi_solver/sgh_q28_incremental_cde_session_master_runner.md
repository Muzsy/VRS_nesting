# SGH-Q28 — Inkrementális CDE session (dense 191 konvergencia) — Master Runner

## Cél

Ez a dokumentum az SGH-Q28 T01–T05 fejlesztési lánc végrehajtási kerete.
A cél: a `CdeCandidateSession` inkrementális lifecycle implementálása, amellyel a
191-darabos LV8 single-sheet nesting ~23× gyorsabb iterációkat ér el és 90 s alatt
legalább 10 iterációt fut (vs. jelenlegi ~2 iteráció).

A master runner nem implementálja a taskokat — csak rögzíti az olvasási sorrendet,
a preflight ellenőrzéseket, a gate-eket és a reportolási szabályokat.

## Source of truth

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `canvases/egyedi_solver/sgh_q28_incremental_cde_session_task_index.md`

## Kötelező olvasnivaló (minden task indítása előtt)

1. `AGENTS.md`
2. `docs/codex/overview.md`
3. `docs/codex/yaml_schema.md`
4. `docs/codex/report_standard.md`
5. `docs/qa/testing_guidelines.md`
6. `canvases/egyedi_solver/sgh_q28_incremental_cde_session_task_index.md`
7. Az aktuálisan futtatott task package:
   - `canvases/egyedi_solver/<TASK_SLUG>.md`
   - `codex/goals/canvases/egyedi_solver/fill_canvas_<TASK_SLUG>.yaml`
   - `codex/prompts/egyedi_solver/<TASK_SLUG>/run.md`

## Baseline preflight (T01 indítása előtt kötelező)

```bash
cargo --version
rustc --version

ls AGENTS.md
ls docs/codex/overview.md
ls docs/codex/yaml_schema.md
ls docs/codex/report_standard.md

ls rust/vrs_solver/Cargo.toml
ls rust/vrs_solver/src/optimizer/cde_adapter.rs
ls rust/vrs_solver/src/optimizer/sparrow/worker.rs
ls rust/vrs_solver/src/optimizer/sparrow/sample/search.rs
ls rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs
ls rust/vrs_solver/tests/sparrow_single_sheet_validation.rs

# Baseline teszt-szám rögzítése
cargo test --manifest-path rust/vrs_solver/Cargo.toml 2>&1 | grep "test result"
# Elvárt: 454 lib + 8 integration
```

Ha bármelyik hiányzik: STOP és BLOCKED/FAIL a reportban.

## Global hard rules

1. Csak valós repo fájlokra és parancsokra támaszkodj.
2. Csak olyan fájl módosítható, ami az adott YAML step `outputs` listájában szerepel.
3. A meglévő 454 unit test + 8 Q26 integration teszt minden task után PASS.
4. Minden task végén kötelező `./scripts/verify.sh` wrapper futtatás.
5. Backward compatibility: a `None` fallback utak minden taskban megmaradnak.
6. Nincs silent correctness regresszió: ha egy teszt elbukik, FAIL a report.

## Global invariants

- `REAL_CODE_ONLY` — nem találhatsz ki nem létező metódusokat vagy API-t
- `NO_SILENT_GEOMETRY_LOSS` — a kollíziós eredmények pontosak maradnak
- `BACKWARD_COMPAT` — None fallback minden opcionális session paraméterbőn
- `CHECKLIST_REQUIRED` — minden taskhoz

## Execution order

```text
T01 → T02 → T03 → T04 → T05
```

Minden task az előző PASS státusza után indítható.

## Dependency graph

```text
T01 (CdeCandidateSession API)
  └─→ T02 (search.rs passthrough)
        └─→ T03 (worker.rs lifecycle)
              └─→ T04 (tracker.rs reuse)
                    └─→ T05 (benchmark gate)
```

## Critical path

`T01 → T02 → T03 → T04 → T05` — nincs párhuzamos ág; minden lépés az előzőre épül.

## Checkpoints

- **CHECKPOINT-1** (T01 után): `CdeCandidateSession` inkrementális API zöld,
  `cde_session_incremental_eq_full_rebuild` unit test PASS, 454 lib teszt PASS.
- **CHECKPOINT-2** (T03 után): `run_worker_pass` single-session lifecycle aktív,
  462 teszt PASS, debug_assert session konzisztencia zöld.
- **CHECKPOINT-FINAL** (T05 után): `smoke_sgh_q28_dense191_benchmark.py` PASS,
  `iterations >= 10` gate zöld.

Minden checkpointnál kötelező:
```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml 2>&1 | grep "test result"
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_single_sheet_validation
```

## Per-task runner referenciák

| Task | Canvas | YAML | Runner | Státusz |
|------|--------|------|--------|---------|
| T01 | `canvases/egyedi_solver/sgh_q28_t01_cde_session_incremental_api.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q28_t01_cde_session_incremental_api.yaml` | `codex/prompts/egyedi_solver/sgh_q28_t01_cde_session_incremental_api/run.md` | READY |
| T02 | `canvases/egyedi_solver/sgh_q28_t02_search_session_passthrough.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q28_t02_search_session_passthrough.yaml` | `codex/prompts/egyedi_solver/sgh_q28_t02_search_session_passthrough/run.md` | READY |
| T03 | `canvases/egyedi_solver/sgh_q28_t03_worker_single_session_lifecycle.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q28_t03_worker_single_session_lifecycle.yaml` | `codex/prompts/egyedi_solver/sgh_q28_t03_worker_single_session_lifecycle/run.md` | READY |
| T04 | `canvases/egyedi_solver/sgh_q28_t04_tracker_session_reuse.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q28_t04_tracker_session_reuse.yaml` | `codex/prompts/egyedi_solver/sgh_q28_t04_tracker_session_reuse/run.md` | READY |
| T05 | `canvases/egyedi_solver/sgh_q28_t05_dense191_benchmark_gate.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q28_t05_dense191_benchmark_gate.yaml` | `codex/prompts/egyedi_solver/sgh_q28_t05_dense191_benchmark_gate/run.md` | READY |

## Várható teljesítményhatás (referencia)

| Metrika | T01–T04 előtt | T01–T04 után (becsült) |
|---------|---------------|----------------------|
| Session build/pass | ~100 db | 1 db |
| Iteráció idő (191 item) | ~37 s/iter | ~1.6 s/iter |
| Iteráció szám (900 s) | ~25 | ~550 |
| 90 s alatt iteráció | ~2 | ≥10 (gate) |

## Rollback plan

Minden task opcionális paramétert ad hozzá `None` fallback-kel. Teljes rollback:
```bash
git revert <T01 commit>..<T05 commit>
```
Részleges rollback: az adott task `None` ágát hagyd aktívan, a `Some` ágat kommenteld ki.
