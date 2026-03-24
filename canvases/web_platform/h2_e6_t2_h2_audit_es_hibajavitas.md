# H2-E6-T2 H2 audit es hibajavitas

## Funkcio
A feladat a H2 zaro auditja es stabilizalasa a H2-E6-T1 end-to-end
manufacturing pilot utan. A cel nem uj H3 feature szallitasa, nem az optionalis
H2-E5-T4 machine-specific adapter potlasa, hanem annak evidence-alapu kimondasa,
hogy a H2 manufacturing/postprocess mainline eleg stabil-e a H3 raepitesehez.

Ez a task egyszerre:
- **closure audit** a H2 vegen,
- **targeted bugfix** task a H2-E6-T1 pilotbol vagy a H2 completion auditbol kijovo kritikus hibakra,
- es **H3 entry gate** dontesi pont.

A tasknak oszinten ki kell mondania:
- mi mukodik stabilan a H2 truth -> plan -> metrics -> preview -> export lancban,
- mi maradhat advisorykent,
- mi blokkolna a H3-at,
- es mely hibak lettek most tenylegesen javitva.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - a teljes H2 completion matrix evidence-alapu osszeallitasa;
  - dedikalt H2 lezarasi / H3 entry gate dokumentum keszitese;
  - a H2-E6-T1 pilot eredmenyeinek es tanulsagainak beepitese;
  - a H2 kritikus, pilotbol vagy auditbol kijovo hibainak celzott javitasa;
  - minimalis docs/known-issues tisztitas es szinkronizalas;
  - regresszios smoke/harness keszitese a H2 mainline manufacturing lancra;
  - zaro report + checklist + verify log.
- Nincs benne:
  - uj H3 strategy/scoring/remnant feature;
  - optionalis H2-E5-T4 machine-specific adapter, G-code/NC emitter vagy `machine_ready_bundle` bevezetese;
  - nagy architekturalis refaktor;
  - uj, nem pilotbol vagy auditbol kovetkezo feature-scope;
  - altalanos frontend/backoffice munka, ha nem kozvetlen H2 blokkolas.

### Fo kerdesek, amiket le kell zarni
- [ ] A H2 task tree minden vallalt fo eleme tenylegesen vegig lett vezetve H2-E6-T1-ig?
- [ ] A H2-E6-T1 pilot alapjan a manufacturing mainline reprodukalhato es auditalhato?
- [ ] Maradt-e H2 blokkolo hiba a manufacturing selection -> snapshot -> plan -> metrics -> preview -> export utban?
- [ ] A `run_manufacturing_*` truth es a `run_artifacts` preview/export vilag tenylegesen query-zhato es visszakeresheto?
- [ ] A H2 a H3 szamara stabil alapot ad-e `PASS` vagy `PASS WITH ADVISORIES` minositessel?
- [ ] Az optionalis H2-E5-T4 hianya helyesen van-e kezelve: nem H2 blocker, ameddig a machine-neutral foag stabil?

### Feladatlista
- [ ] Kesz legyen a task teljes artefaktlanca.
- [ ] Keszuljon el a dedikalt H2 lezarasi / H3 entry gate dokumentum.
- [ ] Keszuljon el a H2 completion matrix a tenyleges taskokkal.
- [ ] Tortenjen meg a H2 pilot + repo state audit.
- [ ] A pilotbol vagy auditbol kijovo kritikus hibak celzottan legyenek javitva.
- [ ] Frissuljon a `web_platform_known_issues.md`, ha marad advisory.
- [ ] Keszuljon regresszios smoke/harness a H2 kritikus vegigfutasi lancra.
- [ ] A task mondja ki egyertelmuen, hogy a H3 raepitheto-e.
- [ ] Repo gate le legyen futtatva a reporton.

