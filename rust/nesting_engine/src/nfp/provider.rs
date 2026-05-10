//! NFP provider interface — behavior-preserving abstraction over the NFP kernel.
//!
//! T05v pilot: wraps the existing convex/concave dispatch in a typed trait.
//! T05w: adds multi-kernel preparation (ReducedConvolutionExperimental,
//!        CgalReference) and the kernel-aware cache key so future providers
//!        cannot pollute each other's cache entries.
//! T05x: wires CgalReferenceProvider behind NFP_ENABLE_CGAL_REFERENCE=1.
//!
//! CAUTION: do NOT add reduced_convolution, do NOT change the optimal chain.

use std::time::Instant;

use crate::geometry::types::{is_convex, Polygon64};
use crate::nfp::concave::compute_concave_nfp_default;
use crate::nfp::convex::compute_convex_nfp;
use crate::nfp::NfpError;

// ---------------------------------------------------------------------------
// Kernel variant — expanded in T05w for future provider safety
// ---------------------------------------------------------------------------

/// Kernel variant used by a provider.
///
/// T05w preparation: `ReducedConvolutionExperimental` and `CgalReference`
/// are listed here so the cache key can be made kernel-aware before any
/// provider is actually wired in.  They are not implemented yet and will
/// return `Err(NfpError::UnsupportedKernel(...))` from `create_nfp_provider`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum NfpKernel {
    /// The existing convex/concave dispatch in concave.rs / convex.rs.
    OldConcave,
    /// Placeholder for a future reduced-convolution NFP kernel.
    /// Not wired in T05w — requests will error.
    ReducedConvolutionExperimental,
    /// Placeholder for a future CGAL-based reference kernel.
    /// Not wired in T05w — requests will error.
    CgalReference,
}

// ---------------------------------------------------------------------------
// Validation status
// ---------------------------------------------------------------------------

/// Validation status of a computed NFP (future use; None = not checked yet).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NfpValidationStatus {
    NotChecked,
    Valid,
    Invalid,
}

// ---------------------------------------------------------------------------
// Provider result
// ---------------------------------------------------------------------------

/// Result returned by an NFP provider.
#[derive(Debug, Clone)]
pub struct NfpProviderResult {
    /// The computed NFP polygon (relative coordinates).
    pub polygon: Polygon64,
    /// Wall-clock time spent in the kernel in milliseconds.
    pub compute_time_ms: u64,
    /// Which kernel produced this result.
    pub kernel: NfpKernel,
    /// Validation result, if any.
    pub validation_status: Option<NfpValidationStatus>,
}

// ---------------------------------------------------------------------------
// NFP provider trait
// ---------------------------------------------------------------------------

/// Trait for NFP computation backends.
///
/// Providers are immutable after construction (no interior mutability);
/// `Send + Sync` allows them to be stored in a static or shared cache.
pub trait NfpProvider: Send + Sync {
    /// The kernel variant this provider uses.
    fn kernel(&self) -> NfpKernel;

    /// Human-readable kernel name for diagnostics.
    fn kernel_name(&self) -> &'static str;

    /// Whether this provider can handle polygons with holes.
    /// Default = false (mirrors the old_concave default).
    fn supports_holes(&self) -> bool {
        false
    }

    /// Compute the NFP of `moving_polygon` relative to `placed_polygon`.
    /// Returns the NFP in relative coordinates, or an error.
    fn compute(
        &self,
        placed_polygon: &Polygon64,
        moving_polygon: &Polygon64,
    ) -> Result<NfpProviderResult, NfpError>;
}

// ---------------------------------------------------------------------------
// Provider configuration
// ---------------------------------------------------------------------------

/// Configuration for which NFP kernel a provider should use.
///
/// T05w: this struct is the entry point for future CLI/profile wiring.
/// Currently only `OldConcave` is wired; other variants error explicitly.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct NfpProviderConfig {
    /// Which NFP kernel to use.
    pub kernel: NfpKernel,
}

impl Default for NfpProviderConfig {
    fn default() -> Self {
        Self {
            kernel: NfpKernel::OldConcave,
        }
    }
}

// ---------------------------------------------------------------------------
// Provider factory
// ---------------------------------------------------------------------------

