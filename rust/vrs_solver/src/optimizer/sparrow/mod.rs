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

pub mod bpp_reduction;
pub mod diagnostics;
pub mod eval;
pub mod explore;
pub mod fixed_sheet;
pub mod lbf;
pub mod model;
pub mod multisheet;
pub mod optimizer;
pub mod profile;
pub mod quantify;
pub mod sample;
pub mod separator;
pub mod shape_profile;
mod tests;
pub mod worker;

pub use diagnostics::{SparrowConfig, SparrowDiagnostics};
pub use model::{
    SPInstance, SparrowContainer, SparrowLayout, SparrowPlacement, SparrowProblem,
    SparrowRotationDomain, SparrowSolution, SparrowSolveResult,
};
pub use optimizer::SparrowOptimizer;
pub(crate) use shape_profile::PartShapeProfile;

pub(crate) use diagnostics::*;
pub(crate) use profile::{ProfileTimer, SearchProfiler};
pub(crate) use eval::lbf_evaluator::*;
pub(crate) use eval::sample_eval::*;
pub(crate) use eval::sep_evaluator::*;
pub(crate) use eval::specialized_cde_pipeline::*;
pub(crate) use fixed_sheet::*;
pub(crate) use lbf::*;
pub(crate) use quantify::overlap_proxy::*;
pub(crate) use quantify::tracker::*;
pub(crate) use sample::best_samples::*;
pub(crate) use sample::coord_descent::*;
pub(crate) use sample::search::*;
pub(crate) use sample::uniform_sampler::*;
pub(crate) use worker::*;
