# yt-dlp-gui Design System — macOS Edition

> **Style:** Modern macOS (Sequoia-era "Liquid Glass" + classic HIG)
> **Color strategy:** **Hybrid C** — YouTube red is the *brand & download
> semantic* color (CTA / progress / brand chip / running indicator).
> macOS system blue is the *navigation semantic* color (selection / link /
> focus ring). They never share the same surface.
> **Scope:** Tauri 2 + Vue 3 desktop, designed to feel native on **macOS**
> while remaining presentable on Win11 / Linux GTK.
> **Token implementation:** `src/assets/theme.css` (refactor target)
> **Generated with** `ui-ux-pro-max-skill` (style domain matched Glassmorphism +
> VisionOS-Spatial as the closest archetypes) + Apple HIG conventions.

This is the **official** design system for the project. The earlier
`docs/design-system.md` (YT-red only, no macOS chrome) has been retired.

---

## 0. Five Inviolable Principles (macOS edition)

1. **Defer to the system.** Use the OS fonts and the OS appearance (light /
   dark / auto). Use macOS *blue* for navigation semantics (selection / link
   / focus) so users feel "this is a Mac app". Use YouTube *red* only for the
   one category-defining action — download.
2. **Translucency is meaning, not decoration.** Use vibrancy (`backdrop-filter`)
   for surfaces that **layer above other content** — sidebar, toolbar, popover.
   Don't blur the main canvas; users want focus.
3. **Specific verbs over generic.** "Download", "Discard", "Pause" — not
   "OK / Cancel". HIG §Buttons.
4. **The pointer is precise.** Hit areas can be smaller than touch (28pt is
   enough for a toolbar item). Don't import phone metaphors.
5. **One window, one job.** No tabbed workspaces inside the window. Each
   download list is the focus; settings are a separate sheet or window section.

---

## 1. Color System

macOS colors are **semantic** (not hex constants) and **theme-adaptive**.
Every named color has a Light and Dark value, and both must be tested.

### 1.1 Two-axis accent model (Hybrid C)

We carry **two separate accent identities**. They never appear on the same
surface. This split is what lets a category-distinct brand color (red) coexist
with macOS native chrome.

| Axis | Token family | Used for |
|---|---|---|
| **Brand / Download** | `--brand-*` (YouTube red) | Primary CTA ("Download" / "Start Download"), progress bar fill, running-task pulse indicator, brand chip in TopBar |
| **Navigation / Selection** | `--accent-*` (macOS system blue) | Selected source-list row, link, focus ring, native form-control `accent-color`, secondary action highlight |

A user looking at the window should be able to point at any red element and
say "that's about downloading", any blue and say "that's where I am or where
I'm going".

### 1.1a Brand tokens (download semantic)

| Token | Light | Dark | Use |
|---|---|---|---|
| `--brand` | `#FF0000` | `#FF2222` | Primary download CTA, progress fill, brand chip, running dot |
| `--brand-hover` | `#E60000` | `#FF4444` | CTA hover |
| `--brand-pressed` | `#CC0000` | `#FF0F0F` | CTA pressed |
| `--brand-soft` | `rgba(255,0,0,0.10)` | `rgba(255,34,34,0.16)` | brand-chip background |
| `--brand-on` | `#FFFFFF` | `#FFFFFF` | text on `--brand` fills |

**On dark mode** the red is slightly lifted (`#FF2222`) so it doesn't read as
"black with a red tint" against `#1E1E1E` window background. This is the same
move macOS does with `systemRed` itself.

### 1.1b Accent tokens (navigation semantic)

| Token | Light | Dark | macOS counterpart |
|---|---|---|---|
| `--accent` | `#007AFF` | `#0A84FF` | `controlAccentColor` (system blue) |
| `--accent-hover` | `#0066CC` | `#1F8FFF` | hover tint |
| `--accent-pressed` | `#0050A8` | `#5AB0FF` | pressed tint |
| `--accent-soft` | `rgba(0,122,255,0.10)` | `rgba(10,132,255,0.18)` | row-selection bg, focus ring shade |
| `--accent-on` | `#FFFFFF` | `#FFFFFF` | text on accent fills |

