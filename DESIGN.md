---
name: Mjera
description: Quotes and cutting plans for a PVC window workshop, measured and priced on site.
colors:
  plaster: "#e6e8e7"
  plaster-deep: "#d3d8d7"
  board: "#fafbfb"
  graphite: "#23272b"
  graphite-soft: "#4b5258"
  graphite-line: "#7a838a"
  shell: "#23272b"
  shell-raised: "#353b41"
  chalk: "#1f5fd1"
  chalk-deep: "#174aa6"
  chalk-tint: "#dbe5f7"
  crayon: "#b42a17"
  crayon-tint: "#f6dcd6"
  tick: "#17653a"
  tick-tint: "#d6ebdf"
typography:
  figure-lg:
    fontFamily: "Noto Sans, system-ui, sans-serif"
    fontSize: "2.75rem"
    fontWeight: 800
    lineHeight: 1
    letterSpacing: "-0.01em"
    fontFeature: "\"tnum\" 1, \"lnum\" 1"
    fontVariation: "\"wdth\" 87.5"
  figure-md:
    fontFamily: "Noto Sans, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 800
    lineHeight: 1.15
    letterSpacing: "-0.01em"
    fontFeature: "\"tnum\" 1, \"lnum\" 1"
    fontVariation: "\"wdth\" 87.5"
  figure-sm:
    fontFamily: "Noto Sans, system-ui, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 800
    lineHeight: 1.3
    letterSpacing: "-0.01em"
    fontFeature: "\"tnum\" 1, \"lnum\" 1"
    fontVariation: "\"wdth\" 87.5"
  headline:
    fontFamily: "Noto Sans, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 800
    lineHeight: 1.33
  title:
    fontFamily: "Noto Sans, system-ui, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 800
    lineHeight: 1.25
  body:
    fontFamily: "Noto Sans, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Noto Sans, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 700
    lineHeight: 1.5
  note:
    fontFamily: "Noto Sans, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.43
rounded:
  slot: "0.625rem"
  pill: "9999px"
spacing:
  gutter: "1rem"
  inset: "0.75rem"
  stack: "1.5rem"
  target-min: "2.75rem"
  control: "3.5rem"
components:
  button-primary:
    backgroundColor: "{colors.chalk}"
    textColor: "{colors.board}"
    typography: "{typography.title}"
    rounded: "{rounded.slot}"
    padding: "0 1.25rem"
    height: "3.5rem"
  button-primary-hover:
    backgroundColor: "{colors.chalk-deep}"
  button-primary-disabled:
    backgroundColor: "{colors.graphite-line}"
  button-secondary:
    backgroundColor: "{colors.board}"
    textColor: "{colors.graphite}"
    typography: "{typography.title}"
    rounded: "{rounded.slot}"
    padding: "0 1.25rem"
    height: "3.5rem"
  button-secondary-hover:
    backgroundColor: "{colors.plaster}"
  button-quiet:
    backgroundColor: "transparent"
    textColor: "{colors.chalk}"
    rounded: "{rounded.slot}"
    height: "3.5rem"
  button-quiet-hover:
    backgroundColor: "{colors.chalk-tint}"
  button-danger:
    backgroundColor: "{colors.board}"
    textColor: "{colors.crayon}"
    rounded: "{rounded.slot}"
    height: "3.5rem"
  button-danger-hover:
    backgroundColor: "{colors.crayon-tint}"
  field:
    backgroundColor: "{colors.board}"
    textColor: "{colors.graphite}"
    rounded: "{rounded.slot}"
    padding: "0 1rem"
    height: "3.5rem"
  top-bar:
    backgroundColor: "{colors.shell}"
    textColor: "{colors.board}"
    typography: "{typography.title}"
    height: "4rem"
  segmented:
    backgroundColor: "{colors.plaster-deep}"
    textColor: "{colors.graphite}"
    rounded: "{rounded.slot}"
    padding: "0.25rem"
  segmented-selected:
    backgroundColor: "{colors.chalk}"
    textColor: "{colors.board}"
  status-pill-draft:
    backgroundColor: "{colors.plaster-deep}"
    textColor: "{colors.graphite}"
    rounded: "{rounded.pill}"
    padding: "0 0.75rem"
  status-pill-sent:
    backgroundColor: "{colors.chalk-tint}"
    textColor: "{colors.chalk-deep}"
    rounded: "{rounded.pill}"
  status-pill-accepted:
    backgroundColor: "{colors.tick-tint}"
    textColor: "{colors.tick}"
    rounded: "{rounded.pill}"
  status-pill-expired:
    backgroundColor: "{colors.crayon-tint}"
    textColor: "{colors.crayon}"
    rounded: "{rounded.pill}"
  bottom-sheet:
    backgroundColor: "{colors.board}"
    textColor: "{colors.graphite}"
    padding: "1rem"
  measure-slot:
    backgroundColor: "{colors.board}"
    textColor: "{colors.graphite}"
    typography: "{typography.figure-md}"
    rounded: "{rounded.slot}"
    width: "4.75rem"
    height: "3rem"
  measure-slot-active:
    textColor: "{colors.chalk}"
