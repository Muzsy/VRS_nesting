#[test]
fn concave_stable_baseline_does_not_use_float_overlay() {
    let source = include_str!("../src/nfp/concave.rs");

    assert!(
        !source.contains("FloatOverlay"),
        "concave.rs must not reference FloatOverlay"
    );
    assert!(
        !source.contains("i_overlay::float"),
        "concave.rs must not reference i_overlay::float modules"
    );
}
