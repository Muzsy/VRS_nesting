# SGH-Q76 Checklist - Skeleton-first seed + residual-fill (contour residual-space objective)

- [x] Q76 canvas/YAML/checklist/report vaz elkeszult
- [x] Kontur maradekter-objektiv: flood-fill kozos helperbe kiemelve (sheet_skeleton.rs)
- [x] `largest_edge_connected_free_area_contour` + `_slot_contour` (scanline poligon-raszter) bevezetve
- [x] Bbox-verziok valtozatlanok (meglevo hivok erintetlenek; additiv)
- [x] Magas-csucsu kontúr egyszerusitve a 50mm-gridhez (`decimate_poly`)
- [x] Unit teszt: konkav darab obleje SZABAD a kontur-verzioban, FOGLALT a bboxban
- [x] `build_skeleton_first_seed` + `skeleton_first_enabled` (gate `VRS_SKELETON_FIRST`, default OFF)
- [x] Particio: `criticality_tier()==Critical` + `VRS_SKELETON_FRAC` kapacitas-sapka (default 0.5)
- [x] Skeleton-elhelyezes: el-horgony (`anchor_candidates_for_instance`), per-tabla (fill-sheet-first),
      a KONTUR-free-area maximalizalasaval, pinnelve (`locked_items`)
- [x] Residual-fill: `direct_insert_on_sheet` loop (csokkeno, largest-room-first), a kieso darabokat is
      visszateve (no-drop completion + exploration)
- [x] Wiring a seed-blokkba (`q74_locked = skeleton`); a pinnelt skeleton tuleli az exploration/gravity/sanitize-t
- [x] F1 diagnosztikak (io.rs): skeleton_count, skeleton_area_frac, largest_free_after_skeleton, fill_placed/unplaced, final_largest_free
- [x] F1 regresszios teszt zold (parhuzamos futasra is, env-guard) + gate-OFF inaktivitas teszt
- [x] Build zold; 551 lib + 9 sparrow_sheet_builder integracios teszt zold
- [x] Full276 Q76 A/B lefutott (`artifacts/benchmarks/sgh_q76/`): default 252/37.96 vs skeleton 274/65.07
- [x] 2. csomag (kis/kozepes-darabos, MixedMed) A/B lefutott (generikussag): dontetlen 120/120 (nincs regresszio)
- [x] q76_summary.json + q76_report.md eredmeny-kozpontu (placed + util + kontur-free-area + validitas)
- [x] Vizualis audit rogzitve (skeleton el-horgonyzott + interlock, residual feltoltve; default szetszort)
- [x] ACCEPT: generikusan nem rontja a defaultot mindket csomagon, Full276-on erdemben veri (+22/+27pp)
- [x] Default (gate OFF) = byte-azonos production (gate-OFF teszt + additiv valtozasok)
- [x] Codex report DoD -> Evidence Matrix kitoltve path+line bizonyitekkal
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q76_skeleton_first_residual_fill.md` PASS (check.sh exit 0, 481s)
