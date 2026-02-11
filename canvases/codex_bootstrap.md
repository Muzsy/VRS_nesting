# Canvas — codex_bootstrap

## Cél

A Codex bootstrap artefaktok konzisztens lezárása:
- hiányzó canvas pótlása,
- kötelező verify futtatás reporttal,
- checklist és report DoD/Evidence lezárása.

## Nem-cél

- Sparrow IO contract módosítása.
- Validator vagy CI viselkedés változtatása.

## Érintett fájlok

- `canvases/codex_bootstrap.md`
- `codex/goals/canvases/fill_canvas_codex_bootstrap.yaml`
- `codex/codex_checklist/codex_bootstrap.md`
- `codex/reports/codex_bootstrap.md`
- `codex/reports/codex_bootstrap.verify.log` *(auto, verify hozza létre)*

## Feladatlista

- [x] Hiányzó canvas létrehozása.
- [x] Verify wrapper futtatása report célfájllal.
- [x] Report mezők és DoD→Evidence kitöltése.
- [x] Checklist pontok kipipálása.

## Kockázatok és rollback

- Kockázat: a verify futás FAIL lehet környezeti vagy függőségi ok miatt.
- Rollback: dokumentációs fájlok visszaállíthatók az előző commitra; kódmódosítás nincs.

## Teszt / Ellenőrzés

- Kötelező parancs: `./scripts/verify.sh --report codex/reports/codex_bootstrap.md`
