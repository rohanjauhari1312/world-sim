import math
import random
import struct
import zlib
import time
from pathlib import Path

# =============================================================================
# 1. PROCEDURAL TOPOGRAPHIC TERRAIN & CONTOUR ENGINE
# =============================================================================

class TopographicTerrain:
    """Generates continuous procedural terrain with realistic river valleys and ridgelines."""
    def __init__(self, size=256, seed=10000):
        self.size = size
        self.rng = random.Random(seed)
        # Permutation table for smooth value noise
        self.perm = list(range(256))
        self.rng.shuffle(self.perm)
        self.perm += self.perm
        # 2D unit gradients
        self.grads = []
        for _ in range(256):
            a = self.rng.uniform(0, 2 * math.pi)
            self.grads.append((math.cos(a), math.sin(a)))

    def _fade(self, t):
        return t * t * t * (t * (t * 6 - 15) + 10)

    def _dot(self, hash_val, x, y):
        gx, gy = self.grads[hash_val & 255]
        return gx * x + gy * y

    def noise2d(self, x, y):
        X = int(math.floor(x)) & 255
        Y = int(math.floor(y)) & 255
        xf = x - math.floor(x)
        yf = y - math.floor(y)
        u = self._fade(xf)
        v = self._fade(yf)
        
        A = self.perm[X] + Y
        B = self.perm[X + 1] + Y
        
        g00 = self._dot(self.perm[A], xf, yf)
        g10 = self._dot(self.perm[B], xf - 1, yf)
        g01 = self._dot(self.perm[A + 1], xf, yf - 1)
        g11 = self._dot(self.perm[B + 1], xf - 1, yf - 1)
        
        x1 = g00 + u * (g10 - g00)
        x2 = g01 + u * (g11 - g01)
        return x1 + v * (x2 - x1)

    def generate(self, octaves=4, persistence=0.5):
        grid = []
        scale = 0.012
        for y in range(self.size):
            row = []
            for x in range(self.size):
                val = 0.0
                amp = 1.0
                freq = 1.0
                max_amp = 0.0
                for _ in range(octaves):
                    val += self.noise2d(x * scale * freq, y * scale * freq) * amp
                    max_amp += amp
                    amp *= persistence
                    freq *= 2.0
                h = (val / max_amp + 1.0) * 0.5
                
                # Sinuous natural river valley carving
                river_center = self.size * 0.45 + 30 * math.sin(x * 0.025) + 15 * math.cos(x * 0.05)
                dist_to_river = abs(y - river_center) / (self.size * 0.5)
                valley = math.pow(min(dist_to_river, 1.0), 0.65)
                
                # Blend mountain ridges with river valley
                h = h * 0.60 + valley * 0.40
                row.append(max(0.0, min(1.0, h)))
            grid.append(row)
        self.grid = grid
        return grid


# =============================================================================
# 2. CONTOUR-FOLLOWING ORGANIC SETTLEMENT GENERATOR
# =============================================================================

