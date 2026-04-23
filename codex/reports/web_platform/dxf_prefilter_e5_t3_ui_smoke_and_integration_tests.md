# Report — dxf_prefilter_e5_t3_ui_smoke_and_integration_tests

## Összefoglaló

Az E5-T3 egy dedikált Playwright-alapú browser-level UI smoke/integration packot vezet be a `DxfIntakePage` köré. A pack a meglévő `installMockApi` harness-re és auth bypass módra épül — nem indít valódi backendet, nem nyit új endpointot, és nem vezet be új tesztframeworkot.

## Miért browser-level mocked UI integration a helyes E5-T3 current-code truth

Az E5-T2 már route-level backend E2E-ként bizonyítja a `complete_upload → BackgroundTasks → run_preflight_for_upload → list_project_files` láncot. Az E5-T3 ezért nem backend E2E helyettesítő — hanem browser-szintű kiegészítő, amely azt ellenőrzi, hogy a meglévő `DxfIntakePage` UI:
- helyesen bridgeli a settings draft-ot `rules_profile_snapshot_jsonb`-ként a finalize requestbe;
- helyesen rendereli a seeded `latest_preflight_summary` és `latest_preflight_diagnostics` adatokat (badge-ek, recommended action, diagnostics drawer);
- nem mutat hamis `Ready for next step` advisory-t non-accepted fájlra.

Az auth bypass (`VITE_E2E_BYPASS_AUTH=1`) és a mock API harness determinisztikus fake állapotot nyújt valódi Supabase/API indítás nélkül.

## Settings -> finalize payload bridge bizonyítása

A spec `E5-T3 UI#1` tesztje:
1. Seedel egy projektet üres fájllistával.
2. A `DxfIntakePage`-en módosítja a `strict_mode` checkboxot (true) és a `max_gap_close_mm` mezőt (2.5).
3. Feltölt egy mock DXF fájlt a page saját uploader-én keresztül.
4. A mock `POST /projects/{id}/files` handler capture-olja a teljes request body-t `state.finalizedBodies`-ba.
5. A teszt assertálja: `snapshot.strict_mode === true`, `snapshot.max_gap_close_mm === 2.5`, `snapshot.auto_repair_enabled === false`, `snapshot.interactive_review_on_ambiguity === true`.
6. A fájl row megjelenik a táblázatban az upload után.

## Diagnostics drawer fő blokkjainak bizonyítása

A spec `E5-T3 UI#2` tesztje:
1. Seedel egy fájlt teljes `accepted_for_import` preflight summary + diagnostics payloaddal.
2. Assertálja az `accepted` badge-et és a `Ready for next step` advisory szöveget.
3. Megnyitja a diagnostics drawer-t a `View diagnostics` gombbal.
4. Assertálja mind a 6 drawer szekció fejlécét: **Source inventory**, **Role mapping**, **Issues**, **Repairs**, **Acceptance**, **Artifacts**.
5. Assertálja, hogy a drawer read-only (csak `Close` gomb létezik, nincs mutáló action).
6. Bezárja a drawer-t és assertálja, hogy eltűnik.

## A "továbblépés" current-code truth szerinti értelmezése

A mai kódban nincs E4-T6 accepted→parts flow. A spec ezért:
- **nem** keres `Create parts` gombot vagy navigációt;
- az `accepted_for_import` fájl esetén a `Ready for next step` szöveg **advisory szövegként** jelenik meg a táblázat "Recommended action" oszlopában — nem mutáló gombként;
- a `not.toBeVisible()` guard (`E5-T3 UI#3`) bizonyítja, hogy `review_required` fájlra NEM jelenik meg ez az advisory.

## Futtatott ellenőrzések

- `python3 -m py_compile scripts/smoke_dxf_prefilter_e5_t3_ui_smoke_and_integration_tests.py`
- `npm --prefix frontend run build`
- `cd frontend && npx playwright test e2e/dxf_prefilter_e5_t3_dxf_intake.spec.ts`
- `python3 scripts/smoke_dxf_prefilter_e5_t3_ui_smoke_and_integration_tests.py`
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e5_t3_ui_smoke_and_integration_tests.md`

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-04-23T20:49:49+02:00 → 2026-04-23T20:52:38+02:00 (169s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/dxf_prefilter_e5_t3_ui_smoke_and_integration_tests.verify.log`
- git: `main@d9904ce`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 frontend/e2e/support/mockApi.ts | 6 ++++++
 frontend/tsconfig.tsbuildinfo   | 2 +-
 2 files changed, 7 insertions(+), 1 deletion(-)
```

**git status --porcelain (preview)**

```text
 M frontend/e2e/support/mockApi.ts
 M frontend/tsconfig.tsbuildinfo
?? canvases/web_platform/dxf_prefilter_e5_t3_ui_smoke_and_integration_tests.md
?? codex/codex_checklist/web_platform/dxf_prefilter_e5_t3_ui_smoke_and_integration_tests.md
?? codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e5_t3_ui_smoke_and_integration_tests.yaml
?? codex/prompts/web_platform/dxf_prefilter_e5_t3_ui_smoke_and_integration_tests/
?? codex/reports/web_platform/dxf_prefilter_e5_t3_ui_smoke_and_integration_tests.md
?? codex/reports/web_platform/dxf_prefilter_e5_t3_ui_smoke_and_integration_tests.verify.log
?? frontend/e2e/dxf_prefilter_e5_t3_dxf_intake.spec.ts
?? scripts/smoke_dxf_prefilter_e5_t3_ui_smoke_and_integration_tests.py
```

<!-- AUTO_VERIFY_END -->
