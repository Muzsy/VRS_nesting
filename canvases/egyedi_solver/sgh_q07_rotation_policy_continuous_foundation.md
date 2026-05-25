# SGH-Q07 — RotationPolicy + continuous rotation foundation

## Státusz

Implementation task.

## Előfeltétel

SGH-Q06 report első sora legyen `PASS`, és a reportban legyen:

```text
SGH-Q07_STATUS: READY
```

Ha nincs Q06 PASS vagy nincs marker, a task `BLOCKED`, és nem módosíthat production kódot.

## Cél

A VRS solver rotációs modelljét ki kell venni a `0/90/180/270`-re korlátozott helper-függvényekből, és be kell vezetni egy moduláris, jagua-rs/Sparrow irányú `RotationPolicy` alapréteget.

A végső alkalmazásban támogatandó policy-k:

```text
locked / no_rotation        # tiltás: csak 0°
half_turn                   # 0°, 180°
orthogonal                  # 0°, 90°, 180°, 270°
forty_five                  # 45°-onként
explicit_discrete           # legacy allowed_rotations_deg vagy új explicit lista
continuous                  # determinisztikus mintavétel + local wiggle foundation
```

Q07 célja nem az exact irregular polygon rotation és nem a jagua-rs CDE backend. Az majd SGH-Q08. Q07 célja az, hogy a jelenlegi rectangle/bbox solver útvonal **valóban tudjon nem-90°-os és continuous rotation candidate-ekkel dolgozni**, determinisztikusan, no-downgrade kapukkal.

## Miért kell?

SGH-Q00/Q01 szerint F01 kritikus gap: a VRS jelenleg hardcoded diszkrét 0/90/180/270 logikára épül. Ez ellentétes azzal az alappal, ami miatt a jagua-rs/Sparrow irányt választottuk: a rotation range a keresési tér része, nem későbbi UI-extra.

Q06 már modularizálta a loss jelet. Most a következő core hiány a rotációs policy és angle generation.

## Kötelező source audit

Ne összefoglalóból dolgozz. Ellenőrizd a valós Sparrow/jagua-rs source-t.

Használd a repo meglévő source resolve mechanizmusait, például:

```bash
./scripts/ensure_sparrow.sh
```

Majd keresd meg és olvasd el a releváns fájlokat. A pontos path lehet checkout / cargo registry / vendored dependency függő, ezért fájlkereséssel azonosítsd.

Kötelezően auditálandó fogalmak:

```text
jagua-rs RotationRange / allowed_rotation modell:
- None / Discrete / Continuous vagy aktuális megfelelője

Sparrow placement search:
- uniform rotation sampling
- search_position / search_placement
- coordinate descent / wiggle rotation-axis finomítás
- same seed determinism
```

A reportban rögzítsd:

```text
source path
struct / enum / function name
mit vettünk át VRS-be
mit nem vettünk még át és miért
```

Ha a source audit nem történt meg, a report `REVISE` vagy `BLOCKED`, és nincs `SGH-Q08_STATUS: READY`.

## Scope

### Engedélyezett production fájlok

```text
rust/vrs_solver/src/rotation_policy.rs          # új modul, ajánlott
rust/vrs_solver/src/lib.rs                      # module export
rust/vrs_solver/src/io.rs                       # globális policy + rotation_deg típusa, ha szükséges
rust/vrs_solver/src/item.rs                     # Part/Instance policy resolution + rotation math bridge
rust/vrs_solver/src/optimizer/mod.rs
rust/vrs_solver/src/optimizer/initializer.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/compress.rs
rust/vrs_solver/src/optimizer/moves.rs
rust/vrs_solver/src/optimizer/sheet_elimination.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/score.rs          # csak ha rotation_deg típusa miatt kell
rust/vrs_solver/src/optimizer/working.rs        # csak ha tests/fixtures miatt kell
```

