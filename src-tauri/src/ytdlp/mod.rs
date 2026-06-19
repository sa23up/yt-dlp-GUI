#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;
use std::path::Path;
use std::process::Stdio;
use tokio::process::Command;

pub mod args;
pub mod parse;

/// Errors that can occur when spawning yt-dlp.
#[derive(Debug)]
pub enum SpawnError {
    NotFound(String),
    Io(std::io::Error),
}

impl std::fmt::Display for SpawnError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            SpawnError::NotFound(path) => write!(f, "yt-dlp binary not found: {path}"),
            SpawnError::Io(e) => write!(f, "failed to spawn yt-dlp: {e}"),
        }
    }
}

impl std::error::Error for SpawnError {}

impl From<std::io::Error> for SpawnError {
    fn from(e: std::io::Error) -> Self {
        SpawnError::Io(e)
    }
}

/// Spawn a yt-dlp process with the given binary path and arguments.
/// Returns the child process handle with piped stdout/stderr, null stdin,
/// and `kill_on_drop` set so any orphaned Child is reaped automatically.
pub fn spawn_ytdlp(ytdlp_bin: &Path, args: &[String]) -> Result<tokio::process::Child, SpawnError> {
    // Only check existence for explicit paths (not bare command names from PATH)
    let is_bare =
        ytdlp_bin.parent().is_none() || ytdlp_bin.parent() == Some(std::path::Path::new(""));
    if !is_bare && !ytdlp_bin.exists() {
        return Err(SpawnError::NotFound(ytdlp_bin.display().to_string()));
    }
    let mut cmd = Command::new(ytdlp_bin);
    cmd.args(args)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .kill_on_drop(true);
    // Prepend bundled binary dirs to PATH so yt-dlp finds the shipped deno
    // (YouTube JS challenges) and ffmpeg/ffprobe even with nothing installed
    // system-wide. No-op in dev (no bundle dir → PATH untouched).
    if let Some(path) = crate::util::augmented_path() {
        cmd.env("PATH", path);
    }
    #[cfg(target_os = "windows")]
    {
        cmd.creation_flags(0x08000000);
    } // CREATE_NO_WINDOW
    #[cfg(unix)]
    {
        // Own process group, so cancellation can kill yt-dlp AND anything it
        // spawned (ffmpeg during the merge step) via killpg. See
        // queue::kill_child_tree.
        cmd.process_group(0);
    }
    Ok(cmd.spawn()?)
}
