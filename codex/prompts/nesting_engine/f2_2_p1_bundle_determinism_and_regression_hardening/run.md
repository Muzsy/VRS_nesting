# VRS Nesting Codex Task — F2-2 P1 bundle (4 fixes): canonical bytes test + spec drift + gate smoke + quarantine workflow
TASK_SLUG: f2_2_p1_bundle_determinism_and_regression_hardening
AREA: nesting_engine

## 1) Kötelező olvasnivaló

1. AGENTS.md
2. docs/codex/overview.md
3. docs/codex/yaml_schema.md
4. docs/codex/report_standard.md
5. codex/reports/nesting_engine/f2_2_full_audit.md (P1: 4 pont)
6. docs/nesting_engine/json_canonicalization.md
7. scripts/canonicalize_json.py
8. scripts/smoke_nesting_engine_determinism.sh
9. scripts/check.sh
10. rust/nesting_engine/src/export/output_v2.rs
11. poc/nfp_regression/README.md
12. canvases/nesting_engine/f2_2_p1_bundle_determinism_and_regression_hardening.md
13. codex/goals/canvases/nesting_engine/fill_canvas_f2_2_p1_bundle_determinism_and_regression_hardening.yaml

Ha bármi hiányzik: STOP, és írd le pontosan mit kerestél.

## 2) Cél (a 4 P1 fix)

P1-1: Rust byte-level canonical JSON teszt hozzáadása (hash-view canonical string).  
P1-2: json_canonicalization.md normatív pontosítás (JCS-szubszet = implementációval egyező).  
P1-3: determinism smoke script bekötése a check.sh gate-be (default RUNS=10, env-ből 50).  
P1-4: quarantine acceptance workflow dokumentálása a poc/nfp_regression/README.md-ben.

Megkötések:
- nincs új dependency
- funkció nem sérülhet
- determinisztika: byte-azonos összehasonlítás

## 3) DoD

- cargo test (nesting_engine) PASS, benne az új byte-level canonical JSON teszt
- scripts/check.sh PASS, és fut benne a determinism smoke (canonical JSON-on)
- verify PASS:
  ./scripts/verify.sh --report codex/reports/nesting_engine/f2_2_p1_bundle_determinism_and_regression_hardening.md

## 4) Végrehajtás

Hajtsd végre a YAML steps lépéseit sorrendben.

Szabály: csak a YAML outputs listában szereplő fájlokat módosíthatod / hozhatod létre.

A végén add meg:
- módosított/létrehozott fájlok listája
- rövid evidencia: az új Rust canonical-bytes teszt neve + a check.sh-ben hol hívódik a determinism smoke
- report + verify log frissítve
