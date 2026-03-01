# Codex Report — nesting_engine_f2_3_large_fixture_benchmark

**Status:** PASS_WITH_NOTES

---

## 1) Meta

- **Task slug:** `nesting_engine_f2_3_large_fixture_benchmark`
- **Kapcsolodo canvas:** `canvases/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark.md`
- **Kapcsolodo goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_f2_3_large_fixture_benchmark.yaml`
- **Futas datuma:** 2026-03-01
- **Branch / commit:** `main` / `27a0b00` (implementacio kozben, uncommitted)
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
- `python3 scripts/bench_nesting_engine_f2_3_large_fixture.py --placer both --runs 5 --input poc/nesting_engine/f2_3_large_1000_noholes_v2.json` -> PASS

### 4.3 Meresi osszefoglalo (median)

| Input | Placer | Runtime median (s) | Sheets used median | Placed count median | Utilization median (%) | Determinism stable |
|---|---|---:|---:|---:|---:|---|
| `f2_3_large_500_noholes_v2.json` | BLF | 300.177904 | 3 | 24 | 68.376068 | igen |
| `f2_3_large_500_noholes_v2.json` | NFP | 11.763649 | 49 | 500 | 62.144078 | igen |
| `f2_3_large_1000_noholes_v2.json` | BLF | 300.234033 | 2 | 16 | 68.376068 | igen |
| `f2_3_large_1000_noholes_v2.json` | NFP | 44.732846 | 98 | 1000 | 62.135008 | igen |

Megjegyzes: 300s time-limit mellett mind a 4 meresi sor `determinism_stable=true`; a benchmark JSON minden sorban egyedi hash-t tartalmaz a `summary.determinism_hash` mezoben.

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
|---|---|---|---|---|
| Generált fixture-ek léteznek és JSON-validak | PASS | `scripts/gen_nesting_engine_large_fixture.py:27`, `poc/nesting_engine/f2_3_large_500_noholes_v2.json:1`, `poc/nesting_engine/f2_3_large_1000_noholes_v2.json:1` | A generator script determinisztikusan eloallitja az explicit peldany-listat (`quantity=1`, egyedi id), es mindket output JSON-valid. | `python3 -m json.tool ...500...`, `python3 -m json.tool ...1000...` |
| Benchmark script lefut és kimenti a bench JSON-t | PASS | `scripts/bench_nesting_engine_f2_3_large_fixture.py:102`, `scripts/bench_nesting_engine_f2_3_large_fixture.py:313`, `runs/benchmarks/nesting_engine_f2_3_large_fixture_benchmark.json` | A script subprocess futtatassal meri a runokat, majd az osszegzest JSON artifactba menti. | benchmark parancsok (500 + 1000) |
| A script ellenőrzi a determinism hash stabilitást placer+input szerint | PASS | `scripts/bench_nesting_engine_f2_3_large_fixture.py:168`, `scripts/bench_nesting_engine_f2_3_large_fixture.py:295` | A summary szamit `determinism_stable` mezot es hash listat; instabilitasnal WARN logot ad. | 500/1000 + BLF/NFP futasok: mind `determinism_stable=true` |
| `./scripts/check.sh` PASS | PASS | `scripts/check.sh:265` | A standard gate verify wrapperrel futott, check.sh exit=0. | `./scripts/verify.sh --report ...` |
| `./scripts/verify.sh --report ...` PASS | PASS | `codex/reports/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark.verify.log` | A report AUTO_VERIFY blokkja automatikusan a sikeres wrapper futasbol frissul. | `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark.md` |

## 8) Advisory notes

- A korabbi 30s-os 1000/NFP hash drift reprodukálhatóan time-limit dominanciahoz kotodott; 300s time-limit mellett a drift nem jelentkezett.
- A benchmark script merged output modban frissit ugyanabba a JSON artifactba, igy tobb input futasa osszefuzheto.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-01T01:31:54+01:00 → 2026-03-01T01:34:53+01:00 (179s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark.verify.log`
- git: `main@27a0b00`
- módosított fájlok (git status): 5

**git diff --stat**

```text
 .../nesting_engine_f2_3_large_fixture_benchmark.md | 20 ++++-----
 ..._engine_f2_3_large_fixture_benchmark.verify.log | 52 +++++++++++-----------
 2 files changed, 36 insertions(+), 36 deletions(-)
```

**git status --porcelain (preview)**

```text
 M codex/reports/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark.md
 M codex/reports/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark.verify.log
?? canvases/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark_refresh_time_limit_300.md
?? codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_f2_3_large_fixture_benchmark_refresh_time_limit_300.yaml
?? codex/prompts/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark_refresh_time_limit_300/
```

<!-- AUTO_VERIFY_END -->
