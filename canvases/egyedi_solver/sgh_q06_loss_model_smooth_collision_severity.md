# SGH-Q06 — LossModel + smooth collision severity

## Státusz

Implementation task.

Előfeltételként a projektgazda elfogadta az SGH-Q05R2 dokumentációs cleanupot. Ha az aktuális checkoutban a `docs/egyedi_solver/sgh_q05_bpp_phase_loop_contract.md` még tartalmazza a régi `PhaseResult.best_score = min(...)` állítást, azt **ismert, Q05R2 által már kezelt dokumentációs késésnek** kell tekinteni. Ez önmagában nem blokkolhatja Q06-ot. Q06 alatt ne módosíts Q05/Q05R/Q05R2 fájlokat; a Q05R2 csomag kezeli azt a cleanupot.

## Cél

Vezesd be a separator collision/loss réteg moduláris alapját:

```text
LossModel
BboxAreaLoss                 # jelenlegi viselkedés, default, backward-compatible PROXY
PolePenetrationSmoothLoss    # Sparrow Algorithm 3 ihletésű smooth severity foundation, VRS bbox surrogate
```

A Q06 nem teljes jagua-rs CDE backend, nem exact irregular polygon collision és nem continuous rotation. A cél most az, hogy a hardcoded `bbox_overlap_area` / bináris boundary-loss útvonal kikerüljön egy bővíthető `LossModel` szerződés mögé, és legyen egy első smooth severity modell, amelyet később SGH-Q08 CDE/geometry backenddel lehet kiváltani.

## Miért kell?

SGH-Q02–Q05 után a keresési váz erősebb lett: GLS rollback, multi-worker separator, phase orchestration és BPP phase loop. A minőségi hiány továbbra is a loss jel:

```text
separator.rs:
- pair loss: bbox_overlap_area(dx * dy)
- boundary loss: BOUNDARY_LOSS_PROXY = 1.0
```

Ez Phase-1 rectangular esetben használható, de Sparrow-parity szinten gyenge jel. A smooth collision severity célja, hogy a separator és GLS ne csak azt lássa, hogy „ütközik/nem ütközik”, hanem azt is, mennyire mély/problémás az ütközés.

## Forrásfeature

Kötelező source audit:

```text
jagua-rs / Sparrow source, különösen:
- sparrow/src/quantify/overlap_proxy.rs
- sparrow/src/quantify/tracker.rs
- SGH-Q00 F05 — collision severity / penetration / smooth loss
- SGH-Q00 F06 — shape-based penalty
```

Használd a repo meglévő Sparrow resolve mechanizmusát, például:

```bash
./scripts/ensure_sparrow.sh
```

Ha az útvonal eltér, fájlkereséssel azonosítsd a valós source-t. A reportban rögzítsd a ténylegesen olvasott pathokat és függvényeket. Ne README-ből és ne korábbi összefoglalóból dolgozz.

Ha a Sparrow formula vagy source nem ellenőrizhető, a report legyen `REVISE` vagy `BLOCKED`, és ne legyen `SGH-Q07_STATUS: READY` marker.

## Scope

Engedélyezett production fájlok:

```text
rust/vrs_solver/src/optimizer/loss_model.rs   # új modul
rust/vrs_solver/src/optimizer/separator.rs    # tracker + config integráció + célzott tesztek
rust/vrs_solver/src/optimizer/mod.rs          # module export
```

Engedélyezett task artefaktok:

```text
docs/egyedi_solver/sgh_q06_loss_model_contract.md
codex/codex_checklist/egyedi_solver/sgh_q06_loss_model_smooth_collision_severity.md
codex/reports/egyedi_solver/sgh_q06_loss_model_smooth_collision_severity.md
codex/reports/egyedi_solver/sgh_q06_loss_model_smooth_collision_severity.verify.log
```

Tiltott scope:

