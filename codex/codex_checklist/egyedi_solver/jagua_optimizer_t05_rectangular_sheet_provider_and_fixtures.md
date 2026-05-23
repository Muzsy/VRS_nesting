# Checklist — JG-05 jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures

## Feladat

Rectangular sheet provider contract és determinisztikus outer-only fixture pack létrehozása a JG-03/JG-04 utáni Phase 1 solver lánchoz.

## Dependency

- [x] JG-03 report első sora `PASS`.
- [x] JG-03 report tartalmazza: `JG-04_STATUS: READY`.
- [x] JG-04 report létezik.
- [x] JG-04 report első sora `PASS`.
- [x] JG-04 report tartalmazza: `JG-05_STATUS: READY` vagy egyértelmű next readiness jelzést.
- [x] Repo szabályfájlok elolvasva: `AGENTS.md`, `docs/codex/overview.md`, `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md`, `docs/qa/testing_guidelines.md`.
- [x] Projektterv dokumentumok elolvasva.

## Rectangular sheet provider contract

- [x] Rectangular sheet provider szerződése dokumentált.
- [x] `Stock.quantity` → expanded sheet lista determinisztikus.
- [x] Stable `sheet_index` mapping ellenőrizve.
- [x] Több stock + több quantity mapping evidence dokumentálva.
- [x] `quantity <= 0` policy dokumentált vagy controlled errorral kezelt. — DEVIATION: Rust skip, Py ValueError (dokumentálva).
- [x] Margin/gap mezők státusza dokumentált: supported / ignored-but-documented / blocked. — DEVIATION: validator-only, nem Rust runtime mező.
- [x] Jagua-specifikus backend típusok nem szivárognak át a publikus sheet provider contractba.

## Fixture pack

- [x] `tests/fixtures/egyedi_solver/jagua_rect_smoke.json` létrejött.
- [x] `tests/fixtures/egyedi_solver/jagua_rect_medium.json` létrejött.
- [x] Smoke fixture outer-only, kicsi és gyors.
- [x] Small realistic / medium fixture outer-only és több quantity-t tartalmaz.
- [x] Fixture-ök contract_version v1 szerint validak.
- [x] Fixture-ök nem tartalmaznak hole-os partot vagy csendes geometry loss kockázatot.
- [x] `allowed_rotations_deg` minden partnál explicit.

## Smoke / validation

- [x] `scripts/smoke_jagua_rectangular_sheet_provider.py` létrejött.
- [x] Smoke fixture runner útvonalon fut.
- [x] Medium fixture runner útvonalon fut.
- [x] Exact validator PASS minden elfogadott layouton.
- [x] Invalid sheet index / invalid output negatív esetet a validator elutasítja.
- [x] Stable `sheet_index` range ellenőrzés dokumentált.
- [x] `cargo build --release --manifest-path rust/vrs_solver/Cargo.toml` PASS.
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml` PASS.
- [x] `python3 scripts/smoke_jagua_rectangular_sheet_provider.py` PASS — 11/11.
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures.md` PASS — exit 0.
- [x] Verify log mentve: `codex/reports/egyedi_solver/jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures.verify.log`.

## Report / checklist

- [x] Report tartalmaz dependency evidence-t.
- [x] Report tartalmaz valós code-boundary auditot.
- [x] Report tartalmaz fixture listát és futtatási parancsokat.
- [x] Report tartalmaz sheet_index mapping evidence-t.
- [x] Report tartalmaz invalid/rejected evidence-t.
- [x] Report tartalmaz exact validation evidence-t.
- [x] Globális progress checklist JG-05 szakasza frissítve.
- [x] Ha eltérés volt a tervtől, `DISCOVERED_MISMATCH`, `DEVIATION` vagy `REQUIRES_DECISION` blokk dokumentálja. — 2 DEVIATION rögzítve.
- [x] Report végső státusza: PASS / REVISE / BLOCKED.
- [x] Következő task indíthatósága jelölve: `JG-06_STATUS: READY` vagy `NOT_READY`.
