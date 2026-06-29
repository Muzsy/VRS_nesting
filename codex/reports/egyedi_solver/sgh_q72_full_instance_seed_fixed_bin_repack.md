# SGH-Q72 Report - Full-instance seed + fixed-bin global repack

## 0) Statusz

**PARTIAL** - a task **fo architekturalis celja teljesult es mereheto**: a forced-latest ut tobbe
nem dob el darabot az optimalizalo elott (no-drop seed), a teljes seed atmegy a valodi exploration
SA + redistribute pipeline-on, es a placed_count **215 (Q71) -> 262**, ami **meghaladja a 259
baseline-t** (Q62). A layout-minoseg DoD pontja (DoD #4: nagy anchorok el-flush igazitasa) viszont
vizualisan **NEM teljesult** - a nagy darabok tovabbra is a tabla kozepe fele kerulnek, es a
maradek ter fragmentalt. Ez a kovetkezo fazis (edge-flush a compactionbol + osszefuggo-ter
celfuggveny) munkaja, ezert a teljes verdict PARTIAL, nem PASS.

## 1) Meta

- **Task slug:** `sgh_q72_full_instance_seed_fixed_bin_repack`
- **Kapcsolodo canvas:** `canvases/egyedi_solver/sgh_q72_full_instance_seed_fixed_bin_repack.md`
- **Kapcsolodo goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q72_full_instance_seed_fixed_bin_repack.yaml`
- **Futas datuma:** 2026-06-25
- **Branch / commit:** `main@<commit>` (verify.sh AUTO_VERIFY blokk rogzi)
- **Fokusz terulet:** `Geometry | Solver core (Sparrow BPP reduction)`

## 2) Scope

### 2.1 Cel

- Forced/strict latest modban a seed **ne dobjon el instance-t** az optimalizalo elott.
- A teljes seed fusson at a valodi globalis optimalizalon (exploration SA + redistribute) a
  rogzitett 2 tablan.
- A placed_count haladja meg a Q62 baseline-t (259), a 276 cel fele.

### 2.2 Nem-cel (explicit)

- Nem cel a 276/276 garantalt elerese egyetlen iteracioban.
- Nem cel uj anchor/corner/residual proxy heurisztika a mohou builderben.
- Nem cel spacing/margin csokkentes, infeasibility-kijelentes, folyamatos forgatas kikapcsolasa,
  part-id/koordinata hardcode.

## 3) Valtozasok osszefoglaloja (Change summary)

### 3.1 Erintett fajlok

- **Solver core:**
  - `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs` - `complete_seed_to_full_instance`
    helper + latest-lock no-drop seed kiegeszites + a latest-lock subsolve valodi idokerete.
  - `rust/vrs_solver/src/io.rs` - Q72 diagnosztikai mezok.
- **Teszt:**
  - `rust/vrs_solver/tests/sparrow_sheet_builder.rs` - `forced_latest_seed_retains_all_instances_no_drop`.
- **Benchmark / artifact:**
  - `scripts/bench_sgh_q72_full_instance_seed_fixed_bin_repack.py`
  - `artifacts/benchmarks/sgh_q72/` (inputs/outputs/logs/renders + q72_summary.json + q72_report.md)

### 3.2 Miert valtoztak?

- A forced-latest ut a darabokat az optimalizalo elott eldobta es kihagyta a globalis keresot, ezert
  a placed_count a baseline ala esett (Q70 237, Q71 215) es a budget ~75%-a kihasznalatlan maradt
  (Q71 wall 158 s / 600 s). A valtozas a darabokat a seedben tartja es a valodi keresore bizza a
  pakolast (Q72 wall 582 s / 600 s).

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs

- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q72_full_instance_seed_fixed_bin_repack.md`

### 4.2 Feladatfuggo ellenorzesek

- `cargo test --release --test sparrow_sheet_builder -- --test-threads=1` -> 5 passed (no-drop teszt zold).
- `python3 scripts/bench_sgh_q72_full_instance_seed_fixed_bin_repack.py --time-limit 600` ->
  placed=262, verdict PASS (bench acceptance: placed > baseline).
- Manualis vizualis audit: `sheet_00.png`, `sheet_01.png`, `overview.png` (lasd q72_report.md).

### 4.3 Ha valami kimaradt

- A DoD #4 (anchor edge-flush) szandekosan nincs lezarva: a render szerint a nagy anchorok meg a
  tabla kozepe fele kerulnek. Ez kulon fazis (Phase 2/3) - itt oszinten NEM-megoldottkent rogzitve.

### 4.4 Automatikus blokk

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-25T21:39:16+02:00 → 2026-06-25T21:47:26+02:00 (490s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q72_full_instance_seed_fixed_bin_repack.verify.log`
- git: `main@a96d649`
- módosított fájlok (git status): 29

**git diff --stat**

```text
 .../sgh_q56c/sheet_edge_anchor_candidates.json     |   74 +-
 .../sgh_q56c/sheet_edge_anchor_candidates.svg      |    2 +-
 .../sgh_q60/critical_group_admission.json          |    4 +-
 .../sgh_q61/critical_3part_real_spacing.svg        |    8 +-
 .../simultaneous_critical_production_cutover.json  |    4 +-
 rust/vrs_solver/src/io.rs                          |   39 +
 .../src/optimizer/sparrow/bpp_reduction.rs         | 1022 ++++++++++++++++++--
 .../sparrow/sheet_edge_placement_catalog.rs        |    9 +-
 rust/vrs_solver/tests/sparrow_sheet_builder.rs     |  105 ++
 9 files changed, 1158 insertions(+), 109 deletions(-)
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
?? canvases/egyedi_solver/sgh_q70_corner_first_residual_space_recovery.md
?? canvases/egyedi_solver/sgh_q71_anchor_edge_lock_and_flush_alignment.md
?? canvases/egyedi_solver/sgh_q72_full_instance_seed_fixed_bin_repack.md
?? codex/codex_checklist/egyedi_solver/sgh_q70_corner_first_residual_space_recovery.md
?? codex/codex_checklist/egyedi_solver/sgh_q71_anchor_edge_lock_and_flush_alignment.md
?? codex/codex_checklist/egyedi_solver/sgh_q72_full_instance_seed_fixed_bin_repack.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q70_corner_first_residual_space_recovery.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q71_anchor_edge_lock_and_flush_alignment.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q72_full_instance_seed_fixed_bin_repack.yaml
?? codex/reports/egyedi_solver/sgh_q70_corner_first_residual_space_recovery.md
?? codex/reports/egyedi_solver/sgh_q70_corner_first_residual_space_recovery.verify.log
?? codex/reports/egyedi_solver/sgh_q71_anchor_edge_lock_and_flush_alignment.md
?? codex/reports/egyedi_solver/sgh_q72_full_instance_seed_fixed_bin_repack.md
?? codex/reports/egyedi_solver/sgh_q72_full_instance_seed_fixed_bin_repack.verify.log
?? scripts/bench_sgh_q70_corner_first_residual_space_recovery.py
?? scripts/bench_sgh_q71_anchor_edge_lock_and_flush_alignment.py
?? scripts/bench_sgh_q72_full_instance_seed_fixed_bin_repack.py
```

<!-- AUTO_VERIFY_END -->

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| -------- | ------: | ------------------------ | ---------- | --------------------------- |
| 1. No-drop seed (276 instance a pipeline elott) | DONE | `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:4738` (`complete_seed_to_full_instance`), `:4929` (latest-lock keszites), `rust/vrs_solver/src/io.rs:415` (`bpp_q72_seed_instance_count_before_pipeline`) | `seed_instance_count_before_pipeline = 276`, `builder_placed = 220`, `reinserted = 56` (220+56=276). | `forced_latest_seed_retains_all_instances_no_drop` |
| 2. Globalis repack a rogzitett 2 tablan | DONE | `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:4957` (latest-lock subsolve `reduction_deadline`-ig) | A teljes seed atmegy az exploration SA-n; wall 582 s (vs Q71 158 s), `global_repack_reinserted_count=56`, `final_pairs=0`. | `artifacts/benchmarks/sgh_q72/q72_summary.json` |
| 3. Placed_count > 259 (baseline meghaladas) | DONE | `artifacts/benchmarks/sgh_q72/q72_summary.json` (`placed_count=262`) | 262 > 259 (Q62), > 237 (Q70), > 215 (Q71); unplaced=14, used_sheets=2. | Q72 benchmark acceptance |
| 4. El-/sarok-flush a compactionbol | **NOT MET** | `artifacts/benchmarks/sgh_q72/renders/q72_A_no_drop_repack_2sheet_sp5/sheet_00.png`, `sheet_01.png` | A render szerint a nagy anchorok a tabla kozepe fele kerulnek, a maradek ter fragmentalt. Phase 2/3 munka. | manualis render audit |
| 5. Teljeskoru run-rogzites | DONE | `artifacts/benchmarks/sgh_q72/` (inputs/outputs/logs/renders + q72_summary.json + q72_report.md) | input/output/log/render (SVG+PNG) + summary + report mind jelen. | artifact listazas |
| 6. Vizualis audit rogzitve | DONE | `artifacts/benchmarks/sgh_q72/q72_report.md` (Visual Audit szekcio) | Sheet 0/1 eredmeny-kozpontu ertekelese rogzitve (mi javult, mi NEM jo). | manualis render audit |
| 7. verify.sh PASS | DONE | `codex/reports/egyedi_solver/sgh_q72_full_instance_seed_fixed_bin_repack.verify.log` (check.sh exit 0, 490s), AUTO_VERIFY blokk: **PASS** | A repo gate (pytest+mypy+Sparrow smoke+determinism) zold. | verify.sh |

## 6) Finding

A Q70/Q71 stagnalas gyokeroka megszunt: a forced-latest ut tobbe nem dobja el a darabokat az igazi
optimalizalo elott, es a teljes seed a valodi exploration SA + redistribute uton fut a rogzitett 2
tablan. Ez merheto javulas: **placed 215 -> 262 (> 259 baseline)**, kihasznalt budget 158 s -> 582 s,
ervenyes (final_pairs=0, boundary_violations=0), folyamatos forgatas megmaradt (199 nem-ortogonalis).

A hatralevo, oszinten nem-megoldott resz a **layout-minoseg**: a nagy anchorok meg nincsenek a tabla
szeleihez flush-olva, es a maradek ter fragmentalt (kulonosen a sheet 1). Ez a kovetkezo fazis:
edge-flush a compaction post-passbol + az osszefuggo szabad ter mint valos SA-celfuggveny.
