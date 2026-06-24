# Q65 - PairCompatibilityIndex production Interlock cutover

## Goal / Funkcio

Vigyük át a Q57A/Q57B interlock pair logikát a production `try_admit_critical()` útba úgy, hogy az
`Interlock` szerep ne a leegyszerűsített `interlock_seeds_against_anchor(...)` bbox-seed generátort
használja elsődlegesen, hanem tényleges PairCompatibilityIndex-alapú candidate-eket konvertáljon live
anchor placement seedekké.

## Context / Hatter

A 2026-06-23 audit szerint a pair index jelenleg csak részlegesen fogyasztódik productionben: az
Interlock role ugyan "konzultálja" a pair utat, de nem a teljes indexelt candidate-sorral dolgozik,
hanem egy egyszerűsített seed producerrel. Emiatt a role-aware interlock authority nem látszik a
layoutokon abban az erősségben, amit a Q57 terv megkövetel.

## Source of truth

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `tmp/audit/audit_2026_06_23.md`
- Előzmény: `canvases/egyedi_solver/sgh_q57b_pair_candidates_to_interlock_role.md`

## Existing code anchors

- `rust/vrs_solver/src/optimizer/sparrow/quantify/pair_matrix.rs`
- `rust/vrs_solver/src/optimizer/sparrow/interlock_pair.rs`
- `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs`
- `rust/vrs_solver/src/io.rs`

## Scope

- Live production PairCompatibilityIndex candidate-ek építése a meglévő `SPInstance` cache-ekből.
- Pair relatív transzform konverzió live anchor placement ellen, anchor-rotáció figyelembevételével.
- Pair candidate-ek boundary/CDE validációja és rangsora a production Interlock admission előtt.
- Diagnosztika és bizonyító artifact a valódi solver boundary-ról.

## Out of scope

- Q58 hint-ek teljes queue/quota/frontier wiringje.
- Q60 bounded critical group admission teljes production cutoverja.
- Anchor catalog first-class versenyeztetése.

## Required implementation

1. Épüljön PairCompatibilityIndex közvetlenül a live `SPInstance` cache-ekből is, ne csak külön
   offline part-listás helperből.
2. A pair relatív transzform konverzió kezelje a live anchor tényleges rotációját: a relatív vektor
   és a candidate rotáció igazodjon a placed anchor világkoordinátás állapotához.
3. A production `Interlock` ág a `try_admit_critical()`-ban először ezeket a pair-index candidate-eket
   próbálja, és csak explicit fallbackkel menjen tovább a neighbour feature candidate-ekre.
4. A diagnosztika rögzítse, hogy mi lett az elfogadott pair source, mi volt a pair score, és milyen
   relatív transzformmal dolgozott a pair út.

## Required diagnostics

- `bpp_q61_pair_index_consulted`
- `bpp_q61_pair_candidates_generated`
- `bpp_q65_pair_candidates_valid`
- `bpp_q61_pair_candidates_accepted`
- `bpp_q61_interlock_fallback_to_neighbour`
- `bpp_q65_accepted_pair_source`
- `bpp_q65_accepted_pair_score`
- `bpp_q65_accepted_pair_relative_transform`
- explicit rejection summary fallback esetén

Artifact:

- `artifacts/benchmarks/sgh_q65/interlock_pair_production_cutover.json`

## Required tests / runners

- Új production-szintű teszt a solver boundary-n:
  `rust/vrs_solver/tests/sparrow_q65_pair_index_cutover.rs`
- Ellenőrizze:
  - a pair index productionben ténylegesen candidate-eket generál;
  - accepted pair esetén a source/score/transform látszik a diagnosztikában;
  - fallback esetén a rejection summary explicit;
  - artifact kiírásra kerül.

Parancsok:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml interlock_pair
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_q65_pair_index_cutover
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q65_pair_index_production_interlock_cutover.md
```

## Acceptance criteria

```text
- Az Interlock production ág nem a simplified bbox pair seed helperrel indul.
- A live anchor rotáció figyelembe vett pair transformmal keletkeznek candidate-ek.
- A pair út accepted source/score/transform diagnosztikailag látszik.
- Sikertelen pair út esetén explicit fallback reason marad.
- Van új artifact és zöld verify.
```
