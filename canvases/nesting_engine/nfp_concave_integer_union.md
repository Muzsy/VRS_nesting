# canvases/nesting_engine/nfp_concave_integer_union.md

> **Mentés helye a repóban:** `canvases/nesting_engine/nfp_concave_integer_union.md`
> **TASK_SLUG:** `nfp_concave_integer_union`
> **Terület (AREA):** `nesting_engine`

---

# F2-2 Hardening — Konkáv NFP stabil alap: integer-only union (float tiltás)

## 🎯 Funkció

Az F2-2 konkáv NFP “stabil alap” útvonalának **float-mentesítése**:

- **Tilos**: `FloatOverlay`, `f64`-re konvertált union a concave stable baseline-ban
- **Kötelező**: **integer-only boolean union** (Point64 / i64 / i128 predikátumok), determinisztikus kimenettel

Cél: a konkáv baseline tényleg “golyóálló” legyen, és ne hozza vissza a lebegőpontos nem-determinizmust.

Nem cél:
- orbitális exact fejlesztése (külön task)
- holes támogatás (külön task)
- `scripts/*` módosítása
- `rust/vrs_solver/**` módosítása

---

## 🧠 Fejlesztési részletek

### Kötelező olvasmány / szabályok (prioritás)

1. `AGENTS.md`
2. `docs/codex/overview.md`
3. `docs/codex/yaml_schema.md`
4. `docs/codex/report_standard.md`
5. `docs/nesting_engine/tolerance_policy.md`
6. `docs/known_issues/nesting_engine_known_issues.md` (KI-007)
7. `rust/nesting_engine/src/nfp/concave.rs` (union_nfp_fragments jelenleg FloatOverlay)
8. `rust/nesting_engine/src/nfp/boundary_clean.rs`
9. `rust/nesting_engine/src/nfp/convex.rs` (F2-1 Minkowski)
10. `rust/nesting_engine/tests/nfp_regression.rs`

Ha bármelyik hiányzik: STOP, pontos fájlútvonallal jelezni.

---

### Probléma (jelenlegi állapot)

`rust/nesting_engine/src/nfp/concave.rs` → `union_nfp_fragments()`:

- `Point64(i64)` → `f64` konverzió
- `i_overlay::float::overlay::FloatOverlay` union
- vissza: `round()` → i64

Ez ellentmond:
- a Truth Layer fixpontos céljának
- a Phase 2 “boss fight” determinisztika elvárásának
- a saját auditban jelzett KI-007 driftnek

### Felderítés (konkrét bizonyítékok)

- Drift helye (pre-change): `rust/nesting_engine/src/nfp/concave.rs` import blokkjában:
  - `i_overlay::float::overlay::FloatOverlay`
  - `i_overlay::core::{fill_rule::FillRule, overlay_rule::OverlayRule}`
- Drift helye (pre-change): `union_nfp_fragments()`:
  - `Point64 -> [f64; 2]` konverzió a subject shape-ek építésénél
  - `FloatOverlay::with_subj(...).overlay(OverlayRule::Subject, FillRule::NonZero)`
  - `round()` visszaalakítás i64-re
- Integer-only API elérhetőség (`i_overlay = 4.4.0`):
  - `i_overlay::core::overlay::Overlay`
  - `Overlay::with_shapes_options(...).overlay(OverlayRule::Union, FillRule::NonZero)`
  - integer pont/shape típusok: `i_overlay::i_float::int::point::IntPoint`, `i_overlay::i_shape::int::shape::{IntContour, IntShape}`
  - Megjegyzés: az integer overlay API `i32` koordinátákat vár, ezért a `Point64(i64)` bemenethez determinisztikus leképezés szükséges.

---

### Követelmények (nem alkuképes)

1) **Concave stable baseline-ban nincs FloatOverlay**  
   - Sem direkt import, sem indirekt wrapper.

2) **Union integer koordinátákon történik**
   - Point64/i64 bemenet
   - orientáció/cross predikátumok: i128

3) **Determinista canonical output**
   - `boundary_clean` kötelező a union után
   - fix ring start + CCW + collinear merge

4) **Teszt bizonyíték**
   - legyen legalább 1 teszt, ami kifejezetten védi:
     - concave.rs-ben nincs FloatOverlay használat
     - concave fixture-ek továbbra is PASS

---

### Megoldási stratégia

#### A) Elsődleges: i_overlay integer overlay (ha elérhető)
Felderítés: az `i_overlay = 4.4.0` tartalmaz-e integer/mesh alapú boolean union API-t, ami nem `float::*`.

- Ha van: építsünk egy `union_polygons_i64()` helper-t, ami `Vec<Polygon64>`-ból union-t ad vissza.

#### B) Fallback (ha i_overlay-ben nincs használható integer union)
Akkor külön, dedikált integer boolean útvonal:
- saját integer sweep / plane subdivision minimal implementáció NFP-fragment unionra **nem** cél (túl nagy)
- helyette: olyan, repo-ban már használt/engedett integer boolean megoldás, ami nem f64-ön dönt (ha nincs: a task FAIL és új stratégia szükséges, ezt reportban ki kell mondani)

Megjegyzés: offset modulban van f64, de ez a task kifejezetten a **concave baseline union** float driftjét szünteti meg.

---

### Érintett fájlok

**Módosul:**
- `rust/nesting_engine/src/nfp/concave.rs` (FloatOverlay union eltávolítás, integer union bevezetés)
- `docs/known_issues/nesting_engine_known_issues.md` (KI-007 státusz: IN_PROGRESS (nfp_concave_integer_union), majd részleges RESOLVED scope megjegyzéssel)
- `rust/nesting_engine/tests/nfp_regression.rs` (ha szükséges csak minimális módosítás)

**Új (csak ha szükséges az integer unionhoz):**
- `rust/nesting_engine/src/geometry/overlay_int.rs` (integer union helper; csak akkor, ha tényleg kell)

**Új teszt (kötelező):**
- `rust/nesting_engine/tests/nfp_no_float_overlay.rs` (forrás-szintű guard: concave.rs nem tartalmaz FloatOverlay/float::overlay importot)

---

## 🧪 Tesztállapot

### DoD

- [ ] `rust/nesting_engine/src/nfp/concave.rs` nem használ `i_overlay::float::*` uniont (FloatOverlay tiltás)
- [ ] concave fixture regressziók PASS (`rust/nesting_engine/tests/nfp_regression.rs`)
- [ ] `boundary_clean` továbbra is garantálja a canonical, nem-önmetsző outputot
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_concave_integer_union.md` PASS

### Evidence

- `codex/reports/nesting_engine/nfp_concave_integer_union.md` AUTO_VERIFY blokk + log

---

## 🌍 Lokalizáció

Nem releváns.

---

## 📎 Kapcsolódások

- F2-2: `canvases/nesting_engine/nfp_computation_concave.md`
- Backlog: `canvases/nesting_engine/nesting_engine_backlog.md`
- Drift registry: `docs/known_issues/nesting_engine_known_issues.md` (KI-007)
- Kód: `rust/nesting_engine/src/nfp/concave.rs`, `rust/nesting_engine/src/nfp/boundary_clean.rs`
