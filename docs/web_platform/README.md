# Web Platform dokumentumok

Ez a mappa a DXF Nesting platform **web/platform-oldali architekturális, roadmap- és backlog dokumentumait** tartalmazza.

A célja, hogy a nesting engine köré épülő teljes platform ne ad-hoc módon fejlődjön, hanem egy egységes, moduláris, verziózott és hosszú távon bővíthető terv mentén.

## A mappa szerepe

Ide azok a dokumentumok tartoznak, amelyek:

- a platform **felépítését** írják le,
- a **Supabase / PostgreSQL domainmodellt** rögzítik,
- a fejlesztés **roadmapját** bontják fázisokra,
- a roadmapből **implementációs backlogot** és **priorizált végrehajtási sorrendet** készítenek.

Ez a mappa **nem** a konkrét Codex-taskok helye.  
A konkrét végrehajtási feladatok továbbra is a `canvases/web_platform/` és a hozzájuk tartozó `codex/` struktúrába valók.

---

## Javasolt olvasási sorrend

### 1. Architektúra és domainmodell
Elsőként ezt érdemes elolvasni:

- `architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `architecture/h0_modulhatarok_es_boundary_szerzodes.md` (modulhatar source-of-truth)

Ez a platform alapdokumentuma:
- modulhatárok
- geometry / nesting / manufacturing / postprocess szétválasztás
- Supabase SQL-szintű domainmodell
- alap storage és RLS elvek

Modulhatar/ownership kerdesben a `h0_modulhatarok_es_boundary_szerzodes.md` az elsosegi forras.

### 2. Összevont roadmap
Utána ez jön:

- `roadmap/dxf_nesting_platform_master_roadmap_h0_h3.md`

Ez adja a teljes H0–H3 ívet egyben:
- mit jelent a H0, H1, H2, H3
- milyen sorrendben épül fel a platform
- mi mire épül rá

### 3. Priorizált backlog
Ezután ezt érdemes nézni:

- `roadmap/dxf_nesting_platform_priorizalt_sprint_backlog_p0_p1_p2.md`

Ez a gyakorlati prioritási nézet:
- mi P0
- mi P1
- mi P2
- mi kritikus
- mi halasztható

### 4. Implementációs task tree
Utána jöhet:

- `roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`

Ez már phase → epic → task bontásban rendezi a fejlesztést.

### 5. Részletes fázisdokumentumok
Ha egy adott szakaszt kell kidolgozni, ezekhez kell visszanyúlni:

- `roadmap/dxf_nesting_platform_h0_reszletes.md`
- `roadmap/dxf_nesting_platform_h1_reszletes.md`
- `roadmap/dxf_nesting_platform_h2_reszletes.md`
- `roadmap/dxf_nesting_platform_h3_reszletes.md`

### 6. Teljes roadmap részletes változat
Kiegészítő, hosszabb összefoglaló:

- `platform_roadmap_reszletes.md`

---

## Javasolt könyvtárszerkezet

```text
docs/
  web_platform/
    README.md
    platform_roadmap_reszletes.md
    architecture/
      dxf_nesting_platform_architektura_es_supabase_schema.md
      h0_modulhatarok_es_boundary_szerzodes.md
    roadmap/
      dxf_nesting_platform_h0_reszletes.md
      dxf_nesting_platform_h1_reszletes.md
      dxf_nesting_platform_h2_reszletes.md
      dxf_nesting_platform_h3_reszletes.md
      dxf_nesting_platform_master_roadmap_h0_h3.md
      dxf_nesting_platform_implementacios_backlog_task_tree.md
      dxf_nesting_platform_priorizalt_sprint_backlog_p0_p1_p2.md
```

---

## Mi mire való röviden

### `architecture/`
Ide a stabilabb, hosszabb életű **source-of-truth architekturális dokumentumok** tartoznak.

### `roadmap/`
Ide a fejlesztési útiterv, fázisbontás, backlog és priorizálási anyagok tartoznak.

### `canvases/web_platform/`
Ide **nem** ezek a stratégiai anyagok mennek, hanem a konkrét végrehajtási task-spec doksik.

---

## Fontos elv

A platform dokumentációban végig meg kell tartani ezeket a szétválasztásokat:

- source file vs canonical geometry
- geometry revision vs part revision
- project input vs run snapshot
- solver output vs platform projection
- nesting geometry vs manufacturing geometry
- manufacturing plan vs machine-ready export
- stock sheet vs remnant
- stratégiai roadmap vs konkrét implementációs task

Ha ez megmarad, a dokumentáció és vele együtt a rendszer is kezelhető marad.

---

## Kapcsolódás a repóhoz

Ez a dokumentumhalmaz a repo azon részéhez tartozik, amely a web/platform oldali fejlődési irányt rögzíti.  
A nesting engine konkrét technikai részletei továbbra is a meglévő engine-dokumentáció és a hozzá kapcsolódó task/canvas anyagok mentén fejlődnek.

Ez a mappa tehát a **platformszintű tervezési és szervezőréteg** dokumentációja.
