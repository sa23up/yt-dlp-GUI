## English Version
### Overview
This is a `yt-dlp`-based downloader (GUI/CLI) that leverages `ffmpeg` for muxing/transcoding and optionally uses the `yt_dlp_ejs` extension to handle specific sites.

### Features
- Download online video/audio, merge tracks with ffmpeg
- Uses static `ffmpeg`, no extra DLLs required
- Optional `yt_dlp_ejs` (EJS) support
- Packaged as a single `exe` for easy distribution

### Requirements
- Windows 10/11 (x64)
- Python 3.8+ (if you build it yourself)
- `ffmpeg.exe` (static build recommended); optional `ffprobe.exe`
- (Optional) `yt_dlp_ejs` extension: `pip install yt-dlp-ejs`

### Quick Start
1. Download the prebuilt `yt_dlp_gui.exe` from [Releases](./releases).
2. Place `ffmpeg.exe` in the same directory (and `ffprobe.exe` if needed).
3. Run `yt_dlp_gui.exe` and follow the prompts/UI.

### Build with PyInstaller
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   # If you need EJS support:
   pip install yt-dlp-ejs
   ```
2. Package with PyInstaller (example):
   ```bash
   pyinstaller -F -w main.py ^
     --name your_app ^
     --add-binary "ffmpeg.exe;." ^
     --hidden-import yt_dlp_ejs
   ```
   > If you don’t use EJS, omit `--hidden-import yt_dlp_ejs`. You can also set `hiddenimports=['yt_dlp_ejs']` in the `.spec` file.
3. The built executable will be in `dist/your_app.exe`.

### Validate the Build
- Use `pyinstaller --clean --log-level=DEBUG ...` to clear cache and inspect missing dependency warnings.
- Copy the generated `exe` to a clean directory or test machine without Python/your libs and run it.
- Exercise key features (download, merge, EJS sites, etc.) to ensure there are no “No module named …” or “ffmpeg not found” errors.

### FAQ
- **Missing module / No module named …**: Ensure the library is installed and declared via `--hidden-import` or `hiddenimports` in the `.spec`.
- **ffmpeg not found**: Ensure `ffmpeg.exe` is in the same directory as the app or on the PATH; static builds are recommended.
- **Architecture mismatch**: Make sure Python/deps/ffmpeg match the target system architecture (x64 vs x86).

