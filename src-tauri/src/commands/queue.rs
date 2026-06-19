//! Centralized download queue. Owns pending → running transitions and concurrency.
//!
//! The frontend submits tasks; the backend decides when to start them. Status
//! changes are emitted via the `task:state` event and persisted to queue.json.
//!
//! State machine:
//!     pending → running → (complete | failed | cancelled)
//! Terminal states are removed from the live queue and forgotten; the system
//! notification is the only persistent record (see ADR 0004).

use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet, VecDeque};
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::{LazyLock, Mutex};
use std::time::{Duration, Instant};
use tauri::Emitter;
use tokio::io::{AsyncBufReadExt, AsyncReadExt, BufReader};

use crate::ytdlp;

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, specta::Type)]
#[serde(rename_all = "lowercase")]
pub enum TaskStatus {
    #[default]
    Pending,
    Running,
    Paused,
    Complete,
    Failed,
    Cancelled,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, specta::Type)]
#[serde(rename_all = "camelCase", default)]
pub struct DownloadParams {
    pub url: String,
    pub title: String,
    pub thumbnail: String,
    pub video_format_id: Option<String>,
    pub audio_format_id: Option<String>,
    pub output_dir: String,
    pub cookie_source: String,
    pub cookie_file_path: String,
    pub proxy: String,
    pub rate_limit: String,
    pub filename_template: String,
    /// Max video height for Best-Quality / batch downloads (0 = unlimited).
    pub max_height: u32,
    /// Preferred video codec ("any" | "h264" | "vp9" | "av1") for Best-Quality.
    pub preferred_codec: String,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, specta::Type)]
#[serde(rename_all = "camelCase", default)]
pub struct Task {
    pub id: String,
    pub status: TaskStatus,
    pub params: DownloadParams,
    pub percent: f64,
    pub speed: String,
    pub eta: String,
    /// Monotonic insertion ordinal. Stable sort key so snapshots (and the
    /// restored queue) keep chronological order rather than HashMap iteration
    /// order. Persisted; restored values are honored (see load_queue_on_startup).
    pub seq: u64,
}

/// Source of `Task::seq`. Bumped past any restored seq on startup so a task
/// enqueued after a restart can't collide with (and sort ahead of) a restored one.
static TASK_SEQ: AtomicU64 = AtomicU64::new(0);

impl Task {
    fn new(id: String, params: DownloadParams) -> Self {
        Self {
            id,
            status: TaskStatus::Pending,
            params,
            percent: 0.0,
            speed: String::new(),
            eta: String::new(),
            seq: TASK_SEQ.fetch_add(1, Ordering::Relaxed),
        }
    }
}

#[derive(Clone, Serialize)]
struct TaskStatePayload<'a> {
    task: &'a Task,
}

/// Global queue state. One Mutex protects the entire structure.
pub struct QueueState {
    pub pending: VecDeque<Task>,
    pub running: HashMap<String, Task>,
    pub children: HashMap<String, tokio::process::Child>,
    /// Paused tasks: killed mid-download but kept (with their `.part` file) so
    /// the user can resume. Not counted against concurrency — pausing frees a
    /// slot for a queued task. Non-terminal, so it persists in the live queue.
    pub paused: HashMap<String, Task>,
    pub concurrency: usize,
}

impl QueueState {
    fn new() -> Self {
        Self {
            pending: VecDeque::new(),
            running: HashMap::new(),
            children: HashMap::new(),
            paused: HashMap::new(),
            concurrency: 2,
        }
    }
}

/// Maximum tasks in flight + pending at once. Guards against runaway batch paste.
pub const MAX_QUEUE_DEPTH: usize = 200;

/// Minimum wall-clock gap between progress `task:state` emits for one task.
/// The stored task is updated on every frame (so snapshot_tasks stays current),
/// but the IPC event only fires when the rounded percent changes or this much
/// time has passed — yt-dlp emits progress many times a second, and at
/// concurrency 5 the unthrottled stream is pure reactivity churn.
const PROGRESS_EMIT_INTERVAL: Duration = Duration::from_millis(250);

/// Cancellation flags for running tasks. Set by `cancel_task`, checked by the
/// runner before emitting Failed so the task ends as Cancelled.
static CANCELLED: LazyLock<Mutex<HashSet<String>>> = LazyLock::new(|| Mutex::new(HashSet::new()));

/// Pause flags for running tasks. Set by `pause_task`, checked by the runner so
/// a killed-for-pause task ends up Paused (kept, resumable) instead of Failed.
static PAUSING: LazyLock<Mutex<HashSet<String>>> = LazyLock::new(|| Mutex::new(HashSet::new()));

/// Children dying-but-not-yet-reaped at app exit. wait_all_on_exit awaits these.
static DYING_CHILDREN: LazyLock<Mutex<Vec<tokio::process::Child>>> =
    LazyLock::new(|| Mutex::new(Vec::new()));

