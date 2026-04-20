# DXF Prefilter E2-T3 — Gap repair V1

## Cel
A DXF prefilter lane-ben az inspect truth (E2-T1) es a canonical role-resolution truth (E2-T2)
alápjan keszuljon el a **determinista, csak egyertelmu eseteket javito gap repair backend reteg**.
A T3 feladata nem a teljes acceptance gate, nem a normalized DXF artifact es nem a duplicate contour
dedupe, hanem a residual open-path vilagbol a javithato, kis gap-ek felismerese, alkalmazasa es
naplozasa ugy, hogy a kesobbi T4/T5/T6 lane-ek mar egy repair-aware working truth-ra tudjanak ulni.

## Miert most?
A jelenlegi repo-grounded helyzet:
- az E2-T1 inspect engine mar tudja a nyers inventory/candidate truth-ot:
  - `entity_inventory`, `layer_inventory`, `color_inventory`, `linetype_inventory`
  - `contour_candidates`, `open_path_candidates`, `duplicate_contour_candidates`
  - `outer_like_candidates`, `inner_like_candidates`, `diagnostics`
- az E2-T2 role resolver mar kulon, determinisztikus canonical role-vilagot ad:
  - `layer_role_assignments`
  - `entity_role_assignments`
  - `resolved_role_inventory`
  - `review_required_candidates`
  - `blocking_conflicts`

Ugyanakkor a T3 szempontjabol a mai truth meg **nem eleg**:
- az inspect output csak `open_path_count` szintu osszegzest hordoz;
- nincs public, structured endpoint/path-level probe a residual open path chain-ekrol;
- a gap repair igy jelenleg nem tudna bizonyitottan megmondani, hogy mely ket chain-veg
  zarhato egyertelmuen `max_gap_close_mm` alatt.

Ezert a T3 helyes iranya:
- minimalisan kinyitni egy repair-safe public probe hatart a meglevo importer truth folott;
- erre epitve kulon backend gap-repair service-t irni;
- de meg **nem** belepni normalized DXF writer / acceptance gate / route / persistence / UI scope-ba.

## Scope boundary

### In-scope
- Kulon backend gap repair service a meglevo inspect + role-resolution truth-ra epitve.
- Minimal, T3-ban tenylegesen hasznalt rules profile boundary:
  - `auto_repair_enabled`
  - `max_gap_close_mm`
  - `strict_mode`
  - `interactive_review_on_ambiguity`
- Minimal public importer/probe bovites, hogy a residual open path chain-ek endpoint-level evidence-e
  determinisztikusan elerheto legyen.
- Cut-like layer/path vilagban a javithato gap candidate-ek felismerese.
- Csak egyertelmu, threshold alatti gap-ek automatikus zarasa.
- Applied repair summary + remaining unresolved gap signalok.
- Task-specifikus unit teszt + smoke.

### Out-of-scope
- Uj DXF parser vagy a meglevo importer truth lecserelese.
- Color/layer role policy ujranyitasa (T2 marad a canonical role truth).
- Duplicate contour dedupe (T4).
- Normalized DXF writer vagy artifact export (T5).
- Acceptance gate, `accepted_for_import` / `preflight_rejected` jellegu kimenet (T6).
- DB persistence, API route, upload trigger, frontend UI.
- Bizonytalan topology automatikus javitasa, tobb outer kozotti valasztas, review UX.

## Talalt relevans fajlok (meglevo kodhelyzet)
- `api/services/dxf_preflight_inspect.py`
  - current-code truth: inspect-only layer; ma csak `open_path_count` szintu outputot ad.
- `api/services/dxf_preflight_role_resolver.py`
  - current-code truth: canonical role assignment; mar elvalasztja a cut-like vs marking-like reteget,
    de nem modosit geometriat.
- `vrs_nesting/dxf/importer.py`
  - current-code truth: az egyetlen parser/chaining truth a repoban;
  - relevans reszek:
    - `CHAIN_ENDPOINT_EPSILON_MM = 0.2`
    - `_chain_segments_to_rings(...)` belul mar csinal endpoint-level chaininget;
    - `probe_layer_rings(...)` ma rings + `open_path_count` shape-et ad, de a residual open path geometriat nem publikalja.
