# World Sim

A settlement-management game for training long-horizon planning and economic reasoning. The agent calls tools (build, assign_workers, trade, set_tax, borrow, repay, end_turn). The economy reacts: prices respond to the agent's own trades and to local scarcity, population needs food and housing, soil wears out, ore runs out, debt accrues interest, elections change tax caps and tariffs, and droughts, floods, plague and war hit at random. Score after 100 turns is gold - debt + stockpile + population value. Buildings only count through what they produce.

Every world is generated from a seed (region type, yields, prices, volatility, interest, hazard rates, politics). `ood` worlds use harsher parameters than anything in `train`.

## Run

    python run_eval.py --split eval --n 20          # baselines, horizon sweep
    python render.py 10000                          # pixel city, cruise vs lookahead40
    python eval_llm.py --model <mlx model> --n 20   # LLM agent, saves full per-turn traces

## Baselines

`Lookahead(k)` tries each build option and rolls a no-investment policy forward k turns on resampled futures. k=1 is the greedy agent. Same simulator and same options for every k, so the only thing that changes is how far ahead it looks.

Mean score over 20 unseen worlds (eval / ood):

| agent | eval | ood |
|---|---|---|
| random | 526 | 208 |
| cruise (no investing) | 809 | 407 |
| greedy (1 turn) | 1317 | 993 |
| lookahead 4 | 2734 | - |
| lookahead 10 | 3559 | 2198 |
| lookahead 20 | 4105 | - |
| lookahead 40 | 4663 | 3373 |

Score rises steadily with planning depth, so there is room for a model to learn to plan further ahead.

## LLM run

`eval_llm.py` ran end to end with Qwen2.5-0.5B (4-bit) on 3 unseen worlds, 20 turns each. Full per-turn traces are in `results/llm_qwen0p5b_v2/`. With a worked example in the prompt the model returned unusable replies in 4 to 14 of 20 turns (17 of 20 without it), so it is not yet a meaningful player. 20-turn scores are not comparable to the 100-turn baselines above. Use a Python environment outside iCloud-synced folders for mlx-lm.

## 9B result

Gemma-2-9B-it (4-bit) on the same 3 worlds, 20 turns, traces in `results/llm_gemma2_9b/`. Zero unusable replies, and the plans read sensibly (more farms and housing for growth), but execution is sloppy: it assigns more workers than exist and orders builds it cannot afford. Mean score 917, against 1180 for the no-investing policy, 1742 for greedy and 4025 for the 20-turn planner on the same worlds. So a 9B model plays below a policy that never invests, and well below one that looks ahead.

Only 3 worlds at 20 turns. A 100-turn, 20-world run is the next step.
