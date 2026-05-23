PASS

## 1) Meta

- **Task slug:** `jagua_optimizer_t04_jagua_adapter_contract_poc`
- **Task ID:** `JG-04`
- **Kapcsolódó canvas:** `canvases/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t04_jagua_adapter_contract_poc.yaml`
- **Runner prompt:** `codex/prompts/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc/run.md`
- **Futás dátuma:** `2026-05-23`
- **Fókusz terület:** `Jagua backend adapter PoC | JaguaAdapter contract | item-item collision smoke | item-sheet boundary smoke`

---

## 2) Dependency ellenőrzés

| Ellenőrzés | Eredmény |
|---|---|
| JG-02 report első sora | `PASS` (`codex/reports/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold.md`) |
| JG-03 report első sora | `PASS` (`codex/reports/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.md`) |
| `JG-04_STATUS: READY` | IGAZOLT (JG-03 report 9. szekció) |
| Goal YAML sanity | `YAML_OK, steps: 9`, nincs sandbox path |

---

## 3) DISCOVERED_MISMATCH

`canvases/jagua_rs_sajat_optimizer/plan/jagua_rs_sajat_optimizer_fejlesztesi_terv.md` a JG-04-et régi névvel jelöli:

```text
Task JG-04 — Rectangular single-sheet baseline optimizer
```

Az aktuális `jagua_optimizer_canvas_yaml_runner_task_bontas.md` és master runner szerint a hivatalos definíció:

```text
JG-04 — jagua_optimizer_t04_jagua_adapter_contract_poc
Phase 1 / backend adapter
```

Feloldás: az aktuális task-bontást követtem. A régi cím planning drift, nem érvényes scope.

---

## 4) Code-boundary audit (JG-03 utáni állapot)

| Fájl | JG-04-ben érintett terület |
|---|---|
| `rust/vrs_solver/Cargo.toml` | `jagua-rs = "0.6.4"` már jelen van |
| `rust/vrs_solver/src/geometry.rs` | `to_jag_point()`, `to_jag_polygon()`, `jag_edge_from_points()` — conversion helperek |
| `rust/vrs_solver/src/sheet.rs` | `CollidesWith`, `SPolygon` — stock hole collision |
| `rust/vrs_solver/src/adapter.rs` | `solve(input)` orchestration + JG-03 hole gate; JG-04 hozzáad `JaguaAdapterError` + `JaguaAdapter` struct |
| `rust/vrs_solver/src/main.rs` | `mod` deklarációk eltávolítva → `use vrs_solver::{adapter, io}` |
| `rust/vrs_solver/src/lib.rs` | ÚJ — 6 modul pub expozíciója, szükséges a smoke binary hozzáféréshez |
| `rust/vrs_solver/src/bin/jagua_adapter_smoke.rs` | ÚJ — 3-eset smoke, JSON output |
| `scripts/smoke_jagua_adapter_contract.py` | ÚJ — Python smoke driver |

---

## 5) Adapter contract döntés

**Választott opció: A — adapter.rs belső JaguaAdapter struct (meglévő solve() megtartásával)**

Indoklás:
- Az adapter.rs-be kerülnek az új típusok (`JaguaAdapterError`, `JaguaAdapter`) a meglévő `solve()` után.
- A `solve()` és a JG-03 hole gate **nem változott**.
- Jagua-specifikus típusok (`SPolygon`, `JagPoint`, `JagEdge`, `CollidesWith`) nem jelennek meg a publikus API-ban — csak a `check_polygon_collision()` függvény belsejében kerülnek importálásra.
- `src/lib.rs` létrehozásának indoka: a `src/bin/jagua_adapter_smoke.rs` binárisnak szüksége van a meglévő modulokra (`geometry`, `sheet`). A library crate expozíció elegánsabb és kevesebb duplikálást okoz, mint standalone copy.

---

## 6) Implementált változások

### 6.1 `rust/vrs_solver/src/lib.rs` (ÚJ)

```rust
pub mod adapter;
pub mod geometry;
pub mod io;
pub mod item;
pub mod optimizer;
pub mod sheet;
```

Library crate root; szükséges a `src/bin/*.rs` binárisok számára.

### 6.2 `rust/vrs_solver/src/main.rs` (módosítva)

```rust
// Korábban: mod adapter; mod geometry; mod io; mod item; mod optimizer; mod sheet;
use vrs_solver::{adapter, io};
```

A mod deklarációk átkerültek `lib.rs`-be; main.rs a library crate-t használja.
A `main()` funkciója változatlan.

### 6.3 `rust/vrs_solver/src/adapter.rs` (módosítva)

