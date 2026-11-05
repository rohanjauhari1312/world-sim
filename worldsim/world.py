import math
import random

from .terrain import INF, N, Terrain

GOODS = ("food", "wood", "ore")
WORK = ("farm", "lumberyard", "mine")
BUILDINGS = {
    "farm": dict(gold=25, wood=8, time=2, slots=5, upkeep=1.0),
    "lumberyard": dict(gold=30, wood=0, time=2, slots=5, upkeep=1.0),
    "mine": dict(gold=40, wood=10, time=3, slots=5, upkeep=2.0),
    "house": dict(gold=20, wood=12, time=2, slots=0, upkeep=0.0),
    "school": dict(gold=70, wood=18, time=5, slots=0, upkeep=3.0),
    "levee": dict(gold=55, wood=25, time=4, slots=0, upkeep=1.0),
    "road": dict(gold=10, wood=2, time=1, slots=0, upkeep=0.1),
    "bridge": dict(gold=45, wood=12, time=3, slots=0, upkeep=0.5),
}
PRODUCES = {"farm": "food", "lumberyard": "wood", "mine": "ore"}
ACTION_BUDGET = 12
LEVEE_RADIUS = 3
_TERRAINS = {}


def terrain_for(seed, split, rugged):
    key = (seed, split, rugged)
    if key not in _TERRAINS:
        if len(_TERRAINS) > 400:
            _TERRAINS.clear()
        _TERRAINS[key] = Terrain(seed, split, rugged)
    return _TERRAINS[key]


def make_params(seed, split="train"):
    r = random.Random("params-%s-%s" % (seed, split))
    stress = 1.0 if split == "train" else 1.6
    return dict(
        seed=seed,
        split=split,
        horizon=100,
        rugged=r.uniform(0.7, 1.4) * (1.2 if split != "train" else 1.0),
        transport=r.uniform(0.03, 0.05),
        food_per_pop=r.uniform(0.4, 0.6),
        yield_={"farm": 2.3 * r.uniform(0.9, 1.15),
                "lumberyard": 1.4 * r.uniform(0.9, 1.15),
                "mine": 1.1 * r.uniform(0.9, 1.15)},
        fert_decay=r.uniform(0.006, 0.02) * (1.3 if split != "train" else 1.0),
        fert_recover=0.01,
        base_price={"food": r.uniform(2.4, 3.8), "wood": r.uniform(3.0, 5.0), "ore": r.uniform(7.0, 12.0)},
        price_vol=r.uniform(0.03, 0.09) * stress,
        price_revert=r.uniform(0.06, 0.12),
        season_amp=r.uniform(0.08, 0.25),
        season_len=r.choice([12, 16, 20, 24]),
        season_phase={g: r.uniform(0, 2 * math.pi) for g in GOODS},
        depth={"food": 80 * r.uniform(0.8, 1.5), "wood": 60 * r.uniform(0.8, 1.5), "ore": 40 * r.uniform(0.8, 1.5)},
        impact=r.uniform(0.8, 1.6),
        spread=r.uniform(0.05, 0.12),
        wage=r.uniform(3.0, 5.0),
        interest=r.uniform(0.015, 0.045) * (1.5 if split != "train" else 1.0),
        pop_growth=r.uniform(0.04, 0.07),
        base_cap=15,
        house_cap=8,
        school_boost=r.uniform(0.25, 0.5),
        election_period=r.choice([15, 20, 25, 30]),
        tax_cap=r.uniform(0.25, 0.45),
        tariff=r.uniform(0.0, 0.2),
        p_drought=r.uniform(0.02, 0.05) * stress,
        p_flood=r.uniform(0.03, 0.07) * stress,
        p_plague=r.uniform(0.01, 0.03) * stress,
        p_war=r.uniform(0.01, 0.03) * stress,
        start_gold=r.uniform(90, 160),
        start_pop=r.randint(26, 34),
    )


