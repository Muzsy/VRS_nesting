declare global {
  interface ImportMetaEnv {
    readonly VITE_API_BASE_URL?: string;
    readonly VITE_DXF_PREFLIGHT_ENABLED?: string;
  }

  interface ImportMeta {
    readonly env: ImportMetaEnv;
  }
}

export type RunStatus = "queued" | "running" | "done" | "failed" | "cancelled";

export interface Project {
  id: string;
  owner_id: string;
  name: string;
  description?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  archived_at?: string | null;
}

export interface ProjectListResponse {
  items: Project[];
  total: number;
  page: number;
  page_size: number;
}

export interface ProjectFile {
  id: string;
  project_id: string;
  uploaded_by: string;
  file_type: string;
  original_filename: string;
  storage_key: string;
  size_bytes?: number | null;
  validation_status?: string | null;
  validation_error?: string | null;
  uploaded_at?: string | null;
  latest_preflight_summary?: ProjectFileLatestPreflightSummary | null;
  latest_preflight_diagnostics?: ProjectFileLatestPreflightDiagnostics | null;
  latest_part_creation_projection?: ProjectFileLatestPartCreationProjection | null;
}

export interface ProjectFileListResponse {
  items: ProjectFile[];
  total: number;
}

export interface ProjectFileReplaceUploadResponse {
  upload_url: string;
  file_id: string;
  storage_bucket: string;
  storage_path: string;
  expires_at: string;
  replaces_file_id: string;
}

export interface ProjectFileLatestPreflightSummary {
  preflight_run_id: string;
  run_seq?: number | null;
  run_status?: string | null;
  acceptance_outcome?: string | null;
  finished_at?: string | null;
  blocking_issue_count: number;
  review_required_issue_count: number;
  warning_issue_count: number;
  total_issue_count: number;
  applied_gap_repair_count: number;
  applied_duplicate_dedupe_count: number;
  total_repair_count: number;
  recommended_action?: string | null;
}

export interface ProjectFileLatestPreflightDiagnostics {
  source_inventory_summary: {
    found_layers: string[];
    found_colors: number[];
    found_linetypes: string[];
    entity_count: number;
    contour_count: number;
    open_path_layer_count: number;
    open_path_total_count: number;
    duplicate_candidate_group_count: number;
    duplicate_candidate_member_count: number;
  };
  role_mapping_summary: {
    resolved_role_inventory: Record<string, number>;
    layer_role_assignments: Array<Record<string, unknown>>;
    review_required_count: number;
    blocking_conflict_count: number;
  };
  issue_summary: {
    counts_by_severity: {
      blocking: number;
      review_required: number;
      warning: number;
      info: number;
    };
    normalized_issues: Array<{
      severity: string;
      family: string;
      code: string;
      message: string;
      source: string;
    }>;
  };
  repair_summary: {
    counts: {
      applied_gap_repair_count: number;
      applied_duplicate_dedupe_count: number;
      skipped_source_entity_count: number;
      remaining_open_path_count: number;
      remaining_duplicate_count: number;
      remaining_review_required_signal_count: number;
    };
    applied_gap_repairs: Array<Record<string, unknown>>;
    applied_duplicate_dedupes: Array<Record<string, unknown>>;
    skipped_source_entities: Array<Record<string, unknown>>;
    remaining_review_required_signals: Array<Record<string, unknown>>;
  };
  acceptance_summary: {
    acceptance_outcome: string;
    precedence_rule_applied: string;
    importer_probe: Record<string, unknown>;
    validator_probe: Record<string, unknown>;
    blocking_reason_count: number;
    review_required_reason_count: number;
  };
  artifact_references: Array<{
    artifact_kind: string;
    download_label: string;
    path: string;
    exists: boolean;
  }>;
}

