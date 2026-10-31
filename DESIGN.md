---
name: "NodeSnap architectural studio"
description: "A calm architectural exhibition for exploring one saved building revision."
colors:
  charcoal: "#202923"
  canvas: "#e9e9e1"
  paper: "#fcfcf8"
  panel: "#f6f6f0"
  ink: "#24332d"
  muted: "#59655b"
  accent: "#2f6e52"
  line: "#d9ded5"
  action: "#375d3f"
  action-hover: "#264a30"
  action-ink: "#f4f7ef"
  control-hover: "#dfe6dc"
  focus: "#438866"
  room-selected: "#e0e9da"
  room-selected-ink: "#305b3c"
  stone-swatch: "#c8c5b7"
  timber-swatch: "#b28d62"
  metal-swatch: "#4d5950"
  glass-swatch: "#bad0c8"
typography:
  display:
    fontFamily: "Geist, sans-serif"
    fontSize: "29px"
    fontWeight: 500
    lineHeight: 1.16
    letterSpacing: "-0.04em"
  headline:
    fontFamily: "Geist, sans-serif"
    fontSize: "28px"
    fontWeight: 500
    lineHeight: 1.2
    letterSpacing: "-0.025em"
  model-title:
    fontFamily: "Geist, sans-serif"
    fontSize: "24px"
    fontWeight: 450
    letterSpacing: "-0.035em"
  title:
    fontFamily: "Geist, sans-serif"
    fontSize: "19px"
    fontWeight: 500
    lineHeight: 1.2
    letterSpacing: "-0.025em"
  body:
    fontFamily: "Geist, sans-serif"
    fontSize: "13px"
  conversation:
    fontFamily: "Geist, sans-serif"
    fontSize: "12px"
    lineHeight: 1.7
  label:
    fontFamily: "Geist, sans-serif"
    fontSize: "11px"
  compact-label:
    fontFamily: "Geist, sans-serif"
    fontSize: "10px"
  mono:
    fontFamily: "Geist Mono, monospace"
    fontSize: "10px"
rounded:
  tag: "3px"
  selection: "4px"
  control: "5px"
  send: "6px"
  floating-group: "7px"
  message: "10px"
  composer: "12px"
spacing:
  4: "4px"
  8: "8px"
  12: "12px"
  16: "16px"
  20: "20px"
  24: "24px"
  32: "32px"
components:
  button-primary:
    backgroundColor: "{colors.action}"
    textColor: "{colors.action-ink}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "0 14px"
  button-primary-hover:
    backgroundColor: "{colors.action-hover}"
  button-secondary:
    textColor: "{colors.ink}"
    typography: "{typography.compact-label}"
    rounded: "{rounded.control}"
    padding: "0 12px"
  button-export:
    backgroundColor: "#d3e5c7"
    textColor: "#293d2a"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "0 14px"
  button-send:
    backgroundColor: "#345f44"
    textColor: "#fff"
    rounded: "{rounded.send}"
    width: "32px"
    height: "32px"
  input-edit:
    backgroundColor: "{colors.paper}"
    textColor: "#304e32"
    rounded: "{rounded.control}"
  navigation-tab:
    textColor: "{colors.muted}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "0 11px"
  navigation-tab-active:
    backgroundColor: "#e9eee4"
    textColor: "#284c34"
  state-warning:
    backgroundColor: "#f1ead6"
    textColor: "#765c38"
    typography: "{typography.compact-label}"
    rounded: "{rounded.selection}"
    padding: "5px 8px"
  sheet-preview:
    backgroundColor: "#fffffc"
    textColor: "#4d6643"
    padding: "20px 17px"
  composer:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.composer}"
    padding: "12px 11px 8px"
  room-row:
    textColor: "{colors.ink}"
    typography: "{typography.compact-label}"
    rounded: "{rounded.selection}"
    padding: "9px 3px"
  room-row-selected:
    backgroundColor: "{colors.room-selected}"
    textColor: "{colors.room-selected-ink}"
---

# Design System: NodeSnap architectural studio

## Overview

**Creative North Star: "The Architectural Exhibition"**

NodeSnap frames an editable building as an architectural exhibition: charcoal navigation, a light mineral model table, warm physical materials and a restrained green accent. The tone is precise and approachable, with the building and conversation carrying the experience.

The interface uses compact controls, quiet panel dividers and generous space around the model. Stone, timber, metal and glass belong to the architectural subject; their visual richness does not require a busier application shell. Motion reveals the accepted geometry and the arrival of a response.

