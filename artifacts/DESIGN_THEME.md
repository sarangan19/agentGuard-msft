# AgentGuard Design Theme — "Security Terminal"

## Fonts
```
Display:  Saira Condensed — weight 700/800/900, uppercase, tight line-height (~0.92)
Body/Mono: Chivo Mono — weight 300/400/500
Google Fonts import:
  family=Saira+Condensed:wght@700;800;900&family=Chivo+Mono:wght@300;400;500
```

## Color Palette
```css
--bg:    #080A0D    /* near-black, slight blue tint */
--s1:    #0C0F14    /* surface 1 */
--s2:    #111520    /* surface 2 */
--b1:    #1A1F2E    /* border 1 */
--b2:    #252C3F    /* border 2 */
--lime:  #BBFF39    /* PRIMARY accent — electric lime */
--lime2: #8ACC1A    /* lime hover */
--red:   #FF4444    /* danger / block */
--amber: #FFB800    /* warning */
--white: #F0F2F5    /* primary text */
--mid:   #8892A4    /* secondary text */
--dim:   #3A4257    /* muted / decorative */
```

## Aesthetic Rules
- Single accent color only (lime). Never two competing accents.
- All heading text: Saira Condensed, UPPERCASE, tight letter-spacing
- Body text max-width: ~340–380px per column. Never full-width prose.
- Borders everywhere — cards, sections, table rows — using `--b1` / `--b2`
- No rounded corners. Everything is sharp/square.
- No gradient blobs, no glows, no shadows.
- Background grid (optional): 1px lines at 60px intervals, 30% opacity, masked radially
- Scanline overlay (optional): repeating-linear-gradient at 4px intervals, 6% opacity

## Layout Principles
- Two-column hero: content left, live data/feed right
- Section headers: eyebrow (`// LABEL` in lime) + condensed H2
- Content grids: `gap: 1px; background: var(--b1)` — creates hairline dividers between cards
- No centered text blocks. Left-aligned always.
- Stats: Saira Condensed numerals at 2–4rem, label below in 0.6rem uppercase mono

## Component Patterns

### Eyebrow label
```css
font-size: .6rem; letter-spacing: .2em; text-transform: uppercase;
color: var(--lime);
/* prefix with // in dim color */
```

### Tier badges
```css
.tier-AUTO  { border: 1px solid #34D399; color: #34D399; }
.tier-SOFT  { border: 1px solid #FCD34D; color: #FCD34D; }
.tier-HARD  { border: 1px solid #FB923C; color: #FB923C; }
.tier-BLOCK { border: 1px solid #FF4444; color: #FF4444; }
font-size: .55rem; letter-spacing: .1em; text-transform: uppercase; padding: .15rem .45rem;
```

### Buttons
```css
/* Primary */
background: var(--lime); color: #080A0D;
font: Chivo Mono .65rem/500; letter-spacing: .12em; text-transform: uppercase;

/* Ghost */
background: transparent; border: 1px solid var(--b2); color: var(--mid);
hover: border-color: var(--lime); color: var(--lime);
```

### Nav CTA
```css
background: var(--lime); color: #080A0D; /* same as btn-primary */
```

### Cards / feature grid
```css
background: var(--bg); transition: background .2s;
hover: background: var(--s1);
/* Large ghost number in top-left: Saira Condensed 3.5rem, color: var(--b2) */
```

### Report/terminal window
```css
/* Title bar with three dots (macOS style but sharp) */
background: var(--s1); border: 1px solid var(--b1);
title bar: background: var(--b1); padding: .6rem 1.2rem;
dots: #FF5F57 / #FFBD2E / #28C840
```

### Live feed items
```css
border-bottom: 1px solid var(--b1); padding: 1rem 1.5rem;
agent label: .6rem uppercase mid-color
text: .72rem white, nowrap + ellipsis
score: .6rem mid-color
```

## Animation Guidelines
- Counter roll-up: cubic ease-out, ~1600ms, triggered on IntersectionObserver
- Bar grow: scaleX from 0, ~800ms, ease, stagger with animation-delay
- Feed items: slideIn (translateY -8px → 0), .4s ease
- Live dot pulse: opacity 1→0.2→1, 1.4s infinite
- No parallax, no scroll-triggered transforms

## File Naming Convention
- New pages/components → new files (never overwrite `landing.html`)
- Pattern: `page_[name].html` or `component_[name].html`
