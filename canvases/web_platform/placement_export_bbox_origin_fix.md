# Placement export bbox origin fix

## Funkcio
A feladat celzott hibajavitas a web_platform worker eredmeny-projekcio es
sheet export retegben. A konkret cel, hogy a negativ lokalis koordinataju
geometriak ugyanazzal a placement referenciaval legyenek kezelve a normalizer,
a sheet SVG export es a sheet DXF export oldalakon, igy a projectalt bbox es a
vizualis kimenet egymassal konzisztens legyen.

A task a mostani probafutasban kijott ket tunetet valasztja szet:
- **valodi bug:** a korok kilognak a sheetbol, mert a worker export/projekcio a
  nyers lokalis geometriat rajzolja ki a bbox-min referenciara epulo placement
  mellett;
- **nem ennek a tasknak a bugja:** a haromszogek nem fordulnak egymasba, mert a
  jelenlegi `rust/vrs_solver` bbox-alapu kontroll solver, nem shape-aware
  nesting motor.

Ez a task tehat javitja a placement/export referenciahibat, es regressziosan
bizonyitja, hogy a nem nulla rotation vegigmegy a pipeline-on es a worker
korrektul alkalmazza, **de nem** vezeti be a valodi shape-aware rotation
valasztast.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - a `run_layout_placements.bbox_jsonb` szamitas referenciajanak javitasa;
  - a sheet SVG export referenciajanak javitasa negativ `bbox.min_x/min_y`
    geometriakra;
  - a sheet DXF export referenciajanak javitasa ugyanerre az esetre;
  - kozos, determinisztikus placement-transform szemantika bevezetese a worker
    oldalon;
  - regresszios smoke, amely negativ lokalis bbox-os geometria + nem nulla
    rotation eseten is bizonyitja a helyes bbox/projekcio/export viselkedest;
  - explicit dokumentacio a rotation korlatrol: a worker alkalmazza a kapott
    rotaciot, de a solver tovabbra is bbox-kontroll solver.
- Nincs benne:
  - uj shape-aware solver vagy solvercsere;
  - a `rust/vrs_solver` heuristikajanak atirasa;
  - viewer-data `10x10` placeholder meretek kulon javitasa;
  - runs API vagy frontend redesign;
  - manufacturing / postprocess / H2-H3 feature-bovites.

### Talalt relevans fajlok
- `worker/result_normalizer.py`
  - itt keszul a `run_layout_placements.bbox_jsonb`; a jelenlegi `_transform_bbox`
    a nyers geometry bbox sarkait transzformalja, es nem a bbox-min referenciara
    normalizalt lokalis teglalappal dolgozik.
- `worker/sheet_svg_artifacts.py`
  - a `_transform_point` / `_transform_ring` jelenleg a nyers `viewer_outline`
    pontokat forgatja-es tolja el, bbox-min kompenzacio nelkul.
- `worker/sheet_dxf_artifacts.py`
  - ugyanaz a problema a `nesting_canonical` geometriaval es a DXF kimenettel.
- `worker/main.py`
  - a normalizer -> sheet SVG -> sheet DXF success path itt van osszekotve; a
    tasknak a meglevo sorrendet kell megtartania.
- `api/services/geometry_derivative_generator.py`
  - a `nesting_canonical` derivative payload a forras arra, hogy a part
    geometria lokalis koordinatai nem feltetlenul `0,0`-bol indulnak;
    a `placement_hints.origin_ref` szemantikat ehhez kell konzisztensen
    ervenyesiteni.
- `docs/solver_io_contract.md`
  - a solver output `x`, `y`, `rotation_deg` contract itt a source-of-truth.
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
  - a projection truth es az artifact ujraepitesi boundary forrasa.
- `canvases/web_platform/h1_e6_t1_result_normalizer_h1_minimum.md`
  - a canonical projection truth eredeti taskja.
- `canvases/web_platform/h1_e6_t2_sheet_svg_generator_h1_minimum.md`
  - az SVG artifact boundary eredeti taskja.
