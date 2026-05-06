/**
 * nfp_cgal_probe — CGAL-based NFP/Minkowski Sum reference implementation
 *
 * Purpose: Validate Rust RC NFP prototype against CGAL ground truth.
 * This is a DEV-ONLY prototype. It is NOT integrated into production.
 *
 * CLI:
 *   nfp_cgal_probe --fixture <json> --algorithm reduced_convolution --output-json [--version] [--help]
 *
 * Input: nfp_pair_fixture_v1 JSON (with optional holes_mm on part_a and part_b)
 * Output: nfp_cgal_probe_result_v1 JSON
 */

#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <chrono>
#include <cmath>
#include <optional>

#include <CGAL/Exact_predicates_exact_constructions_kernel.h>
#include <CGAL/Polygon_2.h>
#include <CGAL/Polygon_with_holes_2.h>
#include <CGAL/minkowski_sum_2.h>

#include <nlohmann/json.hpp>

using json = nlohmann::json;

using Kernel = CGAL::Exact_predicates_exact_constructions_kernel;
using Point_2 = Kernel::Point_2;
using Polygon_2 = CGAL::Polygon_2<Kernel>;
using Polygon_with_holes_2 = CGAL::Polygon_with_holes_2<Kernel>;

constexpr int64_t SCALE = 1'000'000;  // 1 mm = 1_000_000 units

// ──────────────────────────────────────────────────────────────
// CLI argument parsing
// ──────────────────────────────────────────────────────────────

struct CliArgs {
    std::string fixture_path;
    std::string algorithm = "reduced_convolution";
    std::string output_path;
    bool stdout_json = false;
    bool version = false;
    bool help = false;
};

void print_help(const char* prog) {
    std::cout << "nfp_cgal_probe — CGAL NFP reference tool (dev-only)\n"
              << "\n"
              << "Usage:\n"
              << "  " << prog << " --fixture <path> [--output-json [path]] [--algorithm <algo>]\n"
              << "  " << prog << " --version\n"
              << "  " << prog << " --help\n"
              << "\n"
              << "Options:\n"
              << "  --fixture <path>        Path to nfp_pair_fixture_v1 JSON (required)\n"
              << "  --algorithm <algo>      Algorithm: reduced_convolution (default)\n"
              << "  --output-json [path]   Write JSON to stdout (or to path if specified)\n"
              << "  --version              Print version\n"
              << "  --help                 Show this message\n"
              << "\n"
              << "Output schema: nfp_cgal_probe_result_v1\n";
}

CliArgs parse_args(int argc, char** argv) {
    CliArgs args;
    for (int i = 1; i < argc; ++i) {
        std::string arg(argv[i]);
        if (arg == "--help" || arg == "-h") {
            args.help = true;
        } else if (arg == "--version") {
            args.version = true;
        } else if (arg == "--output-json") {
            args.stdout_json = true;
            if (i + 1 < argc) {
                std::string next(argv[i + 1]);
                if (next.size() >= 2 && next.compare(0, 2, "--") != 0 && next[0] != '-') {
                    args.output_path = next;
                    ++i;
                }
            }
        } else if (arg == "--fixture") {
            if (++i >= argc) throw std::runtime_error("--fixture requires a value");
            args.fixture_path = argv[i];
        } else if (arg == "--algorithm") {
            if (++i >= argc) throw std::runtime_error("--algorithm requires a value");
            args.algorithm = argv[i];
        } else {
            throw std::runtime_error("unknown argument: " + arg);
        }
    }
    return args;
}

// ──────────────────────────────────────────────────────────────
// Geometry helpers
// ──────────────────────────────────────────────────────────────

int64_t round_i64(double x) {
    return static_cast<int64_t>(std::llround(x));
}

int64_t mm_to_i64(double mm) {
    return round_i64(mm * SCALE);
}

Point_2 make_point(double x_mm, double y_mm) {
    return Point_2(mm_to_i64(x_mm), mm_to_i64(y_mm));
}

// Ensure counterclockwise orientation (CGAL requirement for outer boundary)
Polygon_2 ensure_ccw(Polygon_2&& poly) {
    if (!poly.is_counterclockwise_oriented()) {
        poly.reverse_orientation();
    }
    return std::move(poly);
}

// Ensure clockwise orientation (CGAL requirement for holes)
Polygon_2 ensure_cw(Polygon_2&& poly) {
    if (!poly.is_clockwise_oriented()) {
        poly.reverse_orientation();
    }
    return std::move(poly);
}

// Reflect polygon_2: (x, y) -> (-x, -y)
Polygon_2 reflect_polygon(const Polygon_2& poly) {
    Polygon_2 out;
    for (auto it = poly.vertices_begin(); it != poly.vertices_end(); ++it) {
        out.push_back(Point_2(-it->x(), -it->y()));
    }
    return out;
}

