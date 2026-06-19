# ADR 0004 — Notification-only terminal tasks

**Status**: accepted (2026-05)
**Builds on**: [ADR 0002](0002-rust-owned-queue.md) (which already removed `history.json`)

## Context

V1 gave terminal tasks (complete / failed / cancelled) a full in-app surface:

- a persisted **history** list with search,
- a per-task **error detail** panel (title / reasons / suggestions / raw stderr),
- **retry** and **Retry All Failed**,
- **open file** / **open folder** on a finished download.

`history.json` persistence was already removed in ADR 0002. The remaining
in-app terminal UI carried a disproportionate amount of machinery for a tool
whose job is "paste URL, get file": a bilingual error-message builder, a
filepath-capture sentinel through yt-dlp's `--print`, opener path permissions,
and retry/history plumbing in the store. Keeping it half-built (frontend
deleted, backend still computing it) left the codebase self-contradictory.

## Decision

Terminal tasks are **notification-only**.

- On a terminal `task:state` event the frontend drops the task from the live
  list and fires a single system notification (✓ complete / ✗ failed). The
  notification text follows the app's selected locale (shared `i18n` instance),
  not `navigator.language`.
- The backend no longer computes per-task error detail. `errors::classify` is
  retained **only** for `commands::formats::fetch_formats`' short error title;
  `to_user_message`, `UserMessage`, the `Lang` enum and `set_error_lang` are
  removed. `QueueState` no longer carries a language.
- `Task` drops `error_title` / `error_reasons` / `error_suggestions` /
  `error_raw` / `filepath` / `filesize`. On failure the first stderr line is
  written to `app.log` for diagnostics (readable via `read_log`).
- The `--print after_video:ytdlpgui_filepath=…` sentinel and its parser are
  removed; the `opener:allow-open-path` / `opener:allow-reveal-item-in-dir`
  capabilities are dropped (no in-app open-file/folder).

## Consequences

- A failed download shows no in-app reason — the user sees a generic failure
  notification and, if needed, consults `app.log`.
- **No retry**: re-paste the URL.
- Smaller `Task` payload and a quieter event stream; less attack/maintenance
  surface (no filepath handling, no opener path permission).
- Supersedes PRD user stories 6, 15, 16 and the error-display portion of 24.

## Alternatives considered

- **Restore a minimal failed-row + error panel + retry/open-file.** Rejected in
  favour of simplicity; the data was cheap to re-surface but the product intent
  is a live-queue tool, and notification + log is a sufficient failure signal.

## Amendment (2026-05-31): notification fallback

The "notification is a sufficient failure signal" assumption breaks when the
user **denies** notification permission: a failed download would then drop from
the live list with no signal at all. We keep the notification-only model but add
one fallback — when notifications are not granted, a failed task is surfaced as a
dismissible in-app alert (`download` store's `failedNotices`, rendered on Home).
This is failure-only and carries no error detail, retry, or history, so the
slim-surface intent above is preserved. When notifications *are* granted,
behaviour is unchanged (notification only, nothing in-app).