- `canvases/web_platform/h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.md`
  - a DXF artifact boundary eredeti taskja.

### Konkret elvarasok

#### 1. A placement referencia legyen egyetlen, kozosen hasznalt truth
A worker oldalon legyen egyertelmu, hogy a current platform szemantikaban a
solver output `x,y` placementje a part **bbox-min corner** referenciara ul.

A fix jo iranya:
- a geometry lokalis pontjai es/vagy bbox-a elott legyen explicit `base_x,
  base_y` kompenzacio;
- ez a `base` a part lokalis bbox minimuma;
- a global transform szemantikaja legyen mindenhol ugyanaz:
  `R(local_point - base) + translation`.

A task jo megoldasa lehet:
- kozos worker helper/modul bevezetese a placement transzformaciohoz,
  **vagy**
- ha tenyleg indokolt, ugyanazon szemantika nagyon fegyelmezett inline
  alkalmazasa.

A lenyeg: a normalizer, az SVG export es a DXF export ne eltero lokalis
referenciaval dolgozzon.

#### 2. A `bbox_jsonb` a normalizalt lokalis bbox-bol szamolodjon
A `worker/result_normalizer.py` ne a nyers `min_x/min_y/max_x/max_y` sarkokat
transzformalja kozvetlenul, mert igy a negativ lokalis minimumok duplan
beszamitodnak a global bbox-ba.

Minimum elvart:
- a projectalt bbox a `0..width` x `0..height` normalizalt lokalis teglalapbol
  szamolodjon;
- a `width` / `height` maradjon a geometry truth-bol;
- a kapott `bbox_jsonb` ugyanazt a sheet-beli helyzetet irja le, amit az export
  tenylegesen kirajzol.

#### 3. Az SVG es DXF export ugyanazt a base-offset korrekciot alkalmazza
A `viewer_outline` es a `nesting_canonical` geometriak tovabbra is maradhatnak
nyers lokalis koordinatakban, de az export retegnek ezt korrektul kell
kezelnia.

Minimum elvart:
- a sheet SVG export a negativ lokalis koordinataju koroket mar teljesen a
  sheeten belul rajzolja ki, ha a projection szerint bent vannak;
- a sheet DXF export ugyanarra a bemenetre ugyanazt a sheet-beli poziciot adja,
  mint az SVG export;
- a ket export kozt ne maradjon rejtett elteres a referencia-kezelest illetoen.

#### 4. Legyen explicit out-of-sheet guard a projection truth-ban
A task ne csak szebb SVG-t rajzoljon, hanem tegye kimondhatova, ha a projection
valojaban kilog a sheetbol.

Jo minimum elvaras:
- a normalizer (vagy a kozos placement helper) tudjon determinisztikusan
  hibazni, ha a projectalt bbox a sheet `0..width_mm`, `0..height_mm`
  tartomanyan kivulre kerul egy dokumentalt, kicsi epsilonon tul;
- emiatt a worker ne zarjon `done` allapotra olyan run-t, amelynek a canonical
  projectionja valojaban ervenytelen.

Ez a guard nem overlap validator es nem uj nesting quality engine; csak a
placement/reference hiba elleni vedohalo.

#### 5. A rotation bugot a task helyesen keretezze
A taskban kulon ki kell mondani es smoke-kal bizonyitani, hogy:
- a worker **nem veszi el** a solver altal adott `rotation_deg` erteket;
- ha a projectionben egy placement `180.0` fokos, akkor a normalizer/export
  reteg azt vegigviszi es korrektul alkalmazza;
- a jelenlegi `rust/vrs_solver` tovabbra is bbox-alapu, ezert ez a task **nem**
  kovetelheti meg, hogy a haromszogek shape-aware modon automatikusan 180 fokra
  forduljanak.

Tehat a regresszio teszt ne azt bizonyitsa, hogy a solver uj orientaciot valaszt,
hanem azt, hogy a worker reteg helyesen kezeli a nem nulla rotaciot.

