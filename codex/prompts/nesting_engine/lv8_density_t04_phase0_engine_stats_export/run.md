# LV8 Density T04 — Phase 0 engine stats export
TASK_SLUG: lv8_density_t04_phase0_engine_stats_export

## Szerep

Senior Python/Rust benchmark-hygiene agent vagy. A feladatod a Phase 0 engine stats export bekötése a meglévő VRS Nesting kódba. Nem algoritmust fejlesztesz, hanem a már létező `NEST_NFP_STATS_V1` stats sort teszed a későbbi T06 shadow run számára stabilan elérhetővé a `summary.json`-ban.

## Kötelező források

Olvasd el futás előtt:

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `codex/reports/nesting_engine/development_plan_packing_density_20260515.md`
- `canvases/nesting_engine/lv8_density_task_index.md`
- `codex/prompts/nesting_engine/lv8_density_master_runner.md`
- `codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md`
- `codex/reports/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md`
- `codex/reports/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.md`
- `canvases/nesting_engine/lv8_density_t04_phase0_engine_stats_export.md`
- `codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t04_phase0_engine_stats_export.yaml`

Előfeltétel: T03 report státusza PASS vagy PASS_WITH_NOTES legyen. Ha nem az, STOP és T04 report `FAIL/BLOCKED`.

## Fontos scope határok

T04-ben tilos:

- `rust/nesting_engine/src/nfp/cache.rs` módosítása — T08 scope.
- `vrs_nesting/config/nesting_quality_profiles.py` módosítása — T02/T20 scope.
- `worker/cavity_validation.py` módosítása — T05 scope.
- `search/sa.rs` módosítása — T21 scope.
- Phase 2+ scoring / lookahead / beam / LNS implementálása.
- Hosszú LV8 benchmark mátrix futtatása.

T04-ben elsődleges módosítás:

- `scripts/experiments/lv8_2sheet_claude_search.py`
- `tests/test_lv8_density_engine_stats_export.py`
- T04 checklist/report

Rust fájlhoz csak akkor nyúlj, ha audit alapján bizonyíthatóan hibás a meglévő stats emission vagy aggregáció. Ilyenkor a reportban külön indokold.

## Kiinduló audit parancsok

```bash
grep -n "struct NfpPlacerStatsV1\|nfp_cache_hits\|nfp_compute_calls\|can_place_profile\|candidates_before" rust/nesting_engine/src/placement/nfp_placer.rs

grep -n "NEST_NFP_STATS_V1\|NESTING_ENGINE_EMIT_NFP_STATS\|should_emit_nfp_stats" rust/nesting_engine/src/main.rs

grep -n "nfp_cache.stats\|NfpPlacerStatsV1\|add_assign" rust/nesting_engine/src/multi_bin/greedy.rs

grep -n "struct CacheStats\|fn stats\|clear_all" rust/nesting_engine/src/nfp/cache.rs

grep -n "stderr\|LV8_HARNESS_QUIET\|summary" scripts/experiments/lv8_2sheet_claude_search.py
```

Rögzítsd az audit eredményét a T04 reportban.

## Implementációs utasítás

### 1) Stats capture env bekötése

A `scripts/experiments/lv8_2sheet_claude_search.py` `run_one()` függvényében az engine subprocess env kapjon:

```python
env["NESTING_ENGINE_EMIT_NFP_STATS"] = "1"
```

A can_place profiling legyen harness controlled. Javasolt:

```python
if os.environ.get("LV8_HARNESS_CAN_PLACE_PROFILE", "1") == "1":
    env["NESTING_ENGINE_CAN_PLACE_PROFILE"] = "1"
else:
    env.pop("NESTING_ENGINE_CAN_PLACE_PROFILE", None)
```

Ha más defaultot választasz, indokold a reportban. A Phase 0 cél a mérhetőség, ezért a default `1` elfogadott.

### 2) Quiet stderr policy módosítása stats capture mellett

Jelenleg `LV8_HARNESS_QUIET=1` esetén stderr `/dev/null`-ba megy. Ez eldobná a `NEST_NFP_STATS_V1` sort.

Módosíts úgy, hogy stats capture aktív állapotban stderr mindig `solver_stderr.log` fájlba menjen, de ne konzolra. A T03 után a concave diag spam default off, ezért ez nem hozhatja vissza a régi stderr problémát.

Elfogadott minta:

```python
capture_engine_stats = True
if quiet and not capture_engine_stats:
    # régi devnull path
else:
    with stderr_path.open("wb") as ferr:
        proc = subprocess.run(..., stderr=ferr, ...)
```

### 3) Parser helper

Adj hozzá parse helper-t a harnesshez:

```python
STAT_PREFIX = "NEST_NFP_STATS_V1 "

def _parse_engine_stats_from_stderr(stderr_text: str) -> dict[str, Any]:
    ...
```

Hibamódok:

- nincs sor: `available=false`, `parse_error="missing_stats_line"`
- több sor: `available=false`, `parse_error` tartalmazza a darabszámot
- invalid JSON: `available=false`, `parse_error` tartalmazza az invalid_json jelzést
- 1 sor: `available=true`, raw + normalized kitöltve

### 4) Normalized stats mapping

A normalized mezők legalább:

```python
normalized = {
    "nfp_cache_hit_count": raw.get("nfp_cache_hits"),
    "nfp_cache_miss_count": raw.get("nfp_cache_misses"),
    "nfp_cache_entries_end": raw.get("nfp_cache_entries_end"),
    "nfp_compute_count": raw.get("nfp_compute_calls"),
    "candidate_generate_count": raw.get("candidates_before_dedupe_total"),
    "candidate_dedup_count": raw.get("candidates_after_dedupe_total"),
    "candidate_after_cap_count": raw.get("candidates_after_cap_total"),
    "can_place_call_count": raw.get("can_place_profile_calls"),
    "can_place_call_count_source": "can_place_profile_calls",
    "sheet_spillover_count": max(0, int(raw.get("sheets_used") or 0) - 1),
    "effective_placer": raw.get("effective_placer"),
    "actual_nfp_kernel": raw.get("actual_nfp_kernel"),
    "actual_narrow_phase": raw.get("actual_narrow_phase"),
}
```

Ha valamelyik mező nincs raw-ban, legyen `None`, ne hamisított 0. A hiányt a reportban dokumentáld.

### 5) Summary integráció

A `summary` dict kapja meg:

```python
stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace") if stderr_path.exists() else ""
engine_stats = _parse_engine_stats_from_stderr(stderr_text)
summary["engine_stats"] = engine_stats
```

A `pending_phase1_fields` mindig tartalmazza:

```python
[
    "nfp_cache_clear_all_events",
    "nfp_cache_peak_entries",
]
```

Ezek T08-ban jönnek, nem T04-ben.

## Teszt

Hozz létre:

- `tests/test_lv8_density_engine_stats_export.py`

Minimum tesztek:

1. Egy érvényes `NEST_NFP_STATS_V1` sor parse-olódik.
2. Hiányzó sor `available=false`.
3. Két stats sor `available=false` és parse error.
4. Invalid JSON `available=false`.
5. Normalized mapping mezők helyesek.
6. `pending_phase1_fields` tartalmazza a két Phase 1 mezőt.

Futtatás:

```bash
python3 -m pytest tests/test_lv8_density_engine_stats_export.py -q
```

## Opcionális kis-fixture smoke

Ha gyorsan fut a környezetben:

```bash
NESTING_ENGINE_EMIT_NFP_STATS=1 \
  cargo run --manifest-path rust/nesting_engine/Cargo.toml --bin nesting_engine -- \
  nest --placer nfp < poc/nesting_engine/f2_4_sa_quality_fixture_v2.json \
  >/tmp/t04_stdout.json 2>/tmp/t04_stderr.log

grep '^NEST_NFP_STATS_V1 ' /tmp/t04_stderr.log
```

Ha a parancs eltér, a reportban a ténylegesen használt parancs szerepeljen.

## Kötelező ellenőrzések

```bash
python3 -m pytest tests/test_lv8_density_engine_stats_export.py -q
```

Ha Rust fájlt módosítottál:

```bash
cargo check -p nesting_engine
```

Full gate:

```bash
./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t04_phase0_engine_stats_export.md
```

## Report és checklist

Hozd létre:

- `codex/codex_checklist/nesting_engine/lv8_density_t04_phase0_engine_stats_export.md`
- `codex/reports/nesting_engine/lv8_density_t04_phase0_engine_stats_export.md`

A report a Report Standard v2-t kövesse. A DoD → Evidence Matrix minden pontja legyen kitöltve.

## Definition of Done röviden

- T03 PASS/PASS_WITH_NOTES előfeltétel ellenőrizve.
- Meglévő stats flow auditálva.
- `NESTING_ENGINE_EMIT_NFP_STATS=1` bekötve a harness mérési pathon.
- Quiet mód nem dobja el a stats sort, ha capture aktív.
- `summary.json` tartalmaz `engine_stats` raw + normalized blokkot.
- Phase 1-re maradó cache mezők pendingként jelölve.
- Parser unit tesztek zöldek.
- Nincs algoritmus / cache / scoring változás.
- `./scripts/verify.sh --report ...` zöld.
