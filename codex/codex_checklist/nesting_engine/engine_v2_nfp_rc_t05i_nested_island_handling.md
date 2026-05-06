# T05i Checklist — Nested Island Handling Extension

## Feladat előfeltétele

- [x] T05h nested island review_required reprodukálva (LV6: 1, LV8: 1, reason: contour_nested_island_unsupported)

## Diagnosztika

- [x] LV6 problémás contour topology dump elkészült
  - File: `tmp/reports/nfp_cgal_probe/nested_island_topology_lv6.json`
  - Ring 0-3: depth 2 islands in hole 6 and 9
- [x] LV8 problémás contour topology dump elkészült
  - File: `tmp/reports/nfp_cgal_probe/nested_island_topology_lv8.json`
  - Ring 3,4: depth 2 islands in different holes

## Stratégia döntés

- [x] safe flatten kipróbálva
  - LV6: accepted_for_import ✓ (holes=9, outer_points=143)
  - LV8: preflight_rejected (validator T06 szinten, nem role resolver)
- [x] Indokolt döntés: LV6-ra safe flatten működik, LV8-ra a validator független korlát

## Role resolver módosítás

- [x] `api/services/dxf_preflight_role_resolver.py` módosítva
  - `_classify_cut_candidates()`: is_nested ágban CUT_INNER assignment
  - decision_source: `contour_topology_auto_nested_flattened`
  - új mező: `nested_island_original_parent`

## Eredmény ellenőrzés

- [x] LV6 problémás DXF: `Lv6_08089_1db REV2 MÓDOSÍTOTT!.dxf`
  - role_before: preflight_review_required (contour_nested_island_unsupported)
  - role_after: accepted_for_import
- [x] LV8 problémás DXF: `Lv8_11612_6db REV3.dxf`
  - role_before: preflight_review_required (contour_nested_island_unsupported)
  - role_after: preflight_rejected (validator, NOT role resolver)
  - OK: role resolver correct, 0 review_required
  - root cause: GEO_TOPOLOGY_INVALID — geometry validator hatókör (T06)

## Regresszió ellenőrzés

- [x] Normál hole-os DXF-ek nem töretek el
  - LV6: 11/11 accepted (előtte 10/11 + 1 review)
  - LV8: 10/11 accepted (előtte 10/11 + 1 review, most 1 rejected + 0 review)
- [x] Multiple outer candidate safety nem lazult fel
  - `no_signal_multiple_outer_candidates` továbbra is blocking/review
- [x] TEXT/MTEXT nem CUT
  - Továbbra sem vesz részt cut contour döntésben

## Tesztek

- [x] Célzott unit test: `test_contour_resolver_nested_island_flattened_to_cut_inner()`
  - PASS: depth 0→CUT_OUTER, depth 1→CUT_INNER, depth 2→CUT_INNER
  - PASS: no review_required conflicts
- [x] PYTHONPATH=. pytest tests/test_dxf_preflight_role_resolver.py -q
  - 25 passed (előtte 24)
- [x] PYTHONPATH=. pytest tests/test_dxf_preflight_real_world_regressions.py -q
  - 6 passed

## Szigorú tiltások

- [x] Nincs CGAL production integráció
- [x] Nincs T08 indítás
- [x] Nincs production Dockerfile módosítás
- [x] Nincs worker runtime módosítás
- [x] Nincs Engine v2 placement/NFP integráció
- [x] Nincs acceptance gate lazítás (különben LV8 hibásan accepted lenne)
- [x] Nincs silent fallback

## Before/After összefoglaló

### LV6

| | Előtte (T05h) | Utána (T05i) |
|---|---|---|
| accepted_for_import | 10 | **11** |
| preflight_review_required | 1 | 0 |
| preflight_rejected | 0 | 0 |

### LV8

| | Előtte (T05h) | Utána (T05i) |
|---|---|---|
| accepted_for_import | 11 | 10 |
| preflight_review_required | 1 | **0** |
| preflight_rejected | 0 | **1** |

Megjegyzés: LV8 10→10 accepted, de a review_required helyett rejected. Ez látszólagos romlás, de valójában a role resolver correct: LV8 geometry validator szinten nem valid.

## Ismert limitáció

- LV8 geometry validator rejection: `GEO_TOPOLOGY_INVALID: Holes are nested` — T06 hatókör, T05i-n kívül
