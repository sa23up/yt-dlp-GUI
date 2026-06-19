use sha2::{Digest, Sha256};
#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;
use std::path::Path;
use std::time::Duration;
use tauri::Emitter;
use tokio::process::Command;

#[derive(Debug, Clone)]
pub struct VersionInfo {
    pub version: String,
}

pub async fn check_ytdlp_version(ytdlp_bin: &Path) -> Result<VersionInfo, String> {
    let mut cmd = Command::new(ytdlp_bin);
    cmd.arg("--version");
    #[cfg(target_os = "windows")]
    {
        cmd.creation_flags(0x08000000);
    } // CREATE_NO_WINDOW
    let output = cmd
        .output()
        .await
        .map_err(|e| format!("无法运行 yt-dlp: {e}"))?;
    if !output.status.success() {
        return Err("yt-dlp --version 执行失败".into());
    }
    let version = String::from_utf8_lossy(&output.stdout).trim().to_string();
    Ok(VersionInfo { version })
}

/// Best-effort first-line version string from a tool's version flag.
/// The flag differs per tool: ffmpeg only accepts `-version` (single dash) and
/// exits non-zero on `--version`, whereas deno wants `--version`.
async fn first_version_line(bin: &Path, flag: &str) -> Result<VersionInfo, String> {
    let mut cmd = Command::new(bin);
    cmd.arg(flag);
    #[cfg(target_os = "windows")]
    {
        cmd.creation_flags(0x08000000);
    }
    let output = cmd
        .output()
        .await
        .map_err(|e| format!("无法运行 {}: {e}", bin.display()))?;
    if !output.status.success() {
        return Err(format!(
            "{} {flag} 退出码非 0",
            bin.file_name().and_then(|n| n.to_str()).unwrap_or("binary")
        ));
    }
    let stdout = String::from_utf8_lossy(&output.stdout);
    let first = stdout.lines().next().unwrap_or("").trim().to_string();
    Ok(VersionInfo { version: first })
}

pub async fn check_ffmpeg_version() -> Result<VersionInfo, String> {
    let path = crate::util::find_ffmpeg_bin().ok_or("ffmpeg 未找到 / ffmpeg not bundled")?;
    // ffmpeg uses single-dash `-version`; `--version` errors out (exit != 0).
    first_version_line(&path, "-version").await
}

pub async fn check_deno_version() -> Result<VersionInfo, String> {
    let path = crate::util::find_deno_bin().ok_or("deno 未找到 / deno not bundled")?;
    first_version_line(&path, "--version").await
}

pub async fn check_latest_ytdlp_release() -> Result<VersionInfo, String> {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(30))
        .build()
        .map_err(|e| format!("创建 HTTP 客户端失败: {e}"))?;
    let resp = client
        .get("https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest")
        .header("User-Agent", "yt-dlp-gui")
        .header("Accept", "application/vnd.github+json")
        .send()
        .await
        .map_err(|e| format!("网络请求失败: {e}"))?;

    if !resp.status().is_success() {
        return Err(format!("GitHub API 返回: {}", resp.status()));
    }

    let text = resp
        .text()
        .await
        .map_err(|e| format!("读取响应失败: {e}"))?;
    let json: serde_json::Value =
        serde_json::from_str(&text).map_err(|e| format!("解析失败: {e}"))?;
    let tag = json["tag_name"]
        .as_str()
        .ok_or("无法解析版本号")?
        .to_string();
    Ok(VersionInfo { version: tag })
}

