# T06b — CFR Strategy Benchmark Checklist

## CFR call graph feltérképezve
✅ Already done in T06a (call graph: `nfp_placer.rs` → `compute_cfr_with_stats` → `compute_cfr_internal` → `run_overlay`)

## CFR diagnosztika env flag mögött
✅ `NESTING_ENGINE_CFR_SNAPSHOT_DIR` added to `cfr.rs`

## teljes LV8 cgal_reference reprodukáló futás elindítva
✅ 120s timeout run → 117 snapshot files written

## CFR log mentve
✅ 117 snapshot JSON files in `tmp/reports/nfp_cgal_probe/cfr_snapshots/`

## diagnosztika összesítő készült
✅ `cfr_union_benchmark` binary created and run

## top lassú CFR hívások azonosítva
✅ Top: 78nfp/23581v → 170ms, 76nfp/23089v → 167ms, 75nfp/22837v → 164ms

## union vs difference fő bottleneck eldöntve
✅ Union: 88% of total CFR time (11.8x ratio). Union IS the bottleneck, not strategy.

## irreleváns NFP polygon / bbox prefilter lehetőség értékelve
✅ No bbox prefilter applicable — every NFP is potentially relevant. But pre-merge/grouping is viable.

## batching lehetőség értékelve
✅ Batching NOT recommended — 1.17 poly/poly ratio, overhead would exceed benefit.

## i_overlay strategy tuning lehetőség értékelve
✅ DECISIVELY REJECTED: Strategy::List is FASTEST. Tree=0.76x, Auto=0.81x, Frag=0.79x slower.

## nincs optimizer rewrite
✅ No optimizer modified

## nincs production CGAL integráció
✅ CGAL remains dev-only probe, not default kernel

## nincs silent fallback
✅ No silent fallback introduced

## következő implementációs task javaslat elkészült
✅ T06c plan: NFP polygon bbox pre-merge spike in `nfp_placer.rs`
