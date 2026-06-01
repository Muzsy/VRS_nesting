use super::*;

#[derive(Debug, Clone)]
pub(crate) struct PairMatrix {
    pub(crate) size: usize,
}

impl PairMatrix {
    pub(crate) fn new(size: usize) -> Self {
        Self { size }
    }
}
