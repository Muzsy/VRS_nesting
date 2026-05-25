# SGH-Q03 — Multi-worker `move_items_multi`

## Kontextus

SGH-Q00/Q01 kimondta, hogy az SGH-01..SGH-05 vonal csak szerkezeti scaffold, nem teljes Sparrow-parity optimalizáló.

SGH-Q02 lezárta az első korrekciós implementációt:

```text
F07 GLS dynamic weights: PARTIAL → FULL(rectangular Phase 1)
F08 restore_but_keep_weights: javított PARTIAL
SGH-Q03_STATUS: READY
```

Ez a task a következő Sparrow-minőségfunkciót vezeti be: több workerrel végzett separator move keresés, Sparrow `move_items_multi()` mintára. A cél nem új phase orchestration, nem solution pool, nem continuous rotation, hanem a meglévő separator belső szomszédkeresésének bővítése.

## Task cél

Implementáld a VRS separatorban a multi-worker `move_items_multi` jellegű keresési réteget:

```text
1. N worker ugyanarról a master layout + tracker állapotról indul;
2. minden worker külön, seedelt és reprodukálható item-sorrenddel próbál separator move-ot;
3. a master a legjobb worker-javaslatot választja ki stabil tie-breakkel;
4. worker_count=1 esetben az SGH-Q02 single-worker viselkedés megmarad;
5. azonos input + azonos seed + azonos worker_count → bit-identikus output;
6. multi-worker nem ronthat: 3 worker dense fixture-en best_loss ≤ 1 worker best_loss.
```

A feladat az SGH-Q01 roadmap F09 hiányát célozza:

```text
F09 multi-worker / move_items_multi: MISSING → PARTIAL vagy FULL(rectangular Phase 1)
```

## Kötelező dependency gate

SGH-Q03 csak akkor indulhat, ha:

```text
codex/reports/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback.md
```

létezik, első sora `PASS` vagy `PASS_WITH_NOTES`, és tartalmazza:

```text
SGH-Q03_STATUS: READY
```

Ha bármely feltétel hiányzik, állj meg `BLOCKED` státusszal, és csak ezeket frissítsd:

```text
codex/reports/egyedi_solver/sgh_q03_multi_worker_move_items_multi.md
codex/codex_checklist/egyedi_solver/sgh_q03_multi_worker_move_items_multi.md
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
docs/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback_contract.md
codex/reports/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback.md
rust/vrs_solver/Cargo.toml
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/working.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/candidates.rs
rust/vrs_solver/src/optimizer/boundary.rs
rust/vrs_solver/src/optimizer/moves.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/io.rs
```

## Sparrow/jagua-rs source evidence

Az SGH-Q00/Q01 alapján kötelező referencia:

```text
sparrow/optimizer/separator.rs move_items_multi() — Algorithm 10
sparrow/optimizer/worker.rs move_items() — Algorithm 5
```

A reportban rögzítsd, hogy a referencia forrást honnan olvastad:

```text
.cache/sparrow / vendor / ensure_sparrow eredmény / SGH-Q00 audit doksi
```

Ha a külső forrás nem elérhető, az SGH-Q00/Q01 auditban rögzített leírást használd, de ezt jelöld a reportban.

## Kötelező implementáció

### 1. Backward-compatible config

A `VrsSeparatorConfig` publikus API-ját ne törd el.

Adj hozzá defaulttal legalább:

```rust
pub worker_count: usize,   // default 1
pub seed: u64,             // default 0 vagy repo-konvenció szerinti determinisztikus default
```

A pontos mezőnevek lehetnek repo-konvencióhoz igazítottak, de kötelező:

```text
- worker_count=1 esetén a régi single-worker ág fusson;
- worker_count=0 legyen validálva vagy normalizálva 1-re;
- azonos seed determinisztikus legyen;
- meglévő struct update szintaxis ne törjön: ..VrsSeparatorConfig::default() működjön.
```

### 2. Worker modell

Vezess be explicit worker absztrakciót a `separator.rs` fájlban.

Minimum elvárás:

```rust
struct SeparatorWorker { ... }
struct WorkerCandidate { ... }
```

Vagy ezzel ekvivalens, jól dokumentált privát típusok.

A worker:

```text
- master layout snapshotból indul;
- master tracker loss-state + GLS weight állapotból indul;
- saját determinisztikus RNG/seed alapján shuffled colliding item sorrendet használ;
- megpróbál legalább egy javító separator move-ot;
- visszaadja a candidate layoutot, tracker állapotot, raw loss-t, weighted loss-t, diagnostics adatokat;
- nem ír közös mutable állapotot.
```

A `VrsCollisionTracker`-hez adj olyan clone/snapshot képességet, ami ehhez kell. Fontos: a GLS súlyok ebben a taskban worker-branchenként másolhatók; a master csak a kiválasztott worker állapotát commitolja.

### 3. `move_items_multi` ág

