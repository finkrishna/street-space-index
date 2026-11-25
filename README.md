# Who gets the street? — Street Space Index

**Live site:** https://finkrishna.github.io/street-space-index/

> **This is not a definitive study.** It's an invitation to analysts, planners, students and curious citizens to approach a shared problem systematically: how should dense Indian cities allocate a scarce common good, street space, among the people who need it? Every number here can be checked, challenged and replaced. Better data and sharper methods are the point.

Every street is a fixed amount of width. Pedestrians, cyclists, bus riders, two-wheelers and cars all share it. This project asks a simple question with an uncomfortable answer:

> **How much of the street does each group get, compared with how many people each group actually moves?**

It starts with three roads in Pune. It's built so that anyone can check their own road, change the assumptions, and ask for a deeper analysis.

---

## Where this came from

A post by **[The Better India](https://x.com/thebetterindia)** about Gangtok asked: *what if Indian cities were designed for people, not just vehicles?* It showed Gangtok's footpaths with protective railings, tactile tiles, solar studs and underground utility cables. That post started this project. Thank you to The Better India for highlighting the story.

Checking it led to a sharper question. Gangtok's 12 km retrofit puts utility cables in ducts under the footpath, so the footpath doesn't have to be dug up again and again. Before copying that anywhere, though, we wanted to know **who the street is currently built for**. Pune, a city with roughly as many registered vehicles as people, seemed a good place to measure.

## What we found (v0.2)

| Road | Walkers get | Cars get | Bus riders get |
|---|---|---|---|
| JM Road (redesigned) | **1.25×** their share | 1.31× | 0.06× |
| Karve Road | **0.57×** | **1.67×** | 0.12× |
| Satara Road (BRT) | **0.49×** | 1.42× | 1.52× |

*1.0× = a fair share: the group's share of street width equals its share of trips. These figures use the city-average mode share with all footpath width counted as usable.*

- **Karve Road is the typical pattern.** Cars get about 1.7× their share of the street. Walkers and bus riders are squeezed.
- **JM Road shows it can be reversed without widening anything.** Organising parking freed width for footpaths and a cycle track. ITDP's 2022 audit ranked it the best of 11 streets.
- **Satara Road is the trap in this metric.** The BRT gives buses more than their share of width, but space given isn't space used. Buses have run below capacity.
- **Under ITDP's corridor evidence the gap widens sharply.** Use the corridor survey split (32% walk, 40% public transport) and count only half the footpath width as usable, reflecting encroachment. On Karve Road, cars then get about **3.3×** their share and walkers about **0.26×**.

## Try it

- **Adjust the assumptions.** Sliders for footpath usability, vehicle occupancy, lane space (PCU) and parking, plus mode-share presets. Every chart updates live.
- **Check your own road.** Enter the cross-section of any street in any city and get its index instantly. *Copy link* gives you a URL that reopens your road exactly as you set it.
- **Ask for a deeper analysis.** One click opens a pre-filled [request](../../issues/new?template=road-request.yml) with your numbers already in it. Add photos or measurements and we'll look into it.

## The approach

### 1. Measure the street
Split the kerb-to-kerb width into six parts: footpaths, cycle track, dedicated bus lane, traffic lanes, parking and medians/other.

### 2. Count the people
Use trip mode share: what fraction of trips are on foot, by cycle, bus, metro, auto/cab, two-wheeler or car.

### 3. Divide the shared lanes fairly
Traffic lanes are shared, so headcount isn't the right way to split them. We split them by **lane-space demand**:

```
lane demand(mode) = trips(mode) ÷ occupancy(mode) × PCU(mode)
```

*Occupancy* converts trips into vehicles. *PCU* (passenger car unit) converts vehicles into road space: a bus takes about 3 cars' worth, a two-wheeler about 0.75. If a road has a dedicated bus lane, buses are removed from the shared lanes. Parking is split between cars and two-wheelers.

Footpath width is multiplied by a **usable fraction**. The unusable part (encroached or obstructed) counts as non-movement space.

### 4. Compare
```
space share(mode) = width serving that mode ÷ total width
index(mode)       = space share(mode) ÷ trip share(mode)
```
Above 1.0, the group has more street than its riders. Below 1.0, it's squeezed. Metro trips count in the people share but use no road surface, which is why elevated rail lowers the transit index on a road without lowering anyone's mobility.

## What could make this wrong

We lead with these before anyone relies on the numbers:

1. **Registered isn't on the road.** RTO totals rarely remove scrapped vehicles. Only about 38% of Pune's 26 lakh pre-2019 vehicles have fitted the mandatory high-security plates, which suggests many old registrations are no longer driven.
2. **City averages aren't corridor reality.** The ITDP corridor survey (32% walk, 40% public transport) differs a lot from the city average. A perception survey also probably over-represents walkers and bus riders.
3. **Drawn width isn't usable width.** That's why the footpath-usable slider exists.
4. **Space given isn't space used.** An empty bus lane scores well here and still fails.
5. **PCU is a simplification.** At signals, two-wheelers fill gaps between cars.
6. **Two of the three cross-sections are assumptions.** Only JM Road's 36 m right of way is sourced. The status of every input is flagged `sourced` or `assumed` in [`data/model.json`](data/model.json).

## The ITDP audit

[Pune's Walk & Cycle Analysis](https://itdp.in/resource/punes-walk-cycle-analysis/) (ITDP India with Pune Municipal Corporation, Dec 2022) audited 11 streets wider than 24 m, about 30 km in 500 m segments, and surveyed 2,300 people. Three findings are built into v0.2:

- 70% of streets had footpaths, but **only 30% of pedestrians used them** → the footpath-usable slider.
- Respondents: **32% walked, 40% used public transport** → the "ITDP 11-corridor" preset.
- **Ranking:** JM Road best, then Raj Bhavan Road and Satara Road. Magarpatta–Mundhwa, Vishrantwadi and Shankarsheth roads lowest.

The audit scores design *quality* and this index scores width *share*. They agree on JM Road and diverge on Satara Road. **Not yet used:** the report's per-street measurements. The full PDF couldn't be retrieved for v0.2; replacing the assumed Karve and Satara cross-sections with it is the next step.

## How the chart is built

No charting library. Every bar is a row of plain HTML `<div>`s, and each segment's `flex-basis` is set to its percentage, so the bars are exact, accessible and print cleanly.

- [`data/model.json`](data/model.json) is the **single source of truth**: mode shares, occupancy, PCU, parking split, footpath usability, road cross-sections, ITDP findings and sources.
- [`index.html`](index.html) loads that file and runs the arithmetic in about 30 lines of JavaScript (`compute()`). Sliders change the in-memory copy and redraw. Your road is saved in the URL (`#road=…`), so a shared link reproduces it exactly.
- [`model/street_space.py`](model/street_space.py) implements **the same arithmetic** in standard-library Python, so every number on the site can be reproduced and audited.

```bash
python3 model/street_space.py                                 # the three Pune roads
python3 model/street_space.py --preset itdp_corridors --usable 0.5
python3 model/street_space.py --set occupancy.car=1.3 --set pcu.bus=2.2
python3 model/street_space.py --road my_road.json --csv out.csv
```

A road file looks like this:
```json
{ "name": "MG Road", "city": "Bengaluru",
  "widths_m": { "footpath": 6, "cycle_track": 0, "bus_lane": 0, "carriageway": 18, "parking": 2, "other": 2 } }
```

Run locally: `python3 -m http.server` in the repo folder, then open http://localhost:8000.

## Progress

`██████████░░░░░░░░░░ 50%`

- [x] Method, city context, three Pune roads
- [x] Adjustable assumptions, check-your-road calculator, request form
- [x] ITDP audit findings (footpath use, corridor users, ranking)
- [ ] Per-street widths from the full ITDP report
- [ ] Corridor traffic counts instead of city averages
- [ ] More cities, from your requests

## Contribute

- **Analyse a road:** open the [request form](../../issues/new?template=road-request.yml), or use *Ask for a deeper analysis* on the site.
- **Fix a number:** if you have a measured cross-section or a traffic count, open an issue with the source. Sourced numbers replace assumptions.

## Sources

All sources, with the claim each one supports, are listed in [`data/model.json`](data/model.json) and at the bottom of the live site. Key ones:

- [Pune RTO vehicle count (Free Press Journal)](https://www.freepressjournal.in/amp/pune/rising-vehicle-numbers-push-pune-towards-3-letter-registration-system-all-you-need-to-know)
- [Pune region population and vehicles; under-used BRT (Down To Earth)](https://www.downtoearth.org.in/air/how-india-moves-punes-roads-buckle-under-an-explosion-of-two-wheeler-traffic)
- [PMRDA CMP mode shares (Parisar/PKC)](https://www.pkc.org.in/wp-content/uploads/2025/08/SUSTAINABLE-TRANSPORT.pdf)
- [ITDP Pune street assessment](https://itdp.in/pune-streets-impact-assessment/) and [report coverage (Punekar News)](https://www.punekarnews.in/pmc-itdp-publish-pune-walk-and-cycle-analysis-report/)
- [Gangtok footpath retrofit with utility ducts (Gangtok Smart City)](https://smartcitygangtok.com/Our%20Projects.aspx)

## Licence

Code: MIT. Text and data: CC BY 4.0. Built by Krishna (finkrishna) with Claude.
