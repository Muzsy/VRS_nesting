# H3-Quality-T7 Quality profile-ok es runtime policy / snapshot integration

## Funkcio
Ez a task a H3 quality lane hetedik lepese.
A T6 ota a helyi trial-run tool, a benchmark runner es az A/B compare tooling mar
kepes explicit backend valasztasra es osszehasonlitasra. A kovetkezo hianyzo reteg
az, hogy a `nesting_engine_v2` futasnak legyen **kanonikus quality profile**
absztrakcioja, ne csak ad-hoc backend valtas.

Jelenleg a repoban:
- a `nesting_engine` CLI mar tud minoseget befolyasolo flag-eket (`--placer`,
  `--search`, `--part-in-part`, SA parameterek),
- a worker viszont csak `seed` + `time_limit` alapjan hivja a `nesting_engine_runner`-t,
- a snapshot `solver_config_jsonb` meg nem hordoz stabil quality-profile szerzodest,
- a local tool / benchmark meg nem tud **profile-szinten** futni es bizonyitani.

Ez a task ezt a gapet zarja le ugy, hogy a profile-ok egy kozos, audit-olhato
regiszterben legyenek definialva, a worker determinisztikusan ugyanazt a mappinget
hasznalja, es a local benchmarking mar profile-szinten is osszehasonlithato legyen.

## Scope

### Benne van
- kozos `quality profile` registry a `nesting_engine_v2` runtime-hoz;
- minimum harom kanonikus profil:
  - `fast_preview`
  - `quality_default`
  - `quality_aggressive`
- snapshot / `solver_config_jsonb` szerzodes bovitese ugy, hogy a futasi inputban
  legyen explicit `quality_profile` es a profile-bol szarmaztatott v2 runtime policy;
- worker runtime policy, amely a profile alapjan a `nesting_engine_runner`-nek
  megfelelo CLI flag-eket adja at;
- `engine_meta` / quality truth bovitese requested vs effective profile mezokkel;
- local tool + benchmark selector a profile-okhoz, ugy hogy ugyanaz a case mar
  profile-szinten is futtathato es diffelheto legyen;
- dedikalt smoke, amely valodi platform / Supabase / solver nelkul bizonyitja a
  profile registry, worker mapping es local tooling viselkedeset.

### Nincs benne
- SQL migration vagy uj DB schema;
- `run_configs` REST schema bovitese uj mezo(k)kel;
- project-level strategy selection teljes bekotese a quality profile vilagba;
- minosegi algoritmus tuning a Rust motorban;
- H3-E4 remnant / inventory;
- UI product rollout.

## Talalt relevans fajlok / jelenlegi kodhelyzet
- `vrs_nesting/runner/nesting_engine_runner.py`
  - jelenleg csak `--input`, `--seed`, `--time-limit`, `--run-root`,
    `--nesting-engine-bin` argumentumokat ismeri;
  - a Rust `nesting_engine` CLI minosegi flagjeit meg nem kozevetiti.
- `worker/main.py`
  - mar tud `sparrow_v1` vs `nesting_engine_v2` backendet valasztani;
  - az `engine_meta.json` ma csak backend/contract/default profile truthot ir.
- `api/services/run_snapshot_builder.py`
  - `solver_config_jsonb` ma seed/time_limit/rotation/kerf/spacing/margin adatot ad,
    de nincs explicit quality-profile szerzodes.
- `scripts/trial_run_tool_core.py`
  - mar viszi a backend truthot es quality summary evidence-t;
  - profile valasztas meg nincs.
- `scripts/run_trial_run_tool.py`
  - CLI wrapper a local toolhoz; profile argumentum meg nincs.
- `scripts/trial_run_tool_gui.py`
  - GUI wrapper a local toolhoz; profile selector meg nincs.
- `scripts/run_h3_quality_benchmark.py`
  - backend matrix mar van;
  - profile matrix meg nincs.
- `docs/nesting_quality/h3_quality_benchmark_harness.md`
  - benchmark harness doksi; profile lane meg nincs lezarva.
- `scripts/smoke_h3_quality_t6_local_tool_backend_selector_and_ab_compare.py`
  - jo minta a local-tool + benchmark fake smoke-okhoz.

