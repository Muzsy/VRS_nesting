# Cavity T6 - SVG/DXF export validacio

## Cel
Bizonyitsd, hogy a T5 utan normalizalt parent + internal child projection
placementeket a meglovo SVG/DXF export helyesen kezeli. Minimalis exporter fix
csak akkor keszuljon, ha a smoke bizonyitja, hogy szukseges.

## Nem-celok
- Nem manufacturing cut-order planner.
- Nem postprocessor workflow.
- Nem result normalizer tovabbfejlesztes a T5 scope-on tul.
- Nem virtual ID user-facing export.

## Repo-kontekstus
- `worker/sheet_svg_artifacts.py` es `worker/sheet_dxf_artifacts.py`
  projection placementek alapjan keresik vissza a source geometryt.
- Ha T5 utan a projectionben real parent/child `part_revision_id` van, az
  exporterek elvileg mukodhetnek kodvaltozas nelkul.
- Parent holes exportja az eredeti geometria derivative alapjan kell maradjon.
- Child geometry kulon placementkent jelenik meg.

## Erintett fajlok
- `worker/sheet_svg_artifacts.py`
- `worker/sheet_dxf_artifacts.py`
- `scripts/smoke_cavity_t6_svg_dxf_export_validation.py`
- Meglevo smoke-ok:
  `scripts/smoke_h1_e6_t2_sheet_svg_generator_h1_minimum.py`,
  `scripts/smoke_h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.py`

## Implementacios lepesek
1. Epits synthetic projection fixturet parent hole + internal child rows
   adatokkal.
2. Futtasd SVG exportot es ellenorizd, hogy parent es child is kirajzolodik.
3. Futtasd DXF exportot es ellenorizd, hogy parent hole es child outer is
   szerepel.
4. Ellenorizd, hogy virtual ID nem jelenik meg artifactban.
5. Ha exporter fix kell, tartsd additive es minimalis scope-ban.
6. Dokumentald, hogy cut-order kulon manufacturing task.

## Checklist
- [ ] SVG smoke parent+child PASS.
- [ ] DXF smoke parent+child PASS.
- [ ] Parent hole megorzodik exportban.
- [ ] Virtual ID nincs exportalva.
- [ ] Metadata alapjan parent-child kapcsolat megmarad projectionben.
- [ ] Repo gate reporttal lefutott.

## Tesztterv
- `python3 scripts/smoke_cavity_t6_svg_dxf_export_validation.py`
- `python3 scripts/smoke_h1_e6_t2_sheet_svg_generator_h1_minimum.py`
- `python3 scripts/smoke_h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.py`
- `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_t6_svg_dxf_export_validation.md`

## Elfogadasi kriteriumok
- Export artifactok parent es child geometriat is tartalmaznak.
- Parent-child kapcsolat legalabb projection metadata szinten bizonyitott.
- Nincs nema DXF sorrendhack.

## Rollback
Ha exporter kodvaltozas keszul, az kulon visszavonhato. A smoke fixture
megtarthato regresszios bizonyiteknak.

## Kockazatok
- Exporterek source geometry indexe csak snapshot parts manifestbol dolgozik;
  ha child nincs vagy virtual ID marad, fail-el.
- DXF semantic cut order tovabbra is nyitott manufacturing kockazat.

## Vegso reportban kotelezo bizonyitek
- Smoke artifact tartalom ellenorzesek.
- Path/line, ha exporter fix tortent; ha nem tortent, explicit bizonyitek hogy
  miert nem kellett.
