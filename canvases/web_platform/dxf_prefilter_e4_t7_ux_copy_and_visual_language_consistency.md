# DXF Prefilter E4-T7 — UX szovegek es vizualis nyelv egysegesitese

## Cel
Az E4-T6 vege ota a `DxfIntakePage` mar valos, vegigkotott intake UX-et ad:
- source DXF upload,
- preflight settings bridge,
- latest preflight runs tabla,
- diagnostics drawer,
- conditional review modal + replacement upload,
- accepted files -> parts flow.

A jelenlegi repo-grounded hiany mar nem uj funkcio, hanem **nyelvi es vizualis inkonzisztencia**:
- a page tobb kulon helperbol, kulon idoben felhuzott badge/szoveg/CTA nyelvet hasznal,
- a user-facing copy keveri a lifecycle-szintu technikai cimkeket es a UX-szintu ajanlasokat,
- a vizualis tone mapping (`pending`, `accepted`, `review required`, `rejected`, `ready`, `already created`) nincs egyetlen kozos presentation truthba rendezve,
- a section intro szovegek es modal copy-k stilusa is vegyes.

Ezert az E4-T7 helyes current-code scope-ja:
**a DxfIntakePage teljes intake UX-en a user-facing copy, badge-ek, CTA-k es szekcio-nyelv egységesitese, uj workflow vagy backend valtozas nelkul.**

## Miert most?
A funkcionalis lepcso mar kesz:
- E4-T1 oldal,
- E4-T2 settings panel,
- E4-T3 latest runs table,
- E4-T4 diagnostics drawer,
- E4-T5 conditional review modal,
- E4-T6 accepted files -> parts flow.

A kovetkezo logikus lepes mar nem uj feature, hanem hogy a teljes intake oldal **egy darab termekfeluletnek hasson**, ne egymasra rakott taskok gyujtemenyenek.

## Scope boundary

### In-scope
- A `DxfIntakePage` user-facing copy auditja es egységesitese.
- A page-en hasznalt status/badge/CTA/szekcio copy kozos presentation truthba rendezese.
- Egységes tone mapping a kovetkezo allapotvilagokra:
  - run status,
  - acceptance outcome,
  - issue/repair count,
  - accepted-files part readiness,
  - diagnostics/review/action CTA-k.
- Inline Tailwind class-ek olyan mertekig torteno konszolidacioja, hogy a vizualis nyelv kovetkezetes legyen.
- Minimalis frontend helper / presentation module bevezetese, ha ez a legkisebb regressziomentes megoldas.
- Task-specifikus smoke.

### Out-of-scope
- Uj backend route vagy projection.
- Uj frontend workflow, modal vagy oldal.
- Persisted review decision domain.
- Parts flow logika modositas.
- Settings persistence redesign.
- Diagnostics payload vagy accepted-files projection schema modositas.
- Globalis design system vagy uj shared UI component library bevezetese.
- I18n/lokalizacios rendszer.

## Talalt relevans fajlok (meglevo kodhelyzet)
- `frontend/src/pages/DxfIntakePage.tsx`
  - itt van a teljes intake UX.
- `frontend/src/lib/types.ts`
  - a jelenlegi preflight summary/diagnostics/parts projection type-ok.
- `frontend/src/lib/api.ts`
  - current-code API boundary, de T7-ben varhatoan nem kell valtoztatni.
- `frontend/src/index.css`
  - csak ha a legkisebb, regressziomentes megoldashoz tenyleg kell; ne legyen default celpont.
- `scripts/smoke_dxf_prefilter_e4_t6_accepted_files_to_parts_flow.py`
- `canvases/web_platform/dxf_prefilter_e4_t4_diagnostics_drawer_modal.md`
- `canvases/web_platform/dxf_prefilter_e4_t5_conditional_review_modal.md`
- `canvases/web_platform/dxf_prefilter_e4_t6_accepted_files_to_parts_flow.md`

## Jelenlegi repo-grounded helyzetkep

### 1. A funkcio mar egyben van, de a nyelv szetszorodott
A page ma mar tobb szekciot fed le, es ezek sajat copy-nyelvet hasznalnak:
- upload + auto-preflight notice,
- latest preflight runs,
- diagnostics drawer,
- conditional review modal,
- accepted files -> parts.

Ez functionalisan rendben van, de product UX szinten most mar lathato a taskonkenti retegzodes.

### 2. A statusvilag tobb helyen kulon helperrel epul
A page ma kulon helperfuggvenyekkel rakja ossze:
- run status badge,
- acceptance outcome badge,
- issue badge,
- repair badge,
- recommended action,
- part readiness presentation.

Ezek jelenleg current-code szerint mukodnek, de nincs koztuk egyetlen kozos copy/visual contract.

### 3. A technical truth es a user-facing truth ma keveredik
Pelda current-code nyelvi szintekbol:
- `preflight complete`, `preflight failed`, `pending`, `accepted`, `rejected`
- `Ready for next step`
- `Open review`, `View diagnostics`, `Create part`
- `Run n/a`, `Finished: ...`
- `Current-code note: persisted review decision save is not implemented yet.`

A T7 helyes celja nem az, hogy ezeket eltuntesse, hanem hogy a page-en vilagos legyen:
- mi a **status**,
- mi a **recommended next step**,
- mi a **technical note**,
- es ezek vizualisan is kulonuljenek.

