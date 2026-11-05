---
name: Valuation Lab
description: A light editorial research workbench for inspectable valuation.
colors:
  paper: "#f7f8f4"
  white: "#fff"
  ink: "#18352f"
  muted: "#596a63"
  line: "#d6dfd7"
  accent: "#176854"
  soft: "#e5eee5"
  warm: "#a64d29"
  focus: "#905018"
  primary-hover: "#104c3e"
  controls: "#edf1e9"
  stale-bg: "#f5e6ca"
  stale-text: "#704b17"
  blocked-bg: "#f3dfd4"
  blocked-text: "#903e21"
  error: "#9b3426"
  band: "#d5e4d7"
  histogram: "#327763"
  tornado: "#779a88"
typography:
  display:
    fontFamily: "Georgia, 'Times New Roman', serif"
    fontSize: "clamp(25px, 2.4vw, 38px)"
    fontWeight: 400
    lineHeight: 1.18
    letterSpacing: "-.025em"
  headline:
    fontFamily: "Georgia, 'Times New Roman', serif"
    fontSize: "25px"
    fontWeight: 400
    lineHeight: 1.25
    letterSpacing: "-.02em"
  title:
    fontFamily: "'Segoe UI', system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 600
  body:
    fontFamily: "'Segoe UI', system-ui, sans-serif"
    fontSize: "14px"
    lineHeight: 1.55
  label:
    fontFamily: "'Segoe UI', system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 600
  metric:
    fontFamily: "Georgia, 'Times New Roman', serif"
    fontSize: "35px"
    fontWeight: 400
    lineHeight: 1.3
  code:
    fontFamily: "Consolas, monospace"
    fontSize: "12px"
    lineHeight: 1.6
rounded:
  field: "3px"
  button: "4px"
  mode: "5px"
spacing:
  compact: "8px"
  field: "9px"
  small: "10px"
  medium: "18px"
  section: "20px"
  spacious: "25px"
  columns: "30px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.white}"
    rounded: "{rounded.button}"
    padding: "9px 14px"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
    textColor: "{colors.white}"
  button-secondary:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.button}"
    padding: "9px 14px"
  input:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    padding: "9px"
  explanation:
    backgroundColor: "{colors.soft}"
    padding: "16px 19px"
  mode-active:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.white}"
    padding: "4px 13px"
---

# Design System: Valuation Lab

## Overview

**Creative North Star: “The Editorial Research Workbench”** is a descriptive name for the implemented direction, not a separately approved brand concept. This light, restrained workspace pairs serif analytical headings with compact system-font controls. Pale paper surfaces, ruled sections and open chart areas support sustained inspection of assumptions and evidence.

This document records the implemented system in `web/style.css`, `web/index.html` and `web/app.js`. The delivery context is Operate mode with confirmed Guided and Advanced views and a direct code-first approach. Reviewer disposition was ship after the mobile-legibility and stale-simulation fixes; this is not a claim of additional user design approval.

**Key Characteristics:**

- Editorial headings and tabular numeric alignment.
- Green base-case marks and terracotta scenario marks.
- Flat, lightly ruled sections with compact forms.
- Visible provenance, unavailable values and stale-result states.

## Colors

The palette is pale botanical paper with deep green ink and a restrained terracotta comparison accent. Frontmatter carries the actual source values.

### Primary

- **Research green (`accent`)** identifies primary actions, links, selected tabs, base-case charts and positive bridge contributions. Its darker hover token applies to primary buttons.
- **Soft green (`soft`)** supports explanations, code records, state labels and tornado tracks.

### Secondary

- **Terracotta (`warm`)** identifies scenario series and negative bridge contributions. Scenario lines are also dashed, so identity does not rely on hue alone.
- **Amber focus (`focus`)** marks keyboard focus. Stale-result amber and blocked-state terracotta each have distinct background and text tokens.

### Neutral

- **Paper** is the page canvas; **white** supports the masthead and editable controls.
- **Ink** is primary text; **muted** supports annotations and labels; **line** draws section boundaries and chart axes.
- **Controls** gives the assumption rail its lightly tinted surface.

**The Series Identity Rule.** Preserve green base and terracotta scenario semantics across chart legends, marks and tables. The sensitivity matrix uses a computed green HSL ramp from lightness 94% to 70%, rather than a categorical status palette.

## Typography

Display and section headings use the serif stack; body text and controls use the system sans stack. Numeric content uses tabular figures. JSON and calculation records use Consolas with a monospace fallback.

The main heading balances text within 28 characters. Body paragraphs cap at 75 characters. Section headings use the headline token, while small component titles use the semibold title token. Knowledge-item headings are serif at 22px. Metric values use the metric token. Labels are compact and semibold; annotations generally range from 10px to 12px. Code records use a slightly roomier line height of 1.65.

