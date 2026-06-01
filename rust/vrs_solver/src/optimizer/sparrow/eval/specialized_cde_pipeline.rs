use super::*;

pub(crate) struct SpecializedCdeHazardCollector;

impl SpecializedCdeHazardCollector {
    pub(crate) fn reload(&mut self, _loss_bound: f64) {}
}

pub(crate) fn collect_poly_collisions_in_detector_custom() -> SpecializedCdeHazardCollector {
    SpecializedCdeHazardCollector
}
