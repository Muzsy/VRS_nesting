# T02 Checklist — lv8_density_t02_phase0_quality_profile_shadow_switch

Pipálható DoD lista a canvas
[lv8_density_t02_phase0_quality_profile_shadow_switch.md](../../../canvases/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md)
alapján. Egy pont csak akkor pipálható, ha a bizonyíték a reportban szerepel
([codex/reports/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md](../../reports/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md)).

## Repo szabályok és T0x előzmények

- [x] `AGENTS.md`, `docs/codex/overview.md`, `docs/codex/yaml_schema.md`,
      `docs/codex/report_standard.md`, `docs/qa/testing_guidelines.md` beolvasva.
- [x] `codex/reports/nesting_engine/development_plan_packing_density_20260515.md`
      v2.2 beolvasva.
- [x] T00 outputok jelen: `canvases/nesting_engine/lv8_density_task_index.md`,
      `codex/prompts/nesting_engine/lv8_density_master_runner.md`.
- [x] T01 report PASS és beolvasva
      ([codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md](../../reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md)).
- [x] T02 canvas + YAML beolvasva.

## Registry bővítés

- [x] `quality_default` és `quality_aggressive` T02 végén változatlanul
      SA-alapú (`search == "sa"`).
- [x] `quality_default_no_sa_shadow` létezik
      ([vrs_nesting/config/nesting_quality_profiles.py:74-79](../../../vrs_nesting/config/nesting_quality_profiles.py#L74-L79));
      `placer=nfp, search=none, part_in_part=auto, compaction=slide`; nincs
      `sa_*` mező.
- [x] `quality_aggressive_no_sa_shadow` létezik
      ([vrs_nesting/config/nesting_quality_profiles.py:80-85](../../../vrs_nesting/config/nesting_quality_profiles.py#L80-L85));
      mezők ugyanazok; nincs `sa_*` mező.
- [x] Gépileg olvasható shadow pair mapping +`get_phase0_shadow_profile_pairs()`
      helper
      ([vrs_nesting/config/nesting_quality_profiles.py:91-94](../../../vrs_nesting/config/nesting_quality_profiles.py#L91-L94),
      [vrs_nesting/config/nesting_quality_profiles.py:230-231](../../../vrs_nesting/config/nesting_quality_profiles.py#L230-L231)).
- [x] `PHASE0_SHADOW_PROFILE_PAIRS` és `get_phase0_shadow_profile_pairs`
      bekerült az `__all__` listába
      ([vrs_nesting/config/nesting_quality_profiles.py:252,258](../../../vrs_nesting/config/nesting_quality_profiles.py#L252)).

## Shadow matrix artefakt

- [x] `tmp/lv8_density_phase0_shadow_profile_matrix.json` létrejött,
      registry-ből generálva (nincs kézzel írt CLI args).
- [x] `tmp/lv8_density_phase0_shadow_profile_matrix.md` létrejött (emberileg
      olvasható összefoglaló).
- [x] Mindkettő tartalmazza a `quality_default → quality_default_no_sa_shadow`
      és `quality_aggressive → quality_aggressive_no_sa_shadow` párokat,
      `hard_cut_allowed_in_t02: false` jelzéssel.

## Smoke / regression tesztek

- [x] `scripts/smoke_h3_quality_t7_quality_profiles_and_run_config_integration.py`
      explicit ellenőrzi a két új shadow profilt (registry blokk + `search="none"`
      + nincs `sa_*` mező).
- [x] `scripts/smoke_h3_quality_t7_quality_profiles_and_run_config_integration.py`
      `expected_count` számítása már nem hardcode-olja a `3`-at — a tényleges
      `--quality-profile` CLI flag-számból derivál.
- [x] `python3 scripts/smoke_h3_quality_t7_quality_profiles_and_run_config_integration.py`
      → zöld (PASS registry_presets / worker_profile_cli_mapping /
      snapshot_quality_truth / local_tool_profile_selector /
      benchmark_profile_matrix_plan_only).
- [x] `python3 scripts/smoke_cavity_t2_runtime_profile_prepack_mode.py` → zöld;
      a smoke nem szorult módosításra (a `quality_default.search=="sa"`
      invariáns érintetlen).

## Tilalmak betartása

- [x] `quality_default` és `quality_aggressive` **nem** lett átírva
      `search=none`-ra.
- [x] `DEFAULT_QUALITY_PROFILE` továbbra is `"quality_default"`.
- [x] `rust/nesting_engine/src/search/sa.rs` nem módosult (production diff
      guard ellenőrzi).
- [x] `quality_cavity_prepack` és `quality_cavity_prepack_cgal_reference`
      érintetlen (`search="sa"`, mezők változatlanok).
- [x] Nincs hosszú LV8 benchmark futtatva.
- [x] Nincs polygon-aware validátor implementálva.
- [x] Nincs Phase 2+ scoring / lookahead / beam / LNS funkció implementálva.
- [x] Production diff scope a canvasban engedélyezett 3 fájlra korlátozódik
      (a `cavity_t2` smoke valójában érintetlen, csak `nesting_quality_profiles.py`
      + `smoke_h3_quality_t7…` módosult).

## Verifikáció

- [x] T02 profile sanity zöld (kötelező runner Python blokk lefutott:
      `T02 profile sanity PASS`).
- [x] T02 shadow matrix sanity zöld (`T02 shadow matrix sanity PASS`).
- [x] `python3 -m py_compile vrs_nesting/config/nesting_quality_profiles.py`
      hibátlan.
- [x] T02 production diff guard zöld (`T02 production diff guard PASS`).
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md`
      lefutott. Eredmény: **PASS** (`check.sh` exit 0, 173s). 302 pytest pass,
      mypy clean, Sparrow + DXF + multisheet + `vrs_solver` determinisztika +
      timeout/perf guard zöld. Log:
      `codex/reports/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.verify.log`.
- [x] Report DoD → Evidence Matrix kitöltve (lásd a report 5) szekcióját);
      mind a 14 DoD pont PASS.
