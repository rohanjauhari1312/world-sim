import math
import random

GOODS = ("food", "wood", "ore")
WORK = ("farm", "lumberyard", "mine")
BUILDINGS = {
    "farm": dict(gold=25, wood=8, time=2, slots=5, upkeep=1.0),
    "lumberyard": dict(gold=30, wood=0, time=2, slots=5, upkeep=1.0),
    "mine": dict(gold=40, wood=10, time=3, slots=5, upkeep=2.0),
    "house": dict(gold=20, wood=12, time=2, slots=0, upkeep=0.0),
    "school": dict(gold=70, wood=18, time=5, slots=0, upkeep=3.0),
    "levee": dict(gold=55, wood=25, time=4, slots=0, upkeep=1.0),
}
PRODUCES = {"farm": "food", "lumberyard": "wood", "mine": "ore"}
ARCHETYPES = {
    "river valley": dict(farm=1.25, wood=1.0, ore=0.8, flood=1.8, drought=0.7, depth=1.2),
    "arid steppe": dict(farm=0.8, wood=0.7, ore=1.2, flood=0.3, drought=1.8, depth=1.0),
    "forest coast": dict(farm=1.0, wood=1.4, ore=0.9, flood=1.2, drought=0.8, depth=1.5),
    "mountain hold": dict(farm=0.75, wood=1.0, ore=1.5, flood=0.5, drought=1.0, depth=0.8),
}
ACTION_BUDGET = 12


def make_params(seed, split="train"):
    r = random.Random("params-%s-%s" % (seed, split))
    arch_name = r.choice(sorted(ARCHETYPES))
    a = ARCHETYPES[arch_name]
    stress = 1.0 if split == "train" else 1.6
    base_price = {
        "food": r.uniform(2.4, 3.8),
        "wood": r.uniform(3.0, 5.0),
        "ore": r.uniform(7.0, 12.0),
    }
    return dict(
        seed=seed,
        split=split,
        archetype=arch_name,
        horizon=100,
        food_per_pop=r.uniform(0.4, 0.6),
        yield_={"farm": 1.7 * a["farm"] * r.uniform(0.9, 1.1),
                "lumberyard": 1.1 * a["wood"] * r.uniform(0.9, 1.1),
                "mine": 0.85 * a["ore"] * r.uniform(0.9, 1.1)},
        ore_reserve=r.uniform(120, 350) * (0.6 if split != "train" else 1.0),
        fert_decay=r.uniform(0.006, 0.02) * (1.3 if split != "train" else 1.0),
        fert_recover=0.01,
        base_price=base_price,
        price_vol=r.uniform(0.03, 0.09) * stress,
        price_revert=r.uniform(0.06, 0.12),
        season_amp=r.uniform(0.08, 0.25),
        season_len=r.choice([12, 16, 20, 24]),
        season_phase={g: r.uniform(0, 2 * math.pi) for g in GOODS},
        depth={"food": 80 * a["depth"], "wood": 60 * a["depth"], "ore": 40 * a["depth"]},
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
        p_drought=r.uniform(0.02, 0.05) * a["drought"] * stress,
        p_flood=r.uniform(0.015, 0.04) * a["flood"] * stress,
        p_plague=r.uniform(0.01, 0.03) * stress,
        p_war=r.uniform(0.01, 0.03) * stress,
        start_gold=r.uniform(90, 160),
        start_pop=r.randint(26, 34),
    )


