//! Cache primitives shared by convex (F2-1) and concave (F2-2) NFP generators.
//!
//! `rotation_steps_b` stores a discrete rotation index in
//! `0..=(360/rotation_step_deg - 1)` and intentionally avoids float angles.

use std::collections::HashMap;

use sha2::{Digest, Sha256};

use crate::geometry::types::{Point64, Polygon64};

pub const MAX_ENTRIES: usize = 10_000;

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
        if let Some(value) = self.store.get(key) {
            self.hits += 1;
            self.debug_log_stats("hit");
            Some(value)
        } else {
            self.misses += 1;
            self.debug_log_stats("miss");
            None
        }
    }

    pub fn insert(&mut self, key: NfpCacheKey, nfp: Polygon64) {
        if self.store.len() >= MAX_ENTRIES {
            self.clear_all();
        }
        self.store.insert(key, nfp);
        self.debug_log_stats("insert");
    }

    pub fn clear_all(&mut self) {
        self.store.clear();
        self.hits = 0;
        self.misses = 0;
        self.debug_log_stats("clear_all");
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

pub fn shape_id(poly: &Polygon64) -> u64 {
    let canonical = canonicalize_polygon(poly);
    let mut hasher = Sha256::new();
    hasher.update(b"shape_id_v1");

    hash_ring(&mut hasher, &canonical.outer);
    hasher.update((canonical.holes.len() as u64).to_le_bytes());
    for hole in &canonical.holes {
        hash_ring(&mut hasher, hole);
    }

    let digest = hasher.finalize();
    let mut first8 = [0_u8; 8];
    first8.copy_from_slice(&digest[..8]);
    u64::from_be_bytes(first8)
}

fn hash_ring(hasher: &mut Sha256, ring: &[Point64]) {
    hasher.update((ring.len() as u64).to_le_bytes());
    for point in ring {
        hasher.update(point.x.to_le_bytes());
        hasher.update(point.y.to_le_bytes());
    }
}

fn canonicalize_polygon(poly: &Polygon64) -> Polygon64 {
    let outer = canonicalize_ring(&poly.outer, true);
    let mut holes: Vec<Vec<Point64>> = poly
        .holes
        .iter()
        .map(|hole| canonicalize_ring(hole, false))
        .collect();
    holes.sort_by(|a, b| compare_rings_lex(a, b));
    Polygon64 { outer, holes }
}

fn canonicalize_ring(points: &[Point64], expect_ccw: bool) -> Vec<Point64> {
    let mut ring = dedup_ring(points);
    if ring.is_empty() {
        return ring;
    }

    let area2 = signed_area2(&ring);
    if area2 != 0 {
        let is_ccw = area2 > 0;
        if is_ccw != expect_ccw {
            ring.reverse();
        }
    }
    rotate_to_lexicographic_min(&mut ring);
    ring
}

fn dedup_ring(points: &[Point64]) -> Vec<Point64> {
    let mut out: Vec<Point64> = Vec::with_capacity(points.len());
    for &point in points {
        if out.last().copied() != Some(point) {
            out.push(point);
        }
    }
    if out.len() > 1 && out.first() == out.last() {
        out.pop();
    }
    out
}

fn rotate_to_lexicographic_min(points: &mut [Point64]) {
    if points.is_empty() {
        return;
    }
    let min_idx = points
        .iter()
        .enumerate()
        .min_by_key(|(_, p)| (p.x, p.y))
        .map(|(idx, _)| idx)
        .unwrap_or(0);
    points.rotate_left(min_idx);
}

fn compare_rings_lex(a: &[Point64], b: &[Point64]) -> std::cmp::Ordering {
    let limit = a.len().min(b.len());
    for idx in 0..limit {
        let pa = a[idx];
        let pb = b[idx];
        let ord = pa.x.cmp(&pb.x).then(pa.y.cmp(&pb.y));
        if !ord.is_eq() {
            return ord;
        }
    }
    a.len().cmp(&b.len())
}

fn signed_area2(points: &[Point64]) -> i128 {
    if points.len() < 3 {
        return 0;
    }
    let mut area2 = 0_i128;
    for idx in 0..points.len() {
        let p0 = points[idx];
        let p1 = points[(idx + 1) % points.len()];
        area2 += (p0.x as i128) * (p1.y as i128) - (p1.x as i128) * (p0.y as i128);
    }
    area2
}

#[cfg(test)]
mod tests {
    use crate::geometry::types::{Point64, Polygon64};

    use super::{shape_id, NfpCache, NfpCacheKey, MAX_ENTRIES};

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

    #[test]
    fn shape_id_is_stable_for_equivalent_polygon_boundary() {
        let a = Polygon64 {
            outer: vec![
                Point64 { x: 0, y: 0 },
                Point64 { x: 5, y: 0 },
                Point64 { x: 5, y: 3 },
                Point64 { x: 0, y: 3 },
                Point64 { x: 0, y: 0 },
            ],
            holes: vec![vec![
                Point64 { x: 4, y: 2 },
                Point64 { x: 1, y: 2 },
                Point64 { x: 1, y: 1 },
                Point64 { x: 4, y: 1 },
                Point64 { x: 4, y: 2 },
            ]],
        };
        let b = Polygon64 {
            outer: vec![
                Point64 { x: 5, y: 3 },
                Point64 { x: 5, y: 0 },
                Point64 { x: 0, y: 0 },
                Point64 { x: 0, y: 3 },
            ],
            holes: vec![vec![
                Point64 { x: 1, y: 1 },
                Point64 { x: 1, y: 2 },
                Point64 { x: 4, y: 2 },
                Point64 { x: 4, y: 1 },
            ]],
        };

        assert_eq!(shape_id(&a), shape_id(&b));
    }

    #[test]
    fn insert_over_cap_clears_cache_and_stats() {
        let mut cache = NfpCache::new();
        let value = unit_square();
        let first_key = NfpCacheKey {
            shape_id_a: 1,
            shape_id_b: 2,
            rotation_steps_b: 0,
        };
        cache.insert(first_key.clone(), value.clone());
        assert!(cache.get(&first_key).is_some());
        assert_eq!(cache.stats().hits, 1);

        cache.clear_all();
        assert_eq!(cache.stats().entries, 0);
        assert_eq!(cache.stats().hits, 0);
        assert_eq!(cache.stats().misses, 0);

        if MAX_ENTRIES > 1 {
            for idx in 0..MAX_ENTRIES {
                cache.insert(
                    NfpCacheKey {
                        shape_id_a: idx as u64,
                        shape_id_b: (idx + 1) as u64,
                        rotation_steps_b: 0,
                    },
                    value.clone(),
                );
            }
            let stats_before = cache.stats();
            assert_eq!(stats_before.entries, MAX_ENTRIES);

            cache.insert(
                NfpCacheKey {
                    shape_id_a: 999_991,
                    shape_id_b: 999_992,
                    rotation_steps_b: 7,
                },
                value,
            );
            let stats_after = cache.stats();
            assert_eq!(stats_after.entries, 1);
            assert_eq!(stats_after.hits, 0);
            assert_eq!(stats_after.misses, 0);
        }
    }
}
