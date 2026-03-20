# H1 End-to-end Pilot Runbook

## Cel
Ez a runbook a `scripts/smoke_h1_e7_t1_end_to_end_pilot_projekt.py` futtatasat irja le.
A pilot a H1 minimum csatorna tenyleges vegigvezeteset bizonyitja egy reprodukalhato
mintaprojekten, valos Supabase/Frontend nelkul.

## Scope
A pilot script a kovetkezo H1 boundary-ket futtatja vegig:
- file ingest metadata (`load_file_ingest_metadata`)
- DXF geometry import (`import_source_dxf_geometry_revision`)
- geometry validation + derivative generalas (a geometry importon belul)
- part/sheet revision create service-ek
- project part requirement + project sheet input service-ek
- run create + snapshot builder (`create_queued_run_from_project_snapshot`)
- worker oldali projection/artifact boundary-k:
  - `persist_raw_output_artifacts`
  - `normalize_solver_output_projection`
  - `persist_sheet_svg_artifacts`
  - `persist_sheet_dxf_artifacts`

## Pilot fixture
- 1 projekt (`H1 Pilot Project`)
- 1 DXF forras: `samples/dxf_demo/stock_rect_1000x2000.dxf`
- 1 part revision
- 1 sheet revision
- 1 active part requirement (`required_qty=1`)
- 1 active/default sheet input (`required_qty=1`)
- 1 run
- 1 synthetic solver placement (`contract_version=v1`), 0 unplaced

## Elokeszuletek
- Python kornyezet legyen telepitve a repo kovetelmennyel (`requirements-dev.txt`).
- A scriptet repo rootbol futtasd.

## Futtatas
```bash
python3 -m py_compile scripts/smoke_h1_e7_t1_end_to_end_pilot_projekt.py
python3 scripts/smoke_h1_e7_t1_end_to_end_pilot_projekt.py
```

## Elvart output / PASS kriteriumok
A script a vegen JSON summary-t ir ki, majd:
- `PASS: H1-E7-T1 end-to-end pilot project smoke`

PASS-hoz minimum:
- `run_status == "done"`
- `projection.sheet_rows > 0`
- `projection.placement_rows > 0`
- `projection.placed_count > 0`
- `artifact_kinds` tartalmazza legalabb:
  - `solver_output`
  - `sheet_svg`
  - `sheet_dxf`

## FAIL kriteriumok
A script FAIL-ra all (nem nulla exit), ha barmelyik boundary-torott:
- geometry nincs validalt allapotban,
- nincs `nesting_canonical` / `viewer_outline` derivative,
- run create/snapshot nem jon letre,
- projection tablavilag ures,
- hianyzik barmely kotelezo artifact kind.

## Ismert korlatok (H1-E7-T2-be hagyva)
- A pilot in-memory fake Supabase gateway-t hasznal, nem valos DB/HTTP utvonalat.
- A worker runner reszben synthetic `solver_output.json` payloadot hasznal (nem CLI solver futtatast).
- Queue lease/retry/network/storage API edge-case-ek teljes koru tesztelese nem cel ebben a taskban.
