# Report — lv8_density_t04_phase0_engine_stats_export

**Státusz:** PASS

A `./scripts/verify.sh` (repo gate) zöld: minden T04 DoD pont teljesült. Parser
unit tesztek 18/18 zöldek. Kis-fixture smoke igazolja, hogy a Rust engine
`NESTING_ENGINE_EMIT_NFP_STATS=1` mellett valóban emittálja a `NEST_NFP_STATS_V1`
sort. Rust fájl nem módosult. A harness quiet policy módosult: `capture_engine_stats=True`
esetén stderr mindig `solver_stderr.log`-ba megy, nem `/dev/null`-ba.

## 1) Meta

- **Task slug:** `lv8_density_t04_phase0_engine_stats_export`
- **Kapcsolódó canvas:** [canvases/nesting_engine/lv8_density_t04_phase0_engine_stats_export.md](../../../canvases/nesting_engine/lv8_density_t04_phase0_engine_stats_export.md)
- **Kapcsolódó goal YAML:** [codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t04_phase0_engine_stats_export.yaml](../../goals/canvases/nesting_engine/fill_canvas_lv8_density_t04_phase0_engine_stats_export.yaml)
- **T00 index:** [canvases/nesting_engine/lv8_density_task_index.md](../../../canvases/nesting_engine/lv8_density_task_index.md)
- **T00 master runner:** [codex/prompts/nesting_engine/lv8_density_master_runner.md](../../prompts/nesting_engine/lv8_density_master_runner.md)
- **T01 előzmény-report:** [codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md](lv8_density_t01_phase0_fixture_inventory.md) (PASS)
- **T02 előzmény-report:** [codex/reports/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md](lv8_density_t02_phase0_quality_profile_shadow_switch.md) (PASS)
- **T03 előzmény-report:** [codex/reports/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.md](lv8_density_t03_phase0_nfp_diag_gate.md) (PASS)
- **Forrásterv:** [codex/reports/nesting_engine/development_plan_packing_density_20260515.md](development_plan_packing_density_20260515.md)
- **Futás dátuma:** 2026-05-16
- **Branch / commit:** `main` @ `9dba5f5`
- **Fókusz terület:** Scripts (Python harness engine stats export)

## 2) Scope

### 2.1 Cél

1. A meglévő `NEST_NFP_STATS_V1` engine stats flow auditálása.
2. `NESTING_ENGINE_EMIT_NFP_STATS=1` bekötése a LV8 harness mérési pathon.
3. Quiet mód módosítása: stats capture aktív esetén stderr fájlba megy, nem `/dev/null`-ba.
4. `_parse_engine_stats_from_stderr()` helper és `_normalize_engine_stats()` hozzáadása a harnesshez.
5. `summary.json` bővítése `engine_stats` blokkal (raw + normalized + pending_phase1_fields).
6. Parser unit tesztek hozzáadása (18 teszt).

### 2.2 Nem-cél (explicit)

1. Nem módosítja `rust/nesting_engine/src/nfp/cache.rs` cache struktúráját (T08).
2. Nem vezeti be `clear_all_events` / `peak_entries` mezőket.
3. Nem módosítja `vrs_nesting/config/nesting_quality_profiles.py` (T02/T20).
4. Nem módosítja `worker/cavity_validation.py` (T05).
5. Nem módosítja `search/sa.rs` (T21).
6. Nem implementál Phase 2+ algoritmust (scoring, lookahead, beam, LNS).
7. Nem futtat hosszú LV8 benchmark mátrixot.

## 3) Változások összefoglalója (Change summary)

### 3.1 Érintett fájlok

- **Scripts (harness):**
  - [scripts/experiments/lv8_2sheet_claude_search.py](../../../scripts/experiments/lv8_2sheet_claude_search.py)
    — `STAT_PREFIX` konstans; `_normalize_engine_stats()`; `_parse_engine_stats_from_stderr()`;
    `NESTING_ENGINE_EMIT_NFP_STATS=1` és `NESTING_ENGINE_CAN_PLACE_PROFILE` env bekötés;
    `capture_engine_stats = True` quiet policy; `engine_stats` a `summary`-ban.
- **Tesztek:**
  - [tests/test_lv8_density_engine_stats_export.py](../../../tests/test_lv8_density_engine_stats_export.py) (új, 18 teszt)
- **Codex artefaktok:**
  - [codex/codex_checklist/nesting_engine/lv8_density_t04_phase0_engine_stats_export.md](../../codex_checklist/nesting_engine/lv8_density_t04_phase0_engine_stats_export.md) (új)
  - [codex/reports/nesting_engine/lv8_density_t04_phase0_engine_stats_export.md](lv8_density_t04_phase0_engine_stats_export.md) (új, ez a fájl)
  - `codex/reports/nesting_engine/lv8_density_t04_phase0_engine_stats_export.verify.log` (a `verify.sh` írja)

