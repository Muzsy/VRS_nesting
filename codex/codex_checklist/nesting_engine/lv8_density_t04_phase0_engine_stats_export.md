# T04 Checklist — lv8_density_t04_phase0_engine_stats_export

Pipálható DoD lista a canvas
[lv8_density_t04_phase0_engine_stats_export.md](../../../canvases/nesting_engine/lv8_density_t04_phase0_engine_stats_export.md)
alapján. Egy pont csak akkor pipálható, ha a bizonyíték a reportban szerepel
([codex/reports/nesting_engine/lv8_density_t04_phase0_engine_stats_export.md](../../reports/nesting_engine/lv8_density_t04_phase0_engine_stats_export.md)).

## Repo szabályok és T0x előzmények

- [x] `AGENTS.md`, `docs/codex/overview.md`, `docs/codex/yaml_schema.md`,
      `docs/codex/report_standard.md`, `docs/qa/testing_guidelines.md`,
      `development_plan_packing_density_20260515.md` beolvasva.
- [x] T00 outputok jelen, T01 / T02 / T03 reportok PASS.
- [x] T04 canvas + YAML beolvasva.

## Audit

- [x] `NfpPlacerStatsV1` mezők auditálva (`nfp_placer.rs:344-406`): minden szükséges
      mező jelen és `Serialize` derive-val rendelkezik.
- [x] `main.rs` `should_emit_nfp_stats()` + `NEST_NFP_STATS_V1` emission auditálva
      (`main.rs:627-648`).
- [x] `greedy_multi_sheet()` aggregáció auditálva (`greedy.rs:643,730,741,847`):
      `add_assign` + `nfp_cache_entries_end` kitöltés korrekt.
- [x] `cache.rs` `CacheStats` auditálva: csak `hits`, `misses`, `entries` — nincs
      `clear_all_events` / `peak_entries` (T08 scope).
- [x] `lv8_2sheet_claude_search.py` stderr / quiet path auditálva: T04 előtt
      `LV8_HARNESS_QUIET=1` esetén stderr `/dev/null` — stats elveszett volna.

## Engine stats bekötése

- [x] `NESTING_ENGINE_EMIT_NFP_STATS=1` beállítva az env-ben a T04/T06 mérési pathon.
- [x] `LV8_HARNESS_CAN_PLACE_PROFILE` harness-szinten kontrollált; default `1`
      a Phase 0 mérési pipeline-hoz.
- [x] Quiet mód (`capture_engine_stats = True`) esetén stderr mindig
      `solver_stderr.log` fájlba megy, nem `/dev/null`-ba.

## Parser és normalized summary

- [x] `STAT_PREFIX = "NEST_NFP_STATS_V1 "` konstans hozzáadva.
- [x] `_normalize_engine_stats()` helper hozzáadva: stabil Phase 0 neveket ad
      (`nfp_cache_hit_count`, `nfp_cache_miss_count`, stb.).
- [x] `_parse_engine_stats_from_stderr()` helper hozzáadva: kezeli a hiányzó sort,
      a több sort és az invalid JSON-t; `available`, `parse_error`, `raw`, `normalized`,
      `pending_phase1_fields` mezőkkel.
- [x] `summary["engine_stats"]` bekötve a `run_one()` végén.
- [x] `pending_phase1_fields` tartalmazza `nfp_cache_clear_all_events` és
      `nfp_cache_peak_entries` mezőket minden esetben.

## Teszt

- [x] `tests/test_lv8_density_engine_stats_export.py` létrehozva (18 teszt).
- [x] `python3 -m pytest tests/test_lv8_density_engine_stats_export.py -q`
      → 18 passed.

## Opcionális smoke

- [x] Kis-fixture smoke futtatva:
      `NESTING_ENGINE_EMIT_NFP_STATS=1 rust/nesting_engine/target/release/nesting_engine nest --placer nfp < poc/nesting_engine/f2_4_sa_quality_fixture_v2.json >/tmp/t04_stdout.json 2>/tmp/t04_stderr.log`
      → exit 0, `NEST_NFP_STATS_V1` sor jelen a stderr-ben.

## Tilalmak betartása

- [x] `rust/nesting_engine/src/nfp/cache.rs` érintetlen (T08 scope).
- [x] `vrs_nesting/config/nesting_quality_profiles.py` érintetlen (T02/T20 scope).
- [x] `worker/cavity_validation.py` érintetlen (T05 scope).
- [x] `search/sa.rs` érintetlen (T21 scope).
- [x] NFP algoritmus, cache struktúra, scoring nem változott.
- [x] Nincs hosszú LV8 benchmark futtatva.
- [x] Nincs Phase 2+ scoring / lookahead / beam / LNS funkció.

## Verifikáció

- [x] `python3 -m pytest tests/test_lv8_density_engine_stats_export.py -q` → 18 passed.
- [x] Rust fájl nem módosult — `cargo check` nem szükséges, reportban rögzítve.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t04_phase0_engine_stats_export.md`
      lefuttatva (eredmény a reportban az AUTO_VERIFY blokkban).
- [x] Report DoD → Evidence Matrix kitöltve (lásd a report 5) szekcióját).
