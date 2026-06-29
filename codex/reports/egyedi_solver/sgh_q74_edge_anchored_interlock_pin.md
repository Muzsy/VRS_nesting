# SGH-Q74 Report - Edge-anchored interlock seed + item pinning

## 0) Statusz

**PASS (a task scope-jara) — eros, mereheto elorelepes; a 276 cel 2 darabra van.** A pinning + edge-
anchored interlock seed mukodik es a Full276-on **placed 274/276** (Q72: 262, **+12**), fizikai
kihasznaltsag **65.1%** (Q72: 53.4%, **+11.7pp**), `final_pairs=0 / boundary=0` (ervenyes). A nagy
`Lv8_11612` krescensbol **4 db (2/tabla) all el, 92deg-on (nem-ortogonalis), a tabla szeleihez
horgonyozva ES a pin altal MEGORIZVE** a teljes pipeline-on at — a Q73 regresszio (visszaforgatas
90deg-ra + kidobas) MEGOLDVA. A 2 elhelyezetlen darab pontosan a 3.-per-tabla nagy krescens.

**Oszinte korlat:** 2 nagy/tabla (4 a 6-bol), nem 3. A 3. krescens egy y-eltolt 2D-lepcsos nestet
igenyel (minden krescens a hosszanti tengely menten eltolva, hogy melyebben atfedjenek); a jelenlegi
fix-y horgony + bounded kozepso-scan 2/tablat er el. Ez a vegso inkrement a 276-hoz (Q75).
Default production valtozatlan (gate `VRS_EDGE_INTERLOCK_SEED` OFF ⇒ Q72 viselkedes, 262).

## 1) Meta

- **Task slug:** `sgh_q74_edge_anchored_interlock_pin`
- **Kapcsolodo canvas:** `canvases/egyedi_solver/sgh_q74_edge_anchored_interlock_pin.md`
- **Kapcsolodo goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q74_edge_anchored_interlock_pin.yaml`
- **Futas datuma:** 2026-06-26
- **Branch / commit:** `main@<commit>` (verify.sh AUTO_VERIFY blokk rogzi)
- **Fokusz terulet:** `Geometry | Solver core (Sparrow pinning + interlock seed)`

## 2) Scope

### 2.1 Cel

- Item-pinning: a seedelt nagy kritikus darabok fix akadalykent tuleljek az exploration separator +
  gravity + sanitize utat (a Q73 pinning-hiany megszuntetese).
- Edge-anchored, nem-ortogonalis, bbox-atfedo mely interlock seed a nagy ismetlodo tipusra.
- Default production valtozatlan (gate `VRS_EDGE_INTERLOCK_SEED`, OFF).

### 2.2 Nem-cel (explicit)

- Nem cel a 6/6 (3/tabla) garantalt elerese; oszinten rogzitve, ha 2/tabla.
- Nem cel proxy heurisztika, spacing/margin csokkentes, forgatas-kikapcsolas, hardcode.

## 3) Valtozasok osszefoglaloja (Change summary)

### 3.1 Erintett fajlok

- **Pinning infra:** `tracker.rs` (`SparrowState.locked_items`), `worker.rs` (move-target szures),
  `multisheet.rs` (`sanitize_partial` locked-prioritas).
- **Solver core:** `bpp_reduction.rs` (`edge_anchored_interlock_big_seed`, `edge_interlock_seed_enabled`,
  run_subsolve/gravity locked param, latest-lock wiring, no-drop exclude), `io.rs` (Q74 diag).
- **Teszt:** `tests/sparrow_sheet_builder.rs` (pin-survival).
- **Benchmark:** `scripts/bench_sgh_q74_edge_anchored_interlock_pin.py`, `artifacts/benchmarks/sgh_q74/`.

### 3.2 Miert valtoztak?

- A Q73 a jo seedet a pinneletlen exploration miatt elvesztette. A Q74 pinning + sanitize-protect
  megtartja a seedet; a seeder az ellentetes elekhez horgonyozza + mely interlockkal nesztelii a nagy
  darabokat.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs

- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q74_edge_anchored_interlock_pin.md`

