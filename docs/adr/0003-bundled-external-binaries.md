# ADR 0003 — Bundle yt-dlp, ffmpeg and deno

**Status**: accepted (2026-05)

## Context

yt-dlp depends at runtime on:

- **ffmpeg** — for merging separate video + audio streams (any quality above ~720p on YouTube)
- **deno** — from yt-dlp 2025.11.12 on, used as the JS runtime for YouTube extractor scripts

Asking non-technical users to install both via package manager is the failure mode that kills competing GUIs. Downloading at first launch leaks the "exit out to install something" UX and is unreliable in restricted networks.

## Decision

Ship all three binaries inside the installer.

| Binary | Source | Pinned in |
|---|---|---|
| `yt-dlp` | `github.com/yt-dlp/yt-dlp/releases/download/<ver>/yt-dlp[.exe\|_linux]` | `src-tauri/deps.json` `yt_dlp` + `yt_dlp_sha256` |
| `ffmpeg` | `github.com/yt-dlp/FFmpeg-Builds/releases/download/<tag>/...` | `src-tauri/deps.json` `ffmpeg` (autobuild-YYYY-MM-DD-HH-mm) + `ffmpeg_sha256` |
| `deno`   | `github.com/denoland/deno/releases/download/<tag>/...` | `src-tauri/deps.json` `deno` + `deno_sha256` |

`.github/workflows/release.yml` downloads each at the pinned version, verifies
it against the per-platform SHA-256 pinned in `deps.json` (in-repo hashes, so a
replaced upstream release asset fails the build even when the tag still
matches), drops them in `src-tauri/binaries/`, and Tauri bundles them as
resources (`bundle.resources["binaries/*"] -> "binaries/"`).

At runtime `crate::util::find_ytdlp_bin()` walks:

1. Environment variable (`YTDLP_BIN`) — overrideable for tests
2. `~/.yt-dlp-gui/bin/yt-dlp` — runtime self-updated copy
3. Each bundle root, i.e. `<exe-dir>` (Windows / dev) then the Tauri resource
   dir (Linux .deb/.AppImage layouts) — probing `<root>/binaries/<name>` then
   `<root>/<name>`
4. `PATH` — final fallback so dev mode still works

The managed dir (2) is checked **before** the bundle (3) for `yt-dlp` so an
in-app self-update takes effect even when the bundled copy sits in a read-only
install location. `find_ffmpeg_bin` / `find_deno_bin` don't self-update; they
probe the same bundle roots as (3) **first**, then `~/.yt-dlp-gui/bin`, and
return nothing in dev mode (callers fall back to `PATH`).

## Consequences

- Installer size jumps to ~150 MB. Acceptable trade for zero first-launch friction.
- ffmpeg and deno do **not** auto-update; they roll with the UI release.
- yt-dlp self-update always writes into `~/.yt-dlp-gui/bin/yt-dlp` (user-writable; the bundle dir may be read-only), and `find_ytdlp_bin` prefers it over the bundled copy. SHA-256 from `SHA2-256SUMS` is mandatory; mismatch aborts and rolls back.
- China-region first-launch needs no GitHub connectivity.

## Pinning policy

- `yt-dlp` — pin to a specific yt-dlp release tag (`YYYY.MM.DD`)
- `ffmpeg` — pin to a specific `autobuild-YYYY-MM-DD-HH-mm` tag. Avoid `latest` — it floats and breaks build reproducibility.
- `deno` — pin to a specific `vX.Y.Z` tag
- Every bump must also refresh the matching `*_sha256` entries (per-platform
  hashes of the exact downloaded asset/archive) — the release workflow fails on
  a missing or mismatching hash.