## Konkret elvarasok

### 1. Vezess be kozos quality-profile regisztert
Legyen egy kozos, importalhato modul, amely definialja a kanonikus quality
profile-okat es azok nesting-engine mappingjet.

Minimum profilok:
- `fast_preview`
  - `placer=blf`
  - `search=none`
  - `part_in_part=off`
- `quality_default`
  - `placer=nfp`
  - `search=sa`
  - `part_in_part=auto`
  - SA parameterek csak akkor legyenek explicit, ha a profile szerzodes ezt igenyli;
    kulonben a runner/engine default maradhat.
- `quality_aggressive`
  - `placer=nfp`
  - `search=sa`
  - `part_in_part=auto`
  - legalabb egy, determinisztikusan rogzitett erositesi kulonbseg legyen a
    `quality_default`-hoz kepest (pl. nagyobb `sa_iters`, vagy explicitebb SA params).

Szabalyok:
- a registry legyen egyetlen source of truth;
- ugyanazt a mappinget hasznalja a worker, a local tool es a benchmark harness;
- a profile megnevezesek stabil, emberileg is ertheto stringek legyenek.

### 2. A snapshot / solver_config kapjon explicit quality-profile truthot
A `run_snapshot_builder` a `solver_config_jsonb`-be irjon explicit quality truthot.
Minimum:
- `quality_profile`
- `engine_backend_hint` vagy ezzel ekvivalens mező **csak akkor**, ha a task ezt
  tisztan es schema-bontas nelkul tudja bevezetni;
- a profile-bol derivalt, nesting-engine specifikus runtime policy blokk, amelyet a
  worker mar kozvetlenul fel tud hasznalni.

Fontos:
- ne legyen migration;
- a snapshot builder defaultban is stabil, determinisztikus erteket adjon;
- a T3/T4/T5/T6 truth ne torjon el.

### 3. A worker a profile alapjan epitse a v2 runner invokaciot
A `worker/main.py` es a `nesting_engine_runner.py` kozti hataron jelenjen meg a
profile mapping.

Kotelezo minimum:
- a `nesting_engine_runner.py` tudjon opcionisan quality flag-eket tovabbitani a
  Rust CLI fele (`--placer`, `--search`, `--part-in-part`, plusz relevans SA flag-ek);
- a worker a resolved quality profile alapjan epitse fel ezeket a flag-eket;
- `engine_meta.json` tartalmazza legalabb:
  - `requested_engine_profile`
  - `effective_engine_profile`
  - `engine_profile_match`
  - `nesting_engine_cli_args` (vagy ezzel ekvivalens, audit-olhato mezot)

Szabaly:
- a profile hatas jelen taskban a `nesting_engine_v2` utra vonatkozik;
- `sparrow_v1` esetben a worker/profile truth ne hazudjon hatast: vagy explicit
  noop-kent jelezze, vagy fail-fast validaljon. A dontes legyen egyertelmu es
  dokumentalt a reportban.

### 4. A local tool es benchmark runner tudjon profile-szinten futni
A T6-ban bevezetett backend selector mellett jelenjen meg a quality-profile selector is.

Minimum:
- a core/CLI/GUI kapjon explicit `quality_profile` inputot;
- a benchmark runner tudjon case x profile matrixot futtatni legalabb a
  `nesting_engine_v2` backenddel;
- convenience compare mod is lehet, de nem kotelezo; a lenyeg, hogy a profile-ok
  kozti kulonbseg gepileg olvashato legyen;
- a `quality_summary.json` es/vagy benchmark output jelezze a requested vs effective
  profile truthot;
- legalabb a `sheet_count`, `utilization_pct`, `runtime_sec`, `nonzero_rotation_count`
  mezok profile-szintuen osszehasonlithatok legyenek.

Fontos:
- ne allits optimalitast;
- csak evidence-first kulonbseget jelents.

### 5. Keszits dedikalt smoke-ot
A smoke bizonyitsa legalabb:
- a profile registry stabil es a vart preseteket adja;
- a worker a megfelelo nesting-engine CLI argokat allitja elo legalabb a harom
  profilra;
