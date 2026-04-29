# Cavity T7 - UI observability cavity diagnosztikahoz

## Cel
Tedd lathatova a cavity kapcsolodo diagnosztikat a DXF Intake / Project
Preparation feluleten, es a cavity prepack osszefoglalot a Run Detail/viewer
audit feluleten. Ez observability task, nem core algorithm.

## Nem-celok
- Nem New Run Wizard rejected-file filtering.
- Nem cavity packer vagy normalizer core logic.
- Nem export vagy cut-order.
- Nem marketing/landing oldal.

## Repo-kontekstus
- `frontend/src/pages/DxfIntakePage.tsx` jelenleg preflight diagnostics drawert
  mutat source/roles/issues/repairs/acceptance/artifacts szekciokkal.
- `frontend/src/lib/dxfIntakePresentation.ts` tartalmazza a DXF Intake copy
  source of truthot.
- `frontend/src/pages/RunDetailPage.tsx` mar mutat Strategy and engine audit
  adatokat viewer-data alapjan.
- `api/routes/runs.py` `ViewerDataResponse` bovitheto additiv mezokkel.
- `api/routes/files.py` es preflight service-ek mar adnak hole_count adatot az
  acceptance importer probe-ban.

## Erintett fajlok
- `api/routes/files.py`
- `api/services/dxf_preflight_runtime.py`
- `api/services/dxf_preflight_inspect.py`
- `api/services/dxf_preflight_role_resolver.py`
- `api/services/dxf_preflight_acceptance_gate.py`
- `api/services/dxf_geometry_import.py`
- `api/services/part_creation.py`
- `api/routes/runs.py`
- `frontend/src/pages/DxfIntakePage.tsx`
- `frontend/src/lib/dxfIntakePresentation.ts`
- `frontend/src/pages/RunDetailPage.tsx`
- `frontend/src/lib/types.ts`
- `frontend/src/lib/api.ts`
- Celozott Playwright vagy smoke script.

## Implementacios lepesek
1. Ellenorizd, hol jelenik meg ma hole_count es diagnostics adat.
2. Additiv API mezokkel vagy metadata atvezetesekkel tedd elerhetove:
   internal hole count, usable cavity candidate count, too small/invalid count.
3. Run viewer oldalon jelenitsd meg cavity prepack summaryt, ha van
   `cavity_plan`/engine metadata.
4. Frontenden ne jelenjen meg cavity blokk olyan runnal/fajllal, ahol nincs adat.
5. A copy a presentation module-on keresztul menjen.
6. Tartsd kulon a rejected/review/pending filtering logikat.

## Checklist
- [ ] DXF Intake lathato cavity diagnostics adatot mutat, ha van.
- [ ] Run Detail lathato cavity prepack summaryt mutat, ha van.
- [ ] Nincs cavity UI olyan runon, ahol nincs cavity_plan/adat.
- [ ] New Run Wizard filtering nem valtozik.
- [ ] Frontend build zold.
- [ ] Celozott smoke/Playwright zold.
- [ ] Repo gate reporttal lefutott.

## Tesztterv
- `cd frontend && npm run build`
- Celozott Playwright: uj vagy boviett cavity observability spec.
- Relevans DXF smoke, ha backend diagnostics mezok valtoznak.
- `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_t7_ui_observability.md`

## Elfogadasi kriteriumok
- A user latja, hogy belso kivagas van-e, cavityre hasznalhato-e, es runban
  mennyi internal placement tortent.
- UI copy nem allit tobbet, mint amit a metadata bizonyit.
- Backward compatible API/TS normalizalas megmarad.

## Rollback
Additiv API/TS/UI diff visszavonhato; core nesting eredmeny valtozatlan marad.

## Kockazatok
- API response mezok es TS normalizer elcsuszhatnak.
- Tulfogalmazott UI copy full hole-aware engine kepesseget sugallhat.

## Vegso reportban kotelezo bizonyitek
- Screenshot vagy Playwright output.
- API response mezok path/line hivatkozasa.
- Frontend build es celzott test eredmeny.
