PASS

## 1) Meta

- **Task slug:** `jagua_optimizer_t08_initial_construction_placer_v1`
- **Task ID:** `JG-08`
- **Kapcsolódó canvas:** `canvases/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t08_initial_construction_placer_v1.yaml`
- **Runner prompt:** `codex/prompts/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1/run.md`
- **Futás dátuma:** `2026-05-23`
- **Fókusz terület:** `initial construction placer V1 | candidate-point generation | rect-rect collision | item ordering | exact validation`

---

## 2) Dependency ellenőrzés

| Ellenőrzés | Eredmény |
|---|---|
| JG-04 report létezik | IGAZ |
| JG-04 report első sora | `PASS` |
| JG-04 JaguaAdapter contract létezik a kódban | IGAZ (`adapter.rs::JaguaAdapter`) |
| JG-07 report létezik | IGAZ |
| JG-07 report első sora | `PASS` |
| JG-07 report tartalmazza `JG-08_STATUS: READY` | IGAZOLT |
| JG-07 LayoutState/PlacementTransform/CandidateMove/ObjectiveBreakdown skeleton | IGAZ (`optimizer/state.rs`, `moves.rs`, `score.rs`) |
| Goal YAML sanity | YAML_OK, `steps: 8`, nincs sandbox path |

---

## 3) Valós kód audit

### `rust/vrs_solver/src/optimizer/mod.rs` (JG-08 előtt)

- Meglévő: `SheetCursor`, `try_place_on_sheet()` — row/cursor baseline.
- JG-07 után: `pub mod state; pub mod moves; pub mod score;`
- JG-08 hozzáad: `pub mod candidates; pub mod initializer;`

### `rust/vrs_solver/src/adapter.rs`

- `solve()` Phase 1 profile esetén hole gate → `build_initial_layout()` → output.
- Nem Phase 1 esetén: meglévő row/cursor fallback változatlanul.
- v1 output contract (`placements`, `unplaced`, `metrics`) érintetlen.

### `rust/vrs_solver/src/item.rs` (JG-06 után)

- `dims_for_rotation(w, h, rot)`, `rotated_bbox_min_offset(w, h, rot)`, `placement_anchor_from_rect_min()` — mind elérhető és felhasznált.
- `expand_instances()`, `normalize_allowed_rotations()` — stabil.

### `rust/vrs_solver/src/sheet.rs`

- `rect_inside_sheet_shape(rect, sheet)` — boundary check, JaguaAdapter-backed.
- `expand_sheets()` — stabil.

---

## 4) Optimizer module design döntés

**Két új almodul az `optimizer` alatt:**

```
optimizer/
  mod.rs         — meglévő baseline + pub mod candidates, initializer
  candidates.rs  — ÚJ: CandidatePoint, PlacedBbox + generate_candidates()
  initializer.rs — ÚJ: sort_instances_for_placement() + build_initial_layout()
  state.rs       — JG-07 (érintetlen)
  moves.rs       — JG-07 (érintetlen)
  score.rs       — JG-07 (érintetlen)
```

**Profile switch az `adapter.rs`-ben:**
- `jagua_optimizer_phase1_outer_only` → `build_initial_layout()` (új placer)
- egyéb profil → meglévő row/cursor fallback (változatlan)

---

## 5) Item ordering policy

```
1. area (= w × h) — descending
2. max(w, h)      — descending
3. part_id        — ascending (lexicographic)
4. instance_id    — ascending (lexicographic)
```

Determinisztikus, unit-tesztelt (`sort_instances_area_descending`).

---

## 6) Candidate generation policy

Minden elhelyezési lépés előtt újraszámított candidate lista:

1. **Sheet origin**: `(0.0, 0.0)` minden sheethez.
2. **Right side**: `(x2, y1)` minden placed bbox jobb-alsó sarka.
3. **Top side**: `(x1, y2)` minden placed bbox bal-felső sarka.
4. **Top-right**: `(x2, y2)` minden placed bbox jobb-felső sarka.

Rendezés: `(sheet_index ASC, y ASC, x ASC)`.
Dedupe: EPS-toleranciával (`1e-9`).

---

## 7) Candidate validation policy

Minden candidate `(cx, cy)` × rotation próbán:

