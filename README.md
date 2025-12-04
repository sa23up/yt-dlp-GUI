# yt-dlp 图形界面使用说明书
中文 | [English](./USER_GUIDE.en.md)

本说明书适用于你的 yt-dlp 图形界面（yt_dlp_gui.py）。它支持解析视频/音频格式、可视化选择（含多选批量组合）、下载视频与音频、Cookie 登录、字幕嵌入，以及通过 EJS（External JS Scripts）+ JS Runtime（Deno/Node/Bun/QuickJS）解析 YouTube 的 4K/AV1/VP9/HDR 等高阶格式。

---

## 目录
- 背景与功能概览
- 系统要求
- 安装与环境准备
  - Python 与依赖
  - FFmpeg
  - EJS 与 JS Runtime（4K/高阶格式）
- 快速开始
- 界面与功能说明
  - 基本设置
  - 高级设置（Cookie / EJS / Runtime）
  - 解析格式对话框（支持多选批量）
- 下载模式
  - 单格式下载
  - 多选批量下载（视频×音频交叉组合）
- 自定义格式表达式示例
- 常见问题与故障排查（FAQ）
- 安全与合规
- 附：Windows 打包为可执行文件

---

## 背景与功能概览
- 粘贴视频 URL，解析所有可用格式（含分离视频/音频）。
- 下载：
  - 单格式（最佳、1080p、仅音频、自定义表达式）
  - 多选批量（视频×音频交叉组合）
- 其他能力：
  - 仅音频提取（MP3）
  - 字幕嵌入
  - Cookie（文件或浏览器读取）
  - EJS + JS Runtime 解锁 YouTube 4K/AV1/VP9/HDR
- 实时进度与日志。

---

## 系统要求
- 操作系统：Windows 10/11、macOS、Linux
- Python 3.8+
- 网络：可访问目标站点；若用远程 EJS，需可访问 GitHub Releases

---

## 安装与环境准备

### 1) Python 与 yt-dlp
安装 Python（添加到 PATH），然后：
```bash
pip install -U yt-dlp
```
推荐（支持 4K）：
```bash
pip install -U yt-dlp yt-dlp-ejs
```
运行 GUI（将文件保存为 `yt_dlp_gui.py`）：
```bash
python yt_dlp_gui.py
```

### 2) 安装 FFmpeg（用于合并分离流、提取音频、字幕）
- Windows：
```bash
winget install ffmpeg
```
- macOS：
```bash
brew install ffmpeg
```
- Linux：用发行版包管理器安装（如 `apt install ffmpeg`）。

未安装 FFmpeg 时，无法自动将分离的音视频流合并为单一文件。

### 3) 启用 EJS 与 JS Runtime（获取 4K/高阶格式）
YouTube 的 4K/2K/AV1/VP9/HDR 等常需 EJS 脚本解码保护参数。

方案 A（推荐）：
```bash
pip install -U yt-dlp-ejs
# 选择一个 JS Runtime（推荐 Deno）
# Windows:
winget install Deno.Deno
# macOS:
brew install deno
# 或安装 Node.js / Bun / QuickJS
```

方案 B：
- 若未安装 `yt-dlp-ejs`，GUI 会在启用 EJS 时自动允许远程（ejs:github）获取脚本。
- 仍需安装 JS Runtime。

在“高级设置（Cookie / EJS / Runtime）”中勾选启用，并选择/填写 Runtime。

---

## 快速开始
1. 运行 `yt_dlp_gui.py`
2. 在“基本设置”粘贴视频 URL
3. 点击“解析格式”
4. 弹窗中：
   - 可单选“完整格式”或“推荐组合”，或
   - 在“视频格式”与“音频格式”中按 Ctrl/Shift 多选，生成批量交叉组合
5. 返回主界面，点击“开始下载”

如需 4K/高阶：
- 勾选“启用高级格式 (EJS)”
- 安装 Deno 或 Node（推荐 Deno）
- 推荐安装 `yt-dlp-ejs`

---

## 界面与功能说明

### 基本设置
- 视频 URL：支持 YouTube、Bilibili 等
- 输出目录：选择保存位置
- 格式选择（单组表达式）：
  - 快速选择（最佳、1080p、仅音频等）
  - 自定义格式表达式（见示例）
