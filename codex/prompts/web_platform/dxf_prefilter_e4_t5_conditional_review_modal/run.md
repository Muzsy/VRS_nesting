Olvasd el az `AGENTS.md` szabalyait, es szigoruan a jelenlegi repo-grounded kodra epits.

Feladat:
Valositsd meg a `canvases/web_platform/dxf_prefilter_e4_t5_conditional_review_modal.md`
canvasban leirt taskot a hozza tartozo YAML szerint.

Kotelezo elvek:
- Ne talalj ki uj preflight review-decision API route-ot vagy persisted review-decision domaint.
- Ne talalj ki rules-profile save/update domaint.
- A helyes T5 current-code modell most: **conditional review modal = diagnostics-driven guidance + replacement upload entrypoint**.
- A replacement flow a mar letezo backend route-ra epul:
  `POST /projects/{project_id}/files/{file_id}/replace`
  majd signed upload, majd a meglevo `complete_upload` finalize a `replaces_file_object_id` bridge-dzsel.
- A page jelenlegi settings draftja replacement finalize-kor is menjen at `rules_profile_snapshot_jsonb`-kent.
- Ne torold vagy regresszald az E4-T4 diagnostics drawert.
- Ne nyiss accepted->parts, signed artifact download, redesign vagy NewRunPage scope-ot.

Modellezesi elvek:
- A review trigger csak akkor jelenjen meg / legyen aktiv, ha a file latest summaryja
  `preflight_review_required` es van `latest_preflight_diagnostics` payload.
- A review modal kulonuljon el a diagnostics drawertol; ne pusztan nevezd at a meglovo drawert.
- A modal a diagnostics truth review slice-at emelje ki:
  - review_required severity issue-k,
  - remaining review-required signals,
  - acceptance summary review allapot,
  - recommended action.
- A modal explicit, felhasznaloi nyelvu current-code disclaimer-t tartalmazzon arrol,
  hogy persisted review decision save meg nincs implementalva.
- A replacement UX legyen minimalis es deterministic:
  - file input,
  - upload allapot,
  - hiba allapot,
  - siker utan `loadData()` refresh.
- A replacement finalize ne bypassolja a meglevő flow-t; a complete_upload route-on menjen at.
- Ha replacement upload nincs kivalasztva, a modal akkor is hasznalhato maradjon read-only review summarykent.
- A diagnostics drawer tovabbra is megnyithato maradjon.

Kulon figyelj:
- ne allits tobbet a reviewrol, mint ami ma igaz;
- ne igerj save/apply decisions funkciot nem letezo backend nelkul;
- a feature flag / rollout gate logika mar bent van, ne vezesd be ujra maskepp;
- a frontend API helper a backend response shape-hez igazodjon (`replaces_file_id`, `storage_path`, stb.);
- a build forduljon.

A feladat vegen kotelezoen fusson:
- `python3 -m py_compile scripts/smoke_dxf_prefilter_e4_t5_conditional_review_modal.py`
- `python3 scripts/smoke_dxf_prefilter_e4_t5_conditional_review_modal.py`
- `npm --prefix frontend run build`
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e4_t5_conditional_review_modal.md`

A reportban kulon terj ki erre:
- miert guidance + replacement entrypoint a helyes T5 current-code modell;
- miert nem persisted review decision save;
- pontosan hogyan epul a replacement flow a meglevő backend route + finalize bridge-re;
- hogyan marad meg regresszio nelkul az E4-T4 diagnostics drawer.
