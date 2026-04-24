# Report — dxf_prefilter_e4_t7_ux_copy_and_visual_language_consistency

## Összefoglaló

Az E4-T7 a `DxfIntakePage` teljes intake UX-én presentation-konszolidációt végez: közös copy/tone truth
bevezetésével egységesíti a badge-eket, a szekciócímeket, az üres állapot szövegeket és a modal copy-t.
Nem jött létre új backend route, workflow, endpoint vagy persisted domain — kizárólag frontend prezentációs réteg változott.

## Miért presentation-konszolidáció a T7, nem új UX workflow

Az E4-T1–T6 feladatok után a `DxfIntakePage` funkcionálisan teljes volt, de a copy és a vizuális language
különböző időpontokban és különböző mintákkal épült fel. Az eredmény: működő, de inkonzisztens termékfelület.

A T7 helyes current-code modellje ezért:
- **nem** ad új gombot, endpointot, modált vagy flow-t,
- **csak** a meglévő badge helper függvényeket, copy string-eket és tone mapping-et rendezi közös presentation truth-ba.

A `dxfIntakePresentation.ts` modul a legkisebb regressziómentes megoldás: a page-en belül helyi helper is elegendő lett volna,
de egy külön modul jobban szétválasztja a prezentációs réteget a komponens logikájától.

## Hogyan különül el a status / next step / technical note copy

A presentation modul és a JSX három vizuálisan elkülönülő réteget érvényesít:

| Réteg | Tartalom | Vizuális jelzés |
|---|---|---|
| **status** | Mi a file/run jelenlegi állapota | badge (TONE szerinti háttérszín) |
| **next step** | Mit kell most csinálni | `recommendedNextStep()` szöveg a `Next step` oszlopban; `guidance_title`/`guidance_body` az overlay guidance szekciójában (amber border) |
| **technical note** | Backend/API igazság, nem akcionálható | `tech_note_title`/`tech_note_body` a review overlay tech note szekciójában (slate border, kisebb betűméret) |

A review overlay korábban egyetlen `What to do now` blokkban keverte a három szintet. Most két külön szekció van:
- amber szekció: actionable guidance (mit kell csinálni)
- slate szekció: technical note (mi nincs implementálva, melyik route hívódik)

## Hogyan egységesedett a badge/tone mapping

Korábban a badge helpers inline class stringeket definiáltak ad-hoc módon. Különösen inkonzisztens volt a
repair count badge: `bg-indigo-100 text-indigo-800` — ami figyelemfelhívó tónusú volt, holott a javítások
informatív/semleges jelzések.

Az új TONE paletta:

| Kulcs | Szín | Szemantika |
|---|---|---|
| `success` | zöld | accepted / ready / 0 issues |
| `attention` | amber | review-required / ambiguous |
| `blocked` | piros | rejected / error / blocking |
| `queued` | sky | running / pending / queued |
| `neutral` | slate | info / already-created / not eligible |

A repair count badge `neutral` (slate) tónusra vált — informatív adat, nem figyelemfelhívó állapot.

## Hogyan maradt regressziómentes a T4/T5/T6

A presentation-konszolidáció kizárólag copy stringeket és badge osztályokat érint. A funkcionális logika (drawer nyitás/zárás,
replacement upload, create-part flow) változatlan maradt:

- **T4 diagnostics drawer**: `setSelectedDiagnosticsFileId`, drawer JSX blokk, `selectedDiagnosticsFile && selectedDiagnostics` guard — mind jelen van
- **T5 review modal**: `canOpenConditionalReviewModal`, `openConditionalReviewModal`, `handleReviewReplacementUpload` — mind jelen van
- **T6 create-part flow**: `canCreatePartFromAcceptedFile`, `handleCreatePart`, `api.createProjectPart` — mind jelen van

A T7 smoke mind a tíz ellenőrzési pontját a funkcionális tokenek jelenlétén alapozza.

## Érintett fájlok

