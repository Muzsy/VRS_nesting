Olvasd el:
- AGENTS.md
- canvases/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.md
- codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.yaml

Majd hajtsd végre a YAML `steps` lépéseit sorrendben.

Kemény szabályok:
- Csak olyan fájlt hozhatsz létre / módosíthatsz, ami szerepel valamely step `outputs` listájában.
- Ez nem broad porting task. Csak a Q25-R5 audit sárga pontjait javítsd.
- Ez nem LV8 benchmark task. Ne optimalizálj benchmarkra, és ne adj hozzá LV8 minőségi acceptance gate-et.
- Ez nem compression task. Compression marad deferred.
- Fixed multisheet marad az alapmodell; nem kell és nem szabad strip-packingre visszaváltani.
- A cél nem report-szintű állítás, hanem source-level hardening.
- Strict large-item disruptionnél a normál kulcs/cutoff convex-hull area legyen, nem `width * height` / bbox area.
- Bbox fallback csak shape-preparation failure branchben maradhat, explicit kommenttel és reporttal.
- Strict touching edge/corner/boundary/exact-fit/epsilon edge case-eket valós CDE/tracker/evaluator pathon kell tesztelni.
- Kötelező upstream `.cache/sparrow` mapping audit kell. Ha `.cache/sparrow` nincs meg, állj meg `BLOCKED_UPSTREAM_MISSING` státusszal.
- Ne vezesd vissza a `WorkingLayout`, `VrsCollisionTracker`, bbox/AABB ranking, legacy VRS-core vagy dense-specific shortcut logikát.
- Ne gyengítsd a Q25-R5 strict profile invariánsait: LBF 1000/0/3, separator 50/25/3, loop 200/3, worker count 3, no strict downscaling, RNG shuffle worker ordering, strict touching policy.

Kötelező végső gate:
- cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
- cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
- python3 scripts/smoke_sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.py
- ./scripts/check.sh
- ./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.md

Eredményként frissítsd:
- codex/codex_checklist/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.md
- codex/reports/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.md
- codex/reports/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.verify.log

A végén add meg a módosított fájlok listáját és a gate-ek eredményét.
