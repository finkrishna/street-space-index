#!/usr/bin/env python3
"""
Street Space Index — reference model (v0.3).

Who gets the street, and who does the street actually carry?

For each road:
  space share  = % of kerb-to-kerb width serving each mode
  people share = % of people moved by each mode
  index        = space share / people share        (1.0 = fair share)
  headline     = % of usable street width serving walking, cycling and buses/metro
  ratio        = street per person in a motor vehicle ÷ street per person walking,
                 cycling or on a bus  (1.0 = even)

Demand comes from measured counts where we have them (Pune: ITDP 2022 peak-hour
counts; Copenhagen: daily counts) and from mode share otherwise.

Usage (standard library only):
  python3 model/street_space.py                       # all roads, as usable (observed)
  python3 model/street_space.py --as-drawn            # ignore observed footpath usability
  python3 model/street_space.py --road my.json        # your own road
  python3 model/street_space.py --set occupancy.car=1.3 --csv out.csv

index.html implements exactly the same arithmetic.
"""
import argparse, csv, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODEL = os.path.join(HERE, "..", "data", "model.json")
GROUPS = [("walk", "Walk"), ("cycle", "Cycle"), ("pt", "Bus + metro"), ("ipt", "Auto + cab"),
          ("tw", "Two-wheeler"), ("car", "Car"), ("goods", "Goods vehicles"), ("other", "Other / unusable")]
PEOPLE = ["walk", "cycle", "pt", "ipt", "tw", "car"]


def step(n, total, msg):
    print(f"[{int(n / total * 100):3d}%] {msg}", flush=True)


def demand(road, m):
    """Return (people by group, vehicles by mode) from counts or mode share."""
    occ = m["occupancy"]
    if "counts" in road:
        c = road["counts"]
        buses = c.get("buses")
        if buses is None:
            buses = c.get("bus_passengers", 0) / occ["bus"]
        bus_people = c.get("bus_passengers", buses * occ["bus"])
        people = {"walk": c.get("pedestrians", 0), "cycle": c.get("cyclists", 0), "pt": bus_people,
                  "ipt": c.get("autos", 0) * occ["ipt"], "tw": c.get("two_wheelers", 0) * occ["two_wheeler"],
                  "car": c.get("cars", 0) * occ["car"]}
        veh = {"two_wheeler": c.get("two_wheelers", 0), "car": c.get("cars", 0), "ipt": c.get("autos", 0),
               "bus": buses, "goods": c.get("goods", 0)}
    else:
        s = road.get("mode_share") or m["mode_share_pct"]
        people = {"walk": s["walk"], "cycle": s["cycle"], "pt": s["bus"] + s["metro"], "ipt": s["ipt"],
                  "tw": s["two_wheeler"], "car": s["car"]}
        veh = {"two_wheeler": s["two_wheeler"] / occ["two_wheeler"], "car": s["car"] / occ["car"],
               "ipt": s["ipt"] / occ["ipt"], "bus": s["bus"] / occ["bus"], "goods": 0}
    return people, veh


