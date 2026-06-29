# SGH-Q70 Report - Corner-first residual-space recovery

## Verdict: PASS

## Goal

- Keep the solver on the forced latest-path.
- Strengthen corner-first / residual-space authority for critical anchor decisions.
- Recover obvious filler opportunities on underfilled sheets before calling the run acceptable.

## Run

| run | status | placed | unplaced | used sheets | util % | non-orth rotations | wall s |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| q70_A_corner_first_2sheet_sp5 | partial | 237 | 39 | 2 | 58.695127362605085 | 198 | 161.7 |

## Q70 Diagnostics

| check | value |
| --- | --- |
| forced latest lock active | true |
| accepted anchor secondary policy | corner_high |
| best corner score | 2574576.875 |
| best center score | 2701440.083333333 |
| center blocked by policy | true |
| center override used | false |
| center-only path | false |
| sheet fill recovery inserted | 187 |
| underfilled sheet recovery used | true |
| completion fill-first applied | true |

## Per-sheet

| sheet | placed | physical util % |
| --- | ---: | ---: |
| 0 | 192 | 55.3233 |
| 1 | 45 | 54.8289 |

## Comparison

| baseline | placed | unplaced | used sheets | util % |
| --- | ---: | ---: | ---: | ---: |
| Q62 current | 259 | 17 | 2 | 49.96641349141249 |
| Q69 forced latest | 62 | 214 | 2 | 48.79324783882088 |
| Q70 recovery | 237 | 39 | 2 | 58.695127362605085 |

## Visual Proxy

- Render manifest: `artifacts/benchmarks/sgh_q70/renders/q70_A_corner_first_2sheet_sp5/render_manifest.json`
- Top rotations: `[{"rotation_deg": 270.0, "count": 20}, {"rotation_deg": 330.0, "count": 20}, {"rotation_deg": 60.0, "count": 19}, {"rotation_deg": 210.0, "count": 19}, {"rotation_deg": 30.0, "count": 17}, {"rotation_deg": 300.0, "count": 17}, {"rotation_deg": 240.0, "count": 15}, {"rotation_deg": 120.0, "count": 13}, {"rotation_deg": 82.0, "count": 10}, {"rotation_deg": 90.0, "count": 10}, {"rotation_deg": 150.0, "count": 10}, {"rotation_deg": 86.0, "count": 7}]`
- Sheet 0 physical utilization: `55.3233`

## Visual Audit

- `sheet_00.png`: a nagy kritikus elemek mar nem csendben center-seat poziciokba ulnek, hanem jol lathatoan
  tabla-szel / sarok kozeli authority szerint indulnak. Az elso tabla belso uregei nem maradnak uresen:
  a recovery pass sok kisebb elemet visszatolt a trivialis ures regiokba, ezert a Q69-ben latott nagy
  holtterek nagyreszt eltuntek.
- `sheet_01.png`: a masodik tabla tovabbra sem tokeletes, de mar nem a kozepre dobalt, regressziv fallback
  kepet mutatja. A nagy elemek edge/corner szemlelettel ulnek, a folyamatos forgatas pedig tenylegesen
  latszik a nem-ortogonalis szogek magas szamaban es a vizualis elhelyezesben is.
- Osszkep: a Q70 layout minosege szemmel lathatoan jobb a Q69-nel, es mar tenylegesen visszaad valamit a
  forced-latest logikabol. Ugyanakkor a teljes placed-count meg mindig elmarad a Q62 current 259-es
  szintjetol, tehat ez javitas, nem vegallapot.

## Finding

Q70 mar nem engedi a forced-latest futast csendben visszacsuszni a center-seat dominans regi viselkedesre:
az elfogadott anchor policy `corner_high`, mikozben a jobb center score explicit policy-blokkolast kapott.
Az underfilled-sheet recovery 187 tovabbi behelyezest csinalt, ami a Q69 62 darabos eredmenyet 237-re
emelte, es a sheet-0 fizikai kihasznaltsagat kb. 35%-rol 55.3%-ra huzta fel. A task celja ezzel teljesult,
de a Q62 current 259 placed szintjehez kepest tovabbi strategiai javitas meg indokolt.

## Artifact evidence

- summary: `artifacts/benchmarks/sgh_q70/q70_summary.json`
- input: `artifacts/benchmarks/sgh_q70/inputs/q70_full276_2x1500x3000_margin5_spacing5_continuous_600.json`
- output: `artifacts/benchmarks/sgh_q70/outputs/q70_A_corner_first_2sheet_sp5_output.json`
- log: `artifacts/benchmarks/sgh_q70/logs/q70_A_corner_first_2sheet_sp5.log`