/// Serializes async queue.json writes. Without this, N concurrent
/// `save_queue_to_disk_async` calls each snapshot + write independently and
/// race on rename() — order of final state on disk becomes non-deterministic
/// and may end up stale.  With the lock held, each save reads the LATEST
/// state at write time, and writes serialise FIFO.
static SAVE_LOCK: LazyLock<tokio::sync::Mutex<()>> = LazyLock::new(|| tokio::sync::Mutex::new(()));

/// Flipped true the instant shutdown begins (`kill_all_on_exit`). Any async
/// save that hasn't taken SAVE_LOCK yet then no-ops, so a late background write
/// can't land after — and clobber — the authoritative synchronous shutdown save.
static SHUTTING_DOWN: AtomicBool = AtomicBool::new(false);

static STATE: LazyLock<Mutex<QueueState>> = LazyLock::new(|| Mutex::new(QueueState::new()));

/// Mutex lock that survives poisoning. If a previous holder panicked, we
/// recover the inner data rather than crashing the whole app — at worst the
/// queue state is partially inconsistent, but the user can keep working.
fn state_lock() -> std::sync::MutexGuard<'static, QueueState> {
    STATE.lock().unwrap_or_else(|e| e.into_inner())
}
fn cancelled_lock() -> std::sync::MutexGuard<'static, HashSet<String>> {
    CANCELLED.lock().unwrap_or_else(|e| e.into_inner())
}
fn pausing_lock() -> std::sync::MutexGuard<'static, HashSet<String>> {
    PAUSING.lock().unwrap_or_else(|e| e.into_inner())
}
fn dying_lock() -> std::sync::MutexGuard<'static, Vec<tokio::process::Child>> {
    DYING_CHILDREN.lock().unwrap_or_else(|e| e.into_inner())
}

fn emit_state(app: &tauri::AppHandle, task: &Task) {
    let _ = app.emit(crate::ipc::event::TASK_STATE, TaskStatePayload { task });
}

/// Combined pending + running snapshot, ordered by insertion seq. Single source
/// for the disk snapshot and `snapshot_tasks`, so the restored queue and the
/// frontend hydration are both chronological rather than HashMap-random.
fn collect_sorted(s: &QueueState) -> Vec<Task> {
    let mut all: Vec<Task> = s.pending.iter().cloned().collect();
    all.extend(s.running.values().cloned());
    all.extend(s.paused.values().cloned());
    all.sort_by_key(|t| t.seq);
    all
}

fn queue_path() -> PathBuf {
    crate::util::data_dir().join("queue.json")
}

/// Snapshot the queue (pending + running) and write queue.json off-thread.
/// Called at structural transitions only, NOT per progress event — the file
/// only needs to be accurate enough to survive restart.
///
/// Saves serialize through SAVE_LOCK so a flurry of structural changes
/// (e.g. batch enqueue) doesn't produce racing writes that overwrite each
/// other out of order.  Each save reads the LATEST state inside the lock.
fn save_queue_to_disk_async() {
    tauri::async_runtime::spawn(async move {
        let _g = SAVE_LOCK.lock().await;
        // Shutdown began while we were queued — the synchronous shutdown save is
        // authoritative; do not write a (possibly already-drained) snapshot over it.
        if SHUTTING_DOWN.load(Ordering::SeqCst) {
            return;
        }
        let snapshot: Vec<Task> = {
            let s = state_lock();
            collect_sorted(&s)
        };
        let data = match serde_json::to_string_pretty(&snapshot) {
            Ok(d) => d,
            Err(_) => return,
        };
        let path = queue_path();
        let _ = tokio::task::spawn_blocking(move || {
            let _ = crate::util::atomic_write(&path, &data);
        })
        .await;
    });
}

/// Synchronous variant for shutdown so unsaved structural state survives.
fn save_queue_to_disk_sync() {
    // Runs on the main thread at shutdown (outside any async runtime), so a
    // blocking acquire is safe and serialises us against any in-flight async
    // save — we write last, and SHUTTING_DOWN blocks any save spawned later.
    let _g = SAVE_LOCK.blocking_lock();
    let snapshot: Vec<Task> = {
        let s = state_lock();
        collect_sorted(&s)
    };
    if let Ok(data) = serde_json::to_string_pretty(&snapshot) {
        let _ = crate::util::atomic_write(&queue_path(), &data);
    }
}

