# SGH-Q69 - Full276 LV8 forced-latest result audit

## Goal

A Q56-Q68 production cutoverek utan ugyanazt a Full276 LV8 / 2 tabla / margin 5 / spacing 5
csomagot ugy kell ujrafuttatni, hogy a solver ne eshessen vissza a regebbi native seed logikara.
A futas legyen az aktualis role-aware / hint-aware / simultaneous-aware builder utjara kenyszeritve,
es a vegso report ne csak diagnostikailag, hanem a renderelt tablakepek alapjan is ellenorizze,
hogy a korszerubb logika tenylegesen lathato a layouton.

## Scope

- Vezess be explicit forced-latest builder modot a BPP multisheet solve-ban.
- Forced-latest modban tiltsd a native constructive seed fallbackot es a random bootstrap mentest.
- Forced-latest modban ne hagyd, hogy az elso sheet felemessze az egesz builder-idokeretet:
  a jelenlegi builder kapjon sheet-fair, eredmeny-kozpontu idoelosztast.
- Emittalj explicit diagnosztikat arrol, hogy a run forced-latest modban futott, hasznalt-e
  native fallbackot, es hany sheetig jutott el a builder.
- Keszits uj benchmark runnert es Q49-alaku artifactcsomagot `artifacts/benchmarks/sgh_q69/` ala.
- A report tartalmazzon hard post-checket: diagnostics, rotation/edge-use summary, es vizualis
  ellenorzes a renderelt PNG/SVG tablakervek alapjan.

## Non-goals

- Nem cel a regebbi Q62/Q63 artifactok atirasa.
- Nem cel azt allitani elore, hogy a forced-latest run biztosan eleri a 276/276 kettablas celallapotot.
- Nem teljes solver-redesign, csak a latest-path visszaesesek kizarasa es az eredmeny-kozpontu audit.

## Acceptance

- Van explicit forced-latest runtime switch a builderhez.
- Forced-latest modban a solve nem valt vissza a native constructive seedre.
- Forced-latest modban a random bootstrap nincs hasznalva.
- Forced-latest modban a builder legalabb ket sheet megnyitasara kap ertelmes es igazolhato lehetoseget.
- Letrejon a `artifacts/benchmarks/sgh_q69/` benchmark input/output/log/render/report csomag.
- A report pontosan dokumentalja, hogy a latest-path milyen role-aware bizonyitekokat hagyott a
  kimenetben, es ha a vizualis ellenorzesen ez nem latszik eleg erosnek, azt FAIL/PASS_WITH_NOTES
  modon egyertelmuen jelzi.