class ContourSettlement:
    """Places buildings and infrastructure organically along elevation contours."""
    def __init__(self, terrain_grid, seed=10000):
        self.grid = terrain_grid
        self.size = len(terrain_grid)
        self.rng = random.Random(seed)
        self.buildings = []
        self.roads = []

    def get_elevation(self, x, y):
        ix = max(0, min(self.size - 1, int(x)))
        iy = max(0, min(self.size - 1, int(y)))
        return self.grid[iy][ix]

    def get_slope(self, x, y):
        ix = max(1, min(self.size - 2, int(x)))
        iy = max(1, min(self.size - 2, int(y)))
        dx = (self.grid[iy][ix + 1] - self.grid[iy][ix - 1]) * 0.5
        dy = (self.grid[iy + 1][ix] - self.grid[iy - 1][ix]) * 0.5
        return math.sqrt(dx * dx + dy * dy), (-dy, dx) # magnitude, contour tangent

    def trace_contour_road(self, start_x, start_y, target_elev, steps=80, step_size=2.0):
        """Traces a winding road that strictly follows an elevation contour."""
        path = [(start_x, start_y)]
        cx, cy = start_x, start_y
        for _ in range(steps):
            slope, (tx, ty) = self.get_slope(cx, cy)
            mag = math.sqrt(tx * tx + ty * ty)
            if mag < 1e-5:
                break
            tx, ty = tx / mag, ty / mag
            # Elevation correction back toward target contour
            cur_e = self.get_elevation(cx, cy)
            e_err = target_elev - cur_e
            # Move along contour tangent with slight corrective bias
            nx = cx + (tx * 0.85 + (ty * -e_err * 2.0)) * step_size
            ny = cy + (ty * 0.85 + (-tx * -e_err * 2.0)) * step_size
            if 10 < nx < self.size - 10 and 10 < ny < self.size - 10:
                cx, cy = nx, ny
                path.append((cx, cy))
            else:
                break
        return path

    def place_settlement(self, building_counts):
        """Organically distributes settlement assets along their natural topographical niches."""
        placed = []
        
        # 1. Trace organic primary contour roads across mid-elevations
        contour_bands = [0.32, 0.42, 0.52]
        all_road_pts = []
        for elev in contour_bands:
            # Find starting seed point near this elevation
            start_y = int(self.size * (0.3 + elev * 0.4))
            road = self.trace_contour_road(20, start_y, target_elev=elev, steps=100, step_size=2.2)
            if len(road) > 20:
                self.roads.append(road)
                all_road_pts.extend(road[::4])

        # Helper to find organic spots along elevation bands
        def find_contour_spots(target_elev, elev_tol, max_slope, count):
            candidates = []
            for y in range(15, self.size - 15, 3):
                for x in range(15, self.size - 15, 3):
                    e = self.get_elevation(x, y)
                    slope, _ = self.get_slope(x, y)
                    if abs(e - target_elev) < elev_tol and slope < max_slope:
                        candidates.append((x, y, e, slope))
            self.rng.shuffle(candidates)
            # Spatial Poisson-like spacing
            selected = []
            for cx, cy, e, s in candidates:
                if len(selected) >= count:
                    break
                # Check separation distance
                if all(math.hypot(cx - px, cy - py) > 9.0 for px, py, *_ in selected):
                    selected.append((cx, cy, e, s))
            return selected

        # A. FARMS: Low-elevation fertile valley terraces (Elev 0.25 - 0.35, gentle slope)
        farm_spots = find_contour_spots(0.30, 0.08, max_slope=0.03, count=building_counts.get("farm", 0))
        for x, y, e, _ in farm_spots:
            placed.append(dict(kind="farm", x=x, y=y, elev=e, rot=self.rng.uniform(0, 360)))

        # B. HOUSES: Clustered along mid-elevation contour roads (Elev 0.38 - 0.50)
        house_target = building_counts.get("house", 0)
        house_spots = []
        if all_road_pts:
            self.rng.shuffle(all_road_pts)
            for rx, ry in all_road_pts:
                if len(house_spots) >= house_target:
                    break
                # Offset slightly perpendicular to road
                _, (tx, ty) = self.get_slope(rx, ry)
                offset = self.rng.choice([-6.0, 6.0])
                hx = rx - ty * offset + self.rng.uniform(-2, 2)
                hy = ry + tx * offset + self.rng.uniform(-2, 2)
                if all(math.hypot(hx - px, hy - py) > 7.0 for px, py, *_ in house_spots):
                    house_spots.append((hx, hy, self.get_elevation(hx, hy), 0))
        for x, y, e, _ in house_spots:
            placed.append(dict(kind="house", x=x, y=y, elev=e, rot=self.rng.uniform(0, 360)))

        # C. LUMBERYARDS: Wooded valley slopes (Elev 0.45 - 0.60)
        lumber_spots = find_contour_spots(0.50, 0.08, max_slope=0.05, count=building_counts.get("lumberyard", 0))
        for x, y, e, _ in lumber_spots:
            placed.append(dict(kind="lumberyard", x=x, y=y, elev=e, rot=self.rng.uniform(0, 360)))

        # D. MINES: Rocky ridgelines and high-elevation crests (Elev 0.65 - 0.85)
        mine_spots = find_contour_spots(0.70, 0.12, max_slope=0.09, count=building_counts.get("mine", 0))
        for x, y, e, _ in mine_spots:
            placed.append(dict(kind="mine", x=x, y=y, elev=e, rot=self.rng.uniform(0, 360)))

        # E. LEVEES: Snaking along the river shoreline contour (Elev 0.20 - 0.26)
        levee_spots = find_contour_spots(0.23, 0.04, max_slope=0.04, count=building_counts.get("levee", 0))
        for x, y, e, _ in levee_spots:
            placed.append(dict(kind="levee", x=x, y=y, elev=e, rot=self.rng.uniform(0, 360)))

        # F. SCHOOL: Central civic plateau
        school_spots = find_contour_spots(0.40, 0.05, max_slope=0.02, count=building_counts.get("school", 0))
        for x, y, e, _ in school_spots:
            placed.append(dict(kind="school", x=x, y=y, elev=e, rot=0))

        self.buildings = placed
        return placed


