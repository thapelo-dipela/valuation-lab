---
name: Valuation Lab
description: A compact dark financial workspace for learning and inspectable valuation.
colors:
  paper: "#0d1117"
  white: "#161b22"
  ink: "#e6edf3"
  muted: "#9da7b3"
  line: "#30363d"
  accent: "#58a6ff"
  soft: "#21262d"
  warm: "#f78166"
  focus: "#58a6ff"
  masthead: "#010409"
  primary: "#238636"
  primary-hover: "#2ea043"
  on-primary: "#fff"
  positive: "#3fb950"
  negative: "#f85149"
  brand-green: "#7ee787"
  input-border: "#484f58"
  placeholder: "#8b949e"
  selection: "#264f78"
  selected-statement: "#263749"
  selected-nav: "#79c0ff"
  warning: "#f2cc60"
  stale: "#e3b341"
  blocked: "#3d2b14"
  error-text: "#ffa198"
typography:
  display:
    fontFamily: "'Segoe UI', system-ui, sans-serif"
    fontSize: "24px"
    fontWeight: 600
    lineHeight: 1.18
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "'Segoe UI', system-ui, sans-serif"
    fontSize: "18px"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "0"
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
    fontFamily: "'Segoe UI', system-ui, sans-serif"
    fontSize: "27px"
    fontWeight: 400
    lineHeight: 1.3
rounded:
  control: "6px"
  mode: "5px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  panel: "20px"
  workspace: "24px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.control}"
    padding: "7px 13px"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
  button-secondary:
    backgroundColor: "{colors.soft}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "7px 13px"
  field:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "8px 10px"
  panel:
    backgroundColor: "{colors.paper}"
    rounded: "{rounded.control}"
    padding: "20px"
---

# Design System: Valuation Lab

## Overview

**Creative North Star: GitHub-style dark financial workspace.** This is the user's selected visual direction: a compact, approachable workspace for teenage finance learners, students and analysts. Keep original Valuation Lab branding, plain financial language, visible evidence and inspectable assumptions. Guided and Advanced views share the same visual system.

This document records the implemented interface, not a speculative comp. `web/index.html` loads `web/style.css` first and `web/workspace.css` second; the workspace overrides define the approved dark identity. The legacy `--paper`, `--white` and `--serif` names remain compatibility aliases: paper and white are dark surfaces, and serif resolves to the sans-serif stack.

Key characteristics:

- Dense editable financial tables, compact controls and horizontal tabs.
- Sans-serif headings and tabular numbers.
- Dark tonal surfaces, blue links and focus, green actions, green/red candlesticks.
- Explicit currency, unit and rate labels next to financial work.

## Colors

Use the frontmatter values as the normative palette. Near-black paper forms the workspace; the deeper masthead anchors navigation. White is the raised dark surface for table headers, notices and metric strips. Soft separates hover and selected controls; line provides restrained dividers. Ink and muted distinguish primary information from explanatory text.

Blue accent is for links and focus. Green primary is for calculation and confirmation actions; brighter brand-green identifies the original Lab wordmark. Warm coral marks the selected horizontal tab. Positive and negative are the candlestick and direction colors. Warning, stale and error-text keep status messages readable on dark surfaces; preserve explanatory text so color is not the only signal.

## Typography

Use Segoe UI with system-ui and sans-serif fallbacks throughout normal financial work. There is no editorial serif hierarchy. Body is 14px/1.55 with tabular numerals; headings are 24px and 18px at weight 600. Smaller titles are 14px. Standard labels are 12px; workspace tool and method labels are 13px. Financial table text is 12px, with accounting headers at 13px. Metric strips use 27px values; market facts use 24px bold values. Explanatory paragraphs normally cap at 75ch; accounting currency notes cap at 90ch.

At 700px and below, the main heading is 20px, brand 17px and market facts 21px. Keep labels legible rather than replacing them with unexplained icons.

## Layout

