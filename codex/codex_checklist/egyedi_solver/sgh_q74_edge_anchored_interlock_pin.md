# SGH-Q74 Checklist - Edge-anchored interlock seed + item pinning

- [x] Q74 canvas/YAML/checklist/report vaz elkeszult
- [x] Item-pinning infra: `SparrowState.locked_items` (tracker.rs)
- [x] Separator worker kihagyja a locked elemeket a move-celokbol (worker.rs)
- [x] `gravity_compact_layout` nem csusztatja a locked elemeket (bpp_reduction.rs)
- [x] `sanitize_partial` a locked elemeket elsobbseggel tartja (multisheet.rs)
- [x] `edge_anchored_interlock_big_seed` implementalva (slide-nest bbox-atfedessel + ellentetes-el
      horgonyzas + bounded 2D kozepso-nest)
- [x] Latest-lock wiring gate mogott (`VRS_EDGE_INTERLOCK_SEED`, default OFF) + q74_locked a pipeline-on at
- [x] Be nem fero nagy darabok kizarva a no-drop completionbol (nincs churn)
- [x] Q74 diagnosztikak felveve (`rust/vrs_solver/src/io.rs`)
- [x] Pin-survival regresszios teszt (`forced_latest_edge_interlock_seed_pins_big_parts_through_pipeline`)
- [x] cargo build + osszes sheet_builder teszt zold (7/7)
- [x] Full276 Q74 benchmark lefutott `artifacts/benchmarks/sgh_q74/` ala (placed 274/276, util 65.1%)
- [x] SVG/PNG render artifactok generalva (sheet_00, sheet_01, overview)
- [x] q74_summary.json + q74_report.md eredmeny-kozpontu (nagy-darab/tabla eloszlas + forgatas, Q72 vs)
- [x] Vizualis audit rogzitve (2 el-horgonyzott krescens/tabla, 92deg, pin altal megorizve)
- [x] 3/tabla allapot OSZINTEN rogzitve: 2/tabla (4 nagy), nem 3 — 2 unplaced; a 3/tabla a kovetkezo inkrement
- [x] Pinning bizonyitva: a nagy darabok TULELIK a pipeline-t (final_pairs=0, 92deg megorizve)
- [x] Codex report DoD -> Evidence Matrix kitoltve path+line bizonyitekkal
- [x] Default (gate OFF) = Q72 (262), nincs production regresszio
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q74_edge_anchored_interlock_pin.md` PASS (check.sh exit 0)
- [x] Teszt env-var verseny javitva (mutex `env_guard`) — 7/7 zold parhuzamosan is (check.sh parallel)
