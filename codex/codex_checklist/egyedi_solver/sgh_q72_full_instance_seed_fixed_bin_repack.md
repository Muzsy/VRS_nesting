# SGH-Q72 Checklist - Full-instance seed + fixed-bin global repack

- [x] Q72 canvas/YAML/checklist/report vaz elkeszult
- [x] No-drop seed wiring kesz: forced/strict latest alatt a layout a pipeline elott mind a 276
      instance-t tartalmazza (builder 220 + reinserted 56 = 276; builder critical/anchor megtartva)
- [x] A teljes seed atmegy a valodi exploration SA + redistribute uton a rogzitett 2 tablan
      (latest-lock subsolve a reduction-ablakot kapja; wall 582 s vs Q71 158 s)
- [ ] El-/sarok-flush a gravity/compaction post-passbol jon ki, nem pre-forced pozicionalasbol
      (DoD #4 - NOT MET: a render szerint a nagy anchorok meg a kozep fele kerulnek; Phase 2 munka)
- [x] Q72 production diagnosztikak felveve (`rust/vrs_solver/src/io.rs`): no_drop_seed_used,
      seed_instance_count_before_pipeline, seed_builder_placed_before_completion,
      global_repack_reinserted_count
- [x] No-drop regresszios teszt zold (`rust/vrs_solver/tests/sparrow_sheet_builder.rs`),
      single-threaded (5/5 passed)
- [x] Full276 Q72 benchmark lefutott `artifacts/benchmarks/sgh_q72/` ala (input/output/log)
- [x] SVG/PNG render artifactok generalva (sheet_00, sheet_01, overview)
- [x] q72_summary.json + q72_report.md eredmeny-kozpontu: placed_count vs Q62(259)/Q70(237)/Q71(215),
      sheetenkenti kihasznaltsag
- [x] Placed_count > 259 (baseline) ELLENORIZVE: 262 (> 259, > 237, > 215)
- [x] Vizualis audit eredmenye rogzitve (maradekter + anchor el-igazitas a renderen; oszintan: a
      flush meg nem jo)
- [x] Codex report DoD -> Evidence Matrix kitoltve path+line bizonyitekkal (DoD #4 NOT MET rogzitve)
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q72_full_instance_seed_fixed_bin_repack.md` PASS (check.sh exit 0, 490s)