/// Load any persisted queue on startup. Running tasks are demoted to Pending
/// because the child processes died with the previous app instance. Emits
/// task:state for each restored entry so the frontend sees them.
pub fn load_queue_on_startup(app: tauri::AppHandle) {
    let path = queue_path();
    let raw = match std::fs::read_to_string(&path) {
        Ok(r) => r,
        Err(_) => return,
    };
    let tasks: Vec<Task> = match serde_json::from_str(&raw) {
        Ok(v) => v,
        Err(_) => return,
    };
    // Resume the seq counter past anything we're about to restore so a freshly
    // enqueued task always sorts after the restored ones.
    let max_seq = tasks.iter().map(|t| t.seq).max().unwrap_or(0);
    TASK_SEQ.fetch_max(max_seq.saturating_add(1), Ordering::Relaxed);
    let mut restored = 0usize;
    for mut t in tasks {
        let is_paused = matches!(t.status, TaskStatus::Paused);
        match t.status {
            TaskStatus::Running | TaskStatus::Pending => {
                t.status = TaskStatus::Pending;
                t.percent = 0.0;
                t.speed.clear();
                t.eta.clear();
            }
            // A paused task keeps its status + last percent so the user can
            // resume it (the .part file on disk lets yt-dlp continue).
            TaskStatus::Paused => {
                t.speed.clear();
                t.eta.clear();
            }
            _ => continue, // skip complete/failed/cancelled — terminal, no UI affordance
        }
        // Defense-in-depth: a tampered queue.json could carry a non-http or
        // flag-injecting URL. Re-validate before it reaches the runner, same as
        // the live enqueue path does.
        if crate::util::validate_http_url(&t.params.url).is_err() {
            continue;
        }
        // Single lock: dedup-check and insert atomically (no TOCTOU window).
        {
            let mut s = state_lock();
            let dup = s.pending.iter().any(|p| p.id == t.id)
                || s.running.contains_key(&t.id)
                || s.paused.contains_key(&t.id);
            let full = s.pending.len() + s.running.len() + s.paused.len() >= MAX_QUEUE_DEPTH;
            if dup || full {
                continue;
            }
            if is_paused {
                s.paused.insert(t.id.clone(), t.clone());
            } else {
                s.pending.push_back(t.clone());
            }
        }
        emit_state(&app, &t);
        restored += 1;
    }
    if restored > 0 {
        try_start_pending(&app);
    }
}

fn resolve_output_dir(output_dir: &str) -> PathBuf {
    if output_dir.is_empty() {
        let home = crate::util::home_dir().unwrap_or_else(|| PathBuf::from("."));
        return home.join("Downloads");
    }
    if let Some(stripped) = output_dir.strip_prefix("~/") {
        let home = crate::util::home_dir().unwrap_or_else(|| PathBuf::from("."));
        return home.join(stripped);
    }
    PathBuf::from(output_dir)
}

fn sanitize_filename_template(t: &str) -> String {
    if t.trim().is_empty() {
        return "%(title)s.%(ext)s".into();
    }
    // Allow path separators (legitimate for subfolders like %(uploader)s/%(title)s.%(ext)s),
    // but reject `..` segments, absolute paths and drive-letter / NTFS stream syntax.
    let trimmed = t.trim_start_matches(['/', '\\']);
    let segments: Vec<String> = trimmed
        .split(['/', '\\'])
        .filter(|seg| !seg.is_empty())
        .map(|seg| {
            // NTFS ignores trailing dots and spaces, so ".. " or "..." escape a
            // literal `..` comparison. A segment that is nothing but dots/spaces
            // is always a traversal attempt or invalid — neutralize it.
            if seg.trim_end_matches([' ', '.']).is_empty() {
                "_".into()
            } else {
                // `C:` would make Path::join replace the base dir on Windows;
                // `name:stream` is NTFS alternate-data-stream syntax.
                seg.replace(':', "_")
            }
        })
        .collect();
    let cleaned = segments.join("/");
    if cleaned.trim_matches(['_', '/', ' ']).is_empty() {
        "%(title)s.%(ext)s".into()
    } else {
        cleaned
    }
}

fn build_args(params: &DownloadParams, out_dir: &std::path::Path) -> Result<Vec<String>, String> {
    use ytdlp::args::{build_download_args, parse_cookie_source, DownloadOptions};

    let cookie_source = parse_cookie_source(&params.cookie_source);

    let opts = DownloadOptions {
        video_format_id: params.video_format_id.clone(),
        audio_format_id: params.audio_format_id.clone(),
        output_dir: out_dir.to_path_buf(),
        filename_template: sanitize_filename_template(&params.filename_template),
        cookie_source,
        cookie_file_path: if params.cookie_file_path.is_empty() {
            None
        } else {
            Some(PathBuf::from(&params.cookie_file_path))
        },
        proxy: if params.proxy.is_empty() {
            None
        } else {
            Some(params.proxy.clone())
        },
        rate_limit: if params.rate_limit.is_empty() {
            None
        } else {
            Some(params.rate_limit.clone())
        },
        max_height: params.max_height,
        preferred_codec: params.preferred_codec.clone(),
    };

    let mut args = build_download_args(&opts)?;

    // Bundled ffmpeg
    if let Some(ffmpeg_path) = crate::util::find_ffmpeg_bin() {
        args.push("--ffmpeg-location".into());
        args.push(ffmpeg_path.to_string_lossy().to_string());
    }

    args.extend_from_slice(&[
        "--progress-template".into(),
        "%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s".into(),
        "--newline".into(),
        "--no-mtime".into(),
        // A download task is always a single video — playlist *expansion* is done
        // up front by resolve_queue. --no-playlist stops a stray `&list=` in a
        // watch URL from pulling the whole playlist here.
        "--no-playlist".into(),
    ]);

    // URL goes LAST
    args.push(params.url.clone());
    Ok(args)
}

