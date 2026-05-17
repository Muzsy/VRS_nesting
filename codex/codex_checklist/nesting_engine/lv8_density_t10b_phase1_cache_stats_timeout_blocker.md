# T10B Checklist — lv8_density_t10b_phase1_cache_stats_timeout_blocker

Pipálható DoD lista a canvas
[lv8_density_t10b_phase1_cache_stats_timeout_blocker.md](../../../canvases/nesting_engine/lv8_density_t10b_phase1_cache_stats_timeout_blocker.md)
alapján. Egy pont csak akkor pipálható, ha a bizonyíték a reportban szerepel
([codex/reports/nesting_engine/lv8_density_t10b_phase1_cache_stats_timeout_blocker.md](../../reports/nesting_engine/lv8_density_t10b_phase1_cache_stats_timeout_blocker.md)).

## Repo szabályok és T0x előzmények

- [x] `AGENTS.md`, `docs/codex/overview.md`, `docs/codex/yaml_schema.md`,
      `docs/codex/report_standard.md`, `docs/qa/testing_guidelines.md` beolvasva.
- [x] T10 report státusza `PASS_WITH_NOTES`, T10 döntési mezők:
      `phase2a_ready: NO`, `cache_stats_available_all_required_runs: NO`,
      `next_task_recommendation: benchmark blocker javítandó`.
- [x] T10B canvas + YAML beolvasva.

## Audit

- [x] T10 blocker oka reprodukálva és dokumentálva: `lv8_276` (276 part, 2-sheet) 60s
      time_limit alatt subprocess.TimeoutExpired → `NEST_NFP_STATS_V1` nem emittálódik.
- [x] `sa_guard` kis fixture 60s alatt lefut, `engine_stats.available=True`.
- [x] A matrix script korábban egységesen `time_limit_sec`-et adott minden family-nek.
- [x] `lv8_2sheet_claude_search.py` timeout mechanizmusa auditálva:
      `subprocess.run(timeout=time_limit_sec + 60)` kill-guard; ha megtelik → `timed_out=True`.

## Matrix script javítás

- [x] `LV8_FAMILY_PREFIX = "lv8_"` konstans hozzáadva.
- [x] `--lv8-time-limit-sec N` CLI paraméter: LV8 prefix family-ek külön, hosszabb time-limit-et
      kapnak.
- [x] `--stats-required-families LIST` CLI paraméter: advisory path-hoz szükséges family-ek
      (default: all required → advisory nem elérhető).
- [x] `--allow-lv8-timeout-without-stats 0|1` CLI paraméter: advisory path engedélyezése.
- [x] `run_matrix()` `lv8_time_limit_sec`, `stats_required_families`,
      `allow_lv8_timeout_without_stats` kwargs hozzáadva.
- [x] `compute_decision()` új mezők: `phase2a_unblocked`, `phase2a_ready_source`,
      `lv8_stats_available`, `sa_guard_stats_available`.
- [x] Háromágú döntési logika: `full_required_stats` | `smoke_stats_plus_lv8_advisory` |
      `blocked`.
- [x] `phase2a_ready` megmarad backward-compat aliasként.
- [x] Matrix JSON tartalmazza: `time_limit_sec`, `lv8_time_limit_sec`,
      `allow_lv8_timeout_without_stats`.
- [x] Matrix MD új fejlécek: `timed_out` oszlop; új döntési sorok az MD-ben.
- [x] Timeout/hiányzó stats row megmarad az outputban (nem törlődik).
- [x] `python3 -m py_compile scripts/experiments/lv8_phase1_cache_usage_matrix.py` → OK.

## Scope compliance

- [x] Rust engine nem módosult.
- [x] NFP cache-key nem módosult.
- [x] LRU implementáció nem történt.
- [x] Candidate scoring / bbox-growth nem kerül be.
- [x] Fake stats nem gyártatott.
- [x] `worker/cavity_validation.py` érintetlen.

## Tesztek

- [x] `tests/test_lv8_phase1_cache_usage_matrix.py` frissítve (16 teszt: 7 régi + 9 új).
- [x] Új tesztek lefedik: `lv8_time_limit_sec` átadást LV8 family-nek; sa_guard
      default limit; `phase2a_unblocked=False` missing stats esetén; advisory path;
      full set blokkolja advisory path-t; timeout row megmarad; `lv8/sa_guard_stats_available`
      külön mezők; `full_required_stats` path; matrix JSON lv8 time limit rögzítve.
- [x] `python3 -m pytest tests/test_lv8_phase1_cache_usage_matrix.py` → **16 passed**.

## Smoke run

- [x] T10B smoke run lefutott:
      `--time-limit-sec 60 --lv8-time-limit-sec 180 --seed 42 --profiles quality_default_no_sa_shadow,quality_aggressive_no_sa_shadow`
- [x] Eredmény rögzítve a reportban és `lv8_phase1_cache_usage_result.md`-ben.
