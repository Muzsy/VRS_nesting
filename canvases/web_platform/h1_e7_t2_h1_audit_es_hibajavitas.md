# H1-E7-T2 H1 audit és hibajavítás

## Funkció
A feladat a H1 záró auditja és stabilizálása a feltételezett H1-E7-T1 pilot
után. A cél nem új H2 feature szállítása, hanem annak evidence-alapú kimondása,
hogy a H1 teljes DXF -> geometry -> part/sheet -> snapshot -> run -> projection
-> artifact lánca valóban elég stabil-e a H2 ráépítéséhez.

Ez a task tehát egyszerre:
- **closure audit** a H1 végén,
- **targeted bugfix** task a pilotból kijött kritikus hibákra,
- és **H2 entry gate** döntési pont.

A tasknak őszintén ki kell mondania:
- mi működik stabilan,
- mi csak advisory,
- mi blokkolná a H2-t,
- és mely hibák lettek most ténylegesen javítva.

## Fejlesztési részletek

### Scope
- Benne van:
  - a teljes H1 completion matrix evidence-alapú összeállítása;
  - dedikált H1 lezárási / H2 entry gate dokumentum készítése;
  - a H1-E7-T1 pilot eredményeinek és tanulságainak beépítése;
  - a H1 kritikus, pilotból kijövő hibáinak célzott javítása;
  - minimális docs/known-issues tisztítás és szinkronizálás;
  - regressziós smoke/harness futtathatóvá tétele;
  - záró report + checklist + verify log.
- Nincs benne:
  - új H2 feature;
  - manufacturing profile, cut rule, postprocess vagy inventory/remnant világ;
  - nagy architekturális refaktor;
  - új, nem pilotból vagy auditból következő feature-scope;
  - általános UI/frontend munka, ha nem közvetlen H1 blokkoló.

### Fő kérdések, amiket le kell zárni
- [ ] A H1 task tree minden vállalt fő eleme ténylegesen végig lett vezetve?
- [ ] A H1-E7-T1 pilot alapján a teljes lánc reprodukálható és auditálható?
- [ ] Maradt-e H1 blokkoló hiba a DXF -> geometry -> run -> result útban?
- [ ] A projection és artifact világ ténylegesen query-zható és visszakereshető?
- [ ] A worker retry/lease/done/error utak H1 minimum szinten stabilak?
- [ ] A H2 indítható-e `PASS` vagy `PASS WITH ADVISORIES` minősítéssel?

### Feladatlista
- [ ] Kész legyen a task teljes artefaktlánca.
- [ ] Készüljön el a dedikált H1 lezárási / H2 entry gate dokumentum.
- [ ] Készüljön el a H1 completion matrix a tényleges taskokkal.
- [ ] Történjen meg a H1 pilot + repo state audit.
- [ ] A pilotból kijövő kritikus hibák célzottan legyenek javítva.
- [ ] Frissüljön a `web_platform_known_issues.md`, ha marad advisory.
- [ ] Készüljön regressziós smoke/harness a H1 kritikus láncra.
- [ ] A task mondja ki egyértelműen, hogy a H2 ráépíthető-e.
- [ ] Repo gate le legyen futtatva a reporton.