Nem módosult Rust fájl. `rust/nesting_engine/src/nfp/cache.rs`, `vrs_nesting/`, `worker/`, `search/`
érintetlen.

### 3.2 Miért változtak?

- **Harness (scripts):** T04 előtt `LV8_HARNESS_QUIET=1` esetén stderr `/dev/null`-ba ment — a
  `NEST_NFP_STATS_V1` sor elveszett volna. A T03 lezárása után a `[CONCAVE NFP DIAG]` default off,
  így nincs diag spam indok a `/dev/null` megtartásához stats capture esetén. A `capture_engine_stats`
  bool (`True`) biztosítja, hogy a stats sor a fájlba kerül, nem a konzolra.
- **Tesztek:** A parser helper determinisztikus viselkedését egységtesztek fedik le, hogy a
  Phase 0 → T06 pipeline megbízható adatot kapjon.

## 4) Verifikáció (How tested)

### 4.1 Kötelező parancs

- `./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t04_phase0_engine_stats_export.md`
  → eredmény az AUTO_VERIFY blokkban (4.4 alatt).

### 4.2 Opcionális, feladatfüggő parancsok

- **Előfeltétel ellenőrzés:** T03 státusz PASS (elolvasva a reportból).
- **Kiinduló audit grep-ek:** mind lefuttatva (eredmények a 5) DoD Matrix audit sorában).
- **Parser unit tesztek:**
  ```
  python3 -m pytest tests/test_lv8_density_engine_stats_export.py -v
  → 18 passed in 0.51s
  ```
- **Kis-fixture smoke (opcionális, futtatva):**
  ```bash
  NESTING_ENGINE_EMIT_NFP_STATS=1 \
    rust/nesting_engine/target/release/nesting_engine \
    nest --placer nfp < poc/nesting_engine/f2_4_sa_quality_fixture_v2.json \
    >/tmp/t04_stdout.json 2>/tmp/t04_stderr.log
  grep '^NEST_NFP_STATS_V1 ' /tmp/t04_stderr.log
  ```
  → exit 0; `NEST_NFP_STATS_V1 {...}` sor jelen (teljes JSON a stderr-ben).
- **Rust fájl nem módosult** — `cargo check` nem szükséges; production diff guard
  a Rust fájlokra üres.

### 4.3 Ha valami kimaradt

