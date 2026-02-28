# canvases/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark.md

> Mentés: `canvases/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark.md`  
> TASK_SLUG: `nesting_engine_f2_3_large_fixture_benchmark`  
> AREA: `nesting_engine`

# F2-3 benchmark: large fixture (500/1000 parts) + BLF vs NFP mérés

## 🎯 Funkció

Cél: mérhető, reprodukálható benchmark létrehozása F2-3 placerhez, ami:
- 500 és 1000 darabos *no-holes* inputot ad a nesting_engine-nek,
- lefuttatja BLF és NFP módban többször,
- rögzíti:
  - runtime (sec) – ugyanazon gépen összehasonlítható,
  - quality: sheets_used, placed_count, utilization (ha számolható),
  - NFP stats: `NEST_NFP_STATS_V1` (már létezik).

Ez NEM gate (nem kerül a check.sh-ba), hanem mérés + baseline report.

## 🧠 Fejlesztési részletek

### Input alap (ne találgass)
Használd a meglévő noholes fixture-t mint “shape seed”:
- `poc/nesting_engine/f2_3_f4_cfr_order_hardening_noholes_v2.json`

Felderítés snapshot (2026-02-28):
- CLI futtatás (repo valós minta): `nesting_engine nest < input.json > output.json`
  - stdin: teljes `nesting_engine_v2` input JSON
  - stdout: output JSON (`version`, `sheets_used`, `placements`, `objective`, `meta`)
  - stderr: NFP stats csak `NESTING_ENGINE_EMIT_NFP_STATS=1` esetén (`NEST_NFP_STATS_V1 {json}`)
- Stabilan olvasható output mezők:
  - `determinism_hash`: `meta.determinism_hash`
  - `sheets_used`: top-level `sheets_used` (integer)
  - `placed_count`: `len(placements)` (top-level `placements` lista)
  - `utilization_pct`: `objective.utilization_pct` (ha hiányzik, `null`)

### 1) Large fixture generálás (determinista)
Hozz létre 2 új bemenetet:

- `poc/nesting_engine/f2_3_large_500_noholes_v2.json`
- `poc/nesting_engine/f2_3_large_1000_noholes_v2.json`

Szabályok:
- ugyanaz a `sheet` objektum, mint az alap fixture-ben
- a `parts` lista a base fixture partjait ismétli ciklikusan
- minden part kap:
  - egyedi `id`: pl. `{base_id}__i{000001}`
  - `quantity = 1` (explicit példányok, ne bízzunk quantity-expand logikában)
  - a base `allowed_rotations_deg`, `outer_points_mm`, `holes_points_mm` 그대로

A generálás történjen scriptből, majd a generált JSON fájlok legyenek committálva (ne runtime-only).

### 2) Benchmark futtatás
Új script:
- `scripts/bench_nesting_engine_f2_3_large_fixture.py`

Funkciók:
- paraméterek:
  - `--bin <path>` (default: `rust/nesting_engine/target/release/nesting_engine`)
  - `--input <path>` (500/1000 json)
  - `--runs <N>` (default 5)
  - `--placer blf|nfp|both` (default both)
  - `--out <path>` (default: `runs/benchmarks/nesting_engine_f2_3_large_fixture_benchmark.json`)
- futtatás:
  - BLF: `nest`
  - NFP: `nest --placer nfp` + env: `NESTING_ENGINE_EMIT_NFP_STATS=1`
- parse:
  - stdout JSON-ból: `meta.determinism_hash`, `result.sheets_used` / `result.placements` (ami ténylegesen van az outputban)
  - stderr-ből: `NEST_NFP_STATS_V1 {json}`
- mérőszámok:
  - runtime_sec (wall clock; ugyanazon gépen trend mérésre)
  - determinism: azonos input + placer esetén hash egyezés runok között
  - sheets_used, placed_count (ha az outputból egyértelmű)
  - utilization: csak ha egyértelműen számolható (különben `null` + megjegyzés)

Output JSON (bench report v1) tartalmazza:
- környezet: python verzió, platform string, bin sha (ha kinyerhető), timestamp
- runs: placer+input alapján listák (runtime + hash + quality + stats)

### 3) Report
`codex/reports/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark.md` tartalmazza:
- pontos parancsok
- mért eredmények összefoglaló táblával (500/1000, BLF/NFP, median runtime, sheets_used, placed_count)
- determinism ellenőrzés (hash-egyezés)
- “CFR sort-key precompute” kontextus: ez a baseline a jövőbeli összevetésekhez

## 🧪 Tesztállapot

### DoD
- [ ] Generált fixture-ek léteznek és JSON-validak:
  - `poc/nesting_engine/f2_3_large_500_noholes_v2.json`
  - `poc/nesting_engine/f2_3_large_1000_noholes_v2.json`
- [ ] `scripts/bench_nesting_engine_f2_3_large_fixture.py` lefut és kimenti a bench JSON-t
- [ ] A script ellenőrzi, hogy run-onként a `determinism_hash` stabil (placer+input szerint)
- [ ] `./scripts/check.sh` PASS (nem módosítjuk a gate-et)
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark.md` PASS

## 🌍 Lokalizáció
Nem releváns.

## 📎 Kapcsolódások
- `poc/nesting_engine/f2_3_f4_cfr_order_hardening_noholes_v2.json`
- `scripts/smoke_nfp_placer_stats_and_perf_gate.py` (stats prefix: `NEST_NFP_STATS_V1`)
- `rust/nesting_engine/src/main.rs` (stderr stats emission env varral)
- `scripts/verify.sh`, `docs/codex/report_standard.md`