---

# Design System: Mjera

## Overview

**Creative North Star: "Pencil on the Site Wall"**

The app looks like the wall of a building site after the owner has measured it. The ground is skimmed plaster. Ink and the top bar are carpenter's graphite. The blue chalk line marks what he is working on now. Red marking crayon marks only what he must check again. A quiet green marks only what is accepted or paid.

Numbers carry the screen. Every size is written like a dimension string on a drawing: the number on top, a line with an end tick on each side under it. The number he says out loud is always the biggest thing on the screen. Every total and every size opens to show its sum. Text is short and the controls are large, because he works in sunlight, with one hand, sometimes on a ladder.

Density is low on the phone and the same layout centres on the PC. There is no imagery and no logo. The only drawings are the windows themselves, drawn from inside with 45° mitres and 90° joints, and they are also the buttons for choosing a construction type.

**Key Characteristics:**
- Cool light plaster ground, graphite ink, one chalk-blue action colour.
- Red only for re-check, green only for accepted or paid.
- Tabular, slightly narrow, extra-bold numerals in exactly three sizes.
- Dimension strings (ticked lines) under every size.
- Window drawings in a 2 px pencil line, 45° and 90° only.
- 17 px body text, 44 px minimum targets, 56 px main controls.
- Flat surfaces; shadows only on the bottom sheet and on a lifted, chosen item.

## Colors

A site-wall palette: two plaster greys, three graphites, and three marking colours, each with a pale tint for fills.

### Primary
- **Chalk-Line Blue** (`chalk`): the one action colour. Primary buttons, the active measuring slot, the selected segment, focus rings, links and "how is it calculated" toggles, dimension-string ticks, the text caret. **Deep Chalk** (`chalk-deep`) is its hover and pressed state and the text of the "sent" status. **Chalk Tint** (`chalk-tint`) fills glass in window drawings, cut pieces in bar rows, the chosen type tile, text selection and the focus halo around an active slot.

### Secondary
- **Marking-Crayon Red** (`crayon`): readings that are too far apart, field errors, missing catalogue values, the danger button, "expired". **Crayon Tint** (`crayon-tint`) is the background of warning and error notes.

### Tertiary
- **Tick Green** (`tick`): accepted quotes and recorded payments, nothing else. **Tick Tint** (`tick-tint`) is the accepted pill background.

### Neutral
- **Skimmed Plaster** (`plaster`): the page ground on every screen; also the background of opened explanations inside a sheet or row.
- **Deep Plaster** (`plaster-deep`): segmented-control track, demo banner, draft and rejected pills, sheet top borders, the hatching of masonry and offcuts.
- **Board White** (`board`): raised surfaces that hold content: rows, bar cards, fields, the bottom sheet, the window frame fill.
- **Graphite** (`graphite`): body ink, window drawing lines, the 2 px border of secondary buttons and bars.
- **Soft Graphite** (`graphite-soft`): secondary text, units ("mm"), placeholders, hint lines.
- **Graphite Line** (`graphite-line`): resting field borders, inactive measuring lines, disabled primary buttons, scrollbars.
- **Shell Graphite** (`shell`, `shell-raised`): the sticky top bar and its raised back button.

### Named Rules
**The Chalk Line Rule.** Chalk blue means "this is where you act now". One primary button per screen; the active slot is the only blue slot.

**The Crayon Rule.** Red is only for a value he must re-check or a stop he must fix. Never use it for decoration or emphasis.

**The Tick Rule.** Green appears only once something is accepted or paid.

**The Sunlight Rule.** Body ink on plaster stays near 13:1. Never set running text lighter than Soft Graphite.

## Typography

**Body Font:** Noto Sans, variable (weights 400 to 900, width 62.5% to 100%), bundled with the app, with system-ui as fallback.
**Figure style:** the same family at 87.5% width, weight 800, tabular lining numerals, -0.01em tracking.

