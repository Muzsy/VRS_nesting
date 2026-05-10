pub mod aabb;
pub mod narrow;

// Re-exports for public API
pub use narrow::{can_place, can_place_profiled, CanPlaceProfile, PlacedIndex, PlacedPart};

/// Re-export own narrow-phase implementation for benchmark access (T06m).
pub use narrow::own_polygons_intersect_or_touch;

/// Re-export i_overlay narrow-phase submodule for benchmark access (T06m).
pub use narrow::i_overlay_narrow;
