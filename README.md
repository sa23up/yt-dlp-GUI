<div align="center">

<img src="assets/logo.png" alt="yt-dlp-gui logo" width="120" />

# yt-dlp-gui

Cross-platform desktop GUI for [yt-dlp](https://github.com/yt-dlp/yt-dlp), built with **Tauri 2 + Vue 3**.<br/>
Bundles `yt-dlp`, `ffmpeg` and `deno` — install and go, no terminal needed.

[![Release](https://img.shields.io/github/v/release/sa23up/yt-dlp-GUI?style=flat-square)](https://github.com/sa23up/yt-dlp-GUI/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/sa23up/yt-dlp-GUI/total?style=flat-square)](https://github.com/sa23up/yt-dlp-GUI/releases)
[![CI](https://img.shields.io/github/actions/workflow/status/sa23up/yt-dlp-GUI/ci.yml?style=flat-square&label=CI)](https://github.com/sa23up/yt-dlp-GUI/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/sa23up/yt-dlp-GUI?style=flat-square)](LICENSE)
![Platforms](https://img.shields.io/badge/platforms-Linux%20%7C%20Windows-blue?style=flat-square)

**English** · [简体中文](README.zh-CN.md)

</div>

---

> **Stack:** Tauri 2 (Rust) · Vue 3 · Pinia · vue-i18n · naive-ui · tauri-specta

## Features

- One-click **Best Quality**, or hand-pick video + audio formats
- Batch & playlist downloads (one URL per line; playlist pages expanded via `--flat-playlist`)
- Live progress (speed / ETA / %) with cancel, **pause and resume**
- Drag-and-drop URLs onto the window
- Cookie auth (Firefox / Chrome / Edge, or a manual `cookies.txt`)
- Proxy and rate-limit support
- Bilingual UI (中文 / English), light & dark themes
- Queue survives restarts
- Built-in yt-dlp updater (SHA-256 verified) plus self-update for the app

## Install

Grab the latest installer from [**Releases**](https://github.com/sa23up/yt-dlp-GUI/releases):

| Platform | Files |
| --- | --- |
| **Linux** | `.deb` or `.AppImage` |
| **Windows** | `.msi` or `.exe` |

> macOS is not provided (requires Apple Developer signing).

## Development

```bash
npm install
npm run tauri dev
```

`cargo test` regenerates `src/bindings.ts` via tauri-specta — commit the result.

## Build

```bash
npm run tauri build
```

External binaries (`yt-dlp`, `ffmpeg`, `deno`) are version- and SHA-256-pinned in `src-tauri/deps.json` and must sit under `src-tauri/binaries/` before bundling (CI downloads and verifies them automatically).

## Documentation

- [`CONTEXT.md`](CONTEXT.md) — glossary of domain terms
- [`docs/adr/`](docs/adr/) — architecture decision records
- [`docs/SECURITY-GUIDELINES.md`](docs/SECURITY-GUIDELINES.md) — security policy

## License

[MIT](LICENSE)
