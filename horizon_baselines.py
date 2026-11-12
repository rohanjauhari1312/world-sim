import json
import statistics as st
import sys

from worldsim.agents import Cruise, Lookahead, play
from worldsim.env import WorldEnv

H, N = int(sys.argv[1]), int(sys.argv[2])
out = {}
for ag in (Cruise(), Lookahead(1), Lookahead(10), Lookahead(20)):
    sc = []
    for s in range(10000, 10000 + N):
        e = WorldEnv(s)
        play(e, ag, horizon=H)
        sc.append(round(e.score()))
    out[ag.name] = sc
    print(ag.name, sc, round(st.mean(sc)), flush=True)
json.dump(out, open("results/horizon%d_baselines.json" % H, "w"))
