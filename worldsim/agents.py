import math
import random

from .world import GOODS, PRODUCES, WORK


def cruise(w, tax=0.2):
    """Housekeeping policy with no investing: feed people, sell surplus, repay debt."""
    p = w.p
    w.act_tax(tax)
    need = w.pop * p["food_per_pop"]
    farm_out = max(p["yield_"]["farm"] * w.fert * w.edu, 1e-6)
    want_farm = min(w.slots("farm"), math.ceil(need * 1.15 / farm_out))
    free = w.workers()
    alloc = {"farm": min(want_farm, free)}
    free -= alloc["farm"]
    rest = sorted(("lumberyard", "mine"), key=lambda k: -p["yield_"][k] * w.ref[PRODUCES[k]] * (w.reserve > 1 or k != "mine"))
    for k in rest:
        alloc[k] = min(w.slots(k), free)
        free -= alloc[k]
    w.work = {k: alloc.get(k, 0) for k in WORK}

    stock = w.stock
    if stock["food"] < need * 3 and w.gold > 20:
        q = min(need * 4 - stock["food"], w.gold / (w.price("food") * 1.2))
        if q > 1:
            w.act_trade("food", q)
    elif stock["food"] > need * 9:
        w.act_trade("food", -(stock["food"] - need * 6))
    if stock["ore"] > 1:
        w.act_trade("ore", -min(stock["ore"], p["depth"]["ore"] * 0.6))
    if stock["wood"] > 60:
        w.act_trade("wood", -min(stock["wood"] - 40, p["depth"]["wood"] * 0.5))
    if w.debt > 0 and w.gold > 45:
        w.act_repay(w.gold - 40)


class Cruise:
    name = "cruise"

    def __init__(self, tax=0.2):
        self.tax = tax

    def act(self, env):
        cruise(env.w, self.tax)


class Random:
    name = "random"

    def __init__(self, seed=0):
        self.r = random.Random(seed)

    def act(self, env):
        w, r = env.w, self.r
        for _ in range(r.randint(0, 4)):
            c = r.choice(["build", "assign", "trade", "tax", "borrow", "repay"])
            if c == "build":
                w.act_build(r.choice(["farm", "lumberyard", "mine", "house", "school", "levee"]), 1)
            elif c == "assign":
                n = w.workers()
                a = r.randint(0, n)
                b = r.randint(0, n - a)
                w.act_assign(farm=min(a, w.slots("farm")), lumberyard=min(b, w.slots("lumberyard")),
                             mine=min(n - a - b, w.slots("mine")))
            elif c == "trade":
                w.act_trade(r.choice(GOODS), r.uniform(-20, 20))
            elif c == "tax":
                w.act_tax(r.uniform(0, 0.5))
            elif c == "borrow":
                w.act_borrow(r.uniform(10, 80))
            else:
                w.act_repay(r.uniform(10, 80))


BUILD_OPTIONS = [None, ("farm", 1), ("lumberyard", 1), ("mine", 1), ("house", 1), ("house", 2),
                 ("school", 1), ("levee", 1)]


def macro(w, build, tax):
    if build:
        w.act_build(*build)
    cruise(w, tax)


class Lookahead:
    """Model-based planner with the true dynamics: tries each build option, then rolls the
    cruise policy forward `depth` turns on re-sampled futures. depth=1 is the greedy agent."""

    def __init__(self, depth, rollouts=3, taxes=(0.12, 0.2, 0.3)):
        self.depth = depth
        self.rollouts = rollouts
        self.taxes = taxes
        self.name = "greedy" if depth == 1 else "lookahead%d" % depth

    def value(self, w, build, tax, seeds):
        total = 0.0
        for s in seeds:
            c = w.clone(s)
            macro(c, build, tax)
            c.end_turn()
            for _ in range(min(self.depth, c.p["horizon"] - w.t) - 1):
                if c.done:
                    break
                cruise(c, tax)
                c.end_turn()
            total += c.score()
        return total / len(seeds)

    def act(self, env):
        w = env.w
        seeds = [w.t * 1000 + i for i in range(self.rollouts)]
        cands = [(b, 0.2) for b in BUILD_OPTIONS] + [(None, t) for t in self.taxes if t != 0.2]
        best = max(cands, key=lambda c: self.value(w, c[0], c[1], seeds))
        macro(w, *best)


def play(env, agent, max_turns=500):
    env.reset()
    for _ in range(max_turns):
        if env.done:
            break
        agent.act(env)
        env.call("end_turn")
    return env
