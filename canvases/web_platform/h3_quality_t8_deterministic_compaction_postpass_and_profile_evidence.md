# H3-Quality-T8 Determinisztikus compaction post-pass es profile evidence

## Funkcio
Ez a task a H3 quality lane nyolcadik lepese, es az **elso tenyleges layout-minoseg javito kor** a T1-T7 integracios munka utan.

A jelenlegi repo-helyzet T7 utan:
- a `nesting_engine_v2` backend mar valaszthato a worker/tool/benchmark vilagban;
- a quality-profile truth (`fast_preview`, `quality_default`, `quality_aggressive`) mar kanonikus registrybol jon;
- a profile-ok ma foleg a `placer`, `search`, `part_in_part` es SA parameterek szintjen hatnak;
- **nincs meg** olyan determinisztikus utolagos tomorites, amely ugyanazon sheet/allokacio mellett a lerakott elemeket kozelebb huzza, csokkenti a szetszort layoutot, es javitja a remnant/utilization jellegu metrikakat.

A felhasznaloi problema tovabbra is az, hogy a futas technikailag zold lehet, de a layout gyakran tul laza, soros jellegu es iparilag gyenge. A legkisebb, de mar valodi minosegi lepes most egy **determinista compaction post-pass**, nem uj domain reteg.

## Scope

### Benne van
- uj, explicit `compaction` runtime dimenzio a `nesting_engine_v2` quality-profile vilagban;
- Rust CLI bovitese uj kapcsoloval:
  - `--compaction off|slide`
  - default: `off`;
- determinisztikus, integer-only **post-placement compaction** a `nesting_engine` oldalon;
- a compaction a meglvo placements-en fut, es csak **monoton balra/le** (vagy ezzel ekvivalens, determinisztikusan dokumentalt iranypolicy) mozgatast vegezhet;
- a compaction nem valtoztathat:
  - sheet hozzarendelest,
  - part sorrendet,
  - rotaciot,
  - placed/unplaced tagsagot;
- a validalas a meglvo feasibility/can_place logikaval tortenjen, nem uj geometriai shortcut-tal;
- output/meta evidence a compactionrol;
- a `quality_default` / `quality_aggressive` profilokhoz ertelmes compaction policy bekotese;
- local quality summary + benchmark compare bovitese, hogy a compaction hatasa gepileg olvashato legyen;
- dedikalt smoke es targeted gate, amely valodi Supabase nelkul bizonyit.

### Nincs benne
- SQL migration vagy REST schema modositas;
- remnant/inventory domain munka;
- uj UI felulet;
- tobbfazisu local search / swap / ruin-recreate;
- part-in-part vagy NFP algoritmus ujrairasa;
- sheet-szam csokkentes garantalasa minden fixture-en;
- exact remnant polygon extraction.

## Talalt relevans fajlok / jelenlegi kodhelyzet
- `vrs_nesting/config/nesting_quality_profiles.py`
  - mar kanonikus registry, de jelenleg nincs `compaction` dimenzio.
- `api/services/run_snapshot_builder.py`
  - a snapshot mar explicit `quality_profile` truthot es `nesting_engine_runtime_policy` blokkot ir;
  - ezt kell additive modon boviteni `compaction` mezovel.
- `worker/main.py`
  - a runtime policyt mar registry/snapshot alapon resolve-olja es CLI args listat epit;
  - ha a registry CLI mapping bovitve van, a worker oldalon csak minimalis vagy nulla valtozas indokolt.
- `rust/nesting_engine/src/main.rs`
  - a `nest` subcommand ma `--placer`, `--search`, `--part-in-part`, SA flag-eket ismer;
  - `--compaction` meg nincs.
- `rust/nesting_engine/src/search/sa.rs`
  - SA search ma a konstruktiv `greedy_multi_sheet` evaluaciot hasznalja;
  - ha a compaction a placement eredmeny resze, a SA evaluacios utban is at kell adni a modot.
- `rust/nesting_engine/src/multi_bin/greedy.rs`
  - itt van a `MultiSheetResult`, a remnant proxy objective, es a sheetenkenti osszesites;
  - ez a legjobb hely a post-pass integraciora.
- `rust/nesting_engine/src/placement/blf.rs`
  - itt van a placement adatmodell, a rotate/translate helper logika es a placed extents helper;
  - a compaction implementationhoz valoszinuleg szukseges lesz nehany helper `pub(crate)` kivezetese vagy minimalis belso ujrafelhasznalasa.
- `rust/nesting_engine/src/export/output_v2.rs`
  - az `objective` blokk ma remnant metrikakat ad, a `meta` blokk csak determinism hash-et;
  - a compaction evidence-nek itt kell megjelennie additive modon.
