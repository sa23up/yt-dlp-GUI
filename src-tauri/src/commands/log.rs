use std::io::Write;
use std::path::PathBuf;
use std::sync::{LazyLock, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};

const LOG_MAX_BYTES: u64 = 1_000_000; // 1 MB

/// Serializes log writes so concurrent runners can't interleave partial lines
/// or both trigger rotation at once.
static LOG_LOCK: LazyLock<Mutex<()>> = LazyLock::new(|| Mutex::new(()));

fn log_path() -> PathBuf {
    crate::util::data_dir().join("app.log")
}

fn ts() -> String {
    let d = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default();
    let secs = d.as_secs() as i64;
    // Reuse chrono-free conversion via Tauri runtime? We're std-only.
    // Compute date components directly (UTC).
    let days_since_epoch = secs.div_euclid(86_400);
    let sod = secs.rem_euclid(86_400);
    let (h, m, s) = (sod / 3600, (sod % 3600) / 60, sod % 60);
    let (y, mo, da) = days_to_ymd(days_since_epoch);
    format!("{y:04}-{mo:02}-{da:02}T{h:02}:{m:02}:{s:02}Z")
}

/// Convert days-since-epoch (1970-01-01) to (year, month, day) in proleptic Gregorian.
fn days_to_ymd(days: i64) -> (i32, u32, u32) {
    // Algorithm from Howard Hinnant — std-free, valid for any signed day count.
    let z = days + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = (z - era * 146_097) as u64; // [0, 146097)
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365; // [0, 399]
    let y = yoe as i64 + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100); // [0, 365]
    let mp = (5 * doy + 2) / 153; // [0, 11]
    let d = doy - (153 * mp + 2) / 5 + 1; // [1, 31]
    let m = if mp < 10 { mp + 3 } else { mp - 9 }; // [1, 12]
    let y = if m <= 2 { y + 1 } else { y };
    (y as i32, m as u32, d as u32)
}

fn rotate_if_needed(path: &std::path::Path) {
    if let Ok(meta) = std::fs::metadata(path) {
        if meta.len() > LOG_MAX_BYTES {
            let _ = std::fs::rename(path, path.with_extension("log.1"));
        }
    }
}

#[tauri::command]
#[specta::specta]
pub fn write_log(level: String, message: String) {
    // `level` is IPC-reachable: whitelist it so a crafted value can't inject
    // fake log fields.
    let level = match level.as_str() {
        "ERROR" | "WARN" | "INFO" | "DEBUG" => level.as_str(),
        _ => "INFO",
    };
    let _guard = LOG_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    let path = log_path();
    if let Some(dir) = path.parent() {
        let _ = std::fs::create_dir_all(dir);
    }
    rotate_if_needed(&path);
    if let Ok(mut f) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&path)
    {
        // Sanitize message to prevent log injection attacks
        // Replace newlines and carriage returns with escaped versions
        let sanitized = message
            .replace('\n', "\\n")
            .replace('\r', "\\r")
            .replace('\0', "\\0");
        let _ = writeln!(f, "[{}] [{}] {}", ts(), level, sanitized);
    }
}

/// Read the most recent N lines of app.log (default 200, max 1000).
#[tauri::command]
#[specta::specta]
pub fn read_log(tail: Option<usize>) -> Result<Vec<String>, String> {
    let path = log_path();
    if !path.exists() {
        return Ok(vec![]);
    }
    let raw = std::fs::read_to_string(&path).map_err(|e| e.to_string())?;
    let lines: Vec<&str> = raw.lines().collect();
    let n = tail.unwrap_or(200).min(1000);
    let start = lines.len().saturating_sub(n);
    Ok(lines[start..].iter().map(|s| s.to_string()).collect())
}