class World:
    def __init__(self, params, rng_seed=None):
        self.p = params
        self.T = terrain_for(params["seed"], params["split"], params["rugged"])
        self.rng = random.Random(params["seed"] * 7919 + 13 if rng_seed is None else rng_seed)
        p, T = params, self.T
        self.t = 0
        self.pop = float(p["start_pop"])
        self.gold = p["start_gold"]
        self.debt = 0.0
        self.stock = {"food": 30.0, "wood": 45.0, "ore": 0.0}
        self.tiles = {}
        self.roads = set()
        self.b = {k: 0 for k in BUILDINGS}
        self.queue = []
        self.work = {k: 0 for k in WORK}
        self.tfert = dict(T.fert0)
        self.tore = dict(T.ore0)
        self.edu = 1.0
        self.happy = 0.7
        self.tax = 0.2
        self.tax_cap = p["tax_cap"]
        self.tariff = p["tariff"]
        self.ref = dict(p["base_price"])
        self.shock = {g: 1.0 for g in GOODS}
        self.hist = {g: [p["base_price"][g]] * 4 for g in GOODS}
        self.drought = 0
        self.war = 0
        self.low_happy = 0
        self.income_last = 0.0
        self.done = False
        self.outcome = "running"
        self.log = []
        self._cost = None
        for kind, n in (("farm", 3), ("lumberyard", 1), ("mine", 1), ("house", 3)):
            for t in self.sites(kind, n):
                self.tiles[t] = kind
                self.b[kind] += 1
        self.assign_default()

    def clone(self, rng_seed):
        w = World.__new__(World)
        w.p, w.T = self.p, self.T
        w.rng = random.Random(rng_seed)
        for k in ("t", "pop", "gold", "debt", "edu", "happy", "tax", "tax_cap", "tariff", "drought", "war",
                  "low_happy", "income_last", "done", "outcome", "_cost"):
            setattr(w, k, getattr(self, k))
        w.stock = dict(self.stock)
        w.tiles = dict(self.tiles)
        w.roads = set(self.roads)
        w.b = dict(self.b)
        w.queue = [list(q) for q in self.queue]
        w.work = dict(self.work)
        w.tfert = dict(self.tfert)
        w.tore = dict(self.tore)
        w.ref = dict(self.ref)
        w.shock = dict(self.shock)
        w.hist = {g: list(v) for g, v in self.hist.items()}
        w.log = []
        return w

    def cost(self):
        if self._cost is None:
            self._cost = self.T.dijkstra(self.roads)
        return self._cost[0]

    def deliver(self, t):
        c = self.cost().get(t, INF)
        return 0.0 if c == INF else max(0.2, 1 - self.p["transport"] * c)

    def season(self, g, t):
        p = self.p
        return 1 + p["season_amp"] * math.sin(2 * math.pi * t / p["season_len"] + p["season_phase"][g])

    def price(self, g):
        base = self.ref[g] * self.shock[g]
        if g == "food":
            need = self.pop * self.p["food_per_pop"] * 5
            cover = max(self.stock["food"] / max(need, 1e-6), 0.15)
            base *= min(max(cover ** -0.35, 0.6), 2.4)
        return base

    def spread(self):
        s = self.p["spread"] * (1 + self.tariff * 3)
        return s * (2.5 if self.war > 0 else 1.0)

    def workers(self):
        return int(self.pop * 0.6)

    def slots(self, kind):
        return self.b[kind] * BUILDINGS[kind]["slots"]

    def housing(self):
        return self.p["base_cap"] + self.p["house_cap"] * self.b["house"]

    def credit_limit(self):
        return 120 + 6 * self.income_last

    def protection(self, t):
        n = sum(1 for q, k in self.tiles.items() if k == "levee" and abs(q[0] - t[0]) + abs(q[1] - t[1]) <= LEVEE_RADIUS)
        return min(1.0, 0.5 * n)

    def net_worth(self):
        return self.gold - self.debt + sum(self.stock[g] * self.p["base_price"][g] for g in GOODS)

    def score(self):
        s = self.net_worth() + 8 * self.pop * (0.5 + 0.5 * self.happy)
        return s - 500 if self.outcome in ("collapse", "bankrupt") else s

    def reserve(self):
        return sum(self.tore[t] for t, k in self.tiles.items() if k == "mine")

    def unit(self, t, kind, farm_mult=1.0):
        y = self.p["yield_"][kind] * self.edu * self.deliver(t)
        if kind == "farm":
            return y * self.tfert[t] * farm_mult
        if kind == "lumberyard":
            return y * (0.5 + self.T.forest[t])
        return y

    def ranked(self, kind, farm_mult=1.0):
        ts = [t for t, k in self.tiles.items() if k == kind]
        return sorted(ts, key=lambda t: -self.unit(t, kind, farm_mult))

    def fert(self):
        fs = [self.tfert[t] for t, k in self.tiles.items() if k == "farm"]
        return sum(fs) / len(fs) if fs else 0.0

    def workers_for_food(self, need):
        got, n = 0.0, 0
        for t in self.ranked("farm"):
            for _ in range(5):
                if got >= need:
                    return n
                got += self.unit(t, "farm")
                n += 1
        return n

    def sites(self, kind, k):
        T = self.T
        cost = self.cost()
        free = [t for t in T.h if T.buildable(t) and t not in self.tiles and cost.get(t, INF) < INF
                and not any(q[2] == t for q in self.queue)]
        if kind == "farm":
            f = lambda t: T.fert0[t] * self.deliver(t) * (1 - 0.6 * T.risk[t])
        elif kind == "lumberyard":
            f = lambda t: (0.5 + T.forest[t]) * self.deliver(t) * (1 - 0.3 * T.risk[t])
        elif kind == "mine":
            free = [t for t in free if self.tore[t] > 5]
            f = lambda t: self.tore[t] * self.deliver(t)
        elif kind in ("house", "school"):
            f = lambda t: self.deliver(t) * (1 - T.risk[t]) - 0.01 * cost.get(t, 0)
        else:
            f = lambda t: sum(T.risk[q] for q in self.tiles
                              if abs(q[0] - t[0]) + abs(q[1] - t[1]) <= LEVEE_RADIUS) * (1 - self.protection(t))
        return sorted(free, key=lambda t: -f(t))[:k]

    def road_routes(self, target, bridge_ok):
        dist, par = self.T.dijkstra(self.roads, bridge_ok)
        path, cur = [], target
        while cur in par:
            if cur not in self.roads and cur != self.T.town:
                path.append(cur)
            cur = par[cur]
        return path

    def assign_default(self):
        free = self.workers()
        for k in WORK:
            n = min(self.slots(k), free)
            self.work[k] = n
            free -= n

    def act_build(self, kind, x, y, **_):
        t = (int(x), int(y))
        T = self.T
        if kind not in BUILDINGS or kind == "bridge":
            return "invalid building"
        if t not in T.h or t in T.water or t == T.town:
            return "cannot build at (%d,%d)" % t
        if t in self.tiles or any(q[2] == t for q in self.queue):
            return "(%d,%d) is occupied" % t
        place = kind
        if t in T.river:
            if kind != "road":
                return "only a road (bridge) can go on a river tile"
            if t in T.ford and t not in self.roads:
                place = "road"
            else:
                place = "bridge"
        if kind == "mine" and self.tore[t] <= 5:
            return "no ore at (%d,%d)" % t
        if kind == "road" and t in self.roads:
            return "already a road"
        c = BUILDINGS[place]
        if self.gold < c["gold"]:
            return "not enough gold (need %.0f)" % c["gold"]
        if self.stock["wood"] < c["wood"]:
            return "not enough wood (need %.0f)" % c["wood"]
        self.gold -= c["gold"]
        self.stock["wood"] -= c["wood"]
        self.queue.append([place, 1, c["time"], t])
        return "queued %s at (%d,%d), ready in %d turns" % (place, t[0], t[1], c["time"])

    def act_assign(self, farm=None, lumberyard=None, mine=None):
        new = dict(self.work)
        for k, v in (("farm", farm), ("lumberyard", lumberyard), ("mine", mine)):
            if v is not None:
                if v < 0:
                    return "invalid assignment"
                new[k] = int(v)
        if sum(new.values()) > self.workers():
            return "only %d workers available" % self.workers()
        for k in WORK:
            if new[k] > self.slots(k):
                return "%s has %d slots" % (k, self.slots(k))
        self.work = new
        return "assigned %s" % new

    def act_trade(self, good, qty):
        if good not in GOODS or qty == 0:
            return "invalid trade"
        k = self.p["impact"] / self.p["depth"][good]
        p0 = self.price(good)
        sp = self.spread()
        if qty > 0:
            cost = p0 * (1 + sp) * (math.exp(k * qty) - 1) / k
            if cost > self.gold:
                return "not enough gold (need %.0f)" % cost
            self.gold -= cost
            self.stock[good] += qty
            self.shock[good] *= math.exp(k * qty * 0.5)
            return "bought %.1f %s for %.0f gold" % (qty, good, cost)
        q = -qty
        if q > self.stock[good] + 1e-9:
            return "only %.1f %s in stock" % (self.stock[good], good)
        rev = p0 * (1 - sp) * (1 - math.exp(-k * q)) / k
        self.gold += rev
        self.stock[good] -= q
        self.shock[good] *= math.exp(-k * q * 0.5)
        return "sold %.1f %s for %.0f gold" % (q, good, rev)

    def act_tax(self, rate):
        if rate < 0:
            return "invalid tax"
        self.tax = min(rate, self.tax_cap)
        return "tax set to %.2f%s" % (self.tax, " (capped)" if rate > self.tax_cap else "")

    def act_borrow(self, amount):
        if amount <= 0:
            return "invalid amount"
        if self.debt + amount > self.credit_limit():
            return "credit limit is %.0f, debt is %.0f" % (self.credit_limit(), self.debt)
        self.debt += amount
        self.gold += amount
        return "borrowed %.0f" % amount

    def act_repay(self, amount):
        amount = min(amount, self.debt, self.gold)
        if amount <= 0:
            return "nothing to repay"
        self.debt -= amount
        self.gold -= amount
        return "repaid %.0f" % amount

    def end_turn(self):
        p, T = self.p, self.T
        r = self.rng
        self.t += 1
        events = []

        left = []
        for q in self.queue:
            kind, n, rem, t = q
            if rem <= 1:
                if kind in ("road", "bridge"):
                    self.roads.add(t)
                    self._cost = None
                else:
                    self.tiles[t] = kind
                    self.b[kind] += 1
            else:
                left.append([kind, n, rem - 1, t])
        self.queue = left

        for k in WORK:
            self.work[k] = min(self.work[k], self.slots(k))
        total = sum(self.work.values())
        if total > self.workers():
            scale = self.workers() / total
            for k in WORK:
                self.work[k] = int(self.work[k] * scale)

        farm_mult = 0.45 if self.drought > 0 else 1.0
        if self.drought > 0:
            self.drought -= 1
        out = {"food": 0.0, "wood": 0.0, "ore": 0.0}
        staffed = set()
        for kind in WORK:
            left_w = self.work[kind]
            for t in self.ranked(kind, farm_mult):
                if left_w <= 0:
                    break
                n = min(5, left_w)
                left_w -= n
                o = n * self.unit(t, kind, farm_mult)
                if kind == "mine":
                    o = min(o, self.tore[t] * self.deliver(t))
                    self.tore[t] -= o / max(self.deliver(t), 1e-6)
                if kind == "farm":
                    staffed.add(t)
                out[PRODUCES[kind]] += o
        for g in GOODS:
            self.stock[g] += out[g]
        for t, k in self.tiles.items():
            if k == "farm":
                use = 1.0 if t in staffed else 0.0
                self.tfert[t] += p["fert_recover"] * (T.fert0[t] - self.tfert[t]) - p["fert_decay"] * use * self.tfert[t]
                self.tfert[t] = min(max(self.tfert[t], 0.1), T.fert0[t])

        need = self.pop * p["food_per_pop"]
        starving = 0.0
        if self.stock["food"] >= need:
            self.stock["food"] -= need
        else:
            starving = 1 - self.stock["food"] / need
            self.stock["food"] = 0.0
            self.pop *= 1 - 0.12 * starving
            events.append("famine")

        compliance = 0.5 + 0.5 * self.happy
        income = self.pop * p["wage"] * self.tax * compliance
        upkeep = sum(self.b[k] * BUILDINGS[k]["upkeep"] for k in BUILDINGS if k not in ("road", "bridge")) + 0.1 * len(self.roads)
        self.gold += income - upkeep
        self.income_last = income
        if self.gold < 0:
            self.debt += -self.gold * 1.25
            self.gold = 0.0
        self.debt *= 1 + p["interest"]

        target_h = 0.85 - 1.8 * starving - 1.6 * max(self.tax - 0.18, 0) \
            - (0.15 if self.drought > 0 else 0) - (0.1 if self.war > 0 else 0)
        if self.stock["food"] > need * 3:
            target_h += 0.05
        target_h = min(max(target_h, 0.0), 1.0)
        self.happy += 0.3 * (target_h - self.happy)
        self.low_happy = self.low_happy + 1 if self.happy < 0.3 else 0
        if self.low_happy >= 3:
            self.gold *= 0.75
            self.pop *= 0.95
            self.low_happy = 0
            events.append("riot")

        if starving == 0 and self.pop < self.housing():
            self.pop += p["pop_growth"] * self.pop * (1 - self.pop / self.housing()) * (0.5 + self.happy)
        elif self.pop > self.housing():
            self.pop -= 0.05 * (self.pop - self.housing())

        school_target = 1 + p["school_boost"] * self.b["school"] / (self.b["school"] + 3)
        self.edu += 0.08 * (school_target - self.edu)

        if r.random() < p["p_drought"] and self.drought == 0:
            self.drought = r.randint(3, 5)
            events.append("drought")
        if r.random() < p["p_flood"]:
            mag = r.uniform(0.3, 1.0)
            lost = []
            for t, k in list(self.tiles.items()):
                if T.risk[t] * mag > 0.25 and r.random() < 0.7 * (1 - self.protection(t)):
                    del self.tiles[t]
                    self.b[k] -= 1
                    lost.append(k)
            for t in [q for q in self.roads if T.risk[q] * mag > 0.4 and r.random() < 0.4]:
                self.roads.discard(t)
                self._cost = None
            self.stock["food"] *= 1 - 0.3 * mag * (1 - 0.5 * min(1.0, self.b["levee"] * 0.3))
            events.append("flood (lost %d buildings)" % len(lost))
        if r.random() < p["p_plague"]:
            self.pop *= 1 - r.uniform(0.08, 0.18)
            events.append("plague")
        if self.war > 0:
            self.war -= 1
        elif r.random() < p["p_war"]:
            self.war = 6
            events.append("war")

        if self.t % p["election_period"] == 0:
            if self.happy < 0.45 or r.random() < 0.2:
                self.tax_cap = r.uniform(0.1, 0.4)
                self.tariff = r.uniform(0.0, 0.4)
                self.tax = min(self.tax, self.tax_cap)
                events.append("new government: tax cap %.2f, tariff %.2f" % (self.tax_cap, self.tariff))
            else:
                events.append("incumbents re-elected")

        for g in GOODS:
            lr = math.log(self.ref[g]) + p["price_revert"] * (math.log(p["base_price"][g]) - math.log(self.ref[g]))
            lr += r.gauss(0, p["price_vol"])
            lr += math.log(self.season(g, self.t)) - math.log(self.season(g, self.t - 1))
            self.ref[g] = math.exp(lr)
            self.shock[g] = 1 + (self.shock[g] - 1) * 0.7
            if self.war > 0 and g == "ore":
                self.ref[g] *= 1.04
            self.hist[g].append(self.price(g))
            self.hist[g] = self.hist[g][-6:]

        if self.pop < 3:
            self.done, self.outcome = True, "collapse"
        elif self.debt > self.credit_limit() * 1.5 + 50:
            self.done, self.outcome = True, "bankrupt"
        elif self.t >= p["horizon"]:
            self.done, self.outcome = True, "survived"
        self.log.append(events)
        return events, out
