# H1 lezarasi kriteriumok es H2 entry gate

## 1. Cel es hasznalat

Ez a dokumentum a H1 szakasz closure audit anyaga. A celja:
- evidencen alapulo H1 completion matrix rogzitese;
- pilot tanulsagok es stabilizacios fixek osszekotese;
- blokkolo vs advisory elteresek tiszta szetvalasztasa;
- egyertelmu H2 entry gate itelet kimondasa.

A dokumentum dontesi anyag: a H2 inditas alapfelteteleinek ellenorizheto allapotat rogzitit.

## 2. H1 lezarasi kriteriumok

A H1 akkor tekintheto zarhatonak, ha az alabbi feltetelek teljesulnek:
- Funkcionalis lanc: DXF upload -> geometry revision -> derivative -> part/sheet -> project input -> snapshot -> run -> worker -> projection/artifact.
- Reprodukcio: legalabb egy reprodukalhato pilot smoke vegigviszi a minimum lancot.
- Projection/artifact szeparacio: `run_layout_*` es `run_metrics` projection adatok, plusz kulon `run_artifacts` visszakeresheto kimenetek.
- Worker lifecycle minimum stabilitas: queue lease, retry/error kezeles, done/failed zaras.
- Route oldali H1 minimum queryzhatosag: run/allapot/log/artifact/viewer minimum endpoint viselkedes.
- Dokumentacios konzisztencia: known issues + roadmap + closure report osszhangban.

## 3. H1 completion matrix

| Task | Statusz | Evidence |
| --- | --- | --- |
| H1-E1-T1 | PASS | `codex/reports/web_platform/h1_e1_t1_upload_endpoint_service_h0_schema_realignment.md` + verify log |
| H1-E1-T2 | SOFT PASS | `codex/reports/web_platform/h1_e1_t2_file_hash_es_metadata_kezeles.md` + verify log |
| H1-E2-T1 | SOFT PASS | `codex/reports/web_platform/h1_e2_t1_dxf_parser_integracio.md` + verify log |
| H1-E2-T2 | SOFT PASS | `codex/reports/web_platform/h1_e2_t2_geometry_normalizer.md` + verify log |
| H1-E2-T3 | SOFT PASS | `codex/reports/web_platform/h1_e2_t3_validation_report_generator.md` + verify log |
| H1-E2-T4 | SOFT PASS | `codex/reports/web_platform/h1_e2_t4_geometry_derivative_generator_h1_minimum.md` + verify log |
| H1-E3-T1 | SOFT PASS | `codex/reports/web_platform/h1_e3_t1_part_creation_service_es_derivative_binding_h1_minimum.md` + verify log |
| H1-E3-T2 | SOFT PASS | `codex/reports/web_platform/h1_e3_t2_sheet_creation_service_h1_minimum.md` + verify log |
| H1-E3-T3 | PASS | `codex/reports/web_platform/h1_e3_t3_project_requirement_management_h1_minimum.md` + verify log |
| H1-E3-T4 | PASS | `codex/reports/web_platform/h1_e3_t4_project_sheet_input_management_h1_minimum.md` + verify log |
| H1-E4-T1 | PASS | `codex/reports/web_platform/h1_e4_t1_run_snapshot_builder_h1_minimum.md` + verify log |
| H1-E4-T2 | PASS | `codex/reports/web_platform/h1_e4_t2_run_create_api_service_h1_minimum.md` + verify log |
| H1-E4-T3 | PASS | `codex/reports/web_platform/h1_e4_t3_queue_lease_mechanika_h1_minimum.md` + verify log |
| H1-E5-T1 | SOFT PASS | `codex/reports/web_platform/h1_e5_t1_engine_adapter_input_mapping_h1_minimum.md` + verify log |
| H1-E5-T2 | SOFT PASS | `codex/reports/web_platform/h1_e5_t2_solver_process_futtatas_h1_minimum.md` + verify log |
| H1-E5-T3 | SOFT PASS | `codex/reports/web_platform/h1_e5_t3_raw_output_mentes_h1_minimum.md` + verify log |
| H1-E6-T1 | SOFT PASS | `codex/reports/web_platform/h1_e6_t1_result_normalizer_h1_minimum.md` + verify log |
| H1-E6-T2 | PASS | `codex/reports/web_platform/h1_e6_t2_sheet_svg_generator_h1_minimum.md` + verify log |
| H1-E6-T3 | PASS | `codex/reports/web_platform/h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.md` + verify log |
| H1-E7-T1 | PASS | `codex/reports/web_platform/h1_e7_t1_end_to_end_pilot_projekt.md` + verify log |

Osszesitett kep:
- PASS: 10
- SOFT PASS: 10
- FAIL: 0

## 4. H1-E7-T1 pilot fo tanulsagok

- A teljes H1 minimum lanc reprodukalhato egyetlen dedikalt smoke scripten keresztul.
- A projection truth (`run_layout_*`, `run_metrics`) es artifact world (`solver_output`, `sheet_svg`, `sheet_dxf`) egyszerre bizonyithato.
- A stabilizacios munka leginkabb route oldali konzisztencia es regresszios bizonyithatosag teren ad hozzaadott erteket.

## 5. Blokkolo vs advisory elteresek

### Blokkolo elteresek
- Nincs azonosithato H1 blokkolo a jelen closure audit alapjan.

### Advisory elteresek
- KI-004: legacy H1-E2-T1 smoke script contract drift (`part_raw.v1` varakozas vs `normalized_geometry.v1` aktualis canonical format). Ez teszt- es dokumentacios adossag, nem pipeline blokkolo.

## 6. H2 entry gate itelet

Vegso itelet: **PASS WITH ADVISORIES**.

Indoklas:
- A H1 funkcionalis lanc evidence alapon vegig igazolt.
- A kotelezo gate-ek es task szintu regression smoke PASS.
- A maradt nyitott pont teszt-karbantartasi advisory, nem H2-blocking mukodesi hiba.

## 7. Mit jelent ez a gyakorlatban?

- H2 indithato a jelen H1 allapotrol ujranyitas nelkul.
- H1-ben nem szukseges uj domain migracios vagy nagy refaktor hullam a H2 start elott.
- A KI-004 advisory pontot erdemes a H2 elejen lezarni, hogy a smoke portfolioban ne maradjon elavult, kontraktustol elcsuszo script.

## 8. Scope-hatar (szandekosan out-of-scope)

- Nincs uj H2 feature beemelve ebben a taskban.
- Nincs uj domain migracio nyitva.
- Nincs altalanos architecture refaktor; csak pilot/audit altal indokolt minimalis stabilizacios korrekcio.
