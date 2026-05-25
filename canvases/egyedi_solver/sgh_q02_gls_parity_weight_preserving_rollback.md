# SGH-Q02 — GLS parity + weight-preserving rollback

## Kontextus

SGH-Q00 kimondta, hogy a VRS SGH-01..SGH-05 vonal hasznos szerkezeti váz, de több minőségkritikus jagua-rs/Sparrow funkció csak `PARTIAL / PROXY / MISSING` szinten van jelen.

SGH-Q01 lezárta a korrekciós migrációs tervet, annotálta a jelöletlen proxy kódhelyeket, és explicit sorrendet adott:

```text
SGH-Q02 → GLS parity + weight-preserving rollback
SGH-Q03 → multi-worker / move_items_multi
SGH-Q04 → exploration/compression orchestration
...
```

Ez a task az első valódi korrekciós implementációs lépés. Nem új keresési réteget nyit, hanem a meglévő `VrsSeparator` tanulási/rollback alapját javítja Sparrow-parity irányba.

## Task cél

Implementáld a `rust/vrs_solver/src/optimizer/separator.rs` fájlban:

```text
1. Sparrow Algorithm 8 szerinti multiplicative GLS weight update;
2. max_loss normalizációt;
3. collision/no-collision decay viselkedést;
4. VrsCollisionTracker loss-state snapshotot;
5. restore_but_keep_weights() rollback helper-t;
6. unit teszteket és SGH-Q02 contract dokumentációt.
```

A cél: F07 és F08 parity státusz javítása.

```text
F07 GLS dynamic weights: PARTIAL → PARTIAL+ vagy FULL(rectangular Phase 1)
F08 separator incumbent/restore/strike: PARTIAL → PARTIAL+ vagy FULL(rectangular Phase 1)
```

## Kötelező dependency gate

SGH-Q02 csak akkor indulhat, ha:

```text
codex/reports/egyedi_solver/sgh_q01_sparrow_quality_migration_correction_plan.md
```

létezik, első sora `PASS` vagy `PASS_WITH_NOTES`, és tartalmazza:

```text
SGH-Q02_STATUS: READY
```

Ha bármely feltétel hiányzik, állj meg `BLOCKED` státusszal, és csak ezeket frissítsd:

```text
codex/reports/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback.md
codex/codex_checklist/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback.md
```

## Kötelező repo anchorok

Olvasd el és auditáld, ne feltételezd:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
docs/egyedi_solver/sgh_q00_sparrow_jagua_quality_feature_parity_audit.md
docs/egyedi_solver/sgh_q00_quality_feature_gap_matrix.md
docs/egyedi_solver/sgh_q00_modular_architecture_principles.md
docs/egyedi_solver/sgh_q01_sparrow_quality_migration_correction_plan.md
docs/egyedi_solver/sgh_q01_corrected_task_roadmap.md
docs/egyedi_solver/sgh_q01_no_downgrade_acceptance_gates.md
codex/reports/egyedi_solver/sgh_q01_sparrow_quality_migration_correction_plan.md
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/working.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/candidates.rs
rust/vrs_solver/src/optimizer/boundary.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/io.rs
```

## Sparrow/jagua-rs source evidence

Az SGH-Q00 report alapján kötelezően használandó referencia:

```text
sparrow/quantify/tracker.rs update_weights() — Algorithm 8
```

A formula lényege:

```text
max_loss = max(pair/container loss)
if loss == 0:
    multiplier = GLS_WEIGHT_DECAY
else:
    multiplier = GLS_WEIGHT_MIN_INC_RATIO + (GLS_WEIGHT_MAX_INC_RATIO - GLS_WEIGHT_MIN_INC_RATIO) * (loss / max_loss)
weight = max(1.0, min(weight * multiplier, weight_max))
```

A pontos konstansokat és elnevezéseket a repo-ban meglévő SGH-Q00/Q01 doksikból és/vagy az auditált Sparrow forrásból igazold. Ha a külső source nem elérhető, az SGH-Q00-ban rögzített képletet használd, és a reportban jelöld a source státuszát.

## Kötelező implementáció

### 1. Backward-compatible config

A `VrsSeparatorConfig` publikus API-ját ne törd el.

Elvárás:

```text
- meglévő mezőket ne törölj;
- ha új GLS mezők kellenek, add hozzá defaulttal;
- régi tesztek változatlanul zöldek maradjanak;
- a reportban írd le, mely config mező mit jelent SGH-Q02 után.
```

Javasolt új/értelmezett mezők, ha a kód alapján indokolt:

```rust
pub gls_weight_decay: f64,      // no-collision multiplier, 0.0 < decay <= 1.0
pub gls_weight_max: f64,        // hard cap
pub gls_min_inc_ratio: f64,     // collision min multiplier
pub gls_max_inc_ratio: f64,     // collision max multiplier
```

A pontos nevek eltérhetnek, de a működés legyen egyértelmű és tesztelt.

### 2. Multiplicative GLS update

Cseréld a jelenlegi additive proxy-t:

```rust
*w = (*w + 1.0 / (1.0 + *w * decay)).min(weight_max)
```

Sparrow-jellegű multiplicative update-re:

```text
- minden boundary collision entry és pair collision entry vesz részt a max_loss számításban;
- loss > 0 esetén loss/max_loss alapján nő a weight;
- loss == 0 esetén a már létező weight decay-eljen vissza 1.0 irányba;
- weight soha nem mehet 1.0 alá;
- weight nem lépheti túl a config weight_max értékét;
- pair weight csak akkor jöjjön létre, ha collision van vagy már létezett.
```

Fontos: rectangular Phase 1-ben a loss továbbra is AABB area proxy, de az update stratégia már ne legyen additive proxy. Az SGH-Q01 `QUALITY_RISK: AdditiveGlsProxy` annotációt frissítsd úgy, hogy ne hazudjon a kód állapotáról.

### 3. Loss-state snapshot + weight-preserving restore

Adj a `VrsCollisionTracker`-hez rollback-safe snapshotot.

Minimum elvárás:

```rust
struct VrsCollisionTrackerSnapshot { ... } // pontos név szabad

