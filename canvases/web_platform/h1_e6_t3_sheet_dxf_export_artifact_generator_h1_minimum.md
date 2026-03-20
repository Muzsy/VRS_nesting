# H1-E6-T3 Sheet DXF/export artifact generator (H1 minimum)

## Funkcio
A feladat a H1-E6 harmadik lepese: a H1-E6-T1-ben letett canonical
projection truth (`app.run_layout_sheets`, `app.run_layout_placements`) es a
snapshot/geometry derivative truth fole per-sheet exportalhato DXF artifactokat
generalni, majd ezeket `app.run_artifacts` alatt visszakereshetoen
regisztralni.

Ez a task tudatosan **nem** manufacturing/postprocess pipeline, **nem**
komplett export center, **nem** bundle workflow redesign es **nem** frontend
ujratervezes. A cel kizarolag az, hogy egy sikeres run utan a platform minimum
szinten mar tudjon sheet-szintu DXF export artifactot adni, amely route- es
artifact-lista oldalon is visszakeresheto.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - explicit worker-oldali sheet DXF generator helper/service boundary;
  - a projection truth + snapshot + `nesting_canonical` derivative alapjan per
    hasznalt sheet determinisztikus DXF dokumentum generalasa;
  - canonical filename + storage path + `sheet_dxf` artifact regisztracio;
  - worker success path bovitese ugy, hogy a per-sheet DXF artifactok a run
    zarasa elott generalodjanak;
  - task-specifikus smoke a sikeres es hibas DXF-generator agakra.
- Nincs benne:
  - `bundle_zip` generalas vagy bundle endpoint/redesign;
  - manufacturing/toolpath/machine program export;
  - original-forras entitasok teljes visszaepitese vagy H2-s
    `manufacturing_canonical` hasznalat;
  - nagy `/viewer-data` vagy frontend workflow redesign;
  - uj schema/enum/tabla, ha a meglavo artifact modell eleg.

### Talalt relevans fajlok
- `worker/main.py`
  - a H1-E6-T1 ota mar megvan a canonical projection write, a H1-E6-T2 ota a
    sheet SVG artifact generator; ide kell a DXF exportot jo sorrendben bekotni.
- `worker/result_normalizer.py`
  - innen latszik a projection truth alakszerkezete (`sheets`, `placements`,
    `transform_jsonb`, `bbox_jsonb`).
- `worker/sheet_svg_artifacts.py`
  - friss minta arra, hogyan nezzen ki kulon export/helper boundary,
    deterministic filename/storage policyval es artifact-regisztracioval.
- `api/services/geometry_derivative_generator.py`
  - a `nesting_canonical` derivative JSON szerkezete itt definialt; ezt kell a
    DXF-export geometriaforrasakent felhasznalni.
- `api/services/run_snapshot_builder.py`
  - a snapshot manifest truth (`parts_manifest_jsonb`, `sheets_manifest_jsonb`)
    adja a part/sheet feloldas alapjat.
- `api/routes/runs.py`
  - a jelenlegi artifact/viewer logika mar felismeri a `.dxf` artifactokat
    filename + `sheet_index` metadata alapjan; ezert a tasknak nem kell nagy
    route-redesign, csak kompatibilis artifactokat kell eloallitani.
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
  - kimondja, hogy az export artifact nem source-of-truth, hanem projection
    + domain truth alapjan ujraepitheto kimenet.
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
  - kimondja, hogy a viewer/export artifact kulon vilag a projectiontol es a
    manufacturingtol.
- `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md`
  - a runbol szuletett file/blob artifactok canonical bucketje a `run-artifacts`.
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
  - H1 artifact/export minimum elvarasok.
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - H1-E6-T3 source-of-truth.

### Konkret elvarasok

#### 1. Legyen explicit sheet DXF generator boundary
A DXF export generalas ne maradjon szetszorva a workerben.

Hasznalj explicit worker-oldali helper/modult, peldaul:
- `worker/sheet_dxf_artifacts.py`
- vagy ezzel egyenerteku, jol tesztelheto boundary.

A helper minimum felelossege:
- a rendereleshez/exporthoz szukseges sheet/placement/geometria indexek
  felallitasa;