#### 6. A worker lifecycle maradjon kovetkezetes
A success path sorrendje maradjon:
1. solver futas,
2. raw artifact persistence,
3. result normalizer,
4. sheet SVG artifactok,
5. sheet DXF artifactok,
6. run `done` zaras.

Ha a bbox/reference fix miatt uj validacios hiba jon elo, a run ne menjen csendben
`done` allapotba.

#### 7. A smoke script bizonyitsa a fo invariansokat
Legyen task-specifikus smoke, amely fake snapshot + fake projection/snapshot
geometriak mellett legalabb ezt bizonyitja:
- negativ lokalis bbox-os geometria eseten a normalizer bbox a helyes sheet-beli
  teglalapot adja;
- ugyanarra az esetre a sheet SVG es sheet DXF export ugyanarra a helyre rajzol;
- nem nulla (`180.0`) rotation eseten a bbox/projekcio/export kovetkezetes;
- a guard hibazik, ha a projectalt bbox kicsuszik a sheetbol;
- a smoke nem igenyel valos solver binaryt vagy Supabase kapcsolatot.

### DoD
- [ ] A worker placement referenciaja (`bbox_min_corner`) explicit es kovetkezetes truth-ra kerul.
- [ ] A `worker/result_normalizer.py` a projectalt bbox-ot a normalizalt lokalis bbox-bol szamolja.
- [ ] A `worker/sheet_svg_artifacts.py` a lokalis bbox-min base offsettel, helyesen exportal.
- [ ] A `worker/sheet_dxf_artifacts.py` ugyanazzal a placement szemantikaval exportal, mint az SVG.
- [ ] A canonical projection es a tenyleges SVG/DXF export ugyanarra a sheet-beli helyzetre mutat.
- [ ] A task bevezet determinisztikus out-of-sheet guardot a referenciahiba elfedese ellen.
- [ ] A task regressziosan bizonyitja, hogy a worker helyesen alkalmazza a nem nulla `rotation_deg` erteket.
- [ ] A task explicit kimondja, hogy a shape-aware rotation valasztas tovabbra is out-of-scope, mert a jelenlegi solver bbox-alapu.
- [ ] Keszul task-specifikus smoke script.
- [ ] Checklist es report evidence-alapon frissitve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/placement_export_bbox_origin_fix.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a fix csak az SVG-t javitja, de a DXF vagy a canonical bbox mas szemantikan marad;
  - a worker veletlenul atirja a rotation szemantikat, mikozben csak a base-offsetet kellene javitani;
  - a task tulterjeszkedik solver-fejlesztes vagy viewer-redesign iranyba.
- Mitigacio:
  - kozos placement-transform truth;
  - normalizer + SVG + DXF egy taskban, kozos smoke-kal;
  - explicit out-of-scope deklaracio a solver rotation-policyra;
  - reportban kulon nevezd meg, hogy mi valodi bugfix es mi solver-korlat.
- Rollback:
  - a worker-oldali placement helper / normalizer / SVG / DXF / smoke diff egy
    commitban visszavonhato;
  - a solver es a route layer erintetlen marad.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/placement_export_bbox_origin_fix.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile worker/main.py worker/result_normalizer.py worker/sheet_svg_artifacts.py worker/sheet_dxf_artifacts.py scripts/smoke_placement_export_bbox_origin_fix.py`
  - `python3 scripts/smoke_placement_export_bbox_origin_fix.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `canvases/web_platform/h1_e6_t1_result_normalizer_h1_minimum.md`
- `canvases/web_platform/h1_e6_t2_sheet_svg_generator_h1_minimum.md`
- `canvases/web_platform/h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.md`
- `docs/solver_io_contract.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `worker/main.py`
- `worker/result_normalizer.py`
- `worker/sheet_svg_artifacts.py`
- `worker/sheet_dxf_artifacts.py`