- 其他：
  - 仅提取音频（MP3）
  - 嵌入字幕（需 FFmpeg）

### 高级设置（Cookie / EJS / Runtime）
- Cookie 文件（cookies.txt）或从浏览器读取（Chrome/Firefox/Edge/Safari/Opera/Brave）
- 启用高级格式 (EJS)
- JS Runtime：auto/deno/node/bun/quickjs，可选路径

### 解析格式对话框（多选与批量）
标签页：
- 所有格式：完整/仅视频/仅音频的总览（单击单选）
- 视频格式（仅视频，支持多选 Ctrl/Shift）
- 音频格式（仅音频，支持多选）
- 推荐组合（单选）
- 组合预览：展示已选视频与音频及其交叉组合（支持手动刷新）

按钮：
- 生成组合并确定：返回批量（视频×音频）。若只选视频或只选音频，则返回该类列表并逐个下载。
- 仅当前单选确定：返回单格式/预设的表达式
- 清空 / 取消

提示：若组合预览不显示，确认已多选（行高亮），切到“组合预览”页或点“手动刷新”。

---

## 下载模式

### 单格式下载
- 在弹窗选择“完整格式”或“推荐组合”，或在主界面填写“自定义格式表达式”。
- 点击“开始下载”。

### 多选批量下载（视频×音频）
- 在弹窗“视频格式”多选 N 个视频流，“音频格式”多选 M 个音频流。
- 点击“生成组合并确定”，返回主界面“开始下载”后顺序下载 N×M 个组合。

注意：
- 批量为顺序执行；大量组合耗时较长。
- 合并分离流需 FFmpeg。

---

## 自定义格式表达式示例
```text
# 最佳视频+音频，若无分离则回退完整格式
bestvideo+bestaudio/best

# 分辨率限制
bestvideo[height<=2160]+bestaudio   # 4K
bestvideo[height<=1440]+bestaudio   # 2K
bestvideo[height<=1080]+bestaudio   # 1080p

# 优先 MP4
bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]

# 指定编码
bestvideo[vcodec^=av01]+bestaudio   # AV1
bestvideo[vcodec^=vp9]+bestaudio    # VP9
bestvideo[vcodec^=avc]+bestaudio    # H.264/AVC

# 精确格式ID组合
137+140   # 137: 1080p 视频，140: m4a 音频
```

---

## 常见问题与故障排查（FAQ）
- 看不到 4K/2K/AV1/VP9？
  - 启用 EJS，安装 `yt-dlp-ejs` + JS Runtime（Deno 推荐），或允许远程脚本（已自动）。
  - 确保可访问 GitHub Releases。

- 下载后未合并为一个文件？
  - 安装 FFmpeg。

- 登录/会员视频失败？
  - 使用 Cookie（文件或浏览器）。
  - 会员内容需有效订阅。

- 出现 signature/n/challenge 相关错误？
  - EJS/Runtime 未就绪。安装 `yt-dlp-ejs` 与 Deno/Node，检查日志。

- 组合预览不显示？
  - 确认确实多选（Ctrl/Shift）。切换到“组合预览”或点“手动刷新”。

- 取消无效？
  - 软取消，当前片段完成后停止。需强制中断可关闭程序。

---

## 安全与合规
- 请遵守目标网站条款与当地法律。
- Cookie 文件包含登录态，务必私密保管。
- 工具仅用于合法用途。

---

