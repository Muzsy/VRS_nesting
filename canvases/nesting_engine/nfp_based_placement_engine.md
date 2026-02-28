# canvases/nesting_engine/nfp_based_placement_engine.md

> **Mentés helye a repóban:** `canvases/nesting_engine/nfp_based_placement_engine.md`
> **TASK_SLUG:** `nfp_based_placement_engine`
> **Terület (AREA):** `nesting_engine`

---

# F2-3 — NFP-alapú Placement Engine (Rect-bin): IFP/CFR + NFP placer

## 🎯 Funkció

A BLF (rácsos) baseline placer kiváltása **NFP/IFP/CFR** alapú, determinisztikus placerrel **rect bin** esetén, a normatív specifikáció szerint:

- Normatív spec: `docs/nesting_engine/f2_3_nfp_placer_spec.md`
- Bemenet: v2 IO contract (backward kompatibilis)
- Placer választás: `--placer blf|nfp` (bootstrap taskban már bekötve)
- Hybrid gating (holes/hole_collapsed → BLF) (bootstrap + hole_collapsed task után már aktív)

Ebben a taskban a **valódi** NFP placer kerül implementálásra:

- `IFP` (Inner Fit Polygon) — rect bin transzlációs téglalap
- `CFR = IFP \ union(NFP_i)` — MultiPolygon + kanonizálás + determinisztikus rendezés
- Candidate selection: CFR-vertex + nudge + first-feasible (min(y,x)) + totális tie-break
- NFP cache: seed-mentes `shape_id` + hard cap “clear all”, multi-sheet scope

## 🧠 Fejlesztési részletek

### Előfeltételek (már megvannak a repóban)
- `docs/nesting_engine/f2_3_nfp_placer_spec.md` már **bin_offset** kánonnal szinkronban
- `nest --placer blf|nfp` + hybrid gating + noholes smoke már bekötve
- HOLE_COLLAPSED: nesting geó outer-only (holes=[]), export megőrzés

### Érintett fájlok (YAML outputs, kizárólag ezek módosíthatók)

- `canvases/nesting_engine/nfp_based_placement_engine.md`
- `rust/nesting_engine/src/nfp/ifp.rs`
- `rust/nesting_engine/src/nfp/cfr.rs`
- `rust/nesting_engine/src/nfp/cache.rs`
- `rust/nesting_engine/src/nfp/mod.rs`
- `rust/nesting_engine/src/placement/nfp_placer.rs`
- `rust/nesting_engine/src/placement/mod.rs`
- `rust/nesting_engine/src/multi_bin/greedy.rs`
- `poc/nesting_engine/f2_3_f0_sanity_noholes_v2.json`
- `poc/nesting_engine/f2_3_f1_wrapper_contract_noholes_v2.json`
- `poc/nesting_engine/f2_3_f2_touching_stress_noholes_v2.json`
- `poc/nesting_engine/f2_3_f3_rotation_coverage_noholes_v2.json`
- `scripts/check.sh`
- `codex/codex_checklist/nesting_engine/nfp_based_placement_engine.md`
- `codex/reports/nesting_engine/nfp_based_placement_engine.md`
- `codex/reports/nesting_engine/nfp_based_placement_engine.verify.log`

### Kánon (specből – nem változtatjuk)
- `spacing_effective = sheet.spacing_mm || sheet.kerf_mm (legacy spacing source)`
- `inflate_delta = spacing_effective/2`
- `bin_offset = inflate_delta - margin`
- Bin a `nest` útvonalban már B_adj-ként készül (rect_bin_bounds)

### NFP placer algoritmus (single-sheet)
1) **Part ordering** determinisztikusan:
   - primary: `nominal_bbox_area` csökkenő
   - tie-break: `part_id` növekvő
   - instance: 0..quantity-1 (mint BLF)

2) **Rotation ordering**:
   - `allowed_rotations_deg` -> `unique + sort` növekvő

3) Minden instance-ra:
   - minden rotációra:
     - moving polygon: rotate + normalize (min_x=min_y=0)
     - IFP rect a bin (B_adj) és a moving AABB alapján
     - NFP-k compute a már placed partokhoz képest (cache-elve)
     - CFR: `IFP \ union(NFPs)` -> MultiPolygon
     - CFR canonicalize + sort (spec 10)
     - candidates: CFR outer vertexek (cap 512/comp) + nudge (s=1,2,4 µm; 8 irány) + IFP prefilter
     - candidates totális sort (spec 11.3), dedupe (determinista), cap 4096
     - első `can_place == true` nyer → place + state update

