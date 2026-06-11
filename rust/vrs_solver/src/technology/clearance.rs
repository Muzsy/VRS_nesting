use crate::io::SolverInput;

const VALIDATION_TOLERANCE_MM: f64 = 1e-6;

/// SGH-Q33: Central technology clearance policy built from existing repo fields.
/// Centralises margin_mm / spacing_mm / kerf_mm that already exist in the
/// backend API, snapshot builder and DB schema. Does NOT apply polygon offset
/// or modify solver geometry — Q33 only validates and reports the policy.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct TechnologyClearancePolicy {
    pub margin_mm: f64,
    pub spacing_mm: f64,
    pub kerf_mm: f64,
    pub validation_tolerance_mm: f64,
}

impl TechnologyClearancePolicy {
    /// Build from a `SolverInput`.
    ///
    /// Defaults:
    ///   margin_mm  = input.margin_mm.unwrap_or(0.0)
    ///   spacing_mm = input.spacing_mm.unwrap_or(margin_mm)
    ///   kerf_mm    = input.kerf_mm.unwrap_or(0.0)
    ///
    /// Returns Err when any value is strictly negative.
    pub fn from_solver_input(input: &SolverInput) -> Result<Self, String> {
        let margin_mm = input.margin_mm.unwrap_or(0.0);
        let spacing_mm = input.spacing_mm.unwrap_or(margin_mm);
        let kerf_mm = input.kerf_mm.unwrap_or(0.0);
        let policy = Self {
            margin_mm,
            spacing_mm,
            kerf_mm,
            validation_tolerance_mm: VALIDATION_TOLERANCE_MM,
        };
        policy.validate()?;
        Ok(policy)
    }

    /// Sheet boundary margin — how far parts must stay from sheet edges.
    pub fn effective_sheet_margin_mm(&self) -> f64 {
        self.margin_mm
    }

    /// Minimum separation between adjacent parts.
    pub fn effective_part_spacing_mm(&self) -> f64 {
        self.spacing_mm
    }

    /// Laser/tool kerf width added to cut paths.
    pub fn effective_kerf_mm(&self) -> f64 {
        self.kerf_mm
    }

    /// Validate that no field is negative (within tolerance).
    pub fn validate(&self) -> Result<(), String> {
        if self.margin_mm < -self.validation_tolerance_mm {
            return Err(format!(
                "invalid technology policy: margin_mm ({}) must be >= 0",
                self.margin_mm
            ));
        }
        if self.spacing_mm < -self.validation_tolerance_mm {
            return Err(format!(
                "invalid technology policy: spacing_mm ({}) must be >= 0",
                self.spacing_mm
            ));
        }
        if self.kerf_mm < -self.validation_tolerance_mm {
            return Err(format!(
                "invalid technology policy: kerf_mm ({}) must be >= 0",
                self.kerf_mm
            ));
        }
        Ok(())
    }
}
