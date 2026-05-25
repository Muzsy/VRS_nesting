# SGH-Q03R — GLS pair weight double-update fix

## Kontextus

Az SGH-Q03 report PASS-t ír és tartalmazza:

```text
SGH-Q04_STATUS: READY
```

A friss repo valós kódellenőrzése közben viszont a `rust/vrs_solver/src/optimizer/separator.rs` fájlban hibagyanús no-downgrade regresszió látszik az SGH-Q02 GLS súlyfrissítésben.

A pair collision ágban ugyanaz a multiplier kétszer kerül alkalmazásra:

```rust
let w = self.pair_weights.entry(key).or_insert(1.0);
*w = (*w * mult).min(weight_max);
*w = (*w * mult).min(weight_max);
```

Ez nem Sparrow-parity GLS viselkedés, mert egyetlen `update_weights()` hívásban a pair weight nem egyszer, hanem kétszer nő. Ez torzítja a weighted loss jelet, és pont azt az SGH-Q02 minőségjavítást rontja el, amire az SGH-Q03 épül.

## Task cél

Javítsd az SGH-Q03 utáni GLS regressziót, mielőtt SGH-Q04 elindulna.

A cél:

```text
1. pair collision GLS weight egy update_weights() híváson belül pontosan egyszer kapja meg a multiplier-t;
2. boundary GLS update viselkedése változatlan marad;
3. SGH-Q02 és SGH-Q03 separator tesztek zöldek legyenek;
4. SGH-Q04_STATUS: READY csak akkor maradhat érvényes, ha ez a korrekció PASS.
```

Ez **nem SGH-Q04 implementációs task**. Ez SGH-Q03 revision gate.

## Dependency gate

Ellenőrizd:

```text
codex/reports/egyedi_solver/sgh_q03_multi_worker_move_items_multi.md
```

Feltételek:

```text
első sor: PASS vagy PASS_WITH_NOTES
report tartalmazza: SGH-Q04_STATUS: READY
```

Ha ezek hiányoznak, állj meg `BLOCKED` státusszal.

## Kötelező repo anchorok

Olvasd el:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
docs/egyedi_solver/sgh_q01_no_downgrade_acceptance_gates.md
docs/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback_contract.md
docs/egyedi_solver/sgh_q03_multi_worker_move_items_multi_contract.md
codex/reports/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback.md
codex/reports/egyedi_solver/sgh_q03_multi_worker_move_items_multi.md
rust/vrs_solver/src/optimizer/separator.rs
```

## Production scope

Engedélyezett production módosítás:

```text
rust/vrs_solver/src/optimizer/separator.rs
```

Tiltott scope:

```text
SGH-Q04 phase orchestration
explore.rs / compress.rs / phase.rs létrehozása
infeasible pool
disruption loop
continuous rotation
CDE backend
smooth collision loss
más production fájl módosítása
```

## Kötelező javítás

A `VrsCollisionTracker::update_weights()` pair collision ágában távolítsd el a dupla alkalmazást.

Elvárt logika:

```rust
let w = self.pair_weights.entry(key).or_insert(1.0);
*w = (*w * mult).min(weight_max);
```

Ne változtasd meg a boundary update logikát.

## Kötelező regressziós ellenőrzés

Minimum legyen igaz:

```text
multiplicative_gls_max_loss_pair_gets_max_ratio PASS
```

Ez a teszt egy max-loss pair esetén azt várja, hogy egyetlen update után:

```text
pair_weight == gls_weight_max_inc_ratio
```

Ha a dupla szorzás bent marad, ennek buknia kellene.

## Kötelező parancsok

Futtasd legalább:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml multiplicative_gls_max_loss_pair_gets_max_ratio --lib
cargo test --manifest-path rust/vrs_solver/Cargo.toml separator --lib
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q03r_gls_pair_weight_double_update_fix.md
```

Emellett futtass egy grep/ellenőrző scriptet, amely bizonyítja, hogy nincs egymás utáni dupla pair update:

```bash
python3 - <<'PY'
from pathlib import Path
p = Path('rust/vrs_solver/src/optimizer/separator.rs')
s = p.read_text()
bad = '*w = (*w * mult).min(weight_max);\n                    *w = (*w * mult).min(weight_max);'
assert bad not in s, 'duplicate pair GLS multiplier update still present'
print('PASS: no duplicate consecutive pair GLS multiplier update')
PY
```

## Kötelező outputok

Hozd létre / töltsd ki:

```text
codex/codex_checklist/egyedi_solver/sgh_q03r_gls_pair_weight_double_update_fix.md
codex/reports/egyedi_solver/sgh_q03r_gls_pair_weight_double_update_fix.md
```

Opcionális, de ajánlott:

```text
docs/egyedi_solver/sgh_q03r_gls_pair_weight_double_update_fix_note.md
```

## Report követelmény

A report tartalmazza:

```text
- dependency evidence
- actual code finding
- exact before/after summary
- proof that pair multiplier is applied once
- SGH-Q02 GLS regression test result
- SGH-Q03 separator test result
- full rust/vrs_solver --lib result
- verify.sh result
- production scope safety
```

A report első sora csak akkor lehet `PASS`, ha minden kötelező parancs zöld.

Ha PASS, a report végén szerepeljen:

```text
SGH-Q04_STATUS: READY
```

Ha bármely gate bukik, a report első sora `REVISE` vagy `BLOCKED`, és **nem** szerepelhet benne `SGH-Q04_STATUS: READY`.

## Elfogadási kritérium

PASS csak akkor:

```text
1. dupla pair GLS multiplier update eltűnt;
2. `multiplicative_gls_max_loss_pair_gets_max_ratio` zöld;
3. `cargo test --manifest-path rust/vrs_solver/Cargo.toml separator --lib` zöld;
4. `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` zöld;
5. verify.sh zöld;
6. production módosítás kizárólag separator.rs;
7. SGH-Q04 nincs implementálva ebben a taskban.
```