On narrow screens, the main heading is 30px, section headings 23px, metric values 26px, and chart text 12px. These are implemented overrides, not a universal proportional type scale.

## Layout

The centered application shell has a maximum width of 1900px and a 285px assumption rail beside a flexible, zero-minimum-width workspace. The masthead is 78px high. Desktop workspace padding is 35px 38px 20px. Metric strips have three equal columns with 25px gaps; paired analysis sections have two equal columns and 30px gaps. Forms use three columns, while search uses a 2:1 split.

At widths of at least 1500px, workspace horizontal padding increases to 55px and charts cap at 1150px. At 1150px and below, the rail narrows to 250px, paired sections stack, forms use two columns, and the edition label disappears. At 720px and below, the rail moves above the workspace, its driver controls use two columns, workspace padding becomes 25px 18px, and the masthead becomes 66px high. Knowledge rows and search stack; workflow descriptions move beneath their labels; export controls wrap. Metrics remain in three columns and forms remain in two.

Tables and the horizontal tab row scroll within their containers. Tables preserve numeric alignment and nonwrapping values. Chart SVG view boxes are generated from their available container width, with a minimum plotting width of 320px, and redraw after a 150ms resize debounce.

## Elevation & Depth

The implementation has no box shadows. Depth comes from the white masthead and fields, tinted assumption rail, soft explanatory surfaces, and thin ruled boundaries. Sections remain visually open instead of becoming raised cards. The active mode is a dark inset selection within a pale segmented container.

## Shapes

Controls have gently softened corners: fields use the field radius, buttons the button radius, and the mode container the mode radius. Section surfaces and tables are square and ruled. Legend dots are circular. Primary and secondary buttons use 1px borders; keyboard outlines sit 4px outside controls. Charts use slender strokes and small focusable data points rather than heavy decoration.

## Components

### Buttons and fields

Primary buttons carry the green action color. Secondary buttons use white surfaces, thin line-colored borders, and soft-green hover surfaces. Standard buttons have a 40px minimum height; compact mode, text and knowledge controls deliberately use smaller observed variants. Disabled buttons have opacity 0.45 and the default cursor. Focusable controls and links receive a 2px focus-colored outline with a 4px offset.

Fields have white backgrounds, thin borders and 9px internal padding. Driver rows pair a numeric percent input with a synchronized range slider. Driver edits recalculate after 350ms; raw JSON edits require the explicit apply action. Text areas resize vertically. Advanced mode reveals the complete case and correlation controls while hiding guided explanation text.

### Navigation and disclosure

Guided and Advanced controls expose their selected state through `aria-pressed`. Five analysis-view buttons use `aria-current="page"` and an accent underline for the current view. Overflow stays horizontally scrollable. Native disclosure sections reveal tables, full method text and model checks. A keyboard-visible skip link targets the workspace.

Views reveal through a 220ms ease-out opacity animation from 0.8 to 1. Reduced-motion preferences remove this animation. No additional animation vocabulary is implemented.

### Analytical displays

Metric strips use serif values, small descriptive labels and vertical separators. Forecast charts use green solid base lines and dashed terracotta scenario lines, with keyboard-focusable points and text descriptions. Exact forecast values remain available in a table. Histogram bars and fan bands have their own green tokens; their supporting tables expose counts and percentile data.

Sensitivity cells are buttons that apply WACC and terminal-growth assumptions. Unsupported combinations say “Unavailable.” The equity bridge uses green and terracotta bars with a ruled total row. Tornado tracks show a muted-green range and an ink-colored base marker, with lower-input and higher-input values printed alongside.

### Research rows and feedback

Knowledge entries, saved runs and evidence entries use ruled rows rather than elevated cards. Workflow states use compact labels, with a distinct blocked treatment. Status messages use live-region semantics. Errors have a red text treatment, while stale-result notices use amber surfaces and explanatory text.

Case changes mark displayed figures stale, disable exports and detach the prior evidence target. Simulation-setting edits mark the prior distribution stale and prevent saving it until rerun. Tab changes and resizing do not redraw a stale simulation as current. Macro and method edits replace the result message with a recalculation prompt. Keep these validity states attached to the affected result, not merely to the input control.

## Do's and Don'ts

- **Do** reuse the existing serif/sans pairing, paper surfaces and ruled layout.
- **Do** retain exact-value tables, text labels and keyboard-accessible chart data.
- **Do** preserve series identity and clearly mark unavailable or stale outputs.
- **Do** keep responsive tables and navigation scrollable inside the workspace.
- **Don't** imply that a saved or simulated result reflects edited inputs before recalculation.
- **Don't** use color alone to distinguish the base and scenario lines.
- **Don't** introduce shadows or a new card hierarchy as though they were incumbent design tokens.
- **Don't** treat this extracted documentation as evidence of an unrecorded user design approval.
