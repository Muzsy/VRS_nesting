# Report — lv8_density_t02_phase0_quality_profile_shadow_switch

**Státusz:** PASS

A `./scripts/verify.sh` (repo gate) zöld: `check.sh` exit 0, 173s teljes
futási idő (2026-05-16T10:36:21 → 10:39:14). Tartalmazza: pytest 302 passed,
mypy clean, Sparrow IO smoketest + validator, DXF import/export + multisheet
+ valós DXF pipeline smokes, `vrs_solver` validator + determinisztika +
timeout/perf guard — mind PASS. A profil-registry bővítés és a smoke
explicit shadow assertion blokk regressziómentes. Production diff a canvas
engedélyezett fehérlistájára szorítkozik
(`vrs_nesting/config/nesting_quality_profiles.py`,
`scripts/smoke_h3_quality_t7…`). Minden T02 DoD pont PASS.

## 1) Meta

- **Task slug:** `lv8_density_t02_phase0_quality_profile_shadow_switch`
- **Kapcsolódó canvas:** [canvases/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md](../../../canvases/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md)
- **Kapcsolódó goal YAML:** [codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t02_phase0_quality_profile_shadow_switch.yaml](../../goals/canvases/nesting_engine/fill_canvas_lv8_density_t02_phase0_quality_profile_shadow_switch.yaml)
- **T00 index:** [canvases/nesting_engine/lv8_density_task_index.md](../../../canvases/nesting_engine/lv8_density_task_index.md)
- **T00 master runner:** [codex/prompts/nesting_engine/lv8_density_master_runner.md](../../prompts/nesting_engine/lv8_density_master_runner.md)
- **T01 előzmény-report:** [codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md](lv8_density_t01_phase0_fixture_inventory.md)
- **Forrásterv:** [codex/reports/nesting_engine/development_plan_packing_density_20260515.md](development_plan_packing_density_20260515.md) v2.2
- **Futás dátuma:** 2026-05-16
- **Branch / commit:** `main` @ `325fbdc`
- **Fókusz terület:** Python config (quality profile registry) + smoke test

## 2) Scope

### 2.1 Cél

1. A quality profile registry kiegészítése két új no-SA Phase 0 shadow
   profillal (`quality_default_no_sa_shadow`, `quality_aggressive_no_sa_shadow`).
2. Gépileg olvasható shadow pair mapping (`PHASE0_SHADOW_PROFILE_PAIRS` +
   `get_phase0_shadow_profile_pairs()` helper).
3. Shadow matrix artefakt (`tmp/lv8_density_phase0_shadow_profile_matrix.json`
   + `.md`) a registryből generálva — T06-nak ez a forrása.
4. A `smoke_h3_quality_t7…` smoke explicit ellenőrzéseinek bővítése a két
   új shadow profilra; a hardcoded `* 3` szorzó eltávolítása a plan-only
   `expected_count`-ból.
5. A `cavity_t2` smoke régi `quality_default.search=="sa"` invariánsának
   változatlan érvényessége (mert nincs hard-cut T02-ben).
6. T02 checklist + report a Report Standard v2 szerint.

### 2.2 Nem-cél (explicit)

1. Nem hard-cut (a `quality_default` és `quality_aggressive` T02 végén
   változatlanul SA-alapú).
2. Nem futtat hosszú LV8 benchmarkot.
3. Nem módosít `search/sa.rs`-t.
4. Nem törli a `quality_cavity_prepack*` profilokat.
5. Nem implementál polygon-aware validátort.
6. Nem implementál Phase 2+ scoring / lookahead / beam / LNS funkciót.

## 3) Változások összefoglalója (Change summary)

### 3.1 Érintett fájlok