A `VrsSeparator::run()` vagy belső helper működése legyen kettéválasztva:

```text
worker_count <= 1 → SGH-Q02 single-worker kompatibilis ág
worker_count > 1  → multi-worker move_items_multi ág
```

A multi-worker ág:

```text
- minden iterációban azonos master állapotból indít N workert;
- worker_id szerint eltérő seedet képez;
- a workerek más colliding item-sorrendet próbálnak;
- a legjobb workert választja ki stabil rendezéssel;
- commit csak akkor történik, ha a kiválasztott candidate javítja a master loss-t vagy weighted loss-t a dokumentált szabály szerint;
- rollback esetén továbbra is weight-preserving logika marad;
- tie-break legyen determinisztikus: raw loss, weighted loss, worker_id, majd placement ordering.
```

Ajánlott kiválasztási szabály:

```text
1. alacsonyabb raw best_loss;
2. ha raw loss egyezik: alacsonyabb weighted_loss;
3. ha egyezik: több accepted move;
4. ha egyezik: kisebb worker_id.
```

A végső szabályt írd le a contract doksiban, és teszteld.

### 4. Rayon / dependency kezelés

Ha a repo-ban nincs párhuzamos worker dependency, hozzáadható:

```text
rust/vrs_solver/Cargo.toml
```

Ajánlott:

```toml
rayon = "1"
```

Shuffle-hoz használhatsz meglévő vagy új RNG dependency-t, de csak akkor, ha indokolt és a lock/build működik. Alternatíva: kis, privát determinisztikus Fisher–Yates shuffle saját LCG/XorShift helperrel `separator.rs` alatt, hogy ne nőjön a dependency felület.

A reportban rögzítsd, melyik megoldást választottad és miért.

### 5. Ne nyisd meg a következő scope-okat

Tilos ebben a taskban:

```text
exploration/compression phase orchestration
infeasible solution pool
large-item disruption loop
BPP phase loop
continuous rotation
RotationPolicy trait
smooth LossModel / pole penetration
CollisionBackend / CDE backend
DXF/preflight módosítás
Python runner módosítás
IO contract módosítás
külső Sparrow backendként futtatása
```

A task célja csak a separator worker-parallel search réteg.

## Kötelező tesztek

Adj/frissíts Rust unit teszteket legalább ezekre:

```text
1. worker_count=1 backward compatibility: egyszerű overlap fixture továbbra is best_loss == 0.0 és valid.
2. worker_count=0 normalizálás vagy validáció: nem pánikol, dokumentáltan 1 workerként fut vagy explicit config error-t ad.
3. worker_count=3 same seed determinism: azonos input + seed + worker_count → bit-identical output/diagnostics.
4. different worker seeds produce distinct shuffled orders smoke: legalább diagnosztikai vagy helper szinten igazolt.
5. 3-worker dense fixture best_loss ≤ 1-worker best_loss.
6. 3-worker dense fixture no violations on accepted output.
7. multi-worker tie-break deterministic: mesterséges/egyszerű fixture-en stabil worker választás.
```

Ha egy teszt csak belső helperrel tartható stabilan, tedd privát helper unit testté a `separator.rs` tesztmodulban.

## Benchmark / acceptance gate

Futtasd legalább:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml separator
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q03_multi_worker_move_items_multi.md
```

A reportban legyen külön összehasonlítás:

```text
Fixture: dense 20+ item rectangular overlap/congestion fixture
1 worker: best_loss, iterations, moves_attempted, moves_accepted, rollback_count
3 worker: best_loss, iterations, moves_attempted, moves_accepted, rollback_count
Acceptance: 3-worker best_loss <= 1-worker best_loss; output valid if best_loss == 0.0
```

Ne hazudj runtime-speedupot. A task célja első körben minőségi search parity és determinisztikus multi-worker szerkezet, nem garantált gyorsulás.

## Contract dokumentáció

Hozd létre:

```text
docs/egyedi_solver/sgh_q03_multi_worker_move_items_multi_contract.md
```

Kötelező szekciók:

```text
# SGH-Q03 multi-worker move_items_multi contract
## Decision
## Source Sparrow feature mapping
## VRS implementation summary
## Config semantics
## Worker model
## Determinism and seed contract
## Candidate selection and tie-break contract
## Rollback and GLS weight handling
## Tests and acceptance gates
## Remaining quality gaps after SGH-Q03
## Next task: SGH-Q04
```

## Report és checklist

Hozd létre/frissítsd:

```text
codex/codex_checklist/egyedi_solver/sgh_q03_multi_worker_move_items_multi.md
codex/reports/egyedi_solver/sgh_q03_multi_worker_move_items_multi.md
```

A report első sora csak akkor lehet `PASS`, ha minden kötelező teszt és verify zöld.

Ha minden zöld, a report végén legyen:

```text
SGH-Q04_STATUS: READY
```