## 附：Windows 打包为 EXE
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name="yt-dlp视频下载器" yt_dlp_gui.py
```
EXE 在 `dist` 目录中。用户仍需安装 FFmpeg（以及 4K 所需的 JS Runtime）。

---


# 12/4 新增内容


本次更新围绕“更易用、更美观、更强大”三个方向进行了增强，尤其适配无 Python/无 FFmpeg 用户的分发场景。以下为新增功能与改进亮点汇总。

## 亮点概览
- 一键打包 EXE（含 ffmpeg/ffprobe）：用户直接运行，无需安装 Python/FFmpeg
- 主题美化：默认亮色 Sun Valley 主题（sv-ttk），缺失主题包时自动优雅降级
- 中英双语界面：支持运行时中英文切换（简体中文/English）
- 多选批量下载：视频×音频交叉组合批量下载（自动生成组合）
- 组合预览增强：即时显示已选视频/音频ID与组合预览，并支持手动刷新
- EJS/JS Runtime 支持：兼容解析 YouTube 4K/AV1/VP9/HDR 高阶格式（可选）
- 环境检测与日志优化：更直观的状态提示与彩色日志标签
- 构建脚本与打包流程文档完善：使用 PowerShell 一键构建，Spec 与 Hook 自动生成

---

## 新增与改进详情

### 1) 一键打包 EXE（含 ffmpeg/ffprobe）
- 新增 PyInstaller Spec（yt_dlp_gui_ffmpeg.spec）与运行时钩子（hook_path_ffmpeg.py）。
- 支持将 ffmpeg.exe 与 ffprobe.exe打包在 EXE 内部，运行时自动加入 PATH。
- 构建脚本 build.ps1 一键生成/检查/打包，首次构建可加 -Clean 清理旧产物。
- 构建产物位于 dist/yt-dlp-gui/yt-dlp-gui.exe，用户无需安装 Python 或 FFmpeg。

实用场景：
- 面向终端用户分发，开箱即用。
- 在严格受限环境（无管理员权限、不便安装第三方软件）下部署更便捷。

### 2) 主题美化（默认亮色）
- 采用 Sun Valley 主题（sv-ttk），统一控件风格、字体与间距。
- 若目标机无主题包，内置亮色方案自动降级，保证稳定性与外观一致性。

### 3) 中英双语界面
- 所有界面元素、日志、提示文本均提供简体中文与英文版本。
- 顶部语言选择下拉框支持运行时切换，无需重启。

### 4) 多选批量下载（视频×音频）
- 在“解析格式”弹窗的“视频格式（仅视频）”与“音频格式（仅音频）”页可多选。
- 自动生成所有交叉组合（N 个视频 × M 个音频 → N×M 组合）。
- 若只选视频或只选音频，则逐个单类下载。

适用场景：
- 同时需要多套编码/容器组合的素材。
- 批量处理不同码率或不同容器的导出需求。

### 5) 组合预览增强
- 新增“组合预览”标签页：展示已选视频、音频及交叉组合（部分预览）。
- 支持手动刷新；在切换到该标签页时自动刷新。
- 选择提示条实时更新，给出组合数量、单类下载提示等。

### 6) EJS 与 JS Runtime（可选）
- 勾选“启用高级格式 (EJS)”后，可解析 YouTube 的 4K/2K/AV1/VP9/HDR 等高阶分离流。
- 推荐安装 Deno 或 Node；未安装 yt-dlp-ejs 时自动允许远程组件（ejs:github）。
- 日志会显示 EJS 与 Runtime 状态与提示。

### 7) 环境检测与日志优化
- 启动时检测 FFmpeg、yt-dlp-ejs、sv-ttk 并在日志中给出结果与建议。
- 统一彩色日志标签（info/success/warning/error/batch/ejs/runtime），提升可读性。
- 下载状态条显示速度与预估剩余时间（ETA）。

### 8) 构建脚本与流程文档完善
- build.ps1 自动生成缺失的 Spec/Hook 文件，避免编码/引号错误。
- 提供逐步操作说明与常见问题排查建议（执行策略、路径、主题包、证书等）。

---

## 兼容性与注意事项
- Windows 10/11，Python 3.8+（构建机）；用户侧无需 Python。
- 打包 EXE包含 ffmpeg/ffprobe，用户无需再安装 FFmpeg。
- 启用 EJS 并解析高阶格式时，用户仍需安装 JS Runtime（Deno/Node/Bun/QuickJS），或使用远程组件。
- 如需图标，编辑 Spec 文件的 icon 路径并重新打包。

---

## 快速体验（用户侧）
1. 双击运行 yt-dlp-gui.exe
2. 粘贴视频 URL → 解析格式
3. 多选视频与音频 → 生成组合并确定 → 开始下载
4. 如需 4K/AV1/VP9/HDR：在高级设置启用 EJS，安装 Deno/Node

---

## 反馈与迭代
如需进一步功能（并行下载、断点续传、自动跳过已存在文件、限速与重试策略、更多语言等），欢迎反馈，我将持续改进。
