# SGH-Q53 task package — True contour-feature critical admission

Ez a csomag a Q53A–Q53E taskokat tartalmazza canvas + goal YAML + runner prompt + checklist formában.

## Apply

Másold a csomag tartalmát a repo gyökerébe:

```bash
cp -R canvases codex README_SGH_Q53_TRUE_CONTOUR_FEATURE_ADMISSION_PACKAGE.md /path/to/VRS_nesting/
```

## Javasolt futási sorrend

```text
Q53A -> Q53B -> Q53C -> Q53D -> Q53E
```

## Master runner

```bash
cat codex/prompts/egyedi_solver/sgh_q53_true_contour_feature_admission_master_runner.md
```

Egyedi task futtatása:

```bash
cat codex/prompts/egyedi_solver/sgh_q53a_contour_feature_extraction/run.md
cat codex/prompts/egyedi_solver/sgh_q53b_feature_candidate_generator/run.md
cat codex/prompts/egyedi_solver/sgh_q53c_continuous_feature_refine/run.md
cat codex/prompts/egyedi_solver/sgh_q53d_critical_admission_integration/run.md
cat codex/prompts/egyedi_solver/sgh_q53e_lv8_feature_admission_proof/run.md
```

## Miért ez a Q53 irány?

Q48–Q52 alatt kiderült, hogy a `contour-near` candidate path valójában neighbour-contour-vertex + moving-bbox-corner seed. Ez nem elég konkáv/íves/low-fill critical alkatrészekhez. A Q53 célja nem raster scoringgal kezdeni, hanem előbb kijavítani a jelölttér minőségét: valódi kontúrfeature -> kontúrfeature candidate-ek, continuous refine, CDE final validation.

## Nem-célok

- NFP visszahozása.
- Bbox/AABB collision shortcut.
- Continuous rotation diszkrét foklistával kiváltása.
- Cavity/hole logika a fő solverben.
- Part-id specifikus LV8 hack.
- Előre kikényszerített `3 big per sheet` szabály.

## Primary acceptance csak Q53E-ben

`6× Lv8_11612`, spacing 5, margin 5, continuous rotation: feature-on módban legalább egy sheeten 3 nagy alkatrész CDE-valid módon létrejön. Full276 2 sheet nem Q53E acceptance, csak későbbi integrációs cél.
