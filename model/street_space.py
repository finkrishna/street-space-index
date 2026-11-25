#!/usr/bin/env python3
"""
Street Space Index — reference model.

Who gets the street, and who does the street actually carry?

For each road this computes:
  space share  = % of kerb-to-kerb width given to each mode group
  people share = % of trips made by that mode group
  index        = space share / people share   (1.0 = fair share)

Usage (no dependencies beyond the standard library):
  python3 model/street_space.py                    # all roads in data/model.json
  python3 model/street_space.py --road my.json     # your own road (see README)
  python3 model/street_space.py --csv out.csv      # also write a CSV

The browser version (index.html) implements exactly the same arithmetic.
"""
import argparse
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODEL = os.path.join(HERE, "..", "data", "model.json")
GROUPS = [
    ("walk", "Walk + cycle"),
    ("pt", "Bus + metro"),
    ("ipt", "Auto + cab"),
    ("tw", "Two-wheeler"),
    ("car", "Car"),
    ("other", "Medians, encroached"),
]


def step(n, total, msg):
    pct = int(n / total * 100)
    print(f"[{pct:3d}%] {msg}", flush=True)


def carriageway_split(ms, occ, pcu, has_bus_lane):
    """Split shared traffic lanes by lane-space demand (vehicles x PCU)."""
    modes = ["two_wheeler", "car", "ipt"] + ([] if has_bus_lane else ["bus"])
    demand = {m: ms[m] / occ[m] * pcu[m] for m in modes}
    total = sum(demand.values()) or 1.0
    split = {m: demand[m] / total for m in modes}
    split.setdefault("bus", 0.0)
    return split


def compute(road, model, mode_share=None):
    ms = mode_share or model["mode_share_pct"]
    occ, pcu, park = model["occupancy"], model["pcu"], model["parking_split"]
    w = road["widths_m"]
    W = sum(w.values())
    if W <= 0:
        raise ValueError(f"{road.get('name')}: widths must add up to more than 0 m")
    has_bl = w.get("bus_lane", 0) > 0
    s = carriageway_split(ms, occ, pcu, has_bl)
    cw, pk = w.get("carriageway", 0), w.get("parking", 0)
    u = model.get("footpath_usable", {}).get("value", 1.0)
    fp = w.get("footpath", 0)

    space = {
        "walk": (fp * u + w.get("cycle_track", 0)) / W,
        "pt": (w.get("bus_lane", 0) + cw * s["bus"]) / W,
        "ipt": cw * s["ipt"] / W,
        "tw": (cw * s["two_wheeler"] + pk * park["two_wheeler"]) / W,
        "car": (cw * s["car"] + pk * park["car"]) / W,
        "other": (w.get("other", 0) + fp * (1 - u)) / W,
    }
    people_total = sum(v for k, v in ms.items() if not k.startswith("_"))
    people = {
        "walk": ms["walk_cycle"] / people_total,
        "pt": (ms["bus"] + ms["metro"]) / people_total,
        "ipt": ms["ipt"] / people_total,
        "tw": ms["two_wheeler"] / people_total,
        "car": ms["car"] / people_total,
        "other": 0.0,
    }
    index = {k: (space[k] / people[k] if people[k] else None) for k in space}
    return {"width_m": W, "space": space, "people": people, "index": index}


def city_parking(model):
    c = model["city_context"]
    a = c["parking_m2_each"]
    m2 = c["cars"] * a["car"] + c["two_wheelers"] * a["two_wheeler"] + c["autos"] * a["auto"] + c["buses"] * a["bus"]
    return m2 / 1e6


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--road", help="JSON file with one road (same shape as an entry in model.json 'roads')")
    ap.add_argument("--csv", help="write results to this CSV path")
    ap.add_argument("--preset", help="mode-share preset from model.json, e.g. pune_city or itdp_corridors")
    ap.add_argument("--usable", type=float, help="fraction of footpath width actually walkable, 0-1")
    ap.add_argument("--set", action="append", default=[], metavar="GROUP.KEY=VALUE",
                    help="override an assumption, e.g. --set occupancy.car=1.4 --set pcu.bus=2.2")
    args = ap.parse_args()

    step(0, 4, f"Loading model: {os.path.relpath(args.model)}")
    with open(args.model, encoding="utf-8") as f:
        model = json.load(f)
    if args.preset:
        p = model["mode_share_presets"][args.preset]
        model["mode_share_pct"] = {k: v for k, v in p.items() if k not in ("label", "_note")}
        print(f"       mode share: {p['label']}")
    if args.usable is not None:
        if not 0 <= args.usable <= 1:
            raise ValueError("--usable must be between 0 and 1")
        model["footpath_usable"]["value"] = args.usable
        print(f"       footpath usable: {args.usable:.0%}")
    for s in args.set:
        key, _, val = s.partition("=")
        group, _, field = key.partition(".")
        if group not in model or field not in model[group]:
            raise KeyError(f"unknown assumption '{key}'")
        model[group][field] = float(val)
        print(f"       override: {key} = {val}")

    roads = model["roads"]
    if args.road:
        with open(args.road, encoding="utf-8") as f:
            roads = [json.load(f)]
    step(1, 4, f"{len(roads)} road(s) to analyse")

    rows = []
    for r in roads:
        res = compute(r, model)
        print(f"\n  {r['name']}, {r.get('city', '')} — {res['width_m']:.0f} m kerb to kerb")
        print(f"  {'group':20s}{'space':>8s}{'people':>8s}{'index':>8s}")
        for key, label in GROUPS:
            idx = res["index"][key]
            print(f"  {label:20s}{res['space'][key]*100:7.1f}%{res['people'][key]*100:7.1f}%"
                  f"{(f'{idx:7.2f}x' if idx is not None else '      –')}")
            rows.append([r["name"], r.get("city", ""), label, round(res["space"][key] * 100, 1),
                         round(res["people"][key] * 100, 1), None if idx is None else round(idx, 2)])
    step(2, 4, "Road indices computed")

    if not args.road:
        km2 = city_parking(model)
        print(f"\n  Space to park Pune RTO's fleet: {km2:.1f} km² (≈{km2*1e6/7140:,.0f} football pitches)")
    step(3, 4, "City context computed")

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            wr = csv.writer(f)
            wr.writerow(["road", "city", "group", "space_pct", "people_pct", "index"])
            wr.writerows(rows)
        print(f"  Wrote {args.csv}")
    step(4, 4, "Done")


if __name__ == "__main__":
    try:
        main()
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as e:
        sys.exit(f"Error: {e}")