### 4. A visual tone mapping is szetszorodott
A class-ek ma inline modon jelennek meg, pl.:
- green = accepted / ready,
- amber = review / attention,
- red = rejected / blocked,
- sky = pending,
- slate = neutral/info.

Ez helyes irany, de a page-nek current-code szerint meg nincs egyetlen presentation truth-ja arra, hogy melyik tone mit jelent.

## Konkret elvarasok

### 1. A T7 ne nyisson uj workflowt
A feladat ne adjon uj gombot, endpointot vagy modal logikat.
A helyes T7 current-code modell:
- ugyanazok a flow-k maradnak,
- csak a copy es a vizualis nyelv lesz egységesebb.

### 2. Legyen kozos presentation truth a DxfIntake UX-re
Vezess be egy olyan minimalis, current-code presentation reteget (helyben a page-ben vagy kulon helper fajlban), amely legalabb ezt lefedi:
- section title + section helper text,
- badge label + tone,
- CTA label,
- empty state / pending state / blocked state copy,
- review es diagnostics modal headline/subcopy.

A presentation truth ne legyen uj domain vagy schema; frontend local/helper szint eleg.

### 3. Kulonitsd el a status, action es technical note nyelvet
A T7 egyik fo minosegi pontja az legyen, hogy a user ne egybefolyo szovegtomeget kapjon.
Current-code szinten egyertelmu legyen a kulonbseg:
- **status**: mi a file vagy run allapota,
- **next step**: mit kell most csinalni,
- **technical detail**: mi a hatterben levo current-code vagy api-truth.

Ez a diagnostics drawerben es a review modalban kulonosen fontos.

### 4. Egységesitsd a badge-eket es tone-okat
A T7-ben a kovetkezo badge-vilag legyen kovetkezetes:
- success/ready/accepted -> zold tone,
- review/attention -> amber tone,
- blocked/rejected/error -> piros tone,
- queued/running/pending -> sky tone,
- neutral/info/already-created -> slate tone.

Ha a page ma mar hasznal ilyen mappinget, azt ne dobd ki; tedd kozosse es kovetkezetesse.

### 5. Egységesitsd a szekcio- es uresallapot-szovegeket
A page szekcioi most funkcionisan jok, de a segedmondatok stilusa vegyes.
A T7-ben:
- az oldal bevezeto copy,
- a settings blokk,
- a latest runs tabla bevezetoje,
- az accepted files -> parts blokk bevezetoje,
- az empty state-ek,
- a pending/not-eligible helper text-ek
ugyanabban a hangnemben jelenjenek meg.

### 6. A diagnostics drawer es review modal copy-t ne keverd ossze
A ket overlay kulon szerepet tol be:
- diagnostics = read-only reszletes allapotkep,
- review modal = guidance + replacement upload entrypoint.

A T7-ben ez a szerepkulonbseg a headline/subcopy/section copy szinten is legyen egyertelmu.

### 7. T4/T5/T6 regressziomentesseg
A T7 nem ronthatja el:
- a diagnostics drawer nyitast/zarat,
- a replacement upload flow-t,
- az accepted files -> parts create-part flow-t,
- a table/action renderinget.

### 8. Bizonyitas
Minimum deterministic evidence:
- task-specifikus smoke, amely bizonyitja, hogy
  - bent van a kozos presentation/copy truth,
  - a DxfIntakePage szekcioi az uj copy-nyelvre epulnek,
  - a diagnostics es review UX kulon headline/subcopy vilagot kap,
  - a T4/T5/T6 trigger tokenek tovabbra is bent maradnak,
  - a create-part / review / diagnostics flow nem tunik el.
- `npm --prefix frontend run build`
- `./scripts/verify.sh --report ...` PASS

## Erintett fajlok / celzott outputok
- `canvases/web_platform/dxf_prefilter_e4_t7_ux_copy_and_visual_language_consistency.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e4_t7_ux_copy_and_visual_language_consistency.yaml`
- `codex/prompts/web_platform/dxf_prefilter_e4_t7_ux_copy_and_visual_language_consistency/run.md`
- `frontend/src/pages/DxfIntakePage.tsx`
- opcionálisan, ha ez a legkisebb tiszta megoldas:
  - `frontend/src/lib/dxfIntakePresentation.ts`
  - es/vagy `frontend/src/index.css`
- `scripts/smoke_dxf_prefilter_e4_t7_ux_copy_and_visual_language_consistency.py`
- `codex/codex_checklist/web_platform/dxf_prefilter_e4_t7_ux_copy_and_visual_language_consistency.md`
- `codex/reports/web_platform/dxf_prefilter_e4_t7_ux_copy_and_visual_language_consistency.md`

## DoD
- [ ] A DxfIntakePage user-facing copy-ja konzisztens, egyseges termeknyelvet hasznal.
- [ ] A status, next-step es technical-note copy szintek kulonvalnak.
- [ ] A badge/tone mapping a page kulonbozo reszein kovetkezetes.
- [ ] A diagnostics drawer es a conditional review modal kulon, tiszta szerepkoru copy-t kap.
- [ ] A latest runs es accepted files -> parts szekcio uresallapot/pending/allapot szovegei egységesek.
- [ ] Nincs uj backend/API/workflow scope.
- [ ] A T4/T5/T6 funkciok nem regresszalnak.
- [ ] Keszul task-specifikus smoke.
- [ ] `npm --prefix frontend run build` PASS.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e4_t7_ux_copy_and_visual_language_consistency.md` PASS.
