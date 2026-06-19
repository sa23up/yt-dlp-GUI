/// Classified error type from yt-dlp stderr output.
///
/// Used by `commands::formats::fetch_formats` to turn a failed parse into a
/// structured error that the frontend can localize. The download path no longer
/// surfaces per-task error detail (terminal tasks are notification-only), so
/// there is intentionally no user-message/reasons/suggestions builder here.
#[derive(Debug, Clone, PartialEq, serde::Serialize, specta::Type)]
#[serde(tag = "kind", content = "message")]
pub enum ErrorKind {
    /// 403, bot detection, "Sign in to confirm you're not a bot"
    RateLimited,
    /// 404, "not available", private, deleted
    VideoUnavailable,
    /// timeout, connection refused, DNS resolve failure
    NetworkTimeout,
    /// cookies expired, invalid cookies
    CookieExpired,
    /// disk full, quota exceeded, no space
    DiskFull,
    /// Any unrecognized error pattern; contains a sanitized snippet
    Unknown(String),
}

/// First non-empty line of a raw message, trimmed to 120 chars. Full yt-dlp
/// stderr can carry local filesystem paths (cookie file, output dir) and must
/// never reach the UI verbatim — callers that surface `Unknown(_)` to the
/// frontend run its payload through this first.
pub fn snippet(raw: &str) -> String {
    let first = raw.lines().find(|l| !l.trim().is_empty()).unwrap_or("");
    first.trim().chars().take(120).collect()
}

impl std::fmt::Display for ErrorKind {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        // Fallback display for logging/debugging (always English)
        match self {
            ErrorKind::RateLimited => f.write_str("Request blocked (rate limited)"),
            ErrorKind::VideoUnavailable => f.write_str("Video unavailable"),
            ErrorKind::NetworkTimeout => f.write_str("Network connection failed"),
            ErrorKind::CookieExpired => f.write_str("Login expired"),
            ErrorKind::DiskFull => f.write_str("Disk full"),
            ErrorKind::Unknown(s) => {
                let snippet = snippet(s);
                if snippet.is_empty() {
                    f.write_str("Unknown error")
                } else {
                    write!(f, "Unknown error: {snippet}")
                }
            }
        }
    }
}

/// Classify yt-dlp's stderr output into an ErrorKind.
///
/// Scans each line case-insensitively. First keyword match wins.
/// Returns `Unknown(raw_stderr)` when no pattern is recognized.
/// This function NEVER fails — classification is always successful.
pub fn classify(stderr: &str) -> ErrorKind {
    let lower = stderr.to_lowercase();

    for line in lower.lines() {
        // 1. CookieExpired — cookie keyword PLUS a co-keyword
        if (line.contains("cookie") || line.contains("cookies"))
            && contains_any(
                line,
                &["expired", "invalid", "required", "login", "sign in"],
            )
        {
            return ErrorKind::CookieExpired;
        }

        // 2. RateLimited
        if contains_any(
            line,
            &[
                "403",
                "bot",
                "sign in to confirm",
                "rate limit",
                "too many requests",
            ],
        ) {
            return ErrorKind::RateLimited;
        }

        // 3. VideoUnavailable — but NOT if "format" or "codec" on same line.
        // Prefer specific phrases over bare keywords ("removed", "deleted",
        // "404") to avoid misclassifying unrelated stderr lines. Bare "404"
        // is kept only in combination with video-context wording.
        if (contains_any(
            line,
            &[
                "video unavailable",
                "this video is private",
                "this video is unavailable",
                "video has been removed",
                "this video has been removed",
                "account associated with this video has been terminated",
            ],
        ) || (line.contains("404") && line.contains("video")))
            && !contains_any(line, &["format", "codec"])
        {
            return ErrorKind::VideoUnavailable;
        }

        // 4. DiskFull — checked before NetworkTimeout so a compound line like
        // "timeout writing to disk: no space" classifies by its root cause
        // (disk), not the incidental "timeout" keyword.
        if contains_any(
            line,
            &[
                "no space",
                "disk full",
                "quota exceeded",
                "not enough space",
                "disk quota",
            ],
        ) {
            return ErrorKind::DiskFull;
        }

        // 5. NetworkTimeout
        if contains_any(
            line,
            &[
                "timeout",
                "timed out",
                "connection refused",
                "cannot resolve",
                "name resolution",
                "dns",
                "unreachable",
                "network is unreachable",
                "could not connect",
            ],
        ) {
            return ErrorKind::NetworkTimeout;
        }
    }

    // 6. Fallback
    ErrorKind::Unknown(stderr.to_string())
}

