# Report — dxf_prefilter_e4_t5_conditional_review_modal

## Összefoglaló

Az E4-T5 egy külön, feltételes review modal UX-et vezet be a `DxfIntakePage`-en a
`preflight_review_required` állapotú fájlokra. A modal a persisted diagnostics truth review szeletét emeli ki,
és a jelenlegi rendszerben már létező replacement flow-ra ad explicit belépési pontot.

A task nem vezet be új review-decision persistence domaint vagy új review API route-ot.

## Miért guidance + replacement entrypoint a helyes T5 current-code modell

A repo current-code állapotban már létezik:
- diagnostics drawer (`latest_preflight_diagnostics` read-only megjelenítés),
- replacement backend route: `POST /projects/{project_id}/files/{file_id}/replace`,
- replacement finalize bridge: `complete_upload` + `replaces_file_object_id`.

Ezért a helyes T5 scope a review-required állapotú fájlokra:
- célzott review információk,
- explicit felhasználói guidance,
- és a már meglévő replacement útvonal bekötése.

## Miért nem persisted review decision save

A jelenlegi backendben nincs review decision mentési domain (`preflight_review_decisions` storage és hozzá route),
ezért a frontend nem ígér/imitál `save/apply decision` műveletet.

A modal explicit szöveggel jelzi: ez current-code szerint guidance + replacement upload entrypoint,
nem persisted review engine.

## Replacement flow pontos current-code bekötése

A modal replacement útvonala:
1. `replaceProjectFile(...)` hívás -> `POST /projects/{project_id}/files/{file_id}/replace`
2. signed upload az új replacement slotra
3. `api.completeUpload(...)` finalize a meglévő route-on
4. finalize payloadban bridge mezők:
   - `replaces_file_object_id: signed.replaces_file_id`
   - `rules_profile_snapshot_jsonb: rulesProfileSnapshot`
5. `loadData()` refresh a friss latest summary/diagnostics állapotért

## E4-T4 diagnostics drawer regressziómentes megtartása

Az E4-T4 drawer UX megmaradt:
- soronként továbbra is van `View diagnostics` trigger,
- a drawer továbbra is tartalmazza a fő blokkokat (`Source inventory`, `Role mapping`, `Issues`, `Repairs`, `Acceptance`, `Artifacts`),
- a review modal külön rétegként működik, nem olvasztja be/törli a meglévő drawert.

## Érintett fájlok

- `frontend/src/lib/types.ts`
- `frontend/src/lib/api.ts`
- `frontend/src/pages/DxfIntakePage.tsx`
- `scripts/smoke_dxf_prefilter_e4_t5_conditional_review_modal.py`
- `codex/codex_checklist/web_platform/dxf_prefilter_e4_t5_conditional_review_modal.md`
- `codex/reports/web_platform/dxf_prefilter_e4_t5_conditional_review_modal.md`

## Verifikáció