- per-sheet DXF payload eloallitasa;
- canonical filename + storage path generalasa;
- artifact upload + `run_artifacts` regisztracio boundaryja;
- worker szamara visszaadhato summary (pl. hany sheet DXF keszult, melyik
  sheet-indexhez milyen artifact keszult).

#### 2. Az export projection truth-ra es `nesting_canonical` derivativara uljon
A task ne olvassa vissza ujra a raw `solver_output.json`-t DXF generalasra.

A minimum elvart adatforras:
- H1-E6-T1 projection output (`run_layout_sheets` / `run_layout_placements`
  szerkezete vagy a workerben meglevő projection objektum);
- snapshot manifest truth a part- es geometry-feloldashoz;
- `nesting_canonical` derivative payload a solver-barát polygon geometryhoz.

A part-shape forras ne legyen:
- raw solver output geometriadump;
- `viewer_outline` visszafele hasznalata DXF-export alapjakent, ha a
  `nesting_canonical` truth elerheto;
- puszta bbox-teglalap vagy mas ad hoc placeholder geometriarajz.

Ha valamely placementhez nem oldhato fel ervenyes `nesting_canonical`
derivative, legyen determinisztikus task-hiba, ne csendes hianyos export.

#### 3. A H1 minimum DXF contract legyen egyszeru, de visszaolvashato
A H1 minimum DXF ne akarjon manufacturing-fidelitast, de legyen stabilan
megnyithato es alap szinten visszatoltheto.

Minimum elvart:
- per hasznalt sheet egy DXF dokumentum;
- mm-unit / egyertelmu DXF dokumentum header beallitas;
- legalabb egy sheet boundary vagy dokumentalt, egyertelmu sheet-keret jelzes;
- placementenkent a `nesting_canonical.polygon.outer_ring` + `hole_rings`
  alapjan rajzolt zart konturok;
- a placement transzformacio (`x`, `y`, `rotation_deg`) kovetkezetes
  alkalmazasa a kimeneti geometriara;
- determinisztikus entitas-sorrend (sheet_index, placement_index,
  part_revision_id) a stabil diff/hash erdekeben;
- a kimenet legalabb basic import/export smoke-ban visszaolvashato legyen.

Jo H1 minimum irany:
- egyszeru, determinisztikus DXF writer;
- zart polyline/polygon reprezentacio;
- egyertelmu layer-policy (pl. `SHEET_FRAME`, `PART_OUTER`, `PART_HOLE`) vagy
  hasonloan egyszeru, dokumentalt konvencio.

Nem cel most:
- eredeti DXF entitasok teljes megoerzese;
- BLOCK+INSERT tokeletesitett export;
- H2 manufacturing_canonical vagy gepspecifikus postprocess.

#### 4. Az artifact persistence legyen canonical es route-kompatibilis
A generalt DXF artifactok `app.run_artifacts` ala keruljenek.

Minimum elvart:
- bucket: canonical run artifact bucket (`run-artifacts`);
- artifact type / kind: `sheet_dxf`;
- filename legyen stabil es route-kompatibilis, peldaul `out/sheet_001.dxf` vagy
  ezzel egyenerteku naming;
- a regisztracio tartalmazza a `sheet_index` metadata truth-ot;
- az upload/regisztracio legyen retry-biztos es ugyanarra a sheetre idempotensen
  lecserelheto.

Jo H1 minimum irany:
- storage pathban szerepeljen `project_id`, `run_id`, `sheet_dxf`, es valamilyen
  tartalomhoz kotott digest;
- metadata-ban legyen legalabb `filename`, `size_bytes`, `sheet_index`,
  `content_sha256`, es `legacy_artifact_type='sheet_dxf'`.

#### 5. A worker lifecycle-be jo helyre keruljon
A worker success path H1 minimum sorrendje igy nezzen ki:
1. solver futas,
2. raw artifact persistence,
3. result normalizer + projection write,
4. sheet SVG artifact generator,
5. sheet DXF artifact generator,
6. run `done` zaras.

