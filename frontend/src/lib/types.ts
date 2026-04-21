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
}

export interface ProjectFileListResponse {
  items: ProjectFile[];
  total: number;
}

export interface ProjectFileLatestPreflightSummary {
  preflight_run_id: string;
  run_seq?: number | null;
  run_status?: string | null;
  acceptance_outcome?: string | null;
  finished_at?: string | null;
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