> When/if we ever read the user's actual `controlAccentColor` via Tauri,
> `--accent` becomes dynamic. For now hard-code the system-blue default;
> this matches an unconfigured Mac.

### 1.2 Semantic / Status

| Token | Light | Dark | Use |
|---|---|---|---|
| `--ok` | `#34C759` | `#30D158` | success (`systemGreen`) |
| `--warn` | `#FF9500` | `#FF9F0A` | warning (`systemOrange`) |
| `--err` | `#FF3B30` | `#FF453A` | error (`systemRed`) |
| `--info` | `#5AC8FA` | `#64D2FF` | informational (`systemTeal`) |

Always pair with text/icon, never color-only.

### 1.3 Window chrome / surfaces (the macOS "materials")

| Token | Light | Dark | macOS material |
|---|---|---|---|
| `--win-bg` | `#ECECEC` | `#1E1E1E` | window background (opaque base) |
| `--content-bg` | `#FFFFFF` | `#1E1E1E` | content area |
| `--sidebar-bg` | `rgba(246, 246, 246, 0.72)` | `rgba(30, 30, 30, 0.72)` | sidebar — translucent over wallpaper |
| `--sidebar-backdrop` | `blur(40px) saturate(1.5)` | `blur(40px) saturate(1.5)` | applied via `backdrop-filter` |
| `--toolbar-bg` | `rgba(246, 246, 246, 0.80)` | `rgba(30, 30, 30, 0.80)` | toolbar — slightly less translucent than sidebar |
| `--popover-bg` | `rgba(255, 255, 255, 0.85)` | `rgba(40, 40, 40, 0.85)` | popovers, menus |
| `--sheet-bg` | `#F6F6F6` | `#2C2C2E` | modal sheets (opaque) |
| `--inset-bg` | `#F2F2F2` | `#2A2A2A` | inset list, code surface |

**Reduced transparency fallback** (`prefers-reduced-transparency: reduce` or
when `backdrop-filter` unsupported): replace all `rgba(... 0.72)` with the
opaque `--win-bg` value. CSS supports this automatically with `@supports`.

### 1.4 Text & labels (Apple's 4-level label hierarchy)

| Token | Light | Dark | AppKit name |
|---|---|---|---|
| `--label` | `#000000` | `#FFFFFF` | `labelColor` (full opacity) |
| `--label-secondary` | `rgba(0,0,0,0.65)` | `rgba(255,255,255,0.65)` | `secondaryLabelColor` |
| `--label-tertiary` | `rgba(0,0,0,0.40)` | `rgba(255,255,255,0.40)` | `tertiaryLabelColor` |
| `--label-quaternary` | `rgba(0,0,0,0.22)` | `rgba(255,255,255,0.22)` | `quaternaryLabelColor` (placeholder, disabled) |
| `--placeholder` | `rgba(0,0,0,0.36)` | `rgba(255,255,255,0.36)` | `placeholderTextColor` |
| `--link` | `var(--accent)` | `var(--accent)` | `linkColor` |

**Why opacity, not gray hex?** Because labels sit on translucent materials,
gray hex would mix wrongly with the wallpaper-tinted backdrop. Apple uses
alpha-on-label for this exact reason. **Follow this convention.**

### 1.5 Separators

| Token | Light | Dark |
|---|---|---|
| `--separator` | `rgba(0,0,0,0.10)` | `rgba(255,255,255,0.15)` |
| `--separator-opaque` | `#E5E5E5` | `#3A3A3A` |

Use translucent separator inside vibrancy panels; opaque variant inside opaque
content areas.

### 1.6 Selection

| Token | Light | Dark | Use |
|---|---|---|---|
| `--selection` | `var(--accent)` | `var(--accent)` | row / item selection background (focused) |
| `--selection-unemphasized` | `rgba(0,0,0,0.08)` | `rgba(255,255,255,0.10)` | row when window loses focus |
| `--selection-text` | `#FFFFFF` | `#FFFFFF` | foreground on `--selection` |

### 1.7 Contrast verification (WCAG)

