# SGH-Q73 Report - Big-part pitch-minimizing interlock row-seed

## 0) Statusz

**PARTIAL (negativ eredmeny, oszinten rogzitve)** - a seeder building block kesz, tesztelt (6/6
cargo teszt zold), es **seed-time-ban mukodik** (4 nagy darab, 2/tabla, @ 81.5deg, pitch 521 mm,
CDE-valid, nem-ortogonalis). DE a teljes Full276 benchmarkon **regresszal**: a vegeredmeny 252 < 262
(Q72), mert a Sparrow magban **nincs elem-pinning**, es a pinneletlen exploration SA a nagy
darabokat (magas loss, sok kis darabbal atfedve) visszamozgatja ~90deg-ra es egyet kidob -> a seedet
szetveri. Emiatt a seeder **alapertelmezetten KI van kapcsolva** (`VRS_BIG_ROW_SEED`, default OFF),
a production latest-path valtozatlanul **262** (Q72). A 6/6 nagy darab (3/tabla) ennel a 2522 mm
hosszu alaknal **geometriailag nem all ossze** (shapely BL-pakolas prototipus is ezt mutatja) - ezt
oszinten rogzitjuk, nem spacing/margin csokkentessel.

Tovabbi lepes (a tenyleges net-nyereshez): item-pinning vagy obstacle-aware filling, hogy a seed
tulelje az exploration-t. Az elerheto plafon igy is csak ~4 nagy darab (2/tabla), mert 3/tabla
geometriailag kizart.

## 1) Meta

- **Task slug:** `sgh_q73_big_part_interlock_rowseed`
- **Kapcsolodo canvas:** `canvases/egyedi_solver/sgh_q73_big_part_interlock_rowseed.md`
- **Kapcsolodo goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q73_big_part_interlock_rowseed.yaml`
- **Futas datuma:** 2026-06-26
- **Branch / commit:** `main@<commit>` (verify.sh AUTO_VERIFY blokk rogzi)
- **Fokusz terulet:** `Geometry | Solver core (Sparrow BPP reduction)`

## 2) Scope

### 2.1 Cel

- A dominans ismetlodo nagy tipust a forced-latest seed ne 90 fokon, 1/tabla modon helyezze el,
  hanem a legkisebb CDE-clear pitch orientacion (nem-ortogonalis is), tablankent a max befero
  darabszammal, egy tablat feltoltve mielott uj tablat nyitna.
- A teljes placed_count ne regresszaljon a Q72 baseline (262) ala.

### 2.2 Nem-cel (explicit)

- Nem cel a 6/6 nagy darab (3/tabla): ennel a 2522 mm hosszu alaknal geometriailag nem all ossze;
  oszinten rogzitve.
- Nem cel proxy heurisztika a mohou builderben, spacing/margin csokkentes, forgatas-kikapcsolas,
  hardcode.

## 3) Valtozasok osszefoglaloja (Change summary)

### 3.1 Erintett fajlok

- **Solver core:**
  - `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs` - `repeated_big_critical_row_seed`
    (orientacio-sweep + CDE-validalt min-pitch row, fill-before-open) + latest-lock seed bekotes.
  - `rust/vrs_solver/src/io.rs` - Q73 diagnosztikak.
- **Teszt:**
  - `rust/vrs_solver/tests/sparrow_sheet_builder.rs` - `forced_latest_big_repeated_type_is_row_seeded_two_per_sheet`.
- **Benchmark / artifact:**
  - `scripts/bench_sgh_q73_big_part_interlock_rowseed.py`
  - `artifacts/benchmarks/sgh_q73/`

### 3.2 Miert valtoztak?

- A nagy darabok a min-bbox-szelesseg miatt 90 fokon, 1/tabla modon ultek; a sor-seed a tenyleges
  CDE-clear pitch alapjan (nem-ortogonalis is) tablankent 2-t helyez, feltoltve a sheet 0-t.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs

- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q73_big_part_interlock_rowseed.md`