**Character:** One sturdy humanist sans for everything. Words are bold and plain; numbers are heavier, narrower and fixed-width, so columns of sizes and prices line up like a ledger.

The root size is 17 px (106.25%), so 1rem is 17 px.

### Hierarchy
- **Figure Large** (800, 2.75rem, 1): the one number he says out loud: the window size on the measuring sheet, the quote total.
- **Figure Medium** (800, 1.5rem, 1.15): reading slots, position prices, units next to a large figure.
- **Figure Small** (800, 1.0625rem, 1.3): sizes in lists, cut lengths, offcuts, formula lines.
- **Headline** (800, 1.5rem): step and screen headings.
- **Title** (800, 1.125rem): top bar title, section headings, button labels (700).
- **Body** (400, 1rem, 1.5): rows, warnings, descriptions.
- **Label** (700, 1rem): field labels and segmented legends.
- **Note** (400 or 600, 0.875rem): hints, errors under fields, top bar subtitle.

### Named Rules
**The Three Numerals Rule.** Numbers use only the three figure sizes. The number he says out loud is always the largest on the screen.

**The Ledger Rule.** Every size, price and length uses the figure style, so digits never shift when a value changes.

## Layout

Phone first. Content sits in one column with a 1rem side gutter. On wider screens the column centres at 48rem (`max-w-3xl`); the login screen centres at 28rem. The construction-type picker is the only grid: two tiles on a phone, three from 640px up.

Screens follow one shape: the sticky graphite top bar, the work in the middle, and a sticky or fixed bottom sheet that holds the result (window size or total) and the one primary action. The sheet respects the safe-area inset.

Spacing rhythm: 0.75rem inside rows and cards, 1rem gutters and sheet padding, 1.5rem between sections. Rows in a list sit 0.75rem apart. Every tap target is at least 2.75rem; buttons and fields are 3.5rem tall.

The measuring screen draws the opening at the places he measures: three width slots across (top, middle, bottom) and three height slots down (left, middle, right), inside a box of at most 19.5rem.

## Elevation & Depth

Flat by default. Depth comes from tone: plaster ground, white board surfaces on top, plaster again for opened explanations inside them. Borders are 2 px solid lines in plaster or graphite, never hairlines.

### Shadow Vocabulary
- **Sheet** (`box-shadow: 0 -6px 20px -8px rgb(35 39 43 / 0.28)`): the bottom sheet that holds the result and the primary action.
- **Lift** (`box-shadow: 0 2px 6px -1px rgb(35 39 43 / 0.22)`): the selected segment and the one opened position row.
- **Active slot halo** (`box-shadow: 0 0 0 4px` Chalk Tint): the measuring slot he is typing into.

### Named Rules
**The Lifted Means Open Rule.** A shadow means "this is open or chosen now". Rows and cards at rest have none.

## Shapes

One radius for almost everything: a gently rounded slot (0.625rem) on buttons, fields, rows, bar cards, notes and tiles. Status pills are fully rounded. Pencil marks are square: drawing lines, bar outlines and the opening reveal use a small 0.125rem to 0.25rem corner or none.

Diagonal hatching is the world's material, not decoration: masonry around the opening, the offcut end of a stock bar, foil in a window drawing, and the demo banner swatch all use a 135° stripe in Deep Plaster or Graphite.

Window drawings use only 45° and 90°. Frames and sashes are rings with mitred corners; the T-mullion butts at 90°. Opening symbols follow the European convention: the triangle points to the hinge, dashes show tilt, the handle sits on the other side. Lines stay 2 px at any size (1.25 px in small thumbnails).

## Components

### Buttons
Big, plain and bold: built to be hit with a thumb.
- **Shape:** rounded slot (0.625rem), 3.5rem tall, 1.25rem side padding, Title type at weight 700, optional icon before the label.
- **Primary:** Chalk Blue with white text. Hover and press go to Deep Chalk. Disabled is Graphite Line.
- **Secondary:** Board White with Graphite text and a 2 px Graphite border; hover Plaster, press Deep Plaster.
- **Quiet:** no fill, Chalk text; hover fills Chalk Tint.
- **Danger:** Board White, Crayon text and 2 px Crayon border; hover Crayon Tint.
- **Focus:** 3 px Chalk outline, 2 px offset, on every control.
- **Inline toggles** ("how is it calculated", "copy previous window"): Chalk text, weight 700, 2 px underline offset 4 px, at least 2.75rem tall.
- **Icon button:** 2.75rem square, rounded slot.

