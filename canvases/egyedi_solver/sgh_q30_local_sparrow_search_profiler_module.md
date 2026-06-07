# SGH-Q30 — Local Sparrow search/CDE profiler module for LV8 cost breakdown

## 🎯 Cél

A Q29 után a következő kérdés már nem upstream A/B, hanem a saját `sparrow_cde` útvonal részletes költségbontása. A Q29 local profiler azt mutatta, hogy a `session_build_ms`, `deregister/reregister`, `candidate_transform_prepare` és a mért `specialized_pipeline_ms` nem magyarázza meg a teljes `native_search_placement` időt; nagy `other_unaccounted` maradt. Ezt kell most felbontani.

A task célja egy **tartósan használható, bővíthető helyi profiling modul** bevezetése a Rust solverbe, és egy komoly LV8-alapú mérési futás, amely megmutatja, hogy a search-loopon belül pontosan mi viszi el az időt.

Ez nem optimalizálási task. Ez mérési infrastruktúra + futtatott mérés.

## Kontextus

A Q29 után ismert állapot:

- Nem a session build bizonyult fő bottlenecknek.
- A saját solver kisebb/medium eseteken nem látszott upstreamhez képest rossznak.
- Dense LV8 jellegű futásnál továbbra is `partial` állapot és kevés iteráció marad.
- A Q29 local profiler nagy `other_unaccounted` blokkot hagyott a search költségből.

Most ezt kell bontani:

```text
sample generation ms
BestSamples insert/dedup ms
coord_descent total ms
evaluate_sample call count
evaluator orchestration ms
RNG/shuffle/sample-loop overhead
per-candidate average time
```

## Nem-célok — kötelező tiltások

- Nem cél upstream Sparrow A/B mérés.
- Nem cél a solver gyorsítása.
- Nem cél sample budget, worker ordering, GLS, touching policy, collision semantics vagy acceptance logika módosítása.
- Nem cél compression bevezetése.
- Nem cél Q26/Q28/Q29 gate-ek lazítása.
- Nem cél dense191 `ok` státusz kikényszerítése.
- Nem cél olyan report, amely mérés helyett következtetést találgat.
- Nem engedélyezett a profiler eredményeinek kozmetikázása: ha egy mező nem mérhető, `not_available` + indok kell.

## Tervezési követelmény — külön, újrahasználható profiling modul

A mérési rész ne szétszórt ad-hoc `println!` legyen. Külön Rust modulban kell kialakítani egy bővíthető profiling infrastruktúrát, például:

```text
rust/vrs_solver/src/optimizer/sparrow/profile.rs
```

vagy ha a repo alapján jobb név adódik:

```text
rust/vrs_solver/src/optimizer/sparrow/search_profile.rs
rust/vrs_solver/src/optimizer/sparrow/profiling.rs
```

A modul célja:

1. Alapértelmezésben legyen inaktív vagy minimális overheadű.
2. Explicit env flaggel vagy configgal kapcsolható legyen, például:

```bash
SGH_Q30_SEARCH_PROFILE=1
```

3. Legyen később bővíthető:
   - új mérőpontok hozzáadása,
   - JSON export,
   - run artifactként mentés,
   - későbbi admin/observability felületre továbbítás.
4. Ne legyen algoritmusfüggő hack; legyen tiszta measurement API.
5. A reportban legyen leírva, hogyan lehet később admin outputba vagy run diagnosticsba bekötni.

### Javasolt API

A pontos Rust API-t a kódhoz kell igazítani, de minimum legyenek ehhez hasonló fogalmak:

```rust
SearchProfiler
SearchProfileSnapshot
SearchProfileScope / SearchProfileTimer
SearchProfileCounters
```

A mérési adatokat aggregálni kell run-szinten és lehetőség szerint search-call szinten is.

## Kötelező mérőpontok

### Per run aggregátum

Minimum:

```text
total_solver_runtime_ms
native_search_calls
candidates_evaluated
evaluate_sample_calls
global_samples_generated
focused_samples_generated
coord_descent_runs
coord_descent_steps
best_samples_insert_attempts
best_samples_inserted
best_samples_dedup_rejects
rng_shuffle_or_sample_loop_count
early_termination_count
broadphase_reject_count
final_pairs
iterations
status
placed_count
```

### Search időbontás

Minimum:

```text
search_total_ms
sample_generation_ms
best_samples_insert_dedup_ms
coord_descent_total_ms
evaluate_sample_total_ms
evaluator_orchestration_ms
rng_shuffle_sample_loop_ms
candidate_transform_prepare_ms
cde_query_collect_ms
specialized_pipeline_ms
hazard_loss_ms
boundary_check_ms
session_build_ms
deregister_reregister_ms
other_unaccounted_ms
per_candidate_avg_ms
per_evaluate_sample_avg_ms
per_search_avg_ms
```

