# canvases/web_platform/h0_e1_t2_domain_entitasterkep_veglegesitese.md

# H0-E1-T2 domain entitasterkep veglegesitese

## Funkcio
A feladat a web platform domain szintjen hasznalt fo entitasok, aggregate-hatarok,
kapcsolatok, ownership szabalyok es source-of-truth szerepek vegleges rogzitese.
A cel, hogy a H0 core schema mar ne absztrakt architekturara, hanem egy lezart
domain entitasterkepre epuljon.

Ez a task kozvetlenul a H0-E1-T1 modulhatarok veglegesitese utan kovetkezik.
A modulok mar le vannak zarva; most azt kell rogzitni, hogy a platformon belul
milyen domain objektumok leteznek, ezek hogyan kapcsolodnak egymashoz, mi a
primer azonossaguk, mi az eletciklusuk, es melyik reteg birtokolja oket.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - a fo domain entitasok katalogusba rendezese;
  - aggregate es ownership boundary rogzitese;
  - entity vs value object vs derived artifact kulonvalasztasa;
  - identifier-strategia es kulcsazonossag leirasa;
  - eletciklus es allapotatmenetek magas szintu rogzitese;
  - domain kapcsolatok es cardinalitasok formalizalasa;
  - source-of-truth matrix entitas szinten;
  - dedikalt H0 domain entitasterkep dokumentum letrehozasa;
  - a fo web_platform dokumentumok hivatkozasainak frissitese.
- Nincs benne:
  - SQL migraciok irasa;
  - konkret tabla-DDL vagy RLS policy kidolgozasa;
  - API contractok reszletes OpenAPI-szintu definialasa;
  - queue/run payload schema reszletes JSON-szintu definialasa;
  - solver output schema implementalasa;
  - frontend modellek vagy TypeScript tipusok bevezetese.

### Fo domain kerdesek, amiket le kell zarni
- [ ] Mi szamit elso osztalyu domain entitasnak?
- [ ] Mi szamit csak derivalt / projection / artifact adatnak?
- [ ] Hol van a hatar Project, Technology Setup, Part Definition, Part Instance,
      Sheet Definition, Sheet Inventory, Run Snapshot, Run Result, Export Job,
      Remnant, Review/Decision objektumok kozott?
- [ ] Melyik entitas minek a gyermeke, es mi az aggregate root?
- [ ] Mi az azonositas alapja: UUID, external fingerprint, canonical hash,
      revision ID vagy ezek kombinacioja?
- [ ] Melyik entitas immutable snapshot, es melyik elerheto "elo" allapotkent?
- [ ] Melyik domain adat a Platform Core truth, es mi csak worker/viewer/manufacturing
      altal eloallitott szarmaztatott eredmeny?

### Feladatlista
- [ ] Kesz legyen egy dedikalt H0 domain entitasterkep dokumentum.
- [ ] Legyen egy "entity catalog" szekcio, amely felsorolja a fo entitasokat.
- [ ] Minden fo entitashoz legyen:
  - rovid definicio
  - tipus (entity / value object / snapshot / artifact / projection)
  - owner modul
  - primer azonosito
  - fo kapcsolatok
  - lifecycle/megjegyzes
- [ ] Legyen aggregate matrix.
- [ ] Legyen source-of-truth matrix entitas szinten.
- [ ] Legyen explicit kulonvalasztva a definition, usage, snapshot, result, artifact.
- [ ] README + architecture + H0 roadmap frissuljon az uj dokumentum hivatkozasaval.
- [ ] Repo gate le legyen futtatva a reporton.

### Erintett fajlok
- `canvases/web_platform/h0_e1_t2_domain_entitasterkep_veglegesitese.md`
- `codex/goals/canvases/web_platform/fill_canvas_h0_e1_t2_domain_entitasterkep_veglegesitese.yaml`
- `codex/prompts/web_platform/h0_e1_t2_domain_entitasterkep_veglegesitese/run.md`
- `codex/codex_checklist/web_platform/h0_e1_t2_domain_entitasterkep_veglegesitese.md`
- `codex/reports/web_platform/h0_e1_t2_domain_entitasterkep_veglegesitese.md`
- `docs/web_platform/README.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`

### Elvart tartalom az uj domain dokumentumban
- domain model celja
- entity catalog
- javasolt fo entitasok, legalabb az alabbi vilag lefedesere:
  - Project
  - Project Revision / Domain Revision logika, ha relevans
  - Technology Setup
  - Material Spec / Machine Spec / Cutting Rules jellegu konfiguracio
  - Part Definition
  - Part Revision
  - Part Demand / Part Requirement / Part Quantity igeny
  - Sheet Definition
  - Sheet Stock Unit / Sheet Inventory
  - Remnant
  - Nesting Job / Run Request
  - Run Snapshot
  - Run Result
  - Placement Result / Nest Result Projection
  - Export Job / Manufacturing Package
  - Review / Decision / Selection objektum
- aggregate root javaslatok
- ownership matrix
- source-of-truth matrix
- lifecycle notes
- immutable vs mutable elvalasztas
- definition vs snapshot vs result vs artifact matrix
- schema kovetkezmenyek H0-E2-hoz
- anti-pattern lista:
  - Part Definition es Part Demand osszemosasa
  - Sheet Definition es Inventory Unit osszemosasa
  - Run Snapshot es Run Result osszemosasa
  - Projection truth-kent kezelese result helyett
  - Remnantot sima sheet definiciokent kezelni
  - Export artifactot domain truth-kent kezelni

### DoD
- [ ] Letrejon a `docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md`
      dokumentum.
- [ ] A dokumentum egyertelmuen elvalasztja az entitasokat, value objecteket,
      snapshotokat, resultokat, projectionokat es artifactokat.
- [ ] Dokumentalva van a fo domain entitasok ownership-je es az aggregate-hatar.
- [ ] Dokumentalva van a fo kapcsolatok es cardinalitasok magas szinten.
- [ ] Dokumentalva van, mely adatok immutable snapshotok, es melyek elo konfiguracios
      vagy inventory allapotok.
- [ ] A `docs/web_platform/README.md`,
      `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`,
      `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
      es `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
      hivatkozik az uj domain entitasterkep dokumentumra.
- [ ] A dokumentum explicit inputkent hasznalhato a kovetkezo H0-E2 core schema taskhoz.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h0_e1_t2_domain_entitasterkep_veglegesitese.md`
      PASS.

### Kockazat + rollback
- Kockazat:
  - a dokumentum tul kozel megy SQL tablakhoz, es elvesziti a domain-szintu tisztasagot;
  - vagy ellenkezoleg: tul absztrakt marad, es nem ad schema-epitesi fogodzot;
  - egyes entitasok keverik a definiciot, a keresletet es a futasi snapshotot.
- Mitigacio:
  - minden entitashoz kotelezo tipus-megjeloles;
  - kulon matrix keszul immutable vs mutable, valamint truth vs derived nezetrol;
  - a H0-E1-T1 boundary dokumentummal osszhang kotelezo.
- Rollback:
  - docs-only modositasok tortenjenek;
  - egy commitban visszafordithato legyen az egesz task.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h0_e1_t2_domain_entitasterkep_veglegesitese.md`
- Manualis ellenorzes:
  - minden fo entitas szerepel;
  - nincs keveredese a definicio / snapshot / result / artifact vilagoknak;
  - a modul boundary dokumentummal konzisztens;
  - a kovetkezo schema task szamara eleg konkret a fogalmazas.

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/README.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/platform_roadmap_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_master_roadmap_h0_h3.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_priorizalt_sprint_backlog_p0_p1_p2.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`