### Érintett fájlok
- `canvases/web_platform/h1_e7_t2_h1_audit_es_hibajavitas.md`
- `codex/goals/canvases/web_platform/fill_canvas_h1_e7_t2_h1_audit_es_hibajavitas.yaml`
- `codex/prompts/web_platform/h1_e7_t2_h1_audit_es_hibajavitas/run.md`
- `codex/codex_checklist/web_platform/h1_e7_t2_h1_audit_es_hibajavitas.md`
- `codex/reports/web_platform/h1_e7_t2_h1_audit_es_hibajavitas.md`
- `docs/web_platform/roadmap/h1_lezarasi_kriteriumok_es_h2_entry_gate.md`
- `docs/known_issues/web_platform_known_issues.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `api/main.py`
- `api/routes/files.py`
- `api/routes/parts.py`
- `api/routes/sheets.py`
- `api/routes/project_part_requirements.py`
- `api/routes/project_sheet_inputs.py`
- `api/routes/runs.py`
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
- `worker/queue_lease.py`
- `worker/engine_adapter_input.py`
- `worker/raw_output_artifacts.py`
- `worker/result_normalizer.py`
- `worker/sheet_svg_artifacts.py`
- `worker/sheet_dxf_artifacts.py`
- `scripts/smoke_h1_e7_t2_h1_audit_es_hibajavitas.py`

### Elvárt auditdimenziók
A konkrét fejezetcímek finomíthatók, de legalább ezek legyenek benne:

#### 1. H1 completion matrix
Legalább az alábbi taskok státuszát és bizonyítékát rögzítse:
- H1-E1-T1
- H1-E1-T2
- H1-E2-T1
- H1-E2-T2
- H1-E2-T3
- H1-E2-T4
- H1-E3-T1
- H1-E3-T2
- H1-E3-T3
- H1-E3-T4
- H1-E4-T1
- H1-E4-T2
- H1-E4-T3
- H1-E5-T1
- H1-E5-T2
- H1-E5-T3
- H1-E6-T1
- H1-E6-T2
- H1-E6-T3
- H1-E7-T1

#### 2. End-to-end pilot audit
Ellenőrizze legalább:
- a teljes inputlánc működését DXF uploadtól a geometry derivatívákig;
- a part/sheet/project input világ konzisztenciáját;
- a snapshot build és run create integritását;
- a worker lease/futtatás/raw artifact/normalizer láncot;
- a projection (`run_layout_*`, `run_metrics`) és artifact (`sheet_svg`, `sheet_dxf`) visszakereshetőségét;
- a route oldali lekérdezhetőséget ott, ahol az H1 minimum része.

#### 3. Blokkoló vs advisory eltérések
A task külön nevezze meg:
- mely hibák blokkolják a H2-t;
- melyek maradhatnak advisoryként;
- mely pontokon történt konkrét célzott hibajavítás ebben a taskban.

#### 4. Stabilizációs javítási elv
A hibajavítások csak akkor jók ebben a taskban, ha:
- közvetlenül a H1 pilotból vagy auditból következnek;
- nem nyitnak új feature-scope-ot;
- minimális diffel oldják meg a H1 blokkoló hiányt;
- a reportban egyenesen meg vannak nevezve.

#### 5. H2 entry gate
A dokumentum mondja ki:
- mi tekinthető H1 structural/functional PASS-nak;
- milyen advisory pontok maradhatnak még;
- és milyen feltételekkel nyitható a H2.

### Elvárt kimenet a dedikált H1 gate doksiban
A `docs/web_platform/roadmap/h1_lezarasi_kriteriumok_es_h2_entry_gate.md` dokumentum legalább ezt tartalmazza:

1. **Cél és használat**
   - miért készült a dokumentum,
   - mire szolgál a H2 előtt.

2. **H1 lezárási kritériumok**
   - funkcionális lánc,
   - reprodukálhatóság,
   - projection/artifact különválás,
   - worker stabilitás,
   - docs/route/known-issues konzisztencia.

3. **H1 completion matrix**
   - taskonként PASS / SOFT PASS / FAIL formában.

4. **Pilotból kijött fő tanulságok**
   - csak a ténylegesen releváns pontok.

5. **Blokkoló vs advisory eltérések**
   - csak a ténylegesen maradt eltérések.

6. **H2 entry gate ítélet**
   - `PASS`, `PASS WITH ADVISORIES` vagy `FAIL`.

7. **Mit jelent ez a gyakorlatban?**
   - mire lehet már biztonsággal H2-t építeni,
   - mit nem kell újranyitni H1-ben,
   - milyen advisory pontokat kell H2 során fejben tartani.

### Fontos modellezési elvek
- Ez audit/stabilizációs task, nem feature-task.
- A task célja a H1 lezárhatóságának bizonyítása vagy őszinte cáfolata.
- Ha kritikus ellentmondás maradt, azt ki kell mondani, nem szabad `PASS`-ra szépíteni.
- A kisebb, nem blokkoló eltérések advisory kategóriában maradhatnak.
- A H2 csak akkor nyílhat meg, ha a H1 verdict `PASS` vagy `PASS WITH ADVISORIES`.
- A taskban csak pilotból vagy auditból közvetlenül következő hibajavítás fér bele.

### DoD
- [ ] Letrejön a `docs/web_platform/roadmap/h1_lezarasi_kriteriumok_es_h2_entry_gate.md` fájl.
- [ ] A dokumentum tartalmaz H1 completion matrixot.
- [ ] A dokumentum tartalmaz pilot-tanulság fejezetet.
- [ ] A dokumentum tartalmaz blokkoló vs advisory bontást.
- [ ] A dokumentum egyértelmű H2 entry gate ítéletet ad.
- [ ] A `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`,
      a `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
      és a `docs/known_issues/web_platform_known_issues.md` minimálisan szinkronba kerül a H1 lezárási állapottal.
