import argparse
import multiprocessing as mp
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


def one(job):
    name, seed, env_split, rollouts = job
    ag = agents([name])[0]
    if isinstance(ag, Lookahead):
        ag.rollouts = rollouts
    env = WorldEnv(seed, env_split)
    play(env, ag)
    w = env.w
    return ag.name, dict(seed=seed, score=round(env.score(), 1), outcome=w.outcome, pop=round(w.pop),
                         gold=round(w.gold), debt=round(w.debt), turns=w.t, roads=len(w.roads))


def run(spec, split, n, rollouts):
    base = SPLITS[split]
    env_split = "ood" if split == "ood" else "train"
    results = {}
    with mp.Pool() as pool:
        for name in spec:
            t0 = time.time()
            jobs = [(name, base + i, env_split, rollouts) for i in range(n)]
            out = pool.map(one, jobs, chunksize=1)
            label = out[0][0]
            rows = [r for _, r in out]
            results[label] = rows
            sc = [r["score"] for r in rows]
            print("%-12s mean %8.1f  median %8.1f  failed %3d/%d  (%.0fs)" % (
                label, st.mean(sc), st.median(sc), sum(r["outcome"] != "survived" for r in rows), n,
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
