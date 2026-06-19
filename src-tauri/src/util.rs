use std::io::Write;
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

pub fn home_dir() -> Option<PathBuf> {
    std::env::var("HOME")
        .or_else(|_| std::env::var("USERPROFILE"))
        .ok()
        .map(PathBuf::from)
}

/// Process-global cache for Tauri's resource directory, populated once at
/// startup (see `lib.rs` setup). We can't call `tauri::Manager::path()` from
/// these free functions, so the app hands us the resolved path here.
///
/// WHY: with `resources` bundling, the binaries land next to the exe on
/// Windows (and in dev) but under the resource dir on Linux packages
/// (.deb/.AppImage). Caching the resource dir lets the lookups below probe both
/// locations rather than betting on a single layout and silently falling back
/// to system PATH.
static RESOURCE_DIR: std::sync::OnceLock<Option<PathBuf>> = std::sync::OnceLock::new();

/// Store Tauri's resource dir. Idempotent (first write wins).
pub fn set_resource_dir(p: Option<PathBuf>) {
    let _ = RESOURCE_DIR.set(p);
}

/// The cached resource dir, if it was set and resolved at startup.
fn resource_dir() -> Option<PathBuf> {
    RESOURCE_DIR.get().cloned().flatten()
}

/// Cheap scheme check shared by the enqueue / fetch / playlist paths.
pub fn is_http_url(url: &str) -> bool {
    let l = url.trim().to_lowercase();
    l.starts_with("http://") || l.starts_with("https://")
}

/// Validate a user-supplied download URL: http/https only, and no embedded
/// newlines (which could smuggle a second token). Single source of truth for
/// every command that accepts a URL.
pub fn validate_http_url(url: &str) -> Result<(), String> {
    let trimmed = url.trim();
    if trimmed.is_empty() {
        return Err("URL 为空 / URL is empty".into());
    }
    if !is_http_url(trimmed) {
        return Err("仅接受 http/https 链接 / Only http/https URLs accepted".into());
    }
    if trimmed.contains('\n') || trimmed.contains('\r') {
        return Err("URL 含非法字符 / URL contains illegal characters".into());
    }
    Ok(())
}

/// Locate the yt-dlp binary. Search order:
/// 1. `YTDLP_BIN` environment variable
/// 2. `~/.yt-dlp-gui/bin/yt-dlp` — runtime self-updated copy (preferred so an
///    in-app update wins over a possibly read-only bundled copy)
/// 3. Next to the current executable (where `resources` land on Windows / dev)
/// 4. The resource dir (where `resources` land on Linux packages)
/// 5. `PATH` fallback: `"yt-dlp"`
pub fn find_ytdlp_bin() -> PathBuf {
    if let Ok(p) = std::env::var("YTDLP_BIN") {
        return PathBuf::from(p);
    }
    // Self-updated copy first: it must override the bundle, which may live in a
    // read-only install dir and can't be replaced in place.
    if let Some(home) = home_dir() {
        for name in &["yt-dlp", "yt-dlp.exe"] {
            let managed = home.join(".yt-dlp-gui/bin").join(name);
            if managed.exists() {
                return managed;
            }
        }
    }
    // Probe every plausible bundle root: next to the exe (Windows / dev) and
    // the resource dir (Linux packages), so we don't silently fall through to
    // system PATH when the bundled binaries live in the resource dir.
    for root in bundle_roots() {
        for name in &["yt-dlp", "yt-dlp.exe"] {
            for candidate in [root.join("binaries").join(name), root.join(name)] {
                if candidate.exists() {
                    return candidate;
                }
            }
        }
    }
    PathBuf::from("yt-dlp")
}

/// Candidate directories that may contain the bundled binaries, in priority
/// order: next to the executable first (Windows / dev), then the resource dir
/// (where `resources` bundling lands on Linux packages). Each is later probed
/// directly and under a `binaries/` subdir.
fn bundle_roots() -> Vec<PathBuf> {
    let mut roots: Vec<PathBuf> = Vec::new();
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            roots.push(dir.to_path_buf());
        }
    }
    if let Some(rd) = resource_dir() {
        roots.push(rd);
    }
    roots
}

/// Locate a bundled side-binary by base name (ffmpeg / deno). Search order:
/// for each bundle root (next-to-exe first, then resource dir):
/// `<root>/binaries/<name>` → `<root>/<name>`; then `~/.yt-dlp-gui/bin/<name>`.
/// `.exe` is appended on Windows. Returns None when nothing is found (dev mode),
/// so the caller can fall back to a PATH lookup.
fn find_bundled_bin(base: &str) -> Option<PathBuf> {
    let name = if cfg!(target_os = "windows") {
        format!("{base}.exe")
    } else {
        base.to_string()
    };
    for root in bundle_roots() {
        for candidate in [root.join("binaries").join(&name), root.join(&name)] {
            if candidate.exists() {
                return Some(candidate);
            }
        }
    }
    if let Some(home) = home_dir() {
        let p = home.join(".yt-dlp-gui/bin").join(&name);
        if p.exists() {
            return Some(p);
        }
    }
    None
}

/// Locate the bundled ffmpeg binary, if present.
pub fn find_ffmpeg_bin() -> Option<PathBuf> {
    find_bundled_bin("ffmpeg")
}

