from .world import ACTION_BUDGET, BUILDINGS, GOODS, World, make_params

TOOLS = [
    {"name": "build", "args": {"building": "farm|lumberyard|mine|house|school|levee", "count": "int"}},
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
                return w.act_build(a["building"], int(a.get("count", 1)))
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
            "Turn %d of %d. Region: %s." % (w.t, p["horizon"], p["archetype"]),
            "Population %.0f (workers %d, housing %d). Happiness %.2f. Soil fertility %.2f. Education x%.2f."
            % (w.pop, w.workers(), w.housing(), w.happy, w.fert, w.edu),
            "Gold %.0f. Debt %.0f (interest %.1f%% per turn, credit limit %.0f)."
            % (w.gold, w.debt, p["interest"] * 100, w.credit_limit()),
            "Stock: food %.0f, wood %.0f, ore %.0f. Ore left in ground: %.0f." % (
                w.stock["food"], w.stock["wood"], w.stock["ore"], w.reserve),
            "Food eaten per turn: %.0f." % (w.pop * p["food_per_pop"]),
            "Buildings: " + ", ".join("%s %d" % (k, v) for k, v in w.b.items()),
            "Under construction: " + (", ".join("%d %s (%d turns)" % (n, k, r) for k, n, r in w.queue) or "nothing"),
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
        lines.append("Costs: " + "; ".join(
            "%s %dg+%dw %dt" % (k, c["gold"], c["wood"], c["time"]) for k, c in BUILDINGS.items()))
        lines.append("Actions left this turn: %d." % self.actions_left)
        return "\n".join(lines)
