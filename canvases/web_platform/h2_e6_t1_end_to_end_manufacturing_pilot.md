# H2-E6-T1 End-to-end manufacturing pilot

## Funkcio
A feladat a H2 fo zaro pilotja: annak bizonyitasa, hogy a mar meglevo H2
manufacturing/postprocess lanc egy reprodukalhato mintarunon vegigfuthat a
snapshotolt manufacturing truthbol a persisted manufacturing planon, a
preview/artifact retegen es a machine-neutral exporton at.

Ez a task tudatosan **nem** altalanos H2 audit/hibajavito hullam
(**az H2-E6-T2**), **nem** machine-specific adapter task
(**a H2-E5-T4 opcionális**), es **nem** H3 scoring / decision layer scope.
A cel az, hogy legyen egy tenylegesen futtathato, evidence-alapu H2 pilot-flow,
amely megmutatja, hogy a jelenlegi repoallapotban a fo H2 chain:
- manufacturing selection + snapshot truth,
- contour classification + cut-rule alap,
- manufacturing plan builder,
- manufacturing metrics,
- manufacturing preview SVG,
- machine-neutral export artifact

valoban osszekapcsolhato es auditálható.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - egy reprodukalhato H2 end-to-end pilot harness/smoke script;
  - egy dedikalt H2 pilot runbook/tesztdokumentum;
  - legalabb egy egyszeru, de valos H2 mintarun evidence-szintu vegigvezetese;
  - a H2 fo lanchossz igazolasa legalabb eddig:
    `manufacturing snapshot/selection -> plan builder -> metrics -> preview -> machine-neutral export`;
  - upstream H2 truth seedelese ott, ahol ez a pilot reprodukalhatosagahoz kell:
    - approved `manufacturing_canonical` derivative ref,
    - contour classification,
    - cut rule set + contour rules,
    - run snapshot manufacturing/postprocess manifest,
    - placement/projection jellegu input a plan buildernek;
  - a pilot outputok ellenorzese checklist/report szinten.
- Nincs benne:
  - altalanos H2 audit/stabilizacios hullam (ez H2-E6-T2);
  - machine-specific adapter, G-code/NC emitter, `machine_ready_bundle`;
  - worker auto-trigger vagy uj export orchestration flow;
  - uj schema/migracios kor megnyitasa, hacsak blokkolo pilot-futtathatosagi ok nem kenyszeriti ki;
  - H3 strategy/scoring/remnant scope;
  - frontend/backoffice redesign.

### Talalt relevans fajlok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - itt van a H2-E6-T1 task: end-to-end manufacturing pilot.
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
  - a H2 elvart full smoke-flow-ja, sikerkritériumai es technical debt tiltólistaja.
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
  - kritikus boundary: manufacturing truth, preview, export es postprocess kulon reteg.
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
  - snapshot-first elv, export artifact != truth.
- `api/services/run_snapshot_builder.py`
  - manufacturing/postprocess manifest snapshot struktura.
- `api/services/project_manufacturing_selection.py`
  - project-level manufacturing selection truth es aktiv profile version logika.
- `api/services/manufacturing_plan_builder.py`
  - a H2 core persisted manufacturing plan eloallitoja.
- `api/services/manufacturing_metrics_calculator.py`
  - a H2 metrics truth generalasa.
- `api/services/manufacturing_preview_generator.py`
  - persisted plan truth -> `manufacturing_preview_svg` artifact.
- `api/services/postprocessor_profiles.py`
  - snapshotolhato postprocessor profile/version metadata.
- `api/services/machine_neutral_exporter.py`
  - persisted plan truth -> `manufacturing_plan_json` artifact.
- `scripts/smoke_h2_e4_t2_manufacturing_plan_builder.py`
  - jo minta a plan-builder truth seeded ellenorzesehez.
- `scripts/smoke_h2_e4_t3_manufacturing_metrics_calculator.py`
  - jo minta metrics truth evidence-re.
- `scripts/smoke_h2_e5_t1_manufacturing_preview_svg.py`
  - jo minta preview artifact evidence-re.
- `scripts/smoke_h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.py`
  - jo minta snapshotolt postprocessor selection reteghez.
