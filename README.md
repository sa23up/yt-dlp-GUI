# 项目名称 / Project Name

[English](README.en.md) | [中文](README.md)

---

## 中文文档

### 项目简介
- **名称**：yt-dlp GUI（CustomTkinter）
- **功能**：图形化下载与解析视频/音频，支持多格式批量组合下载、Cookie 登录、字幕嵌入、EJS/JS Runtime。
- **特点**：
  - 多选视频/音频，自动生成批量组合（视频×音频笛卡尔积）。
  - 单格式/预设快速下载，或在解析弹窗中自定义选择。
  - Cookie 文件或浏览器 Cookie 自动读取。
  - 可启用 EJS（yt-dlp-ejs），并指定 JS Runtime（deno/node/bun/quickjs）。
  - 支持嵌入字幕、提取 MP3。
  - 中文/英文界面切换，界面字体使用“微软雅黑”。

### 运行环境
- Windows 10/11，Python 3.8+（建议）。
- 依赖：
  - `yt-dlp`
  - `customtkinter`
  - （可选）`yt-dlp-ejs` 用于 EJS/高级解析。
- FFmpeg（用于合并音视频/转码）。
- （可选）JS Runtime：deno / node.js / bun / QuickJS，用于解析某些高分辨率或受限视频（如 4K）。

### 安装依赖
```bash
pip install -U yt-dlp customtkinter
# 若使用 EJS/高级解析：
pip install -U yt-dlp-ejs
```

### 安装 FFmpeg（Windows）
1. 访问 FFmpeg 的 Windows 构建发布页（推荐 gyan.dev）：
   https://www.gyan.dev/ffmpeg/builds/
   找到 “release builds”，下载 `ffmpeg-release-essentials.zip`（或 .7z）。
2. 解压后，将文件夹重命名为简单路径，例如 `C:\ffmpeg`。确认其中包含 `C:\ffmpeg\bin`。
3. 配置环境变量：
   - Win 键搜索“编辑系统环境变量”，打开 → 点击右下角“环境变量(N)...”
   - 在“系统变量(S)”中找到 `Path` → “编辑(I)...” → “新建(N)”。
   - 填入 `C:\ffmpeg\bin`，保存。
4. 验证：打开命令提示符，运行
   ```bash
   ffmpeg -version
   ```
   若显示版本信息，则安装成功。

### JS Runtime（可选，但解析 4K/受限视频常用）
- deno: https://deno.com/
- node.js: https://nodejs.org
- bun: https://bun.sh/
- QuickJS: https://bellard.org/quickjs/
安装任一后确保其在系统 PATH 中。程序中可选择 runtime=auto 或指定具体 runtime + path。

### 使用方式
1. 运行脚本：
   ```bash
   python yt_dlp_gui.py
   ```
2. 输入视频 URL → 点击“解析格式”。在弹窗中：
   - 单击 “所有格式” 可选单格式。
   - “视频格式”/“音频格式”标签支持多选，自动生成批量组合。
   - “预设”标签可选择常用格式表达式（单选）。
3. 确定后返回主界面，选择输出目录，勾选提取音频/嵌入字幕等选项 → “开始下载”。
4. 批量组合会依次下载；进度条/日志会实时更新。

### 打包为 exe（可选）
```bash
pip install -U pyinstaller
cd /d C:\Users\del\Desktop\packexe
pyinstaller -F -w yt_dlp_gui.py
```
- 生成文件：`dist/yt_dlp_gui.exe`
- 如需图标：加 `--icon=your.ico`
- 有额外资源时用 `--add-data`。