/// Kill a running child and everything it spawned. yt-dlp forks ffmpeg for the
/// merge step; killing only yt-dlp would orphan that ffmpeg, which keeps
/// burning CPU and leaves `.part` files behind.
fn kill_child_tree(child: &mut tokio::process::Child) {
    #[cfg(unix)]
    if let Some(pid) = child.id() {
        // spawn_ytdlp puts each child in its own process group, so signalling
        // the group id reaches yt-dlp AND its descendants.
        unsafe {
            libc::killpg(pid as i32, libc::SIGKILL);
        }
    }
    #[cfg(windows)]
    if let Some(pid) = child.id() {
        use std::os::windows::process::CommandExt;
        // /T = kill the whole tree. Fire-and-forget; start_kill below is the backstop.
        let _ = std::process::Command::new("taskkill")
            .args(["/PID", &pid.to_string(), "/T", "/F"])
            .creation_flags(0x08000000) // CREATE_NO_WINDOW
            .spawn();
    }
    let _ = child.start_kill();
}

/// Try to start as many pending tasks as concurrency permits.
fn try_start_pending(app: &tauri::AppHandle) {
    let mut started_any = false;
    loop {
        let task = {
            let mut s = state_lock();
            if s.running.len() >= s.concurrency {
                break;
            }
            match s.pending.pop_front() {
                Some(mut t) => {
                    t.status = TaskStatus::Running;
                    s.running.insert(t.id.clone(), t.clone());
                    t
                }
                None => break,
            }
        };
        started_any = true;
        // spawn_runner may fail (or cancel) synchronously and remove the task
        // from `running`; this loop then refills the freed slot on its next
        // pass, so spawn_runner must NOT call try_start_pending itself (that
        // would recurse once per task on a large all-failing batch).
        spawn_runner(app.clone(), task);
    }
    if started_any {
        save_queue_to_disk_async();
    }
}

fn spawn_runner(app: tauri::AppHandle, task: Task) {
    // Honor a cancellation that arrived between `try_start_pending` popping
    // the task and us entering here. Without this, cancel_task can race
    // ahead of spawn → leaving the child orphaned with no task in running.
    if cancelled_lock().remove(&task.id) {
        let mut t = task;
        t.status = TaskStatus::Cancelled;
        t.percent = 0.0;
        t.speed.clear();
        t.eta.clear();
        state_lock().running.remove(&t.id);
        emit_state(&app, &t);
        save_queue_to_disk_async();
        // Slot freed — the try_start_pending loop that called us refills it.
        return;
    }

    let ytdlp_bin = crate::util::find_ytdlp_bin();
    let out_dir = resolve_output_dir(&task.params.output_dir);

    // Reject a cookie path that doesn't point at an existing regular file so
    // yt-dlp fails fast with a clear reason instead of a cryptic parse error.
    // NOTE: this is not a confidentiality boundary — in a local single-user app
    // the path comes from the user's own settings; it only catches typos /
    // missing files / directories.
    if task.params.cookie_source == "file" && !task.params.cookie_file_path.is_empty() {
        let cookie_path = PathBuf::from(&task.params.cookie_file_path);
        if !cookie_path.exists() || !cookie_path.is_file() {
            finalize_failed(
                &app,
                &task.id,
                "Cookie 文件不存在或不是有效文件 / Cookie file does not exist or is not a regular file".into(),
            );
            return;
        }
    }

    if let Err(e) = std::fs::create_dir_all(&out_dir) {
        finalize_failed(
            &app,
            &task.id,
            format!("无法创建输出目录 / cannot create output dir: {e}"),
        );
        return;
    }

    let args = match build_args(&task.params, &out_dir) {
        Ok(a) => a,
        Err(e) => {
            finalize_failed(&app, &task.id, format!("参数无效 / invalid options: {e}"));
            return;
        }
    };
    crate::commands::log::write_log(
        "INFO".into(),
        format!("start {} {}", task.id, task.params.url),
    );

    let mut child = match ytdlp::spawn_ytdlp(&ytdlp_bin, &args) {
        Ok(c) => c,
        Err(e) => {
            finalize_failed(
                &app,
                &task.id,
                format!("spawn yt-dlp 失败 / failed to spawn yt-dlp: {e}"),
            );
            return;
        }
    };

    let stdout = child.stdout.take();
    let stderr = child.stderr.take();

    {
        let mut s = state_lock();
        s.children.insert(task.id.clone(), child);
        // Belt-and-suspenders: if cancel_task arrived after our entry check
        // but before child landed in the map, it couldn't kill anything.
        // Now that the child is registered, honor that pending cancel.
        if cancelled_lock().contains(&task.id) {
            if let Some(c) = s.children.get_mut(&task.id) {
                kill_child_tree(c);
            }
        }
    }
    emit_state(&app, &task);

    let app_clone = app.clone();
    let tid = task.id.clone();
    tokio::spawn(async move {
        let stderr_text = match (stdout, stderr) {
            (Some(out), Some(err)) => run_io(tid.clone(), app_clone.clone(), out, err).await,
            _ => String::from("yt-dlp 未返回 stdout/stderr pipe"),
        };
        finalize_after_io(&app_clone, &tid, stderr_text).await;
        try_start_pending(&app_clone);
    });
}