| Pair (Dark) | Ratio | Grade |
|---|---|---|
| `--label` `#FFF` on `--content-bg` `#1E1E1E` | 17.4 | **AAA** |
| `--label-secondary` (65%) on `--content-bg` | 11.3 | AAA |
| `--label-tertiary` (40%) on `--content-bg` | 7.0 | AAA Large / AA body |
| `--accent` `#0A84FF` on `--content-bg` | 4.6 | AA |
| `--label` on `--sidebar-bg` (composed over wallpaper) | depends — but worst-case backdrop with reduce-transparency = 17 |

| Pair (Light) | Ratio | Grade |
|---|---|---|
| `--label` `#000` on `#FFF` | 21.0 | AAA |
| `--label-secondary` on `#FFF` | 13.7 | AAA |
| `--accent` `#007AFF` on `#FFF` | 4.3 | AA Large only — weight ≥600 |

### 1.8 Usage allocation (Hybrid C)

```
content-bg / win-bg / sidebar-bg / sheet-bg ──────────────  ≈ 86%
labels (all 4 levels)                             ──────  ≈ 9%
brand (red — download CTA, progress, running dot)   ▏▏      ≤ 3%
accent (blue — selection, focus, link)              ▏▏      ≤ 2%
semantic (ok/warn/err)                                  ▏   ≤ 0.5%
```

**Two-color budget rule:** at most one red surface AND one blue surface
visible in the user's foveal area at the same time. If you see both compete
(red CTA + blue selected row + blue focus + red badge in toolbar), you've
overloaded one of them.

**Where they touch:** the **progress bar in a selected row** — the row bg is
`--accent-soft` blue, the fill is `--brand` red. That's the entire collision
surface and it's by design: "selected task is downloading".

---

## 2. Typography

Apple ships **SF Pro Display** (≥20pt) and **SF Pro Text** (≤19pt) plus
**SF Mono**. On non-Mac platforms in a Tauri webview these aren't installed,
so we fall back through `system-ui` → `BlinkMacSystemFont` → `Segoe UI` →
`Inter`. **The visual result on macOS will use the real SF.**

### 2.1 Font Stack

```css
--font-sans: -apple-system, BlinkMacSystemFont, "SF Pro Text",
             "SF Pro Display", system-ui, "Segoe UI", "Inter",
             "PingFang SC", "Microsoft YaHei", sans-serif;
--font-mono: "SF Mono", ui-monospace, "Menlo", "Consolas",
             "JetBrains Mono", monospace;
```

`-apple-system` resolves to SF Pro Text/Display **automatically by size** on
macOS — we don't need to swap families manually.

### 2.2 Type Scale — mapped to Apple's text styles

Apple's "text style" system is named, not pt-numbered, but each style has a
canonical size at the default Dynamic Type setting. We follow those sizes:

| # | Role | Size | Weight | LH | Tracking | Apple style | Use |
|---|---|---|---|---|---|---|---|
| 1 | **Large Title** | 26 px | 700 | 1.20 | +0.4 px | largeTitle | Window primary title (sheet header) |
| 2 | **Title 1** | 22 px | 700 | 1.25 | +0.35 px | title1 | Empty state main line |
| 3 | **Title 2** | 17 px | 600 | 1.30 | -0.43 px | title2 | Card / section header (sheet section) |
| 4 | **Title 3** | 15 px | 600 | 1.30 | -0.41 px | title3 | Sub-section, video meta title |
| 5 | **Headline** | 13 px | 600 | 1.45 | -0.08 px | headline | Selected row, active nav |
| 6 | **Body** | 13 px | 400 | 1.45 | -0.08 px | body | Default text |
| 7 | **Callout** | 12 px | 400 | 1.40 | 0 | callout | Helper text, labels |
| 8 | **Subheadline** | 11 px | 400 | 1.40 | +0.08 px | subheadline | Metadata, captions |
| 9 | **Footnote** | 10 px | 400 | 1.30 | +0.12 px | footnote | Smallest legal-ish text, version strings |
| 10 | **Mono** | 11 px | 400 | 1.40 | 0 | (SF Mono) | Code, URL, stderr |

**Tracking values are real Apple specs** (from SwiftUI text styles). They feel
"natively macOS" because they match what Finder, Mail, and Notes use.

### 2.3 Concrete Pairings (drawn from this app's surfaces)