- `scripts/trial_run_tool_core.py`
  - ma quality summary-t epit, de a v2 objective/metaszintu compaction evidence nincs teljesen kiemelve.
- `scripts/run_h3_quality_benchmark.py`
  - ma backend/profile matrixot tud, de a compactionhoz kotheto delta mezoket nem kezeli kulon.

## Konkret elvarasok

### 1. Vezess be kanonikus compaction policy-t a quality-profile registryben
A T7-ben bevezetett registry kapjon uj runtime dimenziot:
- `compaction`: `off|slide`

Minimum policy-dontes:
- `fast_preview` -> `compaction=off`
- `quality_default` -> `compaction=slide`
- `quality_aggressive` -> `compaction=slide`

Szabalyok:
- a registry maradjon az egyetlen source of truth;
- a snapshot runtime policy blokk ezt is hordozza;
- a CLI args mapping a registrybol jojjon, ne kulon worker-hardcodebol.

### 2. A Rust CLI kapjon uj `--compaction off|slide` kapcsolot
Módositsd a `rust/nesting_engine/src/main.rs` logikat ugy, hogy a `nest` subcommand kezelje:
- `--compaction off|slide`
- default: `off`

Kovetelmenyek:
- ismeretlen ertek -> fail-fast hiba;
- a `SUPPORTED_NEST_FLAGS`/help text frissuljon;
- a default baseline viselkedes maradjon kompatibilis, ha a flag nincs megadva.

### 3. Implementald a determinisztikus compaction post-pass-t
A compaction a placement eredmenyen fusson **ugyanazon sheeten belul**.

Kritikus szabalyok:
- nem helyezhet uj partot;
- nem mozgathat at masik sheetre;
- nem valtoztathat rotaciot;
- nem modosithatja a placed/unplaced darabszamot;
- csak olyan elmozdulas engedelyezett, amelyet a meglvo feasibility ut (`can_place`) ervenyesnek fogad el.

Javasolt elv (evidence-first, minimal-invaziv):
- sheetenkent, determinisztikus placement sorrendben dolgozz;
- minden placed itemre ideiglenesen vedd ki a collision indexbol;
- probald meg a jelenlegi poziciobol monoton modon **balra**, majd **le** (vagy a canvasban rogzitett egyertelmu alternatv sorrendben) a leheto legkozelebbi ervenyes poziciora huzni;
- a jeloltek ne teljes raster scanbol jojjenek, hanem determinisztikus boundary-alapu jelolthalmazbol, peldaul:
  - sheet minimum perem,
  - mar lerakott elemek AABB/placed extents hatarai,
  - aktualis pozicio;
- ha nincs jobb ervenyes pozicio, az elem marad a helyen.

Elfogadhato minosegi minimum:
- a post-pass **nem ronthatja** a primary objective-ot;
- azonos sheet count mellett az occupied envelope / remnant proxy / utilization ne legyen rosszabb a baseline-nal az erre keszitett fixture-en.

### 4. Adj explicit compaction evidence-t a v2 outputhoz
Az output v2 additive modon hordozzon compaction truthot.

Minimum elvaras:
- `meta.compaction` vagy ezzel ekvivalens blokk, amely legalabb ezeket tartalmazza:
  - `mode`
  - `applied`
  - `moved_items_count`
  - `occupied_extent_before`
  - `occupied_extent_after`

Fontos:
- a determinism hash contract maradjon placement-canonical view alapu;
- vagyis a compaction meta bovitese **nem** irhatja felul a hash-szabalyt.

### 5. Emeld be a compaction truthot a local quality summary / benchmark vilagba
A `scripts/trial_run_tool_core.py` es a `scripts/run_h3_quality_benchmark.py` kapja meg a compaction evidence-t ugy, hogy a profile-ok kozti kulonbseg geppel olvashato legyen.

Minimum mezok a quality summaryben vagy benchmark outputban:
- `remnant_value_ppm`
- `remnant_compactness_score_ppm`
- `compaction_mode`
- `compaction_applied`
- `compaction_moved_items_count`
- `occupied_extent_before_mm`
- `occupied_extent_after_mm`

A compare output legalabb ezeket tudja delta formaban jelenteni, ha rendelkezesre allnak:
- `remnant_value_ppm_delta`
- `occupied_extent_width_delta_mm`
- `occupied_extent_height_delta_mm`
- `compaction_moved_items_delta`

### 6. Keszits dedikalt fixture-t es smoke-ot
Kell egy kicsi, repo-beli v2 fixture, amin a compaction hatasa reprodukalhato.

Javasolt uj fixture:
- `poc/nesting_engine/f3_4_compaction_slide_fixture_v2.json`

