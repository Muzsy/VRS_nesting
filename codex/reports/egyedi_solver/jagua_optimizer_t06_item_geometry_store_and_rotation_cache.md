PASS

## 1) Meta

- **Task slug:** `jagua_optimizer_t06_item_geometry_store_and_rotation_cache`
- **Task ID:** `JG-06`
- **Kapcsolódó canvas:** `canvases/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t06_item_geometry_store_and_rotation_cache.yaml`
- **Runner prompt:** `codex/prompts/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache/run.md`
- **Futás dátuma:** `2026-05-23`
- **Fókusz terület:** `ItemGeometryStore | rotation cache | instance expansion determinism | unsupported rotation gate`

---

## 2) Dependency ellenőrzés

| Ellenőrzés | Eredmény |
|---|---|
| JG-05 report létezik | IGAZ |
| JG-05 report első sora | `PASS` |
| JG-05 report tartalmazza `JG-06_STATUS: READY` | IGAZOLT |
| Goal YAML sanity | YAML_OK, `steps: 9`, nincs sandbox path |

---

## 3) Valós kód audit

### `rust/vrs_solver/src/item.rs` (JG-06 előtt)

- `Part` struct: `id`, `width`, `height`, `quantity`, `allowed_rotations_deg: Vec<i64>`, hole/outer geometry `Option<JsonValue>` mezőkkel.
- `normalize_allowed_rotations(raw)`: 0/90/180/270 validáció + dedupe; **input-occurrence-order** megőrzés (első előfordulás). Unsupported rotation → `Err`.
- `dims_for_rotation(w, h, rot)`: rotált bbox (w,h).
- `rotated_bbox_min_offset(w, h, rot)`: anchor offset per rotation.
- `placement_anchor_from_rect_min(...)`: placer anchor számítás.
- `expand_instances(parts)`: `part_id__0001` instance_id, lexikografikusan rendez.
- `can_fit_any_stock(part, sheets)`: fér-e bármely sheetre bármely rotációval.
- `Instance`: `instance_id`, `part_id`, `width`, `height`, `allowed_rotations_deg`.

### `rust/vrs_solver/src/geometry.rs` (JG-06 előtt)

- `Point`, `Rect`, `PointInput`, `polygon_bbox`, jagua konverziók.
- Nincs polygon area, nincs rotate-polygon helper.

### JG-06 ItemGeometryStore döntés

**Döntés: `item.rs`-ben marad, nem kell új modul.** A meglévő típusok mellé kerülnek az új struktúrák. A YAML `outputs` listája `item.rs`-t és `geometry.rs`-t tartalmaz — ez elégséges.

**Rotation ordering policy: input-occurrence-order** (a `normalize_allowed_rotations` már ezt csinálja). Canonical sorted ordering nem kerül bevezetésre, hogy ne törjük a meglévő viselkedést. A döntés explicit dokumentálva van.

**Exact/proxy separation:**
- Exact outer geometry: `Part.outer_points` / `Part.prepared_outer_points` (serde_json::Value) — megmarad, nem vész el.
- Proxy cache: bbox-alapú (`RotationCacheEntry.width/height`) — Phase 1 elegendő.
- Explicit dokumentálva: `// Phase 1 proxy model: bbox-based rotation cache only.`

---

## 4) Implementáció

### `geometry.rs` — `rect_area()`

```rust
pub fn rect_area(width: f64, height: f64) -> f64 {
    width * height
}
```

### `item.rs` — ItemGeometryStore

Hozzáadva `expand_instances()` után:

```rust
pub struct RotationCacheEntry {
    pub rotation_deg: i64,
    pub width: f64,
    pub height: f64,
    pub bbox_min_offset_x: f64,
    pub bbox_min_offset_y: f64,
}

pub struct ItemGeometryRecord {
    pub part_id: String,
    pub quantity: i64,
    pub base_width: f64,
    pub base_height: f64,
    pub area: f64,                        // rect_area(base_width, base_height)
    pub allowed_rotations: Vec<i64>,      // input-occurrence-order, deduped
    pub rotation_cache: Vec<RotationCacheEntry>,
}

pub struct ItemGeometryStore {
    pub records: Vec<ItemGeometryRecord>,
}

pub fn build_item_geometry_store(parts: &[Part]) -> Result<ItemGeometryStore, String>
```

`build_item_geometry_store` hívja `normalize_allowed_rotations` → unsupported rotation explicit `Err`.

---

## 5) Futtatási eredmények

### cargo build