**Empty state**
```
[ Title 1   ]    No downloads yet                ← 22/700 +0.35
[ Subheadline ]  Paste a URL above to begin      ← 11/400 +0.08
```

**Video meta card (after parsing a single URL)**
```
[ Title 3 ]   Never Gonna Give You Up — Rick Astley   ← 15/600 -0.41
[ Callout ]   RickAstleyVEVO  ·  3:33                  ← 12/400
[ Mono    ]   bestvideo+bestaudio/best                 ← 11/400 SF Mono
```

**Format-list row (selected)**
```
[ Headline ]   1080p H.264                            ← 13/600 -0.08
[ Subheadline ] A+V · 156 MB                          ← 11/400 +0.08
```

**Sidebar source-list entry**
```
[ Body     ]   Downloads               3              ← 13/400 -0.08
[ Headline ]   Downloads               3              ← when selected, 13/600
```

### 2.4 Rules
- Use **`text-rendering: geometricPrecision`** on the root — improves SF Pro
  small-cap rendering in WebKitGTK.
- **`-webkit-font-smoothing: antialiased`** on dark backgrounds; **`auto`**
  on light. Mac uses subpixel AA on light, grayscale on dark.
- Numbers use `font-variant-numeric: tabular-nums` for any column that updates
  (file size, ETA, speed, count badge). SF supports this natively.
- **No italics for UI** (HIG: italic reserved for in-content emphasis).
- **No underlines for buttons** — underline only for inline links.

---

## 3. Key Effects (Motion)

macOS motion is **spring-based**. The HIG recommends `easeInOut` for state
changes, `spring` for arrivals and removals, and a strict ≤300 ms ceiling for
chrome animations. Vibrancy is "always on" — no fade-in.

### 3.1 Motion Tokens

```css
/* Bezier — for short state changes */
--ease-default: cubic-bezier(0.4, 0.0, 0.2, 1);   /* Material-equivalent, also matches CAMediaTimingFunction.default */
--ease-out:     cubic-bezier(0.0, 0.0, 0.58, 1);  /* deceleration — enter */
--ease-in:      cubic-bezier(0.42, 0.0, 1.0, 1);  /* acceleration — exit */

/* Spring — for arrivals (popover, sheet, sidebar) */
--spring-snappy:   cubic-bezier(0.5, 1.6, 0.4, 1);   /* slight overshoot — popover */
--spring-smooth:   cubic-bezier(0.32, 0.72, 0, 1);   /* macOS sheet feel */

/* Durations */
--dur-instant: 100ms;     /* hover, focus ring */
--dur-fast:    150ms;     /* button press, row select */
--dur-base:    200ms;     /* popover open, alert appear */
--dur-slow:    300ms;     /* sheet present, sidebar collapse */
```

### 3.2 Named Effects

| Effect | Trigger | Duration | Curve | Implementation note |
|---|---|---|---|---|
| **Sheet present** | open a modal sheet | 300ms | `--spring-smooth` | `transform: translateY(-100%) → 0` + opacity 0 → 1 |
| **Sheet dismiss** | close sheet | 200ms | `--ease-in` | reverse, faster (HIG: exit faster than enter) |
| **Popover open** | menu / inspector flyout | 200ms | `--spring-snappy` | `transform: scale(0.92) → 1` + opacity 0 → 1 |
| **Sidebar item select** | click row | 150ms | `--ease-default` | `background-color` only — no transform |
| **Toolbar button press** | mouseDown → mouseUp | 100ms | `--ease-default` | subtle `opacity 1 → 0.6 → 1` |
| **Hover bg** | enter interactive | 100ms | `--ease-default` | `background-color` |
| **Focus ring** | gain keyboard focus | instant | — | `outline: 3px solid var(--accent-soft); outline-offset: 1px; border-radius: inherit;` — macOS-blue glow |
| **Progress fill** | progress update | 150ms | linear | width transition |
| **Pulse (running)** | task downloading | 1.6s loop | linear | opacity 1 → 0.4 → 1 — macOS uses slower pulse than the 1.2s elsewhere |
| **Window resize** | drag corner | continuous | — | no animation, native handling |
| **Theme switch** | light↔dark | 0ms | — | snap; vibrancy reads new colors immediately |