### Erintett fajlok
- `canvases/web_platform/h2_e6_t2_h2_audit_es_hibajavitas.md`
- `codex/goals/canvases/web_platform/fill_canvas_h2_e6_t2_h2_audit_es_hibajavitas.yaml`
- `codex/prompts/web_platform/h2_e6_t2_h2_audit_es_hibajavitas/run.md`
- `codex/codex_checklist/web_platform/h2_e6_t2_h2_audit_es_hibajavitas.md`
- `codex/reports/web_platform/h2_e6_t2_h2_audit_es_hibajavitas.md`
- `docs/web_platform/roadmap/h2_lezarasi_kriteriumok_es_h3_entry_gate.md`
- `docs/known_issues/web_platform_known_issues.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `api/routes/project_manufacturing_selection.py`
- `api/routes/cut_rule_sets.py`
- `api/routes/cut_contour_rules.py`
- `api/routes/postprocessor_profiles.py`
- `api/routes/runs.py`
- `api/services/project_manufacturing_selection.py`
- `api/services/geometry_derivative_generator.py`
- `api/services/geometry_contour_classification.py`
- `api/services/cut_rule_sets.py`
- `api/services/cut_contour_rules.py`
- `api/services/cut_rule_matching.py`
- `api/services/run_snapshot_builder.py`
- `api/services/manufacturing_plan_builder.py`
- `api/services/manufacturing_metrics_calculator.py`
- `api/services/manufacturing_preview_generator.py`
- `api/services/postprocessor_profiles.py`
- `api/services/machine_neutral_exporter.py`
- `scripts/smoke_h2_e6_t1_end_to_end_manufacturing_pilot.py`
- `scripts/smoke_h2_e6_t2_h2_audit_es_hibajavitas.py`

### Elvart auditdimenziok
A konkret fejezetcimek finomithatok, de legalabb ezek legyenek benne:

#### 1. H2 completion matrix
Legalabb az alabbi taskok statuszat es bizonyitekat rogzitse:
- H2-E1-T1
- H2-E1-T2
- H2-E2-T1
- H2-E2-T2
- H2-E3-T1
- H2-E3-T2
- H2-E3-T3
- H2-E4-T1
- H2-E4-T2
- H2-E4-T3
- H2-E5-T1
- H2-E5-T2
- H2-E5-T3
- H2-E6-T1

Kulon nevezze meg, hogy a **H2-E5-T4 optionalis ag**, ezert a H2 closure
PASS feltetelei kozott csak akkor szerepelhetne, ha a repo tenylegesen be is
vezette volna. Ennek hianya onmagaban nem H2 blocker.

#### 2. End-to-end manufacturing pilot audit
Ellenorizze legalabb:
- manufacturing selection es snapshot manifest konzisztenciat;
- approved `manufacturing_canonical` derivative -> contour classification -> rule matching lancot;
- manufacturing plan builder / contour truth / metrics truth helyesseget;
- preview (`manufacturing_preview_svg`) es machine-neutral export (`manufacturing_plan_json`) artifact visszakereshetoseget;
- route oldali queryzhatosagot ott, ahol az H2 mainline resze;
- hogy nincs tiltott machine-specific side effect a foagban.

#### 3. Blokkolo vs advisory elteresek
A task kulon nevezze meg:
- mely hibak blokkoljak a H3-at;
- melyek maradhatnak advisorykent;
- mely pontokon tortent konkret celzott hibajavitas ebben a taskban.

#### 4. Stabilizacios javitasi elv
A hibajavitasok csak akkor jok ebben a taskban, ha:
- kozvetlenul a H2-E6-T1 pilotbol vagy a H2 completion auditbol kovetkeznek;
- nem nyitnak uj H3 feature-scope-ot;
- nem csempeszik vissza az optionalis H2-E5-T4 adapter-agat PASS feltetelnek;
- minimalis diffel oldjak meg a H2 blokkolo hianyt;
- a reportban egyenesen meg vannak nevezve.

#### 5. H3 entry gate
A dokumentum mondja ki:
- mi tekintheto H2 structural/functional PASS-nak;
- milyen advisory pontok maradhatnak meg;
- es milyen feltetelekkel nyithato a H3.

### Elvart kimenet a dedikalt H2 gate doksiban
A `docs/web_platform/roadmap/h2_lezarasi_kriteriumok_es_h3_entry_gate.md`
dokumentum legalabb ezt tartalmazza:

1. **Cel es hasznalat**
   - miert keszult a dokumentum,
   - mire szolgal a H3 elott.

2. **H2 lezarasi kriteriumok**
   - manufacturing truth szeparacio,
   - reproducibilis pilot,
   - plan/metrics truth,
   - preview/export artifact kulonvalas,
   - optionalis adapter-ag helyes kezelese,
   - docs/route/known-issues konzisztencia.

3. **H2 completion matrix**
   - taskonkent PASS / SOFT PASS / FAIL formaban.

4. **Pilotbol kijott fo tanulsagok**
   - csak a tenylegesen relevans pontok.

5. **Blokkolo vs advisory elteresek**
   - csak a tenylegesen maradt elteresek.

6. **H3 entry gate itelet**
   - `PASS`, `PASS WITH ADVISORIES` vagy `FAIL`.

7. **Mit jelent ez a gyakorlatban?**
   - mire lehet mar biztonsaggal H3-at epiteni,
   - mit nem kell ujranyitni H2-ben,
   - milyen advisory pontokat kell H3 soran fejben tartani.

### Fontos modellezesi elvek
- Ez audit/stabilizacios task, nem feature-task.
- A task celja a H2 lezarhatosaganak bizonyitasa vagy oszinte cafolata.
- Ha kritikus ellentmondas maradt, azt ki kell mondani, nem szabad `PASS`-ra szepiteni.
- A kisebb, nem blokkolo elteresek advisory kategoriaban maradhatnak.
- A H3 csak akkor nyilhat meg, ha a H2 verdict `PASS` vagy `PASS WITH ADVISORIES`.
- A taskban csak pilotbol vagy auditbol kozvetlenul kovetkezo hibajavitas fer bele.
- A `machine-neutral` foag a H2 closure kozepe; a machine-specific export opcionális kulon ag.

### DoD
- [ ] Letrejon a `docs/web_platform/roadmap/h2_lezarasi_kriteriumok_es_h3_entry_gate.md` fajl.
- [ ] A dokumentum tartalmaz H2 completion matrixot.
- [ ] A dokumentum tartalmaz pilot-tanulsag fejezetet.
- [ ] A dokumentum tartalmaz blokkolo vs advisory bontast.
- [ ] A dokumentum egyertelmu H3 entry gate iteletet ad.
- [ ] A `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`,
      a `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
      es a `docs/known_issues/web_platform_known_issues.md` minimalisan szinkronba kerul a H2 lezarasi allapottal.
