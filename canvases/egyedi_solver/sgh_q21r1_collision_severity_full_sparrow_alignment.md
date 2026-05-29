# SGH-Q21R1 — Full Sparrow-aligned collision severity / evaluate_transform hardening

## Státusz

Korrekciós task az SGH-Q21 után.

Ez nem minimális javítócsomag. A cél nem az, hogy a Q21 „éppen zöld” legyen, hanem hogy a `collision_severity` / `evaluate_transform` útvonal a teljes jagua_rs/Sparrow irányhoz igazodjon: a geometriát az aktív CDE/Jagua backend mondja meg, a keresési jel backend-oracle alapú, a GLS/search_position/separator ugyanazt az értékelési magot használja, a diagnosztika nem hazudik, és a default paraméterek ipari sheet méreteken sem adnak lapos/használhatatlan jelet.

## Miért nem elég a minimális Q21 javítás?

A Q21 bevezetett egy központi `collision_severity.rs` modult, és ez jó irány. Viszont a jelenlegi állapot még nem fogadható el teljes Sparrow-alapnak, mert:

```text
- a report markerek hiányosak;
- a tracker útvonal alulszámolja a pair/boundary backend query-ket;
- az oracle-probe Unsupported ág nincs statolva;
- a default initial step nagy sheeteken túl durva;
- a severity cardinal-only probe, tehát kevés irányt próbál;
- nincs adaptív bracketing + binary refinement;
- hard_unsupported_loss config létezik, de több helyen f64::MAX maradt;
- a report erősebbnek állítja a megoldást, mint amit a kód ténylegesen tud.
```

A javításnál tilos a „jó lesz ez most minimumként” gondolkodás. Ha valamelyik teljes követelmény nem készül el, a report legyen `REVISE`, ne `PASS`.

## Cél

A Q21R1 célja:

```text
Full Sparrow-aligned collision severity v1.1
```

Ez azt jelenti:

1. Az aktív backend legyen a collision/boundary source-of-truth CDE/Jagua esetén.
2. A severity ne sima bbox proxy legyen, hanem backend-oracle alapú feloldási távolság.
3. A probe többirányú legyen, ne csak +x/-x/+y/-y.
4. A probe adaptív legyen: bracket keresés + binary refinement.
5. A default step ne legyen ipari sheeten használhatatlanul durva.
6. A tracker és search_position ugyanazt a szemantikát használja.
7. A query/probe/unsupported statisztika teljes legyen, ne részleges.
8. Unsupported esetek a configolt hard loss-t használják.
9. A report és checklist ne állítson többet, mint amit a kód bizonyít.
10. A következő Q22 már erre a valós severity jelre építhessen.

## Nem cél

Ne csináld most:

```text
Q22 exploration/compression shrink-loop rewrite
Q23 fixed-sheet/BPP adapter redesign
Q19 LV8 benchmark gate
Q18B CDE session/cache rewrite
main solver hole-aware collision
full CDE engine API fork vagy jagua-rs upstream módosítás
```

Viszont a Q21R1 scope-on belül nem engedhető meg félmegoldás. Ha a többirányú adaptív probe vagy a statisztika nem készül el, nincs PASS.

## Kötelező pre-audit

Olvasd el:

```text
codex/reports/egyedi_solver/sgh_q21_cde_sparrow_collision_severity_evaluate_transform.md
codex/reports/egyedi_solver/sgh_q21_cde_sparrow_collision_severity_evaluate_transform.verify.log
codex/codex_checklist/egyedi_solver/sgh_q21_cde_sparrow_collision_severity_evaluate_transform.md
canvases/egyedi_solver/sgh_q21_cde_sparrow_collision_severity_evaluate_transform.md
rust/vrs_solver/src/optimizer/collision_severity.rs
rust/vrs_solver/src/optimizer/search_position.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/phase.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/adapter.rs
scripts/smoke_sgh_q21_collision_severity.py
```

Futtasd és reportold:

```bash
rg -n "f64::MAX|hard_unsupported_loss|probe_initial_step_factor|probe_max|oracle_probe|placement_overlaps|placement_within_sheet|pair_queries|boundary_queries|unsupported_queries|bbox_proxy|CollisionSeverityConfig|CollisionSeverityStats" rust/vrs_solver/src/optimizer rust/vrs_solver/src/io.rs rust/vrs_solver/src/adapter.rs scripts codex/reports/egyedi_solver/sgh_q21*
```

A reportban külön válaszold meg:

```text
- Hol volt hard-coded f64::MAX unsupported loss?
- Hol futott backend query stat növelés nélkül?
- Hol volt cardinal-only probe?
- Mi volt a sheet_diag * 0.05 probléma 1500×3000 sheeten?
- Mit változtattál azért, hogy Q21R1 már ne minimális, hanem Sparrow-aligned severity legyen?
```

## Implementációs követelmények

### 1. CollisionSeverityConfig teljesítmény- és minőségorientált bővítése

Bővítsd a configot legalább ezekkel:

```rust
pub probe_max_initial_step_mm: f64,
pub probe_bracket_growth: f64,
pub probe_binary_refine_steps: usize,
pub probe_tolerance_mm: f64,
pub probe_use_diagonal_directions: bool,
pub probe_use_center_direction: bool,
pub probe_use_pair_center_direction: bool,
```

Default irányelv:

```text
probe_initial_step = min(sheet_diag * probe_initial_step_factor, probe_max_initial_step_mm)
probe_initial_step = max(probe_initial_step, probe_min_step)
probe_max_initial_step_mm legyen ipari sheeten is értelmes, például 5–10 mm nagyságrend.
probe_min_step legyen kicsi, például 0.01–0.1 mm.
probe_binary_refine_steps legyen legalább 6–10, vagy tolerance alapján megálló.
```

A pontos defaultot a repo numerikus toleranciáihoz igazítsd, de indokold a reportban.

### 2. Többirányú probe directions

A pair severity ne csak cardinal irányokat próbáljon:

```text
(+x, -x, +y, -y)
```

Kötelező:

```text
cardinal directions
+ diagonals, ha probe_use_diagonal_directions
+ pair-center away direction, ha probe_use_pair_center_direction
```

A pair-center away direction a candidate középpontjától az ütköző másik placement középpontjától elfelé mutasson, normalizálva. Ha degenerált, skip.

Boundary severity esetén kötelező:

```text
cardinal directions
+ diagonals
+ sheet-center direction, ha probe_use_center_direction
```

Sheet-center direction: candidate középpontját a sheet közepe felé mozgató irány. Irregular sheet esetén is használható proxy irányként, de a validálást továbbra is backend végzi.

Deduplikáld a közel azonos irányokat stabil toleranciával.

### 3. Bracket + binary refinement oracle-probe

Cseréld le az egyszerű exponenciális step visszatérést valódi adaptív probe-ra.

Elvárt algoritmus minden directionre:

```text
start = capped_initial_step
last_colliding = 0
first_clear = None
for step in geometric_growth(start, growth, max_steps):
    query backend
    if Collision: last_colliding = step; continue
    if NoCollision: first_clear = step; break
    if Unsupported: count unsupported; mark direction unsupported; stop direction
if first_clear exists:
    binary search between last_colliding and first_clear
    return refined_clear_distance
else:
    return no_resolution_for_this_direction
severity = min(refined_clear_distance over resolved directions)
```

Ha nincs feloldó irány:

```text
return cfg.hard_unsupported_loss vagy egy explicit capped unresolved severity,
```

de ne `f64::MAX` hardcode legyen. A reportban indokold, melyik policy lett választva.

### 4. Unsupported accounting teljes körű javítása

Minden backend `Unsupported` növelje:

```text
unsupported_queries
```

Ez vonatkozik:

```text
evaluate_transform_loss boundary query
evaluate_transform_loss pair query
pair probe query
boundary probe query
VrsCollisionTracker::compute_backend_decisions
VrsCollisionTracker::update_backend_decisions_for_item
```

Ne legyen olyan `Unsupported { .. } => break` ág, amely nem statol.

### 5. Query accounting teljes körű javítása

Minden olyan helyen, ahol CDE/Jagua severity célból backend query fut, növekedjen:

```text
pair_queries vagy boundary_queries
```

Vonatkozik legalább:

```text
evaluate_transform_loss
compute_backend_decisions
update_backend_decisions_for_item
probe subqueries
```

A `probe_queries` maradjon külön mező, de a probe közbeni pair/boundary query is legyen elszámolva a pair/boundary query countban, vagy dokumentáltan legyen külön `probe_pair_queries` / `probe_boundary_queries` mező. A választott szemantika legyen egyértelmű és tesztelt.

Javasolt bővítés:

```rust
pub probe_pair_queries: usize,
pub probe_boundary_queries: usize,
```

Ha ezt bevezeted, az outputban is jelenjen meg.

### 6. hard_unsupported_loss tényleges használata

A Q21R1 után a severity engine-ben ne maradjon olyan unsupported path, amely közvetlenül `f64::MAX`-ot ad vissza, ha van configolt `hard_unsupported_loss`.

Elvárt:

```text
loss = cfg.hard_unsupported_loss
unsupported = true
```

A `f64::MAX` csak olyan belső sentinel lehet, amely nem kerül ki scoring loss-ként, és a reportban indokolni kell. Jobb megoldás: ne használd loss-ként.

### 7. Bbox proxy policy szigorítása

CDE/Jagua backend esetén:

```text
bbox nem lehet collision existence source-of-truth;
bbox nem lehet default severity source, ha oracle-probe engedélyezett;
bbox_proxy_severity_uses csak akkor nőhet, ha probe_enabled=false vagy explicit fallback policy aktív;
bbox false-positive ne kapjon collision severityt backend NoCollision mellett.
```

Adj célzott tesztet bbox false-positive esetre.

### 8. Shared evaluate_transform contract

A `search_position`, a `separator` tracker és későbbi Q22 Sparrow loop ugyanazt a contractot tudja használni.

A reportban dokumentáld az új szemantikát:

```text
EvaluationResult.loss
EvaluationResult.unsupported
EvaluationResult.pair_collision_count
EvaluationResult.boundary_collision
CollisionSeverityStats fields
```

Ha szükséges, bővítsd az `EvaluationResult`-ot:

```rust
pub backend_confirmed_collision: bool,
pub unresolved_probe: bool,
pub severity_mode: CollisionSeverityMode,
```

Ne vidd túlzásba, de a későbbi SparrowState/Q22 számára legyen tiszta API.

### 9. Diagnostics output bővítése

Tartsd meg a meglévő mezőket:

```text
collision_severity_pair_queries
collision_severity_boundary_queries
collision_severity_probe_queries
collision_severity_backend_confirmed_collisions
collision_severity_backend_confirmed_no_collisions
collision_severity_unsupported_queries
collision_severity_bbox_proxy_uses
```

Adj hozzá, ha implementáltad:

```text
collision_severity_probe_pair_queries
collision_severity_probe_boundary_queries
collision_severity_probe_resolved
collision_severity_probe_unresolved
collision_severity_probe_unsupported
collision_severity_min_resolution_mm
collision_severity_max_resolution_mm
collision_severity_avg_resolution_mm
```

A pontos nevek igazodhatnak a repo stílusához, de a lényeg: a probe minősége és költsége látható legyen.

### 10. Report marker fix

PASS report végén kötelező:

```text
SGH-Q21R1_STATUS: READY_FOR_AUDIT
SGH-Q21_STATUS: READY_FOR_AUDIT
SGH-Q22_STATUS: READY
Q19_STATUS: HOLD
Q18B_RECOMMENDATION: REQUIRED|NOT_REQUIRED_NOW|INCONCLUSIVE_NEEDS_BIGGER_FIXTURE
```

`SGH-Q22_STATUS: READY` csak akkor megengedett, ha a severity engine teljes Q21R1 acceptance szerint működik. Ha nem, `HOLD`.

## Kötelező tesztek

Adj vagy frissíts célzott teszteket legalább ezekre:

```text
severity_initial_step_is_capped_on_large_sheet
severity_pair_probe_uses_diagonal_and_pair_center_directions
severity_boundary_probe_uses_diagonal_and_sheet_center_directions
severity_probe_binary_refines_resolution_distance
severity_probe_unsupported_increments_unsupported_queries
severity_tracker_counts_pair_and_boundary_queries
severity_tracker_update_counts_pair_and_boundary_queries
severity_hard_unsupported_loss_used_instead_of_f64_max
severity_bbox_false_positive_exact_backend_no_collision_zero_loss
severity_bbox_proxy_only_when_explicitly_enabled_or_bbox_backend
search_position_uses_improved_severity_stats
separator_gls_uses_improved_backend_confirmed_severity
```

A testnevek eltérhetnek, de a reportban mapeld őket ezekre.

## Kötelező smoke

Bővítsd vagy hozd létre:

```text
scripts/smoke_sgh_q21_collision_severity.py
```

Minimum smoke esetek:

```text
1. large sheet 1500×3000, kis overlap → severity nem 167 mm-es durva lépcső, hanem capped/binary-refined értelmes érték;
2. bbox false-positive exact/CDE no-collision → loss 0 vagy nem-collision score, bbox_proxy_uses == 0;
3. confirmed pair collision → probe_pair_queries > 0, probe_resolved > 0;
4. boundary violation → probe_boundary_queries > 0, resolved severity;
5. unsupported geometry → unsupported_queries > 0 és loss == hard_unsupported_loss;
6. separator tracker build/update útvonalon pair/boundary query count nő;
7. search_position + CDE/Jagua alatt bbox_fallback_queries == 0.
```

## Verify

Futtasd legalább:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::collision_severity
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::search_position
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::separator
cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q20r_sparrow_search_position.py
python3 scripts/smoke_sgh_q21_collision_severity.py
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q21r1_collision_severity_full_sparrow_alignment.md
```

Ha bármelyik nem fut, nincs hamis PASS.

## Report

Hozd létre:

```text
codex/reports/egyedi_solver/sgh_q21r1_collision_severity_full_sparrow_alignment.md
codex/reports/egyedi_solver/sgh_q21r1_collision_severity_full_sparrow_alignment.verify.log
```

A report első sora csak:

```text
PASS
REVISE
BLOCKED
```

PASS report tartalmazza:

```text
- pre-audit findings;
- pontos módosított fájlok;
- config változások és default indoklás;
- többirányú probe irányok listája;
- bracket + binary refinement bizonyíték;
- query/probe/unsupported accounting bizonyíték;
- bbox false-positive exact/CDE no-collision bizonyíték;
- hard_unsupported_loss használat bizonyíték;
- search_position és separator integration bizonyíték;
- smoke output;
- cargo/verify output;
- known limitations, de csak olyan, ami nem sérti az acceptance-t.
```

Nem elfogadható Known limitation PASS mellett:

```text
cardinal-only probe
no binary refinement
large-sheet uncapped 5% step
unsupported probe not counted
tracker query count missing
f64::MAX unsupported loss
```

Ha ezek közül bármi marad: `REVISE`.
