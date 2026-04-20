# DXF Prefilter E2-T6 — Acceptance gate V1

## Cel
A DXF prefilter lane-ben a T5 altal eloallitott **normalized DXF artifact**
kapjon vegre egy kulon, determinisztikus **acceptance gate backend reteget**,
amely a fajlt a **tenyleges importer + validator lancon** visszateszteli, es
csak ezutan mondja ki a V1 gate kimenetet:
- `accepted_for_import`
- `preflight_rejected`
- `preflight_review_required`

A T6 feladata nem DB persistence, nem API route, nem upload trigger es nem UI,
hanem a T1->T5 truth vilag utan az elso olyan lokalis, tiszta backend szolgaltatas,
amely mar tenyleges gate verdictet ad.

## Miert most?
A jelenlegi repo-grounded helyzet:
- a T1 inspect truth mar ad nyers inventoryt es contour/open/duplicate signalokat;
- a T2 role resolver mar ad canonical role truth-ot, `review_required_candidates`
  es `blocking_conflicts` strukturat;
- a T3 gap repair mar eloallitja a repair-aware working truth-ot es a
  `remaining_open_path_candidates` maradekot;
- a T4 duplicate dedupe mar eloallitja a `deduped_contour_working_set` cut-like truth-ot
  es a `remaining_duplicate_candidates` maradekot;
- a T5 mar eloallit local `normalized_dxf` artifactot es `skipped_source_entities`
  diagnosztikat, de **szandekosan nem** ad acceptance verdictet.

Ugyanakkor a mai kodban meg nincs kulon prefilter acceptance gate service,
amely:
- a T5 `normalized_dxf.output_path` artifactot ujra megnyitja a tenyleges importerrel,
- ugyanarra a canonical geometry + validator logikara ul, mint a jelenlegi
  geometry import/validation pipeline,
- de mindezt lokalis, DB-mentes, API-mentes modon teszi,
- es strukturalt gate kimenetet ad.

A T6 helyes iranya ezert:
- a normalized DXF artifactot **nem** source DXF-kent, hanem prefilter writer-kimenetkent kezelni;
- az importer probe-ot a meglevo `import_part_raw(...)` iranyba kotni;
- a canonical geometry + hash + bbox eloallitasnal **nem** ujraimplementalni a
  `api/services/dxf_geometry_import.py` logikat, hanem minimal public pure boundaryt nyitni;
- a validator probe-nal **nem** DB-s `create_geometry_validation_report(...)` utvonalat hasznalni,
  hanem a mar letezo validator logikat minimal public pure helperen keresztul ujrahasznalni;
- es ezek utan, determinisztikus precedence-szel verdictet hozni.

## Scope boundary

### In-scope
- Kulon backend acceptance gate service: `api/services/dxf_preflight_acceptance_gate.py`.
- Minimal public pure helper boundary kinyitasa a meglevo pipeline-bol, hogy a gate
  ne private `_...` helper-ekre vagy kodduplikaciora epuljon:
  - `api/services/dxf_geometry_import.py`
  - `api/services/geometry_validation_report.py`
- A T5 `normalized_dxf.output_path` artifact visszatesztelese a tenyleges importerrel (`import_part_raw`).
- A normalized artifactbol local canonical geometry/bbox/hash truth eloallitasa ugyanazzal
  a normalizer-logikaval, mint amit a geometry import hasznal.
- Local validator probe ugyanazzal a validator-logikaval, mint amit a geometry validation report hasznal,
  de DB insert nelkul.
- Gate outcome precedence es explicit structured output:
  - `accepted_for_import`
  - `preflight_rejected`
  - `preflight_review_required`
- A gate reasons csaladok elkulonitese:
  - importer-fail reasons
  - validator-fail reasons
  - blocking reasons
  - review-required reasons
- Task-specifikus unit teszt + smoke.

### Out-of-scope
- `preflight_runs` / `preflight_artifacts` / DB persistence.
- API route, upload trigger, async worker, feature flag vagy frontend UI.
- Uj DXF parser vagy validator motor fejlesztese.
- T5 writer policy ujranyitasa (`canonical_layer_colors` boundary mar T5 truth).
- T7 diagnostics renderer scope teljes kinyitasa.
- E3 pipeline bekotes.

## Talalt relevans fajlok (meglevo kodhelyzet)
- `api/services/dxf_preflight_normalized_dxf_writer.py`
  - current-code truth: local normalized DXF artifact `output_path`-ra, writer metadata,
    `skipped_source_entities`, unresolved diagnostics, de nincs gate verdict.
- `api/services/dxf_preflight_role_resolver.py`
  - current-code truth: `review_required_candidates`, `blocking_conflicts`.
- `api/services/dxf_preflight_gap_repair.py`
  - current-code truth: `remaining_open_path_candidates`, `review_required_candidates`, `blocking_conflicts`.
- `api/services/dxf_preflight_duplicate_dedupe.py`
  - current-code truth: `remaining_duplicate_candidates`, `review_required_candidates`, `blocking_conflicts`.
