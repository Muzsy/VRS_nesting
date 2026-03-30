#!/usr/bin/env python3
"""Thin Tkinter GUI shell for the trial-run tool core."""

from __future__ import annotations

import argparse
import os
import queue
import subprocess
import sys
import threading
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.trial_run_tool_core import (
    TrialRunConfig,
    TrialRunResult,
    TrialRunToolError,
    VALID_ENGINE_BACKENDS,
    _resolve_env,
    run_trial,
)

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ImportError:
    tk = None  # type: ignore[assignment]
    filedialog = None  # type: ignore[assignment]
    messagebox = None  # type: ignore[assignment]
    ttk = None  # type: ignore[assignment]


@dataclass(frozen=True)
class GuiFormValues:
    dxf_dir: str
    api_base_url: str
    sheet_width: str
    sheet_height: str
    output_base_dir: str
    mode: str
    project_id: str
    project_name: str
    project_description: str
    default_qty: str
    auto_start_platform: bool
    technology_display_name: str
    technology_machine_code: str
    technology_material_code: str
    technology_thickness_mm: str
    technology_kerf_mm: str
    technology_spacing_mm: str
    technology_margin_mm: str
    technology_rotation_step_deg: str
    technology_allow_free_rotation: bool
    engine_backend: str


def collect_dxf_files(dxf_dir: Path) -> list[Path]:
    """Collect .dxf files from a directory."""

    target = dxf_dir.expanduser().resolve()
    if not target.is_dir():
        raise TrialRunToolError(f"DXF directory not found: {target}")

    files = sorted(path for path in target.iterdir() if path.is_file() and path.suffix.lower() == ".dxf")
    if not files:
        raise TrialRunToolError(f"no .dxf files found in: {target}")
    return files


def _parse_positive_int(raw: str, *, field: str) -> int:
    text = raw.strip()
    if not text:
        raise TrialRunToolError(f"{field} is required")
    try:
        value = int(text)
    except ValueError as exc:
        raise TrialRunToolError(f"{field} must be an integer: {raw}") from exc
    if value <= 0:
        raise TrialRunToolError(f"{field} must be > 0")
    return value


def _parse_positive_float(raw: str, *, field: str) -> float:
    text = raw.strip()
    if not text:
        raise TrialRunToolError(f"{field} is required")
    try:
        value = float(text)
    except ValueError as exc:
        raise TrialRunToolError(f"{field} must be a number: {raw}") from exc
    if value <= 0:
        raise TrialRunToolError(f"{field} must be > 0")
    return value


def _parse_non_negative_float(raw: str, *, field: str) -> float:
    text = raw.strip()
    if not text:
        raise TrialRunToolError(f"{field} is required")
    try:
        value = float(text)
    except ValueError as exc:
        raise TrialRunToolError(f"{field} must be a number: {raw}") from exc
    if value < 0:
        raise TrialRunToolError(f"{field} must be >= 0")
    return value


def _parse_rotation_step(raw: str) -> int:
    text = raw.strip()
    if not text:
        raise TrialRunToolError("technology_rotation_step_deg is required")
    try:
        value = int(text)
    except ValueError as exc:
        raise TrialRunToolError(f"technology_rotation_step_deg must be an integer: {raw}") from exc
    if value <= 0 or value > 360:
        raise TrialRunToolError("technology_rotation_step_deg must be in range 1..360")
    return value