/// Create a provider from a config.
///
/// `CgalReference` requires `NFP_ENABLE_CGAL_REFERENCE=1` environment variable.
/// Without it, an explicit `Err(NfpError::UnsupportedKernel(...))` is returned.
///
/// `OldConcave` is always available and is the default.
pub fn create_nfp_provider(config: &NfpProviderConfig) -> Result<Box<dyn NfpProvider>, NfpError> {
    match config.kernel {
        NfpKernel::OldConcave => Ok(Box::new(OldConcaveProvider::new())),
        NfpKernel::ReducedConvolutionExperimental => Err(NfpError::UnsupportedKernel(
            "reduced_convolution_experimental is not wired in T05x",
        )),
        NfpKernel::CgalReference => {
            if std::env::var("NFP_ENABLE_CGAL_REFERENCE").as_deref() != Ok("1") {
                return Err(NfpError::UnsupportedKernel(
                    "cgal_reference requires NFP_ENABLE_CGAL_REFERENCE=1",
                ));
            }
            // Import here to avoid pulling in the CGAL module for non-CGAL builds.
            use crate::nfp::cgal_reference_provider::CgalReferenceProvider;
            Ok(Box::new(CgalReferenceProvider::new()))
        }
    }
}

// ---------------------------------------------------------------------------
// OldConcaveProvider — behavior-preserving wrapper over the existing dispatch
// ---------------------------------------------------------------------------

/// Wraps the existing convex/concave dispatch logic in a provider.
/// This is a pure refactor: no algorithmic change whatsoever.
#[derive(Debug, Clone, Copy, Default)]
pub struct OldConcaveProvider;

impl OldConcaveProvider {
    pub fn new() -> Self {
        Self
    }
}

impl NfpProvider for OldConcaveProvider {
    fn kernel(&self) -> NfpKernel {
        NfpKernel::OldConcave
    }

    fn kernel_name(&self) -> &'static str {
        "old_concave"
    }

    fn supports_holes(&self) -> bool {
        // The existing concave path does not support holes; it returns
        // NfpError::DecompositionFailed for them.
        false
    }

    fn compute(
        &self,
        placed_polygon: &Polygon64,
        moving_polygon: &Polygon64,
    ) -> Result<NfpProviderResult, NfpError> {
        let start = Instant::now();

        let result_polygon = if is_convex(&placed_polygon.outer) && is_convex(&moving_polygon.outer)
        {
            compute_convex_nfp(placed_polygon, moving_polygon)?
        } else {
            compute_concave_nfp_default(placed_polygon, moving_polygon)?
        };

        let elapsed_ms = (start.elapsed().as_secs_f64() * 1000.0).round() as u64;

        Ok(NfpProviderResult {
            polygon: result_polygon,
            compute_time_ms: elapsed_ms,
            kernel: NfpKernel::OldConcave,
            validation_status: None,
        })
    }
}

// ---------------------------------------------------------------------------
// Provider-powered helper — lib-internal, used by nfp_placer.rs
// ---------------------------------------------------------------------------

/// Compute NFP using an arbitrary provider (T05v pilot API).
/// Both arguments are the lib-internal `crate::geometry::types::Polygon64`.
///
/// T06l-a: Per-call `[NFP DIAG]` lines (success and failure) are gated behind
/// `NESTING_ENGINE_NFP_RUNTIME_DIAG=1`. The cache, the provider call itself,
/// and the returned polygon are unaffected — only the eprintln is gated.
pub fn compute_nfp_lib_with_provider(
    placed_polygon: &Polygon64,
    moving_polygon: &Polygon64,
    provider: &dyn NfpProvider,
) -> Option<Polygon64> {
    let runtime_diag = std::env::var("NESTING_ENGINE_NFP_RUNTIME_DIAG").as_deref() == Ok("1");
    match provider.compute(placed_polygon, moving_polygon) {
        Ok(result) => {
            if runtime_diag {
                eprintln!(
                    "[NFP DIAG] provider={} kernel={:?} cache_key_kernel={:?} elapsed_ms={} result_pts={}",
                    provider.kernel_name(),
                    result.kernel,
                    result.kernel,
                    result.compute_time_ms,
                    result.polygon.outer.len()
                );
            }
            Some(result.polygon)
        }
        Err(err) => {
            if runtime_diag {
                eprintln!(
                    "[NFP DIAG] provider={} kernel={:?} FAILED={}",
                    provider.kernel_name(),
                    provider.kernel(),
                    err
                );
            }
            None
        }
    }
}
