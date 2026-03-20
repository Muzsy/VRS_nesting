# H1-E6-T2 Sheet SVG generator (H1 minimum)

## Funkcio
A feladat a H1-E6 masodik lepese: a H1-E6-T1-ben mar feltoltott canonical
projection truth (`app.run_layout_sheets`, `app.run_layout_placements`,
`app.run_layout_unplaced`, `app.run_metrics`) fole per-sheet viewer SVG
artifactokat generalni, majd ezeket `app.run_artifacts` alatt visszakereshetoen
regisztralni.

Ez a task tudatosan **nem** DXF/export pipeline, **nem** manufacturing render,
**nem** nagy frontend/redesign es **nem** raw solver output parser ujranyitasa.
A cel az, hogy egy sikeres run utan a frontend mar kapjon legalabb alap
sheet-szintu SVG artifactokat, amelyeket a jelenlegi `/viewer-data` route mar
fel tud venni es ki tud szolgalni.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - explicit worker-oldali sheet SVG generator helper/service boundary;
  - a projection truth + snapshot geometry/viewer derivative alapjan SVG
    dokumentum generalasa minden hasznalt sheetre;
  - deterministic sheet-SVG payload es canonical storage path/filename policy;
  - `app.run_artifacts` regisztracio `sheet_svg` artifactkent, sheet-indexhez
    kotve;
  - worker success path bovitese ugy, hogy a per-sheet SVG artifactok a run
    zarasa elott generalodjanak;
  - task-specifikus smoke a sikeres es hibas SVG generator agakra.
- Nincs benne:
  - `sheet_dxf`, `bundle_zip`, `machine_program` vagy egyeb export artifact;
  - nagy `api/routes/runs.py` redesign;
  - uj frontend viewer workflow vagy uj UI contract;
  - manufacturing preview / toolpath render;
  - projection schema nagy bovitese, ha a jelenlegi `run_artifacts` +
    `sheet_index` metadata eleg a basic renderhez.

### Talalt relevans fajlok
- `worker/main.py`
  - a H1-E6-T1 ota mar megvan a canonical projection write + `done` zaras;
    ide kell a sheet SVG artifact generalast a megfelelo worker-lepesbe bekotni.
- `worker/result_normalizer.py`
  - innen latszik a projection truth alakszerkezete (`sheets`, `placements`,
    `transform_jsonb`, `bbox_jsonb`, `metrics`).
- `worker/raw_output_artifacts.py`
  - minta arra, hogyan nezzen ki kulon artifact helper boundary es determinisztikus
    storage/regisztracios logika.
- `api/services/geometry_derivative_generator.py`
  - a `viewer_outline` derivative JSON szerkezete itt definialt, ezt kell a
    renderelheto outline forrasakent felhasznalni.
- `api/routes/runs.py`
  - a jelenlegi `/viewer-data` mar felismeri a `.svg` artifactokat filename +
    `sheet_index` metadata alapjan; ezert a tasknak nem kell nagy route-redesign,
    csak kompatibilis artifactokat kell eloallitani.
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
  - kimondja, hogy a `ViewerSvgArtifact` artifact, nem source of truth, es a
    projection alapjan ujraepitheto.
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
  - kimondja, hogy a viewer source of truth projection adat, nem maga az SVG.
- `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md`
  - a runbol szuletett file/blob artifactok canonical bucketje a `run-artifacts`.
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
  - H1 artifact/viewer minimum elvarasok.
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - H1-E6-T2 source-of-truth.

### Konkret elvarasok

#### 1. Legyen explicit sheet SVG generator boundary
A viewer SVG generalas ne maradjon szetszorva a workerben.

Hasznalj explicit worker-oldali helper/modult, peldaul:
- `worker/sheet_svg_artifacts.py`
- vagy ezzel egyenerteku, jol tesztelheto boundary.

A helper minimum felelossege:
- a rendereleshez szukseges sheet/placement/geometria indexek felallitasa;
- per-sheet SVG szoveg/payload eloallitasa;
- canonical filename + storage path generalasa;
- artifact upload + `run_artifacts` regisztracio boundaryja;
- worker szamara visszaadhato summary (pl. hany sheet SVG keszult, melyik
  sheet-indexhez milyen artifact keszult).

#### 2. A rendereles projection truth-ra uljon, ne raw solver outputra
A task ne olvassa vissza ujra a raw `solver_output.json`-t SVG generalasra.

A minimum elvart adatforras:
- H1-E6-T1 projection output (`run_layout_sheets` / `run_layout_placements`
  szerkezete vagy a workerben meglevő projection objektum);
- snapshot manifest truth a geometriak feloldasahoz;
- `viewer_outline` derivative payload a renderelheto outline-hoz.

A part-shape forras ne legyen:
- raw solver output geometriarajz;
- `nesting_canonical` visszafejtese, ha a `viewer_outline` mar elerheto;
- ad hoc bbox-teglalap render, ha a viewer outline truth megvan.

Ha valamely placementhez nem oldhato fel ervenyes `viewer_outline` derivative,
legyen determinisztikus task-hiba, ne csendes ures rajz.

#### 3. Az SVG contract legyen egyszeru, de determinisztikus
A H1 minimum SVG legyen stabilan renderelheto es ujrageneralhato.

Minimum elvart:
- per hasznalt sheet egy SVG dokumentum;
- root `<svg>` `viewBox` es meret a sheet `width_mm` / `height_mm` alapjan;
- legalabb egy sheet boundary/background;
- placementenkent kulon SVG csoport/elem, amely a placement transzformaciot
  koveti (`translate` + `rotate` vagy ezzel egyenerteku stabil forma);
- a geometriak a `viewer_outline.outline.outer_polyline` + `hole_outlines`
  alapjan rajzolodjanak;
