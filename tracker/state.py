import json
import os

from .config import ROOT

STATE_PATH = ROOT / "state" / "stock.json"


def load_state():
    if STATE_PATH.exists():
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"version": 1, "stores": {}, "meta": {}}


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(STATE_PATH) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        # sorted keys + indent so the committed file diffs cleanly in git
        json.dump(state, f, indent=1, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, STATE_PATH)
