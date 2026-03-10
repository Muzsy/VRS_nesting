# canvases/web_platform/h0_e1_t1_modulhatarok_veglegesitese.md

# H0-E1-T1 modulhatarok veglegesitese

## Funkcio
A feladat a H0-E1-T1 backlog pont formalizalasa: a platform fo logikai moduljainak,
ownership boundary-jeinek, input/output szerzodeseinek es tiltott felelossegeinek
vegleges rogzitese. A cel, hogy a H0 core schema, majd a H1/H2/H3 fejlesztesek mar
egy lezart, nem solver-kozpontu architekturara epuljenek.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - Platform Core, Geometry Pipeline, Nesting Engine Adapter, Viewer/Reporting,
    Manufacturing, Postprocess, Decision Layer modulhatarainak rogzitese;
  - ownership matrix: melyik modul mit birtokol, mit olvas, mit allit elo,
    es mit NEM csinalhat;
  - definicio / hasznalat / snapshot / artifact / projection kulonvalasztasanak
    formalizalasa;
  - snapshot-first futasi modell es engine adapter boundary explicit dokumentalasa;
  - egy dedikalt H0 boundary source-of-truth dokumentum letrehozasa;
  - docs/web_platform szintu hivatkozasok frissitese a boundary dokumentumra.
- Nincs benne:
  - Supabase migraciok irasa;
  - API endpoint implementacio;
  - worker queue vagy run contract reszletes schema-szintu kialakitasa;
  - manufacturing es postprocess reszletes domainmodell kibontasa;
  - frontend vagy viewer implementacio.

### Feladatlista
- [ ] Kesz legyen egy dedikalt H0 modulhatar dokumentum.
- [ ] Mind a 7 fo modulra legyen kulon szekcio:
  - purpose
  - ownership
  - inbound inputok
  - outbound outputok
  - tiltott felelossegek
- [ ] Legyen kulon boundary szabaly a definicio / hasznalat / snapshot /
  artifact / projection szetvalasztasra.
- [ ] Legyen kimondva, hogy a solver nem olvas kozvetlenul elo domain allapotot,
  csak snapshot + derivative inputot.
- [ ] Legyen kimondva, hogy a viewer source of truth projection, nem SVG.
- [ ] README + architecture + H0 roadmap doksi hivatkozzon a boundary dokumentumra.
- [ ] Repo gate le legyen futtatva a task reporton.

### Erintett fajlok
- `canvases/web_platform/h0_e1_t1_modulhatarok_veglegesitese.md`
- `codex/goals/canvases/web_platform/fill_canvas_h0_e1_t1_modulhatarok_veglegesitese.yaml`
- `codex/prompts/web_platform/h0_e1_t1_modulhatarok_veglegesitese/run.md`
- `codex/codex_checklist/web_platform/h0_e1_t1_modulhatarok_veglegesitese.md`
- `codex/reports/web_platform/h0_e1_t1_modulhatarok_veglegesitese.md`
- `docs/web_platform/README.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`

### Elvart tartalom a boundary dokumentumban
- modul katalogus
- boundary matrix
- source-of-truth matrix
- ownership szabalyok
- tilos coupling lista
- handoff contractok:
  - Geometry Pipeline -> Engine Adapter
  - Engine Adapter -> Run Results / Projection
  - Manufacturing -> Postprocess
  - Decision Layer -> run selection / comparison
- H0/H1 kovetkezmenyek
- anti-pattern lista:
  - solver-kozpontu architektura
  - elo DB-bol ad-hoc solver input
  - artifact/projection osszemosasa
  - manufacturing truth es nesting truth osszemosasa

### DoD
- [ ] Letrejon a `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
      dokumentum.
- [ ] A dokumentum egyertelmuen lezarja a Platform Core, Geometry Pipeline,
      Nesting Engine Adapter, Viewer/Reporting, Manufacturing, Postprocess,
      Decision Layer hatarait.
- [ ] Egyertelmuen dokumentalt, hogy a definicio, hasznalat, snapshot,
      artifact es projection kulon vilag.
- [ ] Egyertelmuen dokumentalt, hogy a worker/engine adapter csak snapshotbol
      dolgozik, nem elo domain tablakbol.
- [ ] Egyertelmuen dokumentalt, hogy a viewer source of truth projection,
      az SVG csak render artifact.
- [ ] A `docs/web_platform/README.md`,
      `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
      es `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
      hivatkozik a vegleges boundary dokumentumra.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h0_e1_t1_modulhatarok_veglegesitese.md`
      PASS.

### Kockazat + rollback
- Kockazat:
  - docs drift: a fo architektura-doksi, a H0 roadmap es az uj boundary dokumentum
    ellentmondasba kerulhet;
  - tul absztrakt leiras, ami nem ad eleg eros implementacios guardrail-t.
- Mitigacio:
  - az uj boundary dokumentum legyen az explicit source of truth;
  - a tobbi doksi roviden hivatkozzon vissza erre, ne duplikalja teljesen;
  - ownership es tiltott felelossegek tablas formaban is jelenjenek meg.
- Rollback:
  - kizarolag dokumentacios valtozasok tortenjenek;
  - a teljes task egy commitban visszagorgetheto legyen.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h0_e1_t1_modulhatarok_veglegesitese.md`
- Feladat-specifikus manualis ellenorzes:
  - a 7 modul mindegyike szerepel;
  - minden modulhoz ownership + tiltott felelosseg szerepel;
  - kulon ki van mondva az artifact vs projection es a snapshot-first boundary;
  - nincs olyan allitas, ami H0/H1/H2/H3 dokumentumokkal ellentmond.

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/README.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/platform_roadmap_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_master_roadmap_h0_h3.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_priorizalt_sprint_backlog_p0_p1_p2.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`