use std::path::PathBuf;

use serde::{Deserialize, Serialize};

use crate::util::{atomic_write, data_dir};

fn settings_path() -> PathBuf {
    data_dir().join("settings.json")
}

/// Typed mirror of the frontend's settings store. `camelCase` to match
/// what the existing settings.json on disk already uses (frontend wrote it).
/// `#[serde(default)]` makes missing fields fall back to Default so the file
/// remains forward / backward compatible.
#[derive(Debug, Clone, Default, Serialize, Deserialize, specta::Type)]
#[serde(rename_all = "camelCase", default)]
pub struct AppSettings {
    pub theme: String,
    pub language: String,
    pub download_dir: String,
    pub filename_template: String,
    pub concurrency: u32,
    pub cookie_source: String,
    pub cookie_file_path: String,
    pub proxy: String,
    pub rate_limit: String,
    pub preferred_codec: String,
    pub max_height: u32,
}

#[tauri::command]
#[specta::specta]
pub fn load_settings() -> Result<AppSettings, String> {
    let path = settings_path();
    if !path.exists() {
        return Ok(AppSettings::default());
    }
    let raw = std::fs::read_to_string(&path).map_err(|e| format!("读取设置失败: {e}"))?;
    serde_json::from_str(&raw).map_err(|e| format!("解析设置失败: {e}"))
}

#[tauri::command]
#[specta::specta]
pub fn save_settings(settings: AppSettings) -> Result<(), String> {
    let raw =
        serde_json::to_string_pretty(&settings).map_err(|e| format!("序列化设置失败: {e}"))?;
    atomic_write(&settings_path(), &raw)
}
