//! Centralized IPC channel names used between the Tauri runtime and the
//! frontend. Use the typed constants on the Rust side and the matching
//! `src/ipc.ts` constants on the TS side — never hand-write the strings.

/// `emit`-ed events.
pub mod event {
    /// Per-task state transition (pending / running / complete / failed / cancelled).
    pub const TASK_STATE: &str = "task:state";
    /// Progress for an in-flight dependency update (currently: yt-dlp self-update).
    pub const DEP_UPDATE_PROGRESS: &str = "dep:update-progress";
}