```rust
/// VRS-owned error categories for the jagua backend boundary.
/// No jagua-rs types appear here.
pub enum JaguaAdapterError {
    ConversionError(String),
    BackendError(String),
    Unsupported(String),
}

/// Thin VRS adapter to the jagua-rs collision/geometry backend.
/// Accepts VRS-owned point slices; jagua types never appear in the public API.
/// Precision note: f64 VRS coordinates are narrowed to f32 for jagua.
pub struct JaguaAdapter;

impl JaguaAdapter {
    pub fn check_polygon_collision(
        poly_a: &[crate::geometry::Point],
        poly_b: &[crate::geometry::Point],
    ) -> Result<bool, JaguaAdapterError> {
        // jagua imports csak ezen függvény belsejében
        // 1. corners of B inside A
        // 2. corners of A inside B
        // 3. edge-edge intersection
    }

    pub fn check_rect_in_sheet(
        item_rect: crate::geometry::Rect,
        sheet: &crate::sheet::SheetShape,
    ) -> bool {
        crate::sheet::rect_inside_sheet_shape(item_rect, sheet)
    }
}
```

Meglévő `solve(input)` és JG-03 hole gate **érintetlen**.

### 6.4 `rust/vrs_solver/src/bin/jagua_adapter_smoke.rs` (ÚJ)

3 teszteset, determinisztikus JSON output:

```json
{
  "status": "ok",
  "cases": {
    "item_item_non_overlap": true,
    "item_item_overlap": true,
    "item_sheet_boundary": true
  },
  "notes": ["f64_to_f32_conversion_used"]
}
```

Tesztesetek:
1. `item_item_non_overlap`: Rect A=(0,0)-(50,50), Rect B=(100,0)-(150,50) — disjunkt → `false`
2. `item_item_overlap`: Rect A=(0,0)-(100,100), Rect B=(60,60)-(160,160) — B sarokpont (60,60) A belsejében → `true`
3. `item_sheet_boundary`: 200×200 sheet; item (50,50)-(100,100) belül ok; item (180,180)-(220,220) kilóg → `rect_inside_sheet_shape` false

### 6.5 `scripts/smoke_jagua_adapter_contract.py` (ÚJ)

- `cargo build --bin jagua_adapter_smoke` futtatása
- Binary JSON output parse-olása
- 4 explicit assertion: `status=ok`, `item_item_non_overlap=true`, `item_item_overlap=true`, `item_sheet_boundary=true`, `f64_to_f32_conversion_used` note jelenlét
- exit code 0 csak teljes PASS esetén

---

## 7) API megfigyelések és ismert korlátok

| Megfigyelés | Részlet |
|---|---|
| `SPolygon.collides_with(JagPoint)` | Működik — igazolt `sheet.rs`-ben és `jagua_adapter_smoke`-ban |
| `JagEdge.collides_with(JagEdge)` | Működik — igazolt `sheet.rs`-ben |
| `SPolygon.collides_with(SPolygon)` | Nem tesztelve; implementáció ehelyett point containment + edge intersection kompozíciót használ |
| f64 → f32 konverzió | `to_jag_point()` elvégzi; precision loss lehetséges nagy koordinátáknál; dokumentálva a `notes` mezőben |
| Winding order | CCW winding szükséges `SPolygon::new()`-hoz; a rect constructor (x1,y1),(x2,y1),(x2,y2),(x1,y2) sorrend kompatibilis |
| `JagEdge::try_new` | `None` ha két pont azonos (zero-length edge); `jag_edge_from_points` ezt kezeli |

---

## 8) Viselkedésváltozás táblázat

| Elem | Változott? | Megjegyzés |
|---|---|---|
| `solve(input)` rectangular baseline | NO | változatlan |
| JG-03 Phase 1 hole gate | NO | változatlan |
| `main.rs` mod deklarációk | YES | lib.rs-be kerültek; funkcionalitás azonos |
| `src/lib.rs` | NEW | szükséges a smoke binary modulhozzáféréséhez |
| `src/bin/jagua_adapter_smoke.rs` | NEW | PoC smoke binary |
| `scripts/smoke_jagua_adapter_contract.py` | NEW | Python smoke driver |
| `adapter.rs` | EXTENDED | JaguaAdapterError + JaguaAdapter hozzáadva; solve() érintetlen |
| JG-03 outer-only smoke regression | NO | 11/11 PASS |

---

## 9) Verifikáció

### 9.1 Cargo build

```bash
cargo build --release --manifest-path rust/vrs_solver/Cargo.toml
# PASS (3.26s)
```

