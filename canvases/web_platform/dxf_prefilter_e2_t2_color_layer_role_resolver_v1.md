# DXF Prefilter E2-T2 — Color/layer role resolver V1

## Cel
A DXF prefilter lane inspect result objektumabol (E2-T1 output) szabalyvezerelt,
determinisztikus canonical role assignment reteg keszuljon. A role resolver a nyers
layer/szin/topology signalokbol tovabbfeldolgozhato role-resolved strukturaig jusson el,
de meg ne lepjen at repair / normalized DXF writer / acceptance gate / route / persistence
scope-ba.

## Miert most?
Az E2-T1 mar letrehozta a nyers inspect truth-ot:
- `api/services/dxf_preflight_inspect.py`
- `entity_inventory`, `layer_inventory`, `color_inventory`, `linetype_inventory`
- `contour_candidates`, `open_path_candidates`, `duplicate_contour_candidates`
- `outer_like_candidates`, `inner_like_candidates`, `diagnostics`

A kovetkezo lane-ek (E2-T3 gap repair, E2-T4 duplicate dedupe fix, E2-T5 normalized DXF writer,
E2-T6 acceptance gate) csak akkor lehetnek determinisztikusak, ha elotte mar kulon,
ellenorizheto role resolver donti el, hogy a nyers signalok milyen canonical role-vilagba
fordulnak.

## Scope boundary

### In-scope
- Kulon backend role resolver service az E2-T1 inspect result objektumra epitve.
- Minimal, in-memory rules profile boundary a T2-ben tenylegesen hasznalt mezökre.
- Explicit layer mapping + color-hint kezeles + topology-proxy hasznalat.
- Konfliktusdetektalas es review-required / blocking resolution signalok kialakitasa.
- Role-resolved entity/layer struktura eloallitasa repair es acceptance nelkul.
- Task-specifikus unit teszt + smoke.

### Out-of-scope
- DXF olvasas / parser / importer ujranyitasa vagy uj parser logika.
- Gap repair / auto-fix / contour merge / geometry modositas.
- Normalized DXF writer vagy artifact export.
- Acceptance gate, DB persistence, API route, upload trigger, frontend UI.
- Teljes rules profile persistence vagy owner/version domain.
- Linetype-first role dontes; a T2 fokusza layer + color + topology proxy.

## Talalt relevans fajlok (meglevo kodhelyzet)
- `api/services/dxf_preflight_inspect.py`
  - current-code truth: inspect-only backend reteg, amely nyers inventory/candidate objektumot ad.
- `vrs_nesting/dxf/importer.py`
  - current-code truth: strict importer layer-konvencio (`CUT_OUTER`, `CUT_INNER`) es a T1-ben kinyitott minimal public inspect helper felulet.
- `tests/test_dxf_preflight_inspect.py`
  - current-code truth: deterministic JSON fixture coverage az inspect result alakjara.
- `scripts/smoke_dxf_prefilter_e2_t1_preflight_inspect_engine_v1.py`
  - current-code truth: inspect-only smoke, jo alap a T2 elohivasos smoke-hoz.
- `docs/web_platform/architecture/dxf_prefilter_domain_glossary_and_role_model.md`
  - E1-T2 output; rogziti a canonical role-vilagot (`CUT_OUTER`, `CUT_INNER`, `MARKING`) es a role-szintek szetvalasztasat.
- `docs/web_platform/architecture/dxf_prefilter_policy_matrix_and_rules_profile_schema.md`
  - E1-T3 output; rogziti a role-first policy elvet es a rules profile minimum mezoit.
- `docs/web_platform/architecture/dxf_prefilter_error_catalog_and_user_facing_messages.md`
  - E1-T7 output; rogziti a konfliktus/review/error csaladokat, de T2-ben meg nem user-facing translator a cel.
- `canvases/web_platform/dxf_prefilter_e2_t1_preflight_inspect_engine_v1.md`
  - immediate predecessor; rogziti, hogy a T1 inspect truth role assignment nelkul keszult.

## Jelenlegi repo-grounded helyzetkep
A T1 utan mar van eleg nyers signal a role resolverhez:
- pontos source layer nev;
- raw `color_index` inventory;
- contour/open-path/duplicate candidate lista;
- bbox-topology proxy (`outer_like_candidates` / `inner_like_candidates`).

Ugyanakkor a repoban jelenleg meg nincs kulon role resolver truth:
- nincs canonical role assignment service;
- nincs inspect result -> canonical role mapping boundary;
- nincs szabalyalapu konfliktusdetektalas a color/layer signalok kozt;
- nincs olyan output, amire a T3/T4/T5 ra tud ulni ugy, hogy ne kelljen ujra nyers signalokkal foglalkoznia.

Ezert a T2-ben a helyes irany egy kulon service reteg:
- bemenet: E2-T1 inspect result + egy egyszeru rules profile objektum;
- kimenet: role-resolved entity/layer set + konfliktus/review signalok;
- de meg mindig nincs geometry modositas es nincs acceptance dontes.