Ha a `Placement.rotation_deg` f64-re migrálása további fájlokat érint, csak minimálisan, indoklással módosítsd őket. Ne nyisd meg a Python runner, frontend/API, DXF/preflight útvonalakat, hacsak compile/serde break miatt nem muszáj; ilyenkor a reportban külön jelöld.

### Engedélyezett artefaktok

```text
docs/egyedi_solver/sgh_q07_rotation_policy_contract.md
codex/codex_checklist/egyedi_solver/sgh_q07_rotation_policy_continuous_foundation.md
codex/reports/egyedi_solver/sgh_q07_rotation_policy_continuous_foundation.md
codex/reports/egyedi_solver/sgh_q07_rotation_policy_continuous_foundation.verify.log
```

### Tiltott scope

```text
jagua-rs CDE backend
exact irregular polygon collision
hole/cavity semantics
DXF/preflight refaktor
külső benchmark backend
új optimizer stratégia Q07-en kívül
Q06 LossModel refaktor, kivéve compile integrációs igazítás
```

## Elvárt architektúra

### 1. RotationPolicy modul

Hozz létre vagy vezess be egy moduláris policy réteget.

Ajánlott forma:

```rust
pub type AngleDeg = f64;

#[derive(Debug, Clone, PartialEq)]
pub enum RotationPolicyKind {
    Locked,
    HalfTurn,
    Orthogonal,
    FortyFive,
    Discrete(Vec<AngleDeg>),
    Continuous,
}

pub struct RotationPolicyConfig {
    pub kind: RotationPolicyKind,
    pub continuous_sample_count: usize,
    pub wiggle_degrees: Vec<AngleDeg>,
}
```

A pontos Rust forma igazodhat a repo stílusához, de ezek a képességek kötelezők:

```text
- legacy allowed_rotations_deg -> Discrete policy kompatibilitás
- global solver-level policy
- part-level override
- deterministic candidate angle generation same input + same seed esetén
- non-90° discrete angle támogatás, legalább 45°
- continuous policy determinisztikus mintavétellel
- local wiggle angle set foundation, hogy később Sparrow coordinate descent irányba lehessen vinni
```

### 2. Input/contract compatibility

A meglévő `allowed_rotations_deg` mező maradjon támogatott.

Új opcionális input mezők ajánlottak:

```text
SolverInput.rotation_policy        # globális default, opcionális
Part.rotation_policy               # part-level override, opcionális
```

Resolution szabály:

```text
1. Part.rotation_policy, ha meg van adva
2. Part.allowed_rotations_deg, ha nem üres legacy lista
3. SolverInput.rotation_policy, ha meg van adva
4. Ha egyik sincs: legacy mód szerint hiba vagy explicit documented default; no silent downgrade
```

A reportban pontosan írd le a választott precedence-t.

### 3. Placement rotation representation

Ha a continuous rotation valódi támogatásához a `Placement.rotation_deg` mezőt `i64`-ről `f64`-re kell migrálni, végezd el kontrolláltan.

Kötelező no-downgrade követelmény:

```text
- legacy discrete inputok továbbra is működnek
- integer szögek outputja lehetőleg ne változtassa feleslegesen a JSON szerződést
- ha serde output 90 helyett 90.0 lesz, ezt reportold explicit breaking/near-breaking változásként
- determinism hash teszt zöld legyen vagy indokolt, dokumentált update szükséges
```

Ne hagyd meg úgy a rendszert, hogy `Continuous` policy van, de a placement nem tud nem-integer szöget tárolni.

### 4. Általános rectangle rotation math

A `dims_for_rotation`, `rotated_bbox_min_offset`, `placement_anchor_from_rect_min` útvonalat ki kell bővíteni tetszőleges szögre.

Minimum matematika rectangular proxyhoz:

```text
rotate rectangle corners around anchor
bbox_min = min(rotated corners)
bbox_max = max(rotated corners)
rotated_bbox_width  = bbox_max_x - bbox_min_x
rotated_bbox_height = bbox_max_y - bbox_min_y
placement anchor from desired bbox min = rect_min - bbox_min_offset
```