async fn run_io(
    tid: String,
    app: tauri::AppHandle,
    stdout: tokio::process::ChildStdout,
    stderr: tokio::process::ChildStderr,
) -> String {
    let mut reader = BufReader::new(stdout);

    let stderr_task = tokio::spawn(async move {
        // Cap what we keep: a misbehaving yt-dlp could emit unbounded stderr.
        const STDERR_CAP: u64 = 64 * 1024;
        let mut reader = BufReader::new(stderr);
        let mut buf = Vec::new();
        let _ = (&mut reader).take(STDERR_CAP).read_to_end(&mut buf).await;
        // Keep draining (and discarding) past the cap so the child can't block
        // on a full stderr pipe.
        let mut sink = [0u8; 8192];
        loop {
            match tokio::io::AsyncReadExt::read(&mut reader, &mut sink).await {
                Ok(0) | Err(_) => break,
                Ok(_) => {}
            }
        }
        String::from_utf8_lossy(&buf).to_string()
    });

    // Read raw bytes and lossily decode each line so a stray non-UTF-8 byte in
    // yt-dlp's stdout can't end progress parsing for the rest of the download
    // (tokio's strict `lines()` stops the stream on the first decode error).
    let mut line_buf = Vec::new();
    // Per-task throttle state: last emitted rounded percent + wall-clock time.
    let mut last_percent: i64 = -1;
    let mut last_emit: Option<Instant> = None;
    loop {
        line_buf.clear();
        match reader.read_until(b'\n', &mut line_buf).await {
            Ok(0) | Err(_) => break,
            Ok(_) => {}
        }
        let line = String::from_utf8_lossy(&line_buf);
        // Progress line
        if let Some(prog) = ytdlp::parse::parse_progress(&line) {
            // Always update the stored task; only clone + emit when the throttle
            // window allows, so the live state stays accurate without flooding IPC.
            let pct = prog.percent.round() as i64;
            let now = Instant::now();
            let should_emit = pct != last_percent
                || last_emit.is_none_or(|e| now.duration_since(e) >= PROGRESS_EMIT_INTERVAL);
            let snapshot = {
                let mut s = state_lock();
                match s.running.get_mut(&tid) {
                    Some(t) => {
                        t.percent = prog.percent;
                        t.speed = prog.speed.clone();
                        t.eta = prog.eta.clone();
                        if should_emit {
                            Some(t.clone())
                        } else {
                            None
                        }
                    }
                    None => None,
                }
            };
            if let Some(t) = snapshot {
                last_percent = pct;
                last_emit = Some(now);
                emit_state(&app, &t);
            }
        }
    }

    stderr_task.await.unwrap_or_default()
}

