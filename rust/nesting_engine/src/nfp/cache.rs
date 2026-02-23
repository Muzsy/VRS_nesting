//! Cache primitives shared by convex (F2-1) and concave (F2-2) NFP generators.
//!
//! `rotation_steps_b` stores a discrete rotation index in
//! `0..=(360/rotation_step_deg - 1)` and intentionally avoids float angles.

use std::collections::HashMap;

use crate::geometry::types::Polygon64;

/// Cache key for NFP(A, B, rotation(B)).
///
/// `rotation_steps_b` is a discrete step index (i16), never an f64 angle.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct NfpCacheKey {
    pub shape_id_a: u64,
    pub shape_id_b: u64,
    pub rotation_steps_b: i16,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CacheStats {
    pub hits: u64,
    pub misses: u64,
    pub entries: usize,
}

#[derive(Debug, Default)]
pub struct NfpCache {
    store: HashMap<NfpCacheKey, Polygon64>,
    hits: u64,
    misses: u64,
}

impl NfpCache {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn get(&mut self, key: &NfpCacheKey) -> Option<&Polygon64> {
        if self.store.contains_key(key) {
            self.hits += 1;
            self.debug_log_stats("hit");
            self.store.get(key)
        } else {
            self.misses += 1;
            self.debug_log_stats("miss");
            None
        }
    }

    pub fn insert(&mut self, key: NfpCacheKey, nfp: Polygon64) {
        self.store.insert(key, nfp);
        self.debug_log_stats("insert");
    }

    pub fn stats(&self) -> CacheStats {
        CacheStats {
            hits: self.hits,
            misses: self.misses,
            entries: self.store.len(),
        }
    }

    #[cfg(debug_assertions)]
    fn debug_log_stats(&self, event: &str) {
        eprintln!(
            "[nfp::cache][debug] event={event} hits={} misses={} entries={}",
            self.hits,
            self.misses,
            self.store.len()
        );
    }

    #[cfg(not(debug_assertions))]
    fn debug_log_stats(&self, _event: &str) {}
}

#[cfg(test)]
mod tests {
    use crate::geometry::types::{Point64, Polygon64};

    use super::{NfpCache, NfpCacheKey};

    fn unit_square() -> Polygon64 {
        Polygon64 {
            outer: vec![
                Point64 { x: 0, y: 0 },
                Point64 { x: 1, y: 0 },
                Point64 { x: 1, y: 1 },
                Point64 { x: 0, y: 1 },
            ],
            holes: Vec::new(),
        }
    }

    #[test]
    fn cache_hit_and_miss_stats() {
        let mut cache = NfpCache::new();
        let key = NfpCacheKey {
            shape_id_a: 1,
            shape_id_b: 2,
            rotation_steps_b: 0,
        };

        assert!(cache.get(&key).is_none());
        cache.insert(key.clone(), unit_square());
        assert!(cache.get(&key).is_some());

        let stats = cache.stats();
        assert_eq!(stats.misses, 1);
        assert_eq!(stats.hits, 1);
        assert_eq!(stats.entries, 1);
    }

    #[test]
    fn cache_key_is_order_sensitive() {
        let mut cache = NfpCache::new();
        let key_ab = NfpCacheKey {
            shape_id_a: 10,
            shape_id_b: 20,
            rotation_steps_b: 1,
        };
        let key_ba = NfpCacheKey {
            shape_id_a: 20,
            shape_id_b: 10,
            rotation_steps_b: 1,
        };

        cache.insert(key_ab.clone(), unit_square());
        assert!(cache.get(&key_ab).is_some());
        assert!(cache.get(&key_ba).is_none());
    }
}