Desktop uses a 232px sidebar plus a flexible main workspace without a maximum shell width. The masthead is 64px high. Main padding is 24px 28px; sidebar padding is 22px 16px. Panels use 20px padding, with 20px gaps between paired regions. Toolbars wrap with 12px gaps. Editable accounting cells use 4px 8px padding; ordinary cells use 11px 14px. Numeric columns align right, descriptive first columns align left. Scroll containers preserve table structure and keep the first column sticky.

At 1000px and below, the sidebar becomes 190px, main padding becomes 20px 16px and method fields stack. The inherited base layout also collapses paired regions at 1150px and switches the shell to a vertical flex layout at 720px. At 700px, the workspace uses a single block layout with 18px 12px main padding, 14px panel padding and a 58px masthead. Sidebar actions are hidden, while horizontal tabs remain scrollable and metric strips use two columns. Mobile buttons have a 40px minimum height; desktop buttons have a 36px minimum height. Preserve these actual cascade boundaries when extending the interface.

## Elevation & Depth

Depth comes mainly from dark tonal surfaces and one-pixel borders. Buttons alone use a small structural shadow (`0 1px 0 #010409`); text buttons, tabs and side navigation remove it. Avoid floating dashboard cards and large decorative shadows.

Views retain the base 0.22s ease-out opacity reveal from 0.8 to 1, disabled for reduced motion. Pressed buttons translate down by 1px. Do not introduce ornamental motion.

## Shapes

Controls, fields, panels, notices and metric strips have 6px corners. The mode switch container retains 5px corners. Horizontal tabs are square with a 2px coral selected underline. Borders organize the financial workspace; shapes remain simple and compact.

## Components

### Buttons

Primary actions use green primary, a primary-hover border, white text and 7px 13px padding. Hover uses primary-hover. Secondary controls use soft, then line on hover with a placeholder-colored border. Shared focus-visible styling is a 2px blue outline offset by 4px. Disabled buttons retain the base 0.45 opacity and default cursor. Preserve explicit verb labels.

### Fields and editable tables

Fields use the paper surface, input-border stroke, 6px corners and 8px 10px padding. Focus changes the border to blue and keeps the shared visible outline. Accounting inputs are 128px wide, right-aligned and transparent at rest; focus reveals a raised surface and blue border. Table headers use the raised surface and weight 500. Rows gain the raised surface on hover. Use horizontal overflow for wide statements.

### Navigation

Horizontal tabs have 12px 14px padding, a transparent background and coral selected underline. Sidebar items are flat, left-aligned and regular-weight; selected items use soft with selected-nav text. Statement buttons wrap and use selected-statement with a blue border when pressed. Preserve current/pressed semantics.

### Panels, notices and results

Panels have a one-pixel line border, 6px corners and paper background. Metric strips and notices use the raised surface. Status text is 12px in an 8px 10px bordered container; error state pairs error-text with a negative border. Empty status elements disappear. Calculator inputs and outputs are readable fields and labelled results; code editors are not the normal calculation interface.

### Financial context and charts

Green candles close above their open; red candles close below. Wicks and bodies must use matching direction colors against dark gridlines. Chart labels use muted sans-serif text. Show source and display currencies explicitly: statement conversion is display-only, while valuation and calculators retain labelled source units. Normal calculator rates are percentages; beta and multiples are ratios. Keep these distinctions in nearby labels and help text, not color alone. Do not imply that a display currency selection changes source inputs or calculator denominations.

## Do's and Don'ts

- **Do** preserve the original Valuation Lab wordmark and dark workspace identity.
- **Do** use compact sans-serif controls, editable tables, tabular numbers and clear focus states.
- **Do** keep units, source currencies, rate conventions and warning explanations visible.
- **Do** implement and review the working interface directly; this direction is code-led.
- **Don't** restore the rejected light editorial palette or serif display typography.
- **Don't** substitute GitHub logos or branding for the original product identity.
- **Don't** turn financial input into a code editor or hide meaning behind decorative charts.