export interface ProjectFileLatestPartCreationProjection {
  acceptance_outcome?: string | null;
  geometry_revision_id?: string | null;
  geometry_revision_status?: string | null;
  has_nesting_derivative: boolean;
  part_creation_ready: boolean;
  readiness_reason: string;
  suggested_code: string;
  suggested_name: string;
  source_label: string;
  existing_part_definition_id?: string | null;
  existing_part_revision_id?: string | null;
  existing_part_code?: string | null;
}

export interface ProjectPartCreateRequest {
  code: string;
  name: string;
  geometry_revision_id: string;
  source_label?: string;
}

export interface ProjectPartCreateResponse {
  part_definition_id: string;
  part_revision_id: string;
  revision_no: number;
  lifecycle: string;
  code: string;
  name: string;
  current_revision_id?: string | null;
  source_geometry_revision_id: string;
  selected_nesting_derivative_id: string;
  was_existing_definition: boolean;
}

export interface PreflightRulesProfileSnapshot {
  strict_mode: boolean;
  auto_repair_enabled: boolean;
  interactive_review_on_ambiguity: boolean;
  max_gap_close_mm: number;
  duplicate_contour_merge_tolerance_mm: number;
  cut_color_map: number[];
  marking_color_map: number[];
}

export interface PreflightSettingsDraft {
  strict_mode: boolean;
  auto_repair_enabled: boolean;
  interactive_review_on_ambiguity: boolean;
  max_gap_close_mm: number;
  duplicate_contour_merge_tolerance_mm: number;
  cut_color_map_text: string;
  marking_color_map_text: string;
}

export interface RunMetrics {
  placements_count: number;
  unplaced_count: number;
  sheet_count: number;
}

export interface Run {
  id: string;
  project_id: string;
  run_config_id?: string | null;
  triggered_by: string;
  status: RunStatus;
  queued_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  duration_sec?: number | null;
  solver_exit_code?: number | null;
  error_message?: string | null;
  metrics?: RunMetrics | null;
}

export interface RunListResponse {
  items: Run[];
  total: number;
  page: number;
  page_size: number;
}

export interface RunLogLine {
  line_no: number;
  text: string;
}

export interface RunLogResponse {
  lines: RunLogLine[];
  total_lines: number;
  next_offset: number;
  run_status: RunStatus;
  stop_polling: boolean;
}

export interface RunArtifact {
  id: string;
  run_id: string;
  artifact_type: string;
  filename: string;
  storage_key: string;
  size_bytes?: number | null;
  sheet_index?: number | null;
  created_at?: string | null;
}

export interface RunArtifactListResponse {
  items: RunArtifact[];
  total: number;
}

export interface ArtifactUrlResponse {
  artifact_id: string;
  filename: string;
  download_url: string;
  expires_at: string;
}

export interface ViewerSheet {
  sheet_index: number;
  dxf_artifact_id?: string | null;
  svg_artifact_id?: string | null;
  dxf_filename?: string | null;
  svg_filename?: string | null;
  dxf_download_path?: string | null;
  svg_download_path?: string | null;
  dxf_url?: string | null;
  dxf_url_expires_at?: string | null;
  svg_url?: string | null;
  svg_url_expires_at?: string | null;
  width_mm?: number | null;
  height_mm?: number | null;
  utilization_pct?: number | null;
  placements_count: number;
}

export interface ViewerPlacement {
  instance_id: string;
  part_id: string;
  sheet_index: number;
  x: number;
  y: number;
  rotation_deg: number;
  width_mm: number;
  height_mm: number;
}

export interface ViewerUnplaced {
  instance_id: string;
  part_id: string;
  reason?: string | null;
}

export interface ViewerDataResponse {
  run_id: string;
  status: RunStatus;
  sheet_count: number;
  sheets: ViewerSheet[];
  placements: ViewerPlacement[];
  unplaced: ViewerUnplaced[];
}

export interface BundleResponse {
  artifact_id: string;
  filename: string;
  bundle_url: string;
  expires_at: string;
}
