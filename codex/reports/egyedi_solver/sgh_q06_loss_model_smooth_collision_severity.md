PASS

# Report — SGH-Q06 `sgh_q06_loss_model_smooth_collision_severity`

## Status

PASS — Moduláris `LossModel` réteg bevezetve. `BboxAreaLoss` defaultként megőrzi a Q05/Q05R viselkedést. `PolePenetrationSmoothLoss` futtatható, determinisztikus, tesztelt Phase-1 surrogate. Minden pre-Q06 teszt (181) zöld. Új SGH-Q06 tesztek (11): mind zöld. `cargo test --lib`: 192/192 PASS.

## Meta

- **Task slug:** `sgh_q06_loss_model_smooth_collision_severity`
- **Kapcsolódó canvas:** `canvases/egyedi_solver/sgh_q06_loss_model_smooth_collision_severity.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q06_loss_model_smooth_collision_severity.yaml`
- **Futás dátuma:** 2026-05-25
- **Branch / commit:** `main`
- **Fókusz terület:** `rust/vrs_solver/src/optimizer/loss_model.rs`, `separator.rs`, `mod.rs`

---

## Dependency evidence

| Gate | Státusz | Bizonyíték |
|------|---------|------------|
| SGH-Q05R report első sor PASS | PASS | `codex/reports/egyedi_solver/sgh_q05r_bpp_phase_diagnostics_score_semantics_fix.md` sor 1: PASS |
| SGH-Q06_STATUS: READY marker | PASS | `codex/reports/egyedi_solver/sgh_q05r_bpp_phase_diagnostics_score_semantics_fix.md`: `SGH-Q06_STATUS: READY` |
| SGH-Q05R2 elfogadott | PASS | `codex/reports/egyedi_solver/sgh_q05r2_bpp_contract_score_semantics_cleanup.md` sor 1: PASS, projektgazdai override: elfogadva |
| Q05/Q05R/Q05R2 nem módosítva | PASS | Nincs érintett fájl |

---

## Sparrow source audit evidence

Ténylegesen olvasott fájlok:

| Fájl | Függvény / struct | Auditált tartalom |
|------|-------------------|-------------------|
| `.cache/sparrow/src/quantify/overlap_proxy.rs` | `overlap_area_proxy(sp1, sp2, epsilon)` | Sparrow Algorithm 3: pd = (r1+r2) - dist, smooth decay, total * PI |
| `.cache/sparrow/src/quantify/tracker.rs` | `CollisionTracker`, `restore_but_keep_weights` | jagua-rs CDE backend; GLS weight preservation contract azonos a VRS-ével |

**Sparrow Algorithm 3 formula (auditált):**
```rust
let pd = (p1.radius + p2.radius) - p1.center.distance_to(&p2.center);
let pd_decay = if pd >= epsilon { pd } else { epsilon.powi(2) / (-pd + 2.0 * epsilon) };
total_overlap += pd_decay * f32::min(p1.radius, p2.radius);
total_overlap *= PI;
```

**VRS bbox surrogate adaptáció (loss_model.rs):**
```rust
let pd = dx.min(dy);  // min(overlap_x, overlap_y) as penetration depth
let pd_decay = smooth_decay(pd, SMOOTH_EPSILON);
let ra = rect_equiv_radius(a);  // sqrt(w*h/PI)
pd_decay * ra.min(rb) * PI
```

---

## Changed files / functions matrix

| Fájl | Változás típusa | Érintett függvények/struktúrák |
|------|-----------------|-------------------------------|
| `rust/vrs_solver/src/optimizer/loss_model.rs` | ÚJ | `LossQualityRisk`, `LossModelKind`, `smooth_decay`, `pair_loss`, `compute_boundary_loss`, `name`, `quality_risk` |
| `rust/vrs_solver/src/optimizer/mod.rs` | MÓDOSÍTOTT | `pub mod loss_model` export hozzáadva |
| `rust/vrs_solver/src/optimizer/separator.rs` | MÓDOSÍTOTT | `VrsCollisionTracker`, `LossSnapshot`, `VrsSeparatorConfig`, `build`, `build_with_model`, `pair_loss`, `boundary_loss`, `update_placement`, `restore_item`, `snapshot_loss`, `restore_but_keep_weights`, `find_best_candidate_for_target`, `run` |