- a snapshot builder default / explicit quality-profile truthot ad;
- a local tool config normalizalas profile mezot is hordoz;
- a benchmark runner profile matrixot tud epiteni `--plan-only` modban;
- valodi Supabase, worker processz es solver nelkul is PASS.

## Erintett fajlok / celzott outputok
- `canvases/web_platform/h3_quality_t7_quality_profiles_and_run_config_integration.md`
- `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t7_quality_profiles_and_run_config_integration.yaml`
- `codex/prompts/web_platform/h3_quality_t7_quality_profiles_and_run_config_integration/run.md`
- `vrs_nesting/config/nesting_quality_profiles.py`
- `vrs_nesting/runner/nesting_engine_runner.py`
- `api/services/run_snapshot_builder.py`
- `worker/main.py`
- `scripts/trial_run_tool_core.py`
- `scripts/run_trial_run_tool.py`
- `scripts/trial_run_tool_gui.py`
- `scripts/run_h3_quality_benchmark.py`
- `docs/nesting_quality/h3_quality_benchmark_harness.md`
- `scripts/smoke_h3_quality_t7_quality_profiles_and_run_config_integration.py`
- opcionlisan, ha tenyleg szukseges regresszio miatt:
  - `scripts/smoke_trial_run_tool_tkinter_gui.py`
- `codex/codex_checklist/web_platform/h3_quality_t7_quality_profiles_and_run_config_integration.md`
- `codex/reports/web_platform/h3_quality_t7_quality_profiles_and_run_config_integration.md`

## DoD
- letezik kozos quality-profile registry a kanonikus presetekkel;
- a snapshot `solver_config_jsonb` explicit quality-profile truthot hordoz;
- a worker a resolved profile alapjan epiti a `nesting_engine_runner` CLI flagjeit;
- az `engine_meta` es a quality truth requested vs effective profile mezoket ad;
- a local tool es a benchmark runner profile-szinten is tud futni;
- legalabb egy plan-only vagy fake compare output profile-szintu kulonbseget mutat;
- a dedikalt smoke zold;
- a standard verify wrapper lefut, report + log frissul.

## Kockazat + rollback
- Kockazat:
  - a profile registry es a worker/runtime policy konnyen szetcsuszhat;
  - a `sparrow_v1` es `nesting_engine_v2` profile jelentese felreertheto lehet;
  - a benchmark runner output schema gyorsan nohet.
- Mitigacio:
  - egyetlen kozos profile-registry legyen;
  - a reportban explicit nevezd meg, hogyan kezeli a task a `sparrow_v1` + profile
    kombinaciot;
  - a compare output additive legyen.
- Rollback:
  - a shared profile module + worker + local tool + benchmark diff egy task-commitban
    visszavonhato;
  - nincs DB schema / migration kockazat.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h3_quality_t7_quality_profiles_and_run_config_integration.md`
- Feladat-specifikus ellenorzes minimum:
  - `python3 -m py_compile vrs_nesting/config/nesting_quality_profiles.py vrs_nesting/runner/nesting_engine_runner.py api/services/run_snapshot_builder.py worker/main.py scripts/trial_run_tool_core.py scripts/run_trial_run_tool.py scripts/trial_run_tool_gui.py scripts/run_h3_quality_benchmark.py scripts/smoke_h3_quality_t7_quality_profiles_and_run_config_integration.py`
  - `python3 scripts/smoke_h3_quality_t7_quality_profiles_and_run_config_integration.py`
- Ajanlott regresszio:
  - `python3 scripts/smoke_h3_quality_t6_local_tool_backend_selector_and_ab_compare.py`
  - `python3 scripts/smoke_trial_run_tool_tkinter_gui.py` (ha erintett)

## Kapcsolodasok
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/nesting_quality/nesting_quality_konkret_feladatok.md`
- `worker/main.py`
- `vrs_nesting/runner/nesting_engine_runner.py`
- `api/services/run_snapshot_builder.py`
- `scripts/trial_run_tool_core.py`
- `scripts/run_trial_run_tool.py`
- `scripts/trial_run_tool_gui.py`
- `scripts/run_h3_quality_benchmark.py`
- `docs/nesting_quality/h3_quality_benchmark_harness.md`
