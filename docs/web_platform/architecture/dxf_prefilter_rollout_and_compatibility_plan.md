# DXF Prefilter Rollout and Compatibility Plan (E5-T4)

## 1. Cel
Ez a dokumentum a mar implementalt DXF prefilter lane rollout es compatibility truthjat operationalizalja.
A scope docs/ops jellegu: nem vezet be uj feature-t, endpointot, migrationt, persistence-t vagy analytics pipeline-t.

## 2. Current-code alap (repo-grounded)
A terv az alabbi fajlokban letezo viselkedesre epul:
- `api/config.py`: canonical backend rollout flag (`API_DXF_PREFLIGHT_REQUIRED`) + alias (`DXF_PREFLIGHT_REQUIRED`).
- `api/routes/files.py`: `complete_upload` ON/OFF finalize branch, `replace_file` gate OFF esetben.
- `api/services/dxf_geometry_import.py`: legacy direct geometry import helper.
- `frontend/src/lib/featureFlags.ts`: build-time mirror (`VITE_DXF_PREFLIGHT_ENABLED`).
- `frontend/src/App.tsx`: DXF Intake route visibility gate.
- `frontend/src/pages/ProjectDetailPage.tsx`: DXF Intake CTA visibility gate.

## 3. Canonical flag-ek es jelenteseik
- `API_DXF_PREFLIGHT_REQUIRED`
  - Backend canonical env-level rollout gate.
  - `0/false/no/off` ertekre OFF, minden masra ON.
- `DXF_PREFLIGHT_REQUIRED`
  - Legacy/compat alias a backend oldalon.
  - Csak fallback env nev, a canonical nev tovabbra is `API_DXF_PREFLIGHT_REQUIRED`.
- `VITE_DXF_PREFLIGHT_ENABLED`
  - Frontend build-time visibility mirror.
  - Nem runtime toggle; a route/CTA lathatosag build artefaktumban dol el.

## 4. ON/OFF viselkedesi matrix
| Terulet | Rollout ON | Rollout OFF | Operatori elvaras |
|---|---|---|---|
| Source DXF finalize (`complete_upload`) | `validate_dxf_file_async` + `run_preflight_for_upload` | `validate_dxf_file_async` + `import_source_dxf_geometry_revision_async` | Rollout OFF eseten a `complete_upload` legacy direct geometry import helperre esik vissza. |
| Replacement flow (`replace_file`) | Elerheto (signed replacement upload URL) | HTTP 409 konfliktus | Rollout OFF eseten a `replace_file` gate-elve van. |
| DXF Intake route + CTA | Latszik (`/projects/:projectId/dxf-intake` + ProjectDetail CTA) | Nem latszik | Rollout OFF eseten a DXF Intake route/CTA nem latszik. |
| `latest_preflight_*` projection frissules | Uj preflight runok keszulnek, summary/diagnostics adat frissulhet | Uj preflight run nem varhato OFF allapotban | Korabbi runok historical adatkent maradhatnak lathatoak. |
| Support triage | Preflight acceptance/diagnostics alapu triage | Legacy import viselkedes + gate ellenorzes hangsulyos | OFF allapotban preflight volumen varhatoan csokken/nulla az uj feltolteseknel. |

## 5. Rollout stage modell (docs/ops)
- Stage 0 - dark launch / operator verification
  - Kod kesz, de target kornyezetben fokozatos ellenorzes.
  - Elso ellenorzes: flag mapping, UI visibility, replacement gate.
- Stage 1 - guarded rollout
  - `API_DXF_PREFLIGHT_REQUIRED=1`, frontend mirror build ON megfelelo kornyezetben.
  - Support figyeli az acceptance_outcome eloszlast es diagnostics trendeket.
- Stage 2 - prefilter-default operation
  - Prefilter lane az alaput, legacy helper rollback celra marad.
  - Replacement flow aktiv, DXF Intake UI latszik.
- Stage 3 - sunset-ready state
  - Legacy helper eltavolitasa tovabbra sem resze ennek a tasknak.
  - Csak sunset kriteriumok teljesuleset rogzitjuk.

