# DXF Prefilter E2-T1 Preflight inspect engine V1

## Funkcio
Ez a task a DXF prefilter lane elso tenyleges backend-implementacios lepese.
A cel most **nem** javitas, **nem** role-resolver, **nem** acceptance gate es **nem**
API/persistence/UI bekotes, hanem egy olyan **nyers DXF inspect engine** letrehozasa,
amely a jelenlegi importerre epitve, javitas nelkul, determinisztikusan meg tudja mondani,
hogy a forrasfajlban mi van.

A tasknak a jelenlegi repora kell raulnie:
- ma a `vrs_nesting/dxf/importer.py` mar elvegzi a forrasfajl normalizalt entity-szintu
  olvasasat es a layer-szintu konturkepzest, de ezek a helper-ek belso (`_normalize_entities`,
  `_collect_layer_rings`) feluletek;
- ma a public `import_part_raw()` csak a vegso CUT_OUTER/CUT_INNER acceptance celra jo,
  es nem ad vissza inspect-szintu diagnosztikat;
- ma a normalized entity shape nem orzi meg stabilan a szin/linetype jellegu signalokat,
  pedig a prefight V1 taskbontas szerint a kesobbi lane-nek layer/szin/linetype inventoryra
  kell epulnie;
- ma a `api/services/dxf_geometry_import.py` kozvetlenul `import_part_raw()` utan a geometry
  import/normalizer/validator/derivative lancba lep tovabb;
- ma nincs kulon `api/services/dxf_preflight_inspect.py` vagy ezzel egyenerteku inspect service.

Ez a task azert kell most, hogy az E2-T2 role resolver, az E2-T3 gap repair es az E2-T6 acceptance gate
ne a route-okba vagy a geometry import service-be szorva kezdjenek el felderitest vegezni, hanem legyen egy
kulon, ujrafelhasznalhato inspect truth-reteg.

## Scope
- Benne van:
  - minimal, public importer-szintu inspect helper-felulet kinyitasa a meglvo belso parserre epitve;
  - normalized entity inventory bovitese a preflight szempontjabol fontos metaadatokkal (`layer`, `type`,
    `closed`, `color_index`, `linetype_name` vagy ezekkel egyenerteku, determinisztikus raw source mezok);
  - kulon preflight inspect service reteg bevezetese (`api/services/dxf_preflight_inspect.py` vagy
    ezzel egyenerteku fajl), amely nyers inspect result objektumot es diagnosztikai riportot allit elo;
  - layer/szin/linetype inventory;
  - konturjeloltek, zartsag/allapot, open-path jeloltek, duplikalt konturjeloltek,
    outer-like / inner-like jeloltek docs- es kod-szintu elkulonitese;
  - unit test + task-specifikus smoke a determinisztikus inspect bizonyitasara.
- Nincs benne:
  - color/layer role resolver es canonical role assignment (`CUT_OUTER`/`CUT_INNER`/`MARKING`) implementacio;
  - gap repair vagy barmilyen auto-fix;
  - normalized DXF ujrairo/writer;
  - acceptance gate es importer+validator visszateszteles;
  - `api/routes/files.py` vagy `api/services/dxf_geometry_import.py` pipeline-bekotes;
  - uj DB tabla, migration, persistence vagy API endpoint;
  - frontend diagnostics/review UI.

## Talalt relevans fajlok (meglevo kodhelyzet)
- `vrs_nesting/dxf/importer.py`
  - current-code truth: a parser/belso entity-normalizalo es layer-konturkepzo logika itt van;
    jelenleg a kulso vilag fele csak az `import_part_raw()` public felulet stabil.
- `api/services/dxf_geometry_import.py`
  - current-code truth: ma a file ingest utan kozvetlen geometry import/normalizer/validation/derivative
    folyik, nincs kulon preflight inspect lepes.
- `api/services/dxf_validation.py`
  - current-code truth: legacy readability probe; nem inspect truth.
- `api/routes/files.py`
  - current-code truth: a `complete_upload` utan geometry import task indul;
    ez a task **meg nem** nyul hozza, de a kesobbi E3 hook pontot ez adja.
- `tests/test_dxf_importer_json_fixture.py`
  - current-code truth: a JSON fixture backend a deterministic import smoke alapja;
    jo minta a preflight inspect backend-fuggetlen unit tesztjeihez.
- `tests/test_dxf_importer_error_handling.py`
  - current-code truth: a DxfImportError kodvilag es a hibaturo viselkedes mar tesztelt.
- `scripts/smoke_dxf_import_convention.py`
  - current-code truth: a minimum DXF importer smoke ma a public `import_part_raw()` acceptance vilagra ul.
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
  - E1-T1 output; rogziti, hogy a prefilter a geometry import ele kerulo acceptance gate lane lesz.