```text
RotationPolicy / continuous rotation
CollisionBackend / jagua-rs CDE backend
exact irregular polygon collision
DXF/preflight
IO contract
Python runner
frontend/API
SheetElimination/BPP refaktor
PhaseOptimizer refaktor
Q05/Q05R/Q05R2 dokumentáció módosítása
külső benchmark backend
```

## Elvárt architektúra

### 1. Új `loss_model.rs`

Hozz létre külön modult:

```text
rust/vrs_solver/src/optimizer/loss_model.rs
```

Minimum elvárt fogalmak:

```rust
pub trait LossModel {
    fn pair_loss(&self, a: &PlacedBbox, b: &PlacedBbox) -> f64;
    fn boundary_loss(&self, bbox: Option<&PlacedBbox>, sheet: Option<&SheetShape>, boundary_valid: bool) -> f64;
    fn name(&self) -> &'static str;
    fn quality_risk(&self) -> LossQualityRisk;
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LossModelKind {
    BboxArea,
    PolePenetrationSmooth,
}

pub struct BboxAreaLoss;
pub struct PolePenetrationSmoothLoss { ... }
```

A pontos Rust forma igazodhat a meglévő kódhoz. Ha a trait object clone vagy lifetime kezelés túl sok zajt okozna, használj enum-dispatch megoldást. A nyilvános architektúra viszont maradjon moduláris és bővíthető.

### 2. `BboxAreaLoss` backward compatibility

A `BboxAreaLoss` pontosan őrizze meg a Q05/Q05R viselkedést:

```text
pair_loss = bbox overlap area = dx * dy
boundary_loss = 0.0, ha boundary_valid; különben 1.0
```

Ez legyen a `VrsSeparatorConfig` default loss modelje. Q06 után default configgal minden meglévő separator/BPP/phase tesztnek változatlanul zöldnek kell maradnia.

### 3. `PolePenetrationSmoothLoss`

Implementálj Phase-1 rectangle/bbox surrogate smooth modelt a Sparrow Algorithm 3 irányából.

Minimum:

```text
- külön tesztelhető smooth penetration decay helper
- pair loss mélyebb overlapre nagyobb értéket adjon, sekély overlapre kisebbet
- shape/size arányos skálázás legyen, ne flat constant
- boundary loss ne bináris 0/1 legyen, hanem violation depth szerint nőjön
- no-overlap esetén pair_loss = 0.0
- minden surrogate/proxy korlát explicit dokumentálva legyen
```

Elfogadható VRS Phase-1 surrogate:

```text
penetration_depth = min(overlap_x, overlap_y), ha ugyanazon sheeten tényleges bbox overlap van
shape_scale = min(rect_equivalent_radius(a), rect_equivalent_radius(b)) vagy hasonló determinisztikus méretskála
loss = smooth_decay(penetration_depth, epsilon) * shape_scale * PI jellegű formula
```

Boundary esetén a rectangular sheet bounds violation mélységéből számolj smooth loss-t. Irregular sheetnél, ahol most még nincs exact CDE, dokumentált fallback/proxy elfogadható, de ne állíts teljes jagua-rs parityt.

### 4. Separator integráció

Bővítsd a `VrsSeparatorConfig`-ot loss model választással, például:

```rust
pub loss_model: LossModelKind
```

A `VrsCollisionTracker` ne hívjon közvetlenül hardcoded `bbox_overlap_area` / `BOUNDARY_LOSS_PROXY` logikát. Ezek kerüljenek a `BboxAreaLoss` mögé.

Ha smooth boundary loss-hoz kell, a tracker tárolhat computed boundary loss értéket:

```text
boundary_valid: Vec<bool>
boundary_losses: Vec<f64>
```

A következő útvonalakat frissítsd együtt:

```text
VrsCollisionTracker::build
VrsCollisionTracker::update_placement
VrsCollisionTracker::snapshot_loss
VrsCollisionTracker::restore_but_keep_weights
VrsCollisionTracker::total_loss / total_weighted_loss / colliding_indices / weighted_loss_for_item
```

Kötelező megtartani:

```text
same input + same seed + same loss model = deterministic output
worker_count=1 backward compatibility
worker_count>1 deterministic worker ordering
restore_but_keep_weights továbbra is csak geometric loss-state-et restore-ol; GLS weights megmaradnak
```

## Kötelező tesztek

Adj célzott Rust unit/regression teszteket. Minimum bizonyítandó viselkedések:

```text
bbox_area_loss_matches_legacy_overlap_area
bbox_area_loss_preserves_binary_boundary_proxy
smooth_penetration_decay_is_continuous_at_epsilon
smooth_pair_loss_increases_with_overlap_depth
smooth_pair_loss_is_shape_scaled
smooth_boundary_loss_increases_with_violation_depth
separator_default_loss_model_preserves_existing_behavior
separator_can_use_smooth_loss_model
restore_but_keep_weights_preserves_weights_with_loss_model
same_seed_same_loss_model_determinism
```

A pontos tesztnevek igazodhatnak a repo stílusához, de ezek a viselkedések legyenek lefedve.

## Acceptance gate

Futtasd és reportold:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::loss_model
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::separator
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q06_loss_model_smooth_collision_severity.md
```

Kötelező belső összehasonlító smoke ugyanazon kis dense-overlap fixture-n:

```text
BboxAreaLoss:
- initial_loss
- best_loss
- iterations

PolePenetrationSmoothLoss:
- initial_loss
- best_loss
- iterations
```

Ez még nem végső minőségbenchmark. Csak azt bizonyítja, hogy az új modell fut, determinisztikus, és nem rontja el a default útvonalat.

## Dokumentáció

Hozd létre:

```text
docs/egyedi_solver/sgh_q06_loss_model_contract.md
```

Tartalma:

```text
- LossModel célja
- BboxAreaLoss mint backward-compatible proxy
- PolePenetrationSmoothLoss mint Sparrow Algorithm 3 alapú Phase-1 smooth surrogate
- boundary loss kezelés
- determinism contract
- known limitations: no CDE, no exact irregular collision, no continuous rotation
- remaining gaps: RotationPolicy SGH-Q07, CDE/CollisionBackend SGH-Q08
```

## Report elvárás

Hozd létre/frissítsd:

```text
codex/codex_checklist/egyedi_solver/sgh_q06_loss_model_smooth_collision_severity.md
codex/reports/egyedi_solver/sgh_q06_loss_model_smooth_collision_severity.md
codex/reports/egyedi_solver/sgh_q06_loss_model_smooth_collision_severity.verify.log
```

A report tartalmazza:

```text
- dependency evidence: SGH-Q05R PASS + SGH-Q06_STATUS READY + Q05R2 owner-accepted note
- Sparrow source audit evidence: pontos pathok/funkciók
- changed files/functions matrix
- LossModel contract evidence
- DoD -> Evidence matrix path + line hivatkozásokkal
- tests added/fixed
- default no-downgrade evidence
- smooth model limitations
- verify commands and results
```

Report státusz:

```text
PASS: minden DoD és verify zöld, report végén SGH-Q07_STATUS: READY
REVISE/BLOCKED: bármelyik DoD/verify/source-audit fail, SGH-Q07 marker nélkül
```

## Definition of Done

- [ ] Sparrow source audit megtörtént, valós pathokkal dokumentálva.
- [ ] `loss_model.rs` létrejött, moduláris contracttal.
- [ ] `BboxAreaLoss` defaultként megőrzi a Q05/Q05R viselkedést.
- [ ] `PolePenetrationSmoothLoss` futtatható, determinisztikus, tesztelt Phase-1 surrogate.
- [ ] `separator.rs` nem közvetlenül hardcoded loss függvényeket használ a tracker döntési útvonalon.
- [ ] `restore_but_keep_weights` továbbra is GLS weight-preserving.
- [ ] Célzott Rust tesztek zöldek.
- [ ] `cargo test --lib` zöld.
- [ ] `./scripts/verify.sh --report ...` zöld.
- [ ] Report PASS esetén tartalmazza: `SGH-Q07_STATUS: READY`.
