[English](README.en.md) | [中文](README.md)

## English Documentation

### Overview
- **Name**: yt-dlp GUI (CustomTkinter)
- **Features**: GUI for downloading/parsing video/audio; batch combos (video×audio), cookie login, subtitle embed, EJS/JS runtime.
- **Highlights**:
  - Multi-select video/audio and auto-generate batch combinations.
  - Quick presets or single format; custom pick in the parse dialog.
  - Cookie file or browser cookies.
  - Optional EJS (yt-dlp-ejs) and JS Runtime (deno/node/bun/quickjs).
  - Subtitle embedding, MP3 extraction.
  - Bilingual UI (ZH/EN), font: Microsoft YaHei.

### Requirements
- Windows 10/11, Python 3.8+ recommended.
- Dependencies:
  - `yt-dlp`
  - `customtkinter`
  - (Optional) `yt-dlp-ejs` for advanced/EJS parsing.
- FFmpeg for merging/transcoding.
- (Optional) JS Runtime: deno / node.js / bun / QuickJS for some restricted or high-res (4K) videos.

### Install Dependencies
```bash
pip install -U yt-dlp customtkinter
# If you need EJS / advanced parsing:
pip install -U yt-dlp-ejs
```

### Install FFmpeg (Windows)
1. Go to the Windows builds page (gyan.dev is recommended):
   https://www.gyan.dev/ffmpeg/builds/
   Under “release builds”, download `ffmpeg-release-essentials.zip` (or .7z).
2. Extract and rename to a simple path, e.g., `C:\ffmpeg`. Make sure `C:\ffmpeg\bin` exists.
3. Add to PATH:
   - Press Win, search “Edit the system environment variables”, open → click “Environment Variables...”
   - In “System variables”, select `Path` → “Edit...” → “New” → add `C:\ffmpeg\bin`.
4. Verify:
   ```bash
   ffmpeg -version
   ```
   If it shows version info, it’s installed correctly.

### JS Runtime (optional but often needed for 4K/restricted videos)
- deno: https://deno.com/
- node.js: https://nodejs.org
- bun: https://bun.sh/
- QuickJS: https://bellard.org/quickjs/
Install any one and ensure it’s on your PATH. In the GUI you can select runtime=auto or specify a particular runtime + path.

### How to Run
```bash
python yt_dlp_gui.py
```
1) Enter video URL → click “Parse Formats”.
2) In the dialog:
   - “All formats” tab: pick a single format.
   - “Video/Audio” tabs: multi-select to build batch combos.
   - “Presets” tab: common format expressions (single choice).
3) Back to main window: set output folder, options (audio-only, embed subtitles) → “Start”.
4) Batch combos download one by one; progress/logs update in real time.

### Build to EXE (optional)
```bash
pip install -U pyinstaller
cd /d C:\Users\yt_dlp_gui
pyinstaller -F -w yt_dlp_gui.py
```
- Output: `dist/yt_dlp_gui.exe`
- Add icon: `--icon=your.ico`
- Add resources via `--add-data` if needed.

