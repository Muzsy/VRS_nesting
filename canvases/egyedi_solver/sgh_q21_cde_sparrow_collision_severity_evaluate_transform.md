# SGH-Q21 — CDE/Sparrow collision severity + evaluate_transform score

## Státusz

Következő kötelező task SGH-Q20R-R1 után.

Q20R-R1 már bevezette a Sparrow-szerű `search_position()` magot: global/focused sampling, top-k coordinate descent, separator elsődleges bekötés, régi LBF csak fallback. A következő hiány nem újabb sampling/rotation feladat, hanem az értékelő függvény.

Jelenlegi fő rés:

```text
backend mondja meg, hogy collision van-e,
de a collision rosszságát / severity értékét még több helyen bbox/proxy loss adja.
```

Ez nem elég Sparrow-parity irányban. A Sparrow-jellegű separation keresésnek nem csak bináris valid/nem-valid jel kell, hanem olyan severity signal, amely rangsorolni tudja az invalid állapotokat és a candidate transformokat.

## Előfeltétel

Kötelező:

```text
codex/reports/egyedi_solver/sgh_q20r_r1_topk_report_consistency_fix.md
```

Első sor: `PASS`, és legyen benne:

```text
SGH-Q21_STATUS: READY
```

Ha nincs, állj meg `BLOCKED` reporttal, production módosítás nélkül.

## Cél

Implementálj egy explicit, backend-aware Sparrow-style collision severity / evaluate_transform réteget.

A cél nem az, hogy a final validációt javítsd — az Q16 óta megvan. A cél az, hogy a **keresés közbeni score** ne legyen bbox-only proxy, amikor CDE/Jagua backend aktív.

Konkrét célok:

1. Legyen központi `evaluate_transform` / severity API, amelyet a separator és a search_position is használ.
2. Pair collision severity aktív backenddel legyen megerősítve.
3. Boundary violation severity aktív backenddel legyen megerősítve.
4. CDE/Jagua alatt ne legyen silent bbox collision döntés.
5. A bbox loss csak explicit fallback/proxy severity lehet, nem collision source-of-truth.
6. GLS pair/boundary weights már a backend-confirmed severityt súlyozzák.
7. SearchPosition candidate ranking is ezt az új evaluate_transform score-t használja.
8. Diagnosztikából látszódjon, mennyi severity query/probe történt, és volt-e unsupported/fallback.

## Miért nem elég a mostani állapot?

A mostani `search_position.rs` értékelésben CDE/Jagua esetén a collision tényét aktív backend mondja ki, de collision esetén a hozzáadott loss lényegében:

```text
loss_model.pair_loss(other_bbox, candidate_bbox).max(1.0)
```

A `loss_model.rs` maga is dokumentálja, hogy a `PolePenetrationSmooth` még bbox surrogate. Ez jó volt előkészítésnek, de nem végleges Sparrow-logika.

A `separator.rs` tracker is több helyen bbox lossból indul, majd exact backend döntésekkel nulláz vagy unsupportedet jelöl. Ez még nem backend-derived severity.

Q21 feladata ezt a magot kivenni a proxy állapotból.

## Javasolt architektúra

### 1. Új modul

Hozz létre egy új modult, például:

```text
rust/vrs_solver/src/optimizer/collision_severity.rs
```

Javasolt típusok:

```rust
pub struct CollisionSeverityConfig {
    pub enabled_for_exact_backends: bool,
    pub probe_enabled: bool,
    pub probe_initial_step_factor: f64,
    pub probe_min_step: f64,
    pub probe_max_steps: usize,
    pub hard_unsupported_loss: f64,
}

pub struct CollisionSeverityStats {
    pub pair_queries: usize,
    pub boundary_queries: usize,
    pub probe_queries: usize,
    pub backend_confirmed_collisions: usize,
    pub backend_confirmed_no_collisions: usize,
    pub unsupported_queries: usize,
    pub bbox_proxy_severity_uses: usize,
}

pub enum SeverityKind {
    NoCollision,
    Collision { severity: f64 },
    Unsupported,
}
```

A pontos elnevezés igazodhat a repo stílusához, de legyen egy központi API, ne másoljunk újabb bbox-proxy logikát több helyre.

### 2. Pair severity

Kötelező viselkedés:

```text
Bbox backend:
  legacy loss_model pair_loss maradhat.

CDE/Jagua backend:
  placement_overlaps dönti el, van-e collision.
  NoCollision -> severity = 0.
  Unsupported -> hard unsupported, candidate reject vagy hard loss.
  Collision -> backend-confirmed severity számítás.
```

