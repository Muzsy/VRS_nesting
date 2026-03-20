# H1-E7-T1 End-to-end pilot projekt

## Funkcio
A feladat a H1 elso zaro pilotja: annak bizonyitasa, hogy a mar elkeszult H1
lany valoban vegigfuthat egy reprodukalhato mintaprojekten a DXF ingesttol a
projectionokig es az artifactokig.

Ez a task tudatosan **nem** altalanos stabilizacios/hibajavito hullam,
**nem** H1-E7-T2 audit helyett vegzett feature-bovites, es **nem** uj H2/H3
munkacsomag. A cel az, hogy legyen egy tenyleges, reprodukalhato H1 pilot-flow,
amely:
- vegigviszi a minimum H1 csatornat,
- egyertelmu evidence-et ad a vegpontokrol es a worker oldali eredmenyekrol,
- es oszinten kimondja, hogy a jelenlegi H1 hol tekintheto pilot-PASS-nak,
  illetve mi marad meg stabilizacios feladatnak.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - egy reprodukalhato H1 end-to-end pilot harness/smoke-flow script;
  - egy dedikalt pilot runbook/tesztdokumentum;
  - legalabb egy egyszeru, de valos H1 mintaprojekt teljes vegigvezetese
    evidence szinten;
  - a teljes H1 minimum lanchossz igazolasa:
    `file ingest -> geometry -> validation -> derivatives -> part/sheet -> project inputs -> run create -> snapshot -> queue/worker -> projection -> artifacts`;
  - a pilot eredmenyenek dokumentalasa checklist/report szinten.
- Nincs benne:
  - altalanos H1 audit es javitasi hullam (ez H1-E7-T2);
  - nagy API/front-end redesign;
  - H2 manufacturing, postprocess vagy export-center scope;
  - uj domain tablak/migraciok, ha a pilot nem kenyszerit ki blokkolo javitast;
  - bundle workflow, inventory/remnant vagy H3-level feature.

### Talalt relevans fajlok
- `api/routes/files.py`
  - upload URL + `complete_upload` flow, a H1 ingest belepesi pontja.
- `api/services/file_ingest_metadata.py`
  - server-side file metadata truth.
- `api/services/dxf_geometry_import.py`
  - DXF -> `geometry_revisions` parser/import boundary.
- `api/services/geometry_validation_report.py`
  - validation report eloallitas.
- `api/services/geometry_derivative_generator.py`
  - `nesting_canonical` es `viewer_outline` derivative truth.
- `api/services/part_creation.py`
  - part revision/pilot part letrehozas.
- `api/services/sheet_creation.py`
  - sheet revision/pilot sheet letrehozas.
- `api/services/project_part_requirements.py`
  - pilot part-demand input.
- `api/services/project_sheet_inputs.py`
  - pilot sheet input.
- `api/services/run_snapshot_builder.py`
  - pilot snapshot truth builder.
- `api/services/run_creation.py`
  - run create boundary.
- `worker/main.py`
  - worker success path: raw -> projection -> sheet_svg -> sheet_dxf -> done.
- `worker/result_normalizer.py`
  - projection truth.
- `worker/sheet_svg_artifacts.py`
  - viewer artifact boundary.
- `worker/sheet_dxf_artifacts.py`
  - export artifact boundary.
- `scripts/smoke_h1_e4_t1_run_snapshot_builder_h1_minimum.py`
  - jo minta fake gateway + seeded happy-path stilusra.
- `scripts/smoke_h1_e6_t1_result_normalizer_h1_minimum.py`
  - jo minta projection evidence-re.
- `scripts/smoke_h1_e6_t2_sheet_svg_generator_h1_minimum.py`
  - jo minta artifact evidence-re.
- `scripts/smoke_h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.py`
  - jo minta export artifact evidence-re.
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
  - H1 pilot minimum celok.
- `docs/qa/testing_guidelines.md`
  - reprodukalhato smoke/pilot szabalyok.

