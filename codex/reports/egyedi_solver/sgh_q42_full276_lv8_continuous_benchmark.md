# FAIL - SGH-Q42 full276 LV8 continuous benchmark

## Meta

- **Task slug:** `sgh_q42_full276_lv8_continuous_benchmark`
- **Kapcsolodo canvas:** `canvases/egyedi_solver/sgh_q42_full276_lv8_continuous_benchmark.md`
- **Kapcsolodo goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q42_full276_lv8_continuous_benchmark.yaml`
- **Futas datuma:** 2026-06-13
- **Branch / commit:** `main@1057cf8`
- **Fokusz terulet:** Scripts / Benchmark / Docs

## Scope

### Cel

- Full276 LV8 benchmark futtatasa max 3 db 1500x3000 sheeten.
- Valid legfeljebb 2 sheetes layout keresese margin 5, spacing 8, kerf 0 mellett.
- Continuous rotation tenyleges bemeneti aktivalasanak es outputbeli hasznalatanak igazolasa.
- Q41 mintaju output, summary, report es render evidence eloallitasa.

### Nem-cel

- Solverlogika refaktoralasa.
- IO contract megvaltoztatasa.
- Celkriterium lazitasa 3 sheetre.

## Valtozasok osszefoglaloja

### Erintett fajlok

- **Canvas/YAML:** `canvases/egyedi_solver/sgh_q42_full276_lv8_continuous_benchmark.md`, `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q42_full276_lv8_continuous_benchmark.yaml`
- **Script:** `scripts/bench_sgh_q42_full276_lv8_continuous.py`
- **Benchmark artefaktumok:** `artifacts/benchmarks/sgh_q42/`
- **Codex report/checklist:** ez a report es `codex/codex_checklist/egyedi_solver/sgh_q42_full276_lv8_continuous_benchmark.md`

### Miert valtoztak?

A feladat Q42-specifikus benchmark futast kert Q41 mintaval. A runner kulon kezeli a continuous rotation inputot, mert a Q41 part-level `allowed_rotations_deg` listai felulirnak a global policyt.

## Benchmark eredmeny

**Q42 benchmark verdict: FAIL / NOT ACHIEVED.** Mindket futas teljes, valid 276/276 elhelyezest adott 0 collision/boundary/margin/spacing violation mellett, de mindketto 3 sheetet hasznalt, ezert a legfeljebb 2 sheetes cel nem teljesult.

| run | status | placed | unplaced | used sheets | used indices | physical util % | final pairs | boundary | margin viol | spacing viol | wall s | runtime ms | acceptance |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1200 sec | ok | 276 | 0 | 3 | [0, 1, 2] | 49.4037 | 0 | 0 | 0 | 0 | 716.692 | 706582.953092 | FAIL |
| 2400 sec | ok | 276 | 0 | 3 | [0, 1, 2] | 49.4037 | 0 | 0 | 0 | 0 | 1315.501 | 1305567.990552 | FAIL |

Legjobb valid eredmeny: 3 sheetes full placement. 2 sheetes valid layout nem szuletett.

## Continuous rotation bizonyitek

- Mindket Q42 inputban `rotation_policy = continuous`.
- Mindket inputban 12 part / 276 instance van, es 0 part tartalmaz `allowed_rotations_deg` mezot.
- Mindket outputban 236 unique rotation value jelent meg.
- Mindket outputban 259 non-orthogonal placement van.
- Min/max rotation: `0.0` / `349.86328125`.
- Pelda non-orthogonal szogek: `209.667188`, `56.625`, `11.625`, `304.195312`, `98.695312`.

## Margin / spacing validacio

- `margin_mm = 5.0`, `spacing_mm = 8.0`, `kerf_mm = 0.0`.
- `technology_sheet_margin_applied = True`.
- `technology_part_spacing_applied = True`.
- `technology_margin_violation_count = 0`.
- `technology_spacing_violation_count = 0`.
- Kerf nem lett spacinghez adva.

## Verifikacio

### Kotelezo parancs

- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q42_full276_lv8_continuous_benchmark.md` -> FAIL
  - pytest: PASS, 391 passed
  - mypy: PASS
  - Sparrow setup/build: FAIL, `ERROR: required command not found: cargo`

### Feladatfuggo parancsok

- `python3 -m py_compile scripts/bench_sgh_q42_full276_lv8_continuous.py` -> PASS
- `git diff --check` -> PASS
- `python3 scripts/bench_sgh_q42_full276_lv8_continuous.py` -> PASS mint futtatas, de benchmark acceptance FAIL a 3 sheetes eredmeny miatt

### Ha valami kimaradt