- `tests/test_dxf_importer_json_fixture.py`
  - current-code truth: mar bizonyitja, hogy az importer chaining reteg tud rings/open_paths kulonbseget tenni.
- `tests/test_dxf_preflight_inspect.py`
  - current-code truth: az inspect output shape stabil; a T3-nak erre kell ulni, vagy csak minimalisan boviteni.
- `tests/test_dxf_preflight_role_resolver.py`
  - current-code truth: a cut-like open-path mar konfliktusjel a role resolverben, de repair meg nincs mogotte.
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
  - E1-T1 freeze; rogziti, hogy a V1 csak egyertelmu gap fixet vegezhet `max_gap_close_mm` alatt.
- `docs/web_platform/architecture/dxf_prefilter_policy_matrix_and_rules_profile_schema.md`
  - E1-T3 freeze; rogziti a `max_gap_close_mm` es `auto_repair_enabled` szabalymezoket.
- `docs/web_platform/architecture/dxf_prefilter_error_catalog_and_user_facing_messages.md`
  - E1-T7 freeze; rogziti a repair-policy / ambiguity error csaladok helyet.
- `canvases/web_platform/dxf_prefilter_e2_t1_preflight_inspect_engine_v1.md`
  - immediate predecessor; explicit mondja, hogy a gap repair a T3 scope.
- `canvases/web_platform/dxf_prefilter_e2_t2_color_layer_role_resolver_v1.md`
  - immediate predecessor; explicit mondja, hogy geometry modositas tovabbra sincs a T2-ben.

## Jelenlegi repo-grounded helyzetkep
A meglevo importer mar egy implicit, nagyon szuk chaining-javitast csinal:
- `_chain_segments_to_rings(...)` a `CHAIN_ENDPOINT_EPSILON_MM` (0.2 mm) kuszob alatt osszelancolja a path-okat.
- Emiatt a T3 **nem** lehet egyszeruen a chaining epsilon ujracsomagolasa.
- A T3 helyes definicioja a chaining utan is megmarado, residual open path vilag **post-importer gap repairje**.

Kovetkezmeny:
- a T3 ne valtoztassa meg a `CHAIN_ENDPOINT_EPSILON_MM` truth-ot;
- a T3 sajat policy kuszobe a `max_gap_close_mm` legyen;
- a T3 csak azokra a residual gap-ekre dolgozzon, amelyeket a jelenlegi importer chaining mar nem oldott meg.

Masodik fontos current-code gap:
- a mai `probe_layer_rings(...)` output nem hordozza a residual `open_paths` geometriat,
  igy a T3 ma nem tud endpoint-levelen bizonyitani semmit.
- Ezt a tasknak minimal-invaziv modon kell megnyitnia: vagy ugyanazon public helper bovitesekent,
  vagy uj, inspect/repair-safe public probe fuggvennyel.

## Konkret elvarasok

### 1. A T3 ne uj parserre, hanem a meglevo importer truth-ra epuljon
A gap repair ne sajat DXF-olvasot vagy sajat chaining logikat epitsen.
A helyes boundary:
- a service a meglevo importer public feluleteit hasznalja (`normalize_source_entities`, plusz a T3-ban
  minimalisan megnyitott public path/open-path probe felulet);
- a service ne olvasson mas truth-ot, mint amit ugyanaz az importer mar hasznal;
- a T3 ne modositassa az importer strict `CUT_OUTER`/`CUT_INNER` acceptance logikat.

### 2. A T3 inputja az inspect + role-resolution truth legyen, de geometryhoz public probe-ot hasznalhat
A T3 service helyes boundary-ja:
- bemenet: `inspect_result`
- bemenet: `role_resolution`
- bemenet: minimal rules profile
- az esetleges ujraprobalas a forrasgeometriara csak az `inspect_result["source_path"]` / meglevo importer public helperen at mehessen

Indok:
- a T2 mar eldontotte, mely layer/path cut-like, marking-like vagy unassigned;
- a T3 mar geometry-modosito scope, ezert a residual open path geometriat vissza kell tudnia olvasni,
  de csak a meglevo importer truth-on keresztul.

