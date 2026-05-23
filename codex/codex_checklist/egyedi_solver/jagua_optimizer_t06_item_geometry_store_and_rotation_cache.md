# Checklist — JG-06 jagua_optimizer_t06_item_geometry_store_and_rotation_cache

## Feladat

ItemGeometryStore, deterministic instance expansion és 0/90/180/270 rotation cache megvalósítása outer-only polygonokra a JG-05 utáni Phase 1 láncban.

## Dependency

- [x] JG-05 report létezik.
- [x] JG-05 report első sora `PASS`.
- [x] JG-05 report tartalmazza: `JG-06_STATUS: READY`.
- [x] Repo szabályfájlok elolvasva: `AGENTS.md`, `docs/codex/overview.md`, `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md`, `docs/qa/testing_guidelines.md`.
- [x] Projektterv dokumentumok elolvasva.

## Item geometry store

- [x] Item instance id szabály dokumentálva. (`part_id__0001` format, lexikografikus sorrend)
- [x] Quantity expansion determinisztikus és tesztelt.
- [x] Part id / instance id kapcsolat explicit.
- [x] Area számítás rögzítve. (`rect_area(base_width, base_height)`)
- [x] Base bbox számítás rögzítve.
- [x] Exact outer geometry külön megőrzése dokumentált. (Part.outer_points / prepared_outer_points megmarad)
- [x] Proxy bbox/geometry representation dokumentált. (Phase 1: bbox-only proxy, explicit comment)
- [x] Hole metadata nem vész el és Phase 1-ben továbbra is unsupported gate alatt marad.

## Rotation cache

- [x] Allowed rotations ordering stabil. (input-occurrence-order, dokumentálva)
- [x] Duplicate rotációk determinisztikusan dedupe-olva. (unit teszt: [0,0,90,90] → [0,90])
- [x] 0 fokos cache entry működik.
- [x] 90 fokos cache entry működik.
- [x] 180 fokos cache entry működik.
- [x] 270 fokos cache entry működik.
- [x] Rotated bbox dimenziók helyesek. (unit teszt: 100×40 rot=90 → 40×100)
- [x] Anchor/min-offset vagy ezzel ekvivalens transform adat rögzítve. (bbox_min_offset_x/y)
- [x] Unsupported rotáció explicit hibát vagy unsupported státuszt ad. (unit teszt: 45° → Err; smoke: exit=1)
- [x] Unsupported rotáció nem silent drop.

## Smoke / tests

- [x] `scripts/smoke_jagua_item_geometry_store.py` létrejött.
- [x] Simple rectangle quantity expansion PASS.
- [x] Rotation cache summary PASS.
- [x] Unsupported rotation negatív eset PASS.
- [x] Determinism: azonos input két futásban azonos instance/rotation summary.
- [x] `cargo build --manifest-path rust/vrs_solver/Cargo.toml` PASS.
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml` PASS — 10/10.
- [x] `python3 scripts/smoke_jagua_item_geometry_store.py` PASS — 8/8.
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache.md` PASS — exit 0.
- [x] Verify log mentve: `codex/reports/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache.verify.log`.

## Report / checklist

- [x] Report tartalmaz dependency evidence-t.
- [x] Report tartalmaz item geometry store döntést.
- [x] Report tartalmaz rotation ordering policy döntést.
- [x] Report tartalmaz cache és determinism megjegyzést.
- [x] Report tartalmaz smoke futtatási parancsot és eredményt.
- [x] Globális progress checklist JG-06 szakasza frissítve.
- [x] Ha eltérés volt a tervtől, `DISCOVERED_MISMATCH`, `DEVIATION` vagy `REQUIRES_DECISION` blokk dokumentálja.
- [x] Report végső státusza: PASS / REVISE / BLOCKED.
- [x] Következő task indíthatósága jelölve: `JG-07_STATUS: READY`.