A 0/90/180/270 eseteknek bit/epsilon szinten meg kell őrizniük a korábbi eredményt.

### 5. Search/candidate integration

A következő útvonalak ne közvetlenül `normalize_allowed_rotations(&part.allowed_rotations_deg)` + hardcoded 90°-os helperre épüljenek, hanem policyből kérjenek candidate angle listát:

```text
try_place_on_sheet
lbf/initializer placement
separator find_best_candidate_for_target
compression rotation próbák
moves/reinsert/swap/transfer ahol rotációt próbál
sheet_elimination / repair visszarakási útvonalak
```

Continuous policy esetén minimum:

```text
- deterministic sampled angles, seedből és part/instance azonosítóból származtatva
- tartalmazza a kanonikus szögeket is: 0/90/180/270, hogy ne legyen downgrade
- tartalmazzon nem-kanonikus mintákat is, tehát ne legyen fake continuous
- local wiggle listával bővíthető legyen: angle ± small deltas, normalizálva
```

### 6. No-downgrade stratégia

A Q07 nem ronthatja el:

```text
- Q06 default BboxAreaLoss viselkedését
- Q05/Q05R/Q05R2 BPP phase loopot
- Q04R phase orchestrationt
- SGH-Q03 multi-worker determinismet
- legacy allowed_rotations_deg=[0], [0,90], [0,90,180,270] inputokat
```

## Kötelező tesztek

Adj célzott Rust unit/regression teszteket. Minimum viselkedések:

```text
rotation_policy_locked_generates_only_zero
rotation_policy_half_turn_generates_0_180
rotation_policy_orthogonal_matches_legacy_0_90_180_270
rotation_policy_forty_five_generates_8_angles
legacy_allowed_rotations_deg_still_supported
part_policy_overrides_global_policy
global_policy_used_when_part_has_no_explicit_policy
arbitrary_45_degree_bbox_math_is_correct
continuous_policy_generates_non_orthogonal_angles
continuous_policy_same_seed_is_deterministic
continuous_rotation_can_fit_rectangle_that_orthogonal_cannot
separator_uses_rotation_policy_not_hardcoded_orthogonal
compression_uses_rotation_policy_not_hardcoded_orthogonal
```

A `continuous_rotation_can_fit_rectangle_that_orthogonal_cannot` fixture például lehet:

```text
part: 100 x 20
sheet: 90 x 90
orthogonal: 0° = 100x20 fail, 90° = 20x100 fail
45° bbox ≈ 84.85 x 84.85 pass
```

Ha a fixture exact értékei eltérnek az aktuális anchor/bbox modell miatt, használj ekvivalens determinisztikus példát.

## Acceptance gate

Futtasd és reportold:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml rotation_policy
cargo test --manifest-path rust/vrs_solver/Cargo.toml item
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::initializer
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::separator
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::compress
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::moves
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::sheet_elimination
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q07_rotation_policy_continuous_foundation.md
```

Ha bármelyik fail, report első sora `REVISE` vagy `BLOCKED`, és nincs `SGH-Q08_STATUS: READY`.

## Dokumentáció

Hozd létre:

```text
docs/egyedi_solver/sgh_q07_rotation_policy_contract.md
```

Tartalmazza:

```text
- source audit evidence
- policy enum / input contract
- global vs part-level precedence
- legacy allowed_rotations_deg compatibility
- continuous candidate generation determinism
- rectangle/bbox rotation math
- known limitations: no CDE, no exact irregular rotation, sampled continuous not exhaustive global optimum
- remaining gap: CollisionBackend/CDE SGH-Q08
```

## Report

A report legyen Report Standard v2 szerinti. Kötelező szakaszok:

```text
Dependency evidence
Source audit evidence
Changed files/functions matrix
Rotation policy contract evidence
Legacy no-downgrade evidence
Continuous rotation evidence
Tests added/fixed
Known limitations
Verify commands and results
```

PASS esetén a report végén szerepeljen:

```text
SGH-Q08_STATUS: READY
```
