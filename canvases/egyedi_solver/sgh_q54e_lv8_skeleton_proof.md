# Q54E — Integráció + LV8 mechanizmus-proof + diagnosztika

## Goal

A Q54A–D egységes mechanizmusként (skeleton-váz + clearance-aware seed + overlap-toleráns separation +
free-space/band-insert + sheet-close guard) bekötve a Q51 builderbe, **gated** (`VRS_SHEET_BUILDER_SKELETON`,
default off), és **mechanizmus-szinten bizonyítva** — nem vak benchmarkkal. Ez a „kettő egyben"
végbizonyítása.

## Háttér

A Q53E azért volt FAIL és haszontalan, mert scaffoldot mért proof nélkül (306 generált / 0 elfogadott).
A Q54E ezt fordítja meg: a fő gate egy **konkrét mechanizmus-állítás** — ha a solver a reference-szerű
vázzal nem tud 3 nagy critical-t egy táblára validan tenni spacing 5 mellett, full276-ról nincs mit
beszélni. A no-regression a default-off (gate off) byte-azonossággal és a full276 A/B-vel bizonyított.

Érintett valós kódpontok:

- `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs` — `build_critical_aware_seed` (teljes skeleton
  admission bekötés a gate mögött), `try_admit_critical`
- `rust/vrs_solver/src/optimizer/sparrow/sheet_skeleton.rs`, `feature_candidate_generator.rs`
- `rust/vrs_solver/src/io.rs`, `diagnostics.rs` — összesített Q54 diagnosztika
- `scripts/bench_sgh_q54_skeleton_admission.py` (új), `artifacts/benchmarks/sgh_q54/`
- Minta: `scripts/bench_sgh_q53_feature_admission.py`, `scripts/bench_sgh_q51_sheet_builder.py`

## Globális guardrailek

- CDE a collision truth; a proof CSAK CDE-valid layouton számít (0 collision, 0 boundary/spacing).
- Tilos NFP, bbox shortcut; continuous rotation marad continuous; cavity prepack-ben.
- **Nincs hardcoded `Lv8_11612`, nincs hardcoded 3+3** a solverben — a benchmark fixture használhat
  LV8-at, de a solver-logika geometria/profil-alapú.
- **Default off** → a teljes Q47–Q53 viselkedés byte-azonos; a skeleton út csak gate ON mellett aktív.
- **Becsületes verdikt:** ha a gate nem teljesül (nincs 3/tábla spacing 5), az NEGATÍV, de hasznos
  eredmény — fázisonkénti diagnosztikával rögzítve, hol akad el (mint a Q52/Q53 őszinte findingjei).
- Scope-fegyelem + commit-higiénia: a Q54A–E külön, értelmes commitok; a benchmark-artifactok és a
  forráskód külön; ne squash félrevezető üzenetbe (Q53 tanulság).

## Feladat

### Teljes skeleton admission bekötés

- A `build_critical_aware_seed` critical fázisa `VRS_SHEET_BUILDER_SKELETON=1` mellett a Q54A–D utat
  használja: role → clearance-aware seed → overlap-toleráns separation → free-space rangsor → band-insert
  → sheet-close guard. Default off → a jelenlegi (Q51/Q52) seed byte-azonos.
- Feasibility-gated fallback a Q51 LBF seedre (mint a Q51-ben): a skeleton seed csak akkor használt, ha
  teljes és CDE-valid; különben fallback → no-regression.

### Benchmark / runner

- `scripts/bench_sgh_q54_skeleton_admission.py`:
  - **PROOF (fő gate):** 6× `Lv8_11612`, spacing 5, skeleton ON → legalább egy táblán 3 nagy CDE-valid.
  - **kontroll:** ugyanaz skeleton OFF (a jelenlegi 2/2/2).
  - **NO-REGRESSION:** full276, spacing 8, skeleton ON vs OFF → placed=276, used_sheets(ON) ≤ used_sheets(OFF),
    valid.
  - Per-sheet + overview SVG/PNG render (a Q51/Q53 runner-stílus).
  - Artefaktok: `artifacts/benchmarks/sgh_q54/` (inputs, outputs, logs, renders, `q54_summary.json`).

### Diagnosztika (fázisonként, kötelező)

```
skeleton_role_per_admission
clearance_offset_applied / seed_directly_clear_count / controlled_overlap_seed_count
separation_iterations / seed_overlap / seed_rotation / refined_rotation / separation_fail_reason
free_space_proxy_before/after / largest_free_component / band_insert_success
sheet_close_reason
critical_admission_attempts / successes / failures
rotation_distribution (a continuous rotation bizonyítására: nem csak 90/270)
```

### DoD

- A PROOF gate eredménye egyértelmű (PASS = ≥1 táblán 3 nagy spacing 5; vagy NEGATÍV + a fázis-diagnosztika
  megmutatja, hol akad el).
- full276 no-regression bizonyítva (ON ≤ OFF, valid, 276 placed).
- Default off → byte-azonos a Q53 utáni állapottal.
- A report őszinte verdiktet ad (a Q52/Q53 mintára), nem túlkommunikál.

## Runner / verification

- `python3 scripts/bench_sgh_q54_skeleton_admission.py --proof-time 90 --full-time 300`
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml skeleton`
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q54e_lv8_skeleton_proof.md`

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q54e_lv8_skeleton_proof.md
```

## Rollback

- Ha a skeleton admission bármilyen regressziót okoz, gate off → a teljes Q47–Q53 út érintetlen.
- Ha a PROOF NEGATÍV, az NEM rollback-ok: a mechanizmus gated marad, a finding dokumentálva, a következő
  lever a fázis-diagnosztikából adódik.
