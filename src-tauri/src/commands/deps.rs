use crate::deps;

#[tauri::command]
#[specta::specta]
pub async fn check_ytdlp_version_cmd() -> Result<String, String> {
    let bin = crate::util::find_ytdlp_bin();
    deps::check_ytdlp_version(&bin).await.map(|v| v.version)
}

#[tauri::command]
#[specta::specta]
pub async fn check_ffmpeg_version_cmd() -> Result<String, String> {
    deps::check_ffmpeg_version().await.map(|v| v.version)
}

#[tauri::command]
#[specta::specta]
pub async fn check_deno_version_cmd() -> Result<String, String> {
    deps::check_deno_version().await.map(|v| v.version)
}

#[tauri::command]
#[specta::specta]
pub async fn check_latest_release_cmd() -> Result<String, String> {
    deps::check_latest_ytdlp_release().await.map(|v| v.version)
}

#[tauri::command]
#[specta::specta]
pub async fn download_ytdlp_update_cmd(app: tauri::AppHandle) -> Result<(), String> {
    deps::download_ytdlp_update(app).await
}