4) Wrapper szerződés:
   - ha egy part nem fér, nem állunk le → megyünk tovább a következőre
   - `0 placed` csak ha tényleg senki nem fér

### CFR boolean implementáció
- i_overlay boolean:
  - `U = union(NFP_i)` (regularized, FillRule::NonZero)
  - `CFR = difference(IFP, U)` (regularized)
- decode: `Vec<IntContour>` -> Polygon64 (outer + holes)
- tisztítás:
  - dupe/collinear cleanup determinisztikusan
  - 0-területű komponens drop
  - canonicalize ringek: orientáció + lex-min start
  - komponens totális sort (spec 10.3)

### NFP cache (spec 14)
- `shape_id` = seed-mentes u64 (sha256 első 8 byte, canonicalized pontlistákból)
- key = (shape_id_a, shape_id_b, rotation_steps_b=i16)
- scope: multi-sheet (greedy wrapperen át éljen)
- cap: `MAX_ENTRIES` felett determinisztikus `clear_all()`

### Fixture-ek + gate
A spec minimum F0–F3 fixture készletet kér. Ezeket **hole-mentes** v2 JSON-ként hozzuk létre:

- F0: sanity (biztosan felmegy)
- F1: wrapper contract (első nagy nem fér, későbbi kicsi igen)
- F2: touching stress (nudge futása lefedve; cél: ne maradjon 0 placed)
- F3: rotation coverage (csak 90°-kal fér fel)

`scripts/check.sh` nesting_engine blokkját bővítjük:
- NFP determinism: 3 futás ugyanazon fixture-re -> determinism_hash egyezik
- Functional: F1-ben placed>=1
- Rotation: F3-ban a part rotation_deg == 90
- “No worse than BLF” basic: F0 esetén placed_count(nfp) >= placed_count(blf)

## 🧪 Tesztállapot

### DoD
- [ ] `nfp/ifp.rs` implementálva + unit tesztek (spec 6.1, 6.2; normalizált part policy: spec 4.1).
- [ ] `nfp/cfr.rs` implementálva (union + difference + canonicalize + sort) + unit tesztek (spec 9.1, 10.1, 10.2, 10.3).
- [ ] `nfp/cache.rs` bővítve: seed-mentes `shape_id()` + `MAX_ENTRIES` cap + clear_all determinisztikusan (spec 2, 14.6).
- [ ] `placement/nfp_placer.rs` stub kiváltva: deterministic ordering + CFR-vertex candidates + nudge + first-feasible + wrapper contract (spec 2, 7.2, 8.1, 11.1, 11.3, 3.4).
- [ ] multi-sheet cache scope: greedy wrapper cache-t tart, nfp_place kapja meg mutable ref-ként (spec 3.3, 14 cache scope).
- [ ] új F0–F3 v2 fixture-ek létrehozva (noholes, spacing_mm explicit; spec 16.1 minimum fixture set).
- [ ] `scripts/check.sh` bővítve F0–F3 + determinism(3x) + functional + rotation + no-worse-than-BLF checkekkel (spec 2 és DoD gate policy).
- [ ] Gate PASS:
  `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_based_placement_engine.md`

## 🌍 Lokalizáció
Nem releváns.

## 📎 Kapcsolódások
- Normatív spec: `docs/nesting_engine/f2_3_nfp_placer_spec.md`
- Backlog: `canvases/nesting_engine/nesting_engine_backlog.md` (F2-3)
- Bootstrap: `canvases/nesting_engine/nesting_engine_f2_3_bootstrap_placer_flag_gating.md`
- HOLE_COLLAPSED policy: `canvases/nesting_engine/nesting_engine_hole_collapsed_solid_policy.md`
- Spacing/margin kánon: `canvases/nesting_engine/nesting_engine_spacing_margin_bin_offset_model.md`
- Kód:
  - `rust/nesting_engine/src/placement/nfp_placer.rs`
  - `rust/nesting_engine/src/nfp/convex.rs`, `rust/nesting_engine/src/nfp/concave.rs`
  - `rust/nesting_engine/src/feasibility/narrow.rs` (can_place)
  - `rust/nesting_engine/src/multi_bin/greedy.rs`
  - `scripts/check.sh`
  - `poc/nesting_engine/*.json`