impl VrsCollisionTracker {
    fn snapshot_loss_state(&self) -> VrsCollisionTrackerSnapshot;
    fn restore_but_keep_weights(&mut self, snapshot: &VrsCollisionTrackerSnapshot);
}
```

A snapshotnak a loss állapotot kell visszaállítania:

```text
bboxes
boundary_valid
minden olyan mező, amelyből pair_loss/boundary_loss számolódik
```

De nem állíthatja vissza:

```text
pair_weights
boundary_weights
```

### 4. Separator rollback használat

A `VrsSeparator::run()` belső rollback pontjain használd az új helper-t, ahol ez indokolt.

Elvárás:

```text
- sikertelen tentative move után current layout visszaáll;
- tracker loss-state visszaáll;
- tanult GLS weights megmaradnak;
- update_weights() sikertelen próbálkozás után is a megmaradt súlyokon dolgozik;
- best_layout továbbra is valid snapshotként tér vissza.
```

Ne nyisd meg még:

```text
multi-worker
shuffle/random order
exploration/compression
solution pool
continuous rotation
CollisionBackend / CDE
LossModel smooth severity
```

## Kötelező tesztek

A `separator.rs` test moduljában vagy a repo meglévő mintájához illeszkedő helyen adj hozzá/frissíts teszteket.

Minimum:

```text
1. MultiplicativeGls collision: nagyobb loss nagyobb vagy egyenlő weight növekedést kap.
2. MultiplicativeGls max_loss normalizáció: max loss item/pair ratio-ja 1.0-ként viselkedik.
3. No-collision decay: létező weight loss==0 mellett 1.0 irányba csökken, de nem megy 1.0 alá.
4. Boundary weight update: boundary collision is ugyanazzal a formulával frissül.
5. restore_but_keep_weights: loss-state visszaáll, de pair_weights és boundary_weights megmaradnak.
6. Separator convergence regression: egyszerű overlapping fixture továbbra is best_loss == 0.0.
7. Determinism regression: azonos input + azonos config → bit-identical output/diagnostics.
8. Parity non-regression: meglévő separator tesztek zöldek.
```

## Kötelező contract dokumentáció

Hozd létre:

```text
docs/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback_contract.md
```

Kötelező szekciók:

```text
# SGH-Q02 GLS parity + weight-preserving rollback contract
## Decision
## Source Sparrow feature mapping
## VRS implementation summary
## GLS formula
## Config semantics
## Collision/boundary weight handling
## restore_but_keep_weights contract
## Rollback invariants
## Tests and acceptance gates
## Remaining quality gaps after SGH-Q02
## Next task: SGH-Q03
```

## Kötelező report tartalom

A report tartalmazza:

```text
- dependency evidence;
- source evidence: SGH-Q00/Q01 és, ha elérhető, Sparrow source;
- current-state audit: additive GLS + missing restore_but_keep_weights;
- change summary;
- config semantics;
- tests run + results;
- DoD → Evidence Matrix fájl/funkció hivatkozásokkal;
- parity status update F07/F08-ra;
- no-downgrade gates G01–G08 teljesülése;
- explicit scope safety: nincs multi-worker, nincs phase orchestration, nincs CDE, nincs rotation policy;
- végén: SGH-Q03_STATUS: READY.
```

## Kötelező kimenetek

```text
rust/vrs_solver/src/optimizer/separator.rs
docs/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback_contract.md
codex/codex_checklist/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback.md
codex/reports/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback.md
codex/reports/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback.verify.log
```

## Verify

Futtasd legalább:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml separator
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback.md
```

Ha bármelyik fail, a report első sora nem lehet PASS.

## PASS feltételek

PASS csak akkor adható, ha:

```text
- SGH-Q01 dependency gate zöld;
- additive GLS formula ténylegesen lecserélve;
- max_loss normalizáció tesztelve;
- no-collision decay tesztelve;
- restore_but_keep_weights implementálva és tesztelve;
- meglévő separator konvergencia és determinism tesztek zöldek;
- cargo test és verify.sh zöld;
- nincs allowed scope-on kívüli production módosítás;
- report végén szerepel: SGH-Q03_STATUS: READY.
```