### Konkret elvarasok

#### 1. Legyen explicit H1 pilot harness, ne csak szetszort ellenorzes
A task ne csak kulon-kulon hivja meg a resz-smoke-okat, hanem hozzon letre egy
kulon, reprodukalhato H1 pilot scriptet, peldaul:
- `scripts/smoke_h1_e7_t1_end_to_end_pilot_projekt.py`

A pilot script minimum felelossege:
- a pilot fixture/mintaprojekt felallitasa;
- a H1 minimum flow vegigvezetese logikus sorrendben;
- a kulcs-outputok ellenorzese;
- egyertelmu PASS/FAIL kimenet;
- valos Supabase/HTTP front-end nelkul is futtathato bizonyitas.

Jo irany:
- in-process/fake gateway boundaryk ott, ahol nincs szukseg igazi infrastrukturara;
- a mar meglevo H1 service/helper boundaryk ujrafelhasznalasa;
- a pilot ne legyen csak report-szintu allitas, hanem futtathato bizonyitek.

#### 2. A pilot a teljes H1 minimum lanchosszt bizonyitsa
A script legalabb ezt a logikai lanchosszt bizonyitsa:
1. projekt truth megvan;
2. file ingest truth letrejon;
3. geometry import lefut;
4. validation report letrejon;
5. `nesting_canonical` + `viewer_outline` derivative eloall;
6. part revision es sheet revision letrejon;
7. `project_part_requirements` es `project_sheet_inputs` pilot input letrejon;
8. run create/snapshot build megtortenik;
9. worker feldolgozza a runt;
10. letrejon projection truth (`run_layout_*`, `run_metrics`);
11. letrejon a minimum artifact keszlet:
   - raw solver output
   - sheet_svg
   - sheet_dxf
12. a run pilot-szinten sikeres es visszakeresheto.

Nem eleg csak azt ellenorizni, hogy a worker tud egy mar kesz snapshotbol futni.
A pilotnak azt kell bizonyitania, hogy a H1 vegpontok kozt nincs rejtett torott
kezfogasi pont.

#### 3. A mintaprojekt legyen egyszeru, de valodi H1 szempontbol reprezentativ
A pilot ne tulkomplikalt fixture legyen.

Minimum jo H1 pilot:
- 1 projekt;
- 1 technology setup/profile reference;
- 1-2 egyszeru part;
- 1 egyszeru sheet input;
- 1 run;
- legalabb 1 elhelyezett elem;
- legalabb 1 kepzodott projection;
- legalabb 1 kepzodott SVG es DXF artifact.

Megengedett jo irany:
- a fixture egy egyszeru teglalap vagy egyszeru polygon geometryra epul;
- a cel a lanchossz bizonyitasa, nem a nesting minosegi benchmark.

#### 4. A pilot legyen reprodukalhato es bizonyitek-alapu
A pilotnak ne csak "lefutott" uzenete legyen.

Minimum elvart evidence:
- a pilot script determinisztikus/azonositott fixture-rel fusson;
- legyen egyertelmu osszegzes arrol, hogy mely fo outputok jottek letre;
- a report es/vagy runbook nevezze meg a pilot output truth-okat;
- a pilot hiba eseten pontosan mondja meg, melyik H1 boundary torik el.

Jo irany:
- a script a vegen adjon strukturalt summary-t;
- legyen kulon ellenorizve a projection counts + artifact kinds + run status;
- ugyanarra a pilot fixture-re ugyanaz a H1 flow legyen ujrafuttathato.

#### 5. Keszits dedikalt pilot runbook/tesztdokumentumot
A task hozzon letre dedikalt dokumentumot, peldaul:
- `docs/qa/h1_end_to_end_pilot_runbook.md`