Ha a CDE/Jagua API nem ad közvetlen overlap/depth értéket, implementálj determinisztikus **oracle-probe severity estimate** megoldást:

```text
collision van
→ próbálj kis determinisztikus translation eltolásokat x/y irányban
→ keresd a legkisebb lépést, ahol a backend már NoCollisiont ad
→ ebből számolj smooth/severity értéket
```

Minimum probe irányok:

```text
+x, -x, +y, -y
```

Opcionális:

```text
diagonal directions
rotation probe csak később, ha tiszta
```

Ez nem tökéletes shape penetration, de sokkal közelebb van a Sparrow keresési jeléhez, mert az aktív backend oracle-t használja a severity becsléséhez, nem pusztán bbox overlapet.

Ha performance miatt probe csak kis fixture-ökön / exact backendnél / configgal fut, az elfogadható, de a production CDE path alatt legyen explicit és diagnosztizált.

### 3. Boundary severity

Kötelező viselkedés:

```text
Bbox backend:
  legacy boundary loss maradhat.

CDE/Jagua backend:
  placement_within_sheet dönti el, boundary valid-e.
  NoCollision -> severity = 0.
  Collision -> backend-confirmed boundary violation severity.
  Unsupported -> hard unsupported.
```

Ha nincs közvetlen boundary depth, használj determinisztikus probe-ot vagy bbox-based distance-to-rect-boundary proxyt **csak úgy**, hogy a boundary violation tényét a backend mondta ki.

Irregular sheet esetén ne állíts hamis exact depth-et. Dokumentáld, ha a severity estimate proxy, de a violation existence backend-confirmed.

### 4. `evaluate_transform` API

Hozz létre egy közös transform értékelő függvényt, amelyet a `search_position` és a `VrsCollisionTracker`/separator is használhat.

Javasolt forma:

```rust
pub fn evaluate_transform_loss(
    candidate: &Placement,
    candidate_part: &Part,
    layout: &WorkingLayout,
    target_idx: usize,
    parts: &[Part],
    sheets: &[SheetShape],
    collision_backend: &CollisionBackendKind,
    loss_model: LossModelKind,
    severity_cfg: &CollisionSeverityConfig,
    severity_stats: &mut CollisionSeverityStats,
) -> EvaluationResult
```

Javasolt result:

```rust
pub struct EvaluationResult {
    pub loss: f64,
    pub unsupported: bool,
    pub pair_collision_count: usize,
    pub boundary_collision: bool,
}
```

A pontos formát igazítsd a repohoz. A lényeg, hogy a `search_position` ne saját `eval_with_backend_trait` lokális logikából éljen, hanem ebből a központi értékelőből.

### 5. SearchPosition bekötés

A `rust/vrs_solver/src/optimizer/search_position.rs` jelenlegi lokális eval helperjeit csökkentsd vagy szüntesd meg:

```text
eval_with_backend_trait
eval_candidate_loss
```

A candidate ranking a közös `evaluate_transform` score-t használja.

Kötelező:

```text
unsupported sample -> reject/f64::MAX
NoCollision -> 0 vagy compactness/tie-break score, ha van
Collision -> backend-confirmed severity score
CDE/Jagua -> no silent bbox collision source
```

### 6. Separator / GLS bekötés

A `VrsCollisionTracker` jelenleg páronként és boundarynként lossokat tart fenn. Ezeket úgy kell frissíteni, hogy CDE/Jagua backend esetén a loss már a közös severity engineből jöjjön.

Kötelező:

```text
pair_loss(i,j) CDE/Jagua alatt backend-confirmed severityt adjon;
boundary_loss(i) CDE/Jagua alatt backend-confirmed severityt adjon;
update_weights() már ezt súlyozza;
colliding_indices() is ezt használja;
weighted_loss_for_item() is ezt használja.
```

A régi exact no-collision override továbbra is hasznos, de ne maradjon úgy, hogy collision esetén csak bbox loss áll be source-of-truthként.

### 7. Diagnostics

Vezess fel minimális diagnosztikát az optimizer/adapter outputig.

Javasolt mezők:

```text
collision_severity_backend
collision_severity_pair_queries
collision_severity_boundary_queries
collision_severity_probe_queries
collision_severity_backend_confirmed_collisions
collision_severity_backend_confirmed_no_collisions
collision_severity_unsupported_queries
collision_severity_bbox_proxy_uses
collision_severity_enabled
```