### `other_unaccounted_ms` kötelező képlet

A `other_unaccounted_ms` mező nem lehet kézzel írt megjegyzés. Számolt érték legyen:

```text
search_total_ms
- sample_generation_ms
- best_samples_insert_dedup_ms
- coord_descent_total_ms
- evaluate_sample_total_ms
- evaluator_orchestration_ms
- rng_shuffle_sample_loop_ms
- candidate_transform_prepare_ms
- cde_query_collect_ms
- specialized_pipeline_ms
- hazard_loss_ms
- boundary_check_ms
- session_build_ms
- deregister_reregister_ms
```

Ha valamelyik almező átfed a másikkal, a reportban pontosan meg kell jelölni, mely mezők exkluzívak és melyek nested/overlap jellegűek. Az artifact JSON-ban legyen:

```json
"timing_accounting_mode": "exclusive|nested_with_notes|mixed_with_notes"
```

A cél az, hogy ne legyen félrevezető 100%-os bontás, ha a mérések egymásba ágyazottak.

## Kötelező instrumentációs pontok

A kódban legalább az alábbi helyeket kell megvizsgálni és mérni, ha léteznek:

- `rust/vrs_solver/src/optimizer/sparrow/sample/search.rs`
  - `native_search_placement`
  - `search_placement`
  - global/focused sample generation loop
  - evaluator call körüli orchestration
- `rust/vrs_solver/src/optimizer/sparrow/sample/best_samples.rs`
  - insert / dedup / reject idő és számlálók
- `rust/vrs_solver/src/optimizer/sparrow/sample/coord_descent.rs`
  - coord descent total idő
  - coord descent step count
  - evaluate hívások száma coord descentből
- `rust/vrs_solver/src/optimizer/sparrow/eval/sep_evaluator.rs`
  - evaluate_sample call count
  - evaluator orchestration idő
  - candidate transform/prepare idő
  - boundary check idő
- `rust/vrs_solver/src/optimizer/sparrow/eval/specialized_cde_pipeline.rs`
  - specialized pipeline idő
  - collect/collision traversal idő, ha szétválasztható
  - early termination count
  - hazard/loss idő, ha mérhető
- `rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs`
  - update_after_move / query integration költség, ha releváns
- `rust/vrs_solver/src/optimizer/cde_adapter.rs`
  - session build / query / strict post-policy, ha a local search útvonal érinti

Ha egy funkció máshol van, a YAML outputs frissítése után ott kell mérni.

## Mérési inputok

A feladat kizárólag saját solverrel fut. Upstream Sparrow nem kell.

Kötelező case-ek:

1. **medium sanity case**
   - meglévő Q26 fixture vagy hasonló 20–80 instance,
   - cél: profiler működésének gyors validálása.

2. **LV8-derived subset case**
   - meglévő Q26/Q29 LV8-derived subset vagy `samples/real_work_dxf/0014-01H/lv8jav_normalized` alapján,
   - cél: real geometry mérés.

3. **dense LV8 / dense191 case**
   - preferált: `rust/vrs_solver/tests/fixtures/sgh_q28_dense191_benchmark/dense_191_lv8_derived.json`, ha létezik,
   - ha nem létezik, determinisztikusan létre kell hozni Q28/Q29 artefaktumok vagy normalizált LV8 input alapján,
   - cél: komolyabb, sűrű LV8 mérés.

Opcionális, ha futtatható reális időn belül:

4. **full LV8 276 diagnostic case**
   - nem acceptance gate,
   - nem kell `ok`,
   - csak mérési snapshot,
   - ha túl lassú, explicit `skipped_reason`.

## Artifactok

Hozd létre:

```text
artifacts/benchmarks/sgh_q30/local_search_profile_summary.json
artifacts/benchmarks/sgh_q30/local_search_profile_report.md
```

A JSON minimum séma:

```json
{
  "task": "sgh_q30_local_sparrow_search_profiler_module",
  "status": "PASS|FAIL",
  "profile_flag": "SGH_Q30_SEARCH_PROFILE=1",
  "timing_accounting_mode": "exclusive|nested_with_notes|mixed_with_notes",
  "module": {
    "rust_path": "rust/vrs_solver/src/optimizer/sparrow/profile.rs",
    "enabled_by": "SGH_Q30_SEARCH_PROFILE=1",
    "export_path": "...",
    "future_admin_integration_notes": "..."
  },
  "cases": [
    {
      "case_id": "medium|lv8_subset|dense191|full276_optional",
      "input_path": "...",
      "status": "ok|partial|unsupported|error|skipped",
      "runtime_ms": 0.0,
      "placed_count": 0,
      "final_pairs": 0,
      "iterations": 0,
      "profile": {
        "native_search_calls": 0,
        "candidates_evaluated": 0,
        "evaluate_sample_calls": 0,
        "global_samples_generated": 0,
        "focused_samples_generated": 0,
        "coord_descent_runs": 0,
        "coord_descent_steps": 0,
        "best_samples_insert_attempts": 0,
        "best_samples_inserted": 0,
        "best_samples_dedup_rejects": 0,
        "rng_shuffle_or_sample_loop_count": 0,
        "early_termination_count": 0,
        "broadphase_reject_count": 0,
        "search_total_ms": 0.0,
        "sample_generation_ms": 0.0,
        "best_samples_insert_dedup_ms": 0.0,
        "coord_descent_total_ms": 0.0,
        "evaluate_sample_total_ms": 0.0,
        "evaluator_orchestration_ms": 0.0,
        "rng_shuffle_sample_loop_ms": 0.0,
        "candidate_transform_prepare_ms": 0.0,
        "cde_query_collect_ms": 0.0,
        "specialized_pipeline_ms": 0.0,
        "hazard_loss_ms": 0.0,
        "boundary_check_ms": 0.0,
        "session_build_ms": 0.0,
        "deregister_reregister_ms": 0.0,
        "other_unaccounted_ms": 0.0,
        "per_candidate_avg_ms": 0.0,
        "per_evaluate_sample_avg_ms": 0.0,
        "per_search_avg_ms": 0.0
      },
      "top_costs_percent": [
        {"name": "coord_descent_total_ms", "percent_of_search_total": 0.0}
      ],
      "notes": []
    }
  ]
}
```

## Runner és smoke validator

Hozd létre:

```text
scripts/profile_sgh_q30_local_search_breakdown.py
scripts/smoke_sgh_q30_local_search_profiler_module.py
```

### `profile_sgh_q30_local_search_breakdown.py`

Feladata:

- buildelt saját `vrs_solver` release binárist használ,
- beállítja: `SGH_Q30_SEARCH_PROFILE=1`,
- futtatja a kötelező case-eket,
- összegyűjti a profiler JSON-t a solver outputból vagy sidecar artifactból,
- létrehozza a Q30 summary JSON-t és Markdown reportot,
- nem optimalizál, nem módosít runtime paramétereket a mérés kedvéért a canvasban dokumentáltakon kívül.

### `smoke_sgh_q30_local_search_profiler_module.py`

Feladata:

- nem mér, csak validálja a létrejött Q30 artifactokat,
- ellenőrzi a kötelező mezőket,
- ellenőrzi, hogy van `dense191` case vagy indokolt `skipped_reason`,
- ellenőrzi, hogy az új mérőpontok szerepelnek:
  - `sample_generation_ms`,
  - `best_samples_insert_dedup_ms`,
  - `coord_descent_total_ms`,
  - `evaluate_sample_calls`,
  - `evaluator_orchestration_ms`,
  - `rng_shuffle_sample_loop_ms`,
  - `per_candidate_avg_ms`,
- ellenőrzi, hogy a report tartalmaz top-cost bontást.

## Acceptance criteria

A task akkor PASS, ha:

1. Létrejött külön Rust profiling modul, nem ad-hoc scattered-only mérés.
2. A profiler explicit flag mögött fut, default solver viselkedést nem módosít.
3. A kötelező új mérőpontok mind szerepelnek a JSON-ban.
4. Legalább medium + LV8-derived + dense191 saját solver case lefutott, vagy dense191 hiánya reprodukálhatóan indokolt.
5. A dense191 case nem upstream és nem no-session reference; a saját aktuális `sparrow_cde` útvonalat méri.
6. Létrejött `local_search_profile_summary.json` és `local_search_profile_report.md`.
7. A report top-cost bontásban megnevezi, mi viszi el az időt, és külön jelöli az `other_unaccounted_ms` arányt.
8. `python3 scripts/smoke_sgh_q30_local_search_profiler_module.py` PASS.
9. `cargo test --manifest-path rust/vrs_solver/Cargo.toml` PASS.
10. `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q30_local_sparrow_search_profiler_module.md` PASS.

## Report kötelező végső válasza

A report végén legyen külön szakasz:

```md
## Final answer — mi viszi el az időt?

1. A medium case fő költségei
2. Az LV8 subset fő költségei
3. A dense191 fő költségei
4. Mi maradt other_unaccounted és miért
5. Melyik következő optimalizációs irányt indokolja a mérés, de optimalizáció NEM történt ebben a taskban
```

## Különösen fontos

Ha a mérés szerint a legnagyobb költség továbbra is `other_unaccounted_ms`, akkor a task nem PASS automatikusan. PASS csak akkor adható, ha a report pontosan megmondja:

- melyik belső blokk maradt bontatlan,
- hol kell a következő mérőpontot hozzáadni,
- miért nem sikerült most szétbontani.

Ne legyen újabb olyan report, amelyben a költség 80%-a névtelen marad.