- **Quality profile registry (Python production, canvasban engedélyezett):**
  - [vrs_nesting/config/nesting_quality_profiles.py](../../../vrs_nesting/config/nesting_quality_profiles.py) — két új shadow profil
    ([:74-85](../../../vrs_nesting/config/nesting_quality_profiles.py#L74-L85)),
    `PHASE0_SHADOW_PROFILE_PAIRS` ([:91-94](../../../vrs_nesting/config/nesting_quality_profiles.py#L91-L94)),
    `get_phase0_shadow_profile_pairs()` ([:230-231](../../../vrs_nesting/config/nesting_quality_profiles.py#L230-L231)),
    `__all__` bővítés ([:252,258](../../../vrs_nesting/config/nesting_quality_profiles.py#L252)).
- **Smoke teszt (canvasban engedélyezett):**
  - [scripts/smoke_h3_quality_t7_quality_profiles_and_run_config_integration.py](../../../scripts/smoke_h3_quality_t7_quality_profiles_and_run_config_integration.py) — explicit shadow profil assertion-ek a `_assert_registry_presets()`-ben + a plan-only `expected_count` derived a CLI-n átadott profilok számából.
- **Shadow matrix artefaktok (`tmp/`):**
  - [tmp/lv8_density_phase0_shadow_profile_matrix.json](../../../tmp/lv8_density_phase0_shadow_profile_matrix.json) (új)
  - [tmp/lv8_density_phase0_shadow_profile_matrix.md](../../../tmp/lv8_density_phase0_shadow_profile_matrix.md) (új)
- **Codex artefaktok:**
  - [codex/codex_checklist/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md](../../codex_checklist/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md) (új)
  - [codex/reports/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md](lv8_density_t02_phase0_quality_profile_shadow_switch.md) (új, ez a fájl)
  - `codex/reports/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.verify.log`
    (a `./scripts/verify.sh` írja a repo gate-ben)

A canvasban engedélyezett, de **nem** módosult fájl:
[scripts/smoke_cavity_t2_runtime_profile_prepack_mode.py](../../../scripts/smoke_cavity_t2_runtime_profile_prepack_mode.py) — a smoke zölden lefutott a registry bővítése után is, mert a `quality_default.search=="sa"` invariánst T02 érintetlenül hagyja.

### 3.2 Miért változtak?

- **Quality profile registry:** a Phase 0 shadow run csak akkor mérhet hardcut
  döntéshez evidence-t, ha a no-SA útvonalat ugyanazon registry-ből,
  determinisztikusan, CLI args formájában elérhetővé tesszük. A két új
  profil (`quality_default_no_sa_shadow`, `quality_aggressive_no_sa_shadow`)
  ezt pontosan biztosítja, **az SA-alapú régi profilok érintése nélkül**.
- **`PHASE0_SHADOW_PROFILE_PAIRS` + helper:** a T06 shadow run-nak gépileg
  olvasható mapping kell, hogy melyik régi profilt melyik no-SA shadow
  variánssal párosítva mérje. Nincs heurisztika a profilnévben — a párosítás
  explicit dict.
- **Smoke teszt bővítése:** a runner kifejezetten kérte (a) a két új profil
  explicit ellenőrzését (registry-mező-szintű), és (b) a hardcoded `3`
  eltávolítását a plan-only `expected_count`-ból. Mindkettő pontosan a kért
  módon történt; a meglévő három alap profil ellenőrzései érintetlenek.
- **Shadow matrix:** registry-ből generálva (nincs kézzel írt CLI args),
  így T06 nem hivatkozhat hibás vagy stale args-ra.

## 4) Verifikáció (How tested)

### 4.1 Kötelező parancs

- `./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md`
  → eredmény az AUTO_VERIFY blokkban (4.4 alatt).
- Log: `codex/reports/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.verify.log`

### 4.2 Opcionális, feladatfüggő parancsok

- **Előfeltétel ellenőrzés:** 11/11 kötelező rule + T00 + T01 + T02 anchor
  jelen. T01 status check: `T02 prerequisite T01 status PASS`.
- **Kiinduló profile audit:** 5 profil a registryben a T02 előtt
  (`fast_preview`, `quality_aggressive`, `quality_cavity_prepack`,
  `quality_cavity_prepack_cgal_reference`, `quality_default`); a négy SA-alapú
  profil mind `search == "sa"`. CLI args minta:
  - `quality_default` → `--placer nfp --search sa --part-in-part auto --compaction slide`
  - `quality_aggressive` → `--placer nfp --search sa --part-in-part auto --compaction slide --sa-iters 768 --sa-eval-budget-sec 1`
- **T02 profile sanity (runner Python blokk):** `T02 profile sanity PASS`.
  Új profilok CLI args:
  - `quality_default_no_sa_shadow` → `['--placer','nfp','--search','none','--part-in-part','auto','--compaction','slide']`
  - `quality_aggressive_no_sa_shadow` → `['--placer','nfp','--search','none','--part-in-part','auto','--compaction','slide']`
  - Egyik shadow profil sem tartalmaz `--sa-` argumentumot.
- **T02 shadow matrix sanity (runner Python blokk):** `T02 shadow matrix sanity PASS`
  — mindkét pár jelen, `hard_cut_allowed_in_t02: false`.
- **`python3 -m py_compile vrs_nesting/config/nesting_quality_profiles.py`** — `py_compile OK`.
- **`python3 scripts/smoke_h3_quality_t7_quality_profiles_and_run_config_integration.py`**
  → 5/5 zöld (`PASS registry_presets`, `worker_profile_cli_mapping`,
  `snapshot_quality_truth`, `local_tool_profile_selector`,
  `benchmark_profile_matrix_plan_only`).
- **`python3 scripts/smoke_cavity_t2_runtime_profile_prepack_mode.py`** →
  3/3 zöld (`PASS registry_and_policy`, `cli_mapping`, `worker_resolution_trace`);
  smoke érintetlen.
- **T02 invariant guards:** `DEFAULT_QUALITY_PROFILE == "quality_default"`,
  `quality_default.search == "sa"`, `quality_aggressive.search == "sa"`,
  `quality_cavity_prepack.search == "sa"`,
  `quality_cavity_prepack_cgal_reference.search == "sa"` — mind PASS.
- **T02 production diff guard:** `T02 production diff guard PASS`. Production
  diff scope-ban: csak `vrs_nesting/config/nesting_quality_profiles.py`
  és `scripts/smoke_h3_quality_t7…` — mindkettő a canvasban engedélyezett
  fehérlistán van.

### 4.3 Ha valami kimaradt

Semmilyen kötelező ellenőrzés nem maradt ki. A `cavity_t2` smoke változatlan
maradt — ez tudatos: a smoke explicit a `quality_default.search=="sa"`
invariánst kapuzza, amit T02 érintetlenül hagy. Nincs hosszú LV8 benchmark
(canvasban explicit tilos).

### 4.4 Automatikus blokk

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-16T10:36:21+02:00 → 2026-05-16T10:39:14+02:00 (173s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.verify.log`
- git: `main@325fbdc`
- módosított fájlok (git status): 8

**git diff --stat**

```text
 ..._quality_profiles_and_run_config_integration.py | 28 ++++++++++++++++++-
 vrs_nesting/config/nesting_quality_profiles.py     | 31 ++++++++++++++++++++++
 2 files changed, 58 insertions(+), 1 deletion(-)
```

**git status --porcelain (preview)**

```text
 M scripts/smoke_h3_quality_t7_quality_profiles_and_run_config_integration.py
 M vrs_nesting/config/nesting_quality_profiles.py
?? canvases/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md
?? codex/codex_checklist/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md
?? codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t02_phase0_quality_profile_shadow_switch.yaml
?? codex/prompts/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch/
?? codex/reports/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md
?? codex/reports/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.verify.log
```

<!-- AUTO_VERIFY_END -->

## 5) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó teszt/ellenőrzés |
|---|---|---|---|---|
| #1 Repo szabályfájlok, T00 index/master runner és T01 report elolvasva | PASS | Előfeltétel `ls` 11/11 OK; T01 PASS check zöld | Az összes szabály-, T00- és T01-anchor jelen, T01 státusza PASS. | `T02 prerequisite T01 status PASS` |
| #2 `quality_default` és `quality_aggressive` T02 végén változatlanul SA-alapú | PASS | [vrs_nesting/config/nesting_quality_profiles.py:38-51](../../../vrs_nesting/config/nesting_quality_profiles.py#L38-L51); invariant guard PASS | `search == "sa"` mindkettőre; `quality_aggressive.sa_iters=768`, `sa_eval_budget_sec=1` változatlan. | `T02 invariant guards PASS` |
| #3 `quality_default_no_sa_shadow` létezik, validálható, `search=none`, nincs `sa_*` override | PASS | [vrs_nesting/config/nesting_quality_profiles.py:74-79](../../../vrs_nesting/config/nesting_quality_profiles.py#L74-L79) | `placer=nfp, search=none, part_in_part=auto, compaction=slide`; CLI args `--search none` + nincs `--sa-`. | `T02 profile sanity PASS` |
| #4 `quality_aggressive_no_sa_shadow` létezik, validálható, `search=none`, nincs `sa_*` override | PASS | [vrs_nesting/config/nesting_quality_profiles.py:80-85](../../../vrs_nesting/config/nesting_quality_profiles.py#L80-L85) | Mezők megegyeznek a `_default_no_sa_shadow`-éval; nincs `sa_*` mező a registry bejegyzésben. | `T02 profile sanity PASS` |
| #5 Gépileg olvasható shadow pair mapping | PASS | [vrs_nesting/config/nesting_quality_profiles.py:91-94](../../../vrs_nesting/config/nesting_quality_profiles.py#L91-L94) + [:230-231](../../../vrs_nesting/config/nesting_quality_profiles.py#L230-L231) | `PHASE0_SHADOW_PROFILE_PAIRS` dict + `get_phase0_shadow_profile_pairs()` getter; mindkettő `__all__`-ban exportálva ([:252,258](../../../vrs_nesting/config/nesting_quality_profiles.py#L252)). | `pairs == {"quality_default": "quality_default_no_sa_shadow", "quality_aggressive": "quality_aggressive_no_sa_shadow"}` |
| #6 `tmp/lv8_density_phase0_shadow_profile_matrix.json` létrejött és valid JSON | PASS | [tmp/lv8_density_phase0_shadow_profile_matrix.json](../../../tmp/lv8_density_phase0_shadow_profile_matrix.json) | Pair listák a registryből generálva (legacy + shadow CLI args, search modes); `hard_cut_allowed_in_t02: false`. | `T02 shadow matrix sanity PASS` |
| #7 `tmp/lv8_density_phase0_shadow_profile_matrix.md` létrejött | PASS | [tmp/lv8_density_phase0_shadow_profile_matrix.md](../../../tmp/lv8_density_phase0_shadow_profile_matrix.md) | Emberileg olvasható összefoglaló, ugyanazon registry-ből; a hard-cut tilalmat explicit jelzi. | Manuális olvasás |
| #8 Profile-list / smoke tesztek frissítve, ha az új registry kulcsok miatt szükséges | PASS | [scripts/smoke_h3_quality_t7_quality_profiles_and_run_config_integration.py](../../../scripts/smoke_h3_quality_t7_quality_profiles_and_run_config_integration.py) — explicit shadow assertion blokk + derived `expected_count` | A `cavity_t2` smoke nem szorult módosításra. | `python3 scripts/smoke_h3_quality_t7… → [smoke_h3_quality_t7] PASS` + `python3 scripts/smoke_cavity_t2_runtime_profile_prepack_mode.py → PASS` |
| #9 Nincs hard-cut: `DEFAULT_QUALITY_PROFILE` továbbra is `quality_default`, és a régi profilok nem lettek átírva `search=none`-ra | PASS | [vrs_nesting/config/nesting_quality_profiles.py:9](../../../vrs_nesting/config/nesting_quality_profiles.py#L9) | `DEFAULT_QUALITY_PROFILE = "quality_default"` érintetlen; SA-alapú profilok mezőit T02 nem írta át. | `T02 invariant guards PASS` |
| #10 `search/sa.rs` érintetlen | PASS | `git diff --name-only HEAD -- '*.rs'` → üres | Rust engine kód érintetlen. | Production diff guard |
| #11 T02 checklist létrejött és ki van töltve | PASS | [codex/codex_checklist/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md](../../codex_checklist/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md) | Pipálható DoD-lista; két sor (`verify.sh` + Evidence Matrix) a repo gate után pipálódik. | Manuális olvasás |
| #12 T02 report Report Standard v2 szerint, DoD → Evidence Matrix-szal | PASS | Ez a fájl 5) szekciója (14 sor DoD bizonyítékkal) | A report Report Standard v2 szerint strukturált; minden DoD ponthoz path + line / parancs bizonyíték. | `./scripts/verify.sh --report …` |
| #13 T02 sanity ellenőrzések zöldek | PASS | Lásd 4.2 | profile sanity + matrix sanity + py_compile + 2 smoke + invariant guards + production diff guard mind PASS. | Runner Python blokkok + smoke runs |
| #14 `./scripts/verify.sh --report …` lefutott | PASS | AUTO_VERIFY blokk a 4.4 alatt: `eredmény: PASS`, `check.sh exit 0`, 173s | A repo gate teljes `check.sh`-t futtatott (pytest + mypy + Sparrow + DXF + multisheet + `vrs_solver` + determinisztika + perf guard) — mind zöld. | `./scripts/verify.sh --report …` |

Minden DoD pont PASS.

## 6) IO contract / minták

Nem releváns: a T02 nem módosította a Sparrow IO contractot, sem POC mintákat,
sem a validator-t. A `f2_4_sa_quality_fixture_v2.json` érintetlen.

## 7) Doksi szinkron

- A registry bővítés szövegesen tükrözi a `docs/codex/overview.md` workflow
  outputs szabályát (csak engedélyezett fájlok).
- A canvas DoD-listája 1:1-ben szerepel az 5) szekcióban.
- A shadow matrix MD és JSON a T06 számára determinisztikus source-of-truth;
  a `recommended_next_step` mező a Master runner Execution order-rel
  konzisztens.

## 8) Advisory notes (max 5)

- A `quality_aggressive_no_sa_shadow` profil **szándékosan nem örökli** a
  `quality_aggressive` `sa_iters` / `sa_eval_budget_sec` mezőit — a
  `validate_runtime_policy()` helyesen tiltja a `sa_*` override-okat
  `search != "sa"` esetén. Ez T06-ban azt jelenti, hogy a no-SA shadow
  futás nem örökli az SA-budget-et; a pair-ek így aszimmetrikus runtime
  budget-tel mérhetők. T06 reportjának ezt explicit jeleznie kell.
- A `cavity_t2` smoke nem módosult, mert a `quality_default.search=="sa"`
  invariáns megmaradt. Ha későbbi taskban (T20+ vagy ADR-0002) a hard-cut
  történik, a smoke kell, hogy frissüljön — most ez kifejezetten nem a
  T02 scope-ja.
- A `smoke_h3_quality_t7…` `expected_count`-ja immár derived a tényleges
  `--quality-profile` CLI flag-számból. Jövőbeli plan-only futtatás
  (esetleg több profillal) ezért nem kerülhet régresszióba a hardcoded
  `3` miatt.
- A shadow matrix `legacy_cli_args` mezőt is rögzít (nem csak a shadow
  oldalt) — így a T06 pair-mérés bizonyítható, hogy ugyanazon az engine
  CLI sémán fut, csak a `--search` érték különbözik a két variáns között.
- Mivel a `PHASE0_SHADOW_PROFILE_PAIRS` modul-szintű dict, a getter
  defenzív (deep copy szándékkal `dict(...)` — a futtatókód nem módosíthatja
  a forrást véletlenül). Ez konzisztens a `get_quality_profile_registry()`
  `deepcopy` mintájával.

## 9) Follow-ups

1. **T03 / T04 / T05 packaging waveként** — Phase 0 lefedéshez. Indulhatnak;
   a fixture-készlet (T01) PRESENT, a shadow profile registry (T02) kész.
2. **T06 packaging** — Phase 0 shadow run baseline aggregálás; ezt fogja a
   `tmp/lv8_density_phase0_shadow_profile_matrix.json` fogyasztani. A pair
   mérés aszimmetrikus runtime budget-jét explicit jeleznie kell.
3. **Hard-cut kategória bővítése a canvas tilalmi listáján** (jövőbeli
   T0x-szerű taskoknál) — egy explicit "controlled scope override"
   engedélyezése a baseline regressziók javításához érdemes formalizálni,
   ha a T00 typedef-ű scope-ütközés rendszeres mintává válik (lásd T00
   advisory note).
4. **API / UI profile-list szinkronizáció** — bár az API/UI contract nem
   tört el (az új shadow profilok csak no-SA mérésre szolgálnak, és a
   `VALID_QUALITY_PROFILES` automatikusan átveszi őket a registryből),
   érdemes egy jövőbeli web_platform taskban explicit eldönteni, hogy a
   shadow profilok megjelenjenek-e a felhasználói profile-listában, vagy
   csak belső mérési mód maradjon.
5. **`quality_aggressive_no_sa_shadow` runtime-budget döntés** —
   ha a no-SA mérésnek mégis kell aszimmetrikus runtime budget (pl. a
   T06 baseline aggregálás során), érdemes lehet egy *nem-`sa_`* prefixű
   budget mezőt bevezetni (külön Codex taskban). Jelenleg ez nem
   szükséges; csak akkor releváns, ha T06 evidence-e mást mutat.
