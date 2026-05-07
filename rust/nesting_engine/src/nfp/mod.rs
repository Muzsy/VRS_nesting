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
pub mod cgal_reference_provider; // DEV-only CGAL reference provider
pub mod ifp;
pub mod minkowski_cleanup;
pub mod nfp_validation;
pub mod provider;
pub mod reduced_convolution;

use std::fmt::{Display, Formatter};

/// Errors returned by NFP generators.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum NfpError {
    EmptyPolygon,
    NotConvex,
    NotSimpleOutput,
    OrbitLoopDetected,
    OrbitDeadEnd,
    OrbitMaxStepsReached,
    OrbitNotClosed,
    DecompositionFailed,
    /// A provider was requested for a kernel that is not wired in.
    /// The string describes the unsupported kernel.
    UnsupportedKernel(&'static str),
    /// CGAL binary not found at the configured path.
    CgalBinaryNotFound(String),
    /// CGAL subprocess I/O error (temp file read/write).
    CgalIoError(String),
    /// CGAL subprocess spawn failure.
    CgalSubprocessError(String),
    /// CGAL subprocess exited with non-zero code.
    CgalNonZeroExit { code: i32, stderr: String },
    /// CGAL output JSON could not be parsed.
    CgalParseError(String),
    /// CGAL returned status != "success" with an error message.
    CgalInternalError(String),
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
            Self::UnsupportedKernel(name) => write!(f, "kernel not available: {name}"),
            Self::CgalBinaryNotFound(path) => write!(f, "CGAL binary not found: {path}"),
            Self::CgalIoError(msg) => write!(f, "CGAL I/O error: {msg}"),
            Self::CgalSubprocessError(msg) => write!(f, "CGAL subprocess error: {msg}"),
            Self::CgalNonZeroExit { code, stderr } => {
                write!(f, "CGAL exited with code {code}: {stderr}")
            }
            Self::CgalParseError(msg) => write!(f, "CGAL parse error: {msg}"),
            Self::CgalInternalError(msg) => write!(f, "CGAL internal error: {msg}"),
        }
    }
}

impl std::error::Error for NfpError {}