### 3.3 Vibrancy ("Liquid Glass") implementation

```css
.sidebar {
  background: var(--sidebar-bg);
  backdrop-filter: blur(40px) saturate(180%);
  -webkit-backdrop-filter: blur(40px) saturate(180%);
}
@supports not (backdrop-filter: blur(1px)) {
  .sidebar { background: var(--win-bg); }
}
@media (prefers-reduced-transparency: reduce) {
  .sidebar { background: var(--win-bg); backdrop-filter: none; }
}
```

**`saturate(180%)` is critical** — it's what makes the blur feel like Apple's
material instead of generic CSS frosted glass. The saturation pulls color from
the desktop wallpaper, giving the sidebar its characteristic warm tint over
photos and cool tint over solid colors.

### 3.4 Forbidden Effects

| ❌ | Why |
|---|---|
| **Page-slide between routes** | macOS apps don't slide; they swap content in the source-list pattern. |
| **Scale-on-hover transform** | Pointer is precise. Hover changes color only, never size. |
| **Bouncing dock-style overshoot on buttons** | Reserved for App Switcher; in-window UI is calm. |
| **Confetti / celebration anim** | Apple ships zero of this in system apps. |
| **Auto-playing intro animation** | Apps launch silently. |
| **Spinning company logo loader** | Use the system spinner (`NSProgressIndicator` equivalent — a CSS `<svg>` matching macOS spinner style). |
| **Sticky toast notifications** | Use the system notification or an in-window banner with auto-dismiss. |
| **Custom scrollbar styles** | macOS scrollbars are overlay and fade — let them be. (Webview defaults are close.) |
| **Glow / neon on idle elements** | Liquid Glass uses ambient saturation, never neon. |
| **Background-color cross-fade for selection** | Selection is instant on click (150ms is the max). |
| **Hover-revealing tooltips faster than 500ms** | macOS tooltip delay = 500ms — match it. |

### 3.5 Reduced-motion + reduced-transparency

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.001ms !important;
    transition-duration: 0.001ms !important;
    animation-iteration-count: 1 !important;
  }
}
@media (prefers-reduced-transparency: reduce) {
  .sidebar, .toolbar, .popover {
    backdrop-filter: none !important;
    background: var(--win-bg) !important;
  }
}
```

Both are user-controlled accessibility preferences; both must be respected.

---

## 4. macOS-Specific Anti-Patterns (32)

These come from real reviews of cross-platform downloaders / Electron tools
that "look almost macOS" but feel wrong to Mac users. Every one is concrete.

### 4.1 Chrome & window (8)
1. ❌ **Title bar separate from toolbar.** macOS unified them in 10.10 (2014).
   Never draw a horizontal divider between titlebar and toolbar.
2. ❌ **Window controls (close/min/max) on the right.** Traffic lights are
   left, top-left, in red/yellow/green order. Win11/Linux-default is right —
   override only when running on macOS host.
3. ❌ **Custom-painted traffic lights.** If you must show them in the
   webview (because Tauri's `decorations: false`), match exact size 12pt and
   color values. Better: let Tauri use native chrome (`decorations: true` on
   macOS, custom on Win/Linux).
4. ❌ **Sharp 90° corners on the window.** macOS windows have ~10pt radius on
   all corners since macOS 11 (Big Sur). Use `border-radius: 10px` on root.
5. ❌ **Bottom status bar with a row of toolbar buttons.** That's a Windows
   pattern. macOS puts secondary actions in the toolbar or a bottom inspector,
   never a button strip.
6. ❌ **Menu bar inside the window.** macOS apps put their menus in the
   system menu bar at the top of the screen, not inside the window content.
7. ❌ **Full-width "Cancel | Save" footer.** macOS sheets use right-aligned
   buttons, secondary on left. "Discard | Save" pattern — never "OK | Cancel".
8. ❌ **Maximize behavior that fills the screen.** macOS "Maximize" is
   "Zoom" (best-fit). Don't auto-fullscreen.

### 4.2 Color & vibrancy (6)
9. ❌ **Use the brand red for sidebar selection or focus rings.** Red is
    reserved for the *download* semantic. Selection / focus / link is
    `--accent` (system blue). Confusing the two breaks the Hybrid C contract.
10. ❌ **Pure black `#000000` backgrounds.** macOS dark uses `#1E1E1E` —
    softer, avoids OLED smear and lets shadows show.