## Konkret elvarasok

### 1. A T2 a T1 inspect resultre epuljon, ne forrasfajlra
A role resolver ne hivja ujra kozvetlenul a DXF importert es ne olvasson fajlt.
A helyes boundary:
- bemenet: `inspect_result` (az `api/services/dxf_preflight_inspect.py` kimenete);
- bemenet: `rules_profile` vagy ezzel egyenerteku, T2-szintu dict/dataclass;
- kimenet: role-resolved struktura.

Ez biztositsa, hogy a T1 inspect truth kulon, ujrahasznalhato reteg maradjon.

### 2. Legyen kulon, minimal rules profile normalizer/validator a T2 altal tenylegesen hasznalt mezokre
A T2-ben csak azokat a mezoket szabad tenylegesen felhasznalni, amelyek a role resolverhez kellenek:
- `strict_mode`
- `interactive_review_on_ambiguity`
- `cut_color_map`
- `marking_color_map`

Megengedett, hogy a service egy minimal profile-normalizer/validator retegen keresztul dolgozzon,
de ez meg ne legyen persistence/API domain.
A T2 ne nyisson meg teljes owner-scoped profile/version adatmodellt.

### 3. A precedence egyertelmu legyen: explicit canonical layer > color hint > topology proxy
A role resolver dontesi sorrendje legyen explicit es tesztelt:
1. ha a source layer mar pontosan canonical (`CUT_OUTER`, `CUT_INNER`, `MARKING`), az legyen elsosegiu truth;
2. ha nincs explicit canonical layer, a color-hint policy adhasson `cut-like` vagy `marking-like` iranyt;
3. ha a layer/entity `cut-like`, de meg nem derul ki, hogy outer vagy inner, a T1 topology proxy (`outer_like_candidates` / `inner_like_candidates`) segitse a dontest;
4. ha ezek kozul egyik sem ad egyertelmu eredmenyt, review-required vagy blocking conflict keletkezzen a policy szerint.

A resolver ne talaljon ki tovabbi heuristikat a T1 inspect truth-on kivul.

### 4. A T2 explicit kezelje a layer/szin konfliktust
Legalabb ezeket a konfliktus-csaladokat kulon kell felismerni:
- explicit canonical layer kontra ellentmondo color hint;
- ugyanazon layeren/vagy ugyanazon entity-keszletben kevert `cut-like` es `marking-like` signal;
- topology proxy nem kompatibilis az explicit layerrel;
- nyitott path marad olyan layeren, amelyet a resolver cut role iranyba sorolna.

A kimenetben ezek ne acceptance hibakent, hanem role-resolution konfliktuskent jelenjenek meg.

### 5. A T2 kimenete legyen tovabbfeldolgozhato, de meg ne legyen acceptance outcome
A minimum output shape legyen kulon retegekre bontva, pl.:
- `rules_profile_echo`
- `layer_role_assignments`
- `entity_role_assignments`
- `resolved_role_inventory`
- `review_required_candidates`
- `blocking_conflicts`
- `diagnostics`

Kritikus boundary:
- nincs `accepted_for_import`;
- nincs `preflight_rejected`;
- nincs geometry rewrite;
- nincs normalized DXF artifact.

### 6. A resolvernek kulon kell kezelnie az open-path es a marking vilagot
Repo-grounded elv:
- nyitott entity lehet marking-jellegu;
- nyitott entity nem lehet csendben `CUT_OUTER`/`CUT_INNER` success.

Ezert legalabb ezt kell tudnia a T2-nek:
- ha egy layer vagy entity marking-like, attol meg lehet nyitott;
- ha egy layer/entity cut-like es T1 szerint open-path candidate van rajta, az legyen blocking vagy review-required a policy szerint;
- a T2 ne javitsa meg a nyitott konturt, csak jelezze.

### 7. A linetype csak raw signal maradjon, ne legyen T2-ben elsoosztalyu dontesi szabaly
A T1 mar hordozza a `linetype_name` raw signalokat.
A T2-ben ez meg csak diagnosztikai/evidence szerepu lehet.
Ne szülessen linetype-first role policy, hacsak a jelenlegi inspect truth ezt nem koveteli meg.

### 8. A role resolver legyen visszafele kompatibilis a jelenlegi importer truth-tal
Az explicit `CUT_OUTER` / `CUT_INNER` esetek ne romoljanak el.
A resolver ne irja felul agressziven a mar canonical source layereket.
A mostani importer strict vilag legyen a legkonnyebb, zold ut.

