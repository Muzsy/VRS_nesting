# canvases/nesting_engine/nesting_engine_nfp_placer_stats_and_perf_gate.md

> Mentés: `canvases/nesting_engine/nesting_engine_nfp_placer_stats_and_perf_gate.md`  
> TASK_SLUG: `nesting_engine_nfp_placer_stats_and_perf_gate`  
> AREA: `nesting_engine`

# NFP placer: determinisztikus stats + perf gate (F2-3)

## 🎯 Funkció

A cél: az F2-3 `--placer nfp` futásokhoz **determinista, számláló-alapú** statisztikák bevezetése, majd ezekre egy **CI/gate** (check.sh) hozzáadása, ami regressziót fog (pl. NFP compute/candidate/CFR műveletszám robbanás).

**Fontos elv:**
- Nem időt mérünk (az gépfüggő), hanem **műveletszámot/countereket**.
- A stat kimenet **nem** módosíthatja az IO contract v2 output JSON-t (ne változzon a determinism hash).
- A stat kimenet legyen géppel parsolható (egy sor, JSON), és csak akkor jelenjen meg, ha explicit engedélyezve van (env var).

## 🧠 Fejlesztési részletek

### 1) Stat “wire format”
- Prefix + JSON egy sorban, stderr-re:
  - `NEST_NFP_STATS_V1 { ...json... }`
- Engedélyezés env varral (ne legyen állandó zaj):
  - `NESTING_ENGINE_EMIT_NFP_STATS=1`

### 2) Mit mérünk (minimum)
Az alábbi counterek legyenek **egészek**, determinisztikusan növelve:

**NFP / cache**
- `nfp_cache_hits`
- `nfp_cache_misses`
- `nfp_cache_entries_end` (futás végén cache size)

**NFP compute / CFR**
- `nfp_compute_calls` (cache miss → tényleges NFP generálás)
- `cfr_calls` (hányszor számolunk CFR-t)
- `cfr_union_calls` + `cfr_diff_calls` (legalább call-szint, nem belső opszám)

**Candidate pipeline**
- `candidates_before_dedupe_total`
- `candidates_after_dedupe_total`
- `candidates_after_cap_total`
- `cap_applied_count` (hányszor vágott a 4096-os cap)

**Scope meta**
- `effective_placer` (`"nfp"` / `"blf"`)
- `sheets_used` (outputból is következtethető, de itt jó explicit)

### 3) Hol gyűjtjük (kódban)
Kód és felelősségek:

- `rust/nesting_engine/src/placement/nfp_placer.rs`
  - `pub struct NfpPlacerStatsV1` (Default + merge/add)
  - `nfp_place(..., stats: &mut NfpPlacerStatsV1)`:
    - candidate számlálók itt keletkeznek
    - `nfp_compute_calls` itt (cache miss ág)
    - `cfr_calls` itt (minden CFR számítás előtt/után)

- `rust/nesting_engine/src/nfp/cfr.rs`
  - `compute_cfr_with_stats(..., stats: &mut CfrStatsV1)` vagy ekvivalens minimál instrumentation:
    - union/diff call-számlálók itt, hogy ne “2*cfr_calls” becslés legyen

- `rust/nesting_engine/src/multi_bin/greedy.rs`
  - `greedy_multi_sheet(...) -> (MultiSheetResult, Option<NfpPlacerStatsV1>)`
  - BLF esetén `None`, NFP esetén aggregált stat visszaadása (multi-sheet összeadva)

- `rust/nesting_engine/src/main.rs`
  - `run_nest(...)`:
    - `let (result, nfp_stats_opt) = greedy_multi_sheet(...)`
    - ha `NESTING_ENGINE_EMIT_NFP_STATS=1`: írja ki a `NEST_NFP_STATS_V1 ...` sort stderr-re
    - **ne** kerüljenek bele a statok a `build_output_v2(...)` JSON outputba

### 4) Perf gate: baseline + smoke script
Hozz létre egy baseline fájlt a `poc/nesting_engine/` alatt, és egy smoke scriptet.

- Baseline:
  - `poc/nesting_engine/f2_3_nfp_perf_gate_baselines.json`
  - Formátum (v1):
    - `version`
    - `fixtures`: lista, mindegyik:
      - `id` (pl. `f0_sanity`, `f4_cfr_order`)
      - `path` (poc json)
      - `max`: kulcs→max érték (upper bound). Csökkenés OK; növekedés FAIL.

- Smoke:
  - `scripts/smoke_nfp_placer_stats_and_perf_gate.py`
  - Két mód:
    1) `--record` → lefuttatja a fixture-ket, kiolvassa a statot, és létrehozza/frissíti a baseline-t (max = mért érték).
    2) `--check` → lefuttatja és összeveti: minden counter <= baseline.max.

- Gate bekötés:
  - `scripts/check.sh` nesting_engine blokkban, a már meglévő F0–F4 után:
    - `python3 scripts/smoke_nfp_placer_stats_and_perf_gate.py --check --bin "$NESTING_ENGINE_BIN_PATH" --baseline "poc/nesting_engine/f2_3_nfp_perf_gate_baselines.json"`

### 5) Dokumentáció (spec) minimális frissítés
A `docs/nesting_engine/f2_3_nfp_placer_spec.md` megfelelő fejezetében (ahol korábban a stat/perf elvárás szerepel) rögzítsd:
- milyen stat sor formátum van
- hogyan frissül a baseline (`--record`)
- mit véd a gate (mely fixture-kre, mely counterekre)

## 🧪 Tesztállapot

### DoD
- [ ] `NESTING_ENGINE_EMIT_NFP_STATS=1` mellett `nest --placer nfp` futás **stderr**-re kiír 1 db `NEST_NFP_STATS_V1 {json}` sort
- [ ] A stat JSON parse-olható, és a counterek determinisztikusak (ugyanarra a fixture-re többször futtatva azonosak)
- [ ] `scripts/smoke_nfp_placer_stats_and_perf_gate.py --record ...` létrehozza a baseline-t
- [ ] `scripts/smoke_nfp_placer_stats_and_perf_gate.py --check ...` PASS a baseline-nal
- [ ] `scripts/check.sh` hívja a perf gate smoke-ot, és PASS
- [ ] Report + AUTO_VERIFY frissül:
  - `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_nfp_placer_stats_and_perf_gate.md`

## 🌍 Lokalizáció
Nem releváns.

## 📎 Kapcsolódások
- `rust/nesting_engine/src/main.rs::run_nest`
- `rust/nesting_engine/src/multi_bin/greedy.rs::greedy_multi_sheet`
- `rust/nesting_engine/src/placement/nfp_placer.rs::nfp_place`
- `rust/nesting_engine/src/nfp/cfr.rs::compute_cfr`
- `scripts/check.sh`
- `poc/nesting_engine/f2_3_f0_sanity_noholes_v2.json`
- `poc/nesting_engine/f2_3_f4_cfr_order_hardening_noholes_v2.json`
- `docs/nesting_engine/f2_3_nfp_placer_spec.md`

## Felderitesi snapshot (2026-02-28)

- Jelenleg nincs env-gated, machine-parsable `NEST_NFP_STATS_V1 {json}` stats emission a `nest` futasokhoz.
- Jelenleg nincs baseline (`max`) alapu counter gate az F2-3 NFP fixture-kre.
- A perf gate bekotest a `scripts/check.sh` nesting_engine F0-F4 smoke blokk utan kell elhelyezni.