fn contains_any(line: &str, keywords: &[&str]) -> bool {
    keywords.iter().any(|k| line.contains(k))
}

#[cfg(test)]
mod tests {
    use super::*;

    // ── Fixtures ──────────────────────────────────────────────

    const FIXTURE_RATE_LIMITED_1: &str = "\
ERROR: [youtube] xxxxx: Got HTTP Error 403: Forbidden
Cause: Sign in to confirm you're not a bot. Use --cookies-from-browser or --cookies for the authentication.";

    const FIXTURE_RATE_LIMITED_2: &str = "\
ERROR: [youtube] xxxxx: This video is not available
ERROR: Sign in to confirm you're not a bot
YouTube said: Unable to retrieve video";

    const FIXTURE_VIDEO_UNAVAILABLE_1: &str =
        "ERROR: [youtube] xxxxx: Video unavailable. This video is private";

    const FIXTURE_VIDEO_UNAVAILABLE_2: &str =
        "ERROR: [youtube] dQw4w9WgXcQ: Video unavailable. This video has been removed by the uploader";

    const FIXTURE_NETWORK_TIMEOUT_1: &str =
        "ERROR: Unable to download webpage: <urlopen error [Errno 110] Connection timed out>";

    const FIXTURE_NETWORK_TIMEOUT_2: &str =
        "ERROR: Unable to download API page: <urlopen error [Errno -3] Temporary failure in name resolution>";

    const FIXTURE_COOKIE_EXPIRED_1: &str =
        "ERROR: [youtube] xxxxx: Unable to download video. Your cookies may have expired. Please refresh them.";

    const FIXTURE_COOKIE_EXPIRED_2: &str =
        "ERROR: [youtube] xxxxx: This video is age-restricted and requires login. Use --cookies-from-browser.";

    const FIXTURE_DISK_FULL_1: &str =
        "ERROR: unable to open for writing: [Errno 28] No space left on device";

    const FIXTURE_DISK_FULL_2: &str =
        "ERROR: [Errno 122] Disk quota exceeded: '/home/user/video.mp4.part'";

    // ── Classification: RateLimited ───────────────────────────

    #[test]
    fn test_classify_rate_limited_1() {
        let result = classify(FIXTURE_RATE_LIMITED_1);
        assert_eq!(result, ErrorKind::RateLimited);
    }

    #[test]
    fn test_classify_rate_limited_2() {
        // Multi-line: second line triggers
        let result = classify(FIXTURE_RATE_LIMITED_2);
        assert_eq!(result, ErrorKind::RateLimited);
    }

    // ── Classification: VideoUnavailable ──────────────────────

    #[test]
    fn test_classify_video_unavailable_1() {
        let result = classify(FIXTURE_VIDEO_UNAVAILABLE_1);
        assert_eq!(result, ErrorKind::VideoUnavailable);
    }

    #[test]
    fn test_classify_video_unavailable_2() {
        let result = classify(FIXTURE_VIDEO_UNAVAILABLE_2);
        assert_eq!(result, ErrorKind::VideoUnavailable);
    }

    // ── Classification: NetworkTimeout ────────────────────────