- `docs/web_platform/architecture/dxf_prefilter_domain_glossary_and_role_model.md`
  - E1-T2 output; rogziti a role-first vilagot es hogy az inspect meg role assignment elotti szelet.
- `docs/web_platform/architecture/dxf_prefilter_policy_matrix_and_rules_profile_schema.md`
  - E1-T3 output; rogziti, hogy a rules profile kesobb a raw signalokra ul, nem talalgatott role-okra.
- `docs/web_platform/architecture/dxf_prefilter_state_machine_and_lifecycle_model.md`
  - E1-T4 output; rogziti, hogy a preflight lifecycle kulon truth lesz, de E2-T1 meg nem persistence task.

## Jelenlegi repo-grounded helyzetkep
A jelenlegi kodban mar megvan a nyers DXF olvasas nagy resze, de az inspect worldhoz ket fontos hiany latszik:
1. nincs stabil public felulet az entity inventoryhoz es a layer-kontur probe-hoz;
2. a normalized entity shape nem hordozza megbizhatoan azokat a source signalokat,
   amelyekre a kesobbi role resolvernek es diagnosticsnak szuksege lesz.

Ezert a T1-ben a helyes irany nem egy masodik parser/service kitalalasa, hanem:
- a meglvo importer belso parser-logikajat minimalisan, visszafele kompatibilisen kinyitni;
- erre kulon inspect service reteget tenni;
- a szolgaltatas kimenetet ugy tervezni, hogy a T2/T3/T6 fel tudjon ra ulni,
  de meg ne keveredjen bele se role assignment, se javitas, se acceptance dontes.

## Konkret elvarasok

### 1. A preflight inspect engine a meglvo importerre epuljon, ne uj parserre
A taskban nem szabad uj DXF olvasasi logikat irni `api/services/` alatt.
A helyes irany:
- a raw source olvasast tovabbra is a `vrs_nesting/dxf/importer.py` vegezze;
- ha kell, minimal public helper extraction tortenjen a belso `_normalize_entities`
  es/vagy `_collect_layer_rings` korul;
- a service ezekre a helper-ekre epuljon.

### 2. A source signal inventory legyen tenylegesen hasznalhato a kesobbi lane-hez
A T1 minimuma, hogy a normalized entity inventory legalabb ezeket hordozza:
- `layer`
- `type`
- `closed`
- `color_index` vagy ezzel egyenerteku nyers szinjel
- `linetype_name` vagy ezzel egyenerteku nyers linetype-jel

Fontos:
- ez nem canonical color policy es nem UI-szin;
- ha a source backend nem ad explicit erteket, az inspect result jelolje ezt
  determinisztikusan `null`/`None` vagy egy egyertelmu raw placeholder formaban;
- ne tortenjen okoskodo ACI->RGB vagy BYLAYER policy-kitalalas ebben a taskban.

### 3. Az inspect result kulon valassza szet a nyers megfigyelest es a kesobbi dontesi reteget
A service kimenete legalabb ezeket a retegeket tartalmazza:
- `entity_inventory`
- `layer_inventory`
- `color_inventory`
- `linetype_inventory`
- `contour_candidates`
- `open_path_candidates`
- `duplicate_contour_candidates`
- `outer_like_candidates`
- `inner_like_candidates`
- `diagnostics`

A `diagnostics` itt meg technikai/inspect-szintu objektum;
nem user-facing catalog es nem acceptance outcome.

### 4. A konturjeloltek es zartsagdetektalas role assignment nelkul tortenjen
A T1-ben meg nem `CUT_OUTER`/`CUT_INNER` canonical role assignment a cel,
hanem az, hogy a nyers source alapjan latszodjon:
- mely layer(ek)en van zart ring-jelolt;
- hol maradt open-path;
- hol latszik egyertelmu duplikacio-jelolt;
- van-e topology alapjan kulso/belso jellegu ring-jelolt.

A vegso role-dontes a T2 feladata marad.

### 5. A task maradjon persistence- es route-fuggetlen
Ebben a taskban nem szabad:
- `api/routes/files.py`-t preflight triggerre atkotni;
- `api/services/dxf_geometry_import.py` lancat megnyitni;
- `preflight_runs` vagy mas uj DB truth-ot bevezetni.

A T1 vegeredmenye egy tiszta, hivhato backend inspect engine legyen,
amelyet a kesobbi E3 task majd a file upload flowba kot be.

### 6. A hibakezelesben ne torjon el a mai importer acceptance world
A public `import_part_raw()` viselkedese es a ma letezo importer smoke/test vilag
ne romoljon el. Ha a preflighthoz kell public importer helper, az legyen:
- minimalis;
- visszafele kompatibilis;
- kulon teszttel vedett.

