# LV8 Density T04 — Phase 0 engine stats export

## 🎯 Funkció

A feladat célja a Phase 0 mérési higiénia következő eleme: az engine NFP / placement statisztikáinak gépileg olvasható exportja a későbbi T06 shadow run és Phase 1–2 A/B mérések számára.

A friss repo-snapshot alapján **nem nulláról kell új `NfpPlacerStatsV2` struktúrát írni**. A `rust/nesting_engine/src/placement/nfp_placer.rs` fájlban már létezik `NfpPlacerStatsV1`, sok szükséges mezővel, és a `rust/nesting_engine/src/main.rs` már képes `NESTING_ENGINE_EMIT_NFP_STATS=1` mellett `NEST_NFP_STATS_V1 {json}` sort írni stderr-re. A T04 feladata ennek az auditra, normalizálására és az LV8 harness `summary.json`-jába kötésére fókuszál.

A T04 nem cache-hardening feladat. A cache belső `clear_all_events` / `peak_entries` bővítése a Phase 1 / T08 scope-ja. T04-ben csak azt kell biztosítani, hogy a most elérhető statisztikák stabilan eljussanak a benchmark summary-ba, és a hiányzó Phase 1 mezők explicit `pending_phase1` státusszal dokumentálva legyenek.

## Forrás és döntések

A T04 a végleges `codex/reports/nesting_engine/development_plan_packing_density_20260515.md` v2.2 terv Phase 0.4 pontjára és a T00 task index T04 bontására épül.

Beépített végleges döntések:

- A T04 feladata **engine stats export**, nem új algoritmus.
- A `NEST_NFP_STATS_V1` stderr JSON a meglévő engine-side forrás.
- A `summary.json` kapjon `engine_stats` blokkot, amely tartalmazza a raw és normalizált statokat.
- A `LV8_HARNESS_QUIET=1` log-size guard maradhat, de nem akadályozhatja meg a `NEST_NFP_STATS_V1` parsingot.
- A T04 nem futtat hosszú LV8 benchmark mátrixot; csak rövid / célzott sanity futásokat és parser teszteket.
- A T04 nem módosítja `rust/nesting_engine/src/nfp/cache.rs`; cache stats belső bővítés T08.

## Valós repo-kiindulópontok a friss snapshot alapján

A T04 előtt ellenőrzött releváns állapot:

- `rust/nesting_engine/src/placement/nfp_placer.rs`
  - `NfpPlacerStatsV1` már `Serialize` derive-val rendelkezik.
  - Már tartalmaz több Phase 0-hoz hasznos mezőt:
    - `nfp_cache_hits`
    - `nfp_cache_misses`
    - `nfp_cache_entries_end`
    - `nfp_compute_calls`
    - `cfr_calls`
    - `cfr_union_calls`
    - `cfr_diff_calls`
    - `candidates_before_dedupe_total`
    - `candidates_after_dedupe_total`
    - `candidates_after_cap_total`
    - `cap_applied_count`
    - `effective_placer`
    - `sheets_used`
    - `actual_nfp_kernel`
    - `actual_narrow_phase`
    - `can_place_profile_*` mezők, amelyek csak `NESTING_ENGINE_CAN_PLACE_PROFILE=1` mellett populálódnak.
- `rust/nesting_engine/src/main.rs`
  - `should_emit_nfp_stats()` a `NESTING_ENGINE_EMIT_NFP_STATS=1` env-et olvassa.
  - Bekapcsolva pontosan `NEST_NFP_STATS_V1 {json}` sort ír stderr-re.
- `rust/nesting_engine/src/multi_bin/greedy.rs`
  - A teljes multi-sheet futás elején `NfpCache::new()` jön létre.
  - NFP körökben a round statokat `NfpPlacerStatsV1::add_assign()` aggregálja.
  - A végén `nfp_cache_entries_end`, `effective_placer`, `sheets_used` kitöltésre kerül.
- `rust/nesting_engine/src/nfp/cache.rs`
  - `CacheStats` jelenleg csak `hits`, `misses`, `entries` mezőket ad.
  - `clear_all_events` és `peak_entries` még nincs; ezek T08 scope.
