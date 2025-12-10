# 项目名称 / Project Name

[English](README.en.md) | [中文](README.md)

---

## 中文版

### 简介
这是一个基于 `yt-dlp` 的下载工具（图形界面/命令行），支持调用 `ffmpeg` 进行音视频合并和转码，可选启用 EJS 扩展以解析特定站点。

### 特性
- 下载在线视频/音频，支持合并轨道
- 使用 `ffmpeg` 静态版，无需额外依赖
- 可选 `yt_dlp_ejs` 扩展（EJS）
- 打包为单文件 `exe`，方便分发

### 环境要求
- Windows 10/11（x64）
- Python 3.8+（如果需要自行打包）
- `ffmpeg.exe`（建议下载静态版）；可选 `ffprobe.exe`
- （可选）`yt_dlp_ejs` 扩展：`pip install yt-dlp-ejs`

### 快速开始
1. 从 [Releases](https://github.com/sa23up/yt-dlp-GUI/releases) 下载已构建的 `yt_dlp_gui.exe`。
2. 将 `ffmpeg.exe` 放在同一目录（若需要 ffprobe 功能，可一并放置 `ffprobe.exe`）。
3. 直接运行 `yt_dlp_gui.exe`，按界面提示操作。

### 手动构建（PyInstaller）
1. 安装依赖：
   ```bash
   pip install -r requirements.txt
   # 如需 EJS，额外安装：
   pip install yt-dlp-ejs
   ```
2. 使用 PyInstaller 打包（示例）：
   ```bash
   pyinstaller -F -w main.py ^
     --name your_app ^
     --add-binary "ffmpeg.exe;." ^
     --hidden-import yt_dlp_ejs
   ```
   > 如不使用 EJS，可去掉 `--hidden-import yt_dlp_ejs`。也可在 `.spec` 中设置 `hiddenimports=['yt_dlp_ejs']`。
3. 产物位于 `dist/your_app.exe`。

### 确认打包无误
- 使用 `pyinstaller --clean --log-level=DEBUG ...` 清理缓存并查看缺失依赖提示。
- 将生成的 `exe` 复制到一个不含 Python/依赖的干净目录或测试机上运行。
- 覆盖主要功能（下载、合并、EJS 站点等）逐一验证，确保无 “No module named …”“找不到 ffmpeg” 等错误。

### 常见问题
- **缺少模块/No module named …**：检查是否安装对应库，并在打包时添加 `--hidden-import` 或在 `.spec` 的 `hiddenimports` 中声明。
- **找不到 ffmpeg**：确认 `ffmpeg.exe` 与程序在同一目录，或将其路径加入系统 PATH；建议使用静态版。
- **架构不匹配**：确保 Python/依赖/ffmpeg 与目标系统同为 x64 或 x86。
### 无法正常解析4K视频
需要下载nodejs  下载链接：https://nodejs.org/en/download/current