Elv:
- az alap konstruktiv placer valid layoutot ad, de marad benne felesleges X/Y szoras;
- a `slide` post-pass ugyanazon sheet count es placed count mellett kisebb occupied extentet vagy jobb remnant score-t ad.

A dedikalt smoke legalabb ezt bizonyitsa:
- `--compaction off` vs `--compaction slide` futas ugyanazon fixture-en;
- mindket futas valid (`status=ok` vagy determinisztikusan elvart reszleges status);
- `slide` esetben a primary objective nem rosszabb;
- es legalabb egy explicit minosegi evidence jobb vagy nem rosszabb:
  - kisebb occupied extent, vagy
  - magasabb/equal remnant_value_ppm, vagy
  - magasabb/equal utilization.
- azonos seed mellett a `slide` futas hash-stabil.

### 7. Gate es dokumentacio
A tasknak legyen:
- targeted Rust teszt prefix, pl. `compaction_`;
- dedikalt smoke script;
- `scripts/check.sh` bovitese targeted compaction teszttel;
- dokumentacio frissites az architekturaban es az IO contractban.

## Erintett fajlok / celzott outputok
- `canvases/web_platform/h3_quality_t8_deterministic_compaction_postpass_and_profile_evidence.md`
- `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t8_deterministic_compaction_postpass_and_profile_evidence.yaml`
- `codex/prompts/web_platform/h3_quality_t8_deterministic_compaction_postpass_and_profile_evidence/run.md`
- `vrs_nesting/config/nesting_quality_profiles.py`
- `api/services/run_snapshot_builder.py`
- `rust/nesting_engine/src/main.rs`
- `rust/nesting_engine/src/placement/blf.rs`
- `rust/nesting_engine/src/multi_bin/greedy.rs`
- `rust/nesting_engine/src/search/sa.rs`
- `rust/nesting_engine/src/export/output_v2.rs`
- `poc/nesting_engine/f3_4_compaction_slide_fixture_v2.json`
- `scripts/trial_run_tool_core.py`
- `scripts/run_h3_quality_benchmark.py`
- `docs/nesting_engine/architecture.md`
- `docs/nesting_engine/io_contract_v2.md`
- `docs/nesting_quality/h3_quality_benchmark_harness.md`
- `scripts/check.sh`
- `scripts/smoke_h3_quality_t8_deterministic_compaction_postpass_and_profile_evidence.py`
- `codex/codex_checklist/web_platform/h3_quality_t8_deterministic_compaction_postpass_and_profile_evidence.md`
- `codex/reports/web_platform/h3_quality_t8_deterministic_compaction_postpass_and_profile_evidence.md`

## DoD
- letezik kanonikus `compaction` runtime policy a quality-profile registryben;
- a snapshot `nesting_engine_runtime_policy` blokk expliciten hordozza a compaction modot;
- a `nesting_engine` CLI ismeri a `--compaction off|slide` kapcsolot;
- a post-pass determinisztikus, integer-only, es nem valtoztat sheet/rotation/placed-unplaced truthot;
- a v2 output additive compaction evidence-t ad;
- a quality summary / benchmark output geppel olvashato compaction mezoket ad;
- van dedikalt fixture + smoke, ahol a `slide` mod legalabb egy minosegi evidence-ben jobb vagy nem rosszabb;
- targeted Rust tesztek PASS;
- `scripts/check.sh` bovitve van compaction gate-tel;
- a standard verify wrapper lefut, report + log frissul.

## Kockazat + rollback
- Kockazat:
  - a compaction post-pass veletlenul megszegi a feasibility szabalyokat;
  - a mozgatasi heuristika tul draga vagy nem determinisztikus lesz;
  - a `quality_default` profil viselkedese hirtelen nagyot valtozik.
- Mitigacio:
  - csak existing feasibility ut legyen az igazsagforras;
  - nincs uj random vagy float tie-break;
  - targeted fixture + smoke bizonyitsa a minosegi hatast;
  - a profile registryben a feature explicit `compaction` modon kapcsolhato.
- Rollback:
  - a CLI flag + profile registry + compaction post-pass egy task-commitben visszavonhato;
  - nincs migration/API schema kockazat.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h3_quality_t8_deterministic_compaction_postpass_and_profile_evidence.md`
- Feladat-specifikus minimum ellenorzes:
  - `cargo test --manifest-path rust/nesting_engine/Cargo.toml compaction_`
  - `python3 scripts/smoke_h3_quality_t8_deterministic_compaction_postpass_and_profile_evidence.py`
  - plusz a T7 regresszio smoke vagy egy ennel szukebb, profile-registryre epulo ellenorzes, ha a report szerint szukseges.