---

## LossModel contract evidence

| Contract pont | Státusz | Bizonyíték |
|---------------|---------|------------|
| `LossModelKind` enum: BboxArea + PolePenetrationSmooth | PASS | `loss_model.rs:28-36` |
| BboxArea.pair_loss = dx*dy | PASS | `loss_model.rs:73-74`, teszt: `bbox_area_loss_matches_legacy_overlap_area` |
| BboxArea.boundary_loss = 0/1 | PASS | `loss_model.rs:84`, teszt: `bbox_area_loss_preserves_binary_boundary_proxy` |
| smooth_decay folytonos epsilon-nál | PASS | `loss_model.rs:58-63`, teszt: `smooth_penetration_decay_is_continuous_at_epsilon` |
| smooth pair loss nő overlap mélységgel | PASS | teszt: `smooth_pair_loss_increases_with_overlap_depth` |
| smooth pair loss shape-scaled | PASS | teszt: `smooth_pair_loss_is_shape_scaled` |
| smooth boundary loss nő violation depth-el | PASS | teszt: `smooth_boundary_loss_increases_with_violation_depth` |
| Default config = BboxArea | PASS | `separator.rs:VrsSeparatorConfig::default()`, `loss_model: LossModelKind::BboxArea` |
| build() backward compat | PASS | `separator.rs:VrsCollisionTracker::build()` → `build_with_model(..., BboxArea)` |
| restore_but_keep_weights GLS-preserving | PASS | `separator.rs:restore_but_keep_weights`, teszt: `restore_but_keep_weights_preserves_weights_with_loss_model` |
| Determinizmus | PASS | teszt: `same_seed_same_loss_model_determinism` |

---

## DoD → Evidence matrix

| DoD pont | Státusz | Bizonyíték |
|----------|---------|------------|
| Sparrow source audit megtörtént, valós pathokkal | PASS | `.cache/sparrow/src/quantify/overlap_proxy.rs` + `tracker.rs` olvasva |
| `loss_model.rs` létrejött, moduláris contracttal | PASS | `rust/vrs_solver/src/optimizer/loss_model.rs` |
| `BboxAreaLoss` defaultként megőrzi Q05/Q05R viselkedést | PASS | `separator_fixes_simple_overlap`: initial_loss=900 ✓ |
| `PolePenetrationSmoothLoss` futtatható, determinisztikus, tesztelt | PASS | `separator_can_use_smooth_loss_model` + `same_seed_same_loss_model_determinism` |
| `separator.rs` nem hardcoded loss a tracker döntési útvonalon | PASS | `pair_loss()` → LossModelKind dispatch; `find_best_candidate_for_target()` → loss_model.pair_loss() |
| `restore_but_keep_weights` GLS weight-preserving | PASS | `restore_but_keep_weights_preserves_weights_with_loss_model` (BboxArea + Smooth) |
| Célzott Rust tesztek zöldek | PASS | 11/11 új + 181/181 meglévő |
| `cargo test --lib` zöld | PASS | 192/192 |
| `./scripts/verify.sh --report ...` zöld | PASS | AUTO_VERIFY szekció |

---

## Tests added / fixed

### Új tesztek — `loss_model.rs` (6 db)

| Teszt | Viselkedés |
|-------|-----------|
| `bbox_area_loss_matches_legacy_overlap_area` | BboxAreaLoss.pair_loss = dx*dy |
| `bbox_area_loss_preserves_binary_boundary_proxy` | BboxAreaLoss.boundary_loss = 0/1 |
| `smooth_penetration_decay_is_continuous_at_epsilon` | smooth_decay folytonos epsilon-nál |
| `smooth_pair_loss_increases_with_overlap_depth` | mélyebb overlap → nagyobb smooth loss |
| `smooth_pair_loss_is_shape_scaled` | nagyobb item → nagyobb loss ugyanannyi pd-nél |
| `smooth_boundary_loss_increases_with_violation_depth` | nagyobb violation → nagyobb boundary loss |

### Új tesztek — `separator.rs` (5 db)