- [ ] A pilotbol vagy auditbol kijovo kritikus H2 hibak celzottan javitva vannak.
- [ ] A task nem hoz letre uj H3 feature-t.
- [ ] A task nem teszi kotelezove az optionalis H2-E5-T4 ag megvalositasat.
- [ ] A task nem hoz letre uj domain migraciot, hacsak nem kritikus, kozvetlen H2 zaro ok lenne.
- [ ] Keszul regresszios smoke/harness a H2 kritikus mainline lancra.
- [ ] A report DoD -> Evidence Matrix konkret fajl- es parancs-hivatkozasokkal kitoltott.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h2_e6_t2_h2_audit_es_hibajavitas.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a task tul puhan auditál, es nem mondja ki a valodi H2 maradek hibakat;
  - a task tul szelesen kezd feature-jellegu hibajavitasokba;
  - a H3 gate verdict bizonyitek nelkul vagy tul optimistan szuletik meg;
  - az optionalis H2-E5-T4 hianya tevesen blockernek minosul.
- Mitigacio:
  - evidence-alapu completion matrix;
  - blokkolo vs advisory explicit szetvalasztas;
  - csak pilotbol kovetkezo celzott hibajavitas;
  - regresszios smoke/harness;
  - optionalis adapter-ag explicit kezelese a gate dokumentumban.
- Rollback:
  - docs + checklist/report + celzott codefixek egy commitban visszavonhatok;
  - nincs helye nagy refaktornak vagy szetszort scope-bovitesnek.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h2_e6_t2_h2_audit_es_hibajavitas.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile api/routes/project_manufacturing_selection.py api/routes/cut_rule_sets.py api/routes/cut_contour_rules.py api/routes/postprocessor_profiles.py api/routes/runs.py api/services/project_manufacturing_selection.py api/services/geometry_derivative_generator.py api/services/geometry_contour_classification.py api/services/cut_rule_sets.py api/services/cut_contour_rules.py api/services/cut_rule_matching.py api/services/run_snapshot_builder.py api/services/manufacturing_plan_builder.py api/services/manufacturing_metrics_calculator.py api/services/manufacturing_preview_generator.py api/services/postprocessor_profiles.py api/services/machine_neutral_exporter.py scripts/smoke_h2_e6_t1_end_to_end_manufacturing_pilot.py scripts/smoke_h2_e6_t2_h2_audit_es_hibajavitas.py`
  - `python3 scripts/smoke_h2_e6_t2_h2_audit_es_hibajavitas.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_master_roadmap_h0_h3.md`
- `docs/web_platform/roadmap/h1_lezarasi_kriteriumok_es_h2_entry_gate.md`
- `docs/known_issues/web_platform_known_issues.md`
- `canvases/web_platform/h2_e6_t1_end_to_end_manufacturing_pilot.md`
- `codex/reports/web_platform/h2_e6_t1_end_to_end_manufacturing_pilot.md`
- `api/services/project_manufacturing_selection.py`
- `api/services/geometry_derivative_generator.py`
- `api/services/geometry_contour_classification.py`
- `api/services/cut_rule_sets.py`
- `api/services/cut_contour_rules.py`
- `api/services/cut_rule_matching.py`
- `api/services/run_snapshot_builder.py`
- `api/services/manufacturing_plan_builder.py`
- `api/services/manufacturing_metrics_calculator.py`
- `api/services/manufacturing_preview_generator.py`
- `api/services/postprocessor_profiles.py`
- `api/services/machine_neutral_exporter.py`
- `api/routes/project_manufacturing_selection.py`
- `api/routes/cut_rule_sets.py`
- `api/routes/cut_contour_rules.py`
- `api/routes/postprocessor_profiles.py`
- `api/routes/runs.py`
- `scripts/smoke_h2_e6_t1_end_to_end_manufacturing_pilot.py`