- `frontend/src/lib/dxfIntakePresentation.ts` (új)
- `frontend/src/pages/DxfIntakePage.tsx`
- `scripts/smoke_dxf_prefilter_e4_t7_ux_copy_and_visual_language_consistency.py` (új)
- `codex/codex_checklist/web_platform/dxf_prefilter_e4_t7_ux_copy_and_visual_language_consistency.md` (új)
- `codex/reports/web_platform/dxf_prefilter_e4_t7_ux_copy_and_visual_language_consistency.md` (ez a fájl)

## Verifikáció

- `python3 scripts/smoke_dxf_prefilter_e4_t7_ux_copy_and_visual_language_consistency.py` → PASS
- `npm --prefix frontend run build` → PASS
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e4_t7_ux_copy_and_visual_language_consistency.md` → PASS

## DoD → Evidence Matrix

| DoD pont | Státusz | Evidence |
| --- | --- | --- |
| A DxfIntakePage user-facing copy-ja konzisztens, egységes terméknyelvt használ. | PASS | `dxfIntakePresentation.ts`: INTAKE_COPY; `DxfIntakePage.tsx`: INTAKE_COPY.* hivatkozások |
| A status, next-step és technical-note copy szintek különválnak. | PASS | `dxfIntakePresentation.ts`: guidance_title/body + tech_note_title/body; review overlay két szekció |
| A badge/tone mapping a page különböző részein következetes. | PASS | `dxfIntakePresentation.ts`: TONE paletta; repair badge neutral tónusra vált |
| A diagnostics drawer és a review modal külön, tiszta szerepkörű copy-t kap. | PASS | overlay_title: "Preflight diagnostics" vs "Review required"; overlay_subtitle különbözik |
| A latest runs és accepted files → parts szekció üres állapot/pending szövegei egységesek. | PASS | INTAKE_COPY.runs.empty; INTAKE_COPY.acceptedParts.empty |
| Nincs új backend/API/workflow scope. | PASS | Csak `dxfIntakePresentation.ts` és `DxfIntakePage.tsx` változott |
| A T4/T5/T6 funkciók nem regresszálnak. | PASS | T7 smoke 8–10. ellenőrzési pont PASS |
| Készült task-specifikus smoke. | PASS | `scripts/smoke_dxf_prefilter_e4_t7_ux_copy_and_visual_language_consistency.py` |
| `npm --prefix frontend run build` PASS. | PASS | build output: tsc -b && vite build sikeres |
| `./scripts/verify.sh --report ...` PASS. | PASS | AUTO_VERIFY blokk alább |

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-04-24T21:25:20+02:00 → 2026-04-24T21:28:08+02:00 (168s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/dxf_prefilter_e4_t7_ux_copy_and_visual_language_consistency.verify.log`
- git: `main@7bc5b06`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 frontend/src/pages/DxfIntakePage.tsx | 421 ++++++++++-------------------------
 frontend/tsconfig.tsbuildinfo        |   2 +-
 2 files changed, 119 insertions(+), 304 deletions(-)
```

**git status --porcelain (preview)**

```text
 M frontend/src/pages/DxfIntakePage.tsx
 M frontend/tsconfig.tsbuildinfo
?? canvases/web_platform/dxf_prefilter_e4_t7_ux_copy_and_visual_language_consistency.md
?? codex/codex_checklist/web_platform/dxf_prefilter_e4_t7_ux_copy_and_visual_language_consistency.md
?? codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e4_t7_ux_copy_and_visual_language_consistency.yaml
?? codex/prompts/web_platform/dxf_prefilter_e4_t7_ux_copy_and_visual_language_consistency/
?? codex/reports/web_platform/dxf_prefilter_e4_t7_ux_copy_and_visual_language_consistency.md
?? codex/reports/web_platform/dxf_prefilter_e4_t7_ux_copy_and_visual_language_consistency.verify.log
?? frontend/src/lib/dxfIntakePresentation.ts
?? scripts/smoke_dxf_prefilter_e4_t7_ux_copy_and_visual_language_consistency.py
```

<!-- AUTO_VERIFY_END -->
