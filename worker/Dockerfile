# syntax=docker/dockerfile:1.7

FROM rust:1.90-bookworm AS vrs-solver-builder
WORKDIR /build/vrs_solver
COPY rust/vrs_solver/Cargo.toml rust/vrs_solver/Cargo.lock ./
COPY rust/vrs_solver/src ./src
RUN cargo build --release

FROM rust:1.90-bookworm AS sparrow-builder
WORKDIR /build
COPY scripts/ensure_sparrow.sh scripts/ensure_sparrow.sh
COPY poc/sparrow_io/sparrow_commit.txt poc/sparrow_io/sparrow_commit.txt
ENV SPARROW_ALLOW_NETWORK_FALLBACK=1
RUN chmod +x scripts/ensure_sparrow.sh \
    && SPARROW_BIN_PATH="$(./scripts/ensure_sparrow.sh)" \
    && install -m 0755 "$SPARROW_BIN_PATH" /usr/local/bin/sparrow

FROM python:3.12-slim-bookworm AS worker-runtime
WORKDIR /app

# Runtime libs needed by Rust-built binaries.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libstdc++6 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY vrs_nesting vrs_nesting
COPY worker worker
COPY scripts scripts
COPY docs docs
COPY samples samples
COPY poc poc

COPY --from=vrs-solver-builder /build/vrs_solver/target/release/vrs_solver /usr/local/bin/vrs_solver
COPY --from=sparrow-builder /usr/local/bin/sparrow /usr/local/bin/sparrow

ENV PYTHONUNBUFFERED=1
ENV VRS_SOLVER_BIN=/usr/local/bin/vrs_solver
ENV SPARROW_BIN=/usr/local/bin/sparrow

CMD ["python3", "-m", "worker.main"]
