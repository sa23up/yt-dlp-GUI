use crate::errors::ErrorKind;
use crate::ytdlp;
use serde::{Deserialize, Serialize};

/// Hard upper bound on a single `fetch_formats` call. yt-dlp normally returns
/// in under 5s; anything past 30s indicates a hang or a very large playlist.
const FETCH_TIMEOUT: std::time::Duration = std::time::Duration::from_secs(30);

#[derive(Debug, Serialize, specta::Type)]
#[serde(rename_all = "camelCase")]
pub struct FormatList {
    pub title: String,
    pub channel: String,
    pub duration: String,
    pub thumbnail: String,
    pub video_formats: Vec<FormatInfo>,
    pub audio_formats: Vec<FormatInfo>,
}

#[derive(Debug, Clone, Serialize, specta::Type)]
#[serde(rename_all = "camelCase")]
pub struct FormatInfo {
    pub id: String,
    pub label: String,
    pub resolution: String,
    pub codec: String,
    pub filesize: String,
    pub ext: String,
    pub height: u32,
    pub fps: f64,
    /// Underlying byte count (0 if unknown). Sort key; not displayed.
    pub size_bytes: u64,
    /// True if the format carries both video and audio (no merge needed).
    pub muxed: bool,
}

#[derive(Debug, Deserialize)]
struct YtdlpJson {
    title: Option<String>,
    channel: Option<String>,
    duration: Option<f64>,
    thumbnail: Option<String>,
    formats: Option<Vec<YtFormat>>,
}

#[derive(Debug, Deserialize)]
struct YtFormat {
    format_id: Option<String>,
    format_note: Option<String>,
    ext: Option<String>,
    resolution: Option<String>,
    filesize: Option<f64>,
    filesize_approx: Option<f64>,
    vcodec: Option<String>,
    acodec: Option<String>,
    height: Option<f64>,
    fps: Option<f64>,
    abr: Option<f64>,
}

fn human_size(bytes: Option<u64>) -> String {
    match bytes {
        None | Some(0) => "—".into(),
        Some(b) if b < 1024 => format!("{b} B"),
        Some(b) if b < 1024 * 1024 => format!("{:.1} KiB", b as f64 / 1024.0),
        Some(b) if b < 1024 * 1024 * 1024 => format!("{:.1} MiB", b as f64 / (1024.0 * 1024.0)),
        Some(b) => format!("{:.1} GiB", b as f64 / (1024.0 * 1024.0 * 1024.0)),
    }
}

fn fmt_duration(secs: f64) -> String {
    let h = (secs / 3600.0) as u32;
    let m = ((secs % 3600.0) / 60.0) as u32;
    let s = (secs % 60.0) as u32;
    if h > 0 {
        format!("{h}:{m:02}:{s:02}")
    } else {
        format!("{m}:{s:02}")
    }
}

#[tauri::command]
#[specta::specta]
pub async fn fetch_formats(
    url: String,
    net: ytdlp::args::NetworkOptions,
) -> Result<FormatList, ErrorKind> {
    crate::util::validate_http_url(&url).map_err(ErrorKind::Unknown)?;
    let ytdlp_bin = crate::util::find_ytdlp_bin();

    // Cookie / proxy must apply to metadata fetch too, otherwise cookie-gated
    // (YouTube bot check) or region-locked content can't even list formats while
    // the actual download would succeed.
    let mut args = net.to_args().map_err(ErrorKind::Unknown)?;
    args.extend([
        "-J".to_string(),
        // Treat watch?v=X&list=Y as just video X, not the whole playlist.
        "--no-playlist".to_string(),
        "--no-warnings".to_string(),
        url,
    ]);
    let child =
        ytdlp::spawn_ytdlp(&ytdlp_bin, &args).map_err(|e| ErrorKind::Unknown(e.to_string()))?;
    let output = match tokio::time::timeout(FETCH_TIMEOUT, child.wait_with_output()).await {
        Ok(r) => r.map_err(|e| ErrorKind::Unknown(e.to_string()))?,
        Err(_) => {
            // kill_on_drop reaps the child when `child` is dropped at await unwind
            return Err(ErrorKind::NetworkTimeout);
        }
    };

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        // Structured, localizable error. The Unknown fallback carries raw
        // stderr, which can include local filesystem paths — reduce it to a
        // safe snippet before it crosses the IPC boundary to the UI.
        return Err(match crate::errors::classify(&stderr) {
            ErrorKind::Unknown(raw) => ErrorKind::Unknown(crate::errors::snippet(&raw)),
            classified => classified,
        });
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let json: YtdlpJson = serde_json::from_str(&stdout)
        .map_err(|e| ErrorKind::Unknown(format!("JSON 解析失败 / parse failed: {e}")))?;

    let title = json.title.unwrap_or_default();
    let channel = json.channel.unwrap_or_default();
    let duration = json.duration.map(fmt_duration).unwrap_or_default();
    let thumbnail = json.thumbnail.unwrap_or_default();

    let formats = json.formats.unwrap_or_default();
    let mut video_formats: Vec<FormatInfo> = Vec::new();
    let mut audio_formats: Vec<FormatInfo> = Vec::new();

    for f in &formats {
        let vc = f.vcodec.as_deref().unwrap_or("none");
        let ac = f.acodec.as_deref().unwrap_or("none");
        // Skip formats yt-dlp can't address — passing "?" or "" would fail the -f selector.
        let id = match f.format_id.clone() {
            Some(id) if !id.is_empty() => id,
            _ => continue,
        };
        let ext = f.ext.clone().unwrap_or_else(|| "?".into());
        let res = f.resolution.clone().unwrap_or_else(|| "?".into());
        let note = f.format_note.clone().unwrap_or_default();
        let bytes = f
            .filesize
            .or(f.filesize_approx)
            .map(|s| s as u64)
            .unwrap_or(0);
        let size_str = human_size(if bytes == 0 { None } else { Some(bytes) });
        let height = f.height.unwrap_or(0.0) as u32;
        let fps = f.fps.unwrap_or(0.0);
        let label_res = if note.is_empty() {
            res.clone()
        } else {
            note.clone()
        };

        let has_video = vc != "none";
        let has_audio = ac != "none";

        if has_video {
            video_formats.push(FormatInfo {
                id: id.clone(),
                label: format!("{label_res} {vc}"),
                resolution: label_res.clone(),
                codec: vc.into(),
                filesize: size_str.clone(),
                ext: ext.clone(),
                height,
                fps,
                size_bytes: bytes,
                muxed: has_audio,
            });
        }
        if has_audio && !has_video {
            let abr_label = f.abr.map(|a| format!("{a:.0}k")).unwrap_or_default();
            audio_formats.push(FormatInfo {
                id,
                label: if abr_label.is_empty() {
                    ac.to_string()
                } else {
                    format!("{ac} {abr_label}")
                },
                resolution: abr_label,
                codec: ac.into(),
                filesize: size_str,
                ext,
                height: 0,
                fps: 0.0,
                size_bytes: bytes,
                muxed: false,
            });
        }
    }

    // Sort: video by descending height (then codec), audio by descending bitrate proxy (size_bytes).
    video_formats.sort_by(|a, b| {
        b.height
            .cmp(&a.height)
            .then_with(|| b.size_bytes.cmp(&a.size_bytes))
            .then_with(|| a.codec.cmp(&b.codec))
    });
    audio_formats.sort_by_key(|f| std::cmp::Reverse(f.size_bytes));

    Ok(FormatList {
        title,
        channel,
        duration,
        thumbnail,
        video_formats,
        audio_formats,
    })
}