- `scripts/smoke_h2_e5_t3_machine_neutral_exporter.py`
  - jo minta machine-neutral export artifact evidence-re.
- `api/routes/runs.py`
  - generic artifact list/download contract; a pilot outputjai itt is visszakereshetok.
- `docs/qa/testing_guidelines.md`
  - reprodukalhato smoke/pilot szabalyok.

### Konkret elvarasok

#### 1. Legyen explicit H2 pilot harness, ne csak resz-smoke-ok egymas utan
A task hozzon letre kulon, reprodukalhato H2 pilot scriptet, peldaul:
- `scripts/smoke_h2_e6_t1_end_to_end_manufacturing_pilot.py`

A pilot script minimum felelossege:
- egy egyszeru, de valos H2 mintarun seedelese;
- a snapshotolt manufacturing/postprocess truth eloallitasa vagy reprodukalasa;
- a plan builder meghivasa;
- a metrics generator meghivasa;
- a preview generator meghivasa;
- a machine-neutral exporter meghivasa;
- a kulcs outputok ellenorzese;
- egyertelmu PASS/FAIL kimenet strukturalt summaryval.

A jo irany itt nem az, hogy csak a korabbi smoke-okat shellben egymas utan futtatja,
hanem az, hogy egy kozos, konzisztens seeded scenario bizonyitja a H2 fo
kezfogasokat.

#### 2. A pilot a H2 fo mainline chain-t bizonyitsa
A pilot minimum ezt a logikai lanchosszt bizonyitsa:
1. van aktiv manufacturing profile version a relevans truth/snapshot szinten;
2. van approved `manufacturing_canonical` derivative-re epulo manufacturing input;
3. van contour classification es cut rule truth a runhoz szukseges scope-ban;
4. a run snapshot manufacturing/postprocess manifestet tartalmaz;
5. a manufacturing plan builder persisted `run_manufacturing_plans` es `run_manufacturing_contours` truthot hoz letre;
6. a metrics calculator persisted `run_manufacturing_metrics` truthot hoz letre;
7. a preview generator `manufacturing_preview_svg` artifactot general;
8. a machine-neutral exporter `manufacturing_plan_json` artifactot general;
9. a generic artifact listban mindket artifact visszakeresheto;
10. a payloadok nem csusznak at machine-specific scope-ba.

A pilot PASS-hoz **nem kovetelmeny** a H2-E5-T4 opcionális machine-specific adapter.
Ha ilyen output nincs, az helyes. A pilotnak kifejezetten azt kell bizonyitania,
hogy a H2 mainline mar adapter nelkul is vegigfuthat.

#### 3. A mintarun legyen egyszeru, de H2 szempontbol reprezentativ
Minimum jo H2 pilot:
- 1 projekt;
- 1 aktiv manufacturing profile version;
- opcionálisan 1 aktiv postprocessor profile version metadata-szinten;
- 1 run;
- legalabb 1 sheet;
- legalabb 1 manufacturing plan;
- legalabb 1 outer es 1 inner contour jellegu manufacturing contour;
- legalabb 1 preview artifact;
- legalabb 1 machine-neutral export artifact;
- metrics truth legalabb alap mezokkel.

A cel a H2 lanchossz bizonyitasa, nem a nesting algoritmus benchmarking.
A fixture lehet egyszeru es szandekosan kicsi.

#### 4. A pilot legyen reprodukalhato es evidence-alapu
A pilotnak ne csak "lefutott" uzenete legyen.

Minimum elvart evidence:
- strukturalt summary a fo truth/artifact outputokrol;
- plan count, contour count, metrics jelenlet, artifact kindok;
- legalabb `manufacturing_preview_svg` es `manufacturing_plan_json` jelenlet;
- hiba eseten pontos boundary-specifikus uzenet arrol, hol torik el a H2 chain.

Jo irany:
- a script a vegen adjon JSON-szeru vagy konnyen olvashato summaryt;
- kulon ellenorizze a persisted truth es artifact reteg szetvalasztasat;
- ugyanarra a seedelt inputra ujrafuttathato legyen.

