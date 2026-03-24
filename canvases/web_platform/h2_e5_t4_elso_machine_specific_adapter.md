# H2-E5-T4 elso machine-specific adapter

## Funkcio
Ez a task a `config_jsonb` elso valos alkalmazasi pontja a web_platform H2
postprocess agaban.

A task helye a roadmapban: **H2-E5-T4 — Elso machine-specific adapter (opcionalis)**.

Ennek oka:
- a `H2-E5-T2` mar letrehozta a postprocessor profile/version truth reteget;
- a `H2-E5-T3` mar eloallitja a gepfuggetlen `manufacturing_plan_json`
  artifactot;
- a `config_jsonb` szukitett szerzodese adapter-konfig, vagyis a kesz,
  gepfuggetlen export gepi dialektusra forditasanak szabalyait hordozza;
- a reszletes lead-in/out technologiai rendszer **nem** ide tartozik, es mivel
  nincs veglegesitve, ebben a taskban kifejezetten tilos uj lead strategy/model
  tervezesebe belecsuszni.

Ez a task tehat **nem** a lead-in/out rendszer kidolgozasanak taskja.
Az kesobbi, kulon manufacturing-rule workstream lesz.
Ez a task a **kesz `config_jsonb` adapter-oldali alkalmazasa**.

## Elofeltetel / STOP szabaly
A task csak akkor futtathato, ha az alabbi harom adat konkretan rogzitesre kerult:

- `TARGET_MACHINE_FAMILY`
- `TARGET_ADAPTER_KEY`
- `TARGET_OUTPUT_FORMAT`

A jelen canvasban ezeket a task inditasakor ki kell tolteni.
Ha barmelyik hianyzik, a taskot **BLOCKED** allapotban kell lezarni, es tilos
celgep-csaladot, dialektust vagy adapter-kulcsot kitalalni.

Aktualis kitoltendo ertekek:
- `TARGET_MACHINE_FAMILY`: TODO
- `TARGET_ADAPTER_KEY`: TODO
- `TARGET_OUTPUT_FORMAT`: TODO

## Fejlesztesi reszletek

### Scope
- Benne van:
  - a `H2-E5-T3` gepfuggetlen export (`manufacturing_plan_json`) felhasznalasa
    machine-specific adapter bemenetekent;
  - a snapshotolt postprocessor selection es a
    `postprocessor_profile_versions.config_jsonb` tenyleges alkalmazasa;
  - a szukitett `config_jsonb` szerzodes validalasa es enforce-olasa;
  - pontosan **egy** konkret celgep-csaladra irt adapter implementalasa;
  - machine-ready artifact eloallitasa a `run_artifacts` retegen;
  - task-specifikus smoke az adapter-pathra.
- Nincs benne:
  - uj lead-in/out rendszer vagy technology pack;
  - `cut_rule_sets`, `cut_contour_rules`, contour classification vagy
    `manufacturing_plan_builder` atirasa;
  - live `project_manufacturing_selection` olvasasa exporthoz;
  - a gepfuggetlen exporter ujrairasa;
  - tobb adapteres plugin-rendszer altalanositasa;
  - frontend/export UI redesign.

### Talalt relevans fajlok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - itt szerepel a H2-E5-T4 optionalis machine-specific adapter task.
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
  - H2 postprocess irany, machine-neutral export es optionalis adapter-ag.
- `docs/web_platform/roadmap/h2_lezarasi_kriteriumok_es_h3_entry_gate.md`
  - rogziti, hogy a H2-E5-T4 optionalis, nem H2 blocker.
- `canvases/web_platform/h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.md`
  - a postprocessor profile/version truth es `config_jsonb` domain elozo lepese.
- `canvases/web_platform/h2_e5_t3_machine_neutral_exporter.md`
  - a gepfuggetlen export szerzodes es artifact-kiindulopont.
- `api/services/postprocessor_profiles.py`
  - a version-level `config_jsonb`, `adapter_key`, `output_format`,
    `schema_version` truth olvasasi pontja.
- `api/services/run_snapshot_builder.py`
  - a snapshotolt postprocessor selection metadata forrasa.
- `api/services/machine_neutral_exporter.py`
  - a machine-neutral export eloallitasa; erre kell epulnie az adapternek.
- `api/routes/runs.py`
  - generic artifact lista / signed URL flow; itt maradjon a machine-ready
    artifact is lathato.
- `supabase/migrations/20260322040000_h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.sql`
  - postprocessor domain es `config_jsonb` truth.
- `supabase/migrations/20260322043000_h2_e5_t3_machine_neutral_exporter.sql`
  - a `manufacturing_plan_json` artifact kind bevezetese.

### Konkret elvarasok

#### 1. A task a `manufacturing_plan_json` artifactra epuljon
Az adapter source-of-truth-ja a persisted H2 export-lanc legyen:
- `run_artifacts` alatt letrejott `manufacturing_plan_json` artifact;
- snapshotolt postprocessor metadata;
- a kapcsolt `postprocessor_profile_versions.config_jsonb`.

Tilos:
- live project selection olvasasa exporthoz;
- raw solver output vagy preview SVG adapter-bemenetkent;
- kozvetlen manufacturing truth atugrasa, ha a `manufacturing_plan_json`
  mar rendelkezésre all.