- `python3 -m py_compile scripts/smoke_dxf_prefilter_e4_t5_conditional_review_modal.py` -> PASS
- `python3 scripts/smoke_dxf_prefilter_e4_t5_conditional_review_modal.py` -> PASS
- `npm --prefix frontend run build` -> PASS
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e4_t5_conditional_review_modal.md` -> PASS
- Megjegyzés: a build által generált `frontend/tsconfig.tsbuildinfo` visszaállítva, így a végső diff csak task-output fájlokat tartalmaz.

## DoD -> Evidence Matrix

| DoD pont | Státusz | Evidence |
| --- | --- | --- |
| A runs táblában review-required file-ra megjelenik a conditional review trigger. | PASS | `frontend/src/pages/DxfIntakePage.tsx:245`; `frontend/src/pages/DxfIntakePage.tsx:777`; `frontend/src/pages/DxfIntakePage.tsx:815` |
| A review modal csak review-required + diagnostics payloados file-ra nyitható. | PASS | `frontend/src/pages/DxfIntakePage.tsx:245`; `frontend/src/pages/DxfIntakePage.tsx:320`; `frontend/src/pages/DxfIntakePage.tsx:846` |
| A modal külön review summaryt mutat a persisted diagnostics truth review szeleteiből. | PASS | `frontend/src/pages/DxfIntakePage.tsx:875`; `frontend/src/pages/DxfIntakePage.tsx:885`; `frontend/src/pages/DxfIntakePage.tsx:897` |
| A modal replacement upload entrypointot ad a meglévő backend route-ra építve. | PASS | `frontend/src/lib/api.ts:296`; `frontend/src/pages/DxfIntakePage.tsx:474`; `frontend/src/pages/DxfIntakePage.tsx:934` |
| A finalize replacement a meglévő `complete_upload` route-on történik `replaces_file_object_id` bridge-dzsel. | PASS | `frontend/src/lib/api.ts:312`; `frontend/src/lib/api.ts:322`; `frontend/src/pages/DxfIntakePage.tsx:484`; `frontend/src/pages/DxfIntakePage.tsx:491` |
| A page jelenlegi preflight settings draftja replacement finalize-kor snapshotként átmegy. | PASS | `frontend/src/pages/DxfIntakePage.tsx:460`; `frontend/src/pages/DxfIntakePage.tsx:492` |
| A T4 diagnostics drawer nem regresszál. | PASS | `frontend/src/pages/DxfIntakePage.tsx:832`; `frontend/src/pages/DxfIntakePage.tsx:968`; `frontend/src/pages/DxfIntakePage.tsx:1026`; `frontend/src/pages/DxfIntakePage.tsx:1065`; `frontend/src/pages/DxfIntakePage.tsx:1091`; `frontend/src/pages/DxfIntakePage.tsx:1110` |
| Nincs új review-decision API / persisted review decision / rules-profile save scope. | PASS | `api/routes/files.py:710`; `api/routes/files.py:60`; `frontend/src/pages/DxfIntakePage.tsx:909` |
| Készült task-specifikus smoke. | PASS | `scripts/smoke_dxf_prefilter_e4_t5_conditional_review_modal.py:1` |
| `npm --prefix frontend run build` PASS. | PASS | build output: `tsc -b && vite build` sikeres |
| `./scripts/verify.sh --report ...` PASS. | PASS | AUTO_VERIFY blokk (`eredmény: PASS`, `check.sh exit 0`) |

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-04-23T22:38:04+02:00 → 2026-04-23T22:40:50+02:00 (166s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/dxf_prefilter_e4_t5_conditional_review_modal.verify.log`
- git: `main@f8b42b4`
- módosított fájlok (git status): 11

**git diff --stat**

```text
 frontend/src/lib/api.ts              |  18 +++
 frontend/src/lib/types.ts            |  20 +++
 frontend/src/pages/DxfIntakePage.tsx | 270 ++++++++++++++++++++++++++++++++++-
 frontend/tsconfig.tsbuildinfo        |   2 +-
 4 files changed, 308 insertions(+), 2 deletions(-)
```

**git status --porcelain (preview)**

```text
 M frontend/src/lib/api.ts
 M frontend/src/lib/types.ts
 M frontend/src/pages/DxfIntakePage.tsx
 M frontend/tsconfig.tsbuildinfo
?? canvases/web_platform/dxf_prefilter_e4_t5_conditional_review_modal.md
?? codex/codex_checklist/web_platform/dxf_prefilter_e4_t5_conditional_review_modal.md
?? codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e4_t5_conditional_review_modal.yaml
?? codex/prompts/web_platform/dxf_prefilter_e4_t5_conditional_review_modal/
?? codex/reports/web_platform/dxf_prefilter_e4_t5_conditional_review_modal.md
?? codex/reports/web_platform/dxf_prefilter_e4_t5_conditional_review_modal.verify.log
?? scripts/smoke_dxf_prefilter_e4_t5_conditional_review_modal.py
```

<!-- AUTO_VERIFY_END -->