def compute(road, m, as_drawn=False):
    w = road["widths_m"]
    W = sum(w.values())
    if W <= 0:
        raise ValueError(f"{road.get('name')}: widths must add up to more than 0 m")
    u = {"footpath": 1.0, "cycle_track": 1.0} if as_drawn else {**{"footpath": 1.0, "cycle_track": 1.0}, **road.get("usable", {})}
    people, veh = demand(road, m)
    pcu = m["pcu"]
    has_bl = w.get("bus_lane", 0) > 0
    modes = ["two_wheeler", "car", "ipt", "goods"] + ([] if has_bl else ["bus"])
    lane = {k: veh[k] * pcu[k] for k in modes}
    tot = sum(lane.values())
    s = {k: (lane.get(k, 0) / tot if tot else 0) for k in ["two_wheeler", "car", "ipt", "goods", "bus"]}
    ps = road.get("parking_split") or m["parking_split"]
    fp, ct, cw, pk = w.get("footpath", 0), w.get("cycle_track", 0), w.get("carriageway", 0), w.get("parking", 0)
    space = {
        "walk": fp * u["footpath"] / W,
        "cycle": ct * u["cycle_track"] / W,
        "pt": (w.get("bus_lane", 0) + cw * s["bus"]) / W,
        "ipt": cw * s["ipt"] / W,
        "tw": (cw * s["two_wheeler"] + pk * ps.get("two_wheeler", 0)) / W,
        "car": (cw * s["car"] + pk * ps.get("car", 0)) / W,
        "goods": cw * s["goods"] / W,
    }
    space["other"] = 1 - sum(space.values())
    P = sum(people[k] for k in PEOPLE) or 1
    share = {k: (people[k] / P if k in PEOPLE else 0) for k in space}
    index = {k: (space[k] / share[k] if share[k] else None) for k in space}
    sust_space = space["walk"] + space["cycle"] + space["pt"]
    sust_people = share["walk"] + share["cycle"] + share["pt"]
    motor_space = space["car"] + space["tw"] + space["ipt"]
    motor_people = share["car"] + share["tw"] + share["ipt"]
    ratio = ((motor_space / motor_people) / (sust_space / sust_people)
             if motor_people and sust_space and sust_people else 0.0)
    g = m["grades"]
    pct = sust_space * 100
    grade = "Good" if pct >= g["good_min"] else "Ugly" if pct < g["ugly_below"] else "Bad"
    return {"width_m": W, "space": space, "people": share, "index": index, "headline": pct,
            "people_pct": sust_people * 100, "ratio": ratio, "grade": grade}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--road", help="JSON file with one road (same shape as an entry in model.json 'roads')")
    ap.add_argument("--as-drawn", action="store_true", help="count all drawn footpath/cycle width as usable")
    ap.add_argument("--set", action="append", default=[], metavar="GROUP.KEY=VALUE",
                    help="override an assumption, e.g. --set occupancy.car=1.4 --set pcu.bus=2.2")
    ap.add_argument("--csv", help="write results to this CSV path")
    a = ap.parse_args()

    step(0, 3, f"Loading {os.path.relpath(a.model)}")
    with open(a.model, encoding="utf-8") as f:
        m = json.load(f)
    for s in a.set:
        key, _, val = s.partition("=")
        grp, _, fld = key.partition(".")
        if grp not in m or fld not in m[grp]:
            raise KeyError(f"unknown assumption '{key}'")
        m[grp][fld] = float(val)
        print(f"       override {key} = {val}")
    roads = m["roads"]
    if a.road:
        with open(a.road, encoding="utf-8") as f:
            roads = [json.load(f)]
    step(1, 3, f"{len(roads)} road(s), {'as drawn' if a.as_drawn else 'as actually usable'}")

    res = [(r, compute(r, m, a.as_drawn)) for r in roads]
    res.sort(key=lambda x: -x[1]["headline"])
    print("\n  street space for walking, cycling & buses vs the people they carry")
    print(f"  {'street':28s}{'city':12s}{'street':>7s}{'people':>8s}{'ratio':>7s}  grade")
    rows = []
    for r, x in res:
        i = x["index"]
        print(f"  {r['name'][:27]:28s}{r.get('city', '')[:11]:12s}{x['headline']:6.0f}%{x['people_pct']:7.0f}%{x['ratio']:6.1f}×  {x['grade']}")
        for k, label in GROUPS:
            rows.append([r["name"], r.get("city", ""), label, round(x["space"][k] * 100, 1),
                         round(x["people"][k] * 100, 1), None if i[k] is None else round(i[k], 2),
                         round(x["headline"], 1), round(x["ratio"], 2), x["grade"]])
    step(2, 3, "Computed")
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as f:
            wr = csv.writer(f)
            wr.writerow(["road", "city", "group", "space_pct", "people_pct", "index", "sustainable_street_pct", "motor_vs_sustainable_ratio", "grade"])
            wr.writerows(rows)
        print(f"       wrote {a.csv}")
    step(3, 3, "Done")


if __name__ == "__main__":
    try:
        main()
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as e:
        sys.exit(f"Error: {e}")
