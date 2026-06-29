# SGH-Q73 Checklist - Big-part pitch-minimizing interlock row-seed

- [x] Q73 canvas/YAML/checklist/report vaz elkeszult
- [x] `repeated_big_critical_row_seed` implementalva (dominans nagy tipus, orientacio-sweep,
      CDE-validalt min-pitch, tablankenti eloszlas fill-before-open)
- [x] Geometria a tenyleges transzformalt polygon-bboxbol (`prepare_shape_native`), nem sarok-origo
- [x] Latest-lock seedbe bekotve gate mogott (`VRS_BIG_ROW_SEED`, default OFF) + Q72 no-drop kiegeszites
- [x] Q73 diagnosztikak felveve (`rust/vrs_solver/src/io.rs`)
- [x] Q73 regresszios teszt zold (`forced_latest_big_repeated_type_is_row_seeded_two_per_sheet`, 6/6 passed)
- [x] Full276 Q73 benchmark lefutott `artifacts/benchmarks/sgh_q73/` ala (input/output/log)
- [x] SVG/PNG render artifactok generalva (sheet_00, sheet_01, overview)
- [x] q73_summary.json + q73_report.md eredmeny-kozpontu (nagy-darab/tabla eloszlas + forgatas, Q72 vs)
- [ ] 2/tabla eloszlas a vegeredmenyben — **NOT MET**: seed-time 2/tabla @81.5deg, de az exploration
      visszaforgatja ~90deg-ra es sheet 0-t 1-re csokkenti (pinning hianya)
- [ ] Nincs darabszam-regresszio — **NOT MET**: 252 < 262 (Q72); ezert a seeder default OFF
- [x] Vizualis audit eredmenye rogzitve (nagy darabok eloszlasa/forgatasa + maradekter; oszintan negativ)
- [x] Oszinte 3/tabla geometriai limit rogzitve (shapely prototipus), nem spacing/margin csokkentessel
- [x] Codex report DoD -> Evidence Matrix kitoltve path+line bizonyitekkal
- [x] Default viselkedes (seeder OFF) = Q72 (262), nincs production regresszio
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q73_big_part_interlock_rowseed.md` PASS (check.sh exit 0, 489s)
