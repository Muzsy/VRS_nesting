pub mod candidates;
pub mod initializer;
pub mod moves;
pub mod score;
pub mod state;

use crate::geometry::{EPS, Rect};
use crate::io::Placement;
use crate::item::{dims_for_rotation, placement_anchor_from_rect_min, Instance};
use crate::sheet::{rect_inside_sheet_shape, SheetShape};

#[derive(Debug)]
pub struct SheetCursor {
    pub x: f64,
    pub y: f64,
    pub row_h: f64,
}

pub fn try_place_on_sheet(
    instance: &Instance,
    sheet: &SheetShape,
    cursor: &mut SheetCursor,
    sheet_index: usize,
) -> Option<Placement> {
    for rot in &instance.allowed_rotations_deg {
        let Some((w, h)) = dims_for_rotation(instance.width, instance.height, *rot) else {
            continue;
        };
        let mut x = cursor.x;
        let mut y = cursor.y;
        let mut row_h = cursor.row_h;

        if x + w > sheet.width + EPS {
            x = 0.0;
            y += row_h;
            row_h = 0.0;
        }

        if y + h > sheet.height + EPS {
            continue;
        }

        let rect = Rect {
            x1: x,
            y1: y,
            x2: x + w,
            y2: y + h,
        };

        if !rect_inside_sheet_shape(rect, sheet) {
            continue;
        }

        let Some((placement_x, placement_y)) =
            placement_anchor_from_rect_min(x, y, instance.width, instance.height, *rot)
        else {
            continue;
        };

        let placed = Placement {
            instance_id: instance.instance_id.clone(),
            part_id: instance.part_id.clone(),
            sheet_index,
            x: placement_x,
            y: placement_y,
            rotation_deg: *rot,
        };

        cursor.x = x + w;
        if h > row_h {
            row_h = h;
        }
        cursor.row_h = row_h;
        cursor.y = y;
        return Some(placed);
    }

    None
}