### 4.2 Feladatfuggo ellenorzesek

- `cargo test --release --test sparrow_sheet_builder -- --test-threads=1` -> 6 passed.
- `python3 scripts/bench_sgh_q73_big_part_interlock_rowseed.py --time-limit 600`
- Manualis vizualis audit: `sheet_00.png`, `sheet_01.png`, `overview.png`.

### 4.3 Ha valami kimaradt

- A bench + verify lezarasa folyamatban; a nagy-darab 3/tabla limit geometriai (oszinten rogzitve).

### 4.4 Automatikus blokk

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-26T16:28:45+02:00 → 2026-06-26T16:36:54+02:00 (489s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q73_big_part_interlock_rowseed.verify.log`
- git: `main@a96d649`
- módosított fájlok (git status): 36

**git diff --stat**

```text
 .../sgh_q56c/sheet_edge_anchor_candidates.json     |   74 +-
 .../sgh_q56c/sheet_edge_anchor_candidates.svg      |    2 +-
 .../sgh_q60/critical_group_admission.json          |    4 +-
 .../sgh_q61/critical_3part_real_spacing.svg        |    8 +-
 .../simultaneous_critical_production_cutover.json  |    4 +-
 rust/vrs_solver/src/io.rs                          |   54 +
 .../src/optimizer/sparrow/bpp_reduction.rs         | 1221 +++++++++++++++++++-
 .../sparrow/sheet_edge_placement_catalog.rs        |    9 +-
 rust/vrs_solver/tests/sparrow_sheet_builder.rs     |  150 +++
 9 files changed, 1417 insertions(+), 109 deletions(-)
```

**git status --porcelain (preview)**

```text
 M artifacts/benchmarks/sgh_q56c/sheet_edge_anchor_candidates.json
 M artifacts/benchmarks/sgh_q56c/sheet_edge_anchor_candidates.svg
 M artifacts/benchmarks/sgh_q60/critical_group_admission.json
 M artifacts/benchmarks/sgh_q61/critical_3part_real_spacing.svg
 M artifacts/benchmarks/sgh_q67/simultaneous_critical_production_cutover.json
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs
 M rust/vrs_solver/src/optimizer/sparrow/sheet_edge_placement_catalog.rs
 M rust/vrs_solver/tests/sparrow_sheet_builder.rs
?? artifacts/benchmarks/sgh_q70/
?? artifacts/benchmarks/sgh_q71/
?? artifacts/benchmarks/sgh_q72/
?? artifacts/benchmarks/sgh_q73/
?? canvases/egyedi_solver/sgh_q70_corner_first_residual_space_recovery.md
?? canvases/egyedi_solver/sgh_q71_anchor_edge_lock_and_flush_alignment.md
?? canvases/egyedi_solver/sgh_q72_full_instance_seed_fixed_bin_repack.md
?? canvases/egyedi_solver/sgh_q73_big_part_interlock_rowseed.md
?? codex/codex_checklist/egyedi_solver/sgh_q70_corner_first_residual_space_recovery.md
?? codex/codex_checklist/egyedi_solver/sgh_q71_anchor_edge_lock_and_flush_alignment.md
?? codex/codex_checklist/egyedi_solver/sgh_q72_full_instance_seed_fixed_bin_repack.md
?? codex/codex_checklist/egyedi_solver/sgh_q73_big_part_interlock_rowseed.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q70_corner_first_residual_space_recovery.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q71_anchor_edge_lock_and_flush_alignment.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q72_full_instance_seed_fixed_bin_repack.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q73_big_part_interlock_rowseed.yaml
?? codex/reports/egyedi_solver/sgh_q70_corner_first_residual_space_recovery.md
?? codex/reports/egyedi_solver/sgh_q70_corner_first_residual_space_recovery.verify.log
?? codex/reports/egyedi_solver/sgh_q71_anchor_edge_lock_and_flush_alignment.md
?? codex/reports/egyedi_solver/sgh_q72_full_instance_seed_fixed_bin_repack.md
?? codex/reports/egyedi_solver/sgh_q72_full_instance_seed_fixed_bin_repack.verify.log
?? codex/reports/egyedi_solver/sgh_q73_big_part_interlock_rowseed.md
?? codex/reports/egyedi_solver/sgh_q73_big_part_interlock_rowseed.verify.log
?? scripts/bench_sgh_q70_corner_first_residual_space_recovery.py
?? scripts/bench_sgh_q71_anchor_edge_lock_and_flush_alignment.py
?? scripts/bench_sgh_q72_full_instance_seed_fixed_bin_repack.py
?? scripts/bench_sgh_q73_big_part_interlock_rowseed.py
```

<!-- AUTO_VERIFY_END -->

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| -------- | ------: | ------------------------ | ---------- | --------------------------- |
| 1. Sor-seed aktiv (seed-time) | DONE | `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs` (`repeated_big_critical_row_seed`, `big_row_seed_enabled`), `rust/vrs_solver/src/io.rs` (`bpp_q73_big_row_seed_used`) | A dominans nagy tipus sor-seedet kap (gate: `VRS_BIG_ROW_SEED`): 4 db, 2/tabla, @81.5deg, pitch 521. | `forced_latest_big_repeated_type_is_row_seeded_two_per_sheet` |
| 2. 2/tabla eloszlas (vegeredmeny) | **NOT MET** | `artifacts/benchmarks/sgh_q73/q73_summary.json` (`big_part.dominant_per_sheet_rotations` = {"1":[89.9,269.9],"0":[90.0]}) | Seed-time 2/tabla, de az exploration sheet 0-t 1-re csokkenti -> a vegeredmenyben nem 2/tabla. | Q73 benchmark |
| 3. Nem-ortogonalis orientacio (vegeredmeny) | **NOT MET** | `artifacts/benchmarks/sgh_q73/q73_summary.json` (`dominant_non_orthogonal_count`=0) | Seed @81.5deg, de az exploration visszaforgatja ~90deg-ra. | Q73 benchmark |
| 4. Nincs darabszam-regresszio (>=262) | **NOT MET** | `artifacts/benchmarks/sgh_q73/q73_summary.json` (`placed_count`=252) | 252 < 262 -> regresszio; ezert a seeder default OFF. | Q73 benchmark |
| 5. Teljeskoru run-rogzites + vizualis audit | DONE | `artifacts/benchmarks/sgh_q73/` (inputs/outputs/logs/renders + summary + report; Visual Audit szekcio) | input/output/log/render + summary + report jelen; vizualis audit rogzitve. | render audit |
| 6. Oszinte 3/tabla limit | DONE | `canvases/egyedi_solver/sgh_q73_big_part_interlock_rowseed.md` (Context/Non-goals), `artifacts/benchmarks/sgh_q73/q73_report.md` (Visual Audit) | 3/tabla geometriai limit rogzitve (shapely prototipus), nem spacing/margin csokkentessel. | prototipus |
| 7. verify.sh PASS | DONE | `codex/reports/egyedi_solver/sgh_q73_big_part_interlock_rowseed.verify.log` | repo gate; default viselkedes (seeder OFF) = Q72, nincs regresszio; tesztek zoldek. | verify.sh |

## 6) Finding

A nagy darabok eddig a min-bbox-szelesseg miatt 90 fokon, 1/tabla modon ultek. A Q73 sor-seed a
tenyleges CDE-clear pitch alapjan valasztja az orientaciot (nem-ortogonalis is), es tablankent
feltolti a max befero darabszamot, mielott uj tablat nyitna. A 3/tabla az adott ~2522 mm hosszu
alaknal geometriailag nem all ossze (Python+shapely prototipus is ezt mutatja); ezt oszinten
rogzitjuk, nem spacing/margin csokkentessel.
