# Demo price list: Kosovo market estimates

The demo workshop's catalogue (`backend/src/quote_engine/services/demo_catalogue.py`) uses these values. They are **market estimates from public sources, not any workshop's own prices**, in euros **excluding VAT**, researched on 13-14 Nov 2026. The full research report, with every source link, date and confidence, is `reports/Kosovo PVC window prices.md`; the researchers' notes are in `research_notes/Kosovo PVC window prices/`.

**What limits them:** Kosovo window makers and distributors publish no price lists. Most values are regional (Serbia, North Macedonia, Bosnia, Croatia, Turkey) adjusted to Kosovo, and several are assumptions, marked below. Replace them with real supplier quotes before relying on them.

## Profile systems in the demo

Chosen because they are documented as sold in Kosovo:
- Salamander: EB Group, the importer for Kosovo and Albania.
- REHAU: its own Prishtina office since 2000.
- Alumil: Alumil Kosovo, Prishtina.

Winsa, Egepen, VEKA, Deceuninck and ETEM could not be confirmed in Kosovo.

| Tier | PVC | Aluminium |
|---|---|---|
| Budget | REHAU Euro-Design 70 (70 mm, 5 chambers) | Alumil COMFORT M9400 (45 mm, no thermal break) |
| Mid | Salamander greenEvolution 76 (76 mm) | Alumil SMARTIA S67 (67 mm, thermal break) |
| Premium | REHAU SYNEGO 80 (80 mm) | Alumil SMARTIA M11000 (77 mm, thermal break) |

The sheets' deductions are invented (SAMPLE - NOT REAL); only the prices are researched.

## Material

| Item | Demo value | Basis | Confidence |
|---|---|---|---|
| PVC profile, budget, white | €3.60 frame / €4.10 sash per m (6 m bars) | Turkish 70 mm/5-chamber list (Oct 2025) landed ×1.25, then ×1.2 for a German budget brand | medium / low |
| PVC profile, mid | €4.05 / €4.65 per m | same list ×1.7 | low (assumed tier step) |
| PVC profile, premium | €5.25 / €6.00 per m | same list ×2.2 | low (assumed tier step) |
| PVC foil | +25% one side, +45% both sides | Turkish list (+45-47% both sides); one side inferred | medium / low |
| Aluminium profile | €6.5, €9.0 and €11.0 per kg (budget, mid, premium) × 1.0-1.75 kg/m | Turkish and Serbian extrusion prices (Nov 2026), LME check; weights from a partial catalogue reading | low |
| Aluminium wood-grain finish | +10% one side, +14% both | Turkish list: €7.35 wood-grain vs €6.45 coloured per kg | medium |
| Steel reinforcement (PVC) | €8.70 per 6 m bar (€1.25/kg) | Turkish galvanised sheet price plus landing | medium |
| Gasket | €0.40-0.70 per m | regional EPDM retail | medium |
| Glass 4-16-4 / Low-E Ar / triple Low-E Ar | €18 / €21 / €33 per m² | Croatian price guide 2026, uplift ratios | medium |
| Hardware, PVC | €32 tilt-and-turn, €22 turn-only (handle included) | midpoint of budget (€22.50) and branded (€48) sets, regional prices | medium |
| Hardware, aluminium | €40 / €28 | PVC +25%, assumed (no source compares them) | low |
| Production consumables | €2.50 per window (PVC), €4.50 (aluminium) | inferred; aluminium adds corner cleats (assumed) | low |

## Labour, installation, transport

| Item | Demo value | Basis | Confidence |
|---|---|---|---|
| Production labour, PVC | €15 / €20 / €28 per window (small / standard / large) | calibrated so installed windows land on the Kosovo targets below | low |
| Production labour, aluminium | €21 / €28 / €39 | PVC +40% (sources suggest +20-50%, none measured) | low |
| Installation (standard, PU foam) | €20 / €25 / €35 per window | regional 2026: about €25 (€15-40) | medium |
| RAL installation | +€25 (about €50 in total) | regional 2026: €40-60 | medium |
| Removal of the old window | €15 | regional: €8-25 | medium |
| Wall repair | €20 per window | proxy: resealing about €10 per metre | low |
| Transport | €20 flat + €0.30 per km | call-out fee as a proxy; per km assumed | low |

## Extras

| Item | Demo value | Basis | Confidence |
|---|---|---|---|
| Interior PVC sill 200 / 250 / 300 mm | €16 / €20 / €24 per m | Croatian supplier list, Serbian site | medium |
| Roller shutter, PVC / insulated aluminium | €30 / €38 per m² | Kosovo classifieds (€31-33), Serbian list | medium |
| Insect screen, fixed / roll-up / pleated | €22 / €35 / €40 per m² | Serbian lists | medium |

## Check against finished-window prices

Targets for white, 5-chamber, double glazing, installed:
- **Single sash 800×1400:** about €145 (€120-180).
- **Two sashes 1400×1400:** about €255.
- **Fixed 600×900:** about €70.
- **Balcony door 800×2200:** about €260.
- **Per m²:** about €135 (€110-170).
- **Aluminium per m²:** thermal-break about €270, non-thermal-break about €140, premium about €320.

These are regional 2026 prices (Belgrade price list, Daibau, eMajstor, Gradi.ba) adjusted down for Kosovo.

The demo, on an 8-opening house job with standard installation:

| System | Per m² |
|---|---|
| REHAU Euro-Design 70 | €150 |
| Salamander greenEvolution 76 | €156 |
| REHAU SYNEGO 80 | €173 |
| Alumil M9400 | €190 |
| Alumil SMARTIA S67 | €270 |
| Alumil SMARTIA M11000 | €326 |

A single-window quote comes out higher, because the engine prices profile as whole bars used, and one window does not fill its bars.