A teljes repo gate nem tudott vegigfutni, mert a kornyezetben nincs `cargo`. A benchmark acceptance ettol fuggetlenul nem teljesult, mert mindket futas 3 sheetet hasznalt.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **FAIL**
- check.sh exit kód: `2`
- futás: 2026-06-13T23:46:27+02:00 → 2026-06-13T23:46:39+02:00 (12s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q42_full276_lv8_continuous_benchmark.verify.log`
- git: `main@1057cf8`
- módosított fájlok (git status): 7

**git status --porcelain (preview)**

```text
?? artifacts/benchmarks/sgh_q42/
?? canvases/egyedi_solver/sgh_q42_full276_lv8_continuous_benchmark.md
?? codex/codex_checklist/egyedi_solver/sgh_q42_full276_lv8_continuous_benchmark.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q42_full276_lv8_continuous_benchmark.yaml
?? codex/reports/egyedi_solver/sgh_q42_full276_lv8_continuous_benchmark.md
?? codex/reports/egyedi_solver/sgh_q42_full276_lv8_continuous_benchmark.verify.log
?? scripts/bench_sgh_q42_full276_lv8_continuous.py
```

**FAIL tail (utolsó ~60 sor a logból)**

```text
[PYTEST] Unit tests
........................................................................ [ 18%]
........................................................................ [ 36%]
........................................................................ [ 55%]
........................................................................ [ 73%]
........................................................................ [ 92%]
...............................                                          [100%]
391 passed in 9.82s
[MYPY] Type check
Success: no issues found in 26 source files
[SPARROW] Resolve/build via scripts/ensure_sparrow.sh
[ensure_sparrow] pin commit (fallback_cache): c95454e390276231b278c879d25b39708398b7d3
HEAD is now at c95454e Merge pull request #132 from JeroenGar/rand-0.10
ERROR: required command not found: cargo
```

<!-- AUTO_VERIFY_END -->

## DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek | Magyarazat | Ellenorzes |
| --- | ---: | --- | --- | --- |
| #1 Kanonikus full276 input 3 db 1500x3000 stockkal | PASS | `artifacts/benchmarks/sgh_q42/inputs/q42_full276_3x1500x3000_margin5_spacing8_continuous_1200.json` | 12 part, 276 instance, stock quantity 3. | Q42 runner |
| #2 Technologiai parameterek es continuous policy | PASS | `artifacts/benchmarks/sgh_q42/q42_summary.json` | Mindket run margin 5, spacing 8, kerf 0, policy continuous. | Q42 summary |
| #3 Nincs part-level rotation override | PASS | `artifacts/benchmarks/sgh_q42/q42_summary.json` | `part_level_allowed_rotations_present_count = 0`. | Q42 summary |
| #4 Run A 1200 sec output | PASS | `artifacts/benchmarks/sgh_q42/outputs/q42_full276_3x1500x3000_margin5_spacing8_continuous_1200_output.json` | Run A lefutott, `status=ok`, 276/276, 3 sheet. | Q42 runner |
| #5 Run B felteteles logika | PASS | `artifacts/benchmarks/sgh_q42/outputs/q42_full276_3x1500x3000_margin5_spacing8_continuous_2400_output.json` | Run B lefutott, mert Run A 3 sheetet hasznalt. | Q42 runner |
| #6 Summary alapmetrikak | PASS | `artifacts/benchmarks/sgh_q42/q42_summary.json` | Tartalmaz status, placed/unplaced, sheet count/index, utilization, violations, runtime, wall time mezoket. | Q42 summary |
| #7 Continuous rotation bizonyitek | PASS | `artifacts/benchmarks/sgh_q42/q42_summary.json` | 236 unique rotation value es 259 non-orthogonal placement. | Q42 summary |
| #8 Margin/spacing bizonyitek | PASS | `artifacts/benchmarks/sgh_q42/q42_summary.json` | Margin/spacing/kerf es violation countok riportolva, mind 0 violation. | Q42 summary |
| #9 Render evidence | PASS | `artifacts/benchmarks/sgh_q42/renders/q42_full276_3x1500x3000_margin5_spacing8_continuous_2400/render_manifest.json` | Mindket runhoz sheet SVG/PNG es overview keszult. | Render manifest |
| #10 PASS csak valid 2 sheet cel teljesulesnel | FAIL | `artifacts/benchmarks/sgh_q42/q42_report.md` | 2400 sec utan is 3 sheet a legjobb valid eredmeny, ezert nincs teljes PASS. | Q42 report |

## Advisory notes

- A solver mindket futasban valid 3 sheetes full placementet talalt 0 violation mellett.
- A continuous rotation output bizonyitott, nem csak input policy: 259 non-orthogonal placement van.
- A 2400 sec run ugyanazt a sheet countot hozta, mint a 1200 sec run.
