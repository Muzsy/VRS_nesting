# canvases/nesting_engine/nesting_engine_can_place_determinism_hardening.md

> Mentés: `canvases/nesting_engine/nesting_engine_can_place_determinism_hardening.md`  
> TASK_SLUG: `nesting_engine_can_place_determinism_hardening`  
> AREA: `nesting_engine`

# can_place determinism hardening (integer-only feasibility)

## 🎯 Funkció

A `rust/nesting_engine/src/feasibility/narrow.rs::can_place(...)` determinisztika-hardeningje:

- A jelenlegi megvalósítás `i_overlay::float::relate::FloatPredicateOverlay`-t használ (f64), ami:
  - ellentmond a `docs/nesting_engine/tolerance_policy.md` “integer determinisztika” elvnek,
  - elméleti platformfüggő drift-kockázat (floating compare/epsilon/solver heuristics).
- Cél: a feasibility döntés **teljesen integer (i64/i128)** legyen, és a “touching = infeasible” policy determinisztikusan érvényesüljön.

Plusz cél:
- a narrow-phase vizsgálat sorrendje legyen **totális** (ne legyen döntetlen AABB azonos esetén).

Nem cél:
- NFP/IFP/CFR algoritmus módosítás.
- Új tolerancia (TOUCH_TOL) matematikai modell bevezetése (csak determinisztika + integer predicate).

---

## 🧠 Fejlesztési részletek

### 1) Jelenlegi állapot (mi a konkrét gond)
Fájl: `rust/nesting_engine/src/feasibility/narrow.rs`

- `can_place` most:
  - AABB inside check (ok)
  - `FloatPredicateOverlay.within()` a bin containmentre
  - `FloatPredicateOverlay.intersects()` az ütközésre
- A broad-phase (RTree) után a `maybe_overlap` rendezés csak AABB mezőkön történik.
  - Ha két AABB teljesen azonos, a sorrend **nem totális** (tie nincs) → elméletileg drift (későbbi kiterjesztéseknél / debug instrumentációknál).

Felderítés snapshot (2026-02-28):
- `narrow.rs` ténylegesen `FloatPredicateOverlay`-t importál és containment + overlap döntésre használja.
- `scripts/check.sh` `nesting_engine` blokkja épít (`cargo build --release`), de célzott `cargo test ... can_place_` futtatás még nincs bekötve.

### 2) Megoldás: integer-only predicate

#### 2.1 Containment (candidate bin-en belül)
Vezess be integer alapú `poly_strictly_within(candidate, bin) -> bool` logikát:

- Gyors kapu: a meglévő `aabb_inside(bin_aabb, candidate_aabb)` marad.
- Pont-in-polygon (integer, i128):
  - candidate outer minden csúcsa:
    - belül van a bin outerben (Inside),
    - nincs benne bin hole-ban,
    - **nem** lehet boundary-n (touch = infeasible).
- Edge-keresztezés:
  - candidate outer élei nem metszhetik a bin outer/hole éleit,
  - boundary touch is “metszésnek” számít (konzervatív).

Megjegyzés: a pont-in-ring számolás legyen teljesen integer (ray casting cross-multiply), ne használjon f64-et.

#### 2.2 Overlap (candidate vs placed part)
Vezess be integer alapú `polygons_intersect_or_touch(a, b) -> bool` logikát:

- Edge-Edge metszés (outer+holes minden kombináció, touch is true).
- Ha nincs edge metszés:
  - a egyik pontja a b-ben (Inside/OnBoundary) → intersect
  - b egyik pontja a a-ban (Inside/OnBoundary) → intersect

### 3) Determinisztikus narrow-phase vizsgálati sorrend
A jelenlegi `Vec<&PlacedPart>` helyett használd az indexet is:

- `Vec<(usize, &PlacedPart)>` a `query_overlaps()` eredményéből.
- Rendezési kulcs:
  1) min_x, min_y, max_x, max_y
  2) **idx** (tie-break)
Ez totális, determinisztikus.

### 4) Teszt hozzáadások (Rust unit)
A `rust/nesting_engine/src/feasibility/narrow.rs` tesztmodulba:

- `can_place_rejects_touching_bin_boundary()`  
  Candidate pont úgy illesztve, hogy outer éle a bin boundary-n fekszik (touch) → `false`.
- `can_place_is_deterministic_for_identical_aabb_ties()`  
  Két azonos AABB-ú placed part különböző insert sorrendben → az eredmény azonos.
- (Meglévő tesztek maradnak: ok_case, overlap_case, touching_case, stb.)

### 5) Gate integráció
A repo gate jelenleg `scripts/check.sh` alatt buildeli a `nesting_engine`-t, de nem biztos, hogy futtat Rust unit tesztet.

Adj hozzá egy gyors, célzott teszt futtatást a nesting_engine blokkban:

- `cargo test --manifest-path rust/nesting_engine/Cargo.toml can_place_`

Ez:
- lefuttatja a can_place-hoz kötött unit teszteket,
- minimális plusz idővel zárja a regressziót.

---

## 🧪 Tesztállapot

### DoD
- [ ] `rust/nesting_engine/src/feasibility/narrow.rs` többé **nem** importál `FloatPredicateOverlay`-t, és nem használ f64 alapú overlay predicate-et.
- [ ] `can_place` integer-only: containment + overlap predicate determinisztikus (i64/i128).
- [ ] A narrow-phase rendezés totális (AABB + idx tie-break).
- [ ] Új unit tesztek zöldek: `cargo test ... can_place_`
- [ ] `./scripts/check.sh` PASS
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_can_place_determinism_hardening.md` PASS

---

## 🌍 Lokalizáció
Nem releváns.

---

## 📎 Kapcsolódások
- `rust/nesting_engine/src/feasibility/narrow.rs` (can_place + tesztek)
- `rust/nesting_engine/src/feasibility/aabb.rs` (aabb_inside/aabb_overlaps, TOUCH_TOL)
- `rust/nesting_engine/src/geometry/types.rs` (`cross_product_i128`, `Point64`, `Polygon64`)
- `docs/nesting_engine/tolerance_policy.md` (integer determinisztika + touching policy)
- `scripts/check.sh` (gate)
