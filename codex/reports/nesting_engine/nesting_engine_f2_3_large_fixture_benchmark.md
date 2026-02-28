# Codex Report — nesting_engine_f2_3_large_fixture_benchmark

**Status:** PASS_WITH_NOTES

---

## 1) Meta

- **Task slug:** `nesting_engine_f2_3_large_fixture_benchmark`
- **Kapcsolodo canvas:** `canvases/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark.md`
- **Kapcsolodo goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_f2_3_large_fixture_benchmark.yaml`
- **Futas datuma:** 2026-02-28
- **Branch / commit:** `main` / `ffdcefc` (implementacio kozben, uncommitted)
- **Fokusz terulet:** Mixed

## 2) Scope

### 2.1 Cel

1. Determinisztikus large fixture generalas (500/1000 explicit peldany, quantity=1).
2. BLF vs NFP benchmark script keszitese (runtime + quality + NFP stats + determinism vizsgalat).
3. Meresek lefuttatasa release binarissal es baseline benchmark JSON mentese.
4. Eredmenyek rogzítese report formaban, kesobbi CFR sort-key precompute osszeveteshez.

### 2.2 Nem-cel (explicit)

1. Gate (`scripts/check.sh`) benchmarkkel bovitese.
2. Placer algoritmus valtoztatas.
3. Time-limit policy modositasa a fixture-eken tul.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok

- **Canvas:**
  - `canvases/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark.md`
- **Fixture generator + fixtures:**
  - `scripts/gen_nesting_engine_large_fixture.py`
  - `poc/nesting_engine/f2_3_large_500_noholes_v2.json`
  - `poc/nesting_engine/f2_3_large_1000_noholes_v2.json`
- **Benchmark script + output artifact:**
  - `scripts/bench_nesting_engine_f2_3_large_fixture.py`
  - `runs/benchmarks/nesting_engine_f2_3_large_fixture_benchmark.json`
- **Codex workflow:**
  - `codex/codex_checklist/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark.md`
  - `codex/reports/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark.md`

### 3.2 Miert valtoztak?

- Reprodukálható, nagy elemszámú F2-3 benchmark inputok és scriptelt meres kellett.
- A benchmark script egységesen kezeli a BLF/NFP futast, stats parse-t es determinism ellenorzest.
- A meresi output egy osszevont JSON artifactba kerül, ami ujrafuttatasokkal bovithető/frissíthető.

## 4) Verifikacio

### 4.1 Kotelezo parancs

- `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark.md` -> PASS

### 4.2 Task-specifikus parancsok

- `python3 scripts/gen_nesting_engine_large_fixture.py` -> PASS
- `python3 -m json.tool poc/nesting_engine/f2_3_large_500_noholes_v2.json` -> PASS
- `python3 -m json.tool poc/nesting_engine/f2_3_large_1000_noholes_v2.json` -> PASS
- `cargo build --release --manifest-path rust/nesting_engine/Cargo.toml` -> PASS
- `python3 scripts/bench_nesting_engine_f2_3_large_fixture.py --placer both --runs 5 --input poc/nesting_engine/f2_3_large_500_noholes_v2.json` -> PASS
- `python3 scripts/bench_nesting_engine_f2_3_large_fixture.py --placer both --runs 5 --input poc/nesting_engine/f2_3_large_1000_noholes_v2.json` -> PASS (NFP determinism_stable=false jelzessel)

### 4.3 Meresi osszefoglalo (median)

| Input | Placer | Runtime median (s) | Sheets used median | Placed count median | Utilization median (%) | Determinism stable |
|---|---|---:|---:|---:|---:|---|
| `f2_3_large_500_noholes_v2.json` | BLF | 30.191189 | 1 | 8 | 68.376068 | igen |
| `f2_3_large_500_noholes_v2.json` | NFP | 12.420819 | 49 | 500 | 62.144078 | igen |
| `f2_3_large_1000_noholes_v2.json` | BLF | 30.162483 | 1 | 6 | 59.076923 | igen |
| `f2_3_large_1000_noholes_v2.json` | NFP | 30.105402 | 54 | 432 | 67.414859 | **nem** |

Megjegyzes: a 1000/NFP esetben a hash-ek runonként eltertek, amit a benchmark JSON `summary.determinism_hashes` listaban rogzit.

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
|---|---|---|---|---|
| Generált fixture-ek léteznek és JSON-validak | PASS | `scripts/gen_nesting_engine_large_fixture.py:27`, `poc/nesting_engine/f2_3_large_500_noholes_v2.json:1`, `poc/nesting_engine/f2_3_large_1000_noholes_v2.json:1` | A generator script determinisztikusan eloallitja az explicit peldany-listat (`quantity=1`, egyedi id), es mindket output JSON-valid. | `python3 -m json.tool ...500...`, `python3 -m json.tool ...1000...` |
| Benchmark script lefut és kimenti a bench JSON-t | PASS | `scripts/bench_nesting_engine_f2_3_large_fixture.py:102`, `scripts/bench_nesting_engine_f2_3_large_fixture.py:313`, `runs/benchmarks/nesting_engine_f2_3_large_fixture_benchmark.json` | A script subprocess futtatassal meri a runokat, majd az osszegzest JSON artifactba menti. | benchmark parancsok (500 + 1000) |
| A script ellenőrzi a determinism hash stabilitást placer+input szerint | PASS | `scripts/bench_nesting_engine_f2_3_large_fixture.py:168`, `scripts/bench_nesting_engine_f2_3_large_fixture.py:295` | A summary szamit `determinism_stable` mezot es hash listat; instabilitasnal WARN logot ad. | 1000/NFP futas: `determinism_stable=false` |
| `./scripts/check.sh` PASS | PASS | `scripts/check.sh:265` | A standard gate verify wrapperrel futott, check.sh exit=0. | `./scripts/verify.sh --report ...` |
| `./scripts/verify.sh --report ...` PASS | PASS | `codex/reports/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark.verify.log` | A report AUTO_VERIFY blokkja automatikusan a sikeres wrapper futasbol frissul. | `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark.md` |

## 8) Advisory notes

- A 1000/NFP konfiguracio 30s time-limit mellett run-to-run hash driftet mutat; ez benchmark baseline informacio, nem gate failure.
- A benchmark script merged output modban frissit ugyanabba a JSON artifactba, igy tobb input futasa osszefuzheto.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-02-28T23:52:00+01:00 → 2026-02-28T23:55:01+01:00 (181s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark.verify.log`
- git: `main@ffdcefc`
- módosított fájlok (git status): 10

**git status --porcelain (preview)**

```text
?? canvases/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark.md
?? codex/codex_checklist/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark.md
?? codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_f2_3_large_fixture_benchmark.yaml
?? codex/prompts/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark/
?? codex/reports/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark.md
?? codex/reports/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark.verify.log
?? poc/nesting_engine/f2_3_large_1000_noholes_v2.json
?? poc/nesting_engine/f2_3_large_500_noholes_v2.json
?? scripts/bench_nesting_engine_f2_3_large_fixture.py
?? scripts/gen_nesting_engine_large_fixture.py
```

<!-- AUTO_VERIFY_END -->
