use std::path::PathBuf;

#[derive(Debug, Clone)]
pub struct DownloadOptions {
    pub video_format_id: Option<String>,
    pub audio_format_id: Option<String>,
    pub output_dir: PathBuf,
    pub filename_template: String,
    pub cookie_source: CookieSource,
    pub cookie_file_path: Option<PathBuf>,
    pub proxy: Option<String>,
    pub rate_limit: Option<String>,
    /// Max video height for Best-Quality / batch downloads (0 = unlimited).
    pub max_height: u32,
    /// Preferred video codec ("any" | "h264" | "vp9" | "av1") for Best-Quality.
    pub preferred_codec: String,
}

#[derive(Debug, Clone)]
pub enum CookieSource {
    None,
    Firefox,
    Chrome,
    Edge,
    File,
}

/// Map a frontend cookie-source string to the enum. Unknown values fall back to
/// `None` so a malformed setting never silently enables a browser's cookies.
pub fn parse_cookie_source(s: &str) -> CookieSource {
    match s {
        "firefox" => CookieSource::Firefox,
        "chrome" => CookieSource::Chrome,
        "edge" => CookieSource::Edge,
        "file" => CookieSource::File,
        _ => CookieSource::None,
    }
}

/// Cookie + proxy options shared by every yt-dlp invocation that talks to the
/// network: download, `fetch_formats` and `resolve_queue`. Without threading
/// these into format-fetch / playlist-expansion, cookie-gated (YouTube bot
/// check) or proxy-gated (region lock) content fails to even list formats while
/// the actual download would have succeeded.
#[derive(Debug, Clone, Default, serde::Deserialize, specta::Type)]
#[serde(rename_all = "camelCase", default)]
pub struct NetworkOptions {
    pub cookie_source: String,
    pub cookie_file_path: String,
    pub proxy: String,
}

impl NetworkOptions {
    /// Build the cookie + proxy yt-dlp args. Fails on an invalid proxy rather
    /// than silently dropping it (same contract as `build_download_args`).
    pub fn to_args(&self) -> Result<Vec<String>, String> {
        let cookie_path = if self.cookie_file_path.is_empty() {
            None
        } else {
            Some(PathBuf::from(&self.cookie_file_path))
        };
        let proxy = if self.proxy.is_empty() {
            None
        } else {
            Some(self.proxy.as_str())
        };
        build_network_args(
            &parse_cookie_source(&self.cookie_source),
            cookie_path.as_deref(),
            proxy,
        )
    }
}

/// Build the cookie + proxy args (no rate limit — that only applies to an actual
/// download). Shared by `build_download_args` and the metadata/playlist commands.
pub fn build_network_args(
    cookie_source: &CookieSource,
    cookie_file_path: Option<&std::path::Path>,
    proxy: Option<&str>,
) -> Result<Vec<String>, String> {
    let mut args = Vec::new();
    match cookie_source {
        CookieSource::None => {}
        CookieSource::Firefox => {
            args.push("--cookies-from-browser".into());
            args.push("firefox".into());
        }
        CookieSource::Chrome => {
            args.push("--cookies-from-browser".into());
            args.push("chrome".into());
        }
        CookieSource::Edge => {
            args.push("--cookies-from-browser".into());
            args.push("edge".into());
        }
        CookieSource::File => {
            if let Some(path) = cookie_file_path {
                args.push("--cookies".into());
                args.push(path.to_string_lossy().to_string());
            }
        }
    }
    if let Some(proxy) = proxy {
        if !proxy.is_empty() {
            validate_proxy(proxy)?;
            args.push("--proxy".into());
            args.push(proxy.to_string());
        }
    }
    Ok(args)
}

/// Validate a `--proxy` value: known scheme prefix, no whitespace/control chars.
/// A leading `-` is impossible once the scheme is enforced, so flag injection
/// is excluded by construction.
pub fn validate_proxy(proxy: &str) -> Result<(), String> {
    const SCHEMES: [&str; 6] = [
        "http://",
        "https://",
        "socks4://",
        "socks4a://",
        "socks5://",
        "socks5h://",
    ];
    let lower = proxy.to_lowercase();
    let scheme_ok = SCHEMES
        .iter()
        .any(|s| lower.starts_with(s) && proxy.len() > s.len());
    if !scheme_ok || proxy.chars().any(|c| c.is_whitespace() || c.is_control()) {
        return Err(
            "代理格式无效（应为 http(s):// 或 socks5://host:port）/ invalid proxy (expected http(s):// or socks5://host:port)"
                .into(),
        );
    }
    Ok(())
}

