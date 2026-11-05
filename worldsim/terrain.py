import heapq
import math
import random

N = 16
NB = ((1, 0), (-1, 0), (0, 1), (0, -1))
INF = float("inf")


def _noise(r, k):
    g = [[r.random() for _ in range(k + 1)] for _ in range(k + 1)]

    def f(u, v):
        fx, fy = u * k, v * k
        i, j = min(int(fx), k - 1), min(int(fy), k - 1)
        tx, ty = fx - i, fy - j
        tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
        a = g[j][i] * (1 - tx) + g[j][i + 1] * tx
        b = g[j + 1][i] * (1 - tx) + g[j + 1][i + 1] * tx
        return a * (1 - ty) + b * ty
    return f


def _bfs(sources, blocked=()):
    d = {s: 0 for s in sources}
    q = list(sources)
    while q:
        nq = []
        for x, y in q:
            for dx, dy in NB:
                t = (x + dx, y + dy)
                if 0 <= t[0] < N and 0 <= t[1] < N and t not in d:
                    d[t] = d[(x, y)] + 1
                    nq.append(t)
        q = nq
    return d


class Terrain:
    def __init__(self, seed, split="train", rugged=1.0):
        r = random.Random("terrain-%s-%s" % (seed, split))
        n1, n2, n3, nf = _noise(r, 3), _noise(r, 6), _noise(r, 12), _noise(r, 5)
        ang = r.uniform(0, math.pi)
        cx, cy = r.uniform(0.3, 0.7), r.uniform(0.3, 0.7)
        pass_pos = r.uniform(-0.3, 0.3)
        raw = {}
        for y in range(N):
            for x in range(N):
                u, v = x / (N - 1), y / (N - 1)
                val = n1(u, v) * 0.55 + n2(u, v) * 0.3 + n3(u, v) * 0.15
                d = (u - cx) * math.sin(ang) - (v - cy) * math.cos(ang)
                along = (u - cx) * math.cos(ang) + (v - cy) * math.sin(ang)
                gap = math.exp(-((along - pass_pos) ** 2) / (2 * 0.08 ** 2))
                val += rugged * 0.45 * math.exp(-d * d / (2 * 0.07 ** 2)) * (1 - 0.85 * gap)
                raw[(x, y)] = val
        lo, hi = min(raw.values()), max(raw.values())
        self.h = {t: (v - lo) / (hi - lo) for t, v in raw.items()}
        order = sorted(self.h.values())
        sea = order[int(len(order) * 0.1)]
        self.water = {t for t, v in self.h.items() if v <= sea}

        self.river = set()
        tops = sorted(self.h, key=lambda t: -self.h[t])[: int(N * N * 0.08)]
        for _ in range(8):
            cur = r.choice(tops)
            path, seen = [], {cur}
            while len(path) < 45:
                path.append(cur)
                nbs = [(cur[0] + dx, cur[1] + dy) for dx, dy in NB]
                nbs = [t for t in nbs if 0 <= t[0] < N and 0 <= t[1] < N and t not in seen]
                if not nbs:
                    break
                cur = min(nbs, key=lambda t: self.h[t] + r.uniform(0, 0.03))
                seen.add(cur)
                if cur in self.water:
                    break
            if len(path) >= 7:
                self.river = {t for t in path if t not in self.water}
                break
        rl = sorted(self.river)
        self.ford = {t for t in rl if r.random() < 0.18}
        if rl and not self.ford:
            self.ford = {r.choice(rl)}

        wet = self.water | self.river
        dw = _bfs(list(wet)) if wet else {t: 9 for t in self.h}
        dr = _bfs(list(self.river)) if self.river else {t: 9 for t in self.h}
        self.fert0, self.forest, self.ore0, self.risk = {}, {}, {}, {}
        hills = [t for t in self.h if self.h[t] > 0.6 and t not in self.water]
        centers = r.sample(hills, min(len(hills), r.randint(2, 3))) if hills else []
        for t in self.h:
            u, v = t[0] / (N - 1), t[1] / (N - 1)
            h = self.h[t]
            self.fert0[t] = 0.0 if t in wet else min(max(
                0.25 + 0.6 * math.exp(-dw[t] / 3) + 0.3 * (nf(u, v) - 0.5) - 0.5 * max(0, h - 0.6), 0.05), 1.0)
            self.forest[t] = min(max((n2(1 - u, v) - 0.4) * 2.5, 0), 1) if t not in wet else 0.0
            rich = max([math.exp(-((t[0] - c[0]) ** 2 + (t[1] - c[1]) ** 2) / (2 * 1.0 ** 2)) for c in centers] or [0])
            self.ore0[t] = rich * 300 if rich > 0.35 and t not in wet else 0.0
            if t in wet or not self.river:
                self.risk[t] = 0.0
            else:
                near = min(self.river, key=lambda q: abs(q[0] - t[0]) + abs(q[1] - t[1]))
                self.risk[t] = max(0, 1 - dr[t] / 3.5) * max(0, 1 - max(h - self.h[near], 0) / 0.12)

        cands = [t for t in self.h if t not in wet and 0.25 < self.h[t] < 0.62 and 1 <= dr.get(t, 9) <= 4]
        cands = cands or [t for t in self.h if t not in wet]
        self.town = min(cands, key=lambda t: abs(t[0] - N / 2) + abs(t[1] - N / 2))

    def buildable(self, t):
        return t in self.h and t not in self.water and t not in self.river and t != self.town

    def step_cost(self, a, b, roads, bridge_ok):
        if b in roads:
            return 0.3
        if b in self.water:
            return INF
        if b in self.river:
            if b in self.ford:
                return 4.0
            return 6.0 if bridge_ok else INF
        return 1 + 14 * abs(self.h[b] - self.h[a]) + (0.6 if self.forest[b] > 0.5 else 0)

    def dijkstra(self, roads, bridge_ok=False):
        dist, par = {self.town: 0.0}, {}
        pq = [(0.0, self.town)]
        while pq:
            d, a = heapq.heappop(pq)
            if d > dist[a]:
                continue
            for dx, dy in NB:
                b = (a[0] + dx, a[1] + dy)
                if b not in self.h:
                    continue
                nd = d + self.step_cost(a, b, roads, bridge_ok)
                if nd < dist.get(b, INF):
                    dist[b], par[b] = nd, a
                    heapq.heappush(pq, (nd, b))
        return dist, par