### Chips (status pills)
- **Style:** fully rounded, 1.75rem tall, 0.75rem side padding, 0.875rem at weight 800.
- **State:** draft Deep Plaster, sent Chalk Tint with Deep Chalk text, accepted Tick Tint with Tick text, expired Crayon Tint with Crayon text, rejected Deep Plaster with Soft Graphite text struck through.

### Cards / Containers
- **Corner Style:** rounded slot (0.625rem).
- **Background:** Board White on the Plaster ground; opened explanations inside use Plaster.
- **Shadow Strategy:** none at rest; Lift when a row is open.
- **Border:** none outside; a 2 px Plaster rule separates a row's opened part.
- **Internal Padding:** 0.75rem.
- **Notes:** warnings and errors are Crayon Tint cards with an alert icon in Crayon and a Crayon heading.

### Inputs / Fields
- **Style:** 3.5rem tall, Board White, 2 px Graphite Line border, rounded slot, 1.125rem text. The label sits above in Label type.
- **Focus:** the border turns Chalk Blue.
- **Error:** the border turns Crayon; the message below is 0.875rem, weight 600, Crayon.
- **Hint:** 0.875rem Soft Graphite below the field.

### Segmented choice
A Deep Plaster track with 0.25rem padding; each option is at least 2.75rem tall, weight 700. The chosen option is Chalk Blue with white text and the Lift shadow. Used for the colour row (white, foil outside, foil both sides) and other one-tap choices.

### Navigation
- **Top bar:** sticky Shell Graphite, at least 4rem tall, white Title text truncated to one line, an optional 75% white subtitle, a raised back button (Shell Raised, hover Soft Graphite) and actions on the right.
- **Language toggle:** an underlined bold text button that names the other language.
- **Demo banner:** a full-width Deep Plaster strip with a small hatched swatch and bold text, on every screen of the demo workshop.

### Dimension string (signature)
The mark of the system. A size is written as a figure with a 2 px Chalk line under it and a 0.75rem end tick at each side. Used for the window size on the sheet, sizes in position rows, and under the app name on the login screen. On the measuring screen each reading slot sits on its own ticked line across or down the opening; the active line is Chalk, the others Graphite Line.

### Measuring slot (signature)
A 4.75rem by 3rem Board White box in Figure Medium, centred on its measuring line. Active: Chalk border, Chalk text and the Chalk Tint halo. A reading too far from the others: Crayon border and text. The smallest reading, the one that counts, gets a 3 px Graphite ring with a 2px Plaster gap.

### Bottom sheet (signature)
Board White, 2 px Deep Plaster top border, the Sheet shadow, 1rem padding plus the safe-area inset. It holds a Soft Graphite caption, the result in Figure Large with its unit in Figure Medium, the inline "how is it calculated" toggle, the explanation in a Plaster box, and the full-width primary button.

### Window drawing (signature)
An SVG drawn from inside in Graphite, frame fill Board White (hatched for foil on both sides), glass Chalk Tint. In the type picker each drawing is the button: a Board White tile, Chalk Tint with a 3 px Chalk outline when chosen.

### Bar row (signature)
A stock bar drawn as a 1.25rem strip with a 2 px Graphite outline. Cuts are Chalk Tint segments sized to their length, separated by 2 px Graphite lines; the offcut is hatched and always last. The list of cuts below uses Figure Small, with the offcut in Soft Graphite below a Plaster rule.

### Icons
An authored set on a 24 px grid, one 2.25 px round stroke, drawn like pencil marks. Default size 1.5rem; 1.25rem inline with text.

## Do's and Don'ts

### Do:
- **Do** put every size in a dimension string and in the figure style.
- **Do** keep the number he says out loud in Figure Large (2.75rem) and nothing else that large on the screen.
- **Do** let every size and total open to show its formula or price layers.
- **Do** keep one Chalk Blue primary action per screen, in the bottom sheet when the screen has one.
- **Do** keep tap targets at least 2.75rem and main controls 3.5rem tall.
- **Do** draw windows from inside, with 45° mitres and 90° joints only, in a 2 px non-scaling line.
- **Do** use the 135° hatch for masonry, offcuts and foil.

### Don't:
- **Don't** add a fourth numeral size or set numbers in the body style.
- **Don't** use Crayon Red for anything but a re-check, an error or a stop.
- **Don't** use Tick Green for anything but accepted or paid.
- **Don't** build screens as long labelled forms of fields on white cards; put readings where they are measured.
- **Don't** put shadows on rows or cards at rest.
- **Don't** load fonts, icons or images from another host; the Content-Security-Policy allows only the app itself.
- **Don't** add small uppercase labels above headings.