- `scripts/experiments/lv8_2sheet_claude_search.py`
  - Jelenleg a `summary.json` nem tartalmaz `engine_stats` blokkot.
  - `LV8_HARNESS_QUIET=1` esetén stderr `/dev/null`-ba megy, így a `NEST_NFP_STATS_V1` sor elveszne.
  - T03 után a `[CONCAVE NFP DIAG]` default off, ezért a stats sor megőrzése már nem okozhatja a korábbi diag spam problémát.
- `scripts/smoke_nfp_placer_stats_and_perf_gate.py`
  - Már tartalmaz használható mintát a `NEST_NFP_STATS_V1` stderr sor parsingjára.

## T04 scope

### T04 feladata

1. Auditálni a jelenlegi stats flow-t:
   - `NfpPlacerStatsV1` mezők,
   - `main.rs` `NEST_NFP_STATS_V1` emission,
   - `greedy_multi_sheet()` aggregation,
   - LV8 harness stderr kezelés.
2. A `scripts/experiments/lv8_2sheet_claude_search.py` scriptben bekapcsolni az engine stat exportot a benchmark runs számára:
   - `NESTING_ENGINE_EMIT_NFP_STATS=1`.
   - `NESTING_ENGINE_CAN_PLACE_PROFILE` a harness kontrollja alatt legyen, javasolt env: `LV8_HARNESS_CAN_PLACE_PROFILE=1|0`, default `1` a Phase 0 mérési pipeline-hoz.
3. A harness quiet módját úgy módosítani, hogy a `NEST_NFP_STATS_V1` sor ne vesszen el:
   - stats capture esetén stderr menjen `solver_stderr.log` fájlba,
   - summary parsing onnan történjen,
   - nem kell konzolra írni.
4. Parse helper hozzáadása a `NEST_NFP_STATS_V1` sorhoz:
   - 0 sor: `engine_stats_available=false`, indokkal,
   - 1 sor: parse JSON, normalizálás,
   - több sor: fail vagy explicit `engine_stats_parse_error`, de ne silently válasszon random sort.
5. A `summary.json` bővítése `engine_stats` blokkal:
   - `engine_stats.source = "NEST_NFP_STATS_V1"`
   - `engine_stats.available`
   - `engine_stats.raw`
   - `engine_stats.normalized`
   - `engine_stats.pending_phase1_fields`
6. Célzott parser / normalization teszt hozzáadása.
7. T04 checklist és report létrehozása Report Standard v2 szerint.

### T04 nem célja

- Nem módosítja az NFP algoritmust.
- Nem módosítja candidate scoringot.
- Nem implementál lookaheadet, beamet vagy LNS-t.
- Nem módosítja `rust/nesting_engine/src/nfp/cache.rs` belső cache stat struktúráját; az T08.
- Nem vezeti be `clear_all_events` / `peak_entries` mezőket, legfeljebb `pending_phase1_fields` alatt jelzi hiányukat.
- Nem hard-cutolja a `quality_default` SA→none váltást.
- Nem implementál polygon-aware validátort; az T05.
- Nem futtat hosszú LV8 benchmark mátrixot; az T06.
- Nem változtatja meg a `NEST_NFP_STATS_V1` prefixet vagy engine stdout JSON contractot.

## Engedélyezett módosítások

A T04 futása legfeljebb ezeket a fájlokat hozhatja létre vagy módosíthatja:

- `scripts/experiments/lv8_2sheet_claude_search.py`
- `tests/test_lv8_density_engine_stats_export.py`
- `codex/codex_checklist/nesting_engine/lv8_density_t04_phase0_engine_stats_export.md`
- `codex/reports/nesting_engine/lv8_density_t04_phase0_engine_stats_export.md`
- `codex/reports/nesting_engine/lv8_density_t04_phase0_engine_stats_export.verify.log`

Ezeket csak akkor módosíthatod, ha audit alapján tényleg szükséges:

- `rust/nesting_engine/src/placement/nfp_placer.rs` — csak akkor, ha egy meglévő raw stats mező láthatóan nem serializálódik vagy hibásan aggregálódik; ilyen módosítást külön indokolni kell.
- `rust/nesting_engine/src/multi_bin/greedy.rs` — csak akkor, ha a meglévő aggregáció bizonyíthatóan elveszít egy már meglévő mezőt.
- `rust/nesting_engine/src/main.rs` — csak akkor, ha a meglévő `NEST_NFP_STATS_V1` emission nem használható; a prefix és opt-in env név nem változhat.

