# DXF export sheet-enkent (MVP)

## 🎯 Funkcio
Ez a task az MVP szintu gyartasi kimenetet rogziti: sheet-enkenti DXF export a solver placement alapjan, futasi artifact strukturahoz kotve.

## 🧠 Fejlesztesi reszletek
### Scope
- Benne van:
  - DXF exporter modul MVP letrehozasa.
  - Sheet-enkenti output naming szabaly (`sheet_001.dxf`, ...).
  - Run reportba export metrikak es output pathok rogzitese.
- Nincs benne:
  - Preview renderer.
  - Halado layer/preset tamogatas.
  - CAD interoperabilitasi teljes matrix.

### Erintett fajlok
- `NINCS: vrs_nesting/dxf/exporter.py`
- `NINCS: samples/project_rect_1000x2000.json`
- `codex/codex_checklist/egyedi_solver/dxf_export_per_sheet_mvp.md`
- `codex/reports/egyedi_solver/dxf_export_per_sheet_mvp.md`

### DoD
- [ ] Letrejon legalabb egy export fajl: `runs/<run_id>/out/sheet_001.dxf`.
- [ ] Placement transzformaciok helyesek a cel-sheet koordinataban.
- [ ] Ures sheet nem exportalodik.
- [ ] Export report tartalmazza sheet metrikakat.
- [ ] Verify gate PASS.

### Kockazat + mitigacio + rollback
- Kockazat: DXF entitas mapping inkompatibilitas downstream toolokkal.
- Mitigacio: MVP layer konvencio fixalasa + golden minta export.
- Rollback: exporter modul izolalt, fallback output option kikapcsolhato.

## 🧪 Tesztallapot
- Kotelezo gate: `./scripts/verify.sh --report codex/reports/egyedi_solver/dxf_export_per_sheet_mvp.md`
- Task-specifikus ellenorzes a vegrehajto runban:
  - Golden minta export diff.
  - Output fajl letrehozas es naming ellenorzes.

## 🌍 Lokalizacio
Nem relevans.

## 📎 Kapcsolodasok
- `codex/reports/egyedi_solver_backlog.md`
- `tmp/egyedi_solver/dxf_nesting_app_7_multi_sheet_wrapper_reszletes.md`
- `tmp/egyedi_solver/mvp_terv_tablas_nesting_fix_w_h_alakos_tabla_alap_a_meglevo_vrs_nesting_repora_epitve.md`
- `docs/codex/overview.md`
- `scripts/check.sh`
- `scripts/verify.sh`
