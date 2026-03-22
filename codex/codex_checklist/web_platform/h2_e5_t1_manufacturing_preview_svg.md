# H2-E5-T1 Manufacturing preview SVG — Checklist

## Alap
- [x] Relevans fajlok azonositva (felderites)
- [x] Canvas elkeszult (kockazat + rollback + DoD)
- [x] YAML steps + outputs pontos (outputs szabaly betartva)

## DoD
- [x] Letezik `manufacturing_preview_svg` artifact kind a canonical artifact vilagban.
- [x] A bridge fuggvenyek kezelik a `manufacturing_preview_svg` legacy type-ot.
- [x] Keszul dedikalt manufacturing preview generator service.
- [x] A generator persisted manufacturing plan truth + manufacturing_canonical derivative alapjan per-sheet preview SVG-t general.
- [x] A preview a gyartasi meta-informaciot is hordozza (entry/lead/cut-order), nem csak layoutot.
- [x] A preview artifactok a canonical `run-artifacts` bucketbe kerulnek.
- [x] A filename + metadata policy stabil, auditalhato es generic artifact endpointtel hasznalhato.
- [x] A preview artifact persistence idempotens ugyanarra a run + sheet targetre.
- [x] A task nem ir vissza korabbi truth tablaba.
- [x] A task nem nyit export / postprocessor / frontend-redesign scope-ot.
- [x] Keszul task-specifikus smoke script.
- [x] Checklist es report evidence-alapon ki van toltve.
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h2_e5_t1_manufacturing_preview_svg.md` PASS.
