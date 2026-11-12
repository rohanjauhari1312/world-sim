import argparse
import json
import multiprocessing as mp
import os

from worldsim.agents import Lookahead
from worldsim.env import WorldEnv
from worldsim.prompt import SYSTEM

TOOL_OF = {"act_build": "build", "act_trade": "trade", "act_tax": "set_tax", "act_borrow": "borrow", "act_repay": "repay"}


def instrument(w, rec):
    for name in TOOL_OF:
        f = getattr(w, name)

        def g(*a, _f=f, _n=name, _tax=w.tax, **k):
            before = w.tax
            r = _f(*a, **k)
            rec.append((_n, a, r, before))
            return r
        setattr(w, name, g)


def to_actions(rec, work_before, work_after):
    acts = []
    for name, a, r, tax_before in rec:
        if name == "act_build" and r.startswith("queued"):
            acts.append({"tool": "build", "building": a[0], "x": int(a[1]), "y": int(a[2])})
        elif name == "act_trade" and (r.startswith("bought") or r.startswith("sold")):
            acts.append({"tool": "trade", "good": a[0], "quantity": round(a[1], 1)})
        elif name == "act_tax" and not r.startswith("invalid"):
            rate = round(float(r.split()[3]), 2)
            if abs(rate - tax_before) > 1e-9:
                acts.append({"tool": "set_tax", "rate": rate})
        elif name == "act_borrow" and r.startswith("borrowed"):
            acts.append({"tool": "borrow", "amount": round(a[0], 0)})
        elif name == "act_repay" and r.startswith("repaid"):
            acts.append({"tool": "repay", "amount": round(float(r.split()[1]), 0)})
    if work_after != work_before:
        i = next((n for n, x in enumerate(acts) if x["tool"] != "build"), len(acts))
        acts.insert(i, {"tool": "assign_workers", **{k: int(v) for k, v in work_after.items()}})
    return acts


def plan_text(acts):
    b = [a for a in acts if a["tool"] == "build"]
    inv = [a for a in b if a["building"] != "road"]
    if inv:
        return "Invest: build %s at (%d,%d)." % (inv[0]["building"], inv[0]["x"], inv[0]["y"])
    if b:
        return "Lay %d road tiles to cut transport cost." % len(b)
    return "No new build. Feed the town and sell surplus."


def episode(job):
    seed, depth = job
    env = WorldEnv(seed, "train")
    ag = Lookahead(depth)
    rows = []
    while not env.done:
        obs = env.observe()
        w = env.w
        rec = []
        instrument(w, rec)
        before = dict(w.work)
        ag.act(env)
        acts = to_actions(rec, before, dict(w.work))
        for name in TOOL_OF:
            delattr(w, name)
        acts.append({"tool": "end_turn"})
        rows.append({"messages": [{"role": "user", "content": SYSTEM + "\n\n" + obs},
                                  {"role": "assistant", "content": json.dumps({"plan": plan_text(acts), "actions": acts})}],
                     "built": any(a["tool"] == "build" for a in acts)})
        env.call("end_turn")
    return dict(seed=seed, score=env.score(), outcome=env.w.outcome, rows=rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--depth", type=int, default=20)
    ap.add_argument("--out", default="data/planner_traces.jsonl")
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with mp.Pool() as pool, open(a.out, "w") as f:
        for i, ep in enumerate(pool.imap_unordered(episode, [(s, a.depth) for s in range(a.n)])):
            f.write(json.dumps(ep) + "\n")
            f.flush()
            print(i + 1, ep["seed"], round(ep["score"]), ep["outcome"], flush=True)
