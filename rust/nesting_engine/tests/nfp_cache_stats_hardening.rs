use nesting_engine::geometry::types::{Point64, Polygon64};
use nesting_engine::nfp::cache::{NfpCache, NfpCacheKey, NfpKernel, MAX_ENTRIES};

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

fn key(seed: u64) -> NfpCacheKey {
    NfpCacheKey {
        shape_id_a: seed,
        shape_id_b: seed + 1,
        rotation_steps_b: (seed % 360) as i16,
        nfp_kernel: NfpKernel::OldConcave,
    }
}

#[test]
fn peak_entries_tracks_maximum_inserted_entries() {
    let mut cache = NfpCache::new();
    let poly = unit_square();

    cache.insert(key(1), poly.clone());
    cache.insert(key(2), poly.clone());
    cache.insert(key(3), poly);

    let stats = cache.stats();
    assert_eq!(stats.entries, 3);
    assert_eq!(stats.peak_entries, 3);
    assert_eq!(stats.clear_all_events, 0);
}

#[test]
fn hit_and_miss_counters_are_cumulative() {
    let mut cache = NfpCache::new();
    let poly = unit_square();
    let hit_key = key(100);
    let miss_key = key(200);

    cache.insert(hit_key.clone(), poly);
    assert!(cache.get(&hit_key).is_some());
    assert!(cache.get(&hit_key).is_some());
    assert!(cache.get(&miss_key).is_none());

    let stats = cache.stats();
    assert_eq!(stats.hits, 2);
    assert_eq!(stats.misses, 1);
    assert_eq!(stats.entries, 1);
}

#[test]
fn clear_all_preserves_cumulative_stats_and_peak() {
    let mut cache = NfpCache::new();
    let poly = unit_square();
    let k1 = key(300);
    let k2 = key(301);

    cache.insert(k1.clone(), poly.clone());
    cache.insert(k2.clone(), poly);
    assert!(cache.get(&k1).is_some());
    assert!(cache.get(&key(999)).is_none());

    cache.clear_all();
    let stats = cache.stats();
    assert_eq!(stats.entries, 0);
    assert_eq!(stats.clear_all_events, 1);
    assert_eq!(stats.hits, 1);
    assert_eq!(stats.misses, 1);
    assert_eq!(stats.peak_entries, 2);
}

#[test]
fn capacity_clear_all_increments_clear_all_events() {
    if MAX_ENTRIES <= 1 {
        return;
    }

    let mut cache = NfpCache::new();
    let poly = unit_square();
    for idx in 0..MAX_ENTRIES {
        cache.insert(key(idx as u64), poly.clone());
    }
    let before = cache.stats();
    assert_eq!(before.entries, MAX_ENTRIES);

    cache.insert(key(99_999), poly);
    let after = cache.stats();
    assert_eq!(after.entries, 1);
    assert_eq!(after.clear_all_events, before.clear_all_events + 1);
    assert_eq!(after.peak_entries, MAX_ENTRIES);
}
