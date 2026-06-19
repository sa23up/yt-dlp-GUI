//! Playlist URL resolution. Single-task lifecycle lives in `queue.rs`.

use crate::ytdlp;
use serde::Serialize;
use std::time::Duration;

const PLAYLIST_TIMEOUT: Duration = Duration::from_secs(60);
/// Upper bound for one whole `resolve_queue` call. Without it, N playlist URLs
/// expand serially at up to 60s each — a crafted paste could stall for hours.
const RESOLVE_TOTAL_BUDGET: Duration = Duration::from_secs(180);

#[derive(Serialize, specta::Type)]
pub struct QueueEntry {
    pub url: String,
    pub title: String,
}

/// Resolve a list of URLs (including playlists) into individual QueueEntry items.
/// Playlist URLs (a `/playlist` page) are expanded via `yt-dlp --flat-playlist`.
/// A `watch?v=X&list=Y` URL is treated as the single video X (its task carries
/// `--no-playlist`), so pasting one video from a playlist doesn't pull the lot.
/// Returns deduplicated entries; non-http URLs are silently dropped (the frontend
/// filters them up-front so this is defense-in-depth).
#[tauri::command]
#[specta::specta]
pub async fn resolve_queue(
    urls: Vec<String>,
    net: ytdlp::args::NetworkOptions,
) -> Result<Vec<QueueEntry>, String> {
    let ytdlp_bin = crate::util::find_ytdlp_bin();
    // Cookie / proxy must apply to playlist expansion too — a private playlist
    // needs cookies, a region-locked one needs the proxy, exactly as the
    // download does. Built once and reused for every expansion below.
    let net_args = net.to_args()?;
    let mut entries: Vec<QueueEntry> = Vec::new();
    let mut seen = std::collections::HashSet::new();
    let deadline = std::time::Instant::now() + RESOLVE_TOTAL_BUDGET;

    for url in &urls {
        // Never resolve more than the queue can hold — a huge playlist would
        // otherwise build (and IPC-serialize) thousands of entries that enqueue
        // would just reject.
        if entries.len() >= crate::commands::queue::MAX_QUEUE_DEPTH {
            break;
        }
        let url = url.trim();
        if !crate::util::is_http_url(url) {
            continue;
        }
        if is_playlist_url(url) {
            // Spend at most the remaining total budget on this expansion; once
            // exhausted, fall through to single-URL treatment below.
            let remaining = deadline.saturating_duration_since(std::time::Instant::now());
            let timeout = PLAYLIST_TIMEOUT.min(remaining);
            let mut args = net_args.clone();
            args.extend([
                "--flat-playlist".into(),
                "--print".into(),
                "%(webpage_url)s|%(title)s".into(),
                "--no-warnings".into(),
                url.into(),
            ]);
            let mut expanded = false;
            if !timeout.is_zero() {
                if let Ok(child) = ytdlp::spawn_ytdlp(&ytdlp_bin, &args) {
                    if let Ok(Ok(out)) =
                        tokio::time::timeout(timeout, child.wait_with_output()).await
                    {
                        if out.status.success() {
                            for line in String::from_utf8_lossy(&out.stdout).lines() {
                                if entries.len() >= crate::commands::queue::MAX_QUEUE_DEPTH {
                                    break;
                                }
                                let trimmed = line.trim();
                                if trimmed.is_empty() {
                                    continue;
                                }
                                if let Some((u, title)) = trimmed.split_once('|') {
                                    let url_clean = u.trim().to_string();
                                    if crate::util::is_http_url(&url_clean)
                                        && seen.insert(url_clean.clone())
                                    {
                                        entries.push(QueueEntry {
                                            url: url_clean,
                                            title: title.trim().to_string(),
                                        });
                                    }
                                }
                            }
                            expanded = true;
                        }
                    }
                }
            }
            // Fall back to treating it as a single URL if the playlist expansion failed
            if !expanded && seen.insert(url.to_string()) {
                entries.push(QueueEntry {
                    url: url.to_string(),
                    title: url.to_string(),
                });
            }
        } else if seen.insert(url.to_string()) {
            entries.push(QueueEntry {
                url: url.to_string(),
                title: url.to_string(),
            });
        }
    }

    Ok(entries)
}

/// Whether a URL should be treated as a playlist page to expand. Matches
/// `/playlist` only in the path component (before `?`/`#`), so a `/playlist`
/// appearing in a query string or fragment doesn't trigger a spurious expansion.
fn is_playlist_url(url: &str) -> bool {
    let path = url.split_once(['?', '#']).map_or(url, |(before, _)| before);
    path.contains("/playlist")
}

#[cfg(test)]
mod tests {
    use super::is_playlist_url;

    #[test]
    fn playlist_path_matches() {
        assert!(is_playlist_url(
            "https://www.youtube.com/playlist?list=PL123"
        ));
        assert!(is_playlist_url("https://example.com/x/playlist"));
    }

    #[test]
    fn playlist_in_query_or_fragment_does_not_match() {
        assert!(!is_playlist_url("https://example.com/watch?next=/playlist"));
        assert!(!is_playlist_url("https://example.com/watch#/playlist"));
    }

    #[test]
    fn watch_url_is_not_a_playlist() {
        assert!(!is_playlist_url(
            "https://www.youtube.com/watch?v=abc&list=PL123"
        ));
    }
}