#### 2. A `config_jsonb` csak szuk adapter-konfigkent hasznalhato
Ebben a taskban a `config_jsonb`-t az alabbi, szukitett boundary szerint kell
ertelmezni:
- `program_format`
- `motion_output`
- `coordinate_mapping`
- `command_map`
- `lead_output` (csak capability/mapping)
- `artifact_packaging`
- `capabilities`
- `fallbacks`
- `export_guards`
- opcionálisan `process_mapping`

Tilos a `config_jsonb`-be vagy az adapterlogikaba visszacsempeszni:
- lead strategiat;
- anyag/vastagsag technologiai packot;
- feed/kerf/pierce parameterkonyvtarat;
- cut-order policyt;
- contour-specifikus gyartastechnologiai szabalyrendszert.

#### 3. A lead-in/out ebben a taskban csak mapping, nem tervezes
A task a jelenlegi persisted lead descriptorokat csak tovabbitja vagy leképezi.

Elvart viselkedes:
- ha a target adapter a bejovo lead alakot tudja kezelni, irja ki;
- ha nem tudja, a `lead_output` + `fallbacks` szabalyai szerint jarjon el;
- ha a szerzodes szerint `error` a fallback, akkor ne talaljon ki uj lead-et,
  hanem alljon meg determinisztikus hibaval.

Ez a task **nem** tervez uj lead-in/out geometriat.

#### 4. Pontosan egy konkret celadapter legyen
A task ne epitsen altalanos plugin-rendszert vagy tobb adapteres frameworkot.

Elvaras:
- egy konkret `TARGET_ADAPTER_KEY`;
- egy konkret `TARGET_OUTPUT_FORMAT`;
- egy konkret kimeneti artifact-csalad.

Ha a repo nem tartalmaz konkret celgep-csalad dontest, a taskot BLOCKED-kent
kell kezelni, nem szabad kitalalt adaptert implementalni.

#### 5. A task csak a `run_artifacts` reteget bovitse
A task legfeljebb:
- uj artifact kindot vezethet be;
- machine-ready artifactot regisztralhat az `app.run_artifacts` tablaba;
- a generic artifact list/download flow-t hasznalhatja.

Tilos visszairni:
- `run_manufacturing_plans`
- `run_manufacturing_contours`
- `run_manufacturing_metrics`
- `geometry_contour_classes`
- `cut_contour_rules`
- `postprocessor_profile_versions`

#### 6. A smoke bizonyitsa a fo invariansokat
A task-specifikus smoke legalabb ezt bizonyitsa:
- konkret target adapterhez a machine-ready artifact letrejon;
- a `manufacturing_plan_json` + `config_jsonb` ugyanarra a truthra
  determinisztikus kimenetet ad;
- unsupported lead / arc / command esetben a config szerinti fallback vagy hiba lep eletbe;
- nincs write a manufacturing truth retegekbe;
- nincs masodik, implicit adapter vagy generic fallback emitter;
- ownership boundary ervenyesul;
- hiba jon, ha a target adapter metadata vagy a kotelezo `config_jsonb` blokkok hianyoznak.

### DoD
- [ ] A task csak a H2-E5-T4 optionalis adapter-agban mozog, nem minositi at H2 blockerre a T4 hianyat.
- [ ] A task a `manufacturing_plan_json` artifactra epul, nem live selectionre vagy raw solver outputra.
- [ ] A konkret target adapter csalad explicit rogzitesre kerul (`TARGET_*` mezok kitoltve).
- [ ] A `config_jsonb` szukitett boundary-ja tenylegesen enforce-olva van.
- [ ] A task nem tervez uj lead-in/out rendszert, csak mappinget/fallbacket alkalmaz.
- [ ] A task legfeljebb a `run_artifacts` reteget bovit i machine-ready artifacttal.
- [ ] Keszul task-specifikus smoke script.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h2_e5_t4_elso_machine_specific_adapter.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a task tul koran uj lead rendszert vagy technology packot akar bevezetni;
  - konkret target csalad hianyaban kitalalt adapter szuletik;
  - az adapter atugorja a `manufacturing_plan_json` boundary-t;
  - a `config_jsonb` visszaterjeszkedik manufacturing truth iranyba.
- Mitigacio:
  - explicit STOP szabaly, ha a target csalad nincs befagyasztva;
  - explicit no-lead-design boundary;
  - adapter input = machine-neutral export + snapshot metadata;
  - csak szukitett `config_jsonb` blokklista engedelyezett.
- Rollback:
  - migration + adapter service + smoke + dokumentacios artefaktok egy
    task-commitban visszavonhatok;
  - a machine-neutral foag (`H2-E5-T3`) erintetlen marad.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h2_e5_t4_elso_machine_specific_adapter.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile api/services/machine_specific_adapter.py scripts/smoke_h2_e5_t4_elso_machine_specific_adapter.py`
  - `python3 scripts/smoke_h2_e5_t4_elso_machine_specific_adapter.py`

## Kapcsolodasok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
- `docs/web_platform/roadmap/h2_lezarasi_kriteriumok_es_h3_entry_gate.md`
- `canvases/web_platform/h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.md`
- `canvases/web_platform/h2_e5_t3_machine_neutral_exporter.md`
- `api/services/postprocessor_profiles.py`
- `api/services/run_snapshot_builder.py`
- `api/services/machine_neutral_exporter.py`
- `api/routes/runs.py`
