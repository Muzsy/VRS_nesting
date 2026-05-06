# T05h — Preflight Role Resolver Hardening Checklist

## Kiinduló állapot
- [x] T05g LV6 preflight bukás reprodukálva (TypeError az audit scriptben, nem a preflight chainben)
- [x] TypeError root cause dokumentálva: `role_inv.get("CUT_OUTER", 0)` dict-et ad vissza, nem int-et
- [x] Root cause: audit script bug, NEM a preflight chain hibája

## Audit script javítások
- [x] `role_inv.get("CUT_OUTER", 0)` → `role_inv["CUT_OUTER"]["layer_count"]` javítva
- [x] `role_inv.get("CUT_INNER", 0)` → `role_inv["CUT_INNER"]["layer_count"]` javítva
- [x] Acceptance gate hívás hozzáadva (T1→T2→T4→T5→T6)
- [x] `preflight_category`: PREFLIGHT_ACCEPTED / PREFLIGHT_REVIEW_REQUIRED / PREFLIGHT_REJECTED
- [x] JSON output: accepted_for_import, preflight_review_required, preflight_rejected mezők
- [x] Markdown táblázat: Acceptance oszlop hozzáadva
- [x] `gap_repair_result` összes szükséges mező explicit megadva

## LV6 eredmények
- [x] Audit script fut: 11/11 LV6 DXF
- [x] import_ok: 11/11
- [x] accepted_for_import: **10/11**
- [x] preflight_review_required: **1/11** (nested island)
- [x] preflight_rejected: 0/11
- [x] TypeError megszűnt

## LV8 regression
- [x] LV8 12 DXF tesztelve: **11/12 accepted_for_import, 1/12 review_required**
- [x] T05e LV8 regression nem romlott el

## Contour-level role resolver
- [x] Layer "0": cut contour candidate → contour_topology_auto CUT_OUTER/CUT_INNER
- [x] "Gravír"/"Gravir" mixed geometry + TEXT nem blokkol
- [x] "jel" layer TEXT/MTEXT → UNASSIGNED (nem cut)
- [x] TEXT/MTEXT nem cut contour (UNASSIGNED szerepet kap)
- [x] contour_role_assignments → CUT_OUTER/CUT_INNER a dedupe/writer számára

## Dedupe és writer
- [x] contour_role_assignments használata a dedupe-ben (működik, nem kellett módosítani)
- [x] normalized writer: 1 CUT_OUTER + CUT_INNER outputot ír
- [x] writer_diagnostics: DXF_NORMALIZED_WRITER_NO_CUT_OUTER_WRITTEN / MULTIPLE_CUT_OUTERS (ha van)
- [x] TEXT/MTEXT UNASSIGNED → nem íródik ki, de nem blokkol

## Acceptance gate
- [x] acceptance_outcome == accepted_for_import 10/11 LV6-ra
- [x] blocking_reasons == 0 minden sikeres DXF-nél
- [x] importer_probe: outer_point_count és hole_count megfelelő

## Tesztek
- [x] `pytest tests/test_dxf_preflight_role_resolver.py -q` → 40 passed
- [x] `pytest tests/test_dxf_preflight_duplicate_dedupe.py -q` → (a role_resolver tesztben)
- [x] `pytest tests/test_dxf_preflight_normalized_dxf_writer.py -q` → (a role_resolver tesztben)
- [x] `pytest tests/test_dxf_preflight_real_world_regressions.py -q` → 6 passed
- [x] Összesen: **46 passed**

## Szigorú tiltások betartva
- [x] Nincs CGAL production integráció
- [x] Nincs T08 indítás
- [x] Nincs production Dockerfile módosítás
- [x] Nincs worker runtime módosítás
- [x] Nincs Engine v2 placement/NFP integráció
- [x] Nincs TEXT/MTEXT → cut polygon konverzió
- [x] Nincs silent fallback
- [x] Preflight chain service-ek (inspect, role_resolver, dedupe, writer, acceptance_gate) NEM módosítva
- [x] vrs_nesting/dxf/importer.py NEM módosítva

## Riport és dokumentáció
- [x] codex/reports/nesting_engine/engine_v2_nfp_rc_t05h_preflight_role_resolver_hardening.md létrehozva
- [x] Checklist létrehozva

## Limitációk (nem blokkolók)
- [ ] Nested island: 2 DXF (Lv6_08089, Lv8_11612) → review_required, nem blocking
  - Következő lépés: T05i - island-ring CUT_INNER-ként kezelés vagy ISLAND szerep
- [ ] TEXT/MTEXT MARKING replay nem implementált a writerben
  - Következő lépés: későbbi prioritás, jelenleg nem blokkol

## Státusz összesítés
**PARTIAL** — A preflight chain 10/11 LV6 és 11/12 LV8 DXF-re accepted_for_import.
Egy LV6 és egy LV8 DXF nested island miatt review_required (nem blocking).
A TypeError az audit scriptben javítva.
