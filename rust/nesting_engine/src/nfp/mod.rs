pub mod cache;
pub mod convex;

use std::fmt::{Display, Formatter};

/// Errors returned by NFP generators.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NfpError {
    EmptyPolygon,
    NotConvex,
}

impl Display for NfpError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::EmptyPolygon => f.write_str("empty polygon ring"),
            Self::NotConvex => f.write_str("polygon is not convex"),
        }
    }
}

impl std::error::Error for NfpError {}