Ez minimum tartalmazza:
- a pilot celjat;
- a pilot scope-jat;
- a fixture rovid leirasat;
- a futtatas lepeseit;
- az elvart outputokat;
- mit jelent a pilot PASS / FAIL;
- ismert korlatokat, amelyeket a H1-E7-T2 auditban kell kezelni.

Ez ne legyen marketing osszefoglalo, hanem vegrehajthato/ellenorizheto runbook.

#### 6. A task ne csusszon at H1-E7-T2 stabilizacios hullamba
Ha a pilot kozben kritikus hiba derul ki, azt ki kell mondani.
De ez a task alapvetoen pilot-task.

Ezert:
- csak annyi kodvaltoztatas fer bele, ami a pilot harnesshez vagy a kozvetlen,
  minimalis pilot-futtathatosaghoz kell;
- altalanos H1 hiypotlassal/cleanup-pal ne nyuljon tul szelesen a reteghez;
- a report kulon nevezze meg, mi maradt szandekosan H1-E7-T2 scope-ban.

#### 7. A smoke script bizonyitsa a fo H1 pilot-allitasokat
A task-specifikus pilot smoke legalabb ezt bizonyitsa:
- a teljes H1 minimum chain vegigfuthat egy mintaprojekten;
- a run vegul `done` allapotba jut;
- a projection tablavilag nem ures;
- a `run_metrics` es placement counts ertelmesek;
- az artifact listaban megjelenik legalabb a `solver_output`, `sheet_svg`, `sheet_dxf`;
- a pilot script valos kulcs-outputokat ellenoriz, nem csak mock-flaget;
- hiba eseten a script boundary-specifikus uzenetet ad.

### DoD
- [ ] Letrejon a `canvases/web_platform/h1_e7_t1_end_to_end_pilot_projekt.md` canvas.
- [ ] Letrejon a hozza tartozo goal YAML es runner prompt.
- [ ] Keszul dedikalt H1 pilot smoke/harness script.
- [ ] Keszul dedikalt pilot runbook/tesztdokumentum.
- [ ] A pilot legalabb egy mintaprojekten vegigviszi a H1 minimum csatornat.
- [ ] A pilot evidence-alapon ellenorzi a projection truth es az artifactok letet.
- [ ] A task nem csuszik at altalanos H1 stabilizacios/refaktor scope-ba.
- [ ] A checklist es report evidence-alapon ki van toltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h1_e7_t1_end_to_end_pilot_projekt.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a pilot csak resz-smoke-ok osszefuzese lesz valodi end-to-end bizonyitas nelkul;
  - a task tul nagy hibajavito hullamma noveli magat;
  - a pilot fixture tul bonyolult lesz es emiatt instabil/flaky lesz.
- Mitigacio:
  - egy egyszeru, reprodukalhato mintaprojekt;
  - explicit runbook + pilot smoke;
  - a report kulon mondja ki, mit igazolt a pilot es mit nem.
- Rollback:
  - pilot script + runbook + checklist/report egy commitban visszavonhato;
  - a task ne nyisson szet kiterjedt core refaktort.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h1_e7_t1_end_to_end_pilot_projekt.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile scripts/smoke_h1_e7_t1_end_to_end_pilot_projekt.py`
  - `python3 scripts/smoke_h1_e7_t1_end_to_end_pilot_projekt.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/qa/testing_guidelines.md`
- `api/routes/files.py`
- `api/services/file_ingest_metadata.py`
- `api/services/dxf_geometry_import.py`
- `api/services/geometry_validation_report.py`
- `api/services/geometry_derivative_generator.py`
- `api/services/part_creation.py`
- `api/services/sheet_creation.py`
- `api/services/project_part_requirements.py`
- `api/services/project_sheet_inputs.py`
- `api/services/run_snapshot_builder.py`
- `api/services/run_creation.py`
- `worker/main.py`
- `worker/result_normalizer.py`
- `worker/sheet_svg_artifacts.py`
- `worker/sheet_dxf_artifacts.py`
