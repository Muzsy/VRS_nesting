# Q55F — Runner és acceptance javítás

## Goal

A Q54 runner hibáját javítani: **spacing 5 / 3 nagy per sheet nem lehet stretch** — ez a **kötelező
primary acceptance**. A Q55 akkor sikeres, ha bizonyítja a szerep-alapú skeleton működését (Anchor +
Interlock + BandInsert egy sheeten, CDE-valid), nem véletlen benchmark-siker.

## Háttér

A Q54E `verdict: PASS` a no-regression + spacing-0 proofon alapult, a spacing-5 3/tábla **stretch**-ként
(nem kötelező). A felhasználó ezt "misleading PASS"-nak ítélte. A Q55F a primary acceptance-t a
spacing-5 3/tábla-ra köti: ha nem teljesül → `verdict = FAIL` (a secondary no-regression nem írhatja felül).

Érintett valós kódpontok:

- `scripts/bench_sgh_q55_role_skeleton.py` (új) — a Q54 bench mintára, de szigorú primary acceptance
- `artifacts/benchmarks/sgh_q55/` — summary, outputs, logs, renders
- a diagnosztika (Q55A-E): role-by-role counts, free-space before/after, edge distance, rotations,
  sheet-close reason, rejection summary

## Globális guardrailek

- Continuous rotation, nincs NFP, nincs bbox-corner primary, nincs hardcoded `Lv8`/3+3 a solverben.
- CDE a collision truth; a proof csak CDE-valid layouton (0 pair, 0 boundary) számít.
- Gated (`VRS_SHEET_BUILDER_SKELETON`), default off → no-regression.
- **Becsületes verdikt:** ha a primary nem teljesül, FAIL — nem álcázzuk PASS-nak.

## Feladat

### Kötelező primary acceptance

```
6× Lv8_11612, spacing 5, skeleton gate ON:
- status = ok
- final_pairs = 0
- boundary_violations = 0
- max_big_per_sheet >= 3
- legalább egy sheeten Anchor + Interlock + BandInsert
- band_insert_candidates_accepted >= 1
```

Ha bármelyik nem teljesül → `verdict = FAIL`.

### Secondary checks (nem írhatják felül a primary FAIL-t)

```
spacing 0 no-regression (2 tábla / 3+3)
full276 no-regression (placed 276, ON <= OFF, valid)
gate off behavior unchanged (byte-azonos)
```

### Kötelező artifactok

```
artifacts/benchmarks/sgh_q55/
  q55_summary.json
  outputs/  logs/  renders/
```

### Report (kötelező tartalom)

```
- touched-file lista
- scope-on túli módosítások indoklása
- gate off/on A/B
- role-by-role candidate counts
- free-space before/after
- edge distance
- seed/refined rotations
- sheet-close reason
- rejection summary
```

### DoD

- A runner a primary acceptance-t a fenti módon értékeli; FAIL ha a spacing-5 3/tábla + role-skeleton
  nem teljesül.
- A report őszinte verdiktet ad, a diagnosztika role-onként bizonyítja a skeleton működését.
- A secondary no-regression megmarad, de nem írja felül a primary-t.

## Runner / verification

- `python3 scripts/bench_sgh_q55_role_skeleton.py --proof-time 120 --full-time 300`
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml skeleton`
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q55f_runner_primary_acceptance.md`

## Rollback

- A runner read-only (nem változtat solver-viselkedést); ha a primary FAIL, az **valós eredmény**, nem
  rollback — a fázis-diagnosztika mutatja, hol akad el (a következő lever forrása).
