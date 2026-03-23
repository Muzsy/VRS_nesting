# H2 End-to-end Manufacturing Pilot Runbook

## Cel
Ez a runbook a `scripts/smoke_h2_e6_t1_end_to_end_manufacturing_pilot.py` futtatasat irja le.
A pilot a H2 mainline manufacturing chain tenyleges vegigvezeteset bizonyitja egy
reprodukalhato mintarunon, valos Supabase/Frontend nelkul.

## Scope
A pilot script a kovetkezo H2 boundary-ket futtatja vegig:
- manufacturing/postprocess snapshot (fixture-bol szarmazik a run_snapshot_builder minta szerint)
- manufacturing plan builder (`build_manufacturing_plan`)
- manufacturing metrics calculator (`calculate_manufacturing_metrics`)
- manufacturing preview SVG generator (`generate_manufacturing_preview`)
- machine-neutral export (`generate_machine_neutral_export`)

A H2-E5-T4 machine-specific adapter **nem** resze a pilotnak es nem PASS feltetel.

## Pilot fixture
- 1 projekt, 1 run (seeded UUID-kkel)
- 1 sheet placement (3000x1500 mm terulet)
- 1 part revision, 1 geometry revision, 1 manufacturing derivative
- 1 outer contour (rect 100x50 mm) + 1 inner contour (circle r=10 mm)
- Aktiv manufacturing profile (`laser_steel_5mm`) + aktiv postprocessor profile
- Cut rule set: 2 rule (outer + inner), matching logic a contour class alapjan
- Szintetikus snapshot: `run_snapshot_manufacturing_selections`, `run_snapshot_postprocessor_profiles`

## Elokeszuletek
- Python kornyezet legyen telepitve a repo kovetelmennyel (`requirements-dev.txt`).
- A scriptet repo rootbol futtasd.

## Futtatas
```bash
python3 -m py_compile scripts/smoke_h2_e6_t1_end_to_end_manufacturing_pilot.py
python3 scripts/smoke_h2_e6_t1_end_to_end_manufacturing_pilot.py
```

## Elvart output / PASS kriteriumok
A script a vegen JSON evidence summary-t ir ki, majd:
- `PASS: H2-E6-T1 end-to-end manufacturing pilot`

PASS-hoz minimum:
- `run_manufacturing_plans` truth letrejon (legalabb 1 sor)
- `run_manufacturing_contours` truth letrejon (legalabb 2 sor: outer + inner)
- `run_manufacturing_metrics` truth letrejon (legalabb 1 sor)
- Artifact lista tartalmazza legalabb:
  - `manufacturing_preview_svg`
  - `manufacturing_plan_json`
- Nincs `machine_ready_bundle`, `machine_program`, G-code vagy egyeb machine-specific artifact
- Manufacturing plan JSON export `contract_version == "h2_e5_t3_v1"`

## FAIL kriteriumok
A script FAIL-ra all (nem nulla exit), ha barmelyik boundary tort:
- manufacturing plan builder nem tud plan/contour truth-ot letrehozni,
- metrics calculator nem tud metrics truth-ot irni,
- preview SVG generator exception-t dob vagy nem regisztral artifactot,
- machine-neutral exporter exception-t dob vagy nem regisztral artifactot,
- barmelyik persisted truth tabla ures marad,
- tiltott machine-specific side-effect jelenik meg.

## Ellenorzesi fazisok
A script 10 tesztfazist futtat:
1. **Fixture setup** — seeded adatok konzisztenciaja
2. **Plan builder** — `build_manufacturing_plan` futtatasa, plan truth letrejotte
3. **Contour truth** — outer + inner contour sorok jelenlete
4. **Metrics calculator** — `calculate_manufacturing_metrics` futtatasa, metrics truth
5. **Preview SVG** — `generate_manufacturing_preview` futtatasa, SVG artifact
6. **Export JSON** — `generate_machine_neutral_export` futtatasa, JSON artifact
7. **Artifact evidence** — `manufacturing_preview_svg` + `manufacturing_plan_json` jelenlet
8. **No machine-specific** — nincs tiltott artifact kind
9. **No forbidden truth** — nincs `machine_ready_bundle`, `machine_programs` iras
10. **Boundary error** — hibauzenet validalas rossz inputtal

## Ismert korlatok (H2-E6-T2 audit scope-ban marad)
- A pilot in-memory fake Supabase gateway-t hasznal, nem valos DB/HTTP utvonalat.
- A postprocessor metadata snapshotolt, de machine-specific emit nincs tesztelve (H2-E5-T4 optionalis).
- Timing proxy ertekek szintetikusak (nem valos CNC idle mertek).
- Altalanos H2 audit/stabilizacio a H2-E6-T2 taskra marad.
