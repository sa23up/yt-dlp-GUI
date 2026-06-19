# ADR 0001 — Hybrid C colour system (YouTube red + macOS system blue)

**Status**: accepted (2026-05)
**Supersedes**: the original "YouTube-red-everywhere" design system

## Context

The brand we wanted was YouTube red — strong category signal, "this is the video-downloader app". The chrome we wanted was native macOS — light/dark, system fonts, vibrancy, blue selection rings users already trust.

Painting everything red made every selected row, focus ring and link feel like an alarm. Painting everything blue lost the category signal.

## Decision

Carry **two separate accent identities**. They never appear on the same surface.

| Axis | Token | Used for |
|---|---|---|
| **Brand / Download** (`--brand-*`, YouTube red `#FF0000`) | Primary CTA, progress fill, running-task pulse, brand chip in top bar |
| **Navigation / Selection** (`--accent-*`, macOS system blue `#007AFF`) | Selected sidebar row, focus ring, link, native form-control `accent-color` |

A user can point at any red pixel and say "that's about downloading", any blue pixel and say "that's where I am or where I'm going".

Tokens live in `src/assets/theme.css` (CSS variables) and `src/App.vue` (mirrored JS constants for naive-ui's `theme-overrides`). When updating one, update the other — there is no build-time extraction.

## Consequences

- naive-ui's `primary*` token family maps to **accent (blue)**, not brand, because naive uses `primary` to drive selection/focus/radio/checkbox — all navigation semantics.
- `Progress` component is overridden to use `--brand` because progress is a download indicator.
- Light/dark each carries distinct values; dark-mode red is lifted to `#FF2222` so it doesn't read as "black with a red tint" against `#1E1E1E`.
- See `docs/design-system-macos.md` for the full surface/material/typography tokens.
