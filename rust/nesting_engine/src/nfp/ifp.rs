use crate::geometry::types::{Point64, Polygon64};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct TranslationRange {
    pub min: i64,
    pub max: i64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IfpRect {
    pub polygon: Polygon64,
    pub tx: TranslationRange,
    pub ty: TranslationRange,
}

/// Computes rect-bin IFP in translation space.
///
/// Inputs are axis-aligned bounding boxes in i64 units:
/// - bin: `[bin_min_x..bin_max_x] x [bin_min_y..bin_max_y]`
/// - moving part: `[moving_min_x..moving_max_x] x [moving_min_y..moving_max_y]`
///
/// The canonical F2-3 use is normalized moving geometry (`moving_min_x = moving_min_y = 0`),
/// but the formula is kept general and deterministic.
pub fn compute_ifp_rect(
    bin_min_x: i64,
    bin_max_x: i64,
    bin_min_y: i64,
    bin_max_y: i64,
    moving_min_x: i64,
    moving_max_x: i64,
    moving_min_y: i64,
    moving_max_y: i64,
) -> Option<IfpRect> {
    if bin_max_x < bin_min_x
        || bin_max_y < bin_min_y
        || moving_max_x < moving_min_x
        || moving_max_y < moving_min_y
    {
        return None;
    }

    let tx_min = bin_min_x - moving_min_x;
    let tx_max = bin_max_x - moving_max_x;
    let ty_min = bin_min_y - moving_min_y;
    let ty_max = bin_max_y - moving_max_y;

    if tx_max < tx_min || ty_max < ty_min {
        return None;
    }

    let polygon = Polygon64 {
        outer: vec![
            Point64 {
                x: tx_min,
                y: ty_min,
            },
            Point64 {
                x: tx_max,
                y: ty_min,
            },
            Point64 {
                x: tx_max,
                y: ty_max,
            },
            Point64 {
                x: tx_min,
                y: ty_max,
            },
        ],
        holes: Vec::new(),
    };

    Some(IfpRect {
        polygon,
        tx: TranslationRange {
            min: tx_min,
            max: tx_max,
        },
        ty: TranslationRange {
            min: ty_min,
            max: ty_max,
        },
    })
}

#[cfg(test)]
mod tests {
    use crate::geometry::types::{signed_area2_i128, Point64};

    use super::compute_ifp_rect;

    #[test]
    fn rect_ifp_ranges_and_polygon_are_correct() {
        let ifp = compute_ifp_rect(10, 110, 20, 90, 0, 30, 0, 10).expect("ifp must exist");
        assert_eq!(ifp.tx.min, 10);
        assert_eq!(ifp.tx.max, 80);
        assert_eq!(ifp.ty.min, 20);
        assert_eq!(ifp.ty.max, 80);
        assert_eq!(
            ifp.polygon.outer,
            vec![
                Point64 { x: 10, y: 20 },
                Point64 { x: 80, y: 20 },
                Point64 { x: 80, y: 80 },
                Point64 { x: 10, y: 80 },
            ]
        );
        assert!(
            signed_area2_i128(&ifp.polygon.outer) > 0,
            "IFP outer must be CCW"
        );
    }

    #[test]
    fn too_large_part_produces_empty_ifp() {
        let ifp = compute_ifp_rect(0, 50, 0, 40, 0, 60, 0, 10);
        assert!(ifp.is_none());
    }
}
