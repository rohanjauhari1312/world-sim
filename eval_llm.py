import argparse
import json
import os
import re
import statistics as st

from mlx_lm import generate, load
from mlx_lm.sample_utils import make_sampler

from worldsim.env import TOOLS, WorldEnv

SYSTEM = """You run a small settlement for 100 turns. Each turn you may use up to 12 tool calls, then the turn ends and the world updates: workers produce, people eat, taxes come in, prices drift, hazards and elections happen.

Final score = gold - debt + stockpile value + population value. Buildings do not count by themselves, they only pay off through what they produce or protect. Construction takes several turns. Where you build matters: use the map and the site list. Output only reaches town in proportion to the delivery share, which depends on the path to town (hills and unbridged rivers are costly, roads are cheap), and tiles near the river can flood. Think ahead: population only grows if there is housing and spare food, and some investments take 15+ turns to pay back.

Tools (JSON objects):
%s

Reply with one JSON object only, using exactly one value per field. Example:
{"plan": "more housing so the population can grow", "actions": [{"tool": "build", "building": "house", "x": 7, "y": 9}, {"tool": "assign_workers", "farm": 8, "lumberyard": 5, "mine": 3}, {"tool": "trade", "good": "ore", "quantity": -10}, {"tool": "set_tax", "rate": 0.2}, {"tool": "end_turn"}]}
End the list with {"tool": "end_turn"}.""" % "\n".join(
    "- %s %s" % (t["name"], json.dumps(t["args"])) for t in TOOLS)


def parse(text):
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def run_episode(model, tok, sampler, seed, split, horizon, max_tokens, trace_path):
    env = WorldEnv(seed, split)
    env.w.p["horizon"] = horizon
    memory = []
    bad = 0
    with open(trace_path, "w") as tf:
        while not env.done:
            obs = env.observe()
            user = obs
            if memory:
                user = "Recent turns:\n" + "\n".join(memory[-3:]) + "\n\nNow:\n" + obs
            prompt = tok.apply_chat_template(
                [{"role": "user", "content": SYSTEM + "\n\n" + user}],
                add_generation_prompt=True, tokenize=False)
            out = generate(model, tok, prompt=prompt, max_tokens=max_tokens, sampler=sampler)
            msg = parse(out)
            results = []
            if msg is None or not isinstance(msg.get("actions"), list):
                bad += 1
                results.append("unparseable reply")
                env.call("end_turn")
            else:
                ended = False
                for act in msg["actions"]:
                    if not isinstance(act, dict) or "tool" not in act:
                        results.append("malformed action")
                        continue
                    args = {k: v for k, v in act.items() if k != "tool"}
                    results.append("%s: %s" % (act["tool"], env.call(act["tool"], **args)))
                    if act["tool"] == "end_turn":
                        ended = True
                        break
                if not ended:
                    env.call("end_turn")
            memory.append("turn %d: %s" % (env.w.t, " | ".join(results)[:300]))
            tf.write(json.dumps(dict(turn=env.w.t, obs=obs, reply=out, results=results,
                                     score=round(env.score(), 1))) + "\n")
    w = env.w
    return dict(seed=seed, score=round(env.score(), 1), outcome=w.outcome, turns=w.t,
                pop=round(w.pop), bad_replies=bad)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--adapter")
    ap.add_argument("--split", default="eval")
    ap.add_argument("--seed0", type=int, default=10000)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--horizon", type=int, default=100)
    ap.add_argument("--max-tokens", type=int, default=400)
    ap.add_argument("--out", default="results/llm")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    model, tok = load(a.model, adapter_path=a.adapter)
    sampler = make_sampler(temp=0.0)
    rows = []
    for i in range(a.n):
        r = run_episode(model, tok, sampler, a.seed0 + i, "ood" if a.split == "ood" else "train",
                        a.horizon, a.max_tokens, os.path.join(a.out, "trace_%d.jsonl" % (a.seed0 + i)))
        rows.append(r)
        print(r, flush=True)
        with open(os.path.join(a.out, "summary.json"), "w") as f:
            json.dump(rows, f, indent=1)
    print("mean score %.1f, failed %d/%d" % (st.mean(r["score"] for r in rows),
                                              sum(r["outcome"] not in ("survived",) for r in rows), len(rows)))