- `vrs_nesting/dxf/importer.py`
  - current-code truth: `import_part_raw(...)` a tenyleges importer gate.
- `api/services/dxf_geometry_import.py`
  - current-code truth: a canonical geometry normalizer es hash logika itt van,
    de a lenyegi helper ma private (`_normalize_part_raw_geometry`, `_canonical_hash_sha256`).
- `api/services/geometry_validation_report.py`
  - current-code truth: a validator logika itt van,
    de a lenyegi payload-epito helper ma private (`_build_validation_payload`),
    a publikus entrypoint viszont DB insertet is csinal.
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
  - E1-T1 freeze; rogziti, hogy a prefilter acceptance gate a geometry import ele kerul.
- `docs/web_platform/architecture/dxf_prefilter_state_machine_and_lifecycle_model.md`
  - E1-T4 freeze; rogziti a canonical kimeneteket es a gate/outcome logikat.
- `canvases/web_platform/dxf_prefilter_e2_t5_normalized_dxf_writer_v1.md`
  - immediate predecessor; explicit mondja, hogy a T5 meg nem gate, a T6 mar igen.

## Jelenlegi repo-grounded helyzetkep
A T5 utan mar rendelkezesre all minden lenyegi input ahhoz, hogy a gate service
strukturalt verdictet hozzon:
- normalized DXF artifact path;
- source-of-truth diagnostics a role/gap/dedupe vilagbol;
- blocking vs review-required jelolesek;
- skipped writer signals;
- es a normalized file visszatesztelheto a meglevo importerrel.

Viszont ket kritikus current-code gap van:

### 1. A geometry import normalizer ma private helperre ul
A T6-nek a normalized DXF importer probe utan ugyanazt a canonical geometry
vilagot kell eloallitani, mint a meglevo geometry import service.
Ezert a helyes irany **nem** a normalizer logika ujrairasasa a gate service-ben,
hanem minimal public pure helper boundary kinyitasa a `dxf_geometry_import.py`-ban.

### 2. A geometry validator ma DB-side wrapperbe van csomagolva
A T6-nek ugyanazt a validator logikat kell hasznalnia, mint a geometry validation
report, de helyi verdicthez nem szabad DB insertet csinalnia.
Ezert a helyes irany itt is minimal public pure helper boundary,
nem a validator logika lemásolasa.

## Konkret elvarasok

### 1. Kulon acceptance gate service legyen, amely a T5 normalized artifactra ul
A T6 ne a source DXF-et olvassa ujra, hanem a T5 altal eloallitott
`normalized_dxf.output_path` artifactot.

A service bemenete minimum:
- `inspect_result`
- `role_resolution`
- `gap_repair_result`
- `duplicate_dedupe_result`
- `normalized_dxf_writer_result`

### 2. A gate a tenyleges importerrel teszteljen vissza
A normalized artifactot a meglevo `import_part_raw(...)` utvonalon kell visszatesztelni.
Ha ez elbukik, az outcome **mindig** `preflight_rejected`.

Elvart importer probe reteg minimum:
- `is_pass`
- `error_code` / `error_message` ha importer fail tortenik
- `outer_point_count`
- `hole_count`
- `source_entity_count`

### 3. A gate ugyanazzal a canonical geometry + validator logikaval dolgozzon, mint a jelenlegi pipeline
A T6-ben **nem** szabad private `_normalize_part_raw_geometry` vagy `_build_validation_payload`
helperre vakon importalni, es nem szabad a logikat lemásolni.

A helyes irany:
- `api/services/dxf_geometry_import.py` kapjon minimal public pure helper boundaryt a
  canonical geometry/bbox/hash eloallitashoz;
- `api/services/geometry_validation_report.py` kapjon minimal public pure helper boundaryt a
  local validator payload/status eloallitashoz;
- a T6 ezekre epuljon.

### 4. A gate outcome precedence legyen explicit es deterministic
Javasolt precedence:
1. strukturalis misuse / missing normalized artifact -> service-side hiba
2. importer fail -> `preflight_rejected`
3. validator status `rejected` -> `preflight_rejected`
4. barmely megmaradt blocking conflict -> `preflight_rejected`
5. importer+validator pass, de van review-required signal -> `preflight_review_required`
6. importer+validator pass, nincs blocking es nincs review signal -> `accepted_for_import`

Review-required signal minimum forrasai:
- `role_resolution.review_required_candidates`
- `gap_repair_result.review_required_candidates`
- `gap_repair_result.remaining_open_path_candidates`
- `duplicate_dedupe_result.review_required_candidates`
- `duplicate_dedupe_result.remaining_duplicate_candidates`
- `normalized_dxf_writer_result.skipped_source_entities`

Blocking signal minimum forrasai:
- `role_resolution.blocking_conflicts`
- `gap_repair_result.blocking_conflicts`
- `duplicate_dedupe_result.blocking_conflicts`

