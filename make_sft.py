import json
import random
import statistics as st

rows = [json.loads(l) for l in open("data/planner_traces.jsonl")]
ok = [e for e in rows if e["outcome"] == "survived"]
cut = st.median(e["score"] for e in ok)
good = [e for e in ok if e["score"] >= cut]
print("episodes", len(rows), "survived", len(ok), "kept (score >= median %.0f)" % cut, len(good))
built = [r for e in good for r in e["rows"] if r["built"]]
hold = [r for e in good for r in e["rows"] if not r["built"]]
rng = random.Random(0)
rng.shuffle(built)
rng.shuffle(hold)
n_b = min(len(built), 1400)
pick = built[:n_b] + hold[: int(n_b * 0.9)]
rng.shuffle(pick)
print("build turns", len(built), "hold turns", len(hold), "-> train rows", len(pick))
valid, train = pick[:100], pick[100:]
import os
os.makedirs("data/sft", exist_ok=True)
for name, rs in (("train", train), ("valid", valid)):
    with open("data/sft/%s.jsonl" % name, "w") as f:
        for r in rs:
            f.write(json.dumps({"messages": r["messages"]}) + "\n")
