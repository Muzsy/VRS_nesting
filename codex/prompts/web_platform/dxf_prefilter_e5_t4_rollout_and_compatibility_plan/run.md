Olvasd el az `AGENTS.md` szabalyait, es szigoruan a jelenlegi repo-grounded kodra epits.

Feladat:
Valositsd meg a `canvases/web_platform/dxf_prefilter_e5_t4_rollout_and_compatibility_plan.md`
canvasban leirt taskot a hozza tartozo YAML szerint.

Kotelezo elvek:
- Ne talalj ki uj backend vagy frontend feature-t. A helyes E5-T4 current-code modell: **docs/ops runbook task**.
- Ne hozz letre uj endpointot, migrationt, persistence-t, analytics pipeline-t vagy project-level rollout domaint.
- A dokumentum explicit a mar implementalt E3-T5 truthra epuljon: backend env flag, frontend build-time mirror, legacy fallback, replacement gate.
- Ne allitsd be a frontend flaget runtime toggle-kent; a mai truth build-time visibility gate.
- Ne tavolitsd el vagy refaktorald a legacy fallbackot. Csak a jelenlegi szerepet, rollback meneteit es a sunset criteria-t dokumentald.
- A smoke csak structural current-code truthot bizonyitson, ne probaljon deploymentet vagy valodi metrics pipeline-t futtatni.

Modellezesi elvek:
- A rollout terv ne altalanos best-practice lista legyen, hanem a repoban ma tenyleg meglevo mechanizmusok operationalizalasa.
- Az ON/OFF matrix legyen operator szintu: pontosan mi tortenik source finalize, replacement route, DXF Intake UI es projection truth szinten.
- A support/debug checklist legyen rovid, konkret es futtathato: milyen flaget, route-ot, smoke-ot, reportot kell nezni.
- A metrics szekcio current-code truthot mondjon: nevezze meg, mely mutatok nyerhetok ki mar a meglovo summary/diagnostics/report vilagbol, es melyekhez kellene kesobbi observability.
- A sunset criteria legyen vilagos, de a helper tenyleges eltavolitasa maradjon out-of-scope.

Kulon figyelj:
- A dokumentum nevezze meg pontosan: `API_DXF_PREFLIGHT_REQUIRED`, `DXF_PREFLIGHT_REQUIRED`, `VITE_DXF_PREFLIGHT_ENABLED`.
- Mondd ki explicit, hogy rollout OFF eseten a `complete_upload` legacy direct geometry import helperre esik vissza.
- Mondd ki explicit, hogy rollout OFF eseten a `replace_file` gate-elve van.
- Mondd ki explicit, hogy rollout OFF eseten a DXF Intake route/CTA nem latszik.
- Ne igerj olyan compatibility garanciat, amit a repo nem bizonyit.
- A smoke tiltott allitaskent kezelje a project-level flaget es a runtime frontend config endpointot.

A feladat vegen kotelezoen fusson:
- `python3 scripts/smoke_dxf_prefilter_e5_t4_rollout_and_compatibility_plan.py`
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e5_t4_rollout_and_compatibility_plan.md`

A reportban kulon terj ki erre:
- miert docs/ops task a helyes E5-T4, nem uj feature;
- hogyan epit a terv a mar implementalt E3-T5 gate-re;
- mi a current compatibility guarantee es mi a legacy fallback szerepe;
- miert sunset criteria a helyes scope, nem a fallback helper removalja.