- `fill-rule="evenodd"` vagy ezzel egyenerteku hole-kompatibilis render;
- determinisztikus elem-sorrend (sheet_index, placement_index, part_revision_id)
  a stabil diff/hash erdekeben.

Nem cel most a tokeletes stilus vagy UX. Eleg a tiszta alap render, amelybol a
viewer basic render mar lehetseges.

#### 4. Az artifact persistence legyen canonical es viewer-route kompatibilis
A generalt SVG artifactok `app.run_artifacts` ala keruljenek.

Minimum elvart:
- bucket: canonical run artifact bucket (`run-artifacts`);
- artifact type / kind: `sheet_svg`;
- filename legyen stabil es route-kompatibilis, peldaul `out/sheet_001.svg` vagy
  ezzel egyenerteku, egyertelmu naming;
- a regisztracio tartalmazza a `sheet_index` metadata truth-ot;
- az upload/regisztracio legyen retry-biztos es ugyanarra a sheetre idempotensen
  lecserelheto.

Jo H1 minimum irany:
- storage pathban szerepeljen `project_id`, `run_id`, `sheet_svg`, es valamilyen
  tartalomhoz kotott digest;
- metadata-ban legyen legalabb `filename`, `size_bytes`, `sheet_index`,
  `content_sha256`, es `legacy_artifact_type='sheet_svg'`.

#### 5. A worker lifecycle-be jo helyre keruljon
A worker success path H1 minimum sorrendje igy nezzen ki:
1. solver futas,
2. raw artifact persistence,
3. result normalizer + projection write,
4. sheet SVG artifact generator,
5. run `done` zaras.

Mivel ez a task mar a H1 basic viewer render resze, a canonical success path ne
hallgassa el a generator hibat. Ha a task vallalja, hogy futas utan viewer SVG
elerheto, akkor SVG generalasi/regisztracios hiba eseten a run ne menjen csendben
`done` allapotba.

#### 6. A task ne csusszon at DXF/export vagy frontend-redesign scope-ba
Ebben a taskban meg nincs:
- sheet DXF generalas;
- bundle zip;
- manufacturing preview SVG;
- placement projection schema nagy attervezese;
- frontend komponensek atirasa.

A cel csak annyi, hogy a jelenlegi viewer route mar talaljon es ki tudjon
szolgalni sheet SVG artifactokat.

#### 7. A smoke script bizonyitsa a fo render es artifact agakra
Legyen task-specifikus smoke, amely fake snapshot + fake projection + fake
storage/DB gateway mellett legalabb ezt bizonyitja:
- per hasznalt sheet pontosan egy SVG jon letre;
- az SVG a sheet mereteit es a placement transzformaciokat koveti;
- a `viewer_outline` hole-os geometria is renderelheto;
- az artifact filename/sheet_index metadata route-kompatibilis;
- ugyanarra a bemenetre az SVG payload es a storage/regisztracios kimenet
  determinisztikus;
- hiba jon, ha hianyzik a `viewer_outline` vagy ervenytelen a placement/sheet
  kapcsolat;
- a smoke nem igenyel valos Supabase kapcsolatot vagy frontendet.

### DoD
- [ ] Keszul explicit worker-oldali sheet SVG generator helper/boundary.
- [ ] A generator a projection truth + snapshot geometry/viewer derivative alapjan renderel, nem raw solver outputbol.
- [ ] Per hasznalt sheet legalabb egy deterministic SVG dokumentum generalodik.
- [ ] A geometriak a `viewer_outline` derivative-bol rajzolodnak, hole-kompatibilis renderrel.
- [ ] Az artifactok `sheet_svg` artifactkent a canonical run-artifacts bucketbe kerulnek.
- [ ] A regisztracio route-kompatibilis `filename` + `sheet_index` metadata truth-ot ad.
- [ ] Az upload/regisztracio ugyanarra a sheetre retry-biztos/idempotens replace viselkedest ad.
- [ ] A worker success path a sheet SVG generator utan zarja `done`-ra a runt.
- [ ] A task nem csuszik at DXF/export/manufacturing vagy nagy frontend/redesign scope-ba.
- [ ] Keszul task-specifikus smoke a sikeres es hibas SVG-generator agakra.
- [ ] A checklist es report evidence-alapon ki van toltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h1_e6_t2_sheet_svg_generator_h1_minimum.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a rendereles ujra raw solver outputra ulne, es megkerulne a H1-E6-T1
    projection truth-ot;
  - a generator bbox-teglalapokat rajzolna a `viewer_outline` helyett;
  - a route nem talalja meg az artifactokat, mert a filename/sheet-index metadata
    nem kompatibilis;
  - SVG hiba mellett a worker megis `done` allapotba megy.
- Mitigacio:
  - explicit helper/boundary;
  - deterministic filename + metadata policy;
  - smoke-ban fedett render/idempotencia/error agak;
  - reportban egyertelmu scope-hatarok.
- Rollback:
  - a helper/worker/smoke/report/checklist diff egy task-commitban
    visszavonhato;
  - schema-modositas csak akkor johet, ha a meglavo metadata-utas megoldas nem
    eleg, es ezt a reportban ki kell mondani.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h1_e6_t2_sheet_svg_generator_h1_minimum.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile worker/main.py worker/sheet_svg_artifacts.py worker/result_normalizer.py worker/raw_output_artifacts.py scripts/smoke_h1_e6_t2_sheet_svg_generator_h1_minimum.py`
  - `python3 scripts/smoke_h1_e6_t2_sheet_svg_generator_h1_minimum.py`

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
- `worker/raw_output_artifacts.py`
- `api/services/geometry_derivative_generator.py`
- `api/routes/runs.py`