### 9.2 Cargo test

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml
# test item::tests::placement_anchor_from_rect_min_keeps_rotated_bbox_inside_target_rect ... ok
# test item::tests::rotated_bbox_min_offset_matches_expected_quadrants ... ok
# test result: ok. 2 passed
```

### 9.3 Jagua adapter smoke

```bash
python3 scripts/smoke_jagua_adapter_contract.py
```

| Assertion | Eredmény |
|---|---|
| cargo build --bin jagua_adapter_smoke | PASS |
| status=ok | PASS |
| item_item_non_overlap=true | PASS |
| item_item_overlap=true | PASS |
| item_sheet_boundary=true | PASS |
| f64_to_f32_conversion_used note | PASS |

### 9.4 JG-03 outer-only regression smoke

```bash
python3 scripts/smoke_jagua_optimizer_outer_only_contract.py
# ALL SMOKE TESTS PASSED (11/11)
```

### 9.5 Repo gate

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.md
```

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-23
- parancs: `./scripts/check.sh`
- log: `codex/reports/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.verify.log`

<!-- AUTO_VERIFY_END -->

---

## 10) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték |
|---|---|---|
| JG-02 dependency PASS | PASS | report 1. sor |
| JG-03 dependency PASS | PASS | report 1. sor |
| JG-04_STATUS = READY | PASS | JG-03 report 9. szekció |
| Goal YAML parse OK | PASS | YAML_OK, steps: 9 |
| DISCOVERED_MISMATCH dokumentálva | PASS | 3. szekció |
| Code boundary audit dokumentálva | PASS | 4. szekció |
| Adapter contract döntés dokumentálva | PASS | 5. szekció (Option A) |
| `JaguaAdapterError` VRS-owned, jagua-mentes | PASS | adapter.rs, no jagua types in public API |
| `JaguaAdapter` struct VRS-owned | PASS | adapter.rs |
| jagua típusok nem szivárognak a publikus modellbe | PASS | imports lokálisak a check_polygon_collision-ben |
| f64→f32 precision kockázat dokumentálva | PASS | API megfigyelések + smoke notes |
| Item-item non-overlap smoke | PASS | jagua_adapter_smoke case 1 |
| Item-item overlap smoke | PASS | jagua_adapter_smoke case 2 |
| Item-sheet boundary smoke | PASS | jagua_adapter_smoke case 3 |
| Meglévő `solve(input)` behavior nem változott | PASS | viselkedésváltozás tábla + JG-03 regression |
| `src/lib.rs` szükségesség dokumentálva | PASS | 5. szekció adapter döntés |
| `cargo build` PASS | PASS | 3.26s |
| `cargo test` 2/2 | PASS | item::tests |
| Adapter smoke ALL PASS | PASS | 4/4 assertion + build |
| JG-03 regression smoke ALL PASS | PASS | 11/11 |
| `./scripts/verify.sh` PASS | PASS | EXIT_CODE=0 |
| Nincs teljes optimizer-loop | PASS | scope guard |
| Nincs sheet elimination / repair / SA | PASS | scope guard |
| Nincs cavity-prepack / hole engedélyezés | PASS | scope guard |

---

## 11) JG04_RESULT

```text
JG04_RESULT
STATUS: PASS
CREATED_OR_UPDATED:
- rust/vrs_solver/src/lib.rs (new — library crate root for smoke binary access)
- rust/vrs_solver/src/main.rs (mod declarations removed, use vrs_solver::{adapter, io})
- rust/vrs_solver/src/adapter.rs (JaguaAdapterError + JaguaAdapter added; solve() unchanged)
- rust/vrs_solver/src/bin/jagua_adapter_smoke.rs (new — 3-case smoke, JSON output)
- scripts/smoke_jagua_adapter_contract.py (new — Python smoke driver)
- canvases/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.md
- codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t04_jagua_adapter_contract_poc.yaml
- codex/prompts/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc/run.md
- codex/codex_checklist/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.md
- codex/reports/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.md
- codex/reports/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.verify.log
ADAPTER_DECISION: adapter.rs internal JaguaAdapter (Option A) — solve() unchanged
API_OBSERVATIONS:
- SPolygon.collides_with(JagPoint): confirmed working
- JagEdge.collides_with(JagEdge): confirmed working
- f64→f32 conversion in to_jag_point(): explicit, documented
- Point containment + edge intersection used for polygon-polygon collision
VERIFY:
- cargo build: PASS (3.26s)
- cargo test: PASS (2/2)
- python3 scripts/smoke_jagua_adapter_contract.py: ALL PASS (4/4)
- python3 scripts/smoke_jagua_optimizer_outer_only_contract.py: ALL PASS (11/11)
- ./scripts/verify.sh: PASS (EXIT_CODE=0)
NEXT:
- JG-05_STATUS: READY
- JG-08_DEPENDENCY_JG04: READY
- Nincs showstopper, nincs blokkoló
```
