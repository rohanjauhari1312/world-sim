# World Sim

A settlement-management game on irregular terrain, for training long-horizon planning and economic reasoning. The agent calls tools (build at x,y, assign_workers, trade, set_tax, borrow, repay, end_turn). Score after 100 turns is gold - debt + stockpile + population value. Buildings only count through what they produce.

## Why this environment

Current models choose reasonable next moves but plan poorly. Here the payoff from a house, school, road or levee shows up 10 to 40 turns later, and every world has different rules, terrain and hazards, so a strategy cannot be memorized. The model has to read the map, work out how the economy responds, and plan around delayed returns. The score is the long-run outcome, so greedy play is punished.

## Terrain

Every world is a 16x16 map generated from a seed: noisy elevation with a ridge that has a pass in it, a river that winds downhill from the highlands with a few fords, lakes, forests, and ore deposits in the hills. Nothing is on a grid template, and no two worlds look alike.

Where you build matters:

- Output reaches the town in proportion to a delivery share set by the cheapest path to the town. Slopes, forest and unbridged rivers make a tile expensive to cross, so the obvious straight line is often not the cheapest route. A tile across the ridge may be best reached through the pass, or by paying for a bridge.
- Roads cut the cost of a path. A road on a river tile becomes a bridge. Roads are an investment that pays back slowly.
- Farm soil wears out tile by tile. Ore runs out tile by tile.
- Tiles close to the river and low relative to it flood. Levees protect buildings within 3 tiles.

The economy on top: prices respond to the agent's own trades and to local scarcity, population needs food and housing, debt accrues interest, elections change tax caps and tariffs, and droughts, floods, plague and war hit at random. Hard `ood` worlds use rougher terrain, higher interest, more hazards and faster soil wear than anything in `train`.

## Run

    python run_eval.py --split eval --n 200         # baselines on 200 worlds, parallel
    python demo.py 10003                            # animated terrain replay, cruise vs lookahead40
    python eval_llm.py --model <mlx model> --n 20   # LLM agent, saves full per-turn traces

## Baselines at scale

`Lookahead(k)` tries candidate builds and road routes (including a bridged route and the cheapest existing route to its worst-served producers), then rolls a no-investment policy forward k turns on resampled futures. k=1 is greedy. Same simulator and candidates for every k, so only the planning depth changes.

Mean score, 100 turns. eval is 200 unseen worlds, ood is 100 harder ones:

| agent | eval | ood |
|---|---|---|
| random | -131 | - |
| cruise (no investing) | 1247 | 850 |
| greedy (1 turn) | 1835 | 1334 |
| lookahead 4 | 2409 | - |
| lookahead 10 | 2637 | 2039 |
| lookahead 20 | 2705 | - |
| lookahead 40 | 2847 | 2159 |

Failed towns (collapse or bankruptcy) out of 200 on eval: cruise 37, greedy 36, lookahead 10 17, lookahead 40 10.

## LLM run

Gemma-2-9B-it (4-bit), 3 unseen terrain worlds (seeds 10000-10002), 20 turns each, traces in `results/llm_gemma2_9b_terrain/`. Mean score 533 (818, 450, 332). Scripted agents on the same worlds at the same 20-turn horizon (`horizon_baselines.py 20 3`): never invests 951, greedy 854, looks 10 turns ahead 1158, looks 20 turns ahead 1214. So the 9B scored below every scripted agent, including the one that never invests, on all three worlds.

Correction (2026-11-12): an earlier version of this section compared the 9B's 20-turn scores with the scripted agents' 100-turn scores (a bug in `play()`, which reset the horizon). That version wrongly said the 9B beat the no-investing and greedy agents. The numbers above are the matched ones.

What the traces show: the model places roads and buildings, but it orders builds it cannot afford (wood is the usual shortfall), puts buildings on tiles that are already taken, and tries to build on water and the town tile. Earlier flat-map runs (3 worlds, 20 turns) are in `results/llm_gemma2_9b/` and `results/llm_qwen0p5b_v2/`.

Small sample. A 100-turn run on many worlds is the next step, and needs a faster inference setup than a single laptop.

## Training on planner traces (in progress)

`collect_traces.py` replays the 20-turn planner over 200 train worlds and saves each turn as (observation, tool-call JSON), `make_sft.py` keeps the top half of surviving runs and builds 1,149 examples, and a LoRA fine-tune of Qwen2.5-0.5B-4bit on them ran to iteration 450 of 600 (validation loss 1.42 at iteration 1, 0.46 at 200, 0.30 at 400; log in `results/sft_qwen05.log`). The tuned model has not been evaluated yet, so there is no claim about behaviour. The untuned 0.5B base returned unusable replies on 28 of 40 turns on its first world (`results/llm_qwen05_base_h40/`). `results/world_sim_summary.png` summarizes everything above.

## Limits and next steps

- The 9B result is 3 worlds at 20 turns. It shows the model plays below a planner, not by how much at the full 100 turns.
- The planners use the true simulator. They show how much room there is above the model, not what a learned agent can reach.
- The planner's road candidates are simple (cheapest existing route and a bridged route). Gains flatten between 20 and 40 turns of lookahead, so better route search could lift the ceiling.
- No unit tests yet.
- Next: a 100-turn run on 20+ worlds with a faster inference setup, then training on traces from the planners and checking whether a trained model beats greedy play on unseen worlds.
