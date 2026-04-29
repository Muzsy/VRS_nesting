# Cavity Prepack Quality Policy

## 1. Cel

Ez a dokumentum a cavity-first/composite prepack runtime policy szabalyait
rogziti a quality profile registry es worker runtime mapping szintjen.

## 2. Policy fogalmak

- `part_in_part=off`:
  - Nincs prepack.
  - Engine CLI: `--part-in-part off`
- `part_in_part=auto`:
  - Legacy engine runtime cavity candidate logika.
  - Engine CLI: `--part-in-part auto`
- `part_in_part=prepack`:
  - Worker-side cavity prepack aktiv.
  - Engine CLI: `--part-in-part off`

Normativ szabaly:
- `prepack` es legacy `auto` ugyanazon runban nem lehet egyszerre aktiv.

## 3. Quality profile elv

- Uj profile: `quality_cavity_prepack`
- Javasolt policy:
  - `placer=nfp`
  - `search=sa`
  - `part_in_part=prepack`
  - `compaction=slide`

Megjegyzes:
- `quality_default` nem valtozik automatikusan.
- `quality_default` csak benchmark/regression evidence utan valthat cavity
  prepack policyre.

## 4. Worker mapping elv

Runtime mapping:
- requested `part_in_part=prepack` ->
  - worker prepack enabled
  - effective engine part_in_part `off`
- requested `part_in_part=auto` ->
  - worker prepack disabled
  - effective engine part_in_part `auto`
- requested `part_in_part=off` ->
  - worker prepack disabled
  - effective engine part_in_part `off`

Audit elvaras:
- reportban es/vagy engine_meta-ban szerepeljen:
  - requested part_in_part
  - effective engine part_in_part
  - cavity prepack enabled flag

## 5. Rust CLI korlat

- A jelenlegi Rust parser csak `off|auto` erteket fogad.
- `prepack` policy Python/worker policy, NEM Rust CLI ertek.
- Rust CLI-be `prepack` ertek kuldese tilos.

## 6. Stabilitasi es minosegi elvarasok

- Nincs timeout-only javitas.
- Nincs work_budget-only javitas.
- Nincs warning suppression.
- Nincs globalis hole deletion user-facing geometrybol.
- Nincs partnev/fajlnev alapu hardcode.

## 7. Regression baseline

Root-cause kontextus:
- Holed moving part mellett globalis NFP->BLF fallback lehet.
- Cavity prepack policy celja, hogy a top-level engine input parent hole nelkuli
  virtual partokkal fusson, igy a fallback ne emiatt legyen globalis.

Meroelvaras:
- prepack modban ne legyen fallback warning pusztan parent hole miatt
- `NEST_NFP_STATS_V1.effective_placer` legyen `nfp`, ha top-level input hole-free
- cavity nelkuli runok legacy viselkedese maradjon

## 8. Rollout szabaly

- Kotelezo lepessorrend:
  1. T0 artifact replay baseline
  2. T1 contract/policy
  3. T2 runtime mapping
  4. T3-T6 implementacio + validacio
  5. T8 production regression benchmark
- `quality_default` atallitas csak T8 evidence alapjan, kulon dontessel.

## 9. Kapcsolodo dokumentumok

- `docs/nesting_engine/cavity_prepack_contract_v1.md`
- `docs/nesting_engine/io_contract_v2.md`
- `docs/nesting_quality/h3_quality_benchmark_harness.md`