| Teszt | Viselkedés |
|-------|-----------|
| `separator_default_loss_model_preserves_existing_behavior` | default = BboxArea, initial_loss=900 |
| `separator_can_use_smooth_loss_model` | smooth model fut, konvergál, violation-free |
| `restore_but_keep_weights_preserves_weights_with_loss_model` | GLS weights megőrzése mindkét modellnél |
| `same_seed_same_loss_model_determinism` | bit-identikus output BboxArea + Smooth esetén |
| `smoke_bbox_vs_smooth_loss_model_on_dense_fixture` | mindkét model finite, non-negative, overlap detected |

### Meglévő tesztek — változatlanul zöld (181 db)

Összes pre-Q06 teszt (separator: 22, working, score, boundary, stb.) változatlanul PASS.

---

## Default no-downgrade evidence

```text
VrsSeparatorConfig::default() → loss_model: LossModelKind::BboxArea

separator_fixes_simple_overlap:
  diag.initial_loss == 900.0  ✓  (30*30 = 900, BboxAreaLoss dx*dy)
  diag.best_loss == 0.0       ✓
  diag.converged == true      ✓

tracker_valid_layout_total_loss_zero: PASS ✓
tracker_overlap_gives_positive_pair_loss: PASS ✓
tracker_boundary_violation_gives_positive_boundary_loss: PASS ✓
```

---

## Smooth model limitations

```text
- Nem CDE backend: jagua-rs Collision Detection Engine nincs bevezetve.
  bbox overlap → penetration depth surrogate, nem exact shape collision.
- Nem exact irregular polygon: bbox overapproximates irregular shape boundaries.
- Nincs continuous rotation: csak 0/90/180/270° támogatott.
- Smooth boundary fallback: irregular sheet polygon violation esetén (viol=0 de boundary_valid=false)
  konstans proxy = rect_equiv_radius * PI (nem depth-arányos).
- Phase-1 surrogate jelleg: Sparrow parity szinten gyengébb, mint az exact CDE.
```

---

## Smoke comparison — BboxAreaLoss vs PolePenetrationSmoothLoss (dense_fixture_21)

`smoke_bbox_vs_smooth_loss_model_on_dense_fixture` teszt eredménye (seed=42, max_strikes=30, iters=200):

```text
BboxAreaLoss:          initial_loss > 0 (bbox dx*dy scale), best_loss >= 0, finite ✓
PolePenetrationSmooth: initial_loss > 0 (smooth pd*r*PI scale), best_loss >= 0, finite ✓
```

Megjegyzés: a két modell eltérő abszolút loss értéket produkál (különböző skála). Az összehasonlítás
igazolja, hogy mindkét modell detektálja az átfedéseket és futtatható determinisztikusan ugyanazon
fixture-n.

---

## Verify commands and results

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::loss_model
# Result: 6/6 PASS

cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::separator
# Result: 28/28 PASS

cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
# Result: 192/192 PASS

./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q06_loss_model_smooth_collision_severity.md
# Result: lásd AUTO_VERIFY szekció
```

---

SGH-Q07_STATUS: READY

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-25T17:36:57+02:00 → 2026-05-25T17:40:00+02:00 (183s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q06_loss_model_smooth_collision_severity.verify.log`
- git: `main@75fe4dc`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 rust/vrs_solver/src/optimizer/mod.rs       |   1 +
 rust/vrs_solver/src/optimizer/separator.rs | 299 ++++++++++++++++++++++++++---
 2 files changed, 273 insertions(+), 27 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/optimizer/mod.rs
 M rust/vrs_solver/src/optimizer/separator.rs
?? canvases/egyedi_solver/sgh_q06_loss_model_smooth_collision_severity.md
?? codex/codex_checklist/egyedi_solver/sgh_q06_loss_model_smooth_collision_severity.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q06_loss_model_smooth_collision_severity.yaml
?? codex/prompts/egyedi_solver/sgh_q06_loss_model_smooth_collision_severity/
?? codex/reports/egyedi_solver/sgh_q06_loss_model_smooth_collision_severity.md
?? codex/reports/egyedi_solver/sgh_q06_loss_model_smooth_collision_severity.verify.log
?? docs/egyedi_solver/sgh_q06_loss_model_contract.md
?? rust/vrs_solver/src/optimizer/loss_model.rs
```

<!-- AUTO_VERIFY_END -->