# =============================================================================
# 3. HIGH-RESOLUTION VECTOR SVG & CONTOUR MAP RENDERER
# =============================================================================

def render_contour_svg(terrain, settlement, out_path):
    """Renders an authentic topographic contour map with hillshading and organic settlement layout."""
    size = terrain.size
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="800" height="800" style="background:#eef2e6;font-family:sans-serif">')
    
    # 1. Topographic Elevation Tinting / Shading
    svg.append('<defs>')
    svg.append('<filter id="hillshade"><feGaussianBlur stdDeviation="1.5"/></filter>')
    svg.append('</defs>')

    # 2. Draw Elevation Contour Isolines
    contour_levels = [0.22, 0.28, 0.35, 0.42, 0.50, 0.58, 0.66, 0.74]
    for lvl in contour_levels:
        stroke = "#a8b598" if lvl != 0.50 else "#7c8c69"
        width = "0.7" if lvl != 0.50 else "1.2"
        dash = "" if lvl != 0.50 else 'stroke-dasharray="4,2"'
        
        # Extract isoline segments
        segments = []
        for y in range(0, size - 2, 2):
            for x in range(0, size - 2, 2):
                h00 = terrain.grid[y][x]
                h10 = terrain.grid[y][x + 2]
                h01 = terrain.grid[y + 2][x]
                if (h00 < lvl and h10 >= lvl) or (h00 >= lvl and h10 < lvl):
                    segments.append(f"M {x} {y} L {x+2} {y}")
                elif (h00 < lvl and h01 >= lvl) or (h00 >= lvl and h01 < lvl):
                    segments.append(f"M {x} {y} L {x} {y+2}")
        if segments:
            path_d = " ".join(segments[:1200]) # Bounded for SVG efficiency
            svg.append(f'<path d="{path_d}" stroke="{stroke}" stroke-width="{width}" fill="none" opacity="0.65" {dash}/>')

    # 3. Draw Sinuous River Meander
    river_pts = []
    for x in range(0, size, 4):
        ry = size * 0.45 + 30 * math.sin(x * 0.025) + 15 * math.cos(x * 0.05)
        river_pts.append(f"{x},{ry:.1f}")
    svg.append(f'<polyline points="{" ".join(river_pts)}" fill="none" stroke="#6baed6" stroke-width="7" stroke-linecap="round" opacity="0.85"/>')
    svg.append(f'<polyline points="{" ".join(river_pts)}" fill="none" stroke="#9ecae1" stroke-width="4" stroke-linecap="round" opacity="0.9"/>')

    # 4. Draw Organic Contour Roads
    for road in settlement.roads:
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in road)
        svg.append(f'<polyline points="{pts}" fill="none" stroke="#d4b58c" stroke-width="3" stroke-linecap="round" opacity="0.9"/>')
        svg.append(f'<polyline points="{pts}" fill="none" stroke="#8c6d48" stroke-width="1.2" stroke-linecap="round" stroke-dasharray="2,2"/>')

    # 5. Draw Organic Buildings by Topographic Niche
    PALETTE = {
        "farm": ("#c8b43c", "#8c781e", 8, "Agricultural Terrace"),
        "house": ("#d95f02", "#8c2d04", 5, "Hillside Dwelling"),
        "lumberyard": ("#31a354", "#006d2c", 7, "Forestry Mill"),
        "mine": ("#756bb1", "#54278f", 8, "Crest Quarry"),
        "levee": ("#2b8cbe", "#045a8d", 6, "Flood Defense"),
        "school": ("#e7298a", "#980043", 9, "Civic Academy")
    }
    
    for b in settlement.buildings:
        fill, stroke, bsize, label = PALETTE[b["kind"]]
        bx, by = b["x"], b["y"]
        rot = b["rot"]
        svg.append(f'<rect x="{bx - bsize/2:.1f}" y="{by - bsize/2:.1f}" width="{bsize}" height="{bsize}" '
                   f'fill="{fill}" stroke="{stroke}" stroke-width="0.8" rx="1" '
                   f'transform="rotate({rot:.0f} {bx:.1f} {by:.1f})"/>')

    # 6. Topographic Map Legend & Coordinates
    svg.append('<rect x="10" y="10" width="220" height="100" fill="white" fill-opacity="0.9" stroke="#cbd5e1" rx="4"/>')
    svg.append('<text x="20" y="28" font-size="11" font-weight="bold" fill="#0f172a">CONTOUR SETTLEMENT MAP</text>')
    svg.append('<text x="20" y="42" font-size="8" fill="#475569">Organic Topographic Settlement Morphology</text>')
    
    # Legend dots
    leg_y = 56
    for k, (f, s, _, name) in list(PALETTE.items())[:3]:
        svg.append(f'<rect x="20" y="{leg_y}" width="6" height="6" fill="{f}" stroke="{s}" rx="1"/>')
        svg.append(f'<text x="32" y="{leg_y+5}" font-size="7" fill="#334155">{name}</text>')
        leg_y += 13
    leg_y = 56
    for k, (f, s, _, name) in list(PALETTE.items())[3:]:
        svg.append(f'<rect x="120" y="{leg_y}" width="6" height="6" fill="{f}" stroke="{s}" rx="1"/>')
        svg.append(f'<text x="132" y="{leg_y+5}" font-size="7" fill="#334155">{name}</text>')
        leg_y += 13

    svg.append('</svg>')
    Path(out_path).write_text("\n".join(svg))
    return out_path