A pontos nevek igazodhatnak a meglévő `optimizer_diagnostics` stílushoz.

A reportból derüljön ki:

```text
CDE/Jagua alatt futott-e severity engine;
hány query/probe történt;
maradt-e bbox proxy;
ha maradt, pontosan hol és miért;
unsupported hogyan lett kezelve.
```

## Explicit non-goals

Ne csináld most:

```text
Q19 LV8 acceptance benchmark gate
Q18B CDE session/cache rewrite
Q22 exploration/compression shrink-loop redesign
full exact overlap-area computation, ha a backend API nem adja
main solver hole-aware collision
DXF/preflight refaktor
multi-sheet objective redesign
```

## Fontos korlát

A Q21 elsődleges célja nem az, hogy matematikailag tökéletes exact penetration depth legyen minden alakra. A cél az, hogy a keresés score-ja **backend-confirmed collision structure** alapján működjön, ne bbox-only proxy alapján.

Ha nincs elérhető exact depth API, a probe-based severity estimate elfogadható, de:

```text
- aktív backend collision/no-collision oracle-t használjon;
- determinisztikus legyen;
- diagnosztizált legyen;
- ne legyen csendes bbox fallback;
- legyen tesztelve shallow vs deep collision monotonicity legalább egyszerű fixture-ön.
```

## Kötelező tesztek

Minimum tesztek:

```text
collision_severity_bbox_backend_preserves_legacy_pair_loss
collision_severity_exact_backend_no_collision_zeroes_bbox_false_positive
collision_severity_exact_backend_collision_returns_positive_severity
collision_severity_shallow_vs_deep_collision_is_monotonic
collision_severity_boundary_valid_is_zero
collision_severity_boundary_violation_positive
collision_severity_unsupported_returns_hard_loss_or_reject
search_position_uses_collision_severity_engine
separator_tracker_uses_backend_confirmed_pair_severity
separator_tracker_weight_update_uses_backend_severity
cde_path_reports_no_bbox_collision_source_of_truth
q20r_search_position_smoke_still_passes
```

A tesztnevek eltérhetnek, de a reportban mapeld őket ezekre.

## Smoke

Készíts vagy bővíts célzott smoke-ot:

```text
scripts/smoke_sgh_q21_collision_severity.py
```

Minimum fixture-ök:

1. Two rectangles shallow overlap vs deep overlap — deep severity nagyobb.
2. Bbox false-positive / exact no-collision fixture — CDE/Jagua no collision severity 0.
3. Boundary violation fixture — boundary severity pozitív.
4. SearchPosition fixture — candidate ranking severity alapján javít.
5. CDE path — `bbox_fallback_queries == 0`, severity diagnostics jelen van.

Ez nem LV8 benchmark.

## Verify

Minimum parancsok:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::collision_severity
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::search_position
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::separator
cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q20r_sparrow_search_position.py
python3 scripts/smoke_sgh_q21_collision_severity.py
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q21_cde_sparrow_collision_severity_evaluate_transform.md
```

Ha valamelyik nem fut, ne adj hamis PASS-t.

## Report

Hozd létre:

```text
codex/reports/egyedi_solver/sgh_q21_cde_sparrow_collision_severity_evaluate_transform.md
codex/reports/egyedi_solver/sgh_q21_cde_sparrow_collision_severity_evaluate_transform.verify.log
```

Első sor csak ez lehet:

```text
PASS
REVISE
BLOCKED
```

PASS report tartalmazza:

```text
- dependency gate eredmény;
- pontos módosított fájlok;
- új severity API összefoglaló;
- hogyan lett kiváltva a search_position lokális bbox-eval;
- hogyan használja a separator/GLS a backend-confirmed severityt;
- probe strategy, ha van;
- CDE/Jagua no silent bbox fallback bizonyíték;
- diagnostics mezők listája;
- tesztparancsok és eredmények;
- fennmaradó ismert limitationök.
```

PASS végén kötelező markerek:

```text
SGH-Q21_STATUS: READY_FOR_AUDIT
SGH-Q22_STATUS: READY|HOLD
Q19_STATUS: HOLD
Q18B_RECOMMENDATION: REQUIRED|NOT_REQUIRED_NOW|INCONCLUSIVE_NEEDS_BIGGER_FIXTURE
```

Q19 maradjon HOLD. A real LV8 quality gate csak akkor jöjjön, ha a Sparrow-style search_position és a backend-confirmed severity már együtt fut.