## 6. Rollback es emergency fallback eljaras
1. Backend rollout OFF: `API_DXF_PREFLIGHT_REQUIRED=0` (vagy kompat alias: `DXF_PREFLIGHT_REQUIRED=0`).
2. API redeploy utan ellenorizd, hogy uj `complete_upload` source DXF finalize a legacy import utat valasztja.
3. Frontend visibility alignment: `VITE_DXF_PREFLIGHT_ENABLED=0`, uj build + deploy.
4. Ellenorizd, hogy replacement route 409-et ad OFF allapotban.
5. Futtasd a task smoke-ot: `python3 scripts/smoke_dxf_prefilter_e5_t4_rollout_and_compatibility_plan.py`.

## 7. Compatibility garanciak es jelenlegi korlatok
### Garanciak (current-code szerint)
- Source DXF finalize mindket allapotban folytathato (ON: preflight runtime, OFF: legacy import helper).
- Replacement flow csak prefilter rollout ON mellett hasznalhato.
- Frontend DXF Intake entrypoint csak rolloutolt buildben jelenik meg.

### Korlatozasok
- Nincs project-level rollout flag.
- Nincs runtime frontend config endpoint.
- Frontend/back-end alignment build+deploy fegyelemmel tarthato fenn, nem runtime handshake-kel.
- Legacy helper removal nem E5-T4 scope, csak sunset kriterium.

## 8. Support/debug checklist
- [ ] Backend env ellenorzes: `API_DXF_PREFLIGHT_REQUIRED` (es ha hasznalt, `DXF_PREFLIGHT_REQUIRED`) tenyleges erteke.
- [ ] Frontend build flag ellenorzes: `VITE_DXF_PREFLIGHT_ENABLED` megfelel a backend rollout allapotnak.
- [ ] OFF eset ellenorzes: replacement route vartan 409 conflict.
- [ ] OFF eset ellenorzes: DXF Intake route/CTA nem latszik.
- [ ] ON eset ellenorzes: uj preflight summary/diagnostics adatok kepzodnek uj source DXF uploadoknal.
- [ ] Anomalia triage: `accepted_for_import`, `preflight_review_required`, `preflight_rejected` mintak valtozasa.
- [ ] Futtatasi minimum: task smoke + kotelezo verify reporttal.

## 9. Rollout metrika terv (current-source vs kesobbi observability)
| Metrika | Definicio | Current-code forras | Megjegyzes |
|---|---|---|---|
| `accepted_for_import` arany | Accepted kimenetek aranya az uj preflight runokon | `latest_preflight_summary.acceptance_outcome` projection (`GET /projects/{project_id}/files?include_preflight_summary=true`) | Aggregalt trendhez kulso osszesites kell. |
| `preflight_review_required` arany | Review required kimenetek aranya | Ugyanaz a summary projection | Operatori terheles korai jelzoje. |
| `preflight_rejected` arany | Rejected kimenetek aranya | Ugyanaz a summary projection | Gyors rollback trigger-jel lehet, ha kiugrik. |
| Replacement flow volumen | `replace_file` flow hasznalat gyakorisaga | Nincs dedikalt aggregate endpoint; API/edge log alapu kovetes kell | Kesoobbi observability bovitessel lesz stabilabb. |
| Legacy fallback activity OFF idoszakban | Mennyit fut a legacy import ut | Kozvetlen, strukturalt metric nincs a task scope-ban | Kesoobbi event/metric instrumentation ajanlott. |
| Diagnostics issue family trend | Ismelt issue family-k idobeli trendje | `latest_preflight_diagnostics.issue_summary.normalized_issues` | Aggregacio jelenleg manualis/kulso feldolgozast igenyel. |

## 10. Legacy sunset kriteriumok (helper removal nelkul)
A legacy helper tenyleges eltavolitasa nem resze E5-T4-nek. Sunset-ready allapothoz ajanlott kriteriumok:
- Stabil smoke + E2E evidence tobb release-en keresztul.
- Elfogadhato `accepted/review_required/rejected` arany tobb egymast koveto release-ben.
- Nincs kritikus replacement-flow regresszio.
- Support/load tapasztalatok szerint a rollback igeny ritka vagy nulla.
- Meghatarozott idointervallumban rollback nelkuli stabil uzem.

## 11. Explicit anti-scope
- Nincs uj project-level rollout domain/flag.
- Nincs uj runtime frontend config endpoint.
- Nincs legacy helper kodtorles vagy refaktor.
- Nincs uj migration, endpoint vagy analytics pipeline.