### 3. A T3 csak cut-like residual open path vilagban dolgozzon
A gap repair V1 fokusza:
- csak olyan layer/path kerulhet repair vizsgalatba, amely a T2 szerint `CUT_OUTER` vagy `CUT_INNER`
  (vagy legalabb egyertelmuen cut-like role-ba lett sorolva);
- marking-like vagy unassigned layer/path ne kapjon csendes gap repairt;
- nyitott marking vilag tovabbra is megengedett lehet, de nem T3 feladata azt vagasi geometriava alakitani.

### 4. A javithatosag definicioja legyen explicit es szuk
Csak az legyen auto-repair candidate, ahol egyszerre teljesul:
- `auto_repair_enabled = true`
- a residual open path endpoint-par tavolsaga `<= max_gap_close_mm`
- a pairing egyertelmu (egy endpointnak nincs tobb, policy szerint azonos erossegu partner-jeloltje)
- a javitas csak egy egyszeru, explicit gap-bridge letrehozasat igenyli
- a javitas utan a path/ring probe ujrafuttatva konzisztens eredmenyt ad

Ami nem fer bele a T3 V1-be:
- tobb partner kozul heurisztikus valasztas
- tobb lepesis, branch-elosztasos topology helyreallitas
- self-intersection vagy outer/inner topology auto-fix
- silent repair marking/unassigned retegen

### 5. A T3 kimenete legyen repair-aware working truth, de meg ne artifact
A minimum output shape kulon retegeken adja vissza peldaul:
- `rules_profile_echo`
- `repair_candidate_inventory`
- `applied_gap_repairs`
- `repaired_path_working_set`
- `remaining_open_path_candidates`
- `review_required_candidates`
- `blocking_conflicts`
- `diagnostics`

Kritikus boundary:
- nincs normalized DXF file iras;
- nincs `accepted_for_import` vagy vegso lifecycle dontes;
- nincs DB/persistence/API side-effect.

A T3 altal eloallitott `repaired_path_working_set` legyen eleg a T4/T5 kovetkezo lane-eknek,
anelkul hogy meg egyszer ki kellene talalni, milyen gap fix tortent.

### 6. Az ambiguity kezelese legyen policy-vezerelt es evidence-alapu
Minimum konfliktus/review csaladok:
- `gap_repair_disabled_by_profile`
- `gap_candidate_over_threshold`
- `ambiguous_gap_partner`
- `gap_repair_topology_not_safe`
- `gap_repair_failed_reprobe`
- `cut_like_open_path_remaining_after_repair`

Policy:
- `interactive_review_on_ambiguity=true` -> ambiguity review-required retegbe menjen;
- `strict_mode=true` -> ugyanaz a csalad blocking retegbe kerulhessen, ha a V1 fail-fast policy ezt keri;
- a T3 ne emeljen acceptance outcome-ot, csak repair truth-ot es konfliktusjeleket adjon.

### 7. A T3 kulon reportolja, mi volt mar implicit importer chaining es mi az uj T3 repair
Ez kulcskovetelmeny.
A reportban es diagnosticsban kulon kell nevezni:
- hogy a meglevo importer chaining mar kezelt endpoint-kozeliteseket `CHAIN_ENDPOINT_EPSILON_MM` alatt;
- a T3 csak a residual open-path maradekvilagot vizsgalta;
- az `applied_gap_repairs` lista csak a T3 altal tenylegesen hozzadott repair-eket tartalmazza.

### 8. A teszteles fedje le a fontos repair csaladokat
Minimum deterministic coverage:
- auto-repair disabled -> nincs applied repair;
- egyetlen, threshold alatti, egyertelmu residual gap -> applied repair;
- gap tul nagy -> nincs repair, marad unresolved;
- tobb lehetseges partner -> review/blocking ambiguity;
- cut-like layeren a repair utan megszunik az open path;
- cut-like layeren a repair utan is marad open path -> explicit unresolved signal;
- marking-like open path nem kap csendes repairt;
- a T3 nem ad acceptance outcome-ot es nem ir DXF-et.

