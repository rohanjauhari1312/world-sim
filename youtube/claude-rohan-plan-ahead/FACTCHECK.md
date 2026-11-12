# FACTCHECK — Plan Ahead.

Checked against the project's own run artifacts in `world-sim/results/` and the code in `world-sim/worldsim/`. Every number on screen is a measured result from those runs. DOUBLE-CHECK LAW: claims are stated at the strength the evidence supports and no further.

| # | Claim (as narrated or shown) | Verdict | Source | Fix applied |
|---|---|---|---|---|
| 1 | "Every town sits on its own generated land … a new seed gives a different map" | TRUE | `worldsim/terrain.py` builds elevation, river, lakes, forest and ore from the world seed | — |
| 2 | "A ridge with one pass … a river with a few fords … ore only in the hills" | TRUE as a description of the generator | `terrain.py`: ridge bump with a gap, river walk from high ground, `ford` set, ore centers chosen among tiles with height above 0.6 | — |
| 3 | "No strategy can be memorized" | SOFTENED | Worlds differ in terrain, prices, yields, hazards and politics, so a fixed build order cannot be replayed. This is design intent, not a measured result | narration says "so no strategy can be memorized" as the purpose of the randomization; no measured claim is attached |
| 4 | "Goods reach the town along the cheapest path … slopes, forest and unbridged water make a tile expensive" | TRUE | `terrain.py` `step_cost`: 1 + 14 x height change + 0.6 for forest; river tiles blocked unless ford or bridge | — |
| 5 | On screen: "Mine to town: 9 tiles in a straight line", "15 tiles, cost 31.7" | TRUE | Seed 10013, ore tile (9,15), town (7,8): Manhattan distance 9, Dijkstra route 15 steps, cost 31.7 (computed from `Terrain.dijkstra`) | — |
| 6 | "Roads and bridges cost money now and cut the cost of every trip after" | TRUE | `world.py`: road 10 gold + 2 wood, bridge on a river tile 45 gold + 12 wood; road tiles cost 0.3 to cross | — |
| 7 | "Floods hit low ground near the river" | TRUE | `terrain.py` `risk` is highest near the river and low relative to it; `world.py` flood event damages buildings by that risk | — |
| 8 | "A hundred turns, and one score at the end" | TRUE | `horizon` 100; score = gold - debt + stockpile at base prices + population value | — |
| 9 | "On two hundred unseen worlds, never invests 1247" | TRUE | `results/scale_eval_200.json`, `cruise`, mean 1247.4 | — |
| 10 | "One turn ahead 1835; ten turns 2637; forty turns 2847" (also 2409 at 4 turns, 2705 at 20 turns on screen) | TRUE | Same file: greedy 1835.1, lookahead10 2636.6, lookahead40 2847.4, lookahead4 2409.1, lookahead20 2704.8 | spoken as rounded integers |
| 11 | "Far fewer towns collapse" | TRUE | 37 of 200 failed with no investing, 10 of 200 at 40 turns ahead | stated as a count on the verdict card |
| 12 | "Same land, same luck" (seed 10003, 1,027 against 5,496) | TRUE | One run each on seed 10003 with the same world seed for events: cruise 1027, lookahead40 5496. Single world, not a mean | labelled "SEED 10003" on screen; narration says "ten twenty seven against fifty four ninety six" |
| 13 | "A nine billion parameter model … Gemma 2, three worlds, twenty turns, five thirty three" | TRUE | `results/llm_gemma2_9b_terrain/summary.json`: scores 818.0, 450.4, 331.6, mean 533.3 | eyebrow states "SAME 3 WORLDS · 20 TURNS" |
| 14 | Comparators on the Gemma chart: greedy 854, never invests 951, 10 turns ahead 1158, 20 turns ahead 1214 | TRUE (corrected 2026-11-12) | Same seeds 10000-10002, scripted agents run with the horizon set to 20 after the world reset (`horizon_baselines.py 20 3`, `play(..., horizon=20)`). An earlier version of this table used 100-turn scripted scores by mistake because `play()` reset the horizon; that version wrongly showed Gemma above never investing | narration says "a town that never invests scored nine fifty one … a planner looking twenty turns ahead scored twelve fourteen" |
| 15 | "It plans sensibly, then orders buildings it cannot afford" | SUPPORTED, interpretive | Trace counts in `llm_gemma2_9b_terrain`: 31 accepted builds, with rejections led by "not enough wood" (about 43) and occupied tiles | stated as the reading of the traces |
| 16 | "Models pick decent next moves. They plan badly" (B00) | INTERPRETIVE | Motivation for the environment, supported by Gemma scoring below a 20-turn planner. Not a general claim about all models | scoped to "a 9B model" in the evidence beats |
| 17 | Verdict: "Unproven: the 9B result at 100 turns, and that training closes the gap" | TRUE | No 100-turn model run and no training run exist | — |
| 18 | Planners use the true simulator | TRUE | `worldsim/agents.py` `Lookahead` clones the world and rolls it forward | stated as a limit on the verdict card |

## De-sensationalised

- The reel does not claim the model "can't plan". It says the 9B scored below both a planner and a town that never invests, on three worlds at 20 turns.
- The 5,496 against 1,027 comparison is one seed and is labelled that way. The headline claim rests on the 200-world means.
- Planner scores are an upper reference, not what a learned agent can reach.
