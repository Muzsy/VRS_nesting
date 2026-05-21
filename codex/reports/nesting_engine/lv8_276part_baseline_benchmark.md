# LV8 276-Part Full Nesting Baseline Benchmark

**Date:** 2026-05-17  
**Input:** `tmp/lv8_single_benchmark/prepacked_solver_input.json` (cavity-prepacked, 276 parts, 12 types)  
**Engine:** `rust/nesting_engine` release build  
**Command:** `nest --placer nfp --compaction off`

## Results

| Metric | Value |
|--------|-------|
| Parts placed | **276 / 276** |
| Sheets used | **3** (223 + 51 + 2 parts) |
| Utilization | **49.4%** |
| Runtime | **~65 seconds** |
| NFP cache hits | 118,576 |
| NFP cache misses | 874 |
| NFP cache hit rate | **99.3%** |
| NFP compute calls | 874 |

## Key Fixes Applied (This Session)

### Problem: Machine Freeze (OOM) + Zero Parts Placed
Previous attempts caused machine freeze due to OOM during NFP computation for complex polygons.

### Fix 1: Polygon Simplification (main.rs)
- Lowered `NESTING_ENGINE_SIMPLIFY_MAX_REFLEX` default: **30 → 12**
- Raised `NESTING_ENGINE_SIMPLIFY_MAX_EPSILON_MM` default: **20mm → 100mm**
- Result: Lv8_11612 (2522×732mm, 520 vertices) → **16 vertices, 7 reflex** (eps=51.2mm)
- NFP pairs for Lv8_11612: **1849 → 196** (14×14 triangles)

### Fix 2: Decomp Cache (concave.rs)
- Thread-local `CONVEX_DECOMP_CACHE: HashMap<u64, Vec<Polygon64>>`
- Polygon ring hash prevents re-decomposition of the same shape across multiple NFP pairs
- 99.3% cache hit rate confirms the cache is working effectively

### Fix 3: Batched NFP Fragment Union (concave.rs, previous session)
- `NFP_FRAGMENT_BATCH_SIZE = 32`, hierarchical tree-reduce
- Prevents i_overlay memory explosion for large fragment counts

### Polygon Simplification Summary
```
Lv8_11612:  520 → 16 vertices, 7 reflex  (eps=51.200mm)
Lv8_07921:  344 → 30 vertices, 12 reflex (eps=1.600mm)
Lv8_07920:  215 → 39 vertices, 11 reflex (eps=0.400mm)
Lv8_07919:  165 → 46 vertices, 11 reflex (eps=0.100mm)
Lv8_15348:   54 → 16 vertices,  7 reflex (eps=3.200mm)
Lv8_10059:   52 → 26 vertices,  0 reflex (eps=0.100mm)
LV8_00057:   29 → 22 vertices,  6 reflex (eps=0.100mm)
LV8_02049:   28 → 15 vertices,  0 reflex (eps=0.100mm)
Lv8_15435:   66 → 34 vertices,  3 reflex (eps=0.100mm)
```

## Notes
- Input `ne2_input_lv8jav.json` triggers BLF fallback (hole_collapsed parts) — use prepacked input for NFP benchmark
- Memory usage stable at ~5-15MB RSS (no freeze risk)
- RLIMIT_AS set to 12GB as safety guard