### 9. Kulon legyen kimondva, mi marad a kovetkezo taskokra
A reportban es canvasban is legyen explicit:
- T4: duplicate contour dedupe
- T5: normalized DXF writer
- T6: acceptance gate

A T3 csak a gap-repair-aware working truth-ot es diagnosticsot kesziti elo.

## Erintett fajlok / celzott outputok
- `canvases/web_platform/dxf_prefilter_e2_t3_gap_repair_v1.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e2_t3_gap_repair_v1.yaml`
- `codex/prompts/web_platform/dxf_prefilter_e2_t3_gap_repair_v1/run.md`
- `vrs_nesting/dxf/importer.py`
- `api/services/dxf_preflight_gap_repair.py`
- `tests/test_dxf_preflight_gap_repair.py`
- `scripts/smoke_dxf_prefilter_e2_t3_gap_repair_v1.py`
- `codex/codex_checklist/web_platform/dxf_prefilter_e2_t3_gap_repair_v1.md`
- `codex/reports/web_platform/dxf_prefilter_e2_t3_gap_repair_v1.md`
- `codex/reports/web_platform/dxf_prefilter_e2_t3_gap_repair_v1.verify.log`

## DoD
- [ ] Letrejott kulon backend gap repair service, amely inspect result + role resolution + minimal rules profile boundaryra ul.
- [ ] A T3-hoz szukseges residual open path geometry determinisztikusan elerheto public importer/probe feluleten.
- [ ] A service explicit kulonvalasztja a repair candidate inventoryt, az applied repair-eket, a remaining unresolved gap vilagot es a conflict/review reteget.
- [ ] Csak egyertelmu, threshold alatti residual gap javitas tortenik; nincs heurisztikus topology talalgatas.
- [ ] A service nem ir DXF-et, nem ad acceptance outcome-ot, nem nyit route/persistence/UI scope-ot.
- [ ] A diagnostics kulon nevezi a T3 uj repair-eit es a meglevo importer chaining truth-tol valo elvalasztast.
- [ ] Keszult task-specifikus unit teszt es smoke.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e2_t3_gap_repair_v1.md` PASS.

## Kockazatok / megjegyzesek
- A legfontosabb tervezesi kockazat, hogy a mai inspect output shape (`open_path_count`) nem eleg a T3-hoz.
  Ezert a tasknak minimalisan bovitett public importer/probe hatarra van szuksege.
- Nem szabad belecsuszni T4/T5 scope-ba:
  - duplicate dedupe nem itt keszul;
  - normalized DXF writer nem itt keszul;
  - acceptance gate nem itt keszul.
- Nem szabad felulirni a meglevo importer chaining epsilon truth-jat a T3 kedveert.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e2_t3_gap_repair_v1.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile vrs_nesting/dxf/importer.py api/services/dxf_preflight_gap_repair.py tests/test_dxf_preflight_gap_repair.py scripts/smoke_dxf_prefilter_e2_t3_gap_repair_v1.py`
  - `python3 -m pytest -q tests/test_dxf_preflight_gap_repair.py`
  - `python3 scripts/smoke_dxf_prefilter_e2_t3_gap_repair_v1.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
- `docs/web_platform/architecture/dxf_prefilter_policy_matrix_and_rules_profile_schema.md`
- `docs/web_platform/architecture/dxf_prefilter_state_machine_and_lifecycle_model.md`
- `docs/web_platform/architecture/dxf_prefilter_error_catalog_and_user_facing_messages.md`
- `api/services/dxf_preflight_inspect.py`
- `api/services/dxf_preflight_role_resolver.py`
- `vrs_nesting/dxf/importer.py`
- `tests/test_dxf_preflight_inspect.py`
- `tests/test_dxf_preflight_role_resolver.py`
- `tests/test_dxf_importer_json_fixture.py`
- `scripts/smoke_dxf_prefilter_e2_t1_preflight_inspect_engine_v1.py`
- `scripts/smoke_dxf_prefilter_e2_t2_color_layer_role_resolver_v1.py`
- `canvases/web_platform/dxf_prefilter_e2_t1_preflight_inspect_engine_v1.md`
- `canvases/web_platform/dxf_prefilter_e2_t2_color_layer_role_resolver_v1.md`
