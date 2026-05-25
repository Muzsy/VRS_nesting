# Runner prompt — SGH-Q03R `gls_pair_weight_double_update_fix`

## Feladat

A helyi `VRS_nesting` repo gyökerében dolgozz. Hajtsd végre az SGH-Q03 revision taskot:

```text
SGH-Q03R — GLS pair weight double-update fix
```

Ez **nem SGH-Q04**. Ne implementálj exploration/compression orchestrationt. A cél egy SGH-Q03 után talált GLS regresszió javítása.

## Miért kell ez?

A friss repo valós `rust/vrs_solver/src/optimizer/separator.rs` fájljában a `VrsCollisionTracker::update_weights()` pair collision ágában ez a hibagyanús minta látszik:

```rust
let w = self.pair_weights.entry(key).or_insert(1.0);
*w = (*w * mult).min(weight_max);
*w = (*w * mult).min(weight_max);
```

Ez egyetlen `update_weights()` híváson belül kétszer alkalmazza ugyanazt a GLS multiplier-t a pair weightre. Ez sérti az SGH-Q02 GLS parity contractot, torzítja a weighted loss-t, és SGH-Q04 előtt javítani kell.

## Production scope

Engedélyezett production módosítás:

```text
rust/vrs_solver/src/optimizer/separator.rs
```

Tiltott production módosítás:

```text
rust/vrs_solver/src/optimizer/explore.rs
rust/vrs_solver/src/optimizer/compress.rs
rust/vrs_solver/src/optimizer/phase.rs
bármely SGH-Q04 phase orchestration implementáció
continuous rotation
CDE backend
smooth collision severity modell
más production fájl
```

## Dokumentáció/report/checklist scope

Hozd létre / töltsd ki:

```text
codex/codex_checklist/egyedi_solver/sgh_q03r_gls_pair_weight_double_update_fix.md
codex/reports/egyedi_solver/sgh_q03r_gls_pair_weight_double_update_fix.md
codex/reports/egyedi_solver/sgh_q03r_gls_pair_weight_double_update_fix.verify.log
```

Opcionális:

```text
docs/egyedi_solver/sgh_q03r_gls_pair_weight_double_update_fix_note.md
```

## Dependency preflight

Ellenőrizd:

```text
codex/reports/egyedi_solver/sgh_q03_multi_worker_move_items_multi.md
```

Feltételek:

```text
első sor: PASS vagy PASS_WITH_NOTES
tartalmazza: SGH-Q04_STATUS: READY
```

Ha bármelyik hiányzik, állj meg `BLOCKED` státusszal, és ne módosíts production kódot.

## Kötelező olvasmányok

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

## Kötelező javítás

A pair collision ágban csak egyszer alkalmazd a multiplier-t:

```rust
let w = self.pair_weights.entry(key).or_insert(1.0);
*w = (*w * mult).min(weight_max);
```

Ne változtasd meg:

```text
boundary weight update
non-colliding pair decay
weight_max clamp
restore_but_keep_weights
SGH-Q03 worker_count/seed/multi-worker logika
```

## Kötelező ellenőrző script

Futtasd:

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

## Kötelező tesztek

Futtasd legalább:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml multiplicative_gls_max_loss_pair_gets_max_ratio --lib
cargo test --manifest-path rust/vrs_solver/Cargo.toml separator --lib
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q03r_gls_pair_weight_double_update_fix.md
```

A reportba másold be a parancsokat és a lényegi eredményeket.

## Acceptance gates

PASS csak akkor:

```text
G01 dependency gate PASS
G02 duplicate pair update nincs jelen
G03 multiplicative_gls_max_loss_pair_gets_max_ratio PASS
G04 cargo test ... separator --lib PASS
G05 cargo test ... --lib PASS
G06 verify.sh PASS
G07 production módosítás kizárólag separator.rs
G08 SGH-Q04 nem lett implementálva
```

## Report formátum

A report első sora:

```text
PASS
```

csak akkor, ha minden gate zöld.

Ha nem minden gate zöld:

```text
REVISE
```

vagy

```text
BLOCKED
```

A report tartalmazza:

```text
# Report — SGH-Q03R `gls_pair_weight_double_update_fix`

## Status
## Dependency evidence
## Actual code finding
## Change summary
## Regression proof
## Tests run
## Scope safety
## DoD -> Evidence Matrix
```

PASS esetén a report végén szerepeljen:

```text
SGH-Q04_STATUS: READY
```

Fail esetén ez a marker nem szerepelhet.
