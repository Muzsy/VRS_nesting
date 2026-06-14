# Third-Party Notices

This project includes code and/or algorithmic structure derived from third-party sources.

## coroush/sparrow (BPP / multisheet sheet-reduction algorithm)

The SGH-Q45 BPP sheet-reduction multisheet solver
(`rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs`) is an **adapted reimplementation**
of the bin-packing (BPP) sheet-reduction layer of `coroush/sparrow`
(`src/bp_optimizer/{bp_lbf,bp_explore,bp_moves,bp_separator}.rs`). The algorithm structure
(FFD + existing-sheet-first construction, bin/sheet reduction loop, displaced-item
redistribution, inter-bin transfer/swap repair, and bin compaction) was studied and
re-expressed onto VRS's native `SparrowLayout` / CDE collision tracker. No source files were
copied verbatim.

```
This project includes code and/or algorithmic structure derived from coroush/sparrow.
Original copyright:
Copyright (c) 2025 Jeroen Gardeyn, KU Leuven
Licensed under the MIT License.
Source reference: https://github.com/coroush/sparrow, commit 5df9ce15
```

### MIT License (coroush/sparrow)

```
MIT License

Copyright (c) 2025 Jeroen Gardeyn, KU Leuven

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## jagua-rs (collision detection engine)

VRS depends on `jagua-rs` (https://github.com/JeroenGar/jagua-rs) as the geometry / collision
detection backend, used as an unmodified upstream dependency. `jagua-rs` is licensed under the
**Mozilla Public License 2.0 (MPL-2.0)**. No `jagua-rs` source files are modified in this
repository; it is consumed as a pinned crate dependency.
