#[derive(Debug, Clone)]
pub struct ProgressEvent {
    pub percent: f64,
    pub speed: String,
    pub eta: String,
}

/// Sanitize a format ID to prevent injection attacks.
/// yt-dlp format IDs should be alphanumeric with hyphens/underscores only.
fn sanitize_format_id(id: &str) -> String {
    id.chars()
        .filter(|c| c.is_alphanumeric() || *c == '-' || *c == '_')
        .collect()
}

/// Build the `-f` format selector string for yt-dlp.
///
/// - Both ids `None` → "Best Quality". Honors `max_height` (0 = unlimited) so
///   that the Settings → Format Preference cap applies to one-click / batch /
///   playlist downloads, not just the manual picker's displayed list. The cap
///   is *hard*: a video whose only formats exceed it fails rather than silently
///   downloading something larger (PRD US21 — "never accidentally download 8K").
/// - An explicit video id means the user hand-picked a format; the height cap
///   is intentionally NOT applied (their choice wins).
pub fn build_format_selector(
    video_id: Option<&str>,
    audio_id: Option<&str>,
    max_height: u32,
) -> String {
    match (video_id, audio_id) {
        (None, None) => {
            if max_height > 0 {
                format!("bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]")
            } else {
                "bestvideo+bestaudio/best".to_string()
            }
        }
        (Some(v), None) => sanitize_format_id(v),
        (None, Some(a)) => sanitize_format_id(a),
        (Some(v), Some(a)) => format!("{}+{}", sanitize_format_id(v), sanitize_format_id(a)),
    }
}

/// Map a preferred-codec setting to a yt-dlp `-S` sort token, or `None` for
/// "any"/unknown. Used only for Best-Quality / batch downloads (no hand-picked
/// video format) to *prefer* a codec without hard-failing when it's absent.
pub fn codec_sort(preferred_codec: &str) -> Option<String> {
    let vcodec = match preferred_codec {
        "h264" => "avc",
        "vp9" => "vp9",
        "av1" => "av01",
        _ => return None, // "any" or unrecognized
    };
    Some(format!("vcodec:{vcodec}"))
}

/// Parse a single line of yt-dlp progress output.
/// Expected template: "%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s"
pub fn parse_progress(line: &str) -> Option<ProgressEvent> {
    let fields: Vec<&str> = line.trim().split('|').collect();
    if fields.len() != 3 {
        // In debug builds, surface unmatched lines to catch yt-dlp output-format
        // changes. Silenced in release so it doesn't spam stderr on every
        // ordinary non-progress stdout line.
        #[cfg(debug_assertions)]
        if !line.is_empty() && !line.starts_with('[') {
            eprintln!("[parse_progress] unmatched line: {line}");
        }
        return None;
    }
    let percent_str = fields[0].trim_end_matches('%').trim();
    let percent = percent_str.parse::<f64>().ok()?;
    Some(ProgressEvent {
        percent,
        speed: fields[1].trim().to_string(),
        eta: fields[2].trim().to_string(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn selector_best_quality_defaults() {
        assert_eq!(
            build_format_selector(None, None, 0),
            "bestvideo+bestaudio/best"
        );
    }

    #[test]
    fn selector_best_quality_with_height_cap() {
        assert_eq!(
            build_format_selector(None, None, 1080),
            "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
        );
    }

    #[test]
    fn selector_explicit_video_ignores_height_cap() {
        // Hand-picked format wins — cap must NOT be injected.
        assert_eq!(build_format_selector(Some("399"), None, 720), "399");
    }

    #[test]
    fn selector_audio_only() {
        assert_eq!(build_format_selector(None, Some("140"), 0), "140");
    }

    #[test]
    fn selector_combined() {
        assert_eq!(
            build_format_selector(Some("313"), Some("251"), 0),
            "313+251"
        );
    }

    #[test]
    fn codec_sort_maps_known_codecs() {
        assert_eq!(codec_sort("h264").as_deref(), Some("vcodec:avc"));
        assert_eq!(codec_sort("vp9").as_deref(), Some("vcodec:vp9"));
        assert_eq!(codec_sort("av1").as_deref(), Some("vcodec:av01"));
    }

    #[test]
    fn codec_sort_any_is_none() {
        assert_eq!(codec_sort("any"), None);
        assert_eq!(codec_sort(""), None);
    }

    #[test]
    fn progress_typical_line() {
        let e = parse_progress(" 67.3%|12.5MiB/s|00:32").unwrap();
        assert!((e.percent - 67.3).abs() < 0.01);
        assert_eq!(e.speed, "12.5MiB/s");
        assert_eq!(e.eta, "00:32");
    }

    #[test]
    fn progress_unknown_speed() {
        let e = parse_progress("45.0%|Unknown|--:--").unwrap();
        assert_eq!(e.speed, "Unknown");
        assert_eq!(e.eta, "--:--");
    }

    #[test]
    fn progress_non_progress_line_is_none() {
        assert!(parse_progress("[download] Destination: video.mp4").is_none());
    }

    #[test]
    fn progress_100_percent() {
        let e = parse_progress("100.0%|0.0KiB/s|00:00").unwrap();
        assert!((e.percent - 100.0).abs() < 0.01);
    }

    // Security tests for format ID sanitization
    #[test]
    fn sanitize_format_id_allows_valid_chars() {
        assert_eq!(sanitize_format_id("399"), "399");
        assert_eq!(sanitize_format_id("video-1080p"), "video-1080p");
        assert_eq!(sanitize_format_id("audio_high"), "audio_high");
    }

    #[test]
    fn sanitize_format_id_strips_dangerous_chars() {
        // Prevent injection via format IDs
        assert_eq!(sanitize_format_id("399]malicious"), "399malicious");
        assert_eq!(sanitize_format_id("399/etc/passwd"), "399etcpasswd");
        assert_eq!(sanitize_format_id("399;rm -rf"), "399rm-rf"); // hyphen is allowed
        assert_eq!(sanitize_format_id("399`whoami`"), "399whoami");
        assert_eq!(sanitize_format_id("399$()"), "399");
        assert_eq!(sanitize_format_id("399\n140"), "399140");
    }

    #[test]
    fn selector_sanitizes_injected_format_ids() {
        // Ensure combined selectors are safe
        assert_eq!(
            build_format_selector(Some("399]bad"), Some("140;evil"), 0),
            "399bad+140evil"
        );
    }
}
