Olvasd el:
- AGENTS.md
- canvases/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.md
- codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.yaml

Majd hajtsd végre a YAML `steps` lépéseit sorrendben.

Kemény szabályok:
- Csak olyan fájlt hozhatsz létre / módosíthatsz, ami szerepel valamely step `outputs` listájában.
- Ez nem LV8 benchmark task. Ne optimalizálj benchmarkra, és ne adj hozzá LV8 minőségi acceptance gate-et.
- Ez nem compression task. Compression marad deferred.
- Fixed multisheet marad az alapmodell; nem kell és nem szabad strip-packingre visszaváltani.
- A cél nem újabb report-szintű állítás, hanem source-level strict Sparrow parity profile.
- Strict parity módban touching/exact boundary fit nem lehet implicit `NoCollision`.
- Strict parity módban separator sample budget 50/25/3, LBF budget 1000/0/3, worker count 3, separator loop 200/3.
- Strict parity módban nincs instance-count alapú sample shrink.
- Strict worker ordering: RNG shuffle only, nincs worst-first/reverse/least-loss-first worker-index bias.
- Exploration restore: normal-biased pool selection, nem seed+attempt modulo better-half.
- Disruption: random large-item pair poolból, nem mindig a top két legnagyobb.
- Ne vezesd vissza a `WorkingLayout`, `VrsCollisionTracker`, bbox/AABB ranking, legacy VRS-core vagy dense-specific shortcut logikát.

Kötelező végső gate:
- cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
- cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
- python3 scripts/smoke_sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.py
- ./scripts/check.sh
- ./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.md

Eredményként frissítsd:
- codex/codex_checklist/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.md
- codex/reports/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.md
- codex/reports/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.verify.log

A végén add meg a módosított fájlok listáját és a gate-ek eredményét.
