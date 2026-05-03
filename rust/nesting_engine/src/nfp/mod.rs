//! NFP computation layer for nesting_engine.
//!
//! F2-1 provides convex NFP generation and cache primitives.
//! F2-2 (concave NFP) is implemented in a separate task but reuses the same
//! cache API and key policy.

pub mod boundary_clean;
pub mod cache;
pub mod cfr;
pub mod concave;
pub mod convex;
pub mod ifp;
pub mod minkowski_cleanup;
pub mod nfp_validation;
pub mod reduced_convolution;

use std::fmt::{Display, Formatter};

/// Errors returned by NFP generators.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NfpError {
    EmptyPolygon,
    NotConvex,
    NotSimpleOutput,
    OrbitLoopDetected,
    OrbitDeadEnd,
    OrbitMaxStepsReached,
    OrbitNotClosed,
    DecompositionFailed,
}

impl Display for NfpError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::EmptyPolygon => f.write_str("empty polygon ring"),
            Self::NotConvex => f.write_str("polygon is not convex"),
            Self::NotSimpleOutput => f.write_str("nfp output boundary is not simple"),
            Self::OrbitLoopDetected => f.write_str("orbit exact mode detected a loop"),
            Self::OrbitDeadEnd => f.write_str("orbit exact mode reached dead-end"),
            Self::OrbitMaxStepsReached => f.write_str("orbit exact mode reached max-steps"),
            Self::OrbitNotClosed => f.write_str("orbit exact mode failed to close a boundary"),
            Self::DecompositionFailed => f.write_str("concave decomposition failed"),
        }
    }
}

impl std::error::Error for NfpError {}
