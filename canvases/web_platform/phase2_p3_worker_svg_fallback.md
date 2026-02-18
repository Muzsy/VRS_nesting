# canvases/web_platform/phase2_p3_worker_svg_fallback.md

# Phase 2 P2.3 worker SVG fallback

## Funkcio
A Phase 2.3 feladat celja, hogy a worker ellenorizze a `out/sheet_NNN.svg`
artifactokat, es ha hianyzik vagy ures SVG, akkor fallback SVG-t generaljon
`solver_output.json` + `solver_input.json` alapjan.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - worker oldali SVG existence/size check;
  - fallback SVG generalas placement adatokbol;
  - fallback SVG upload + artifact metadata frissites.
- Nincs benne:
  - frontend viewer modositas;
  - DXF exporter ujratervezes.

### Erintett fajlok
- `canvases/web_platform/phase2_p3_worker_svg_fallback.md`
- `codex/goals/canvases/web_platform/fill_canvas_phase2_p3_worker_svg_fallback.yaml`
- `codex/codex_checklist/web_platform/phase2_p3_worker_svg_fallback.md`
- `codex/reports/web_platform/phase2_p3_worker_svg_fallback.md`
- `worker/main.py`
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`

### DoD
- [ ] Worker ellenorzi az SVG artifactok jelenletet es meretet.
- [ ] Hianyzo/ures esetben fallback SVG keszul sheet szinten.
- [ ] Fallback SVG artifact feltoltesre kerul Storage-ba.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/phase2_p3_worker_svg_fallback.md` PASS.

### Kockazat + rollback
- Kockazat: fallback SVG geometria leegyszerusitett lehet.
- Mitigacio: explicit fallback jelleg, normal export elsodleges marad.
- Rollback: worker fallback blokkok visszavonhatok egy commitban.