### 7. A teszteles backend-fuggetlenul is bizonyitson
A minimum task-specific coverage:
- JSON fixture alapu unit tesztek, hogy `ezdxf` nelkul is reprodukalhato legyen;
- inspect result inventory + contour/open-path/duplicate candidate ellenorzes;
- legalabb egy olyan scenario, ahol a service nem acceptance errorral all le,
  hanem diagnosztikaban mutatja a nyers allapotot;
- legalabb egy hard-fail scenario (pl. nem olvashato input / unsupported units / invalid schema),
  ahol tovabbra is stabil importer-hiba jon.

### 8. Kulon legyen kimondva, mi marad a kovetkezo taskokra
A reportban es canvasban is legyen explicit:
- T2: role resolver
- T3: gap repair
- T4: duplicate dedupe javito lepes
- T5: normalized DXF writer
- T6: acceptance gate

A T1-ben ezeknek csak az inspect-input truth-ja keszul el.

## Erintett fajlok / celzott outputok
- `canvases/web_platform/dxf_prefilter_e2_t1_preflight_inspect_engine_v1.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e2_t1_preflight_inspect_engine_v1.yaml`
- `codex/prompts/web_platform/dxf_prefilter_e2_t1_preflight_inspect_engine_v1/run.md`
- `vrs_nesting/dxf/importer.py`
- `api/services/dxf_preflight_inspect.py`
- `tests/test_dxf_preflight_inspect.py`
- `scripts/smoke_dxf_prefilter_e2_t1_preflight_inspect_engine_v1.py`
- `codex/codex_checklist/web_platform/dxf_prefilter_e2_t1_preflight_inspect_engine_v1.md`
- `codex/reports/web_platform/dxf_prefilter_e2_t1_preflight_inspect_engine_v1.md`
- `codex/reports/web_platform/dxf_prefilter_e2_t1_preflight_inspect_engine_v1.verify.log`

## DoD
- [ ] Van minimal, public importer-felulet a raw inspect celra; nem uj parser logika keszult.
- [ ] A normalized entity inventory hordozza a preflight T1-hez szukseges `layer/type/closed/color/linetype` raw signalokat.
- [ ] Letrejott kulon backend inspect service (`api/services/dxf_preflight_inspect.py` vagy ezzel egyenerteku megoldas).
- [ ] A service inspect result objektumot ad vissza, kulon inventory es diagnostics reteggel.
- [ ] A service javitas nelkul tud konturjelolteket, open-path jelolteket, duplicate contour jelolteket es outer-like/inner-like jelolteket listazni.
- [ ] A task nem nyitotta meg a route/persistence/UI scope-ot.
- [ ] A mai `import_part_raw()` acceptance viselkedese nem romlott.
- [ ] Keszult task-specifikus unit teszt es smoke script.
- [ ] A checklist es report evidence-alapon frissult.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e2_t1_preflight_inspect_engine_v1.md` PASS.

## Kockazat + rollback
- Kockazat:
  - a task idovel elott beleszalad role resolver vagy auto-repair scope-ba;
  - az inspect kedveert parhuzamos parser logika szuletik;
  - az importer public felulete tul nagyra nyilik es destabilizalja a mai acceptance worldot.
- Mitigacio:
  - explicit tiltas a role assignment / repair / acceptance gate fele;
  - importer oldalon csak minimal helper extraction;
  - kulon unit tesztek a public inspect helperre es a meglevo `import_part_raw()`-ra.
- Rollback:
  - az importer minimal public inspect helper es az uj service/task-specifikus tesztek
    egy task-commitban visszavonhatok.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e2_t1_preflight_inspect_engine_v1.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile vrs_nesting/dxf/importer.py api/services/dxf_preflight_inspect.py tests/test_dxf_preflight_inspect.py scripts/smoke_dxf_prefilter_e2_t1_preflight_inspect_engine_v1.py`
  - `python3 -m pytest -q tests/test_dxf_preflight_inspect.py`
  - `python3 scripts/smoke_dxf_prefilter_e2_t1_preflight_inspect_engine_v1.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
- `docs/web_platform/architecture/dxf_prefilter_domain_glossary_and_role_model.md`
- `docs/web_platform/architecture/dxf_prefilter_policy_matrix_and_rules_profile_schema.md`
- `docs/web_platform/architecture/dxf_prefilter_state_machine_and_lifecycle_model.md`
- `docs/web_platform/architecture/dxf_prefilter_data_model_and_migration_plan.md`
- `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md`
- `vrs_nesting/dxf/importer.py`
- `api/services/dxf_geometry_import.py`
- `api/services/dxf_validation.py`
- `api/routes/files.py`
- `tests/test_dxf_importer_json_fixture.py`
- `tests/test_dxf_importer_error_handling.py`
- `scripts/smoke_dxf_import_convention.py`
