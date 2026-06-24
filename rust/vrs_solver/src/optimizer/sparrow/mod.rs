//! Native Sparrow module boundary for the production `sparrow_cde` path.
//!
//! Production flow is kept explicit at this boundary:
//! `SparrowProblem` -> `SparrowOptimizer::solve` -> `SparrowSolveResult` ->
//! `SparrowSolution::to_solver_projection`.

pub(crate) use std::cmp::Ordering;
pub(crate) use std::collections::HashMap;
pub(crate) use std::rc::Rc;
pub(crate) use std::time::Instant;

pub(crate) use crate::geometry::Point;
pub(crate) use crate::io::{CollisionBackendKind, Placement, Unplaced};
pub(crate) use crate::item::{
    can_fit_any_stock_with_policy, dims_for_rotation, expand_instances_with_policy,
    placement_anchor_from_rect_min, rotated_bbox_min_offset, Instance, Part,
};
pub(crate) use crate::rotation_policy::{RotationPolicyKind, RotationResolveContext};
pub(crate) use crate::sheet::SheetShape;

pub(crate) use super::cde_adapter::{
    convex_hull_area_and_diameter, prepare_base_shape_native, prepare_shape_from_sheet,
    prepare_shape_native, prepare_spacing_base_shape_native, transform_base_to_candidate,
    translate_prepared, CandidatePole, CdeAdapter, CdeBaseShape, CdeCandidateSession,
    CdePreparedShape, CdeQueryResult, SpecializedCollectionCtx, SpecializedHazardSink,
};

pub mod band_insert_slot_edge;
pub mod bpp_reduction;
pub mod contour_features;
pub mod critical_simultaneous;
pub mod density;
pub mod diagnostics;
pub mod eval;
pub mod explore;
pub mod feature_candidate_generator;
pub mod fixed_sheet;
pub mod interlock_pair;
pub mod lbf;
pub mod model;
pub mod multisheet;
pub mod one_part_edge;
pub mod optimizer;
pub mod orientation_catalog;
pub mod part_analysis;
pub mod profile;
pub mod quantify;
pub mod sample;
pub mod separator;
pub mod shape_profile;
pub mod sheet_edge_placement_catalog;
pub mod sheet_feasibility;
pub mod sheet_feasibility_bpp;
pub mod sheet_skeleton;
mod tests;
pub mod worker;

pub use diagnostics::{SparrowConfig, SparrowDiagnostics};
pub use model::{
    SPInstance, SparrowContainer, SparrowLayout, SparrowPlacement, SparrowProblem,
    SparrowRotationDomain, SparrowSolution, SparrowSolveResult,
};
pub use optimizer::SparrowOptimizer;
pub(crate) use shape_profile::{CriticalityTier, PartShapeProfile};

pub(crate) use band_insert_slot_edge::*;
pub(crate) use contour_features::*;
pub(crate) use critical_simultaneous::*;
pub(crate) use diagnostics::*;
pub(crate) use eval::lbf_evaluator::*;
pub(crate) use eval::sample_eval::*;
pub(crate) use eval::sep_evaluator::*;
pub(crate) use eval::specialized_cde_pipeline::*;
pub(crate) use feature_candidate_generator::*;
pub(crate) use fixed_sheet::*;
pub(crate) use interlock_pair::*;
pub(crate) use lbf::*;
pub(crate) use orientation_catalog::*;
pub(crate) use part_analysis::*;
pub(crate) use profile::{ProfileTimer, SearchProfiler};
pub(crate) use quantify::overlap_proxy::*;
pub(crate) use quantify::pair_matrix::*;
pub(crate) use quantify::tracker::*;
pub(crate) use sample::best_samples::*;
pub(crate) use sample::coord_descent::*;
pub(crate) use sample::search::*;
pub(crate) use sample::uniform_sampler::*;
pub(crate) use sheet_edge_placement_catalog::*;
pub(crate) use sheet_feasibility::*;
pub(crate) use sheet_feasibility_bpp::*;
pub(crate) use worker::*;
