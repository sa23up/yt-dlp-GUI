# ADR 0002 — Rust owns `queue.json`

**Status**: accepted (2026-05)
**Replaces**: dual-write where both frontend Pinia store and Rust shared the file

## Context

Originally the frontend persisted the queue to `queue.json` from Pinia and Rust also wrote it during state transitions. Two writers competing on the same file plus a noisy progress event stream led to:

- Out-of-order writes where a stale snapshot could land last and lose newer tasks
- The frontend writing at progress tick frequency (10+ Hz per task)
- Difficult invariants: which side "wins" if frontend store disagreed with Rust state

## Decision

`queue.json` is owned exclusively by Rust:

- `commands::queue` writes via `save_queue_to_disk_async()` only at **structural transitions** (enqueue, start, cancel, terminal). Progress ticks do not write to disk.
- All writes serialise through a `tokio::sync::Mutex<()>` (`SAVE_LOCK`) so concurrent saves capture the latest state in FIFO order and the final `rename()` is total.
- Writes are atomic: `atomic_write` does tmp → `fsync` → `rename` with a counter-suffixed tmp filename so two writes can't share a tmp path.
- On startup `load_queue_on_startup` reads the file, demotes anything Running back to Pending (the child process died with the previous instance), and re-emits `task:state` events so the frontend hydrates.
- The frontend store subscribes to `task:state`; it never touches `queue.json` directly.

Shutdown is handled in `kill_all_on_exit`: it calls `save_queue_to_disk_sync()` first, then kills children, then `wait_all_on_exit` reaps them with a 3 s timeout.

## Consequences

- The frontend is a pure projection of the event stream — refreshes / HMR / view re-mounts always recover correct state.
- The Pinia store can be entirely in-memory; no debouncing, no `beforeunload`.
- A frontend bug can no longer corrupt the queue.
- `history.json` was once the same dual-write design; the feature has since been removed entirely (see release notes).
