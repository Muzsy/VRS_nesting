# Q56B2 — CavityPrepackBridgeHints diagnosztika és szerződés

## Goal / Funkció

Formalizáld a szerződést a **már működő** worker-szintű cavity prepack v2 pipeline és a Rust/Sparrow
solver preprocessing rétege között. Tedd explicitté, diagnosztikával alátámasztottá és nehezen
regresszálhatóvá, hogy a fősolver cavity prepack v2 után **hole-free** inputot kap.

## Context / Háttér

Fontos architekturális tény, amit rögzíteni kell:

```text
A cavity prepack v2 már meglévő pre-solver réteg.
A Rust/Sparrow solvernek hole-free inputot kell kapnia.
A task célja bridge hint/diagnosztika/szerződés, nem cavity újraírás Rustban.
```

Helyes rétegzés:

```text
worker cavity_prepack v2
→ solver hole-free top-level partokat / composite-okat kap
→ Rust preprocessing bridge hinteket rögzít
→ a solver nem érvel belső furatokról mint szabad nesting térről
→ result_normalizer expandálja/normalizálja a cavity tervet a solver output után
```

A solver feltételezheti: ha a cavity prepack engedélyezett és sikeres, akkor a `vrs_solver` input
top-level partjainak nincs aktív `holes_points_mm`-je a solver placementhez.

## Source of truth

- `AGENTS.md`, `docs/codex/overview.md`, `docs/codex/yaml_schema.md`,
  `docs/codex/report_standard.md`, `docs/qa/testing_guidelines.md`
- Forrásterv: `tmp/plans/q56_q60_preprocessing_tasks/Q56B2_CavityPrepackBridgeHints.md`
- Kapcsolódó: `canvases/egyedi_solver/sgh_q15_cavity_prepack_v2_solver_hole_free_contract.md`

## Existing code anchors

- `worker/cavity_prepack.py` — `build_cavity_prepacked_engine_input_v2(...)`,
  `validate_prepack_solver_input_hole_free(...)`, `_rotation_shapes(...)`, `holes_points_mm`.
- `worker/cavity_validation.py` — `validate_cavity_plan_v2(...)`.
- `worker/engine_adapter_input.py` — `cavity_prepack_parts_to_vrs_solver_v1(...)` (adapter).
- `worker/result_normalizer.py` — `cavity_plan_v2` expansion / virtual/composite kezelés.
- `worker/main.py` — `cavity_prepack_enabled`, `build_cavity_prepacked_engine_input_v2(...)` hívás,
  `validate_cavity_plan_v2(...)`.

## Valós repo anchorok

```text
worker/cavity_prepack.py
worker/cavity_validation.py
worker/result_normalizer.py
worker/engine_adapter_input.py
worker/main.py
tests/worker
```

A cavity prepack v2 már meglévő pre-solver réteg. A Rust/Sparrow solvernek hole-free inputot kell
kapnia. A task célja bridge hint/diagnosztika/szerződés, **nem** cavity újraírás Rustban.

## Scope

- `CavityPrepackBridgeHints` diagnosztikai modell (Python-oldalon, és/vagy minimal Rust-oldali
  rögzítés a PartAnalysis diagnosztikában). Az output artifact egyértelműen kimondja a szerződést.
- Worker pipeline tesztek (bővítés a meglévőkön, ne duplikáld a teljes fixture-öket).
- Bridge blokk a generált solver input / run artifactokban.

## Out of scope

```text
- cavity packing újraimplementálása Rustban
- a meglévő worker cavity prepack v2 viselkedés eltávolítása
- main solver hole-aware CDE collision
- holes átadása a Rust/main solvernek mint elérhető cavity
- validáció gyengítése/eltávolítása fixture-passért
- result_normalizer expansion törése
```

## Required implementation

`CavityPrepackBridgeHints` ajánlott mezők:

```text
cavity_prepack_requested, cavity_prepack_enabled, cavity_prepack_version,
input_part_count_before_prepack, solver_part_count_after_prepack,
virtual_part_count, composite_part_count, module_variant_count,
hole_bearing_input_part_count, hole_free_solver_part_count,
solver_top_level_holes_remaining, hole_free_validation_passed,
cavity_plan_v2_present, cavity_plan_v2_validated, normalizer_expansion_supported,
bridge_status, bridge_warnings[], bridge_errors[]
```