# =============================================================================
# 4. BENCHMARK & SCALE THE PROCESS
# =============================================================================

def benchmark_process_scaling(n_worlds=100):
    """Demonstrates how procedural contour generation scales across hundreds of worlds."""
    t0 = time.time()
    total_buildings = 0
    
    for seed in range(10000, 10000 + n_worlds):
        # 1. Generate 128x128 continuous terrain
        tt = TopographicTerrain(size=128, seed=seed)
        grid = tt.generate()
        
        # 2. Place settlement assets along contours
        cs = ContourSettlement(grid, seed=seed)
        counts = {"farm": 12, "house": 24, "lumberyard": 6, "mine": 5, "levee": 8, "school": 2}
        placed = cs.place_settlement(counts)
        total_buildings += len(placed)
        
    duration = time.time() - t0
    rate = n_worlds / duration
    b_rate = total_buildings / duration
    return dict(n_worlds=n_worlds, duration=duration, worlds_per_sec=rate, buildings_per_sec=b_rate)


if __name__ == "__main__":
    out_dir = Path("world-sim/results")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print("Generating High-Resolution Contour City for Seed 10000...")
    tt = TopographicTerrain(size=256, seed=10000)
    grid = tt.generate()
    
    cs = ContourSettlement(grid, seed=10000)
    # Using typical Lookahead-40 mature building portfolio (57 buildings)
    portfolio = {"farm": 14, "house": 26, "lumberyard": 7, "mine": 6, "levee": 8, "school": 2}
    buildings = cs.place_settlement(portfolio)
    
    svg_path = out_dir / "contour_city_10000.svg"
    render_contour_svg(tt, cs, svg_path)
    print(f"Rendered Topographic SVG Map -> {svg_path} ({len(buildings)} buildings)")
    
    print("\nRunning Process Scaling Benchmark (100 Worlds)...")
    res = benchmark_process_scaling(100)
    print(f"Generated {res['n_worlds']} contour worlds in {res['duration']:.2f}s "
          f"({res['worlds_per_sec']:.1f} worlds/sec, {res['buildings_per_sec']:.0f} buildings/sec)")
