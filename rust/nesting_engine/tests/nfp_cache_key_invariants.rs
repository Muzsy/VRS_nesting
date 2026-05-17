use nesting_engine::geometry::types::{Point64, Polygon64};
use nesting_engine::nfp::cache::{shape_id, NfpCacheKey, NfpKernel};

fn polygon(outer: &[[i64; 2]], holes: &[Vec<[i64; 2]>]) -> Polygon64 {
    Polygon64 {
        outer: outer
            .iter()
            .map(|p| Point64 { x: p[0], y: p[1] })
            .collect(),
        holes: holes
            .iter()
            .map(|ring| {
                ring.iter()
                    .map(|p| Point64 { x: p[0], y: p[1] })
                    .collect()
            })
            .collect(),
    }
}

fn square(size: i64) -> Polygon64 {
    polygon(&[[0, 0], [size, 0], [size, size], [0, size]], &[])
}

#[test]
fn shape_id_changes_when_polygon_coordinates_change() {
    let nominal = square(10);
    let inflated_like = square(12);

    assert_ne!(shape_id(&nominal), shape_id(&inflated_like));
}

#[test]
fn shape_id_stable_for_equivalent_polygon_boundary_external() {
    let canonical = polygon(&[[0, 0], [10, 0], [10, 10], [0, 10]], &[]);
    let rotated_start = polygon(&[[10, 10], [0, 10], [0, 0], [10, 0]], &[]);

    assert_eq!(shape_id(&canonical), shape_id(&rotated_start));
}

#[test]
fn shape_id_includes_holes() {
    let no_hole = square(20);
    let with_hole = polygon(
        &[[0, 0], [20, 0], [20, 20], [0, 20]],
        &[vec![[5, 5], [5, 15], [15, 15], [15, 5]]],
    );

    assert_ne!(shape_id(&no_hole), shape_id(&with_hole));
}

#[test]
fn shape_id_is_stable_for_equivalent_holes() {
    let with_hole_a = polygon(
        &[[0, 0], [20, 0], [20, 20], [0, 20]],
        &[vec![[5, 5], [5, 15], [15, 15], [15, 5]]],
    );
    // Same hole geometry with different start index + opposite winding.
    let with_hole_b = polygon(
        &[[0, 0], [20, 0], [20, 20], [0, 20]],
        &[vec![[15, 15], [5, 15], [5, 5], [15, 5]]],
    );

    assert_eq!(shape_id(&with_hole_a), shape_id(&with_hole_b));
}

#[test]
fn cache_key_separates_nfp_kernel() {
    let key_old = NfpCacheKey {
        shape_id_a: 11,
        shape_id_b: 22,
        rotation_steps_b: 3,
        nfp_kernel: NfpKernel::OldConcave,
    };
    let key_cgal = NfpCacheKey {
        nfp_kernel: NfpKernel::CgalReference,
        ..key_old.clone()
    };

    assert_ne!(key_old, key_cgal);
}

#[test]
fn cache_key_separates_rotation_steps() {
    let key_r0 = NfpCacheKey {
        shape_id_a: 100,
        shape_id_b: 200,
        rotation_steps_b: 0,
        nfp_kernel: NfpKernel::OldConcave,
    };
    let key_r1 = NfpCacheKey {
        rotation_steps_b: 1,
        ..key_r0.clone()
    };

    assert_ne!(key_r0, key_r1);
}

#[test]
fn cache_key_is_order_sensitive_external() {
    let key_ab = NfpCacheKey {
        shape_id_a: 77,
        shape_id_b: 88,
        rotation_steps_b: 4,
        nfp_kernel: NfpKernel::OldConcave,
    };
    let key_ba = NfpCacheKey {
        shape_id_a: 88,
        shape_id_b: 77,
        ..key_ab.clone()
    };

    assert_ne!(key_ab, key_ba);
}