**Key Characteristics:**

- Charcoal frame and layered ivory work surfaces.
- Green action, selection and focus treatments with text and shape cues.
- Geist typography with tabular measurement numerals.
- Physical architectural materials and restrained interface depth.
- Revision-aware model assembly with a settled reduced-motion presentation.

This record describes the shipped application in `apps/web/app`, principally `globals.css`, `page.tsx`, `components/NewDesign.tsx`, `Plan2D.tsx`, `Villa3D.tsx` and `layout.tsx`. The confirmed direction remains in `.impeccable/surfaces/workspace.md` and `.impeccable/surfaces/new-building.md`; product scope remains in `PRODUCT.md`. Tokens above describe reusable implementation values, not an expanded engineering capability claim.

## Colors

The palette combines a mineral neutral field with one calm green family. The frontmatter is the normative token list; the sidecar's generated tonal ramps are preview aids, not additional application tokens.

### Primary

- **Mineral Green** (`accent`): caret and architectural plan selection stroke.
- **Action Green** (`action`, `action-hover`, `action-ink`): review-package actions with a darker hover response.
- **Selection Greens** (`room-selected`, `room-selected-ink`): selected room rows; nearby green tints distinguish navigation and floor states.
- **Focus Green** (`focus`): the shared visible keyboard outline.

### Neutral

- **Charcoal Frame** (`charcoal`): project and revision navigation.
- **Mineral Table** (`canvas`): model surroundings and application backdrop.
- **Paper** (`paper`): toolbars, floating controls and input surfaces.
- **Warm Panel** (`panel`): conversation and contextual inspector.
- **Deep Ink** (`ink`), **Muted Ink** (`muted`) and **Fine Divider** (`line`): readable hierarchy and panel separation. Muted Ink records the shipped contrast correction.
- **Control Hover** (`control-hover`): the shared enabled-button hover fill.
- **Stone, Timber, Metal and Glass** (`*-swatch`): the four inspector material samples. These are UI swatch values, not renderer material base colors; the renderer varies its materials with the saved finish palette.

Warm amber-brown fills identify warning and error content; recording uses a red-brown indicator. These are semantic feedback states rather than additional brand accents. Status meaning is also written in text.

**The Material and Interface Rule.** Use the green family for interface emphasis; keep stone, timber, metal and glass variation attached to the architectural model and its material previews.

## Typography

**Display and body:** Geist, loaded with Next's font integration and exposed through `--font-geist-sans` / `--font-body`, with a sans-serif fallback. **Revision hashes and code:** Geist Mono through `--font-geist-mono`, with a monospace fallback.

The hierarchy is compact, sentence case and primarily regular to medium weight. Headings generally use weight 500 and slightly tightened tracking; strong quantities use 550. Values use tabular numerals in property rows, floor summaries, quantities and drawing zoom.

- **Display:** conversation introduction uses the frontmatter display role; it grows to 32px at wide desktop and is 31px on mobile.
- **Headline:** evidence and document headings use the headline role, constrained to 22ch; supporting text is constrained to 60ch. They become 25px at the compact desktop breakpoint and 27px on mobile.
- **Model title:** 24px normally, 28px at wide desktop, 21px on compact desktop and 22px on mobile.
- **Title:** contextual object heading is 19px normally, 17px on compact desktop and 24px in mobile Details.
- **Body and conversation:** the shell body is 13px. Conversation messages are 12px at base, 13px on wide desktop and mobile; paragraph line height is 1.65. The message container declares 1.7, while its paragraphs retain the global paragraph line height.
- **Labels:** most controls use 10–12px. Secondary technical annotations are smaller in the shipped workspace; those context-specific sizes are not a universal body-text standard.

## Layout

The current workspace uses a full-height grid (`100dvh`) with independent scrolling conversation, inspector and document content. The model area takes the flexible center column. The following are observed workspace rules, not a requirement that every future NodeSnap surface copy this composition.

| Viewport | Shipped layout |
| --- | --- |
| Base desktop | Columns 310px / flexible center / 276px; rows 66px / flexible body / 29px. |
| At least 1600px | Columns 335px / flexible center / 300px; larger model and introduction titles. |
| At most 1250px | Columns 280px / flexible center / 236px; inactive view labels hide, leaving icons and the active label. |
| 761–1000px | Conversation 270px; inspector leaves the grid and becomes a 270px right overlay between top 122px and bottom 29px; view labels are visible. |
| At most 760px | One column; rows 57px / 42px / flexible body / 28px. Model, Chat and Details switch the active work area. |