11. ❌ **Pure white `#FFFFFF` backgrounds.** Light mode content surface is
    fine at white, but the *window* background is `#ECECEC` (subtly off-white
    to differentiate from sheet/content).
12. ❌ **Solid gray text on solid gray bg.** macOS labels use **alpha on
    label**, not gray hex, so they pick up the wallpaper-tinted vibrancy
    correctly. Use `rgba(255,255,255,0.65)` not `#A0A0A0`.
13. ❌ **Translucent everything.** Vibrancy is for sidebar / toolbar /
    popover / menu. Content area is opaque. Mixing breaks the visual
    hierarchy.
14. ❌ **Drown the sidebar in a colored "accent" background.** macOS sidebar
    is the wallpaper tint, not a brand color. Use a 2 px `--brand` (for active
    download tasks count) or `--accent` (for current filter) **left bar**, not
    a full-row fill.

### 4.3 Typography (5)
15. ❌ **Inter or Roboto as the primary font on macOS.** Use
    `-apple-system` so SF Pro renders on Mac; fall back to others off-Mac.
16. ❌ **Bold 24pt headlines everywhere.** macOS prefers regular weight body
    + bold headlines used sparingly. Inverse of marketing-site convention.
17. ❌ **Underlined buttons.** Reserved for links inline in text.
18. ❌ **All caps labels** with tight tracking. macOS Micro labels use
    +1.0 letter-spacing, never all-caps. (We had this in YT-red version;
    drop it.)
19. ❌ **Custom fonts shipped with the app for "branding".** macOS apps
    use system fonts. Adding webfonts feels like a website.

### 4.4 Controls & interaction (8)
20. ❌ **Big colorful buttons everywhere.** Toolbar / inspector buttons are
    icon-only, 22-26pt, gray on hover, accent only when selected/active.
    Reserve filled buttons for the **one** primary action in a sheet footer.
21. ❌ **"Are you sure?" confirmation for non-destructive actions.** macOS
    only confirms truly destructive ones (delete file, permanent removal).
22. ❌ **Custom checkboxes/radios.** Use `accent-color: var(--accent)` and
    let native form controls render. They'll look perfect on macOS.
23. ❌ **Modal alert blocking the entire window for a recoverable error.**
    Inline banner at top of content, not a modal.
24. ❌ **Right-click menu without keyboard shortcut hints.** macOS context
    menus show `⌘C` etc. next to each item. Show them.
25. ❌ **Drag-and-drop without visible drop targets.** macOS shows a blue
    rectangular outline on the drop zone. Match it.
26. ❌ **Disabled buttons that look the same as enabled.** Apple uses 35%
    opacity on disabled controls. Be at least that obvious.
27. ❌ **Hover state that changes size, position, or border.** Only color
    changes on hover. Layout never shifts.

### 4.5 Navigation & layout (3)
28. ❌ **Tabbed workspaces inside the window** (browser tabs metaphor). macOS
    apps use the system tabbar (`NSWindow tabbingMode`) for new tabs, not an
    in-content row. Keep one document per window or use a sidebar source list.
29. ❌ **Hamburger menu** on a desktop window. Hamburger is mobile. On macOS,
    actions live in the menu bar (system) or toolbar.
30. ❌ **Breadcrumbs at the top of the window.** Mac uses path bar in the
    *bottom* of Finder windows, or no breadcrumb at all.

### 4.6 Error / feedback (2)
31. ❌ **Error toast in the bottom-right corner.** That's Windows.
    macOS shows errors as an inline banner or a sheet attached to the window.
32. ❌ **Console-style raw error.** Wrap stderr in a disclosure-triangle
    expandable section with SF Mono, matching the Xcode console pattern.

---

## 5. PR Checklist (10)

Run before merging UI changes against the macOS edition.

- [ ] Brand red is **only** on: primary download CTA, progress fill, running
      indicator pulse, brand chip in TopBar. Never on selection / focus / link.
