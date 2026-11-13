# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

Phone-first mobile web (the owner on site), also used at a PC in the workshop. Served by the same FastAPI process as the API, one origin.

## Users

- **The owner (primary).** Runs a small PVC window workshop in Kosovo. Measures openings on building sites and in clients' homes, on his phone, often in bright sunlight, with dusty or wet hands, sometimes on a ladder. App comfort is Viber/WhatsApp level: he messages and calls daily and uses little else, so every screen must be obvious without explanation. Job on site: measure each opening, turn it into a priced quote, and send it to the client before he leaves.
- **The owner at the workshop PC.** The same person at a laptop or PC: keeps price lists current (a supplier raised prices by X%), reads the cutting plan, checks quotes, records payments.
- **The admin.** The developer who maintains the technical catalogue: profile systems, system sheets with their deductions, hardware sets, construction types, users and sessions. Uses TOTP.
- **Demo workshop.** PLAN.md includes a public demo workshop with invented data (`demo@example.invalid`), wiped nightly. Confirmed as a feature, not as a primary design audience.

## Product Purpose

Mjera (working name) replaces pencil-and-paper quoting. From three width and three height readings per opening it computes the window size, cuts every piece with its formula, packs the pieces onto the fewest stock bars, prices the job layer by layer and produces the client PDF and the workshop cutting plan.

Success: the client gets a correct, explained price in minutes, on site; the workshop buys fewer bars and cuts with fewer mistakes; a price the client accepted never changes afterwards.

## Positioning

Every number explains itself. Each cut piece carries its formula (`W + 2a = 1200 + 6 = 1206`), each price is a sum of named layers in whole cents, and catalogue values are never guessed: a missing deduction or price stops the quote and says exactly what is missing. Accepted quotes are frozen with the exact system sheet and price list they used. A generic quoting tool or a spreadsheet cannot truthfully claim this.

## Operating Context

- Owner flow (PLAN.md section 7): log in once and stay logged in, quotes list (search, status filter), new quote (pick or add client), add position (tap a construction type picture, width and height on the number keypad, opening side, colour, glass, quantity, a live drawing seen from inside with the handle side), warnings, summary (positions, extras, discount, total; tap for the cutting plan and the price layers), PDFs and the phone's share sheet (Viber, WhatsApp; download as fallback), status (sent, accepted, rejected) and payments (advance, balance).
- Admin screens: price lists (new version with a start date, supplier +X%), suppliers, system sheets (each deduction with its catalogue page), construction types, settings, users, sessions.
- Measuring: three widths and three heights per wall opening; the smallest counts; readings more than 10 mm apart are a warning. Window drawings and opening sides are always shown from inside.
- Five construction types in v1: single sash tilt-and-turn, two fields with a fixed T-mullion, two sashes with a false mullion, fixed glazing, balcony door. Extras: sills (per metre), roller shutters and insect screens (per m²), manual lines.
- Units: sizes in whole millimetres, money in euros (stored as cents), percentages shown as %.
- Language: Bosnian by default, English one tap away. Client PDFs in Bosnian or Albanian.
- Quote states: draft, sent, accepted, rejected; expired is computed from the validity (15 days by default). Editing a sent quote makes a new revision.

## Capabilities and Constraints

- Buttons and touch targets at least 44 px; high contrast; one task per screen; sizes always in mm, labelled, with `inputmode="numeric"`.
- Remember the last profile system, colour and glass; a "copy previous window" action.
- A "DEMO" banner on every screen in the demo workshop.
- Data through TanStack Query, forms through React Hook Form + Zod, types only from the generated OpenAPI schema (`frontend/openapi.json`); i18next keys in `bs.json` and `en.json`.
- Content-Security-Policy is `default-src 'self'`: no external fonts, scripts, images or `data:` URIs. Fonts must be bundled with the app.
- Session by cookie with a CSRF header; the admin passes a TOTP step; sensitive actions (prices, system sheets, export, erase) ask for the password again.
- No Figma designs exist. Mirza decided (2026-11-13) that the screens are designed from PLAN.md section 7 with Impeccable.
- Undecided: the product name. "Mjera" (from *po mjeri*, made to measure) is a working name chosen on Mirza's delegation; the workshop's own name from its settings is shown alongside it.

## Brand Commitments

- Plain and fast, not flashy (Mirza's brief for the owner's app).
- No logo, imagery or brand assets exist.

## Evidence on Hand

- No real client data, prices, photos, logos, testimonials or usage numbers in the repository, and none may be invented. Demo data is invented and marked SAMPLE.
- Real facts that may be shown: the five construction types, the formula strings, the optimizer benchmark in `docs/optimizer.md` (FFD matches the fewest bars on 94% of 300 orders, never more than one bar off).

## Product Principles

1. **Every number explains itself.** A length, a price or a warning can always be opened to show where it came from.
2. **Built for the site, not the desk.** Sunlight, dust, one hand, a ladder: big targets, strong contrast, the number keypad, one decision per screen.
3. **Never guess.** A missing catalogue value or price is a clear, fixable stop, never a silent default.
4. **What the client accepted stays accepted.** Accepted quotes are frozen; changes go through a new revision.
5. **The workshop's own words.** Bosnian first, the trade's terms, nothing a Viber-level user would have to learn.

## Accessibility & Inclusion

- Readable in direct sunlight: contrast well above WCAG AA for text and controls.
- Touch targets of at least 44 px; usable with one hand on a phone.
- axe reports no serious issues on any main screen (PLAN.md section 14, M8).
- Works when the phone's text size is raised.
