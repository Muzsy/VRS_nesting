# H0 domain entitasterkep es ownership matrix (source of truth)

## 1. Dokumentum szerepe

Ez a dokumentum a H0 domain entitasok, aggregate-hatarok, ownership szabalyok,
es source-of-truth felelossegek normativ leirasa.

Prioritas konfliktus eseten:
1. modulhatarok es retegfelelossegek: `h0_modulhatarok_es_boundary_szerzodes.md`
2. domain entitas-tipusok es ownership: ez a dokumentum
3. roadmap/osszefoglalo doksik: tamogato jellegu anyagok

Kapcsolodo dokumentumok:
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`

## 2. Domain vilagok explicit szetvalasztasa

### 2.1 Fogalmi szetvalasztas

- Definition: hosszu eletu, verziozott torzs-definicio (pl. `part_definition`, `sheet_definition`).
- Usage: project kontextusban aktivalt valasztas (pl. `project_technology_selection`).
- Demand: igenyoldali mennyiseg/szabaly (pl. `part_demand`, `sheet_inventory_allocation`).
- Snapshot: futas inditasakor befagyasztott immutable allapot (`run_snapshot`).
- Result: engine/manufacturing kimenet canonical strukturaban (`run_result`, `manufacturing_package`).
- Projection: query/view celu szarmaztatott adat (`placement_projection`, metrics).
- Artifact/Export: fajl/blobjellegu output (SVG/DXF/ZIP/machine program).

### 2.2 Mi NEM ugyanaz

- `Part Definition` != `Part Demand`
- `Sheet Definition` != `Sheet Inventory Unit`
- `Run Snapshot` != `Run Result`
- `Projection` != domain truth
- `Export Artifact` != domain truth

## 3. Entitas kategoriak

### 3.1 Elso osztalyu domain entitasok

- Project
- Technology Setup
- Part Definition
- Part Revision
- Part Demand
- Sheet Definition
- Sheet Revision
- Sheet Inventory Unit
- Remnant
- Run Request
- Run Snapshot
- Run Result
- Export Job
- Review Decision

### 3.2 Value objectek (nem aggregate root)

- MaterialSpec
- MachineSpec
- CuttingRuleSetRef
- KerfPolicy
- RotationPolicy
- QuantityDemand
- TimeBudgetPolicy
- TolerancePolicy
- CostHint
- FingerprintHash

### 3.3 Immutable snapshot objektumok

- RunSnapshotPartDemand
- RunSnapshotSheetInput
- RunSnapshotTechnology
- RunSnapshotManufacturing
- RunSnapshotGeometryRef
- RunSnapshotEngineOptions

### 3.4 Result / projection / artifact objektumok

- RunResultPlacementSet (result)
- RunResultUnplacedSet (result)
- PlacementProjectionSheet (projection)
- PlacementProjectionItem (projection)
- RunMetricsProjection (projection)
- SolverOutputArtifact (artifact)
- ViewerSvgArtifact (artifact)
- SheetDxfArtifact (artifact)
- BundleZipArtifact (artifact)
- MachineProgramArtifact (artifact)

## 4. Entity catalog

| Entitas | Tipus | Owner modul | Primer azonosito | Fo kapcsolatok | Lifecycle / megjegyzes |
| --- | --- | --- | --- | --- | --- |
| Project | Entity (aggregate root) | Platform Core | `project_id` (UUID) | 1:N PartDemand, 1:N SheetInventoryUnit, 1:N RunRequest, 1:1 active TechnologySetup | Aktiv allapotban szerkesztheto; archived allapotban immutable konfiguracios szinten |
| TechnologySetup | Entity | Platform Core | `technology_setup_id` (UUID) + `version` | N:1 Project, 1:N value object policy | Verziozott konfiguracio; run snapshot csak adott verziot fagyaszt |
| PartDefinition | Entity (aggregate root) | Platform Core | `part_definition_id` (UUID) | 1:N PartRevision | Nem tartalmaz project-specifikus mennyiseget |
| PartRevision | Entity | Geometry Pipeline + Platform Core | `part_revision_id` (UUID) + canonical hash | N:1 PartDefinition, 1:1 geometry revision | Immutable revizio; uj forras -> uj revision |
| PartDemand | Entity | Platform Core | `part_demand_id` (UUID) | N:1 Project, N:1 PartRevision | Demand vilag; mennyiseg/prioritas itt lakik, nem PartDefinitionben |
| SheetDefinition | Entity (aggregate root) | Platform Core | `sheet_definition_id` (UUID) | 1:N SheetRevision | A tabla-tipus definicio, nem inventory peldany |
| SheetRevision | Entity | Geometry Pipeline + Platform Core | `sheet_revision_id` (UUID) + canonical hash | N:1 SheetDefinition | Shape valtozas revizioval megy |
| SheetInventoryUnit | Entity | Platform Core | `sheet_inventory_unit_id` (UUID) | N:1 Project, N:1 SheetRevision, 0:N Remnant | Fizikai/kvazi-fizikai keszlet-egyseg, allapotatmenettel |
| Remnant | Entity | Manufacturing | `remnant_id` (UUID) | N:1 SheetInventoryUnit vagy N:1 prior Remnant | Nem SheetDefinition, hanem eredmeny-oldali keszletmaradek |
| RunRequest | Entity (aggregate root) | Platform Core | `run_request_id` (UUID) | N:1 Project, 1:1 RunSnapshot, 0:1 RunResult | `draft -> queued -> running -> succeeded/failed/cancelled` |
| RunSnapshot | Immutable snapshot entity | Platform Core | `run_snapshot_id` (UUID) | 1:1 RunRequest, 1:N snapshot children | Snapshot csak append-only; utolag nem irhato at |
| RunResult | Entity | Nesting Engine Adapter | `run_result_id` (UUID) | 1:1 RunRequest, 1:N result sets, 0:N artifacts | Snapshotbol kepzett canonical eredmeny |
| PlacementProjection | Projection aggregate | Viewer/Reporting | `run_result_id` + projection version | N:1 RunResult | Query optimalizalt; nem domain truth |
| ExportJob | Entity | Postprocess | `export_job_id` (UUID) | N:1 RunResult, 1:N artifact | Gepfuggo export futas; ujraprodukalhato snapshot/result alapjan |
| ManufacturingPackage | Result entity | Manufacturing | `manufacturing_package_id` (UUID) | N:1 RunResult, 0:N ExportJob | Manufacturing policy alkalmazott eredmeny |
| ReviewDecision | Entity | Decision Layer | `review_decision_id` (UUID) | N:1 Project, optional N:1 RunResult | Emberi/policy dontes audit trail |

## 5. Aggregate root es ownership matrix

| Aggregate root | Birtokolt gyermekek | Owner modul | Cross-aggregate kapcsolat |
| --- | --- | --- | --- |
| Project | TechnologySetup, PartDemand, SheetInventoryUnit, RunRequest, ReviewDecision | Platform Core | PartRevision / SheetRevision referenciat hasznal |
| PartDefinition | PartRevision | Platform Core + Geometry Pipeline | Project oldalon PartDemand referalja |
| SheetDefinition | SheetRevision | Platform Core + Geometry Pipeline | Project oldalon SheetInventoryUnit referalja |
| RunRequest | RunSnapshot, RunResult (referencia), artifacts manifest | Platform Core + Engine Adapter | Projection/Export kulon aggregate |
| RunResult | Placement result set, Unplaced set | Nesting Engine Adapter | Viewer projection es ManufacturingPackage erre epul |
| ManufacturingPackage | Manufacturing result komponensek | Manufacturing | ExportJob erre epul |
| ExportJob | Export artifacts | Postprocess | RunResult + ManufacturingPackage bemenet |

Ownership szabaly:
- Aggregate rooton kivuli objektum kulso modulbol csak API-level contracton keresztul modosithato.
- Snapshot aggregate append-only; mutable update tilos.

## 6. Kapcsolatok es cardinalitasok (magas szint)

- Project 1:N PartDemand
- Project 1:N SheetInventoryUnit
- Project 1:N RunRequest
- PartDefinition 1:N PartRevision
- SheetDefinition 1:N SheetRevision
- RunRequest 1:1 RunSnapshot
- RunRequest 0:1 RunResult
- RunResult 1:N PlacementProjectionItem
- RunResult 0:N ExportJob
- SheetInventoryUnit 0:N Remnant
- RunResult 0:1 ManufacturingPackage
- Project 0:N ReviewDecision

## 7. Source-of-truth matrix (entitas szinten)

| Objektum | Source of truth | Canonical tarolo vilag | Nem source-of-truth pelda |
| --- | --- | --- | --- |
| PartDefinition / PartRevision | Platform Core + Geometry Pipeline | Definition vilag | Run outputban szereplo part meta |
| PartDemand | Platform Core | Demand vilag | PartDefinition mennyiseg mezok |
| SheetDefinition / SheetRevision | Platform Core + Geometry Pipeline | Definition vilag | Inventory tablaban tarolt shape dump |
| SheetInventoryUnit | Platform Core | Usage/Inventory vilag | SheetDefinition |
| RunSnapshot | Platform Core | Snapshot vilag | Elo Project allapot |
| RunResult | Engine Adapter | Result vilag | Viewer SVG |
| PlacementProjection | Viewer/Reporting | Projection vilag | Solver raw JSON |
| ManufacturingPackage | Manufacturing | Result vilag (manufacturing) | Export file |
| ExportJob artifacts | Postprocess | Artifact/Export vilag | Projection tabla |
| Remnant | Manufacturing | Inventory/Result hatarvilag | SheetDefinition |
| ReviewDecision | Decision Layer | Decision audit vilag | UI temporary selection state |

## 8. Mutable vs immutable szabalyok

Immutable:
- PartRevision, SheetRevision
- RunSnapshot es snapshot child objektumok
- RunResult core placement payload (utolag nem modositando)
- Artifact content hash szerint azonositott export output

Mutable:
- Project metadata
- TechnologySetup aktiv valasztas (uj verzioval)
- PartDemand mennyiseg/prioritas (run inditas elott)
- SheetInventoryUnit allapot (available/reserved/consumed)
- ReviewDecision statusz (pending/approved/rejected)

## 9. Definition vs usage vs demand vs snapshot vs result vs export matrix

| Vilag | Tipikus objektum | Irhatosag | Felelos modul | Fo cel |
| --- | --- | --- | --- | --- |
| Definition | PartDefinition, SheetDefinition, reviziok | Verziozott (append) | Platform Core + Geometry Pipeline | Torzs-azonossag |
| Usage | Project + technology kivalasztas | Mutable | Platform Core | Projekt konfiguracio |
| Demand | PartDemand, SheetInventoryUnit allokacio | Mutable (runig) | Platform Core | Futas igenyoldal |
| Snapshot | RunSnapshot | Immutable | Platform Core | Reprodukcio es audit |
| Result | RunResult, ManufacturingPackage | Immutable canonical payload | Engine Adapter / Manufacturing | Szamitas eredmenye |
| Projection | PlacementProjection, metrics | Rebuildelheto | Viewer/Reporting | UI/API query reteg |
| Export | DXF/SVG/ZIP/NC artifact | Immutable blob | Postprocess | Kulso atadas |

## 10. H0-E2 schema kovetkezmenyek

A kovetkezo core schema feladatban kotelezoen ervenyesitendo:
- Kulon tabla/aggregate a `part_definitions` es `project_part_requirements` vilagnak.
- Kulon tabla/aggregate a `sheet_definitions` es `sheet_inventory_units` vilagnak.
- `run_snapshot` es `run_result` explicit kulon entitas marad.
- Projection tablakat tilos domain truth tablakkent kezelni.
- Export artifact tarolas csak manifest + blob referencia modellben tortenjen.
- Remnant entitas sajat azonosito-val rendelkezzen, ne legyen sheet revision alias.

## 11. Anti-pattern lista

- Part Definition es Part Demand osszemosasa.
- Sheet Definition es Sheet Inventory Unit osszemosasa.
- Run Snapshot es Run Result osszemosasa.
- Projection truth-kent kezelese result helyett.
- Remnantot sima sheet definiciokent kezelni.
- Export artifactot domain truth-kent kezelni.

## 12. Dontesi szabaly konfliktus eseten

Ha domain entitas-tipus, aggregate ownership, vagy source-of-truth kerdesben ket dokumentum
ellentmond, ez a dokumentum az ervenyes domain-nezet.
A modulhatar-szintu tiltasokban a `h0_modulhatarok_es_boundary_szerzodes.md` az elsosegi forras.