Tilos módosítani:

- `rust/nesting_engine/src/nfp/cache.rs` — T08 scope.
- `vrs_nesting/config/nesting_quality_profiles.py` — T02/T20 scope.
- `worker/cavity_validation.py` — T05 scope.
- `search/sa.rs` — T21 scope.

Ha bármely tiltott fájl módosítása szükségesnek tűnik, STOP + report szükséges, nem scope-tágítás.

## Kötelező `engine_stats` summary séma

A `summary.json` legalább ezt tartalmazza:

```json
{
  "engine_stats": {
    "source": "NEST_NFP_STATS_V1",
    "available": true,
    "parse_error": null,
    "raw": {
      "nfp_cache_hits": 12,
      "nfp_cache_misses": 34,
      "nfp_cache_entries_end": 34,
      "nfp_compute_calls": 34,
      "candidates_before_dedupe_total": 100,
      "candidates_after_dedupe_total": 80,
      "candidates_after_cap_total": 50,
      "effective_placer": "nfp",
      "sheets_used": 1,
      "actual_nfp_kernel": "old_concave",
      "actual_narrow_phase": "own"
    },
    "normalized": {
      "nfp_cache_hit_count": 12,
      "nfp_cache_miss_count": 34,
      "nfp_cache_entries_end": 34,
      "nfp_compute_count": 34,
      "candidate_generate_count": 100,
      "candidate_dedup_count": 80,
      "candidate_after_cap_count": 50,
      "can_place_call_count": 0,
      "can_place_call_count_source": "can_place_profile_calls",
      "sheet_spillover_count": 0,
      "effective_placer": "nfp",
      "actual_nfp_kernel": "old_concave",
      "actual_narrow_phase": "own"
    },
    "pending_phase1_fields": [
      "nfp_cache_clear_all_events",
      "nfp_cache_peak_entries"
    ]
  }
}
```

A `raw` blokk legyen a `NEST_NFP_STATS_V1` JSON változatlan objektuma. A `normalized` blokk tartalmazzon stabil, Phase 0/T06 által használt neveket. Ha egy érték nem elérhető, `null` és `*_source` mező magyarázza, ne legyen hamis 0.

## Javasolt helper-függvények a harnessben

A pontos implementáció igazodhat a meglévő stílushoz, de legyen hasonló:

```python
STAT_PREFIX = "NEST_NFP_STATS_V1 "


def _parse_engine_stats_from_stderr(stderr_text: str) -> dict[str, Any]:
    matches = [line for line in stderr_text.splitlines() if line.startswith(STAT_PREFIX)]
    if not matches:
        return {
            "source": "NEST_NFP_STATS_V1",
            "available": False,
            "parse_error": "missing_stats_line",
            "raw": None,
            "normalized": None,
            "pending_phase1_fields": ["nfp_cache_clear_all_events", "nfp_cache_peak_entries"],
        }
    if len(matches) != 1:
        return {
            "source": "NEST_NFP_STATS_V1",
            "available": False,
            "parse_error": f"expected_1_stats_line_got_{len(matches)}",
            "raw": None,
            "normalized": None,
            "pending_phase1_fields": ["nfp_cache_clear_all_events", "nfp_cache_peak_entries"],
        }
    try:
        raw = json.loads(matches[0][len(STAT_PREFIX):])
    except json.JSONDecodeError as exc:
        return {
            "source": "NEST_NFP_STATS_V1",
            "available": False,
            "parse_error": f"invalid_json:{exc}",
            "raw": None,
            "normalized": None,
            "pending_phase1_fields": ["nfp_cache_clear_all_events", "nfp_cache_peak_entries"],
        }
    return {
        "source": "NEST_NFP_STATS_V1",
        "available": True,
        "parse_error": None,
        "raw": raw,
        "normalized": _normalize_engine_stats(raw),
        "pending_phase1_fields": ["nfp_cache_clear_all_events", "nfp_cache_peak_entries"],
    }
```

## Minimális célzott ellenőrzések

### Stats parser unit teszt

