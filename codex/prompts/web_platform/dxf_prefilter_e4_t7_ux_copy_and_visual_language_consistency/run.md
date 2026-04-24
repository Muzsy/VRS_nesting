Olvasd el az `AGENTS.md` szabalyait, es szigoruan a jelenlegi repo-grounded kodra epits.

Feladat:
Valositsd meg a `canvases/web_platform/dxf_prefilter_e4_t7_ux_copy_and_visual_language_consistency.md`
canvasban leirt taskot a hozza tartozo YAML szerint.

Kotelezo elvek:
- Ne talalj ki uj backend route-ot, API schema-t, workflowt vagy persisted domaint.
- A helyes T7 current-code modell most: **presentation-konszolidacio**, nem uj feature.
- A diagnostics drawer, a conditional review modal es az accepted files -> parts flow funkcionalisan maradjon meg.
- A status / next step / technical note copy-szintek kulonuljenek el.
- A vizualis tone mapping legyen kovetkezetes a teljes intake oldalon.
- Ne bovitsd a NewRunPage.tsx legacy wizardot.

Modellezesi elvek:
- A page jelenlegi helper-vilaga mar mukodik, de nincs kozos presentation truth. Ezt kell rendbe tenni.
- Jo irany lehet egy minimalis frontend helper/presentation module, de csak ha ez a legkisebb tiszta megoldas.
- A T7 ne rejtsen el technical truthot, csak tegye vilagossa, hogy mi status, mi ajanlott kovetkezo lepes, es mi technical note.
- A diagnostics drawer read-only allapotkep maradjon.
- A conditional review modal guidance + replacement upload entrypoint maradjon.
- Az accepted files -> parts blokk tovabbra is valodi create-part flow maradjon, ne advisory-only copy.
- A copy legyen egyseges, tomor, termekesebb, de ne hazudjon tul a current-code kepessegeken.

Kulon figyelj:
- A badge-eknel ne legyen ad hoc class-hasznalat ugyanarra a jelentesszintre.
- Az empty state / pending / blocked szovegek kozos nyelvet beszeljenek.
- A diagnostics es review overlay headline/subcopy vilaga kulonuljon el.
- Ha kulon helper fajlt vezetsz be, csak minimalis presentation/logikai reteget vigyel oda, ne mozgasd ki a teljes page workflowt.
- `frontend/src/index.css`-hez csak akkor nyulj, ha ennel kisebb, tisztabb megoldas nincs.

A feladat vegen kotelezoen fusson:
- `python3 scripts/smoke_dxf_prefilter_e4_t7_ux_copy_and_visual_language_consistency.py`
- `npm --prefix frontend run build`
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e4_t7_ux_copy_and_visual_language_consistency.md`

A reportban kulon terj ki erre:
- miert presentation-konszolidacios task a T7, nem uj UX workflow;
- hogyan kulonul el a status / next step / technical note copy a vegso oldalon;
- hogyan egysegesedett a badge/tone mapping;
- hogyan maradt regressziomentes a T4 diagnostics drawer, a T5 review modal es a T6 accepted-files->parts flow.
