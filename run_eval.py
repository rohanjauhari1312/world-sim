import argparse
import json
import statistics as st
import time

from worldsim.agents import Cruise, Lookahead, Random, play
from worldsim.env import WorldEnv

SPLITS = {"train": 0, "eval": 10000, "ood": 20000}


def agents(spec):
    out = []
    for name in spec:
        if name == "random":
            out.append(Random())
        elif name == "cruise":
            out.append(Cruise())
        else:
            out.append(Lookahead(int(name)))
    return out


def run(spec, split, n, rollouts):
    base = SPLITS[split]
    env_split = "ood" if split == "ood" else "train"
    results = {}
    for ag in agents(spec):
        if isinstance(ag, Lookahead):
            ag.rollouts = rollouts
        rows = []
        t0 = time.time()
        for i in range(n):
            env = WorldEnv(base + i, env_split)
            play(env, ag)
            w = env.w
            rows.append(dict(seed=base + i, score=round(env.score(), 1), outcome=w.outcome,
                             pop=round(w.pop), gold=round(w.gold), debt=round(w.debt), turns=w.t,
                             region=w.p["archetype"]))
        results[ag.name] = rows
        sc = [r["score"] for r in rows]
        print("%-12s mean %8.1f  median %8.1f  failed %2d/%d  (%.0fs)" % (
            ag.name, st.mean(sc), st.median(sc), sum(r["outcome"] != "survived" for r in rows), n,
            time.time() - t0), flush=True)
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--agents", default="random,cruise,1,4,10,20,40")
    ap.add_argument("--split", default="eval", choices=list(SPLITS))
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--rollouts", type=int, default=3)
    ap.add_argument("--out")
    a = ap.parse_args()
    res = run(a.agents.split(","), a.split, a.n, a.rollouts)
    if a.out:
        with open(a.out, "w") as f:
            json.dump(res, f, indent=1)