Desktop conversation and inspector can collapse. Mobile switching retains the current in-memory revision, selected object and view. Selecting a room in the mobile model keeps Model visible; opening Details shows that room at the top of the inspector. Switching floors clears the room selection and changes the 3D presentation to cutaway. Project and conversation persistence are provided by the application; the visual tabs are not documented as persistent user preferences across reloads.

The desktop toolbar and panel heading are 56px high; the model toolbar becomes 46px on mobile. The floor strip is 69px on desktop and 62px on mobile. Its level list scrolls horizontally while the unit selector stays outside the scrolling area. Level buttons retain their width instead of compressing as floors are added; the active level scrolls into view instantly. Document content uses 36px 38px padding, then 30px 22px at compact desktop and 25px 20px on mobile. The two-column package overview becomes one column on mobile and hides the illustrative cover thumbnail; the actual PDF preview remains available at 420px high.

Spacing is practical rather than a strict multiple-only scale: the reusable steps above coexist with optical values such as 7px icon gaps, 17px toolbar padding and 23px floor-strip padding. Global buttons/selects have a 34px minimum; individual controls deliberately override it, including 32px send, 36px secondary actions, 39px package actions, 44px floor options and 43px mobile room rows. Control size is variant-specific.

The plan is a scrollable SVG sheet with explicit zoom/fit controls. Its final stylesheet overrides remove the earlier sheet max-width and centered flex layout so enlarged drawings remain reachable.

## Elevation & Depth

Persistent panels are flat and separated by one-pixel dividers. The canvas is a tonal stage; soft shadows lift floating model modes, zoom tools, paper previews and the temporary tablet inspector. Three-dimensional depth comes from actual geometry, orthographic lighting, material response and scene shadows.

- **Floating tools:** `0 8px 30px #22352a15` (the shared `--shadow`).
- **Plan paper:** `0 5px 20px #253d2010`.
- **Document cover:** `0 8px 28px #243d1b0b`.
- **Tablet inspector:** `-10px 0 30px #253b2014`.
- **Camera tools:** `0 4px 16px #323b3814`.

**The Quiet Frame Rule.** Use tonal surfaces and fine dividers for persistent panels; reserve soft shadows for floating tools, drawing sheets and the temporary inspector overlay.

## Shapes

Controls are compact, softly squared rectangles. Five-pixel corners recur on navigation, selectors and actions; selected list rows and drawing toggles use four pixels. The composer is more generously rounded (12px), the model-mode group uses seven pixels and the send control uses six. Tags use three pixels. The paper preview and major panel boundaries remain square. The user message is asymmetric (`10px 10px 2px 10px`), while avatars and small status dots are circular.

These are observed variants, not a single radius applied indiscriminately. Architectural silhouettes and drawing lineweights come from the canonical geometry and its rendering rules.

## Components

### Buttons and focus

Primary package actions use Action Green, light text, five-pixel corners, horizontal 14px padding and a 39px minimum height. Secondary actions have a fine green-gray border, transparent resting background, horizontal 12px padding and a 36px minimum height. Export is a pale-green control inside the charcoal header; send is a compact dark-green square with an inline arrow icon.

Enabled buttons receive their class-specific hover or the shared Control Hover fill. Background, color and opacity transition over 0.18s. Disabled buttons use a not-allowed cursor and 0.4 opacity; send uses 0.35. The shared keyboard focus outline is two pixels with a three-pixel offset. Plan selection has an SVG-specific focus stroke rather than a CSS outline.

### Inputs and conversation

The composer uses Paper, a subtle border and 12px corners. Focus within changes the border to Accent; its textarea suppresses its individual outline so the whole composer carries focus. The textarea is at least 65px high, 12px at desktop and 14px on mobile. Numeric edit fields pair an unbordered, tabular-number input with an attached pale-green Apply button inside one five-pixel wrapper. Values are labeled and units remain visible.

New-building brief entry is a larger variant of the paper composer, with a visible label and an Accent outline around the whole field on focus. Text and voice share an editable textarea; transcription fills it before the user submits. Recording, transcription and request states are written beside their controls. Clarifications stay inline, and failed requests retain the submitted brief for retry. Starting ideas fill the field for editing. The entry page's composition and empty-sheet treatment remain defined in its surface brief rather than becoming workspace-wide layout rules.

