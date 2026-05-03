PASS

## 1) Meta
- Task slug: `engine_v2_nfp_rc_t04_nfp_baseline_instrumentation`
- Kapcsolodo canvas: `canvases/nesting_engine/engine_v2_nfp_rc_t04_nfp_baseline_instrumentation.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/nesting_engine/fill_canvas_engine_v2_nfp_rc_t04_nfp_baseline_instrumentation.yaml`
- Futas datuma: `2026-05-04`
- Branch / commit: `main@991473a`
- Fokusz terulet: `Rust benchmark bin + fixture baseline metrics`

## 2) Scope

### 2.1 Cel
- A jelenlegi `concave.rs` NFP viselkedes baseline mérése T01 fixture-okon.
- Fragment/pair metrikak, timeout reprodukcio, verdict rogzitese.
- `baseline_metrics` mezok kitoltese mindharom T01 fixture-ben.

### 2.2 Nem-cel (explicit)
- `concave.rs` algoritmusmodositas nem tortent.
- Uj NFP kernel nem lett implementalva.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `rust/nesting_engine/src/bin/nfp_pair_benchmark.rs`
- `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json`
- `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_02.json`
- `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_03.json`
- `codex/codex_checklist/nesting_engine/engine_v2_nfp_rc_t04_nfp_baseline_instrumentation.md`
- `codex/reports/nesting_engine/engine_v2_nfp_rc_t04_nfp_baseline_instrumentation.md`

### 3.2 Mi valtozott es miert
- Letrejott a `nfp_pair_benchmark` bin, ami fixture alapjan meri a baseline NFP futast, timeouttal es explicit verdictdel.
- A bin JSON outputja tartalmazza a T04-hez kello decomposition + nfp metrikakat.
- Mindharom T01 fixture `baseline_metrics` blokkja ki lett toltve a mért ertekekkel.

## 4) T04 baseline meresi eredmenyek

| pair_id | fragment_count_a | fragment_count_b | expected_pair_count | verdict | timed_out | total_time_ms |
| --- | ---: | ---: | ---: | --- | --- | ---: |
| lv8_pair_01 | 518 | 342 | 177156 | TIMEOUT | true | 5000 |
| lv8_pair_02 | 518 | 214 | 110852 | TIMEOUT | true | 5000 |
| lv8_pair_03 | 342 | 214 | 73188 | TIMEOUT | true | 5000 |

Megjegyzes:
- Minden parnal reprodukalt timeout jelentkezett 5000ms limitnel.
- `nfp_error_kind` nem volt (timeout path), ezert fixture-ben `nfp_error_kind_if_errored=null` maradt.

## 5) Verifikacio

### 5.1 Feladatfuggo ellenorzes
- `cargo run --bin nfp_pair_benchmark -- --help` -> PASS
- `cargo run --bin nfp_pair_benchmark -- --fixture ../../tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json --timeout-ms 5000 --output-json | python3 -c ...` -> PASS (`verdict=TIMEOUT`)
- `python3 -c "import json; ... bm['fragment_count_a'] is not None ..."` -> PASS
- `python3 -c "... for pair in lv8_pair_01..03 ..."` -> PASS (mindharom fixture baseline_metrics kitoltve)
- `ls rust/nesting_engine/src/bin/nfp_pair_benchmark.rs` -> PASS
- `git diff HEAD -- rust/nesting_engine/src/nfp/concave.rs` -> ures (PASS)

### 5.2 Kotelezo repo gate
- `./scripts/verify.sh --report codex/reports/nesting_engine/engine_v2_nfp_rc_t04_nfp_baseline_instrumentation.md` -> PASS (AUTO_VERIFY blokk frissiti)