async fn finalize_after_io(app: &tauri::AppHandle, tid: &str, stderr_text: String) {
    // Remove child + task atomically so cancel_task can't race us into ownership.
    let (child_opt, task_opt) = {
        let mut s = state_lock();
        (s.children.remove(tid), s.running.remove(tid))
    };

    let mut task = match task_opt {
        Some(t) => t,
        None => {
            // No task in running — shutdown drained, or spawn_runner cancelled
            // ahead of us. Either way the emit was handled (or unneeded).
            cancelled_lock().remove(tid);
            pausing_lock().remove(tid);
            return;
        }
    };

    // None = child handle missing (should be unreachable: the runner only gets
    // here after spawn registered the child). Treated as failure below — never
    // as success, which a defaulted ExitStatus would fake on Unix.
    let status_result = match child_opt {
        Some(mut c) => Some(c.wait().await),
        None => None,
    };

    // Decide outcome AFTER awaiting the child so a late cancel_task still wins.
    let was_cancelled = cancelled_lock().remove(tid);
    if was_cancelled {
        pausing_lock().remove(tid); // a cancel supersedes any pending pause
        task.status = TaskStatus::Cancelled;
        task.percent = 0.0;
        task.speed.clear();
        task.eta.clear();
        emit_state(app, &task);
        // Persist the removal: this task is already gone from `running`, but the
        // last on-disk snapshot still lists it. Without this save, killing the
        // app before the next save would resurrect a cancelled task as pending
        // on the next launch.
        save_queue_to_disk_async();
        crate::commands::log::write_log("INFO".into(), format!("cancel {tid}"));
        return;
    }

    // Killed for pause: keep the task (with its last percent) in the paused map
    // so the user can resume; the `.part` file on disk lets yt-dlp continue.
    let was_paused = pausing_lock().remove(tid);
    if was_paused {
        task.status = TaskStatus::Paused;
        task.speed.clear();
        task.eta.clear();
        state_lock().paused.insert(task.id.clone(), task.clone());
        emit_state(app, &task);
        save_queue_to_disk_async();
        crate::commands::log::write_log("INFO".into(), format!("pause {tid}"));
        // The runner epilogue calls try_start_pending after we return, so the
        // freed concurrency slot is refilled by a queued task.
        return;
    }

    match status_result {
        Some(Ok(s)) if s.success() => {
            task.status = TaskStatus::Complete;
            task.percent = 100.0;
            crate::commands::log::write_log("INFO".into(), format!("done {tid}"));
        }
        _ => {
            task.status = TaskStatus::Failed;
            // Terminal tasks are notification-only (ADR 0004): we keep no
            // per-task error detail in the payload, but still log the first
            // stderr line for diagnostics (readable via `read_log`).
            let first = stderr_text
                .lines()
                .find(|l| !l.trim().is_empty())
                .unwrap_or("")
                .chars()
                .take(500)
                .collect::<String>();
            crate::commands::log::write_log("ERROR".into(), format!("fail {tid}: {first}"));
        }
    }
    emit_state(app, &task);
    save_queue_to_disk_async();
}

/// Mark a task Failed before it ever produced output (dir creation / spawn
/// failure). The reason is logged for diagnostics; terminal tasks carry no
/// error detail in the event payload.
fn finalize_failed(app: &tauri::AppHandle, tid: &str, log_reason: String) {
    let task_opt = {
        let mut s = state_lock();
        s.running.remove(tid)
    };
    if let Some(mut t) = task_opt {
        // A cancel can land between spawn_runner's entry check and this setup
        // failure. Honor it (and clear the flag so it can't leak) rather than
        // reporting Failed for a task the user already cancelled.
        if cancelled_lock().remove(tid) {
            t.status = TaskStatus::Cancelled;
            t.percent = 0.0;
            t.speed.clear();
            t.eta.clear();
            crate::commands::log::write_log("INFO".into(), format!("cancel {tid}"));
        } else {
            t.status = TaskStatus::Failed;
            crate::commands::log::write_log("ERROR".into(), format!("fail {tid}: {log_reason}"));
        }
        emit_state(app, &t);
        save_queue_to_disk_async();
    }
}

// ── Public Tauri commands ──────────────────────────────────────────

/// Reject invalid proxy / rate-limit at enqueue time so the user gets immediate
/// feedback, instead of a Failed task (or worse, a silently-unproxied download).
fn validate_params(params: &DownloadParams) -> Result<(), String> {
    if !params.proxy.is_empty() {
        ytdlp::args::validate_proxy(&params.proxy)?;
    }
    if !params.rate_limit.is_empty() {
        ytdlp::args::validate_rate_limit(&params.rate_limit)?;
    }
    Ok(())
}

#[tauri::command]
#[specta::specta]
pub fn enqueue_download(
    app: tauri::AppHandle,
    id: String,
    params: DownloadParams,
) -> Result<(), String> {
    crate::util::validate_http_url(&params.url)?;
    validate_params(&params)?;
    let task = Task::new(id.clone(), params);
    // Hold lock until after insertion to prevent TOCTOU race on queue depth check
    {
        let mut s = state_lock();
        if s.pending.iter().any(|t| t.id == id) || s.running.contains_key(&id) {
            return Err("任务 ID 重复 / Duplicate task ID".into());
        }
        if s.pending.len() + s.running.len() >= MAX_QUEUE_DEPTH {
            return Err(format!(
                "队列已满（上限 {MAX_QUEUE_DEPTH}）/ Queue full (max {MAX_QUEUE_DEPTH})"
            ));
        }
        s.pending.push_back(task.clone());
        // Explicitly drop lock before emit to avoid holding it during IPC
        drop(s);
    }
    emit_state(&app, &task);
    save_queue_to_disk_async();
    try_start_pending(&app);
    Ok(())
}