pub async fn download_ytdlp_update(app: tauri::AppHandle) -> Result<(), String> {
    // Always install into the user-writable managed dir. The bundled copy may
    // sit in a read-only location (/usr, Program Files, AppImage mount), so an
    // in-place replace would fail; find_ytdlp_bin() prefers this dir over the
    // bundle, so the freshly-downloaded binary takes effect next launch.
    let bin_name = if cfg!(target_os = "windows") {
        "yt-dlp.exe"
    } else {
        "yt-dlp"
    };
    let home =
        crate::util::home_dir().ok_or("无法定位 HOME 目录 / cannot resolve HOME directory")?;
    let dir = home.join(".yt-dlp-gui/bin");
    std::fs::create_dir_all(&dir)
        .map_err(|e| format!("创建目录失败 / failed to create bin dir: {e}"))?;
    let target = dir.join(bin_name);

    let platform_asset = if cfg!(target_os = "windows") {
        "yt-dlp.exe"
    } else if cfg!(target_os = "macos") {
        "yt-dlp_macos"
    } else {
        "yt-dlp_linux"
    };

    // Single API call — get release info + assets in one request
    let client = reqwest::Client::builder()
        .connect_timeout(Duration::from_secs(30))
        .build()
        .map_err(|e| format!("创建 HTTP 客户端失败: {e}"))?;
    let release_resp = client
        .get("https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest")
        .header("User-Agent", "yt-dlp-gui")
        .header("Accept", "application/vnd.github+json")
        // The shared client only sets connect_timeout (the binary download must
        // not be killed mid-stream); this small metadata request gets its own
        // total deadline.
        .timeout(Duration::from_secs(30))
        .send()
        .await
        .map_err(|e| format!("网络请求失败: {e}"))?;

    let release_text = release_resp
        .text()
        .await
        .map_err(|e| format!("读取响应失败: {e}"))?;
    let json: serde_json::Value =
        serde_json::from_str(&release_text).map_err(|e| format!("解析失败: {e}"))?;
    let assets = json["assets"].as_array().ok_or("无法解析 assets")?;

    let download_url = assets
        .iter()
        .find_map(|a| {
            let name = a["name"].as_str()?;
            if name == platform_asset {
                a["browser_download_url"].as_str().map(|s| s.to_string())
            } else {
                None
            }
        })
        .ok_or(format!("找不到平台二进制: {platform_asset}"))?;

    // Download with progress
    let resp = client
        .get(&download_url)
        .header("User-Agent", "yt-dlp-gui")
        .send()
        .await
        .map_err(|e| format!("下载失败: {e}"))?;

    let total = resp.content_length().unwrap_or(0);
    // Reject obviously oversized payloads (yt-dlp binary is ~15 MB; cap at 100 MB
    // to catch a malicious server returning a large file).
    const MAX_BYTES: u64 = 100 * 1024 * 1024;
    if total > MAX_BYTES {
        return Err(format!(
            "二进制大小异常（{total} 字节）/ binary too large (got {total} bytes)"
        ));
    }
    let tmp_path = target.with_extension("download");
    let mut downloaded: u64 = 0;
    let mut file =
        std::fs::File::create(&tmp_path).map_err(|e| format!("创建临时文件失败: {e}"))?;

    let mut stream = resp.bytes_stream();
    use futures_util::StreamExt;
    // Per-chunk read deadline. We deliberately avoid a tight overall request
    // `.timeout()` — a legitimate ~15 MB download over a slow link must not be
    // killed while it's still making progress. Instead, each chunk must arrive
    // within 60s; a server that connects then stalls/trickles bytes is treated
    // as a download error so the update can't hang forever.
    const CHUNK_TIMEOUT: Duration = Duration::from_secs(60);
    loop {
        let next = match tokio::time::timeout(CHUNK_TIMEOUT, stream.next()).await {
            Ok(next) => next,
            Err(_) => {
                let _ = std::fs::remove_file(&tmp_path);
                return Err(
                    "下载超时：服务器停止发送数据 / download timed out: server stalled".into(),
                );
            }
        };
        let Some(chunk) = next else { break };
        let chunk = match chunk {
            Ok(chunk) => chunk,
            Err(e) => {
                let _ = std::fs::remove_file(&tmp_path);
                return Err(format!("下载错误: {e}"));
            }
        };
        downloaded += chunk.len() as u64;
        if downloaded > MAX_BYTES {
            let _ = std::fs::remove_file(&tmp_path);
            return Err("二进制超出大小上限 / payload exceeded size limit".into());
        }
        if let Err(e) = std::io::Write::write_all(&mut file, &chunk) {
            let _ = std::fs::remove_file(&tmp_path);
            return Err(format!("写入失败: {e}"));
        }
        if total > 0 {
            let percent = (downloaded as f64 / total as f64 * 100.0) as u32;
            let _ = app.emit(
                crate::ipc::event::DEP_UPDATE_PROGRESS,
                serde_json::json!({ "percent": percent }),
            );
        }
    }

    // Verify hash from checksum asset — MANDATORY
    let sha256_asset_name = "SHA2-256SUMS";
    let checksum_url = assets
        .iter()
        .find_map(|a| {
            let name = a["name"].as_str()?;
            if name == sha256_asset_name {
                a["browser_download_url"].as_str().map(|s| s.to_string())
            } else {
                None
            }
        })
        .ok_or("SHA2-256SUMS 缺失，拒绝替换")?;

    let checksum_resp = client
        .get(&checksum_url)
        .header("User-Agent", "yt-dlp-gui")
        .timeout(Duration::from_secs(30))
        .send()
        .await
        .map_err(|e| format!("下载校验和失败: {e}"))?;
    let checksum_text = checksum_resp
        .text()
        .await
        .map_err(|e| format!("读取校验和失败: {e}"))?;
    // Match the exact filename column (`<hash>  <name>`), not a substring, so
    // `yt-dlp_linux` can't accidentally match a `yt-dlp_linux.zip` line.
    let expected = checksum_text
        .lines()
        .find_map(|l| {
            let mut it = l.split_whitespace();
            let hash = it.next()?;
            let name = it.next()?;
            (name == platform_asset).then_some(hash)
        })
        .unwrap_or("");
    if expected.is_empty() {
        let _ = std::fs::remove_file(&tmp_path);
        return Err(format!(
            "SHA2-256SUMS 中找不到 {platform_asset} 条目，拒绝替换"
        ));
    }
    if !verify_hash(&tmp_path, expected)? {
        let _ = std::fs::remove_file(&tmp_path);
        return Err("SHA-256 校验失败，下载文件可能损坏".into());
    }

    replace_binary(&tmp_path, &target)?;
    Ok(())
}

pub fn verify_hash(path: &Path, expected: &str) -> Result<bool, String> {
    let data = std::fs::read(path).map_err(|e| format!("读取文件失败: {e}"))?;
    let mut hasher = Sha256::new();
    hasher.update(&data);
    let hash = hasher.finalize();
    let result: String = hash.iter().map(|b| format!("{:02x}", b)).collect();
    Ok(result == expected.to_lowercase())
}

pub fn replace_binary(new: &Path, target: &Path) -> Result<(), String> {
    let backup = target.with_extension("old");
    if target.exists() {
        std::fs::rename(target, &backup).map_err(|e| format!("备份失败: {e}"))?;
    }
    if let Err(e) = std::fs::rename(new, target) {
        // Rollback: restore backup
        if backup.exists() {
            let _ = std::fs::rename(&backup, target);
        }
        return Err(format!("替换失败: {e}"));
    }
    // Restore executable permission on Unix
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let _ = std::fs::set_permissions(target, std::fs::Permissions::from_mode(0o755));
    }
    // Clean up backup
    if backup.exists() {
        let _ = std::fs::remove_file(&backup);
    }
    Ok(())
}