### 5. A T6 legyen az elso task, amely gate verdictet ad, de meg ne nyisson E3 scope-ot
A T6 output shape mar kimondhatja a canonical gate outcome-ot, de ez meg mindig
local service truth legyen, nem persistence/API/outbox world.

Minimum output shape:
- `acceptance_outcome`
- `normalized_dxf_echo`
- `importer_probe`
- `validator_probe`
- `blocking_reasons`
- `review_required_reasons`
- `diagnostics`

Kritikus boundary:
- nincs DB insert;
- nincs storage upload;
- nincs route response contract freeze;
- nincs feature flag/pipeline bekotes.

### 6. A teszteles fedje le a harom canonical outcome-ot
Minimum deterministic coverage:
- `accepted_for_import`: importer pass + validator pass + nincs blocking/review signal
- `preflight_rejected`: importer fail vagy validator reject vagy blocking conflict
- `preflight_review_required`: importer+validator pass, de review-required signal marad

A smoke legalabb egy teljes T1->T2->T3->T4->T5->T6 lancot bizonyitson.

### 7. Kulon legyen kimondva, mi marad a kovetkezo taskokra
A reportban es canvasban is legyen explicit:
- T7: diagnostics and repair summary renderer backend oldalon
- E3: persistence/API/upload bekotes
- E4: UI intake/review flow

## Erintett fajlok / celzott outputok
- `canvases/web_platform/dxf_prefilter_e2_t6_acceptance_gate_v1.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e2_t6_acceptance_gate_v1.yaml`
- `codex/prompts/web_platform/dxf_prefilter_e2_t6_acceptance_gate_v1/run.md`
- `api/services/dxf_preflight_acceptance_gate.py`
- `api/services/dxf_geometry_import.py`
- `api/services/geometry_validation_report.py`
- `tests/test_dxf_preflight_acceptance_gate.py`
- `scripts/smoke_dxf_prefilter_e2_t6_acceptance_gate_v1.py`
- `codex/codex_checklist/web_platform/dxf_prefilter_e2_t6_acceptance_gate_v1.md`
- `codex/reports/web_platform/dxf_prefilter_e2_t6_acceptance_gate_v1.md`
- `codex/reports/web_platform/dxf_prefilter_e2_t6_acceptance_gate_v1.verify.log`

## DoD
- [ ] Letrejott kulon backend acceptance gate service, amely a T5 normalized DXF artifactra ul.
- [ ] A gate a normalized artifactot a tenyleges `import_part_raw(...)` utvonalon visszateszteli.
- [ ] A canonical geometry/bbox/hash eloallitas nem kodduplikacioval, hanem minimal public helper boundaryval tortenik.
- [ ] A validator probe ugyanarra a validator logikara epul, mint a meglevo geometry validation report, DB insert nelkul.
- [ ] A service explicit outcome precedence-szel ad `accepted_for_import` / `preflight_rejected` / `preflight_review_required` verdictet.
- [ ] A service strukturalt `blocking_reasons` es `review_required_reasons` outputot ad.
- [ ] A task nem nyitotta meg a persistence / route / upload trigger / UI scope-ot.
- [ ] Keszult task-specifikus unit teszt, amely lefedi a 3 canonical outcome-ot.
- [ ] Keszult task-specifikus smoke, amely a teljes T1->T6 local lancot bizonyitja.
- [ ] A checklist es report evidence-alapon frissult.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e2_t6_acceptance_gate_v1.md` PASS.

## Kockazat + rollback
- Kockazat:
  - a gate elkezd private helper-ekre vagy kodmasolatra ulni;
  - a review-required es blocking signalok precedence-e keveredik;
  - a T6 idovel elott E3 persistence/API scope-ba csuszik.
- Mitigacio:
  - minimal public pure helper boundary, nem private import es nem duplikacio;
  - explicit precedence tablazat a canvasban, tesztben es reportban;
  - output shape local marad, nincs DB/API oldal.
- Rollback:
  - az uj gate service + helper-promocio + teszt + smoke egy task-commitban visszavonhato a T1->T5 lane truth erintese nelkul.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e2_t6_acceptance_gate_v1.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile api/services/dxf_preflight_acceptance_gate.py api/services/dxf_geometry_import.py api/services/geometry_validation_report.py tests/test_dxf_preflight_acceptance_gate.py scripts/smoke_dxf_prefilter_e2_t6_acceptance_gate_v1.py`
  - `python3 -m pytest -q tests/test_dxf_preflight_acceptance_gate.py`
  - `python3 scripts/smoke_dxf_prefilter_e2_t6_acceptance_gate_v1.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
- `docs/web_platform/architecture/dxf_prefilter_state_machine_and_lifecycle_model.md`
- `docs/web_platform/architecture/dxf_prefilter_error_catalog_and_user_facing_messages.md`
- `api/services/dxf_preflight_normalized_dxf_writer.py`
- `api/services/dxf_geometry_import.py`
- `api/services/geometry_validation_report.py`
- `vrs_nesting/dxf/importer.py`
- `canvases/web_platform/dxf_prefilter_e2_t5_normalized_dxf_writer_v1.md`