#[derive(Debug, Deserialize, specta::Type)]
#[serde(rename_all = "camelCase")]
pub struct BatchItem {
    pub id: String,
    pub params: DownloadParams,
}

/// Enqueue many tasks in one IPC call. Used for playlist / multi-URL paste so a
/// 200-item batch is a single lock acquisition + one disk save + one scheduler
/// pass, instead of N round-trips that each spawn their own save.
/// Returns the number actually accepted; invalid URLs, duplicate ids and items
/// past `MAX_QUEUE_DEPTH` are skipped.
#[tauri::command]
#[specta::specta]
pub fn enqueue_batch(app: tauri::AppHandle, items: Vec<BatchItem>) -> Result<usize, String> {
    // Proxy / rate limit come from shared settings, so one bad value means the
    // whole batch is misconfigured — fail it up front rather than per item.
    for item in &items {
        validate_params(&item.params)?;
    }
    let mut accepted: Vec<Task> = Vec::new();
    {
        let mut s = state_lock();
        for item in items {
            if crate::util::validate_http_url(&item.params.url).is_err() {
                continue;
            }
            if s.pending.len() + s.running.len() >= MAX_QUEUE_DEPTH {
                break;
            }
            // Accepted items are already in s.pending, so this also rejects
            // duplicate ids appearing twice within the same batch.
            if s.pending.iter().any(|t| t.id == item.id) || s.running.contains_key(&item.id) {
                continue;
            }
            let task = Task::new(item.id, item.params);
            s.pending.push_back(task.clone());
            accepted.push(task);
        }
    }
    for t in &accepted {
        emit_state(&app, t);
    }
    if !accepted.is_empty() {
        save_queue_to_disk_async();
        try_start_pending(&app);
    }
    Ok(accepted.len())
}

#[tauri::command]
#[specta::specta]
pub fn cancel_task(app: tauri::AppHandle, id: String) -> Result<(), String> {
    // Pending removal: emit Cancelled directly — no runner involved.
    {
        let mut s = state_lock();
        if let Some(idx) = s.pending.iter().position(|t| t.id == id) {
            let mut t = s.pending.remove(idx).unwrap();
            t.status = TaskStatus::Cancelled;
            drop(s);
            emit_state(&app, &t);
            save_queue_to_disk_async();
            return Ok(());
        }
    }
    // Paused removal: no running child, just drop it from the paused map.
    {
        let mut s = state_lock();
        if let Some(mut t) = s.paused.remove(&id) {
            t.status = TaskStatus::Cancelled;
            drop(s);
            emit_state(&app, &t);
            save_queue_to_disk_async();
            return Ok(());
        }
    }
    // Running (or pending-being-spawned): mark and signal. The runner / spawn_runner
    // is the single source of truth for the final Cancelled emit.
    // Hold both locks atomically to prevent TOCTOU race with spawn_runner
    {
        let mut s = state_lock();
        // Only arm the cancel flag for a task that is actually running (or being
        // spawned — try_start_pending moves it into `running` before spawn). For
        // an unknown / already-terminal id we do nothing, so the flag can't leak
        // an entry that no runner will ever clear.
        if s.running.contains_key(&id) {
            cancelled_lock().insert(id.clone());
            if let Some(c) = s.children.get_mut(&id) {
                kill_child_tree(c);
            }
            // If child not yet in map, spawn_runner's belt-and-suspenders check
            // will catch the cancelled flag and kill it immediately after insertion.
        }
    }
    // Note: try_start_pending will run via the runner's epilogue once finalize_after_io fires.
    let _ = app;
    Ok(())
}

/// Pause a running task: arm the pause flag and kill its child. yt-dlp leaves a
/// `.part` file behind, and the runner's finalize moves the task into the paused
/// map (status Paused) instead of Failed. No-op for non-running ids.
#[tauri::command]
#[specta::specta]
pub fn pause_task(id: String) -> Result<(), String> {
    let mut s = state_lock();
    if s.running.contains_key(&id) {
        pausing_lock().insert(id.clone());
        if let Some(c) = s.children.get_mut(&id) {
            kill_child_tree(c);
        }
    }
    Ok(())
}

/// Resume a paused task: move it back to pending (front, so it starts next) and
/// kick the scheduler. The re-spawned yt-dlp continues from the `.part` file via
/// its default `--continue`. No-op for ids that aren't paused.
#[tauri::command]
#[specta::specta]
pub fn resume_task(app: tauri::AppHandle, id: String) -> Result<(), String> {
    let task = {
        let mut s = state_lock();
        match s.paused.remove(&id) {
            Some(mut t) => {
                t.status = TaskStatus::Pending;
                t.speed.clear();
                t.eta.clear();
                s.pending.push_front(t.clone());
                Some(t)
            }
            None => None,
        }
    };
    if let Some(t) = task {
        emit_state(&app, &t);
        save_queue_to_disk_async();
        try_start_pending(&app);
    }
    Ok(())
}