#### 5. Keszits dedikalt H2 pilot runbookot
A task hozzon letre dedikalt dokumentumot, peldaul:
- `docs/qa/h2_end_to_end_manufacturing_pilot_runbook.md`

Ez minimum tartalmazza:
- a pilot celjat;
- a pilot scope-jat;
- a fixture rovid leirasat;
- a futtatas lepeseit;
- az elvart truth es artifact outputokat;
- mit jelent a pilot PASS / FAIL;
- mit **nem** igazol ez a pilot (pl. machine-specific adapter, worker auto-trigger, H2 audit).

#### 6. A task ne csusszon at H2-E6-T2 auditba
Ha a pilot kozben blokkolo handshake hiba derul ki, azt ki kell mondani,
es csak a kozvetlen pilot-futtathatosaghoz szukseges minimalis korrekcio fer bele.

Nem cel most:
- altalanos H2 cleanup hullam;
- nagy service-refaktor;
- uj schema-tervezes;
- optionalis H2-E5-T4 adapter-scope becsempeszese.

A report kulon nevezze meg, mi maradt szandekosan H2-E6-T2 scope-ban.

#### 7. A pilot smoke bizonyitsa a fo H2 allitasokat
A task-specifikus pilot smoke legalabb ezt bizonyitsa:
- a H2 mainline manufacturing chain vegigfuthat egy mintarunon;
- letrejon `run_manufacturing_plans`;
- letrejon `run_manufacturing_contours`;
- letrejon `run_manufacturing_metrics`;
- az artifact listaban megjelenik legalabb:
  - `manufacturing_preview_svg`
  - `manufacturing_plan_json`
- nincs `machine_ready_bundle`, `machine_program`, `gcode` vagy egyeb machine-specific side effect, ha a T4 nincs implementalva;
- a snapshotolt postprocessor metadata - ha jelen van - csak metadata/input marad;
- ownership/snapshot/truth hiba eseten a script boundary-specifikus hibat ad.

### DoD
- [ ] Letrejon a `canvases/web_platform/h2_e6_t1_end_to_end_manufacturing_pilot.md` canvas.
- [ ] Letrejon a hozza tartozo goal YAML es runner prompt.
- [ ] Keszul dedikalt H2 pilot smoke/harness script.
- [ ] Keszul dedikalt H2 pilot runbook/tesztdokumentum.
- [ ] A pilot legalabb egy mintarunon vegigviszi a H2 mainline manufacturing chain-t.
- [ ] A pilot evidence-alapon ellenorzi a persisted plan/metrics truthot es a preview/export artifactokat.
- [ ] A task nem csuszik at machine-specific adapter vagy altalanos audit scope-ba.
- [ ] A checklist es report evidence-alapon ki van toltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h2_e6_t1_end_to_end_manufacturing_pilot.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a pilot csak a korabbi smoke-ok laza osszefuzese lesz kozos seeded scenario nelkul;
  - a task tul nagy stabilizacios hullamma no;
  - a pilot felreerthetoen machine-specific adapter hianyat hibanak veszi, pedig a T4 opcionális.
- Mitigacio:
  - kozos, egyszeru H2 mintarun;
  - explicit runbook + strukturalt pilot summary;
  - a report kulon mondja ki, hogy a T4 opcionális es nincs a PASS feltetelei kozott.
- Rollback:
  - a pilot script + runbook + checklist/report visszavonhato egy commitban;
  - ne nyisson szet kiterjedt core refaktort vagy schema-modositast.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h2_e6_t1_end_to_end_manufacturing_pilot.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile scripts/smoke_h2_e6_t1_end_to_end_manufacturing_pilot.py`
  - `python3 scripts/smoke_h2_e6_t1_end_to_end_manufacturing_pilot.py`

## Lokalizacio
Nem relevans.

## Megjegyzes
A task tree szerint a `H2-E5-T4` elso machine-specific adapter **opcionalis**.
Ezert a fo roadmap-vonal kovetkezo kotott taskja itt a `H2-E6-T1` pilot.
A pilotnak ezt a mainline-t kell lezarnia, nem az optionalis adapter-agat.
