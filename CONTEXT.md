# Project context — yt-dlp-gui

Glossary of terms used across code, issues, ADRs and PRD. When you write a new file, use the vocabulary defined here.

## Domain terms

| Term | Definition |
|---|---|
| **Task** | One download. Has a unique `id` (`t_<base36-time>_<seq>`), `params: DownloadParams`, `status` and progress fields. |
| **Queue** | Live structure inside Rust: `pending: VecDeque<Task>` + `running: HashMap<id, Task>`. Persisted as `~/.yt-dlp-gui/queue.json`. |
| **Pending** → **Running** → (**Complete** \| **Failed** \| **Cancelled**) | The task state machine. Terminal states are removed from the live queue. |
| **Concurrency** | Number of tasks allowed in `running` at once. User-controlled 1–5, default 2. |
| **Format selector** | The `-f` argument to yt-dlp. Built from `video_format_id + audio_format_id`. `None+None` → `bestvideo+bestaudio/best`. |
| **Best Quality** | UI synonym for the default selector. |
| **Cookie source** | `none` \| `firefox` \| `chrome` \| `edge` \| `file`. Maps directly to yt-dlp's `--cookies-from-browser` / `--cookies`. |
| **Hybrid C** | The two-axis colour system: YouTube red = *download semantic*, macOS system blue = *navigation semantic*. See ADR 0001. |
| **Bundle binaries** | `yt-dlp` + `ffmpeg` + `deno` shipped inside the installer. Located at runtime via `crate::util::find_*_bin()`. See ADR 0003. |
| **task:state event** | Tauri event emitted by Rust on every status transition; payload `{ task: Task }`. The frontend store is a pure projection of this stream. |

## Hard-coded constants

| Constant | Value | Where |
|---|---|---|
| `MAX_QUEUE_DEPTH` | 200 | `commands/queue.rs` — total pending + running ceiling |
| `LOG_MAX_BYTES` | 1 000 000 | `commands/log.rs` — rotates `app.log` → `app.log.1` |
| `FETCH_TIMEOUT` | 30 s | `commands/formats.rs` — `fetch_formats` hard ceiling |
| `PLAYLIST_TIMEOUT` | 60 s | `commands/download.rs` — `resolve_queue` per-playlist |
| `MAX_BYTES` (yt-dlp updater) | 100 MiB | `deps/mod.rs` — defence against malicious server |
| Concurrency range | 1–5 (default 2) | `commands/queue.rs::set_concurrency` |
| Notification permission | Requested once at first `startListening()` | `stores/download.ts` |

## On-disk layout

```
~/.yt-dlp-gui/
├── settings.json           — AppSettings (frontend mirror)
├── queue.json              — pending + running snapshot (Rust-owned)
├── app.log                 — rolling log (1 MB rotate)
├── app.log.1               — last rotation
└── bin/                    — runtime-installed yt-dlp (when bundle bin is bare)
    └── yt-dlp[.exe]
```

## IPC channel names

Centralised in `src-tauri/src/ipc.rs` and `src/ipc.ts`. Never hand-write the strings:

| Constant | Value | Direction |
|---|---|---|
| `TASK_STATE` | `"task:state"` | Rust → frontend, per task transition |
| `DEP_UPDATE_PROGRESS` | `"dep:update-progress"` | Rust → frontend, yt-dlp self-update bytes |

## ADRs

- [0001 — Hybrid C colour system](docs/adr/0001-hybrid-c-color-system.md)
- [0002 — Rust owns queue.json](docs/adr/0002-rust-owned-queue.md)
- [0003 — Fully bundled external binaries](docs/adr/0003-bundled-external-binaries.md)
- [0004 — Notification-only terminal tasks](docs/adr/0004-notification-only-terminal-tasks.md)