Messages are vertically separated, with a tinted asymmetric bubble for the homeowner and an author line for the studio. New messages enter over 0.35s with `cubic-bezier(0.16, 1, 0.3, 1)`, moving upward from 9px and removing a 1.5px blur. Pending dots pulse over 1.2s with 0.15s stagger; the header's active job dot uses 1.4s. Recording uses a one-second dot pulse and a 0.8s alternating waveform. These indicators accompany real application states.

### Navigation, floors and room selection

Every visit starts at the homepage: an open ivory surface, a large Geist heading, one green new-house action, and a list of saved buildings alongside it. The example villa is a separate optional action; no house rendering appears before selection. On mobile, the choices stack and the saved list remains fully accessible. Explicit Home controls return from the brief or workspace, with keyboard focus moved to the destination. New-project creation and reopening retain their existing controllers and session ownership.

Model, Plan, Structure, Systems and Documents share a compact navigation family. Selected view, model mode and floor controls add tinted green fill and stronger text; view/mode/floor buttons expose pressed state. Floor controls keep their label and elevation together; elevations remain displayed in metres to two decimal places, including an explicit plus sign for nonnegative values. The strip is generated from the current snapshot and ends with a plus-icon action labeled “Add another level.” This action uses the shared focus treatment, is disabled while work is pending, and adds a floor below the roof using the top floor’s layout. Its minimum width is 38px; normal floor buttons are 76px at base and 57px at compact/mobile widths. On narrow screens active view labels remain visible alongside the icon.

After an accepted revision adds a level, that level becomes active, room selection clears, and the workspace switches to Exploded 3D with Model visible on mobile. A surviving active floor remains selected. If undo or another accepted revision removes it, the nearest surviving living floor below its previous elevation becomes active. If none is available, the fallback is Ground, then the first surviving living floor, then the first remaining level. A room selection that no longer exists also clears. Living-floor and bedroom counts in the brief, and living-floor/principal-room counts in the inspector, are calculated from the current snapshot.

For a selected living floor other than Ground, the inspector includes a **Building levels** section with a minus-icon “Remove {floor label}” action. It reuses the outlined secondary-button style and is disabled while work is pending. The nearby explanation states that removal deletes the floor and its rooms, lowers the levels above and can be undone.

Room selection shares a stable entity ID between model, plan, room list and inspector. It opens the Design inspector tab, restores its scroll position to the top and selects the object's floor. Plan polygons support Enter/Space selection, show a green-tinted fill and stronger stroke, and provide a selected-object drag preview before the typed move command is committed. Room rows use the selected colors above; exact area and dimensions remain in the inspector. The 3D renderer uses its own physically shaded green selection materials rather than substituting UI swatch values directly.

### Feedback, document surfaces and quantities

Statuses appear as compact text tags with green or warning tints, accompanied by explicit result and scope text. Document content uses a square paper cover, restrained shadow, revision label, coverage rows and an actual embedded PDF. Property and quantity rows use fine dividers, aligned labels and tabular values; narrow layouts can wrap long values.

### Revision assembly and reduced motion

The signature assembly animates actual canonical floor groups. Each level is delayed by 0.12s and settles over 1.1s using exponential ease-out, from 2.5% vertical scale and a 0.8m display offset. A changed revision, replay request or mode remounts this sequence. Building, Cutaway and Exploded are presentation modes; exploded display adds 3.5m per elevation-sorted floor index without changing saved geometry. The orthographic camera fits the current footprint and rendered vertical extents, including exploded offsets, rather than assuming the original floor count. Its vertical target is the midpoint of those extents; camera distance, far clipping, lighting and fog adapt to the resulting height.

With reduced motion, CSS animations/transitions are disabled, conversation scrolling is instant and level assembly resolves directly to its final state. User-driven orbit controls still use damping in the shipped renderer. The record therefore does not claim that all camera movement disappears. Missing or mismatched architectural geometry displays an unavailable state; it is not replaced with an invented building.

## Do's and Don'ts

### Do:

- Do reuse the current semantic colors and Geist hierarchy when extending the studio.
- Do retain a clear selected state in the model or plan, the room list and the contextual inspector.
- Do show exact selected-room quantities in the inspector when drawing labels become small.
- Do preserve revision identity and visible missing-evidence states beside architectural output.
- Do respect reduced motion for assembly, message entrances, pending indicators and conversation scrolling.

### Don't:

- Don't introduce a second promotional accent into the quiet application frame.
- Don't use presentation furniture or finishes as evidence of canonical geometry, material performance or engineering approval.
- Don't replace responsive workspace switching with a compressed three-column mobile layout.
- Don't use the smallest existing technical annotations as the default size for new body copy.
