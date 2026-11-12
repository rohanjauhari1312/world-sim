import json

from .env import TOOLS

SYSTEM = """You run a small settlement for 100 turns. Each turn you may use up to 12 tool calls, then the turn ends and the world updates: workers produce, people eat, taxes come in, prices drift, hazards and elections happen.

Final score = gold - debt + stockpile value + population value. Buildings do not count by themselves, they only pay off through what they produce or protect. Construction takes several turns. Where you build matters: use the map and the site list. Output only reaches town in proportion to the delivery share, which depends on the path to town (hills and unbridged rivers are costly, roads are cheap), and tiles near the river can flood. Think ahead: population only grows if there is housing and spare food, and some investments take 15+ turns to pay back.

Tools (JSON objects):
%s

Reply with one JSON object only, using exactly one value per field. Example:
{"plan": "more housing so the population can grow", "actions": [{"tool": "build", "building": "house", "x": 7, "y": 9}, {"tool": "assign_workers", "farm": 8, "lumberyard": 5, "mine": 3}, {"tool": "trade", "good": "ore", "quantity": -10}, {"tool": "set_tax", "rate": 0.2}, {"tool": "end_turn"}]}
End the list with {"tool": "end_turn"}.""" % "\n".join(
    "- %s %s" % (t["name"], json.dumps(t["args"])) for t in TOOLS)