- [ ] A pilotból vagy auditból kijövő kritikus H1 hibák célzottan javítva vannak.
- [ ] A task nem hoz létre új H2 feature-t.
- [ ] A task nem hoz létre új domain migrációt, hacsak nem kritikus, közvetlen H1 zárási ok lenne.
- [ ] Készül regressziós smoke/harness a H1 kritikus végigfutási láncra.
- [ ] A report DoD -> Evidence Matrix konkrét fájl- és parancs-hivatkozásokkal kitöltött.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h1_e7_t2_h1_audit_es_hibajavitas.md` PASS.

### Kockázat + rollback
- Kockázat:
  - a task túl puhán auditál, és nem mondja ki a valódi H1 maradék hibákat;
  - a task túl szélesen kezd feature-jellegű hibajavításokba;
  - a H2 gate verdict bizonyíték nélkül vagy túl optimistán születik meg.
- Mitigáció:
  - evidence-alapú completion matrix;
  - blokkoló vs advisory explicit szétválasztás;
  - csak pilotból következő célzott hibajavítás;
  - regressziós smoke/harness.
- Rollback:
  - docs + checklist/report + célzott codefixek egy commitban visszavonhatók;
  - nincs helye nagy refaktornak vagy szétszórt scope-bővítésnek.

## Tesztállapot
- Kötelező gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h1_e7_t2_h1_audit_es_hibajavitas.md`
- Feladat-specifikus ellenőrzés:
  - `python3 -m py_compile api/main.py api/routes/files.py api/routes/parts.py api/routes/sheets.py api/routes/project_part_requirements.py api/routes/project_sheet_inputs.py api/routes/runs.py api/services/file_ingest_metadata.py api/services/dxf_geometry_import.py api/services/geometry_validation_report.py api/services/geometry_derivative_generator.py api/services/part_creation.py api/services/sheet_creation.py api/services/project_part_requirements.py api/services/project_sheet_inputs.py api/services/run_snapshot_builder.py api/services/run_creation.py worker/main.py worker/queue_lease.py worker/engine_adapter_input.py worker/raw_output_artifacts.py worker/result_normalizer.py worker/sheet_svg_artifacts.py worker/sheet_dxf_artifacts.py scripts/smoke_h1_e7_t2_h1_audit_es_hibajavitas.py`
  - `python3 scripts/smoke_h1_e7_t2_h1_audit_es_hibajavitas.py`

## Lokalizáció
Nem releváns.

## Kapcsolódások
- `canvases/web_platform/h1_e7_t1_end_to_end_pilot_projekt.md`
- `codex/reports/web_platform/h1_e7_t1_end_to_end_pilot_projekt.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/known_issues/web_platform_known_issues.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `docs/solver_io_contract.md`
- `api/routes/files.py`
- `api/routes/parts.py`
- `api/routes/sheets.py`
- `api/routes/project_part_requirements.py`
- `api/routes/project_sheet_inputs.py`
- `api/routes/runs.py`
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
- `worker/queue_lease.py`
- `worker/engine_adapter_input.py`
- `worker/raw_output_artifacts.py`
- `worker/result_normalizer.py`
- `worker/sheet_svg_artifacts.py`
- `worker/sheet_dxf_artifacts.py`