- [ ] `--accent` (blue) is on selection / focus / link / native form-control
      `accent-color`. Never on download actions.
- [ ] Translucent surfaces include `@supports not (backdrop-filter)` fallback.
- [ ] Translucent surfaces include `prefers-reduced-transparency` fallback.
- [ ] `font-family` chain starts with `-apple-system, BlinkMacSystemFont`.
- [ ] No `letter-spacing` or `font-size` outside §2.2 table.
- [ ] No animation over 300ms (except progress bar fill).
- [ ] No hover/select effect changes size or position.
- [ ] All primary buttons use specific verbs ("Download", "Discard"), not "OK".
- [ ] Light + Dark + reduced-transparency + reduced-motion all visually verified.

---

## 6. Implementation Map (token → file)

| Layer | Where |
|---|---|
| Color / radius / font / motion tokens | `src/assets/theme.css` (refactor needed) |
| naive-ui theme overrides | `src/App.vue` — `BRAND` for download primary, future `ACCENT` for selection-related n-components |
| Window radius + chrome | `tauri.conf.json` (`decorations: true` on macOS, custom on others) |
| Source list (sidebar) | `src/components/Sidebar.vue` — restyle for vibrancy + blue selection |
| Toolbar (top bar) | `src/components/TopBar.vue` — restyle for unified titlebar + red brand chip |
| Sheet / popover | future component (Settings could move from page to sheet) |
| Helpers (`.sr-only`, focus ring) | `src/assets/theme.css` — focus ring uses `--accent` (blue) |

---

## 7. Migration delta from YouTube-red-only edition (Hybrid C)

The previous design treated red as the universal accent. The macOS edition
splits accents along the brand-vs-navigation axis. Concrete deltas:

1. **Keep `--brand` red** but narrow its allowed surfaces to: download CTA,
   progress fill, running indicator, brand chip. Remove from sidebar active
   state, focus rings, links.
2. **Add `--accent` blue** token family for selection / focus / link.
3. **Add vibrancy material variables** + `backdrop-filter` rules on Sidebar /
   TopBar / future popovers (sidebar opacity 0.72, blur 40px, saturate 180%).
4. **Restyle Sidebar active state**: 2 px blue left bar + neutral hover bg.
   (Currently red-soft fill; this gives red back to download semantics.)
5. **Restyle URL input bar** as a toolbar search-field equivalent (capsule
   shape, inset shadow on focus, **focus ring is blue**). Not the current
   outlined card with red focus border.
6. **Restyle format-row selected state** to use `--accent-soft` (blue) bg
   and `--label` text. Like a Finder row, not a YouTube row.
7. **Restyle TaskRow** to look like Mail's message row: tighter density,
   monospace numbers, no card border (rows separated by `--separator`).
   Progress fill stays **red**; running pulse dot stays **red**.
8. **Restyle SettingsView** to look like System Settings: left source-list
   of categories + right detail. Or split into a sheet.
9. **Font tokens**: ship the `-apple-system` chain (already done — but
   currently leads with `'Inter'`; swap order).
10. **Add `accent-color: var(--accent);`** at root so native checkboxes /
    radios get system blue. Native `<progress>` if used follows `--brand`
    via explicit override.
11. **Window radius**: 10 px on root container if Tauri's `decorations: false`,
    else system handles. macOS keeps the radius natively.
12. **Keep the i18n verb labels** ("Download" / "下载"). The Hybrid C split is
    purely visual; copy unchanged.

This is a **~2 day visual refactor** (CSS + small HTML structure for
toolbar/sidebar). No business logic changes.

---

## 8. Inputs that informed this document

- `ui-ux-pro-max-skill` v2.5.0: `style` domain matched Glassmorphism + Spatial
  UI (VisionOS) — both Apple-adjacent. Their token outputs are quoted in §1.3
  and §3.3.
- Apple Human Interface Guidelines (knowledge cutoff): SF Pro typography,
  semantic system colors, vibrancy materials, traffic light placement.
- 10-round audit of `src/components/` (carries through anti-patterns).
- WebSearch was attempted but the runtime rejected it under 1M-context mode;
  if a fresh search is run later this document should be cross-checked
  against macOS Sequoia 15.x release notes.
