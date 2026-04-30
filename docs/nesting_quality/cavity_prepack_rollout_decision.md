# Cavity prepack rollout decision (T8)

Datum: 2026-04-29
Task: `cavity_t8_production_regression_benchmark`

## Kontextus

- A T0 report szerint a production 1:1 replay tovabbra is blokkolt:
  - `codex/reports/nesting_engine/cavity_t0_artifact_recovery_and_baseline_replay.md` DoD matrix:
    - `Production run URL recovery valos API endpointen ujraellenorizve | FAIL`
    - `Production 1:1 replay uj letoltott snapshot alapjan | FAIL`
- Ugyanezt tamasztja ala egy konkret trial evidence:
  - `tmp/runs/20260330T224752Z_sample_dxf_1ebe1445/downloaded_artifact_urls.json`
  - `solver_input` es `engine_meta` artifact URL: `status=400` / `artifact url failed`.

## Legacy vs prepack benchmark (synthetic fallback evidence)

Production snapshot blokk miatt synthetic fallback replay keszult.
Forras evidence: `tmp/cavity_t8_smoke_evidence.json`

| Mod | Effective placer | NFP fallback warning | Placed | Unplaced | Elapsed (wall sec) | NFP stats (fo jel) |
| --- | --- | --- | --- | --- | --- | --- |
| legacy (`--part-in-part auto`) | `blf` | igen | 13 | 0 | 1.268 | `nfp_compute_calls=0`, `effective_placer=blf` |
| prepack (`--part-in-part off`) | `nfp` | nem | 1 | 0 | 0.138 | `cfr_calls=4`, `effective_placer=nfp` |

Megjegyzes:
- A synthetic prepack futasban a top-level `placed_count` kisebb, mert az internal child placement-ek a cavity plan szerint elore lefoglalasra kerulnek, nem top-level placementkent jelennek meg.
- A celjel itt nem a darabszam maximalizalas, hanem a globalis NFP->BLF fallback megszunese lyukas parent jelenlete mellett.

## Döntés

Jelenlegi dontes: **ne valtsunk `quality_default` profilt**.

Indok:
1. Production 1:1 replay snapshot tovabbra is blokkolt (T0 FAIL pontok).
2. A synthetic benchmark igazolja a vart technikai iranyt (`prepack` mellett nincs globalis NFP->BLF fallback), de ez onmagaban nem eleg production rollout donteshez.

## Rollout gate a default profilhoz

`quality_default` atallitas csak akkor javasolhato kulon taskban, ha:
1. production `solver_input` + `engine_meta` artifact URL recovery igazoltan mukodik;
2. legalabb egy valos, korabban fallbackes run 1:1 legacy vs prepack replay evidenciaval osszehasonlitva;
3. riportalt metrikak:
   - effective placer,
   - fallback warning jelenlet,
   - placed/unplaced (okokkal),
   - elapsed,
   - NFP/BLF/SA telemetry,
   - run-level profile metadata.
