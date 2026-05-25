# SGH-Q06 LossModel Contract

## 1. Cél

A `LossModel` réteg egy pluggable collision/loss absztrakciót vezet be a VRS separatorba.
Korábban a `VrsCollisionTracker` hardcoded `bbox_overlap_area(dx*dy)` és bináris `BOUNDARY_LOSS_PROXY`
logikát használt. Q06 után ezek a `LossModelKind` enum mögé kerültek, bővíthető contract-tal.

Modul: `rust/vrs_solver/src/optimizer/loss_model.rs`

## 2. BboxAreaLoss — backward-compatible proxy (default)

A default loss modell. Minden pre-Q06 viselkedést megőriz.

```text
pair_loss(a, b)        = dx * dy  (bbox overlap terület)
boundary_loss(i)       = 0.0, ha boundary_valid; 1.0 különben (bináris proxy)
```

Garantált backward-compatibility:
- `VrsSeparatorConfig::default()` → `loss_model: LossModelKind::BboxArea`
- `VrsCollisionTracker::build(...)` → `BboxArea` model (meglévő call site-ok változatlanul)
- Meglévő tesztek változatlanul zöldek

Quality risk: BboxOnlyProxy — exact rectangular items esetén; irregular shapes esetén felülbecslés.

## 3. PolePenetrationSmoothLoss — Sparrow Algorithm 3 alapú Phase-1 surrogate

Smooth penetration severity modell VRS rectangle/bbox surrogate adatmodellhez igazítva.

### Sparrow Algorithm 3 forrás

Forrás: `.cache/sparrow/src/quantify/overlap_proxy.rs` (ténylegesen auditált)

```rust
fn overlap_area_proxy(sp1: &SPSurrogate, sp2: &SPSurrogate, epsilon: f32) -> f32 {
    for p1 in &sp1.poles {
        for p2 in &sp2.poles {
            let pd = (p1.radius + p2.radius) - p1.center.distance_to(&p2.center);
            let pd_decay = if pd >= epsilon { pd } else { ε² / (-pd + 2ε) };
            total_overlap += pd_decay * min(p1.radius, p2.radius);
        }
    }
    total_overlap * PI
}
```

### VRS bbox surrogate adaptáció

```text
penetration_depth = min(overlap_dx, overlap_dy)    // ha mindkettő > 0
shape_scale       = min(rect_equiv_radius(a), rect_equiv_radius(b))
                    ahol rect_equiv_radius(bbox) = sqrt(w * h / PI)
loss              = smooth_decay(pd, ε) * shape_scale * PI
```

Smooth decay formula:
```text
smooth_decay(pd, ε) = pd              ha pd >= ε
smooth_decay(pd, ε) = ε² / (-pd + 2ε)  ha pd < ε (hyperbolikus kiterjesztés)
```

Epsilon: `SMOOTH_EPSILON = 1.0` (mm-ben)

### Boundary loss (smooth)

```text
viol_depth = max(0, min_x - bbox.x1, bbox.x2 - max_x, ...)
loss = smooth_decay(viol_depth, ε) * rect_equiv_radius(bbox) * PI
```

Fallback: ha a violation_depth = 0 de boundary_valid = false (irregular sheet polygon violation),
proxy = `rect_equiv_radius(bbox) * PI` (konstans, dokumentált korlát).

## 4. Határkezelés és determinizmus

### Determinism contract

```text
same input + same seed + same LossModelKind → bit-identikus output
worker_count=1 backward compatibility: megőrzött
worker_count>1 deterministic worker ordering: megőrzött
```

### GLS weight preservation

`restore_but_keep_weights(snap: LossSnapshot)` csak geometric loss-state-et állít vissza
(bboxes + boundary_valid + boundary_losses). A GLS pair/boundary weights **nem** érintődnek.
Megőrzött mindkét loss modell esetén.

### Precomputed boundary loss

A `boundary_losses: Vec<f64>` a trackerben tárolt, előre kiszámított értékek.
Frissítés: `build_with_model()` és `update_placement()` útján.
Snapshot/restore: `LossSnapshot.boundary_losses` tartalmazza.

## 5. Integráció — módosított útvonalak

| Elem | Változás |
|------|----------|
| `VrsSeparatorConfig.loss_model` | Új mező, default `BboxArea` |
| `VrsCollisionTracker.loss_model_kind` | Belső mező, build-kor beállítva |
| `VrsCollisionTracker.boundary_losses` | Új mező: precomputed boundary loss értékek |
| `VrsCollisionTracker::build()` | Változatlan signature, BboxArea default |
| `VrsCollisionTracker::build_with_model()` | Új: explicit loss_model_kind paraméter |
| `VrsCollisionTracker::pair_loss()` | LossModelKind dispatch |
| `VrsCollisionTracker::boundary_loss()` | boundary_losses[i] visszaadása |
| `VrsCollisionTracker::update_placement()` | boundary_losses[idx] frissítése |
| `VrsCollisionTracker::snapshot_loss()` | boundary_losses snapshot |
| `VrsCollisionTracker::restore_but_keep_weights()` | boundary_losses restore |
| `VrsSeparator::run()` | build_with_model(config.loss_model) |
| `find_best_candidate_for_target()` | loss_model.pair_loss() a ranking-hoz |

## 6. Known limitations

- **Nem CDE backend:** Nincs jagua-rs Collision Detection Engine integráció. Bbox overlap = penetration depth surrogate.
- **Nem exact irregular polygon collision:** Irregular shapes esetén a bbox overapproximates.
- **Nincs continuous rotation:** Csak 0/90/180/270° támogatott.
- **Smooth boundary fallback:** Irregular sheet polygon violation esetén violation_depth = 0 → konstans proxy.
- **Phase-1 surrogate:** Sparrow parity szinten gyengébb jel, mint az exact CDE.

## 7. Remaining gaps

| Gap | Következő task |
|-----|---------------|
| RotationPolicy / continuous rotation | SGH-Q07 |
| CollisionBackend / jagua-rs CDE backend | SGH-Q08 |
| Exact irregular polygon collision | SGH-Q08 |