### 9. A teszteles fedje le a fontos dontesi csaladokat
A minimum task-specific coverage:
- explicit canonical layer mapping (`CUT_OUTER`, `CUT_INNER`, `MARKING`);
- color-hint fallback akkor, amikor nincs canonical layer;
- topology-proxy alapu outer/inner feloldas `cut-like` esetben;
- explicit layer vs color-hint konfliktus;
- cut-like layer open-path signalja -> nem success;
- ambiguous eset `interactive_review_on_ambiguity=true/false` policy alatt;
- legalabb egy scenario, ahol a resolver sikeres role-resolved outputot ad;
- legalabb egy scenario, ahol review-required objektum jon;
- legalabb egy scenario, ahol blocking conflict jon.

### 10. Kulon legyen kimondva, mi marad a kovetkezo taskokra
A reportban es canvasban is legyen explicit:
- T3: gap repair
- T4: duplicate contour dedupe mint modosito lepes
- T5: normalized DXF writer
- T6: acceptance gate

A T2-ben ezekhez csak a role-resolved truth keszul el.

## Erintett fajlok / celzott outputok
- `canvases/web_platform/dxf_prefilter_e2_t2_color_layer_role_resolver_v1.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e2_t2_color_layer_role_resolver_v1.yaml`
- `codex/prompts/web_platform/dxf_prefilter_e2_t2_color_layer_role_resolver_v1/run.md`
- `api/services/dxf_preflight_role_resolver.py`
- `tests/test_dxf_preflight_role_resolver.py`
- `scripts/smoke_dxf_prefilter_e2_t2_color_layer_role_resolver_v1.py`
- `codex/codex_checklist/web_platform/dxf_prefilter_e2_t2_color_layer_role_resolver_v1.md`
- `codex/reports/web_platform/dxf_prefilter_e2_t2_color_layer_role_resolver_v1.md`
- `codex/reports/web_platform/dxf_prefilter_e2_t2_color_layer_role_resolver_v1.verify.log`

## DoD
- [ ] Letrejott kulon backend role resolver service, amely az E2-T1 inspect result objektumra ul.
- [ ] A T2-ben tenylegesen hasznalt rules profile mezok minimal validator/normalizer hataron mennek at.
- [ ] Az explicit canonical layer mapping precedence-t elvez a color hint es topology proxy felett.
- [ ] A color-hint policy tud `cut-like` es `marking-like` iranyt adni canonical layer hianyaban.
- [ ] A topology proxy determinisztikusan segit outer vs inner feloldasban, de nem talal ki uj nyers signalokat.
- [ ] A resolver kulon listazza a `layer_role_assignments` / `entity_role_assignments` / `review_required_candidates` / `blocking_conflicts` retegeket.
- [ ] A task nem nyitotta meg a repair / normalized DXF writer / acceptance gate / route / persistence / UI scope-ot.
- [ ] Az explicit `CUT_OUTER` / `CUT_INNER` current-code truth tovabbra is zold ut marad.
- [ ] Keszult task-specifikus unit teszt es smoke script.
- [ ] A checklist es report evidence-alapon frissult.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e2_t2_color_layer_role_resolver_v1.md` PASS.

## Kockazat + rollback
- Kockazat:
  - a T2 idovel elott belecsuszik repair vagy acceptance gate scope-ba;
  - a color policy tul agressziv lesz es felulirja a mar canonical source layereket;
  - a topology-proxy tul sokat "okoskodik" es a nyers inspect truth helyett uj heurisztikat gyart.
- Mitigacio:
  - a resolver csak az E2-T1 inspect result altal hordozott signalokra tamaszkodhat;
  - explicit precedence szabalyok legyenek tesztelve;
  - nincs geometry modositas, nincs acceptance outcome.
- Rollback:
  - az uj role resolver service + teszt + smoke egy task-commitban visszavonhato a T1 inspect truth erintese nelkul.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e2_t2_color_layer_role_resolver_v1.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile api/services/dxf_preflight_role_resolver.py tests/test_dxf_preflight_role_resolver.py scripts/smoke_dxf_prefilter_e2_t2_color_layer_role_resolver_v1.py`
  - `python3 -m pytest -q tests/test_dxf_preflight_role_resolver.py`
  - `python3 scripts/smoke_dxf_prefilter_e2_t2_color_layer_role_resolver_v1.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
- `docs/web_platform/architecture/dxf_prefilter_domain_glossary_and_role_model.md`
- `docs/web_platform/architecture/dxf_prefilter_policy_matrix_and_rules_profile_schema.md`
- `docs/web_platform/architecture/dxf_prefilter_state_machine_and_lifecycle_model.md`
- `docs/web_platform/architecture/dxf_prefilter_error_catalog_and_user_facing_messages.md`
- `api/services/dxf_preflight_inspect.py`
- `vrs_nesting/dxf/importer.py`
- `tests/test_dxf_preflight_inspect.py`
- `scripts/smoke_dxf_prefilter_e2_t1_preflight_inspect_engine_v1.py`
- `canvases/web_platform/dxf_prefilter_e2_t1_preflight_inspect_engine_v1.md`
