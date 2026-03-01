# Codex Report — nesting_engine_f2_3_real_dxf_quality_benchmark

**Status:** PASS_WITH_NOTES

---

## 1) Meta

- **Task slug:** `nesting_engine_f2_3_real_dxf_quality_benchmark`
- **Kapcsolodo canvas:** `canvases/nesting_engine/nesting_engine_f2_3_real_dxf_quality_benchmark.md`
- **Kapcsolodo goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_f2_3_real_dxf_quality_benchmark.yaml`
- **Futas datuma:** 2026-03-01
- **Branch / commit:** `main` / `b9db576` (implementacio kozben, uncommitted)
- **Fokusz terulet:** Mixed

## 2) Scope

### 2.1 Cel

1. Real DXF forrasbol (stock + part) canonical outer-only nesting_engine_v2 fixture-ek generalasa.
2. 200/500 explicit instance benchmark input eloallitasa (`quantity=1`, egyedi id).
3. BLF vs NFP benchmark futtatasa 5-5 ismelessel inputonkent.
4. Median quality/determinism osszefoglalo dokumentalasa report standard formatban.

### 2.2 Nem-cel (explicit)

1. Placer algoritmus vagy NFP implementacio modositasa.
2. IO contract schema valtoztatas.
3. Benchmark script forrasanak atdolgozasa.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok

- **Canvas:**
  - `canvases/nesting_engine/nesting_engine_f2_3_real_dxf_quality_benchmark.md`
- **Fixture generator + fixtures:**
  - `scripts/gen_nesting_engine_real_dxf_quality_fixture.py`
  - `poc/nesting_engine/real_dxf_quality_200_outer_only_v2.json`
  - `poc/nesting_engine/real_dxf_quality_500_outer_only_v2.json`
- **Codex workflow:**
  - `codex/codex_checklist/nesting_engine/nesting_engine_f2_3_real_dxf_quality_benchmark.md`
  - `codex/reports/nesting_engine/nesting_engine_f2_3_real_dxf_quality_benchmark.md`

### 3.2 Miert valtoztak?

- Uj, valos DXF eredetu benchmark fixture kellett, amely outer-only modban tisztan hasonlitja BLF/NFP viselkedeset.
- A report celja az volt, hogy evidence alapon rogzitse a runtime, quality es determinism mintazatot 200 es 500 elemszamra.

## 4) Verifikacio

### 4.1 Kotelezo parancs

- `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_f2_3_real_dxf_quality_benchmark.md` -> PASS

### 4.2 Task-specifikus parancsok

- `python3 scripts/gen_nesting_engine_real_dxf_quality_fixture.py` -> PASS
- `python3 -m json.tool poc/nesting_engine/real_dxf_quality_200_outer_only_v2.json` -> PASS
- `python3 -m json.tool poc/nesting_engine/real_dxf_quality_500_outer_only_v2.json` -> PASS
- `cargo build --release --manifest-path rust/nesting_engine/Cargo.toml` -> PASS
- `python3 scripts/bench_nesting_engine_f2_3_large_fixture.py --placer both --runs 5 --input poc/nesting_engine/real_dxf_quality_200_outer_only_v2.json --out /tmp/nesting_engine_f2_3_real_dxf_quality_benchmark.json` -> PASS
- `python3 scripts/bench_nesting_engine_f2_3_large_fixture.py --placer both --runs 5 --input poc/nesting_engine/real_dxf_quality_500_outer_only_v2.json --out /tmp/nesting_engine_f2_3_real_dxf_quality_benchmark.json` -> PASS

### 4.3 Meresi osszefoglalo (median)

| Input | Placer | Runtime median (s) | Sheets used median | Placed count median | Utilization median (%) | Determinism stable |
|---|---|---:|---:|---:|---:|---|
| `real_dxf_quality_200_outer_only_v2.json` | BLF | 319.800558 | 1 | 24 | 14.516587 | igen |
| `real_dxf_quality_200_outer_only_v2.json` | NFP | 9.559497 | 2 | 200 | 60.485780 | igen |
| `real_dxf_quality_500_outer_only_v2.json` | BLF | 317.427091 | 1 | 24 | 14.516587 | **nem** |
| `real_dxf_quality_500_outer_only_v2.json` | NFP | 59.161771 | 5 | 500 | 60.485780 | igen |

Ertelmezes (csak evidence alapjan): ezen a valos DXF-eredetu outer-only dataseten NFP egyertelmuen tobb partot helyezett el es magasabb kihasznaltsagot adott, mikozben 500/BLF esetben hash-instabilitas is jelentkezett.

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
|---|---|---|---|---|
| A ket fixture letezik (`200/500`) | PASS | `scripts/gen_nesting_engine_real_dxf_quality_fixture.py:22`, `scripts/gen_nesting_engine_real_dxf_quality_fixture.py:299`, `poc/nesting_engine/real_dxf_quality_200_outer_only_v2.json:1`, `poc/nesting_engine/real_dxf_quality_500_outer_only_v2.json:1` | A generator script default output pathokra ir, explicit `quantity=1` partlistaval es egyedi id-kkel. | `python3 scripts/gen_nesting_engine_real_dxf_quality_fixture.py` |
| A benchmark lefut mindket fixture-re | PASS | `scripts/bench_nesting_engine_f2_3_large_fixture.py:235`, `scripts/bench_nesting_engine_f2_3_large_fixture.py:284`, `scripts/bench_nesting_engine_f2_3_large_fixture.py:313` | A benchmark script `--placer both --runs 5` modban futtat es summary entry-ket ment; mindket inputra sikeres run keszult. | ket benchmark parancs (`200`, `500`) |
| A report tartalmazza a median osszefoglalot + determinism megallapitast | PASS | `codex/reports/nesting_engine/nesting_engine_f2_3_real_dxf_quality_benchmark.md:72`, `codex/reports/nesting_engine/nesting_engine_f2_3_real_dxf_quality_benchmark.md:81` | A 2x2 tabla tartalmaz runtime/sheets/placed/utilization medianokat es determinism stabilitast, kulon jelolve a `500/BLF` instabil esetet. | report review |
| `./scripts/check.sh` PASS | PASS | `scripts/check.sh:265`, `codex/reports/nesting_engine/nesting_engine_f2_3_real_dxf_quality_benchmark.verify.log:1` | A repo gate-et verify wrapper futtatja, ami check.sh PASS eredmenyt ad. | `./scripts/verify.sh --report ...` |
| `./scripts/verify.sh --report ...` PASS | PASS | `scripts/verify.sh:1`, `codex/reports/nesting_engine/nesting_engine_f2_3_real_dxf_quality_benchmark.verify.log:1` | A wrapper lefut, logot ir, es automatikusan frissiti az AUTO_VERIFY blokkot. | `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_f2_3_real_dxf_quality_benchmark.md` |

## 8) Advisory notes

- A `real_dxf_quality_500_outer_only_v2` BLF futasnal hash-instabilitas jelentkezett (`determinism_stable=false`) egy 23-vs-24 placement elteressel.
- Az NFP ugyanazon inputon stabil hash-t adott es teljes darabszamot helyezett el (`200/200`, `500/500`).
- A benchmark artifactot `/tmp` ala irtuk (`--out /tmp/...`), igy a feladat csak a YAML `outputs` repofajlokat modositotta.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-01T22:46:11+01:00 → 2026-03-01T22:49:18+01:00 (187s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/nesting_engine_f2_3_real_dxf_quality_benchmark.verify.log`
- git: `main@b9db576`
- módosított fájlok (git status): 9

**git status --porcelain (preview)**

```text
?? canvases/nesting_engine/nesting_engine_f2_3_real_dxf_quality_benchmark.md
?? codex/codex_checklist/nesting_engine/nesting_engine_f2_3_real_dxf_quality_benchmark.md
?? codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_f2_3_real_dxf_quality_benchmark.yaml
?? codex/prompts/nesting_engine/nesting_engine_f2_3_real_dxf_quality_benchmark/
?? codex/reports/nesting_engine/nesting_engine_f2_3_real_dxf_quality_benchmark.md
?? codex/reports/nesting_engine/nesting_engine_f2_3_real_dxf_quality_benchmark.verify.log
?? poc/nesting_engine/real_dxf_quality_200_outer_only_v2.json
?? poc/nesting_engine/real_dxf_quality_500_outer_only_v2.json
?? scripts/gen_nesting_engine_real_dxf_quality_fixture.py
```

<!-- AUTO_VERIFY_END -->
