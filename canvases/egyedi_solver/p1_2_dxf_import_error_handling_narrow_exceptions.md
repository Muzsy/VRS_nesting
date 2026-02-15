# canvases/egyedi_solver/p1_2_dxf_import_error_handling_narrow_exceptions.md
# P1-2: DXF import hibakezelés célzott szűkítése (ne `except Exception`)

## 🎯 Funkció

A cél, hogy a DXF import pipeline-ban megszüntessük a túl tág `except Exception` ágakat, és helyettük célzott, elvárt kivételeket kapjunk el:

- DXF beolvasás (`ezdxf.readfile`) → célzott kivételek → stabil `DxfImportError("DXF_READ_FAILED", ...)`
- Geometria tisztítás (`clean_ring`) → célzott `GeometryCleanError` kezelése → stabil `DxfImportError("DXF_INVALID_RING", ...)`
- SPLINE flattening fallback → ne „mindent elkapó” Exception, hanem ésszerűen szűkített kivételek

A meglévő funkciók nem sérülhetnek: ugyanazokat a `DxfImportError.code`-okat és ugyanazt a viselkedést kell megtartani, csak a hibakezelés legyen precízebb.

## 🧠 Fejlesztési részletek

### Scope

**Benne van**
- `vrs_nesting/dxf/importer.py` összes `except Exception` ágának átírása célzott kivételekre.
- Ahol kell: új import(ok) (pl. `GeometryCleanError`) felvétele.
- Új/hiányzó unit tesztek hozzáadása, hogy:
  - ne szivárogjanak ki belső kivételek (GeometryCleanError, ezdxf hibák),
  - a `DxfImportError.code` determinisztikus maradjon.

**Nincs benne**
- Exporter/egyéb modulok exception-polírozása (csak import).
- Új DXF diagnosztikai report/mentett debug artifact (külön P1-2 “diagnosztika” feladat).

### Konkrét target helyek (jelenlegi állapot)

- `vrs_nesting/dxf/importer.py`
  - DXF read: `except Exception` → célzott (ezdxf + IO + decode)
  - SPLINE flatten: `except Exception` → célzott (flattening/attrib jellegű + ezdxf)
  - `clean_ring(...)` körüli blokkok: `except Exception` → `except GeometryCleanError`

### Javasolt célzott kivételek (irány)

- `ezdxf.readfile(...)`:
  - `except (OSError, UnicodeDecodeError, ezdxf.DXFError) as exc: ...`
  - Megjegyzés: a DXFStructureError tipikusan DXFError leszármazott, így lefedett.

- `clean_ring(...)`:
  - `except GeometryCleanError as exc: ...`

- SPLINE flatten fallback:
  - `except (AttributeError, TypeError, ValueError, ezdxf.DXFError): ...`
  - A fallback ág maradjon: fit_points → control_points.

### DoD

- [ ] `vrs_nesting/dxf/importer.py`-ben nincs `except Exception` az import útvonalon.
- [ ] A DXF read hibák továbbra is `DxfImportError(code="DXF_READ_FAILED")`-be fordulnak.
- [ ] A degenerate/invalid ring hibák továbbra is `DxfImportError(code="DXF_INVALID_RING")`-be fordulnak.
- [ ] Új unit teszt(ek) lefedik legalább:
  - invalid ring → `DXF_INVALID_RING`
  - nem-érvényes dxf tartalom → `DXF_READ_FAILED`
- [ ] Repo gate PASS:
  - `./scripts/verify.sh --report codex/reports/egyedi_solver/p1_2_dxf_import_error_handling_narrow_exceptions.md`

### Kockázat + mitigáció + rollback

- Kockázat: túl szűk kivétellista miatt bizonyos hibák nem fordulnak `DxfImportError`-be.
- Mitigáció: DXF read esetén `ezdxf.DXFError` bevonása, plusz unit teszt nem-DXF bemenetre.
- Rollback: célzott kivételek visszabővítése (de továbbra se `Exception`), vagy a változtatás revert.

## 🧪 Tesztállapot

- `./scripts/verify.sh --report codex/reports/egyedi_solver/p1_2_dxf_import_error_handling_narrow_exceptions.md`
- `./scripts/check.sh`

## 🌍 Lokalizáció

Nem releváns.

## 📎 Kapcsolódások

- `vrs_nesting/dxf/importer.py`
- `vrs_nesting/geometry/clean.py`
- `tests/test_dxf_importer_json_fixture.py` (mintázat)
- `scripts/check.sh`
- `scripts/verify.sh`
