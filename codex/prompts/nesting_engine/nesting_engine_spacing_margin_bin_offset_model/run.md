# VRS Nesting Codex Task — Spacing+margin kánon: bin_offset modell
TASK_SLUG: nesting_engine_spacing_margin_bin_offset_model

## 1) Kötelező olvasnivaló (prioritási sorrend)

1. `AGENTS.md`
2. `docs/codex/overview.md`
3. `docs/codex/yaml_schema.md`
4. `docs/codex/report_standard.md`
5. `canvases/nesting_engine/nesting_engine_spacing_margin_bin_offset_model.md`
6. `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_spacing_margin_bin_offset_model.yaml`

Ha bármelyik nem létezik: állj meg és írd le pontosan mit kerestél.

---

## 2) Cél

Állítsd át a teljes clearance modellt a frissített kánonra:

- spacing = part–part min távolság
- margin = part–bin edge min távolság
- kerf = pre-baked, F2-3 matekban nem szerepel

Képletek:
- inflate_delta = spacing/2
- bin_offset = spacing/2 - margin

Kötelező új eset: margin < spacing/2 (bin inflate).

---

## 3) Munkaszabályok

- Valós repó elv: nem találsz ki új fájlokat/mezőket.
- Outputs szabály: csak a YAML `outputs` listájában szereplő fájlokat módosíthatod/hozhatod létre.
- Gate csak wrapperrel.

---

## 4) Végrehajtás

Hajtsd végre a YAML `steps` lépéseit sorrendben:

- `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_spacing_margin_bin_offset_model.yaml`

---

## 5) Kötelező gate

A végén futtasd egyszer:

```bash
./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_spacing_margin_bin_offset_model.md