Mivel ez a task mar a H1 basic export resze, a canonical success path ne
hallgassa el a generator hibat. Ha a task vallalja, hogy futas utan sheet DXF
elerheto, akkor DXF generalasi/regisztracios hiba eseten a run ne menjen
csendben `done` allapotba.

#### 6. A task ne csusszon at bundle/manufacturing vagy frontend-redesign scope-ba
Ebben a taskban meg nincs:
- bundle ZIP generalas;
- manufacturing canonical hasznalat;
- machine program / NC export;
- artifact-center / export-center teljes API redesign;
- frontend komponensek atirasa.

A cel csak annyi, hogy a jelenlegi artifact lista es viewer/bundle utak mar
kapjanak per-sheet DXF artifactokat, amelyeket kesobb tovabb lehet epiteni.

#### 7. A smoke script bizonyitsa a fo export es artifact agakra
Legyen task-specifikus smoke, amely fake snapshot + fake projection + fake
storage/DB gateway mellett legalabb ezt bizonyitja:
- per hasznalt sheet pontosan egy DXF jon letre;
- a DXF a sheet mereteit es a placement transzformaciokat koveti;
- a `nesting_canonical` hole-os geometria is exportalhato;
- az artifact filename/sheet_index metadata route-kompatibilis;
- ugyanarra a bemenetre a DXF payload es a storage/regisztracios kimenet
  determinisztikus;
- a smoke vissza tudja olvasni / alap szerkezetre validalni a letrehozott DXF-et;
- hiba jon, ha hianyzik a `nesting_canonical` vagy ervenytelen a placement/sheet
  kapcsolat;
- a smoke nem igenyel valos Supabase kapcsolatot vagy frontendet.

### DoD
- [ ] Keszul explicit worker-oldali sheet DXF generator helper/boundary.
- [ ] A generator a projection truth + snapshot geometry/`nesting_canonical` derivative alapjan exportal, nem raw solver outputbol.
- [ ] Per hasznalt sheet legalabb egy deterministic DXF dokumentum generalodik.
- [ ] A geometriak a `nesting_canonical` derivative-bol rajzolodnak, a placement transzformaciot kovetve.
- [ ] Az artifactok `sheet_dxf` artifactkent a canonical run-artifacts bucketbe kerulnek.
- [ ] A regisztracio route-kompatibilis `filename` + `sheet_index` metadata truth-ot ad.
- [ ] Az upload/regisztracio ugyanarra a sheetre retry-biztos/idempotens replace viselkedest ad.
- [ ] A worker success path a sheet DXF generator utan zarja `done`-ra a runt.
- [ ] A task nem csuszik at bundle/manufacturing vagy nagy frontend/redesign scope-ba.
- [ ] Keszul task-specifikus smoke a sikeres es hibas DXF-generator agakra.
- [ ] A checklist es report evidence-alapon ki van toltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.md` PASS.

### Kockazat + rollback
- Kockazat:
  - az export ujra raw solver outputra ulne, es megkerulne a H1-E6-T1
    projection truth-ot;
  - a generator bbox-teglalapokat vagy SVG-bol visszafejtett geometriat exportalna
    a `nesting_canonical` helyett;
  - a route nem talalja meg az artifactokat, mert a filename/sheet-index metadata
    nem kompatibilis;
  - DXF hiba mellett a worker megis `done` allapotba megy.
- Mitigacio:
  - explicit helper/boundary;
  - deterministic filename + metadata policy;
  - smoke-ban fedett export/idempotencia/error agak;
  - reportban egyertelmu scope-hatarok.
- Rollback:
  - a helper/worker/smoke/report/checklist diff egy task-commitban
    visszavonhato;
  - schema-modositas csak akkor johet, ha a meglavo artifact-utas megoldas nem
    eleg, es ezt a reportban ki kell mondani.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile worker/main.py worker/sheet_svg_artifacts.py worker/sheet_dxf_artifacts.py worker/result_normalizer.py worker/raw_output_artifacts.py scripts/smoke_h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.py`
  - `python3 scripts/smoke_h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md`
- `worker/main.py`
- `worker/result_normalizer.py`
- `worker/sheet_svg_artifacts.py`
- `api/services/geometry_derivative_generator.py`
- `api/routes/runs.py`