class World:
    def __init__(self, params, rng_seed=None):
        self.p = params
        self.rng = random.Random(params["seed"] * 7919 + 13 if rng_seed is None else rng_seed)
        p = params
        self.t = 0
        self.pop = float(p["start_pop"])
        self.gold = p["start_gold"]
        self.debt = 0.0
        self.stock = {"food": 30.0, "wood": 45.0, "ore": 0.0}
        self.b = {"farm": 2, "lumberyard": 1, "mine": 1, "house": 3, "school": 0, "levee": 0}
        self.queue = []
        self.work = {"farm": 0, "lumberyard": 0, "mine": 0}
        self.fert = 1.0
        self.reserve = p["ore_reserve"]
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
        self.assign_default()

    def clone(self, rng_seed):
        w = World.__new__(World)
        w.p = self.p
        w.rng = random.Random(rng_seed)
        for k in ("t", "pop", "gold", "debt", "fert", "reserve", "edu", "happy", "tax", "tax_cap",
                  "tariff", "drought", "war", "low_happy", "income_last", "done", "outcome"):
            setattr(w, k, getattr(self, k))
        w.stock = dict(self.stock)
        w.b = dict(self.b)
        w.queue = list(self.queue)
        w.work = dict(self.work)
        w.ref = dict(self.ref)
        w.shock = dict(self.shock)
        w.hist = {g: list(v) for g, v in self.hist.items()}
        w.log = []
        return w

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

    def prot(self):
        return 1 - math.exp(-0.45 * self.b["levee"])

    def net_worth(self):
        stock_val = sum(self.stock[g] * self.p["base_price"][g] for g in GOODS)
        return self.gold - self.debt + stock_val

    def score(self):
        s = self.net_worth() + 8 * self.pop * (0.5 + 0.5 * self.happy)
        return s - 500 if self.outcome in ("collapse", "bankrupt") else s

    def assign_default(self):
        free = self.workers()
        for k in WORK:
            n = min(self.slots(k), free)
            self.work[k] = n
            free -= n

    def eff_work(self, kind):
        return min(self.work[kind], self.slots(kind))

    def act_build(self, kind, n):
        if kind not in BUILDINGS or n < 1:
            return "invalid build"
        c = BUILDINGS[kind]
        g, w = c["gold"] * n, c["wood"] * n
        if self.gold < g:
            return "not enough gold (need %.0f)" % g
        if self.stock["wood"] < w:
            return "not enough wood (need %.0f)" % w
        self.gold -= g
        self.stock["wood"] -= w
        self.queue.append([kind, n, c["time"]])
        return "queued %d %s, ready in %d turns" % (n, kind, c["time"])

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
        p = self.p
        r = self.rng
        self.t += 1
        events = []

        left = []
        for kind, n, rem in self.queue:
            if rem <= 1:
                self.b[kind] += n
            else:
                left.append([kind, n, rem - 1])
        self.queue = left

        for k in WORK:
            self.work[k] = min(self.work[k], self.slots(k))
        total = sum(self.work.values())
        if total > self.workers():
            scale = self.workers() / total
            for k in WORK:
                self.work[k] = int(self.work[k] * scale)

        farm_mult = 1.0
        if self.drought > 0:
            farm_mult = 0.45
            self.drought -= 1
        out = {}
        for k in WORK:
            n = self.eff_work(k)
            o = n * p["yield_"][k] * self.edu
            if k == "farm":
                o *= self.fert * farm_mult
            if k == "mine":
                o = min(o, self.reserve)
                self.reserve -= o
            out[PRODUCES[k]] = o
            self.stock[PRODUCES[k]] += o

        use = self.eff_work("farm") / max(self.slots("farm"), 1)
        self.fert += p["fert_recover"] * (1 - self.fert) - p["fert_decay"] * use * self.fert
        self.fert = min(max(self.fert, 0.15), 1.0)

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
        upkeep = sum(self.b[k] * BUILDINGS[k]["upkeep"] for k in BUILDINGS)
        self.gold += income - upkeep
        self.income_last = income
        if self.gold < 0:
            self.debt += -self.gold * 1.25
            self.gold = 0.0
        self.debt *= 1 + p["interest"]

        target_h = 0.85 - 0.9 * starving * 2 - 1.6 * max(self.tax - 0.18, 0) \
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
            growth = p["pop_growth"] * self.pop * (1 - self.pop / self.housing()) * (0.5 + self.happy)
            self.pop += growth
        elif self.pop > self.housing():
            self.pop -= 0.05 * (self.pop - self.housing())

        school_target = 1 + p["school_boost"] * self.b["school"] / (self.b["school"] + 3)
        self.edu += 0.08 * (school_target - self.edu)

        if r.random() < p["p_drought"] and self.drought == 0:
            self.drought = r.randint(3, 5)
            events.append("drought")
        if r.random() < p["p_flood"]:
            prot = self.prot()
            self.stock["food"] *= 1 - 0.5 * (1 - prot)
            if r.random() < 0.6 * (1 - prot):
                kind = r.choice(["farm", "house", "lumberyard", "mine"])
                if self.b[kind] > 0:
                    self.b[kind] -= 1
            events.append("flood")
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