def build_config_from_form(values: GuiFormValues, qty_inputs: Mapping[str, str]) -> tuple[TrialRunConfig, list[Path]]:
    """Validate GUI form values and build TrialRunConfig for core runner."""

    dxf_dir = Path(values.dxf_dir.strip()).expanduser()
    dxf_files = collect_dxf_files(dxf_dir)

    mode = values.mode.strip().lower()
    if mode not in {"new", "existing"}:
        raise TrialRunToolError("mode must be one of: new, existing")

    default_qty = _parse_positive_int(values.default_qty, field="default_qty")
    per_file_qty: dict[str, int] = {}
    for path in dxf_files:
        raw_qty = str(qty_inputs.get(path.name, "")).strip()
        qty = default_qty if not raw_qty else _parse_positive_int(raw_qty, field=f"qty for {path.name}")
        if qty != default_qty:
            per_file_qty[path.name] = qty

    existing_project_id = values.project_id.strip() if mode == "existing" else None
    if mode == "existing" and not existing_project_id:
        raise TrialRunToolError("project_id is required in existing mode")

    api_base_url = values.api_base_url.strip() or "http://127.0.0.1:8000/v1"
    output_base_dir = Path(values.output_base_dir.strip() or "tmp/runs")
    if mode == "new" and (not _resolve_env("SUPABASE_URL") or not _resolve_env("SUPABASE_ANON_KEY")):
        raise TrialRunToolError(
            "new project mode requires SUPABASE_URL and SUPABASE_ANON_KEY from .env.local/.env."
        )

    tech_display_name = values.technology_display_name.strip() or "Trial Default Setup"
    tech_machine_code = values.technology_machine_code.strip() or "TRIAL-MACHINE"
    tech_material_code = values.technology_material_code.strip() or "TRIAL-MATERIAL"
    tech_thickness_mm = _parse_positive_float(
        values.technology_thickness_mm.strip() or "3.0",
        field="technology_thickness_mm",
    )
    tech_kerf_mm = _parse_non_negative_float(
        values.technology_kerf_mm.strip() or "0.2",
        field="technology_kerf_mm",
    )
    tech_spacing_mm = _parse_non_negative_float(
        values.technology_spacing_mm.strip() or "0.0",
        field="technology_spacing_mm",
    )
    tech_margin_mm = _parse_non_negative_float(
        values.technology_margin_mm.strip() or "0.0",
        field="technology_margin_mm",
    )
    tech_rotation_step_deg = _parse_rotation_step(values.technology_rotation_step_deg.strip() or "90")

    engine_backend = values.engine_backend.strip() or "auto"
    if engine_backend not in VALID_ENGINE_BACKENDS:
        raise TrialRunToolError(f"engine_backend must be one of {VALID_ENGINE_BACKENDS}, got: {engine_backend}")

    config = TrialRunConfig(
        dxf_dir=dxf_dir,
        api_base_url=api_base_url,
        sheet_width=_parse_positive_float(values.sheet_width, field="sheet_width"),
        sheet_height=_parse_positive_float(values.sheet_height, field="sheet_height"),
        existing_project_id=existing_project_id,
        project_name=(values.project_name.strip() or None) if mode == "new" else None,
        project_description=(values.project_description.strip() or None) if mode == "new" else None,
        default_qty=default_qty,
        per_file_qty=per_file_qty,
        output_base_dir=output_base_dir,
        auto_start_platform=bool(values.auto_start_platform),
        technology_display_name=tech_display_name,
        technology_machine_code=tech_machine_code,
        technology_material_code=tech_material_code,
        technology_thickness_mm=tech_thickness_mm,
        technology_kerf_mm=tech_kerf_mm,
        technology_spacing_mm=tech_spacing_mm,
        technology_margin_mm=tech_margin_mm,
        technology_rotation_step_deg=tech_rotation_step_deg,
        technology_allow_free_rotation=bool(values.technology_allow_free_rotation),
        engine_backend=engine_backend,
    )
    return config, dxf_files


def _open_path(path: Path) -> None:
    if sys.platform.startswith("win"):
        os.startfile(str(path))
        return
    if sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
        return
    subprocess.run(["xdg-open", str(path)], check=False)


