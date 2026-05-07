# T06a — CFR Bottleneck Audit Checklist

## Státusz: DONE

### Call Graph
- [x] CFR call graph feltérképezve
- [x] `nfp_placer.rs` → `compute_cfr_with_stats` → `compute_cfr_internal` hívási lánc azonosítva
- [x] `cfr.rs` belső lépések (encode, union, diff, decode, sort) dokumentálva
- [x] `concave.rs:union_nfp_fragments` nem a LV8 bottleneck — igazolva
- [x] `Strategy::List` mindkét helyen: `cfr.rs:126` és `concave.rs:1073`
- [x] Polygon típusok azonosítva (Polygon64 → IntShape → IntContour)
- [x] Nincs bbox prefilter, nincs clipping, nincs batching — dokumentálva

### Instrumentáció
- [x] CFR diagnosztika env flag mögött (`NESTING_ENGINE_CFR_DIAG=1`)
- [x] `emit_cfr_diag()` függvény: `nfp_poly_count`, `nfp_total_vertices`, `nfp_max_vertices`, `ifp_vertices`, `union_time_ms`, `diff_time_ms`, `component_count`, `component_total_vertices`, `candidate_count`, `total_cfr_time_ms`
- [x] Threshold: `nfp_poly_count >= 50` VAGY `total_cfr_time_ms >= 1000` VAGY env flag
- [x] `Instant` timing a `compute_cfr_internal`-ben

### Reprodukáló futás
- [x] Teljes LV8 cgal_reference reprodukáló futás elindítva
- [x] 120s timeout alatt futott le
- [x] CFR log mentve: `tmp/reports/nfp_cgal_probe/t06a_lv8_cfr_diag.log` (312 lines)

### Diagnosztika összesítő
- [x] `scripts/experiments/summarize_cfr_diag.py` elkészült
- [x] JSON output: `tmp/reports/nfp_cgal_probe/t06a_lv8_cfr_diag_summary.json`
- [x] MD output: `tmp/reports/nfp_cgal_probe/t06a_lv8_cfr_diag_summary.md`

### Bottleneck azonosítás
- [x] Top 10 lassú CFR hívások táblázva
- [x] max nfp_poly_count = 77
- [x] max nfp_total_vertices = 23,717
- [x] max union_time_ms = 128.58ms
- [x] max diff_time_ms = 9.73ms
- [x] max total_cfr_time_ms = 148.29ms
- [x] union_vs_diff_ratio = 11.8x — union dominál

### Hipotézisek
- [x] A) NFP union fő bottleneck: IGEN (11.8x ratio)
- [x] B) IFP difference fő bottleneck: NEM (max 9.73ms)
- [x] C) Candidate extraction bottleneck: NEM (max 10 components)
- [x] D) Irreleváns NFP polygonok: NEM (minden polygon metszi az IFP-t)
- [x] E) CGAL vertex count: HOZZÁJÁRULÓ (23k vertex input), de nem egyedüli ok
- [x] F) i_overlay Strategy::List: valós, de vak csere tilos
- [x] G) Cache működik, CFR újraszámolás: IGEN

### Opciók értékelése
- [x] Opció 1 (IFP bbox prefilter): NEM ALKALMAZHATÓ — minden NFP releváns
- [x] Opció 2 (placement-space clipping): NEM ALKALMAZHATÓ
- [x] Opció 3 (batched union — concave.rs): NEM UGYANAZ A BOTTLENECK
- [x] Opció 4 (NFP output simplification): KOCKÁZATOS — külön task
- [x] Opció 5 (i_overlay strategy tuning): MÉRÉS SZÜKSÉGES
- [x] Opció 6 (incremental CFR): NAGY ALGORITMIKUS VÁLTOZÁS
- [x] Opció 7 (NFP polygon pre-merge): AJÁNLOTT
- [x] Opció 8 (IFP area skip): AJÁNLOTT

### Tiltások betartva
- [x] Nincs optimizer rewrite
- [x] Nincs production CGAL integráció
- [x] Nincs silent fallback
- [x] Nincs greedy/SA/multi-sheet stratégia módosítás
- [x] Nincs default kernel váltás
- [x] Nincs vak i_overlay strategy csere

### Következő task javaslat
- [x] T06b: NFP polygon bbox pre-merge + IFP area skip spike

### Riportok
- [x] Fő riport: `codex/reports/nesting_engine/engine_v2_nfp_rc_t06a_cfr_bottleneck_audit.md`
- [x] Checklista: `codex/codex_checklist/nesting_engine/engine_v2_nfp_rc_t06a_cfr_bottleneck_audit.md`