/// Validate a `-r` rate limit: digits with at most one decimal point, optional
/// K/M/G suffix (e.g. "500K", "1.5M").
pub fn validate_rate_limit(limit: &str) -> Result<(), String> {
    let body = limit
        .strip_suffix(['K', 'k', 'M', 'm', 'G', 'g'])
        .unwrap_or(limit);
    let ok = body.chars().any(|c| c.is_ascii_digit())
        && body.chars().all(|c| c.is_ascii_digit() || c == '.')
        && body.matches('.').count() <= 1;
    if !ok {
        return Err(
            "限速格式无效（数字 + 可选 K/M/G 后缀，如 1M）/ invalid rate limit (number with optional K/M/G suffix, e.g. 1M)"
                .into(),
        );
    }
    Ok(())
}

/// Build download arguments as a flat Vec<String> (no binary path, no URL).
/// The caller appends the URL last so all flags are parsed first.
/// Fails on an invalid proxy / rate limit — silently dropping either would
/// e.g. download over a direct connection the user believes is proxied.
pub fn build_download_args(opts: &DownloadOptions) -> Result<Vec<String>, String> {
    use super::parse::{build_format_selector, codec_sort};

    let format_selector = build_format_selector(
        opts.video_format_id.as_deref(),
        opts.audio_format_id.as_deref(),
        opts.max_height,
    );
    let output_path = opts.output_dir.join(&opts.filename_template);

    let mut args = vec![
        "-f".into(),
        format_selector,
        "-o".into(),
        output_path.to_string_lossy().to_string(),
        // Restrict filenames to ASCII alphanumeric + safe chars to prevent
        // path traversal via malicious video titles (e.g., "../../etc/passwd")
        "--restrict-filenames".into(),
    ];

    // Codec preference only applies to Best Quality (no hand-picked video
    // format). `-S` *sorts* so it prefers the codec but still succeeds when
    // it's unavailable, rather than hard-failing like a `[vcodec=...]` filter.
    if opts.video_format_id.is_none() && opts.audio_format_id.is_none() {
        if let Some(sort) = codec_sort(&opts.preferred_codec) {
            args.push("-S".into());
            args.push(sort);
        }
    }

    args.extend(build_network_args(
        &opts.cookie_source,
        opts.cookie_file_path.as_deref(),
        opts.proxy.as_deref(),
    )?);

    if let Some(ref limit) = opts.rate_limit {
        if !limit.is_empty() {
            validate_rate_limit(limit)?;
            args.push("-r".into());
            args.push(limit.clone());
        }
    }

    Ok(args)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn proxy_valid_schemes_accepted() {
        assert!(validate_proxy("http://127.0.0.1:7890").is_ok());
        assert!(validate_proxy("socks5://localhost:1080").is_ok());
        assert!(validate_proxy("SOCKS5H://host:1080").is_ok());
    }

    #[test]
    fn proxy_injection_rejected() {
        assert!(validate_proxy("--exec=rm -rf /").is_err());
        assert!(validate_proxy("-x").is_err());
        assert!(validate_proxy("http://h\nost:1").is_err());
        assert!(validate_proxy("ftp://host:1").is_err());
        assert!(validate_proxy("http://").is_err());
    }

    #[test]
    fn rate_limit_valid_accepted() {
        assert!(validate_rate_limit("500K").is_ok());
        assert!(validate_rate_limit("1.5M").is_ok());
        assert!(validate_rate_limit("42").is_ok());
    }

    #[test]
    fn rate_limit_injection_rejected() {
        assert!(validate_rate_limit("-r").is_err());
        assert!(validate_rate_limit("1M\n--exec").is_err());
        assert!(validate_rate_limit(".").is_err());
        assert!(validate_rate_limit("1.2.3M").is_err());
    }

    #[test]
    fn invalid_proxy_fails_build_instead_of_silent_drop() {
        let opts = DownloadOptions {
            video_format_id: None,
            audio_format_id: None,
            output_dir: PathBuf::from("/tmp"),
            filename_template: "%(title)s.%(ext)s".into(),
            cookie_source: CookieSource::None,
            cookie_file_path: None,
            proxy: Some("--bad-flag".into()),
            rate_limit: None,
            max_height: 0,
            preferred_codec: "any".into(),
        };
        assert!(build_download_args(&opts).is_err());
    }
}