Adj hozzá `tests/test_lv8_density_engine_stats_export.py` fájlt. A teszt importálja a harness parse helperét és ellenőrzi:

- pontosan 1 `NEST_NFP_STATS_V1` sor → `available=true`, raw és normalized kitöltve;
- hiányzó sor → `available=false`, `parse_error="missing_stats_line"`;
- két sor → `available=false`, multiple-line parse error;
- invalid JSON → `available=false`, invalid-json parse error;
- candidate monotonicity / mapping mezők helyesek.

### Manual smoke kis fixture-rel

Ha a build környezet engedi, futtass rövid, kis fixture-es smoke-ot a meglévő stats emission bizonyítására. Példa:

```bash
NESTING_ENGINE_EMIT_NFP_STATS=1 \
  cargo run --manifest-path rust/nesting_engine/Cargo.toml --bin nesting_engine -- \
  nest --placer nfp < poc/nesting_engine/f2_4_sa_quality_fixture_v2.json \
  >/tmp/t04_stdout.json 2>/tmp/t04_stderr.log

grep '^NEST_NFP_STATS_V1 ' /tmp/t04_stderr.log
```

Ha a pontos binárisnév / parancs eltér, a reportban a valós parancsot rögzíteni kell.

### Harness parser smoke

A `lv8_2sheet_claude_search.py` helperre célzott Python ellenőrzés:

```bash
python3 -m pytest tests/test_lv8_density_engine_stats_export.py -q
```

### Full repo gate

```bash
./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t04_phase0_engine_stats_export.md
```

## Rollback terv

Ha T04 visszavonandó:

1. Távolítsd el az `engine_stats` parsing / summary bővítést a `scripts/experiments/lv8_2sheet_claude_search.py` fájlból.
2. Távolítsd el a `tests/test_lv8_density_engine_stats_export.py` tesztet.
3. Töröld a T04 checklist/report/verify log fájlokat.
4. Ne érintsd a T03 diag gate-et és a T02 shadow profilokat.

## Definition of Done

A T04 akkor PASS, ha:

1. Repo szabályfájlok, T00 index/master runner, T01/T02/T03 reportok elolvasva, és T03 státusza PASS vagy PASS_WITH_NOTES.
2. A reportban audit mátrix szerepel a meglévő stats flow-ról: `NfpPlacerStatsV1`, `main.rs` emission, `greedy_multi_sheet` aggregáció, LV8 harness stderr út.
3. A harness `NESTING_ENGINE_EMIT_NFP_STATS=1` mellett futtatja az engine-t a T04/T06 mérési pathon.
4. A harness quiet módja nem dobja el a `NEST_NFP_STATS_V1` sort, ha engine stats capture aktív.
5. A `summary.json` tartalmaz `engine_stats` blokkot raw és normalized al-blokkal.
6. A normalizált blokk tartalmazza legalább: `nfp_cache_hit_count`, `nfp_cache_miss_count`, `nfp_cache_entries_end`, `nfp_compute_count`, `candidate_generate_count`, `candidate_dedup_count`, `candidate_after_cap_count`, `can_place_call_count`, `sheet_spillover_count`, `effective_placer`, `actual_nfp_kernel`, `actual_narrow_phase`.
7. A Phase 1-re maradó cache mezők (`nfp_cache_clear_all_events`, `nfp_cache_peak_entries`) explicit `pending_phase1_fields` alatt szerepelnek, nem hamis értékként.
8. Parser unit tesztek zöldek.
9. Ha Rust fájl módosult, `cargo check -p nesting_engine` és releváns Rust teszt zöld; ha nem módosult Rust fájl, reportban rögzítve, hogy Rust kód érintetlen.
10. `./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t04_phase0_engine_stats_export.md` zöld.
11. Checklist és report elkészült Report Standard v2 szerint.

## Report elvárás

A reportban külön szerepeljen:

- A meglévő stats mezők auditja.
- Mely mezők kerültek be raw/normalized formában a summary-ba.
- A stderr/quiet policy pontos döntése.
- A parser hibamódjai.
- A Phase 1-re halasztott mezők listája.
- Futott parancsok és eredmények.
- DoD → Evidence Matrix a fenti DoD pontokra 1:1-ben.
