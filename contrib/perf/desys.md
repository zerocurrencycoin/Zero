# Design System — Ice-Blue Light Theme

A cool, calm light theme built on one accent family. Surfaces are layered by
brightness rather than shadow; a single deep-blue hue carries links and
selection; the navigation and two utility surfaces sit deliberately off-palette
for contrast.

## Theme & ideas

- **Ice-blue light base, white lift.** The page rests on a faint cool grey-blue.
  Raised elements — panels, wells, cards — are lifted to pure white against it.
  Depth reads from the surface/panel brightness gap plus hairline borders, not
  from drop shadows.
- **One accent family.** A single deep blue is the entire accent language: it
  colors links, darkens on hover, and reappears at low opacity as a selection
  wash. Nothing competes with it inside the content area.
- **Intentional off-palette breaks.** The navigation bar is *not* themed into the
  blue system — it stays plain white-on-black and inverts to black-on-white on
  hover, a hard contrast against the soft page. Two utility surfaces (search and
  status/connection boxes) use an olive green as a second, deliberately
  unrelated accent so functional controls read as distinct from content.
- **Calm by default, contrast on demand.** Resting state is low-contrast and
  quiet (cool greys, near-black text); interaction and emphasis introduce the
  sharp pairs (black/white nav, blue links, olive controls).

## Typography

- **Primary face: Ubuntu.** A humanist sans-serif — warm, rounded, slightly
  geometric — set as the body family for a friendly, modern tone that suits the
  soft cool palette.
- **System fallback: generic `sans-serif`.** When Ubuntu is unavailable the
  stack falls through to the platform's default sans-serif (the OS UI face),
  so text always renders in a clean grotesque rather than a serif.
- **Google-font sourcing.** Ubuntu is a Google Fonts family; the intent is to
  load it from Google's CDN with the local/system sans-serif as the graceful
  default while the web font arrives or if it never does.
- **Recommended stack:**

  ```css
  font-family: "Ubuntu", sans-serif;
  ```

- **Type color, not type scale.** The system governs text *color* (near-black
  body, mid-grey muted) and leaves the size/weight scale to the base — headings
  and body share the same near-black ink; secondary text steps down to grey.

## Color palette

### Core (cool neutrals + blue accent)

| Token | Hex | Use |
|---|---|---|
| Page surface | `#eef1f4` | App background — faint cool grey-blue ("ice-blue") |
| Panel | `#ffffff` | Raised surfaces: panels, wells, cards, status blocks |
| Text | `#1f2933` | Primary body text and headings (near-black, cool) |
| Muted | `#6b7480` | Secondary / de-emphasized text |
| Line | `#dbe4ec` | Borders, horizontal rules, table separators |
| Link | `#1a5e9c` | Links, accent text |
| Link hover | `#0f3f6e` | Link hover / focus (darker blue) |
| Selection wash | `rgba(26, 94, 156, .08)` | Selected-item background — link blue at 8% opacity |

The selection wash is the link hue (`#1a5e9c` → `rgb(26, 94, 156)`) dropped to
8% alpha, so selection and links read as one family.

### Navigation (off-palette, high contrast)

| Token | Hex | Use |
|---|---|---|
| Nav background | `#000000` | Top navigation bar resting state |
| Nav text | `#ffffff` | Nav item labels (white on black) |
| Nav hover background | `#ffffff` | Nav item on hover/focus — inverts to white |
| Nav hover text | `#000000` | Nav label on hover/focus — inverts to black |

The nav is a pure black/white invert pair, intentionally outside the blue system
for maximum separation from content.

### Olive utility accent

| Token | Hex | Use |
|---|---|---|
| Olive | `#597338` | Functional control surfaces — search field, status/connection box |

A muted olive green — the only warm hue in the system. It marks utility
controls (search input, connection-status surface) as a distinct functional
class, set apart from both the cool content palette and the black/white nav.
Used as a solid fill behind white/light text.

## Palette at a glance

```
ice-blue page  #eef1f4   ░  cool grey-blue surface
panel white    #ffffff   █  raised
text           #1f2933   █  near-black ink
muted          #6b7480   ▓  grey secondary
line           #dbe4ec   ░  hairline borders
link           #1a5e9c   █  deep blue accent
link hover     #0f3f6e   █  darker blue
nav            #000000 / #ffffff   black ⇄ white invert
olive          #597338   █  utility-control fill
```