#[tauri::command]
#[specta::specta]
pub fn set_concurrency(n: usize, app: tauri::AppHandle) -> Result<(), String> {
    if !(1..=5).contains(&n) {
        return Err("并发数应在 1-5 之间 / Concurrency must be between 1 and 5".into());
    }
    state_lock().concurrency = n;
    try_start_pending(&app);
    Ok(())
}

#[tauri::command]
#[specta::specta]
pub fn snapshot_tasks() -> Vec<Task> {
    let s = state_lock();
    collect_sorted(&s)
}

/// On exit: kill all running children but keep their handles for later wait.
pub fn kill_all_on_exit() {
    // Mark shutdown FIRST so any async save spawned from here on no-ops, then
    // persist current structural state synchronously before we drain.
    SHUTTING_DOWN.store(true, Ordering::SeqCst);
    save_queue_to_disk_sync();
    let mut state = state_lock();
    let drained: Vec<_> = state.children.drain().collect();
    state.running.clear();
    state.pending.clear();
    drop(state);

    let mut dying = dying_lock();
    for (_, mut c) in drained {
        kill_child_tree(&mut c);
        dying.push(c);
    }
}

/// Wait up to 3 s for the dying children to fully reap.
pub fn wait_all_on_exit() {
    let rt = match tokio::runtime::Builder::new_current_thread()
        .enable_time()
        .enable_io()
        .build()
    {
        Ok(rt) => rt,
        Err(_) => return,
    };
    rt.block_on(async {
        let children: Vec<_> = dying_lock().drain(..).collect();
        let _ = tokio::time::timeout(
            std::time::Duration::from_secs(3),
            futures_util::future::join_all(children.into_iter().map(|mut c| async move {
                let _ = c.wait().await;
            })),
        )
        .await;
    });
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sanitize_basic_template_passes() {
        assert_eq!(
            sanitize_filename_template("%(title)s.%(ext)s"),
            "%(title)s.%(ext)s"
        );
    }

    #[test]
    fn sanitize_subfolder_allowed() {
        assert_eq!(
            sanitize_filename_template("%(uploader)s/%(title)s.%(ext)s"),
            "%(uploader)s/%(title)s.%(ext)s",
        );
    }

    #[test]
    fn sanitize_blocks_dotdot_segment() {
        assert_eq!(
            sanitize_filename_template("../../etc/%(title)s"),
            "_/_/etc/%(title)s",
        );
    }

    #[test]
    fn sanitize_blocks_dotdot_with_trailing_dots_or_spaces() {
        // NTFS strips trailing dots/spaces, so ".. " and "..." are `..` in disguise.
        assert_eq!(
            sanitize_filename_template(".. /etc/%(title)s"),
            "_/etc/%(title)s"
        );
        assert_eq!(sanitize_filename_template(".../%(title)s"), "_/%(title)s");
    }

    #[test]
    fn sanitize_neutralizes_drive_letter_and_ads() {
        // `C:` would replace the base dir in Path::join on Windows.
        assert_eq!(
            sanitize_filename_template("C:/evil/%(title)s"),
            "C_/evil/%(title)s",
        );
        // NTFS alternate data stream syntax.
        assert_eq!(sanitize_filename_template("a:b.txt"), "a_b.txt");
    }

    #[test]
    fn sanitize_strips_leading_separators() {
        assert_eq!(
            sanitize_filename_template("/abs/%(title)s.%(ext)s"),
            "abs/%(title)s.%(ext)s",
        );
        assert_eq!(sanitize_filename_template("\\\\share\\foo"), "share/foo",);
    }

    #[test]
    fn sanitize_empty_falls_back_to_default() {
        assert_eq!(sanitize_filename_template(""), "%(title)s.%(ext)s");
        assert_eq!(sanitize_filename_template("   "), "%(title)s.%(ext)s");
    }

    #[test]
    fn validate_http_url_ok() {
        assert!(crate::util::validate_http_url("https://example.com").is_ok());
        assert!(crate::util::validate_http_url("HTTP://example.com").is_ok());
    }

    #[test]
    fn validate_non_http_rejected() {
        assert!(crate::util::validate_http_url("file:///etc/passwd").is_err());
        assert!(crate::util::validate_http_url("javascript:alert(1)").is_err());
        assert!(crate::util::validate_http_url("").is_err());
        assert!(crate::util::validate_http_url("https://example.com\nfoo").is_err());
    }
}
