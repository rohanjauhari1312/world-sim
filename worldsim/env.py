from .terrain import N
from .world import ACTION_BUDGET, BUILDINGS, GOODS, World, make_params

TOOLS = [
    {"name": "build", "args": {"building": "farm|lumberyard|mine|house|school|levee|road", "x": "int", "y": "int"}},
    {"name": "assign_workers", "args": {"farm": "int", "lumberyard": "int", "mine": "int"}},
    {"name": "trade", "args": {"good": "food|wood|ore", "quantity": "float, positive buys, negative sells"}},
    {"name": "set_tax", "args": {"rate": "float 0-1"}},
    {"name": "borrow", "args": {"amount": "float"}},
    {"name": "repay", "args": {"amount": "float"}},
    {"name": "end_turn", "args": {}},
]


class WorldEnv:
    def __init__(self, seed, split="train"):
        self.seed = seed
        self.split = split
        self.reset()

    def reset(self):
        self.w = World(make_params(self.seed, self.split))
        self.actions_left = ACTION_BUDGET
        self.last_events = []
        return self.observe()

    @property
    def done(self):
        return self.w.done

    def score(self):
        return self.w.score()

    def call(self, name, **a):
        w = self.w
        if w.done:
            return "episode over"
        if name == "end_turn":
            return self._end()
        if self.actions_left <= 0:
            return self._end(prefix="action budget used up, turn ended. ")
        self.actions_left -= 1
        try:
            if name == "build":
                return w.act_build(a["building"], int(a["x"]), int(a["y"]))
            if name == "assign_workers":
                return w.act_assign(**{k: a[k] for k in ("farm", "lumberyard", "mine") if k in a})
            if name == "trade":
                return w.act_trade(a["good"], float(a["quantity"]))
            if name == "set_tax":
                return w.act_tax(float(a["rate"]))
            if name == "borrow":
                return w.act_borrow(float(a["amount"]))
            if name == "repay":
                return w.act_repay(float(a["amount"]))
        except (KeyError, TypeError, ValueError):
            return "bad arguments for %s" % name
        return "unknown tool %s" % name

    def _end(self, prefix=""):
        self.last_events, out = self.w.end_turn()
        self.actions_left = ACTION_BUDGET
        ev = ", ".join(self.last_events) or "none"
        return "%sturn %d done. produced food %.0f wood %.0f ore %.0f. events: %s" % (
            prefix, self.w.t, out["food"], out["wood"], out["ore"], ev)

    def observe(self):
        w = self.w
        p = w.p
        lines = [
            "Turn %d of %d. Town at (%d,%d)." % (w.t, p["horizon"], w.T.town[0], w.T.town[1]),
            "Population %.0f (workers %d, housing %d). Happiness %.2f. Average farm fertility %.2f. Education x%.2f."
            % (w.pop, w.workers(), w.housing(), w.happy, w.fert(), w.edu),
            "Gold %.0f. Debt %.0f (interest %.1f%% per turn, credit limit %.0f)."
            % (w.gold, w.debt, p["interest"] * 100, w.credit_limit()),
            "Stock: food %.0f, wood %.0f, ore %.0f. Ore left in ground: %.0f." % (
                w.stock["food"], w.stock["wood"], w.stock["ore"], w.reserve()),
            "Food eaten per turn: %.0f." % (w.pop * p["food_per_pop"]),
            "Buildings: " + ", ".join("%s %d" % (k, w.b[k]) for k in BUILDINGS if k not in ("road", "bridge"))
            + ", road tiles %d" % len(w.roads),
            "Under construction: " + (", ".join("%s (%d,%d) %dt" % (k, t[0], t[1], r) for k, n, r, t in w.queue) or "nothing"),
            "Workers assigned: " + ", ".join("%s %d/%d" % (k, w.work[k], w.slots(k)) for k in w.work),
            "Tax rate %.2f (cap %.2f). Tariff %.2f. Trade spread %.0f%%. Next election turn %d."
            % (w.tax, w.tax_cap, w.tariff, w.spread() * 100,
               (w.t // p["election_period"] + 1) * p["election_period"]),
        ]
        for g in GOODS:
            lines.append("Price %s: %.2f (last turns: %s)" % (
                g, w.price(g), ", ".join("%.1f" % x for x in w.hist[g][-5:])))
        flags = []
        if w.drought > 0:
            flags.append("drought (%d turns left)" % w.drought)
        if w.war > 0:
            flags.append("war, trade costs high (%d turns left)" % w.war)
        lines.append("Active: " + (", ".join(flags) or "nothing"))
        if self.last_events:
            lines.append("Last turn: " + ", ".join(self.last_events))
        lines.append(ascii_map(w))
        lines.append("Delivery: share of output that reaches town. Best free sites (x,y):")
        for k in ("farm", "lumberyard", "mine", "house", "levee"):
            lines.append("  %s: " % k + "; ".join("(%d,%d) delivers %.0f%% fert %.2f ore %.0f flood %.1f" % (
                t[0], t[1], w.deliver(t) * 100, w.T.fert0[t], w.tore[t], w.T.risk[t]) for t in w.sites(k, 3)))
        lines.append("Costs: " + "; ".join(
            "%s %dg+%dw %dt" % (k, c["gold"], c["wood"], c["time"]) for k, c in BUILDINGS.items() if k != "bridge")
            + "; a road on a river tile becomes a bridge (45g+12w 3t)")
        lines.append("Actions left this turn: %d." % self.actions_left)
        return "\n".join(lines)


GLYPH = {"farm": "F", "lumberyard": "L", "mine": "M", "house": "H", "school": "S", "levee": "V"}


def ascii_map(w):
    T = w.T
    rows = ["Map (x across, y down). @ town, ~ water, = river, : ford, + road, # bridge, ^ high ground, "
            "t forest, o ore, . plain; F farm L lumber M mine H house S school V levee",
            "    " + "".join("%x" % x for x in range(N))]
    for y in range(N):
        row = ""
        for x in range(N):
            t = (x, y)
            if t == T.town:
                c = "@"
            elif t in w.tiles:
                c = GLYPH[w.tiles[t]]
            elif t in w.roads:
                c = "#" if t in T.river else "+"
            elif t in T.water:
                c = "~"
            elif t in T.river:
                c = ":" if t in T.ford else "="
            elif T.ore0[t] > 5:
                c = "o"
            elif T.forest[t] > 0.5:
                c = "t"
            elif T.h[t] > 0.7:
                c = "^"
            else:
                c = "."
            row += c
        rows.append("%2x  " % y + row)
    return "\n".join(rows)