```
Finished `dev` profile [unoptimized + debuginfo] target(s) in 1.49s
```

**PASS**

### cargo test (10/10)

```
test item::tests::item_geometry_store_all_four_rotations ... ok
test item::tests::item_geometry_store_area ... ok
test item::tests::item_geometry_store_deterministic ... ok
test item::tests::item_geometry_store_duplicate_rotation_deduped ... ok
test item::tests::item_geometry_store_rotation_cache_dims ... ok
test item::tests::item_geometry_store_unsupported_rotation_error ... ok
test item::tests::placement_anchor_from_rect_min_keeps_rotated_bbox_inside_target_rect ... ok
test item::tests::rotated_bbox_min_offset_matches_expected_quadrants ... ok
test sheet::tests::expand_sheets_stable_order_and_quantity ... ok
test sheet::tests::expand_sheets_zero_quantity_skipped ... ok

test result: ok. 10 passed; 0 failed
```

**PASS**

### python3 scripts/smoke_jagua_item_geometry_store.py (8/8)

```
[Determinism] PASS: identical placements across 2 runs (3 placed)
[Rotation 90°] PASS: part placed at rotation=90 (width=80 > sheet_w=40, only fits rotated)
[Duplicate dedupe] PASS: duplicate rotations produce identical placement to deduped list
[Unsupported rot] PASS: solver correctly rejected rotation=45 (exit=1)
[All 4 rotations] PASS: all 4 instances placed
[All 4 rotations] PASS: exact validator PASS on 4-rotation layout
[JG-05 regression] PASS: solver status=ok
[JG-05 regression] PASS: exact validator PASS on JG-05 smoke fixture
=== RESULTS: 8 PASS, 0 FAIL ===
OVERALL: PASS
```

**PASS**

---

## 6) Contract summary

| Contract pont | Státusz |
|---|---|
| `build_item_geometry_store` Err unsupported rotation-ra | ✓ IGAZOLT (unit teszt: 45° → Err, smoke: exit=1) |
| Duplicate rotation dedupe | ✓ IGAZOLT (unit teszt: [0,0,90,90] → [0,90]) |
| Input-occurrence ordering | ✓ IGAZOLT (megtartva, dokumentálva) |
| area = base_w × base_h | ✓ IGAZOLT (unit teszt: 80×60=4800) |
| 0/90/180/270 bbox cache | ✓ IGAZOLT (unit teszt: 100×40 → rot=90 gives 40×100) |
| Exact geometry nem vész el | ✓ DOKUMENTÁLVA (Part.outer_points / prepared_outer_points megmarad) |
| Determinism | ✓ IGAZOLT (ugyanaz az input → azonos output, 2 futás) |
| JG-05 rectangulár regresszió | ✓ IGAZOLT (smoke: JG-05 fixture PASS) |
| adapter.rs / optimizer/mod.rs nem módosult | ✓ IGAZ (nem kellett backward compat módosítás) |

---

## 7) Módosított / létrehozott fájlok

| Fájl | Változás |
|---|---|
| `rust/vrs_solver/src/geometry.rs` | `rect_area()` hozzáadva |
| `rust/vrs_solver/src/item.rs` | `RotationCacheEntry`, `ItemGeometryRecord`, `ItemGeometryStore`, `build_item_geometry_store()`, 6 unit teszt |
| `scripts/smoke_jagua_item_geometry_store.py` | ÚJ — JG-06 smoke (8 check) |
| `codex/codex_checklist/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache.md` | Frissítve |
| `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md` | JG-06 szekció frissítve |

---

JG-07_STATUS: READY

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-23T13:18:43+02:00 → 2026-05-23T13:21:42+02:00 (179s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache.verify.log`
- git: `main@550f7db`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 .../jagua_optimizer_task_progress_checklist.md     |  32 ++--
 rust/vrs_solver/src/geometry.rs                    |   4 +
 rust/vrs_solver/src/item.rs                        | 182 ++++++++++++++++++++-
 3 files changed, 201 insertions(+), 17 deletions(-)
```

**git status --porcelain (preview)**

```text
 M canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
 M rust/vrs_solver/src/geometry.rs
 M rust/vrs_solver/src/item.rs
?? canvases/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache.md
?? codex/codex_checklist/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t06_item_geometry_store_and_rotation_cache.yaml
?? codex/prompts/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache/
?? codex/reports/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache.md
?? codex/reports/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache.verify.log
?? scripts/smoke_jagua_item_geometry_store.py
```

<!-- AUTO_VERIFY_END -->