// Reflect Polygon_with_holes_2: (x, y) -> (-x, -y)
// After reflection, renormalize orientations:
//   - outer boundary: CCW
//   - hole boundaries: CW
Polygon_with_holes_2 reflect_polygon_with_holes(const Polygon_with_holes_2& pwh) {
    Polygon_2 reflected_outer = reflect_polygon(pwh.outer_boundary());
    // Reflection reverses orientation, so:
    //   CCW outer -> CW after reflection -> reverse -> CCW (correct)
    //   CW hole -> CCW after reflection -> reverse -> CW (correct)
    reflected_outer = ensure_ccw(std::move(reflected_outer));

    std::list<Polygon_2> reflected_holes;
    for (auto hole_it = pwh.holes_begin(); hole_it != pwh.holes_end(); ++hole_it) {
        Polygon_2 reflected_hole = reflect_polygon(*hole_it);
        reflected_hole = ensure_cw(std::move(reflected_hole));
        reflected_holes.push_back(std::move(reflected_hole));
    }

    if (reflected_holes.empty()) {
        return Polygon_with_holes_2(std::move(reflected_outer));
    }
    return Polygon_with_holes_2(std::move(reflected_outer),
                                reflected_holes.begin(),
                                reflected_holes.end());
}

// Convert vector<array<double,2>> -> Polygon_2 (outer, CCW)
Polygon_2 make_polygon(const std::vector<std::array<double,2>>& pts) {
    Polygon_2 poly;
    for (const auto& p : pts) {
        poly.push_back(make_point(p[0], p[1]));
    }
    return ensure_ccw(std::move(poly));
}

// Convert holes ring vector<array<double,2>> -> Polygon_2 (hole, CW)
Polygon_2 make_hole_polygon(const std::vector<std::array<double,2>>& pts) {
    Polygon_2 poly;
    for (const auto& p : pts) {
        poly.push_back(make_point(p[0], p[1]));
    }
    return ensure_cw(std::move(poly));
}

// Build Polygon_with_holes_2 from outer + holes rings
// outer_pts: CCW ordered outer boundary
// holes_pts: vector of CW ordered hole rings
Polygon_with_holes_2 make_polygon_with_holes(
    const std::vector<std::array<double,2>>& outer_pts,
    const std::vector<std::vector<std::array<double,2>>>& holes_pts)
{
    Polygon_2 outer = make_polygon(outer_pts);

    if (holes_pts.empty()) {
        return Polygon_with_holes_2(std::move(outer));
    }

    std::list<Polygon_2> holes;
    for (const auto& hole_ring : holes_pts) {
        holes.push_back(make_hole_polygon(hole_ring));
    }
    return Polygon_with_holes_2(std::move(outer), holes.begin(), holes.end());
}

// Convert Polygon_2 vertices to i64 array
std::vector<std::array<int64_t,2>> polygon_to_i64(const Polygon_2& poly) {
    std::vector<std::array<int64_t,2>> out;
    out.reserve(poly.size());
    for (auto it = poly.vertices_begin(); it != poly.vertices_end(); ++it) {
        std::array<int64_t,2> pt;
        pt[0] = static_cast<int64_t>(std::llround(CGAL::to_double(it->x())));
        pt[1] = static_cast<int64_t>(std::llround(CGAL::to_double(it->y())));
        out.push_back(pt);
    }
    return out;
}

// Convert Polygon_with_holes_2 to result JSON
json polygon_with_holes_to_json(const Polygon_with_holes_2& pwh) {
    json result;

    // Outer boundary as outer_i64
    std::vector<std::array<int64_t,2>> outer_i64;
    outer_i64.reserve(pwh.outer_boundary().size());
    for (auto it = pwh.outer_boundary().vertices_begin();
         it != pwh.outer_boundary().vertices_end(); ++it) {
        std::array<int64_t,2> pt;
        pt[0] = static_cast<int64_t>(std::llround(CGAL::to_double(it->x())));
        pt[1] = static_cast<int64_t>(std::llround(CGAL::to_double(it->y())));
        outer_i64.push_back(pt);
    }
    result["outer_i64"] = outer_i64;

    // Holes as holes_i64
    std::vector<std::vector<std::array<int64_t,2>>> holes_i64;
    for (auto hole_it = pwh.holes_begin(); hole_it != pwh.holes_end(); ++hole_it) {
        std::vector<std::array<int64_t,2>> hole_ring;
        hole_ring.reserve(hole_it->size());
        for (auto vit = hole_it->vertices_begin(); vit != hole_it->vertices_end(); ++vit) {
            std::array<int64_t,2> pt;
            pt[0] = static_cast<int64_t>(std::llround(CGAL::to_double(vit->x())));
            pt[1] = static_cast<int64_t>(std::llround(CGAL::to_double(vit->y())));
            hole_ring.push_back(pt);
        }
        holes_i64.push_back(std::move(hole_ring));
    }
    result["holes_i64"] = holes_i64;

    return result;
}

