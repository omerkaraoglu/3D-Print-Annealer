"""results.json helper for the earthed campaign (this folder only)."""
import json, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results.json")
PLOTS = os.path.join(HERE, "plots")
os.makedirs(PLOTS, exist_ok=True)


def _np(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))


def save(section, data):
    res = {}
    if os.path.exists(RESULTS):
        with open(RESULTS, encoding="utf8") as f:
            res = json.load(f)
    res[section] = data
    with open(RESULTS, "w", encoding="utf8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False, default=_np)
