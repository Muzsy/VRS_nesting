# codex/prompts/nesting_engine/nesting_engine_spatial_index_rtree_and_sweepline_self_intersect/run.md

Szerep: **VRS_nesting task runner (canvas+YAML+verify fegyelmezett végrehajtás)**

Feladat:
A nesting_engine teljesítmény-kockázatainak kezelése két módosítással:
1) Spatial index (rstar::RTree) bevezetése a baseline placer feasibility broad-phase jelöltgyűjtéséhez.
2) Sweep-line (geo) self-intersect detektálás bevezetése a pipeline brute-force O(N^2) helyett.

Kötelező szabályok:
- Kövesd az AGENTS.md + codex szabályokat.
- Ne találgass: csak a repó valós fájlstruktúrája és konvenciói alapján dolgozz.
- Csak a YAML step `outputs` listájában szereplő fájlokat hozhatod létre/módosíthatod.
- A változtatás nem módosíthatja a funkcionalitást: csak a broad-phase jelöltek számát és a self-intersect detektálás komplexitását.
- Determinizmus megőrzése kötelező: a narrow-phase jelöltek explicit sorrendezése maradjon meg.

Inputok:
- Canvas: `canvases/nesting_engine/nesting_engine_spatial_index_rtree_and_sweepline_self_intersect.md`
- Goal: `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_spatial_index_rtree_and_sweepline_self_intersect.yaml`

Végrehajtás:
1) Olvasd be a canvas-t és a YAML-t, majd hajtsd végre a step-eket sorrendben.
2) Geo sweep-line:
   - Add hozzá a geo dependency-t a rust/nesting_engine/Cargo.toml-hoz.
   - Cseréld a pipeline.rs polygon_self_intersects implementációját geo sweep-line-ra.
   - A viselkedés maradjon: self-intersect -> STATUS_SELF_INTERSECT (nem auto-fix).
3) RTree broad-phase:
   - narrow.rs-ben vezess be PlacedIndex-et (Vec + RTree).
   - can_place a PlacedIndex-ből query-zzen (AABB envelope intersect).
   - A query eredményét explicit sortold (min_x, min_y) narrow-phase előtt.
4) blf.rs:
   - állj át PlacedIndex state-re, és a can_place hívást igazítsd.
5) Tesztek:
   - pipeline: self-intersect teszt
   - placer/feasibility: determinism regresszió megmaradjon
6) Checklist + report:
   - rögzítsd a változásokat és a determinisztikus rendezés tényét.
7) Verify:
   Futtasd:
     ./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_spatial_index_rtree_and_sweepline_self_intersect.md
   és mentsd:
     codex/reports/nesting_engine/nesting_engine_spatial_index_rtree_and_sweepline_self_intersect.verify.log

Kimenetek:
- `canvases/nesting_engine/nesting_engine_spatial_index_rtree_and_sweepline_self_intersect.md`
- `rust/nesting_engine/Cargo.toml`
- `rust/nesting_engine/src/geometry/pipeline.rs`
- `rust/nesting_engine/src/feasibility/narrow.rs`
- `rust/nesting_engine/src/placement/blf.rs`
- `codex/codex_checklist/nesting_engine/nesting_engine_spatial_index_rtree_and_sweepline_self_intersect.md`
- `codex/reports/nesting_engine/nesting_engine_spatial_index_rtree_and_sweepline_self_intersect.md`
- `codex/reports/nesting_engine/nesting_engine_spatial_index_rtree_and_sweepline_self_intersect.verify.log`

Ha a geo sweep-line API eltér a várttól:
- először derítsd fel a pontos importot és trait használatot a geo crate dokumentációjából / type errors alapján,
- és csak utána commitold a végleges megoldást.
Ne hozz létre “saját sweep-line”-t: a döntés a geo crate használata.