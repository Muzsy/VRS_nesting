# VRS Nesting Codex Task — F2-2 P0: “3 valós DXF alakzat-pár” NFP bizonyíték (DXF→fixture→golden)
TASK_SLUG: nfp_real_dxf_pairs_proof
AREA: nesting_engine

## 1) Kötelező olvasnivaló

1. AGENTS.md
2. docs/codex/overview.md
3. docs/codex/yaml_schema.md
4. docs/codex/report_standard.md
5. docs/nesting_engine/tolerance_policy.md
6. docs/nesting_engine/json_canonicalization.md
7. canvases/nesting_engine/nesting_engine_backlog.md (F2-2 DoD)
8. canvases/nesting_engine/nfp_computation_concave.md
9. canvases/nesting_engine/nfp_real_dxf_pairs_proof.md
10. samples/dxf_demo/README.md + *.dxf
11. vrs_nesting/sparrow/input_generator.py
12. rust/nesting_engine/tests/nfp_regression.rs
13. scripts/check.sh
14. codex/goals/canvases/nesting_engine/fill_canvas_nfp_real_dxf_pairs_proof.yaml

Ha bármelyik hiányzik: STOP, és írd le pontosan mit kerestél.

---

## 2) Cél

F2-2 DoD hiányzó pontját lefedni futtatható bizonyítékkal:

- 3 db “valós DXF” alakzat-párhoz (stock×part, part×stock, part×part) legyen:
  - DXF→canonical i64 ring export (fixture polygon_a/polygon_b)
  - golden expected NFP (expected_nfp + expected_vertex_count)
  - smoke script, ami bizonyítja:
    - a fixture ring tényleg a DXF importból jön
    - computed NFP = expected NFP (3/3)
- A smoke legyen bekötve a scripts/check.sh gate-be.
- verify.sh PASS:
  ./scripts/verify.sh --report codex/reports/nesting_engine/nfp_real_dxf_pairs_proof.md

Megkötések:
- nincs új dependency
- outer-only (holes proof csak evidence; holes-os NFP külön task)

---

## 3) Nem cél

- F2-2 core algoritmus módosítása
- holes támogatás
- scripts/verify.sh wrapper módosítása
- rust/vrs_solver módosítása

---

## 4) DoD

- 3 fixture létrejött a poc/nfp_regression alatt (real_dxf_pair_01/02/03)
- scripts/smoke_real_dxf_nfp_pairs.py PASS (DXF→fixture egyezés + computed NFP egyezés)
- scripts/check.sh futtatja a smoke-ot
- verify wrapper PASS:
  ./scripts/verify.sh --report codex/reports/nesting_engine/nfp_real_dxf_pairs_proof.md

---

## 5) Végrehajtás

Hajtsd végre a YAML steps lépéseit sorrendben.

Szabály: csak a YAML outputs listában szereplő fájlokat módosíthatod / hozhatod létre.

A végén add meg:
- módosított/létrehozott fájlok listája
- smoke futás rövid kimenete (PASS)
- report + verify log frissítve