Viselkedés — prepack engedélyezve:
1. Futtasd a meglévő prepack pipeline-t.
2. Validáld, hogy a kibocsátott solver input top-level szinten hole-free.
3. Bocsásd ki a bridge diagnosztikát.
4. Csak akkor add tovább a solver inputot, ha a szerződés teljesül.
5. Őrizd meg a cavity plan metaadatot a normalizer expanzióhoz.

Viselkedés — prepack letiltva:
1. Diagnosztika: disabled/not requested.
2. Ne hamisíts hole-free garanciát, hacsak az input ténylegesen furatmentes.

Rust-oldali implikáció: a Rust/Sparrow preprocessing a bridge után **nem** próbálhat furatokba
pakolni. A PartAnalysis rögzítheti: `hole_free_solver_input`, `cavity_prepack_bridge_status`
(`enabled_passed`/`disabled`/`failed`/`unknown`), `original_hole_bearing_part`, `is_cavity_composite`.
De a Rust **nem** állítja vissza az eredeti furatokat placement cavity-ként.

## Required diagnostics

A generált solver input / run artifactban tömör bridge blokk:

```json
{
  "cavity_prepack_bridge": {
    "requested": true,
    "enabled": true,
    "version": "v2",
    "hole_free_validation_passed": true,
    "solver_top_level_holes_remaining": 0,
    "cavity_plan_v2_validated": true,
    "status": "enabled_passed"
  }
}
```

Artifact: `artifacts/benchmarks/sgh_q56b2/cavity_prepack_bridge_hints.json`.

## Required tests / runners

Teszt: `tests/worker/test_cavity_prepack_bridge_hints.py`. Ellenőrzések:

1. Prepack-engedélyezett, furatos input → solver input top-level `holes_points_mm` nélkül.
2. `validate_prepack_solver_input_hole_free(...)` hibázik, ha furat marad.
3. `cavity_plan_v2` jelen van és validál.
4. A result normalizer látja a cavity plan metaadatot.
5. A Rust-oldali diagnosztika nem állít prepacket, ha nem történt.

Parancsok:

```bash
python3 -m pytest tests/worker/test_cavity_prepack_bridge_hints.py -q
python3 -m pytest tests worker -q -k "cavity or prepack or normalizer"
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q56b2_cavity_prepack_bridge_hints.md
```

## Acceptance criteria

```text
- bridge diagnosztika létezik és generálódik;
- prepack-engedélyezett út bizonyítja a hole-free solver inputot;
- a letiltott út explicit;
- Rust-oldali PartAnalysis / diagnosztika rögzíteni tudja a bridge státuszt;
- result normalizer kompatibilitás megőrizve;
- tesztek lefedik a sikeres ÉS a violation esetet.
```

## Hard restrictions

```text
- nincs cavity packing reimplementáció Rustban
- nincs silent hole passthrough a fő solver felé
- holes nem kezelhető elérhető cavity-ként a Rust Sparrow solverben
- validáció nem gyengíthető fixture-passért
- result_normalizer expansion nem törhet
- CDE/final exact validation marad az igazság
```

## Rollback

- Ha a bridge gate hibásan blokkol valós, furatmentes inputot, állítsd diagnosztika-only módba és
  csak warningot adj (ne fail), amíg a contract finomodik — de soha ne engedj silent hole passthrough-t
  a fősolverhez.
- Worker viselkedés-regresszió esetén revert a bridge gate bekötésére, a meglévő prepack v2 megmarad.

## Deliverables

```text
canvases/egyedi_solver/sgh_q56b2_cavity_prepack_bridge_hints.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q56b2_cavity_prepack_bridge_hints.yaml
codex/prompts/egyedi_solver/sgh_q56b2_cavity_prepack_bridge_hints/run.md
codex/codex_checklist/egyedi_solver/sgh_q56b2_cavity_prepack_bridge_hints.md
codex/reports/egyedi_solver/sgh_q56b2_cavity_prepack_bridge_hints.md
codex/reports/egyedi_solver/sgh_q56b2_cavity_prepack_bridge_hints.verify.log
```
