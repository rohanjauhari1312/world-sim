import struct
import sys
import zlib

from run_eval import SPLITS
from worldsim.agents import Lookahead, Cruise, play
from worldsim.env import WorldEnv

COL = {"farm": (200, 180, 60), "lumberyard": (40, 120, 50), "mine": (110, 110, 120),
       "house": (190, 90, 70), "school": (70, 90, 200), "levee": (60, 160, 200)}
T = 8


def png(path, px, w, h):
    raw = b"".join(b"\x00" + bytes(c for p in px[y * w:(y + 1) * w] for c in p) for y in range(h))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                           + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def render(w, path):
    cols, rows = 24, 20
    W, H = cols * T, rows * T
    px = [(150 + int(60 * w.fert), 200, 120)] * (W * H)
    def tile(i, c):
        x0, y0 = (i % cols) * T, (i // cols) * T
        for y in range(y0 + 1, y0 + T - 1):
            for x in range(x0 + 1, x0 + T - 1):
                px[y * W + x] = c
    i = 0
    for k, n in w.b.items():
        for _ in range(n):
            if i < cols * rows - cols:
                tile(i, COL[k])
                i += 1
    for j in range(min(int(w.pop / 2), cols)):
        tile(cols * (rows - 1) + j, (240, 220, 200))
    for j in range(min(int(w.gold / 100), cols)):
        tile(cols * (rows - 2) + j, (255, 215, 0))
    png(path, px, W, H)


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
    for name, ag in (("cruise", Cruise()), ("lookahead40", Lookahead(40))):
        env = WorldEnv(seed)
        play(env, ag)
        render(env.w, "results/city_%s_%d.png" % (name, seed))
        print(name, round(env.score()), env.w.outcome, env.w.b)