### 4.2 Feladatfuggo ellenorzesek

- `cargo test --release --test sparrow_sheet_builder -- --test-threads=1`
- `python3 scripts/bench_sgh_q74_edge_anchored_interlock_pin.py --time-limit 600`
- Manualis vizualis audit: `sheet_00.png`, `sheet_01.png`, `overview.png`.

### 4.3 Ha valami kimaradt

- A bench + verify lezarasa folyamatban; a 3/tabla allapota oszinten rogzitendo.

### 4.4 Automatikus blokk

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-26T22:11:09+02:00 → 2026-06-26T22:19:02+02:00 (473s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q74_edge_anchored_interlock_pin.verify.log`
- git: `main@a96d649`
- módosított fájlok (git status): 46

**git diff --stat**

```text
 .../sgh_q56c/sheet_edge_anchor_candidates.json     |   74 +-
 .../sgh_q56c/sheet_edge_anchor_candidates.svg      |    2 +-
 .../sgh_q60/critical_group_admission.json          |    4 +-
 .../sgh_q61/critical_3part_real_spacing.svg        |    8 +-
 .../simultaneous_critical_production_cutover.json  |    4 +-
 rust/vrs_solver/src/io.rs                          |   69 +
 .../src/optimizer/sparrow/bpp_reduction.rs         | 1593 +++++++++++++++++++-
 .../vrs_solver/src/optimizer/sparrow/multisheet.rs |   20 +-
 .../src/optimizer/sparrow/quantify/tracker.rs      |    6 +
 .../sparrow/sheet_edge_placement_catalog.rs        |    9 +-
 rust/vrs_solver/src/optimizer/sparrow/worker.rs    |   10 +
 rust/vrs_solver/tests/sparrow_sheet_builder.rs     |  211 +++
 12 files changed, 1887 insertions(+), 123 deletions(-)
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
 M rust/vrs_solver/src/optimizer/sparrow/multisheet.rs
 M rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs
 M rust/vrs_solver/src/optimizer/sparrow/sheet_edge_placement_catalog.rs
 M rust/vrs_solver/src/optimizer/sparrow/worker.rs
 M rust/vrs_solver/tests/sparrow_sheet_builder.rs
?? artifacts/benchmarks/sgh_q70/
?? artifacts/benchmarks/sgh_q71/
?? artifacts/benchmarks/sgh_q72/
?? artifacts/benchmarks/sgh_q73/
?? artifacts/benchmarks/sgh_q74/
?? canvases/egyedi_solver/sgh_q70_corner_first_residual_space_recovery.md
?? canvases/egyedi_solver/sgh_q71_anchor_edge_lock_and_flush_alignment.md
?? canvases/egyedi_solver/sgh_q72_full_instance_seed_fixed_bin_repack.md
?? canvases/egyedi_solver/sgh_q73_big_part_interlock_rowseed.md
?? canvases/egyedi_solver/sgh_q74_edge_anchored_interlock_pin.md
?? codex/codex_checklist/egyedi_solver/sgh_q70_corner_first_residual_space_recovery.md
?? codex/codex_checklist/egyedi_solver/sgh_q71_anchor_edge_lock_and_flush_alignment.md
?? codex/codex_checklist/egyedi_solver/sgh_q72_full_instance_seed_fixed_bin_repack.md
?? codex/codex_checklist/egyedi_solver/sgh_q73_big_part_interlock_rowseed.md
?? codex/codex_checklist/egyedi_solver/sgh_q74_edge_anchored_interlock_pin.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q70_corner_first_residual_space_recovery.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q71_anchor_edge_lock_and_flush_alignment.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q72_full_instance_seed_fixed_bin_repack.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q73_big_part_interlock_rowseed.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q74_edge_anchored_interlock_pin.yaml
?? codex/reports/egyedi_solver/sgh_q70_corner_first_residual_space_recovery.md
?? codex/reports/egyedi_solver/sgh_q70_corner_first_residual_space_recovery.verify.log
?? codex/reports/egyedi_solver/sgh_q71_anchor_edge_lock_and_flush_alignment.md
?? codex/reports/egyedi_solver/sgh_q72_full_instance_seed_fixed_bin_repack.md
?? codex/reports/egyedi_solver/sgh_q72_full_instance_seed_fixed_bin_repack.verify.log
?? codex/reports/egyedi_solver/sgh_q73_big_part_interlock_rowseed.md
?? codex/reports/egyedi_solver/sgh_q73_big_part_interlock_rowseed.verify.log
?? codex/reports/egyedi_solver/sgh_q74_edge_anchored_interlock_pin.md
?? codex/reports/egyedi_solver/sgh_q74_edge_anchored_interlock_pin.verify.log
?? scripts/bench_sgh_q70_corner_first_residual_space_recovery.py
?? scripts/bench_sgh_q71_anchor_edge_lock_and_flush_alignment.py
?? scripts/bench_sgh_q72_full_instance_seed_fixed_bin_repack.py
?? scripts/bench_sgh_q73_big_part_interlock_rowseed.py
?? scripts/bench_sgh_q74_edge_anchored_interlock_pin.py
```

<!-- AUTO_VERIFY_END -->

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| -------- | ------: | ------------------------ | ---------- | --------------------------- |
| 1. Pinning mukodik (seed tuleli) | DONE (smoke) | `tracker.rs` (`SparrowState.locked_items`), `worker.rs` (locked move-szures), `bpp_reduction.rs` gravity skip, `multisheet.rs` sanitize-protect | Tiny smoke: 4 nagy darab, 2/tabla, 92deg megorizve, final_pairs=0. | `forced_latest_edge_interlock_seed_pins_big_parts_through_pipeline` |
| 2. Edge-anchored + nem-ortogonalis | DONE (smoke) | `bpp_reduction.rs` (`edge_anchored_interlock_big_seed`) | A nagy darabok a szeleken, 92deg (nem 90 kenyszer). | tiny smoke |
| 3. Nincs production regresszio (gate OFF) | DONE | `bpp_reduction.rs` (`edge_interlock_seed_enabled`, default OFF) | Gate OFF eseten a Q74 ut kimarad ⇒ Q72 viselkedes (262). | verify.sh / kod |
| 4. Full276 eredmeny + 3/tabla oszinte allapot | DONE | `artifacts/benchmarks/sgh_q74/q74_summary.json`, `artifacts/benchmarks/sgh_q74/q74_report.md` | placed **274/276** (Q72 262), util **65.1%** (Q72 53.4%); nagy: 2/tabla @92deg; 3/tabla NEM elert (2 unplaced), oszinten rogzitve. | Q74 benchmark |
| 5. Teljeskoru run-rogzites + vizualis audit | DONE | `artifacts/benchmarks/sgh_q74/` (inputs/outputs/logs/renders + summary + report; Visual Audit szekcio) | input/output/log/render (SVG+PNG) + summary + report jelen; vizualis audit rogzitve (2 el-horgonyzott krescens/tabla, megorizve). | render audit |
| 6. verify.sh PASS | DONE | `codex/reports/egyedi_solver/sgh_q74_edge_anchored_interlock_pin.verify.log`, AUTO_VERIFY blokk | repo gate; default (gate OFF) = Q72, nincs regresszio; 7/7 sheet_builder teszt zold. | verify.sh |

## 6) Finding

A Q73 gyokeroka (pinning hianya) megszunt: a seedelt nagy darabok mostantol fix akadalyok az
exploration + gravity + sanitize uton, igy a szelhez horgonyzott, nem-ortogonalis (92deg) mely
interlock seed TULELI a pipeline-t (tiny smoke: 4 nagy, 2/tabla, megorizve). A 3/tabla (a referencia
y-eltolt lepcsos neszt) allapota a Full276 benchmark + vizualis audit utan kerul oszinten rogzitesre.