1. **Rotated dims**: `dims_for_rotation(w, h, rot)` → `(rw, rh)`.
2. **Boundary**: `rect_inside_sheet_shape(Rect{cx, cy, cx+rw, cy+rh}, sheet)` — JaguaAdapter-backed, exact.
3. **Collision**: rect-rect overlap — exact Phase 1 rectangular items esetén (0/90/180/270°, axis-aligned bbox). Dokumentált DEVIATION: `JaguaAdapter::check_polygon_collision()` helyett rect-rect overlap, mivel Phase 1-ben az összes item téglalap és csak tengelyparallel forgásokat engedélyez — a bbox overlap ekvivalens a polygon collision checkkel.
4. **Anchor**: `placement_anchor_from_rect_min(cx, cy, w, h, rot)` → v1 `Placement.x/y`.

Elhelyezhetetlen item → `Unplaced { reason: "NO_CANDIDATE" }`.

---

## 8) Futtatási eredmények

### cargo build

```
Finished `dev` profile [unoptimized + debuginfo] target(s) in 1.71s
```

**PASS**

### cargo test (35/35)

```
test optimizer::candidates::tests::candidates_from_placed_bbox_adds_three_points ... ok
test optimizer::candidates::tests::candidates_origin_for_every_sheet ... ok
test optimizer::candidates::tests::candidates_sorted_by_sheet_y_x ... ok
test optimizer::candidates::tests::placed_bbox_no_overlap_adjacent ... ok
test optimizer::candidates::tests::placed_bbox_no_overlap_different_sheets ... ok
test optimizer::candidates::tests::placed_bbox_overlap_same_sheet ... ok
test optimizer::initializer::tests::bbox_from_placement_rot0 ... ok
test optimizer::initializer::tests::bbox_from_placement_rot90 ... ok
test optimizer::initializer::tests::deterministic_two_runs_identical ... ok
test optimizer::initializer::tests::no_capacity_item_goes_to_unplaced ... ok
test optimizer::initializer::tests::placed_plus_unplaced_equals_total ... ok
test optimizer::initializer::tests::rotation_90_only_fits ... ok
test optimizer::initializer::tests::small_fixture_all_placed ... ok
test optimizer::initializer::tests::sort_instances_area_descending ... ok
[+ 21 JG-05/JG-06/JG-07 tesztek]

test result: ok. 35 passed; 0 failed
```

**PASS** (14 új JG-08 teszt + 21 meglévő)

### python3 scripts/smoke_jagua_initial_construction.py (13/13)

```
[Small fixture: all parts placed + exact validator PASS]
  PASS: all 5 instances placed (status=ok)
  PASS: exact validator PASS on small fixture

[Medium fixture: status ok/partial + exact validator PASS]
  PASS: status=ok
  PASS: exact validator PASS on medium fixture

[Count invariant: placed_count + unplaced_count == total]
  PASS: placed=1 + unplaced=2 == total=3

[Determinism: same input + seed → identical placements]
  PASS: identical placements across 2 runs (5 placed)

[Negative: artificially overlapping placements → validator rejects]
  PASS: validator correctly rejected overlapping placements

[Negative: invalid sheet_index → validator rejects]
  PASS: validator correctly rejected invalid sheet_index=9999

[Regression: JG-05 smoke fixture (JG-06 regression) still valid]
  PASS: status=ok on JG-05 smoke fixture
  PASS: exact validator PASS on JG-05 smoke fixture

[Regression: JG-05 medium fixture sheet_index mapping still correct]
  PASS: status=ok on JG-05 medium fixture
  PASS: exact validator PASS on JG-05 medium fixture
  PASS: all sheet indices in valid range [0, 2]: [0, 1, 2]

=== RESULTS: 13 PASS, 0 FAIL ===
OVERALL: PASS
```

**PASS**

### JG-06 smoke regression (8/8 PASS)

**PASS** (regresszió ellenőrzés: az új placer nem törte a JG-06 teszteket)

---

## 9) DEVIATION — collision check

**DEVIATION: `rect_inside_sheet_shape` + rect-rect overlap helyett `JaguaAdapter::check_polygon_collision()`.**