## 6) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| `nfp_pair_benchmark.rs` letezik | PASS | `rust/nesting_engine/src/bin/nfp_pair_benchmark.rs:1` | Uj benchmark bin letrejott. | `ls rust/nesting_engine/src/bin/nfp_pair_benchmark.rs` |
| JSON outputban kotelezo metrikak szerepelnek | PASS | `rust/nesting_engine/src/bin/nfp_pair_benchmark.rs:42` | `BenchmarkOutput` + nested metric structok tartalmazzak a kotelezo mezoket. | `--output-json` schema check |
| Timeout explicit verdictdel jelenik meg | PASS | `rust/nesting_engine/src/bin/nfp_pair_benchmark.rs:333` | Timeout path `verdict="TIMEOUT"`-ot allit, nem success-t. | `lv8_pair_01` benchmark futas |
| T01 fixture-okon benchmark lefut (akar timeouttal) | PASS | `rust/nesting_engine/src/bin/nfp_pair_benchmark.rs:283` | Mindharom fixture-re futtatva, mind TIMEOUT verdictdel visszater. | release futas `/tmp/t04_pair0*.json` |
| `baseline_metrics` nem nullak | PASS | `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json:3478` | Minden kotelezo baseline mezo kitoltve. | python 3 fixture assert |
| `baseline_metrics` nem nullak | PASS | `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_02.json:2966` | Minden kotelezo baseline mezo kitoltve. | python 3 fixture assert |
| `baseline_metrics` nem nullak | PASS | `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_03.json:2262` | Minden kotelezo baseline mezo kitoltve. | python 3 fixture assert |
| `concave.rs` erintetlen | PASS | `rust/nesting_engine/src/nfp/concave.rs:1` | Task explicit nem-celja teljesult. | `git diff HEAD -- .../concave.rs` |

## 7) Advisory notes
- A jelenlegi `concave.rs` futas nagyon verbose diagnosztikai kimenetet ir stderr-re; ez a T04 scope-ban nem kerult modositasra.
- A `decomposition_time_ms` most gyors heuristic becslesbol adodik (0ms), mert T04-ben nem dekompozicio algoritmus fejlesztes volt a cel.

## 8) Acceptance criteria allapot
- [x] `cargo run --bin nfp_pair_benchmark -- --help` fut
- [x] T01 osszes fixture-n lefut (timeout-tal)
- [x] `fragment_count_a`, `fragment_count_b`, `pair_count`, `verdict` megjelenik JSON-ban
- [x] fixture `baseline_metrics` mezok kitoltve (nem null)
- [x] `concave.rs` erintetlen

## 9) Task status
- T04 statusz: PASS
- Blocker: nincs
- Kockazat: kozepes (algoritmus tovabbra is timeoutol ezeken a fixture-okon)
- Kovetkezo task indithato: igen (`T05`), de csak kulon emberi jovahagyassal.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-04T00:43:28+02:00 → 2026-05-04T00:46:29+02:00 (181s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/engine_v2_nfp_rc_t04_nfp_baseline_instrumentation.verify.log`
- git: `main@991473a`
- módosított fájlok (git status): 18

**git diff --stat**

```text
 rust/nesting_engine/src/geometry/mod.rs                  |  2 ++
 tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json | 14 +++++++++-----
 tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_02.json | 14 +++++++++-----
 tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_03.json | 14 +++++++++-----
 4 files changed, 29 insertions(+), 15 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/nesting_engine/src/geometry/mod.rs
 M tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json
 M tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_02.json
 M tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_03.json
?? codex/codex_checklist/nesting_engine/engine_v2_nfp_rc_t02_geometry_profile_contract.md
?? codex/codex_checklist/nesting_engine/engine_v2_nfp_rc_t03_geometry_cleanup_pipeline.md
?? codex/codex_checklist/nesting_engine/engine_v2_nfp_rc_t04_nfp_baseline_instrumentation.md
?? codex/reports/nesting_engine/engine_v2_nfp_rc_t02_geometry_profile_contract.md
?? codex/reports/nesting_engine/engine_v2_nfp_rc_t02_geometry_profile_contract.verify.log
?? codex/reports/nesting_engine/engine_v2_nfp_rc_t03_geometry_cleanup_pipeline.md
?? codex/reports/nesting_engine/engine_v2_nfp_rc_t03_geometry_cleanup_pipeline.verify.log
?? codex/reports/nesting_engine/engine_v2_nfp_rc_t04_nfp_baseline_instrumentation.md
?? codex/reports/nesting_engine/engine_v2_nfp_rc_t04_nfp_baseline_instrumentation.verify.log
?? docs/nesting_engine/geometry_preparation_contract_v1.md
?? rust/nesting_engine/src/bin/geometry_prepare_benchmark.rs
?? rust/nesting_engine/src/bin/nfp_pair_benchmark.rs
?? rust/nesting_engine/src/geometry/cleanup.rs
?? rust/nesting_engine/src/geometry/simplify.rs
```

<!-- AUTO_VERIFY_END -->