Semmilyen kötelező ellenőrzés nem maradt ki. Hosszú LV8 benchmark explicit tilos
(T06 scope). Rust fájl érintetlen, ezért `cargo check` nem kötelező — ezt a
reportban rögzítjük (DoD #9).

### 4.4 Automatikus blokk

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-16T20:24:47+02:00 → 2026-05-16T20:27:51+02:00 (184s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/lv8_density_t04_phase0_engine_stats_export.verify.log`
- git: `main@9dba5f5`
- módosított fájlok (git status): 8

**git diff --stat**

```text
 scripts/experiments/lv8_2sheet_claude_search.py | 78 ++++++++++++++++++++++++-
 1 file changed, 77 insertions(+), 1 deletion(-)
```

**git status --porcelain (preview)**

```text
 M scripts/experiments/lv8_2sheet_claude_search.py
?? canvases/nesting_engine/lv8_density_t04_phase0_engine_stats_export.md
?? codex/codex_checklist/nesting_engine/lv8_density_t04_phase0_engine_stats_export.md
?? codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t04_phase0_engine_stats_export.yaml
?? codex/prompts/nesting_engine/lv8_density_t04_phase0_engine_stats_export/
?? codex/reports/nesting_engine/lv8_density_t04_phase0_engine_stats_export.md
?? codex/reports/nesting_engine/lv8_density_t04_phase0_engine_stats_export.verify.log
?? tests/test_lv8_density_engine_stats_export.py
```

<!-- AUTO_VERIFY_END -->

## 5) DoD → Evidence Matrix

### Audit eredménye

**NfpPlacerStatsV1 mezők** (`nfp_placer.rs:344-406`):
Jelen és serializálható (`#[derive(Serialize)]`):
`nfp_cache_hits`, `nfp_cache_misses`, `nfp_cache_entries_end`, `nfp_compute_calls`,
`cfr_calls`, `cfr_union_calls`, `cfr_diff_calls`, `cfr_skipped_by_hybrid_count`,
`active_set_*` (15 mező), `candidates_before_dedupe_total`, `candidates_after_dedupe_total`,
`candidates_after_cap_total`, `cap_applied_count`, `effective_placer`, `sheets_used`,
`actual_nfp_kernel`, `actual_narrow_phase`, `can_place_profile_enabled`,
`can_place_profile_calls` és 15 further `can_place_profile_*` mező.

**Nincs a raw-ban** (T08 scope, `pending_phase1_fields`):
`clear_all_events`, `peak_entries` — ezek a `cache.rs:34` `CacheStats`-ban nem szerepelnek.

**main.rs emission** (`main.rs:627-648`):
`should_emit_nfp_stats()` → `NESTING_ENGINE_EMIT_NFP_STATS=1` env; `NEST_NFP_STATS_V1 {json}` a stderr-re.

**greedy.rs aggregáció** (`greedy.rs:643,730,741,847`):
`NfpPlacerStatsV1::default()` → per-round `add_assign` → `nfp_cache_entries_end` a cache `stats().entries`-ből.

**LV8 harness stderr (T04 előtt)**:
`LV8_HARNESS_QUIET=1` esetén stderr → `/dev/null` (stats elveszett volna).
T04 után: `capture_engine_stats=True` → stderr → `solver_stderr.log`.

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó teszt/ellenőrzés |
|---|---|---|---|---|
| #1 T03 PASS előfeltétel ellenőrizve | PASS | [lv8_density_t03_phase0_nfp_diag_gate.md](lv8_density_t03_phase0_nfp_diag_gate.md) státusz: PASS | T03 report elolvasva; minden T03 DoD pont PASS. | — |
| #2 Meglévő stats flow auditálva (NfpPlacerStatsV1, emission, aggregáció, harness) | PASS | [nfp_placer.rs:344-406](../../../rust/nesting_engine/src/placement/nfp_placer.rs#L344-L406); [main.rs:627-648](../../../rust/nesting_engine/src/main.rs#L627-L648); [greedy.rs:643,730,741,847](../../../rust/nesting_engine/src/multi_bin/greedy.rs#L643); [cache.rs:34-38](../../../rust/nesting_engine/src/nfp/cache.rs#L34-L38) | Minden releváns struct/fn megtalálva, mezők azonosítva; az audit eredménye a 5) szekció fejlécében. | — |
| #3 `NESTING_ENGINE_EMIT_NFP_STATS=1` bekötve a T04/T06 mérési pathon | PASS | [scripts/experiments/lv8_2sheet_claude_search.py:L224](../../../scripts/experiments/lv8_2sheet_claude_search.py) — `env["NESTING_ENGINE_EMIT_NFP_STATS"] = "1"` | A harness `run_one()` minden engine futásnál beállítja; nem igényel manuális env-t. | Kis-fixture smoke: `NEST_NFP_STATS_V1` sor jelen |
| #4 Quiet mód nem dobja el a stats sort, ha capture aktív | PASS | [scripts/experiments/lv8_2sheet_claude_search.py](../../../scripts/experiments/lv8_2sheet_claude_search.py) — `capture_engine_stats = True`; `if quiet and not capture_engine_stats:` branch sosem aktív | `capture_engine_stats=True` hardcoded — a devnull branch sosem fut; stderr mindig `solver_stderr.log`-ba megy. | parser tesztek + smoke |
| #5 `summary.json` tartalmaz `engine_stats` blokkot raw + normalized al-blokkal | PASS | [scripts/experiments/lv8_2sheet_claude_search.py](../../../scripts/experiments/lv8_2sheet_claude_search.py) — `engine_stats = _parse_engine_stats_from_stderr(stderr_text)` + `"engine_stats": engine_stats` a summary-ban | A `summary` dict `engine_stats` kulcsa tartalmazza `source`, `available`, `parse_error`, `raw`, `normalized`, `pending_phase1_fields` mezőket. | `test_valid_single_line` |
| #6 Normalized blokk tartalmazza a kötelező 12 mezőt | PASS | [scripts/experiments/lv8_2sheet_claude_search.py](../../../scripts/experiments/lv8_2sheet_claude_search.py) — `_normalize_engine_stats()` | `nfp_cache_hit_count`, `nfp_cache_miss_count`, `nfp_cache_entries_end`, `nfp_compute_count`, `candidate_generate_count`, `candidate_dedup_count`, `candidate_after_cap_count`, `can_place_call_count`, `sheet_spillover_count`, `effective_placer`, `actual_nfp_kernel`, `actual_narrow_phase`. | `test_normalized_field_mapping` |
| #7 Phase 1 cache mezők `pending_phase1_fields` alatt, nem hamis 0-ként | PASS | [scripts/experiments/lv8_2sheet_claude_search.py](../../../scripts/experiments/lv8_2sheet_claude_search.py) — minden `_parse_engine_stats_from_stderr()` ágban `"pending_phase1_fields": ["nfp_cache_clear_all_events", "nfp_cache_peak_entries"]` | A két T08 mező soha nem szerepel `raw` vagy `normalized`-ban; mindig `pending_phase1_fields` alatt jelölt. | `TestPendingPhase1Fields` (6 teszt) |
| #8 Parser unit tesztek zöldek | PASS | `python3 -m pytest tests/test_lv8_density_engine_stats_export.py -v` → `18 passed in 0.51s` | 18 teszt lefedi: valid sor, hiányzó sor, dupla sor, invalid JSON, normalizált mapping, pending fields minden esetben, sheet_spillover számítás. | `pytest tests/test_lv8_density_engine_stats_export.py` |
| #9 Rust fájl nem módosult; ha módosult volna, `cargo check` + Rust teszt zöld | PASS | `git diff HEAD -- 'rust/**'` → üres; production diff: csak Python fájlok | T04 kizárólag Python harness + teszt módosítás. A `cargo check` nem kötelező, mert Rust fájl érintetlen. | — |
| #10 `./scripts/verify.sh --report …` zöld | PASS | AUTO_VERIFY blokk a 4.4 alatt | A repo gate lefutott (pytest + mypy + Sparrow + DXF + multisheet + `vrs_solver` + determinisztika + perf guard). | `./scripts/verify.sh --report …` |
| #11 Checklist és report Report Standard v2 szerint | PASS | [Checklist](../../codex_checklist/nesting_engine/lv8_density_t04_phase0_engine_stats_export.md) + ez a fájl | Checklist pipálható DoD listával; report Report Standard v2 struktúrát követ minden ponthoz path + parancs bizonyítékkal. | `./scripts/verify.sh --report …` |

## 6) IO contract / minták

Nem releváns: T04 nem módosítja a Sparrow IO contractot, a POC mintákat vagy a validátort.
A `summary.json` új `engine_stats` kulcsa visszafelé kompatibilis (additive bővítés).

## 7) Doksi szinkron

- A canvas és YAML T04 scope-ját 1:1-ben követi az implementáció.
- `docs/codex/report_standard.md` és `docs/codex/yaml_schema.md` szabályai betartva.

## 8) Advisory notes (max 5)

- `capture_engine_stats = True` jelenleg hardcoded — a Phase 0 mérési pipeline mindig
  stats-ot kap. Ha T06-ban kiderül, hogy bizonyos futásoknál a stats overhead problémás,
  egy `LV8_HARNESS_ENGINE_STATS` env flag lazán bekapcsolható (T06 döntse el).
- A `LV8_HARNESS_CAN_PLACE_PROFILE` default `1` a Phase 0-ban teljes profiling adatot ad;
  a `can_place_profile_calls` a normalized `can_place_call_count` forrása. Ha a profiling
  maga overhead-et okoz, T06 mérheti az on/off különbséget.
- `_normalize_engine_stats()` a `sheets_used` mezőből számítja `sheet_spillover_count`-ot
  (`max(0, sheets_used - 1)`). Ha a solver 0-t ad vissza (hiba/timeout), az érték 0 marad
  — nem negatív. Ez a mező T06-ban hasznos lehet a multi-sheet arány trackinghez.
- A `can_place_call_count` értéke `None`, ha `can_place_profile_calls` nincs a raw-ban
  (pl. `NESTING_ENGINE_CAN_PLACE_PROFILE` ki van kapcsolva). A `can_place_call_count_source`
  mező jelzi a forrást — T06 így tudja, mikor megbízható az érték.
- A `_parse_engine_stats_from_stderr()` helper `importlib.util`-lal importálható a tesztből —
  ez a minta a `test_dxf_preflight_persistence.py`-ban is alkalmazott megközelítés.

## 9) Follow-ups

1. **T05** — polygon-aware validation gate; T04 lezárása után indítható.
2. **T06** — Phase 0 baseline aggregálás (shadow run); a `engine_stats` blokk T06
   számára stabil forrás. A `LV8_HARNESS_QUIET` policy és a `capture_engine_stats` flag
   T06-ban mérési alapra helyezhető.
3. **T08** — `nfp_cache_clear_all_events` / `nfp_cache_peak_entries` bevezetése a cache-ben;
   ezek a `pending_phase1_fields`-ben dokumentálva.
4. **`capture_engine_stats` env flag (opcionális)** — ha T06 alatt kell a devnull fallback
   visszakapcsolhatóság, egy `LV8_HARNESS_ENGINE_STATS=0|1` env kapcsoló elegendő.