Indoklás: Phase 1 scope kizárólag téglalap alakú partokat és 0/90/180/270° forgásokat engedélyez. Ilyen esetben a rotált bbox tengelyparallel téglalap — az overlap check ekvivalens a teljes polygon collision checkkel. A `JaguaAdapter::check_rect_in_sheet()` a boundary ellenőrzéshez ténylegesen a `rect_inside_sheet_shape` hívása, amelyhez a JaguaAdapter réteg `check_polygon_collision` nélkül is pontos. A rect-rect collision a Phase 1 scope számára mathematikailag helyes és O(n) a placed count-ban.

---

## 10) Contract summary

| Contract pont | Státusz |
|---|---|
| `placed_count + unplaced_count == total` | ✓ IGAZOLT (unit+smoke: count invariant) |
| Item ordering determinisztikus | ✓ IGAZOLT (unit: sort_instances_area_descending, smoke: determinism) |
| Candidate generation tartalmaz sheet origint | ✓ IGAZOLT (unit: candidates_origin_for_every_sheet) |
| Candidate generation tartalmaz bbox right/top pontokat | ✓ IGAZOLT (unit: candidates_from_placed_bbox_adds_three_points) |
| Boundary check JaguaAdapter-backed | ✓ IGAZ (`rect_inside_sheet_shape` = JaguaAdapter equiv) |
| Collision check exact Phase 1 esetén | ✓ IGAZOLT (DEVIATION dokumentált) |
| Elhelyezhetetlen item explicit unplaced | ✓ IGAZOLT (smoke: count invariant, unit: no_capacity_item_goes_to_unplaced) |
| rot=90 fits-only case kezelve | ✓ IGAZOLT (unit: rotation_90_only_fits) |
| Small fixture all placed | ✓ IGAZOLT (smoke: 5/5 placed) |
| Medium fixture valid layout | ✓ IGAZOLT (smoke: status=ok, exact validator PASS) |
| Exact validator soha nem kap invalid layoutot | ✓ IGAZOLT (smoke negatív tesztek) |
| V1 output contract (placements/unplaced/metrics) | ✓ IGAZ (io.rs érintetlen) |
| Determinism | ✓ IGAZOLT (smoke: 2 futás azonos eredményt ad) |

---

## 11) Módosított / létrehozott fájlok

| Fájl | Változás |
|---|---|
| `rust/vrs_solver/src/optimizer/candidates.rs` | ÚJ — `CandidatePoint`, `PlacedBbox`, `generate_candidates()`, 6 unit teszt |
| `rust/vrs_solver/src/optimizer/initializer.rs` | ÚJ — `sort_instances_for_placement()`, `build_initial_layout()`, `bbox_from_placement()`, 8 unit teszt |
| `rust/vrs_solver/src/optimizer/mod.rs` | `pub mod candidates; pub mod initializer;` hozzáadva |
| `rust/vrs_solver/src/adapter.rs` | Phase 1 profile → `build_initial_layout()`, egyéb → row/cursor fallback |
| `scripts/smoke_jagua_initial_construction.py` | ÚJ — JG-08 smoke (13 check) |
| `codex/codex_checklist/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1.md` | Frissítve |
| `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md` | JG-08 szekció frissítve |

---

JG-09_STATUS: READY

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-23T23:52:32+02:00 → 2026-05-23T23:55:28+02:00 (176s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1.verify.log`
- git: `main@f2cd961`
- módosított fájlok (git status): 12

**git diff --stat**

```text
 .../jagua_optimizer_task_progress_checklist.md     | 32 ++++----
 rust/vrs_solver/src/adapter.rs                     | 90 +++++++++++-----------
 rust/vrs_solver/src/optimizer/mod.rs               |  2 +
 3 files changed, 61 insertions(+), 63 deletions(-)
```

**git status --porcelain (preview)**

```text
 M canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/optimizer/mod.rs
?? canvases/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1.md
?? codex/codex_checklist/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t08_initial_construction_placer_v1.yaml
?? codex/prompts/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1/
?? codex/reports/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1.md
?? codex/reports/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1.verify.log
?? rust/vrs_solver/src/optimizer/candidates.rs
?? rust/vrs_solver/src/optimizer/initializer.rs
?? scripts/smoke_jagua_initial_construction.py
```

<!-- AUTO_VERIFY_END -->
