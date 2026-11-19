---
name: window-rules
description: PVC window workshop rules for this app - construction types, cutting constants, installation gaps, measuring, optimizer goal, price layers, rounding, glass minimums and hardware limits. Use when writing, reviewing or testing engine code (rules, measuring, optimizer, pricing, warnings, lists) or golden tests.
---

# Workshop rules (PVC windows, Kosovo)

Values marked **default** are settings, not facts about every system. Load them from the system sheet or settings; never hard-code them in formulas. Values marked **confirm** still need the owner's check (docs/PLAN.md section 15).

## Construction types in v1
1. `single_sash_tilt_turn`: single sash, tilt-and-turn, typical 800 x 1400
2. `two_field_t_mullion`: fixed T-mullion, tilt-and-turn + turn, typical 1400 x 1400
3. `two_sash_false_mullion`: two sashes, false mullion (no fixed mullion), typical 1200 x 1200
4. `fixed`: fixed glazing, any size (bathrooms, stairwells)
5. `balcony_door_tilt_turn`: balcony door, tilt-and-turn, typical 800 x 2200

Roller shutters and insect screens: priced per m². Sills: per metre. No cut lists in v1. Anything else is a manual line with a manual price.

## Cutting constants (per profile system)
| Constant | Default | Notes |
|---|---|---|
| Bar length | 6000 mm per profile | **confirm**: measure a real bar; catalogues vary (e.g. 6060 mm) |
| Weld allowance | 3 mm per end | **confirm** with one test corner; burn-off depends on the welder |
| Saw kerf | 4 mm | 3.5 mm on 450 mm blades, 4.0 mm on 500 mm blades; **confirm** from his blade |
| Bar end trim | 10 mm per bar total | **confirm** (assumption, not from a source) |
| Steel reinforcement | 10-15 mm shorter than the profile's inner length, 90°, never touches the weld | default 10, **confirm** |
| Angles | frame and sash 45° welded; mullion and steel 90° mechanical | |
| Offcuts | kept from 500 mm; shorter is scrap | |
| Sash, bead, glass deductions | **none**: only from that system's catalogue | missing → `MissingConstant`; never guess |
| Gasket extra | 5% (500 bp) over the perimeter | **confirm** |

Every piece formula must be printable: `"H + 2a = 1400 + 6 = 1406"`.

## Measuring
- 3 widths and 3 heights of the wall opening; use the smallest of each; warn if one dimension's readings differ by more than 10 mm.
- Installation gap **per side**, by that side's length and the profile colour:
  - white: 10 mm up to 1500, 15 up to 2500, 20 up to 3500
  - coloured (foiled): 15 / 20 / 25 mm for the same ranges
  - above 3500 mm: outside the table → error, not a guess
- Window width = opening width − 2 × gap(width); same for height.
- Drawings and opening sides are always shown **from inside**, handle side marked.

## Optimizer
- Group pieces by role + profile + colour; one bar length per group.
- Capacity: `Σ(length + kerf) ≤ bar_length − end_trim`. Same rule for FFD, exact and lower bound.
- Goal: fewest bars first, then the longest reusable offcut.
- Quotes use FFD (`ffd.py`). The CP-SAT solver is for the benchmark and the admin compare button only.

## Price layers (in this order)
1. Material cost: profiles and steel as **whole bars used** × price per bar (by colour), allocated to positions by consumed length with largest remainder; gasket per metre; one hardware set per opening sash; glass per m² per pane with a minimum billable area (default 0.3 m², **confirm** with the glass company); consumables per window; optional price-risk bp.
2. Margin on material only: default 25% (2500 bp), editable per quote, warning below 15%.
3. Labour per window by type and size class.
4. Installation per opening by size class; switches for RAL installation, old-window removal, wall repair.
5. Extras: sills per metre, shutters and screens per m².
6. Transport per job: flat + per km (Mitrovica to Prishtina is about 40 km).
7. Discount as its own line.
8. VAT 18% only if the workshop is VAT-registered (registration is mandatory above EUR 30,000 yearly turnover).
9. Advance 50% on acceptance; balance on installation.

Integer maths only: mm, cents, bp, mm². Round half up per line with `engine/units.py` helpers; totals are sums of rounded lines; VAT on the net total.

## Quote rules
- Valid for 15 days (setting), printed on the PDF.
- Warn when the price list used is older than 30 days.
- On acceptance: lock the revision, generate the purchase list so material is bought the day the advance arrives.
- Price-request message for suppliers is plain text built from the purchase list.

## Hardware and size warnings
- Each hardware set has max sash width, height, area and weight from its catalogue. Heavy-duty sets (e.g. MACO Multi Mammut) are rated up to 180 kg and 3.6 m² for PVC; standard sets are lower. Use the set's own catalogue values.
- Sash weight = glass area × glass kg/m² + sash perimeter × profile kg/m, both from the system sheet. Double glazing with two 4 mm panes is roughly 20 kg/m² (sanity check only).

## Profile systems sold in Kosovo
Salamander (EB Group), REHAU, VEKA (e.g. Gashi, Suhareka), Spectrum (NPT SEFO; 70/80/86 mm), Turkish brands Winsa and Egepen (Ege Profil; supplier not yet known). A system is data: profiles, bar lengths, prices, deductions, limits.