/// Best-effort: mark every file in the bundled `binaries/` dirs executable.
/// Tauri's `resources` bundling copies the binaries as data and does not
/// reliably preserve the +x bit on Linux, so a freshly installed yt-dlp /
/// ffmpeg / ffprobe / deno can land non-executable and fail to spawn. Run once
/// at startup (see lib.rs). No-op on Windows and when the dir doesn't exist.
#[cfg(unix)]
pub fn ensure_bundled_executables() {
    use std::os::unix::fs::PermissionsExt;
    for root in bundle_roots() {
        let dir = root.join("binaries");
        let Ok(entries) = std::fs::read_dir(&dir) else {
            continue;
        };
        for entry in entries.flatten() {
            let p = entry.path();
            if !p.is_file() {
                continue;
            }
            if let Ok(meta) = std::fs::metadata(&p) {
                let mut perms = meta.permissions();
                let mode = perms.mode();
                if mode & 0o111 != 0o111 {
                    perms.set_mode(mode | 0o111);
                    let _ = std::fs::set_permissions(&p, perms);
                }
            }
        }
    }
}
#[cfg(not(unix))]
pub fn ensure_bundled_executables() {}

/// Settings/queue live under ~/.yt-dlp-gui/.
pub fn data_dir() -> PathBuf {
    let home = home_dir().unwrap_or_else(|| PathBuf::from("."));
    home.join(".yt-dlp-gui")
}

static TMP_SEQ: AtomicU64 = AtomicU64::new(0);

/// Atomically write text to a file: tmp + fsync + rename.
/// tmp filename is timestamp+counter so concurrent writes can't collide.
pub fn atomic_write(path: &std::path::Path, data: &str) -> Result<(), String> {
    let dir = path.parent().ok_or("path has no parent")?;
    std::fs::create_dir_all(dir).map_err(|e| format!("创建目录失败: {e}"))?;
    let stem = path.file_name().and_then(|n| n.to_str()).unwrap_or("write");
    let ts = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_nanos() as u64)
        .unwrap_or(0);
    let seq = TMP_SEQ.fetch_add(1, Ordering::Relaxed);
    let tmp = dir.join(format!(".{stem}.{ts:x}-{seq:x}.tmp"));
    {
        let mut f = std::fs::File::create(&tmp).map_err(|e| format!("创建临时文件失败: {e}"))?;
        f.write_all(data.as_bytes())
            .map_err(|e| format!("写入失败: {e}"))?;
        f.sync_all().map_err(|e| format!("fsync 失败: {e}"))?;
    }
    std::fs::rename(&tmp, path).map_err(|e| {
        let _ = std::fs::remove_file(&tmp);
        format!("替换失败: {e}")
    })
}

/// Locate the bundled deno binary, if present. yt-dlp uses deno as the JS
/// runtime for YouTube extractor JS execution from 2025.11.12 onward.
pub fn find_deno_bin() -> Option<PathBuf> {
    find_bundled_bin("deno")
}

/// Build a `PATH` value for spawned yt-dlp processes with the bundled binary
/// directories prepended. yt-dlp discovers `deno` (the JS runtime it needs for
/// YouTube extractor challenges since 2025.11.12) and `ffmpeg`/`ffprobe` by
/// searching `PATH`; the bundled copies live in our bundle dir(s) (next to the
/// exe, or the resource dir on Linux), which aren't on the inherited `PATH`.
/// Without this the shipped deno is unreachable.
///
/// Returns `None` when no bundle directory exists (e.g. dev mode), leaving the
/// child's `PATH` untouched so it falls back to system-installed tools.
pub fn augmented_path() -> Option<std::ffi::OsString> {
    let mut dirs: Vec<PathBuf> = Vec::new();
    // Same roots find_bundled_bin probes: exe dir (Windows / dev) then the
    // resource dir (Linux packages), each with and without a `binaries/` subdir.
    for root in bundle_roots() {
        dirs.push(root.join("binaries"));
        dirs.push(root);
    }
    if let Some(home) = home_dir() {
        dirs.push(home.join(".yt-dlp-gui/bin"));
    }
    dirs.retain(|d| d.is_dir());
    prepend_to_path(dirs, std::env::var_os("PATH"))
}

/// Pure core of [`augmented_path`]: prepend `dirs` to an existing `PATH`.
/// Returns `None` when `dirs` is empty so the caller leaves `PATH` untouched.
fn prepend_to_path(
    mut dirs: Vec<PathBuf>,
    existing: Option<std::ffi::OsString>,
) -> Option<std::ffi::OsString> {
    if dirs.is_empty() {
        return None;
    }
    if let Some(e) = existing {
        dirs.extend(std::env::split_paths(&e));
    }
    std::env::join_paths(dirs).ok()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn prepend_to_path_empty_is_none() {
        assert!(prepend_to_path(vec![], Some("/usr/bin".into())).is_none());
    }

    #[test]
    fn prepend_to_path_puts_bundle_dirs_first() {
        let out = prepend_to_path(
            vec![PathBuf::from("/opt/app/binaries")],
            Some(std::ffi::OsString::from("/usr/bin:/bin")),
        )
        .expect("non-empty dirs must yield Some");
        let parts: Vec<PathBuf> = std::env::split_paths(&out).collect();
        assert_eq!(parts.first(), Some(&PathBuf::from("/opt/app/binaries")));
        assert!(parts.contains(&PathBuf::from("/usr/bin")));
    }
}
