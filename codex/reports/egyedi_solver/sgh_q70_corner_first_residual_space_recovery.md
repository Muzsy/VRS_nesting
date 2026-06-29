# DONE - SGH-Q70 Corner-first residual-space recovery

## Meta

- Task slug: `sgh_q70_corner_first_residual_space_recovery`
- Canvas: `canvases/egyedi_solver/sgh_q70_corner_first_residual_space_recovery.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q70_corner_first_residual_space_recovery.yaml`
- Fokusz: `critical anchor authority + residual-space recovery`

## Kiindulasi problema

- A Q69 forced-latest run oszinten megmutatta az uj utvonalat, de a nagy kritikus alkatreszeknel a
  center-seat es a gyenge completion miatt a layout minoseg rossz maradt.
- A render alapjan az elso tabla kirivoan alultoltott, es a solver nem hasznalja eleg eros
  authorityval a maradek egybefuggo szabad ter szempontjat.

## Tervezett bizonyitekok

- path+line evidence a corner-first / center-seat authority valtozasrol
- teszt, ami forced-latest alatt ved a center-seat regresszio ellen
- uj Full276 benchmark sheetenkenti kihasznaltsaggal es manualis vizualis audittal

## DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| -------- | ------: | ------------------------ | ---------- | --------------------------- |
| Corner-first / residual-space authority megerositve | DONE | `rust/vrs_solver/src/optimizer/sparrow/sheet_edge_placement_catalog.rs:11`, `rust/vrs_solver/src/optimizer/sparrow/sheet_edge_placement_catalog.rs:530`, `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:215`, `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:2678` | A catalog oldalon a corner variants first-class statuszt kapnak, a score erosabban bunteti a center kandidansokat, a builder oldalon pedig forced-latest alatt kulon corner vs center authority dontes tortenik, ahol a center csak materialis nyereseg eseten torhet at. | `cargo test --manifest-path rust/vrs_solver/Cargo.toml forced_latest_catalog_ -- --nocapture` |
| Forced-latest alatt center-seat regresszio vedett | DONE | `rust/vrs_solver/src/io.rs:381`, `rust/vrs_solver/tests/sparrow_sheet_builder.rs:120` | Uj diagnosztikai mezok rogzitik, hogy a center policy blokkolt, override-olt vagy csak last-resort ut volt-e, es erre explicit regresszios teszt is van. | `cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_sheet_builder forced_latest -- --nocapture` |
| Q70 benchmark artifactcsomag letrehozva | DONE | `scripts/bench_sgh_q70_corner_first_residual_space_recovery.py:1`, `artifacts/benchmarks/sgh_q70/q70_summary.json:1`, `artifacts/benchmarks/sgh_q70/q70_report.md:1` | A Full276 2x1500x3000 margin5 spacing5 continuous csomag ujrafutott forced-latest lockkal, es teljes input/output/log/render/report artifactot irt. | `python3 scripts/bench_sgh_q70_corner_first_residual_space_recovery.py --time-limit 600` |
| Vizualis audit eredmeny-kozpontuan rogzitve | DONE | `artifacts/benchmarks/sgh_q70/q70_report.md:45`, `artifacts/benchmarks/sgh_q70/renders/q70_A_corner_first_2sheet_sp5/render_manifest.json:1` | A report mar nem placeholder: rogzitve van, hogy a sheet 0 belso uregei feltoltesre kerultek, a nagy elemek edge/corner authority szerint indulnak, es a masodik tabla sem regressziv center-dump kepet mutat. | manualis ellenorzes: `sheet_00.png`, `sheet_01.png` |
| `./scripts/verify.sh --report ...` lefutott | DONE | `codex/reports/egyedi_solver/sgh_q70_corner_first_residual_space_recovery.verify.log` | A repo gate PASS eredmennyel lefutott; a report auto-verify blokkja rogzitette a pontos futasi adatokat es a git allapotot is. | `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q70_corner_first_residual_space_recovery.md` |

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-24T18:39:42+02:00 → 2026-06-24T18:48:01+02:00 (499s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q70_corner_first_residual_space_recovery.verify.log`
- git: `main@a96d649`
- módosított fájlok (git status): 16

**git diff --stat**

```text
 .../sgh_q56c/sheet_edge_anchor_candidates.json     |  74 +++---
 .../sgh_q56c/sheet_edge_anchor_candidates.svg      |   2 +-
 .../sgh_q60/critical_group_admission.json          |   4 +-
 .../sgh_q61/critical_3part_real_spacing.svg        |   8 +-
 .../simultaneous_critical_production_cutover.json  |   4 +-
 rust/vrs_solver/src/io.rs                          |  17 ++
 .../src/optimizer/sparrow/bpp_reduction.rs         | 296 +++++++++++++++++++--
 .../sparrow/sheet_edge_placement_catalog.rs        |   9 +-
 rust/vrs_solver/tests/sparrow_sheet_builder.rs     |  39 +++
 9 files changed, 388 insertions(+), 65 deletions(-)
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
?? canvases/egyedi_solver/sgh_q70_corner_first_residual_space_recovery.md
?? codex/codex_checklist/egyedi_solver/sgh_q70_corner_first_residual_space_recovery.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q70_corner_first_residual_space_recovery.yaml
?? codex/reports/egyedi_solver/sgh_q70_corner_first_residual_space_recovery.md
?? codex/reports/egyedi_solver/sgh_q70_corner_first_residual_space_recovery.verify.log
?? scripts/bench_sgh_q70_corner_first_residual_space_recovery.py
```

<!-- AUTO_VERIFY_END -->