    #[test]
    fn test_classify_network_timeout_1() {
        let result = classify(FIXTURE_NETWORK_TIMEOUT_1);
        assert_eq!(result, ErrorKind::NetworkTimeout);
    }

    #[test]
    fn test_classify_network_timeout_2() {
        // DNS variant
        let result = classify(FIXTURE_NETWORK_TIMEOUT_2);
        assert_eq!(result, ErrorKind::NetworkTimeout);
    }

    // ── Classification: CookieExpired ─────────────────────────

    #[test]
    fn test_classify_cookie_expired_1() {
        let result = classify(FIXTURE_COOKIE_EXPIRED_1);
        assert_eq!(result, ErrorKind::CookieExpired);
    }

    #[test]
    fn test_classify_cookie_expired_2() {
        // age-restricted variant
        let result = classify(FIXTURE_COOKIE_EXPIRED_2);
        assert_eq!(result, ErrorKind::CookieExpired);
    }

    // ── Classification: DiskFull ──────────────────────────────

    #[test]
    fn test_classify_disk_full_1() {
        let result = classify(FIXTURE_DISK_FULL_1);
        assert_eq!(result, ErrorKind::DiskFull);
    }

    #[test]
    fn test_classify_disk_full_2() {
        // quota variant
        let result = classify(FIXTURE_DISK_FULL_2);
        assert_eq!(result, ErrorKind::DiskFull);
    }

    // ── Classification: Unknown (fallback) ────────────────────

    #[test]
    fn test_classify_unknown_empty() {
        let result = classify("");
        assert_eq!(result, ErrorKind::Unknown("".to_string()));
    }

    #[test]
    fn test_classify_unknown_no_match() {
        let input = "Some random output\nwith no yt-dlp error patterns";
        let result = classify(input);
        assert_eq!(result, ErrorKind::Unknown(input.to_string()));
    }

    #[test]
    fn test_classify_unknown_pure_digits() {
        let input = "12345\n67890";
        let result = classify(input);
        assert_eq!(result, ErrorKind::Unknown(input.to_string()));
    }

    #[test]
    fn test_classify_unknown_special_chars() {
        let input = "!!@@##$$\n%%^^&&**";
        let result = classify(input);
        assert_eq!(result, ErrorKind::Unknown(input.to_string()));
    }

    // ── Classification: Priority & edge cases ─────────────────

    #[test]
    fn test_classify_first_match_wins() {
        // timeout on line 1 before 403 on line 2
        let input = "timeout error\nand also 403 forbidden";
        let result = classify(input);
        assert_eq!(result, ErrorKind::NetworkTimeout);
    }

    #[test]
    fn test_classify_case_insensitive() {
        let input = "Error: TIMEOUT occurred";
        let result = classify(input);
        assert_eq!(result, ErrorKind::NetworkTimeout);
    }

    #[test]
    fn test_classify_cookie_false_positive_avoided() {
        // Just mentioning cookies without expired/invalid → no trigger
        let input = "This video uses --cookies-from-browser format for extraction";
        let result = classify(input);
        assert_eq!(result, ErrorKind::Unknown(input.to_string()));
    }

    #[test]
    fn test_classify_format_not_available_not_video_unavailable() {
        // "not available" + "format" → skip VideoUnavailable
        let input = "ERROR: requested format not available";
        let result = classify(input);
        match result {
            ErrorKind::Unknown(_) => {} // expected
            ErrorKind::VideoUnavailable => {
                panic!("should NOT be VideoUnavailable when 'format' co-occurs")
            }
            other => panic!("expected Unknown, got {other:?}"),
        }
    }

    #[test]
    fn test_classify_disk_full_beats_timeout_on_compound_line() {
        // Root cause is disk space; the incidental "timeout" must not win.
        let input = "ERROR: timeout writing to disk: no space left on device";
        assert_eq!(classify(input), ErrorKind::DiskFull);
    }
}