// Count total vertices across all rings
int count_ring_vertices(const std::vector<std::vector<std::array<double,2>>>& rings) {
    int total = 0;
    for (const auto& ring : rings) {
        total += static_cast<int>(ring.size());
    }
    return total;
}

// ──────────────────────────────────────────────────────────────
// NFP/Minkowski computation
// ──────────────────────────────────────────────────────────────

json compute_nfp_cgal(const json& fixture) {
    auto start = std::chrono::steady_clock::now();

    const auto& part_a_json = fixture["part_a"];
    const auto& part_b_json = fixture["part_b"];

    // Read outer + holes from fixture
    auto outer_a_pts = part_a_json["points_mm"].get<std::vector<std::array<double,2>>>();
    auto outer_b_pts = part_b_json["points_mm"].get<std::vector<std::array<double,2>>>();
    auto holes_a_pts = part_a_json.contains("holes_mm")
        ? part_a_json["holes_mm"].get<std::vector<std::vector<std::array<double,2>>>>()
        : std::vector<std::vector<std::array<double,2>>>();
    auto holes_b_pts = part_b_json.contains("holes_mm")
        ? part_b_json["holes_mm"].get<std::vector<std::vector<std::array<double,2>>>>()
        : std::vector<std::vector<std::array<double,2>>>();

    json result;
    result["schema"] = "nfp_cgal_probe_result_v1";
    result["sidecar_version"] = "0.2.0";
    result["algorithm"] = "cgal_reduced_convolution";
    result["pair_id"] = fixture.value("pair_id", "unknown");
    result["scale"] = SCALE;

    // Build Polygon_with_holes_2 for part_a and part_b
    Polygon_with_holes_2 pwh_a = make_polygon_with_holes(outer_a_pts, holes_a_pts);
    Polygon_with_holes_2 pwh_b = make_polygon_with_holes(outer_b_pts, holes_b_pts);

    // Check if input is valid (outer boundary simple)
    if (!pwh_a.outer_boundary().is_simple()) {
        result["status"] = "error";
        result["error"] = {{"code", "INVALID_INPUT"}, {"message", "part_a outer boundary is not simple"}};
        result["outer_i64"] = json::array();
        result["holes_i64"] = json::array();
        result["stats"] = {
            {"input_vertices_a", static_cast<int>(outer_a_pts.size())},
            {"input_holes_a", static_cast<int>(holes_a_pts.size())},
            {"input_hole_vertices_a", count_ring_vertices(holes_a_pts)},
            {"input_vertices_b", static_cast<int>(outer_b_pts.size())},
            {"input_holes_b", static_cast<int>(holes_b_pts.size())},
            {"input_hole_vertices_b", count_ring_vertices(holes_b_pts)},
            {"output_outer_vertices", 0},
            {"output_holes", 0},
            {"output_hole_vertices", 0}
        };
        auto elapsed = std::chrono::steady_clock::now() - start;
        result["timing_ms"] = std::chrono::duration<double, std::milli>(elapsed).count();
        return result;
    }

    if (!pwh_b.outer_boundary().is_simple()) {
        result["status"] = "error";
        result["error"] = {{"code", "INVALID_INPUT"}, {"message", "part_b outer boundary is not simple"}};
        result["outer_i64"] = json::array();
        result["holes_i64"] = json::array();
        result["stats"] = {
            {"input_vertices_a", static_cast<int>(outer_a_pts.size())},
            {"input_holes_a", static_cast<int>(holes_a_pts.size())},
            {"input_hole_vertices_a", count_ring_vertices(holes_a_pts)},
            {"input_vertices_b", static_cast<int>(outer_b_pts.size())},
            {"input_holes_b", static_cast<int>(holes_b_pts.size())},
            {"input_hole_vertices_b", count_ring_vertices(holes_b_pts)},
            {"output_outer_vertices", 0},
            {"output_holes", 0},
            {"output_hole_vertices", 0}
        };
        auto elapsed = std::chrono::steady_clock::now() - start;
        result["timing_ms"] = std::chrono::duration<double, std::milli>(elapsed).count();
        return result;
    }

    try {
        // Compute Minkowski sum via CGAL reduced convolution with Polygon_with_holes_2 inputs
        // CGAL overload at minkowski_sum_2.h:80 — Polygon_with_holes_2 x Polygon_with_holes_2
        // Reflect part_b for NFP (not Minkowski sum)
        Polygon_with_holes_2 reflected_pwh_b = reflect_polygon_with_holes(pwh_b);
        Polygon_with_holes_2 mink_sum =
            CGAL::minkowski_sum_by_reduced_convolution_2(pwh_a, reflected_pwh_b);

        auto elapsed = std::chrono::steady_clock::now() - start;

        // Extract result geometry
        auto geo = polygon_with_holes_to_json(mink_sum);

        // Count output hole vertices
        int output_hole_vertices = 0;
        for (auto hole_it = mink_sum.holes_begin(); hole_it != mink_sum.holes_end(); ++hole_it) {
            output_hole_vertices += static_cast<int>(hole_it->size());
        }

        result["status"] = "success";
        result["scale"] = SCALE;
        result["outer_i64"] = geo["outer_i64"];
        result["holes_i64"] = geo["holes_i64"];
        result["stats"] = {
            {"input_vertices_a", static_cast<int>(outer_a_pts.size())},
            {"input_holes_a", static_cast<int>(holes_a_pts.size())},
            {"input_hole_vertices_a", count_ring_vertices(holes_a_pts)},
            {"input_vertices_b", static_cast<int>(outer_b_pts.size())},
            {"input_holes_b", static_cast<int>(holes_b_pts.size())},
            {"input_hole_vertices_b", count_ring_vertices(holes_b_pts)},
            {"output_outer_vertices", static_cast<int>(mink_sum.outer_boundary().size())},
            {"output_holes", static_cast<int>(mink_sum.number_of_holes())},
            {"output_hole_vertices", output_hole_vertices}
        };
        result["timing_ms"] = std::chrono::duration<double, std::milli>(elapsed).count();
        result["error"] = nullptr;

    } catch (const std::exception& e) {
        auto elapsed = std::chrono::steady_clock::now() - start;
        result["status"] = "error";
        result["error"] = {{"code", "CGAL_EXCEPTION"}, {"message", e.what()}};
        result["outer_i64"] = json::array();
        result["holes_i64"] = json::array();
        result["stats"] = {
            {"input_vertices_a", static_cast<int>(outer_a_pts.size())},
            {"input_holes_a", static_cast<int>(holes_a_pts.size())},
            {"input_hole_vertices_a", count_ring_vertices(holes_a_pts)},
            {"input_vertices_b", static_cast<int>(outer_b_pts.size())},
            {"input_holes_b", static_cast<int>(holes_b_pts.size())},
            {"input_hole_vertices_b", count_ring_vertices(holes_b_pts)},
            {"output_outer_vertices", 0},
            {"output_holes", 0},
            {"output_hole_vertices", 0}
        };
        result["timing_ms"] = std::chrono::duration<double, std::milli>(elapsed).count();
    }

    return result;
}

