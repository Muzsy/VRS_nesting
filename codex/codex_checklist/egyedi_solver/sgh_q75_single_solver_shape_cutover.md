# SGH-Q75 Checklist - Single solver-shape cutover cleanup

- [x] Q75 canvas/YAML/checklist/report vaz elkeszult
- [x] Fazis 1: `SPInstance.spacing_collision_base_shape` mezo torolve (model.rs)
- [x] Minden collision/boundary olvasas a `base_shape` (egy alak) ellen (11 fajl, mezo-olvasas csere)
- [x] model.rs spacing-shape epitese + spacing_unsupported_parts torolve (diagnosztika 0-ra)
- [x] tracker.rs `spacing_applied` always-false (Q36 dual-ut kivezetve, ertelmetlen ptr_eq javitva)
- [x] Dual-geometry unit tesztek a single-shape modellre frissitve:
      `orientation_catalog::extrema_trace_true_solver_contour`, `verify_one_part_sheet_edge_placement`
      (offset-bake + spacing=0, mint production)
- [x] Fazis 2: SolverInputGuard hard-fail top-level hole-ra (`CAVITY_PREPACK_TOP_LEVEL_HOLES_REMAIN`,
      adapter.rs, pipeline-szinten)
- [x] Fazis 3: PartAnalysis furat-mezoi igazoltan diagnosztika-only (sehol nem dontesi input) + dokumentalva
- [x] Fazis 4: tracker/terminologia tisztitva
- [x] Build zold (release)
- [x] 550 lib teszt zold (cutover utan)
- [x] Erintett integracios tesztek zoldek (technology/spacing, one_part_sheet_edge 1/1, sheet_builder 7/7, q61 8/8)
- [x] Production no-regress: Q74 600s = 274 (azonos a cutover elottivel); Q72 254 = wall-time-zaj
- [x] Gated-modul diagnosztikai artifact-valtozasok oszinten rogzitve (NEM production-regresszio)
- [x] Codex report DoD -> Evidence Matrix kitoltve path+line bizonyitekkal
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q75_single_solver_shape_cutover.md` PASS (check.sh exit 0, 479s)