class TrialRunToolGuiApp:
    """Tkinter shell that delegates actual run execution to trial_run_tool_core."""

    def __init__(self, root: Any, args: argparse.Namespace) -> None:
        self._root = root
        self._event_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._running = False
        self._qty_vars: dict[str, Any] = {}

        self._dxf_dir_var = tk.StringVar(value=args.dxf_dir)
        self._api_base_var = tk.StringVar(value=args.api_base_url)
        self._sheet_width_var = tk.StringVar(value=str(args.sheet_width))
        self._sheet_height_var = tk.StringVar(value=str(args.sheet_height))
        self._output_base_dir_var = tk.StringVar(value=args.output_base_dir)
        self._mode_var = tk.StringVar(value=args.project_mode)
        self._project_id_var = tk.StringVar(value="")
        self._project_name_var = tk.StringVar(value="")
        self._project_description_var = tk.StringVar(value="")
        self._default_qty_var = tk.StringVar(value="1")
        self._auto_start_var = tk.BooleanVar(value=bool(args.auto_start_platform))
        self._technology_display_name_var = tk.StringVar(value=args.technology_display_name)
        self._technology_machine_code_var = tk.StringVar(value=args.technology_machine_code)
        self._technology_material_code_var = tk.StringVar(value=args.technology_material_code)
        self._technology_thickness_mm_var = tk.StringVar(value=str(args.technology_thickness_mm))
        self._technology_kerf_mm_var = tk.StringVar(value=str(args.technology_kerf_mm))
        self._technology_spacing_mm_var = tk.StringVar(value=str(args.technology_spacing_mm))
        self._technology_margin_mm_var = tk.StringVar(value=str(args.technology_margin_mm))
        self._technology_rotation_step_deg_var = tk.StringVar(value=str(args.technology_rotation_step_deg))
        self._technology_allow_free_rotation_var = tk.BooleanVar(value=bool(args.technology_allow_free_rotation))
        self._engine_backend_var = tk.StringVar(value=args.engine_backend)
        self._status_var = tk.StringVar(value="Idle")
        self._last_run_dir_var = tk.StringVar(value="")

        self._project_id_entry: Any | None = None
        self._project_name_entry: Any | None = None
        self._project_description_entry: Any | None = None
        self._technology_display_name_entry: Any | None = None
        self._technology_machine_code_entry: Any | None = None
        self._technology_material_code_entry: Any | None = None
        self._technology_thickness_mm_entry: Any | None = None
        self._technology_kerf_mm_entry: Any | None = None
        self._technology_spacing_mm_entry: Any | None = None
        self._technology_margin_mm_entry: Any | None = None
        self._technology_rotation_step_deg_entry: Any | None = None
        self._technology_allow_free_rotation_check: Any | None = None
        self._start_btn: Any | None = None
        self._log_text: Any | None = None
        self._qty_frame: Any | None = None

        self._build_ui()
        self._set_mode_widgets()
        self._refresh_dxf_rows()
        self._root.after(250, self._drain_events)

    def _build_ui(self) -> None:
        self._root.title("Trial Run Tool - Tkinter shell")
        self._root.geometry("1100x780")
        self._root.minsize(960, 680)

        self._root.columnconfigure(0, weight=1)
        self._root.rowconfigure(0, weight=1)

        main = ttk.Frame(self._root, padding=12)
        main.grid(row=0, column=0, sticky="nsew")
        main.columnconfigure(1, weight=1)
        main.rowconfigure(20, weight=1)

        row = 0
        ttk.Label(main, text="DXF directory").grid(row=row, column=0, sticky="w", pady=2)
        ttk.Entry(main, textvariable=self._dxf_dir_var).grid(row=row, column=1, sticky="ew", padx=(8, 8), pady=2)
        ttk.Button(main, text="Browse", command=self._browse_dxf_dir).grid(row=row, column=2, sticky="ew", pady=2)
        ttk.Button(main, text="Refresh DXF list", command=self._refresh_dxf_rows).grid(row=row, column=3, sticky="ew", pady=2)

        row += 1
        ttk.Label(main, text="API base URL").grid(row=row, column=0, sticky="w", pady=2)
        ttk.Entry(main, textvariable=self._api_base_var).grid(row=row, column=1, columnspan=3, sticky="ew", padx=(8, 0), pady=2)

        row += 1
        ttk.Label(main, text="Sheet width (mm)").grid(row=row, column=0, sticky="w", pady=2)
        ttk.Entry(main, textvariable=self._sheet_width_var, width=16).grid(row=row, column=1, sticky="w", padx=(8, 8), pady=2)
        ttk.Label(main, text="Sheet height (mm)").grid(row=row, column=2, sticky="w", pady=2)
        ttk.Entry(main, textvariable=self._sheet_height_var, width=16).grid(row=row, column=3, sticky="w", pady=2)

        row += 1
        ttk.Label(main, text="Output base dir").grid(row=row, column=0, sticky="w", pady=2)
        ttk.Entry(main, textvariable=self._output_base_dir_var).grid(row=row, column=1, sticky="ew", padx=(8, 8), pady=2)
        ttk.Button(main, text="Browse", command=self._browse_output_dir).grid(row=row, column=2, sticky="ew", pady=2)

        row += 1
        ttk.Label(main, text="Project mode").grid(row=row, column=0, sticky="w", pady=2)
        mode_frame = ttk.Frame(main)
        mode_frame.grid(row=row, column=1, sticky="w", padx=(8, 8), pady=2)
        ttk.Radiobutton(mode_frame, text="New project", value="new", variable=self._mode_var, command=self._set_mode_widgets).grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )
        ttk.Radiobutton(mode_frame, text="Existing project", value="existing", variable=self._mode_var, command=self._set_mode_widgets).grid(
            row=0, column=1, sticky="w"
        )
        ttk.Label(main, text="Project ID").grid(row=row, column=2, sticky="w", pady=2)
        self._project_id_entry = ttk.Entry(main, textvariable=self._project_id_var)
        self._project_id_entry.grid(row=row, column=3, sticky="ew", pady=2)

        row += 1
        ttk.Label(main, text="Project name (new mode)").grid(row=row, column=0, sticky="w", pady=2)
        self._project_name_entry = ttk.Entry(main, textvariable=self._project_name_var)
        self._project_name_entry.grid(row=row, column=1, sticky="ew", padx=(8, 8), pady=2)
        ttk.Label(main, text="Default qty").grid(row=row, column=2, sticky="w", pady=2)
        ttk.Entry(main, textvariable=self._default_qty_var, width=10).grid(row=row, column=3, sticky="w", pady=2)

        row += 1
        ttk.Label(main, text="Project description (new mode)").grid(row=row, column=0, sticky="w", pady=2)
        self._project_description_entry = ttk.Entry(main, textvariable=self._project_description_var)
        self._project_description_entry.grid(row=row, column=1, columnspan=2, sticky="ew", padx=(8, 8), pady=2)
        ttk.Checkbutton(main, text="Auto-heal platform (start/restart components)", variable=self._auto_start_var).grid(
            row=row, column=3, sticky="w", pady=2
        )

        row += 1
        ttk.Label(main, text="Tech setup display name (new mode)").grid(row=row, column=0, sticky="w", pady=2)
        self._technology_display_name_entry = ttk.Entry(main, textvariable=self._technology_display_name_var)
        self._technology_display_name_entry.grid(row=row, column=1, sticky="ew", padx=(8, 8), pady=2)
        ttk.Label(main, text="Machine code").grid(row=row, column=2, sticky="w", pady=2)
        self._technology_machine_code_entry = ttk.Entry(main, textvariable=self._technology_machine_code_var)
        self._technology_machine_code_entry.grid(row=row, column=3, sticky="ew", pady=2)

        row += 1
        ttk.Label(main, text="Material code").grid(row=row, column=0, sticky="w", pady=2)
        self._technology_material_code_entry = ttk.Entry(main, textvariable=self._technology_material_code_var)
        self._technology_material_code_entry.grid(row=row, column=1, sticky="ew", padx=(8, 8), pady=2)
        ttk.Label(main, text="Thickness mm").grid(row=row, column=2, sticky="w", pady=2)
        self._technology_thickness_mm_entry = ttk.Entry(main, textvariable=self._technology_thickness_mm_var)
        self._technology_thickness_mm_entry.grid(row=row, column=3, sticky="ew", pady=2)

        row += 1
        ttk.Label(main, text="Kerf mm").grid(row=row, column=0, sticky="w", pady=2)
        self._technology_kerf_mm_entry = ttk.Entry(main, textvariable=self._technology_kerf_mm_var)
        self._technology_kerf_mm_entry.grid(row=row, column=1, sticky="ew", padx=(8, 8), pady=2)
        ttk.Label(main, text="Spacing mm").grid(row=row, column=2, sticky="w", pady=2)
        self._technology_spacing_mm_entry = ttk.Entry(main, textvariable=self._technology_spacing_mm_var)
        self._technology_spacing_mm_entry.grid(row=row, column=3, sticky="ew", pady=2)

        row += 1
        ttk.Label(main, text="Margin mm").grid(row=row, column=0, sticky="w", pady=2)
        self._technology_margin_mm_entry = ttk.Entry(main, textvariable=self._technology_margin_mm_var)
        self._technology_margin_mm_entry.grid(row=row, column=1, sticky="ew", padx=(8, 8), pady=2)
        ttk.Label(main, text="Rotation step deg").grid(row=row, column=2, sticky="w", pady=2)
        self._technology_rotation_step_deg_entry = ttk.Entry(main, textvariable=self._technology_rotation_step_deg_var)
        self._technology_rotation_step_deg_entry.grid(row=row, column=3, sticky="ew", pady=2)

        row += 1
        self._technology_allow_free_rotation_check = ttk.Checkbutton(
            main,
            text="Allow free rotation (new mode)",
            variable=self._technology_allow_free_rotation_var,
        )
        self._technology_allow_free_rotation_check.grid(row=row, column=0, columnspan=2, sticky="w", pady=2)
        ttk.Label(main, text="Engine backend").grid(row=row, column=2, sticky="w", pady=2)
        self._engine_backend_combo = ttk.Combobox(
            main,
            textvariable=self._engine_backend_var,
            values=list(VALID_ENGINE_BACKENDS),
            state="readonly",
            width=20,
        )
        self._engine_backend_combo.grid(row=row, column=3, sticky="w", pady=2)

        row += 1
        qty_group = ttk.LabelFrame(main, text="Detected DXF files and per-file qty")
        qty_group.grid(row=row, column=0, columnspan=4, sticky="nsew", pady=(10, 8))
        qty_group.columnconfigure(0, weight=1)
        self._qty_frame = ttk.Frame(qty_group)
        self._qty_frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self._qty_frame.columnconfigure(0, weight=1)

        row += 1
        actions = ttk.Frame(main)
        actions.grid(row=row, column=0, columnspan=4, sticky="ew", pady=(2, 8))
        actions.columnconfigure(2, weight=1)
        self._start_btn = ttk.Button(actions, text="Start trial run", command=self._start_run)
        self._start_btn.grid(row=0, column=0, sticky="w")
        ttk.Label(actions, text="Status:").grid(row=0, column=1, sticky="w", padx=(12, 4))
        ttk.Label(actions, textvariable=self._status_var).grid(row=0, column=2, sticky="w")

        row += 1
        run_dir_frame = ttk.Frame(main)
        run_dir_frame.grid(row=row, column=0, columnspan=4, sticky="ew", pady=(0, 8))
        run_dir_frame.columnconfigure(1, weight=1)
        ttk.Label(run_dir_frame, text="Last run dir").grid(row=0, column=0, sticky="w")
        ttk.Entry(run_dir_frame, textvariable=self._last_run_dir_var, state="readonly").grid(
            row=0, column=1, sticky="ew", padx=(8, 8)
        )
        ttk.Button(run_dir_frame, text="Open run dir", command=self._open_last_run_dir).grid(row=0, column=2, sticky="ew")

        row += 1
        ttk.Label(main, text="Log / status").grid(row=row, column=0, sticky="w")

        row += 1
        main.rowconfigure(row, weight=1)
        log_frame = ttk.Frame(main)
        log_frame.grid(row=row, column=0, columnspan=4, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self._log_text = tk.Text(log_frame, height=16, wrap="word")
        self._log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self._log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._log_text.configure(yscrollcommand=scrollbar.set, state="disabled")

    def _set_mode_widgets(self) -> None:
        mode = self._mode_var.get().strip().lower()
        is_existing = mode == "existing"
        tech_state = "disabled" if is_existing else "normal"
        if self._project_id_entry is not None:
            self._project_id_entry.configure(state="normal" if is_existing else "disabled")
        if self._project_name_entry is not None:
            self._project_name_entry.configure(state="disabled" if is_existing else "normal")
        if self._project_description_entry is not None:
            self._project_description_entry.configure(state="disabled" if is_existing else "normal")
        for entry in (
            self._technology_display_name_entry,
            self._technology_machine_code_entry,
            self._technology_material_code_entry,
            self._technology_thickness_mm_entry,
            self._technology_kerf_mm_entry,
            self._technology_spacing_mm_entry,
            self._technology_margin_mm_entry,
            self._technology_rotation_step_deg_entry,
        ):
            if entry is not None:
                entry.configure(state=tech_state)
        if self._technology_allow_free_rotation_check is not None:
            self._technology_allow_free_rotation_check.configure(state=tech_state)

    def _append_log(self, message: str) -> None:
        if self._log_text is None:
            return
        stamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{stamp}] {message}\n"
        self._log_text.configure(state="normal")
        self._log_text.insert("end", line)
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    def _browse_dxf_dir(self) -> None:
        if filedialog is None:
            return
        selected = filedialog.askdirectory(title="Select DXF directory")
        if selected:
            self._dxf_dir_var.set(selected)
            self._refresh_dxf_rows()

    def _browse_output_dir(self) -> None:
        if filedialog is None:
            return
        selected = filedialog.askdirectory(title="Select output base directory")
        if selected:
            self._output_base_dir_var.set(selected)

    def _refresh_dxf_rows(self) -> None:
        if self._qty_frame is None:
            return

        for child in self._qty_frame.winfo_children():
            child.destroy()

        existing_values = {name: var.get() for name, var in self._qty_vars.items()}
        self._qty_vars.clear()

        try:
            files = collect_dxf_files(Path(self._dxf_dir_var.get().strip()))
        except (TrialRunToolError, ValueError, OSError) as exc:
            ttk.Label(self._qty_frame, text=str(exc)).grid(row=0, column=0, sticky="w")
            self._append_log(f"DXF scan warning: {exc}")
            return

        default_qty = self._default_qty_var.get().strip() or "1"
        ttk.Label(self._qty_frame, text="DXF file").grid(row=0, column=0, sticky="w")
        ttk.Label(self._qty_frame, text="Qty").grid(row=0, column=1, sticky="w", padx=(8, 0))

        for idx, path in enumerate(files, start=1):
            ttk.Label(self._qty_frame, text=path.name).grid(row=idx, column=0, sticky="w", pady=1)
            initial_qty = existing_values.get(path.name, default_qty)
            qty_var = tk.StringVar(value=initial_qty)
            self._qty_vars[path.name] = qty_var
            ttk.Entry(self._qty_frame, textvariable=qty_var, width=8).grid(row=idx, column=1, sticky="w", padx=(8, 0), pady=1)

        self._append_log(f"Detected {len(files)} DXF files.")

    def _collect_form(self) -> GuiFormValues:
        return GuiFormValues(
            dxf_dir=self._dxf_dir_var.get(),
            api_base_url=self._api_base_var.get(),
            sheet_width=self._sheet_width_var.get(),
            sheet_height=self._sheet_height_var.get(),
            output_base_dir=self._output_base_dir_var.get(),
            mode=self._mode_var.get(),
            project_id=self._project_id_var.get(),
            project_name=self._project_name_var.get(),
            project_description=self._project_description_var.get(),
            default_qty=self._default_qty_var.get(),
            auto_start_platform=bool(self._auto_start_var.get()),
            technology_display_name=self._technology_display_name_var.get(),
            technology_machine_code=self._technology_machine_code_var.get(),
            technology_material_code=self._technology_material_code_var.get(),
            technology_thickness_mm=self._technology_thickness_mm_var.get(),
            technology_kerf_mm=self._technology_kerf_mm_var.get(),
            technology_spacing_mm=self._technology_spacing_mm_var.get(),
            technology_margin_mm=self._technology_margin_mm_var.get(),
            technology_rotation_step_deg=self._technology_rotation_step_deg_var.get(),
            technology_allow_free_rotation=bool(self._technology_allow_free_rotation_var.get()),
            engine_backend=self._engine_backend_var.get(),
        )

    def _set_running(self, running: bool) -> None:
        self._running = running
        if self._start_btn is not None:
            self._start_btn.configure(state="disabled" if running else "normal")

    def _start_run(self) -> None:
        if self._running:
            return

        form = self._collect_form()
        qty_inputs = {name: var.get() for name, var in self._qty_vars.items()}
        try:
            config, dxf_files = build_config_from_form(form, qty_inputs)
        except TrialRunToolError as exc:
            self._status_var.set("Validation failed")
            self._append_log(f"Validation failed: {exc}")
            if messagebox is not None:
                messagebox.showerror("Invalid input", str(exc))
            return

        self._set_running(True)
        self._status_var.set("Running")
        self._append_log(f"Starting run for {len(dxf_files)} DXF files.")
        worker = threading.Thread(target=self._run_worker, args=(config,), daemon=True)
        worker.start()

    def _run_worker(self, config: TrialRunConfig) -> None:
        self._event_queue.put(("log", "Background runner started."))
        try:
            result = run_trial(config)
            self._event_queue.put(("result", result))
        except Exception as exc:  # noqa: BLE001
            self._event_queue.put(("error", f"{exc}\n{traceback.format_exc()}"))

    def _drain_events(self) -> None:
        while True:
            try:
                kind, payload = self._event_queue.get_nowait()
            except queue.Empty:
                break

            if kind == "log":
                self._append_log(str(payload))
                continue

            if kind == "error":
                self._set_running(False)
                self._status_var.set("Failed")
                self._append_log(f"Run failed with exception: {payload}")
                if messagebox is not None:
                    messagebox.showerror("Run failed", str(payload))
                continue

            if kind == "result":
                self._handle_result(payload)
                continue

        self._root.after(250, self._drain_events)

    def _handle_result(self, result: TrialRunResult) -> None:
        self._set_running(False)
        self._last_run_dir_var.set(str(result.run_dir))
        if result.success:
            self._status_var.set("Success")
            self._append_log(f"Run finished successfully. run_dir={result.run_dir}")
            self._append_log(f"Summary: {result.summary_path}")
            return

        self._status_var.set("Failed")
        error_text = result.error_message or "unknown error"
        self._append_log(f"Run failed. run_dir={result.run_dir} error={error_text}")
        if messagebox is not None:
            messagebox.showerror("Run failed", error_text)

    def _open_last_run_dir(self) -> None:
        raw = self._last_run_dir_var.get().strip()
        if not raw:
            self._append_log("No run directory available yet.")
            return
        run_dir = Path(raw)
        if not run_dir.exists():
            self._append_log(f"Run directory does not exist: {run_dir}")
            return
        try:
            _open_path(run_dir)
            self._append_log(f"Opened run directory: {run_dir}")
        except Exception as exc:  # noqa: BLE001
            self._append_log(f"Could not open run directory: {exc}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Thin Tkinter shell for scripts.trial_run_tool_core")
    parser.add_argument("--dxf-dir", default="", help="Optional default DXF directory")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8000/v1", help="Default API base URL")
    parser.add_argument("--sheet-width", type=float, default=3000.0, help="Default sheet width")
    parser.add_argument("--sheet-height", type=float, default=1500.0, help="Default sheet height")
    parser.add_argument("--output-base-dir", default="tmp/runs", help="Default run output directory")
    parser.add_argument("--project-mode", choices=["new", "existing"], default="new", help="Default project mode")
    parser.add_argument(
        "--auto-start-platform",
        dest="auto_start_platform",
        action="store_true",
        default=True,
        help="Auto-heal platform (start/restart components when needed)",
    )
    parser.add_argument(
        "--no-auto-start-platform",
        dest="auto_start_platform",
        action="store_false",
        help="Disable automatic platform start/restart",
    )
    parser.add_argument("--technology-display-name", default="Trial Default Setup", help="Default setup display_name")
    parser.add_argument("--technology-machine-code", default="TRIAL-MACHINE", help="Default setup machine_code")
    parser.add_argument("--technology-material-code", default="TRIAL-MATERIAL", help="Default setup material_code")
    parser.add_argument("--technology-thickness-mm", type=float, default=3.0, help="Default setup thickness_mm")
    parser.add_argument("--technology-kerf-mm", type=float, default=0.2, help="Default setup kerf_mm")
    parser.add_argument("--technology-spacing-mm", type=float, default=0.0, help="Default setup spacing_mm")
    parser.add_argument("--technology-margin-mm", type=float, default=0.0, help="Default setup margin_mm")
    parser.add_argument("--technology-rotation-step-deg", type=int, default=90, help="Default setup rotation_step_deg")
    parser.add_argument(
        "--technology-allow-free-rotation",
        action="store_true",
        help="Default setup allow_free_rotation",
    )
    parser.add_argument(
        "--engine-backend",
        choices=list(VALID_ENGINE_BACKENDS),
        default="auto",
        help="Engine backend selector (auto | sparrow_v1 | nesting_engine_v2)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    if tk is None or ttk is None:
        raise TrialRunToolError("tkinter is not available in this Python runtime.")

    parser = _build_parser()
    args = parser.parse_args(argv)

    root = tk.Tk()
    TrialRunToolGuiApp(root, args)
    root.mainloop()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except TrialRunToolError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