// ──────────────────────────────────────────────────────────────
// Main
// ──────────────────────────────────────────────────────────────

int main(int argc, char** argv) {
    try {
        CliArgs args = parse_args(argc, argv);

        if (args.version) {
            std::cout << "nfp_cgal_probe v0.2.0\n";
            return 0;
        }

        if (args.help) {
            print_help(argv[0]);
            return 0;
        }

        if (args.fixture_path.empty()) {
            std::cerr << "Error: --fixture is required\n";
            print_help(argv[0]);
            return 1;
        }

        // Read fixture
        std::ifstream f(args.fixture_path);
        if (!f) {
            std::cerr << "Error: cannot open fixture: " << args.fixture_path << "\n";
            return 1;
        }
        json fixture;
        f >> fixture;

        // Validate fixture schema
        if (!fixture.contains("fixture_version") ||
            fixture["fixture_version"] != "nfp_pair_fixture_v1") {
            std::cerr << "Error: not a nfp_pair_fixture_v1 fixture\n";
            return 1;
        }
        if (!fixture.contains("part_a") || !fixture.contains("part_b")) {
            std::cerr << "Error: fixture missing part_a or part_b\n";
            return 1;
        }
        if (!fixture["part_a"].contains("points_mm") ||
            !fixture["part_b"].contains("points_mm")) {
            std::cerr << "Error: part_a or part_b missing points_mm\n";
            return 1;
        }

        // Compute NFP
        json result = compute_nfp_cgal(fixture);

        if (args.stdout_json) {
            std::cout << result.dump(2) << "\n";
        }

        // Write to output path if specified
        if (!args.output_path.empty()) {
            std::ofstream of(args.output_path);
            if (!of) {
                std::cerr << "Error: cannot write output: " << args.output_path << "\n";
                return 1;
            }
            of << result.dump(2) << "\n";
        }

        if (result["status"] == "error") {
            return 1;
        }
        return 0;

    } catch (const std::exception& e) {
        std::cerr << "Fatal: " << e.what() << "\n";
        return 1;
    }
}
