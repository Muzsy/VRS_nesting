# T06g Checklist — Cavity Prepack Solver Contract

- [x] cavity_prepack.py elolvasva
- [x] result_normalizer.py elolvasva
- [x] cavity_validation.py elolvasva
- [x] worker/main.py prepack útvonal auditálva
- [x] LV8 raw part type / quantity / hole count mérve
- [x] LV8 current prepack solver part type count mérve (12 → 231 confirmed)
- [x] 12 → 231 root cause feltárva
- [x] Cavity Prepack Solver Contract V1 definiálva
- [x] planning artifact és solver part szétválasztva
- [x] module variant grouping implementálva (_module_variant_key, _group_placement_trees_by_variant)
- [x] identical module variants quantity alapján összevonva
- [x] empty parent outer proxy nem szaporodik cavity/instance szerint
- [x] child demand reduction implementálva (quantity_delta, remaining_qty tracking)
- [x] quantity preservation tesztelve
- [x] top-level solver holes after prepack = 0
- [x] result normalizer module reconstruction auditálva
- [ ] result normalizer javítva (collapsed ID → virtual_id mapping)
- [x] cavity validation module metadata auditálva
- [x] no internal placement esetén nincs solver part type explosion (231 → 12)
- [ ] internal placement esetén child nem marad duplikált top-level demandben (nem tesztelve, LV8-en 0 internal placement)
- [x] synthetic no-placement test PASS
- [x] synthetic one-child-fit test PASS
- [x] synthetic quantity-accounting test PASS
- [x] synthetic variant-grouping test PASS
- [x] LV8 prepack-only benchmark lefutott
- [x] solver smoke lefutott vagy dokumentáltan blokkolt (CGAL timeout, BLF fallback success)
- [x] nincs új optimizer változás
- [x] nincs NFP provider policy változás
- [x] nincs production Dockerfile változás
- [x] tesztek futtatva (35 PASS)
- [x] report elkészült

## Result Normalizer Javítás Szükséges

A collapsed module variant ID (`__cavity_composite__variant_key__hash`) és az eredeti virtual_id (`__cavity_composite__parent__000000`) nem egyezik meg. A normalizerben a `placement_trees.get(part_id)` lookup失败了.

**Javítás:** result_normalizer._normalize_solver_output_projection_v2-ben a `module_variants` mappinget kell használni collapsed ID → representative_virtual_id átfordításhoz.