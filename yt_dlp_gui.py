#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
yt-dlp GUI (Light Theme • Bilingual: 简体中文 / English)
- Preferred theme: sv-ttk (Sun Valley ttk theme) from rdbende/Sun-Valley-ttk-theme
  Install: pip install sv-ttk
- Light theme by default. Falls back to a custom light palette if sv-ttk is not installed
- Bilingual UI: Simplified Chinese and English, runtime toggle
- EJS + JS runtime support for YouTube 4K/AV1/VP9/HDR
- Cookies (file + from browser)
- Parse formats with multi-select, batch combinations
- Single-format and batch downloads
- Subtitles embedding, audio-only extraction
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import threading
import os
import sys
import shutil
import datetime
from pathlib import Path
from itertools import product

# --- Dependencies: yt-dlp ---
try:
    from yt_dlp import YoutubeDL
except ImportError:
    print("Error: yt-dlp not installed. Run: pip install -U yt-dlp")
    sys.exit(1)

# --- Optional: yt_dlp_ejs ---
try:
    import yt_dlp_ejs  # noqa: F401
    HAVE_EJS = True
except Exception:
    HAVE_EJS = False

# --- Preferred theme: sv-ttk (Sun Valley) ---
HAS_SVTTK = False
try:
    # PyPI name: sv-ttk
    # Repo: https://github.com/rdbende/Sun-Valley-ttk-theme
    import sv_ttk
    HAS_SVTTK = True
except Exception:
    HAS_SVTTK = False


# ========================= Fallback light palette for ttk ========================= #
def setup_fallback_light_theme(root):
    style = ttk.Style(root)
    # try a stable base theme
    for t in ('clam', 'alt', 'default'):
        try:
            style.theme_use(t)
            break
        except Exception:
            continue

    # colors (light)
    bg = '#f5f6f8'
    surface = '#ffffff'
    border = '#d9dde3'
    fg = '#1f2937'
    fg_muted = '#6b7280'
    accent = '#2563eb'
    success = '#2e7d32'
    warning = '#ed6c02'
    error = '#d32f2f'
    info = '#1e88e5'

    root.configure(background=bg)

    # Frames
    style.configure('TFrame', background=bg)
    style.configure('Card.TLabelframe', background=surface, foreground=fg, bordercolor=border, relief='solid')
    style.configure('Card.TLabelframe.Label', background=surface, foreground=fg, font=('Segoe UI', 10, 'bold'))

    # Labels
    style.configure('TLabel', background=surface, foreground=fg)
    style.configure('Muted.TLabel', background=surface, foreground=fg_muted)

    # Entry
    style.configure('TEntry', padding=6, fieldbackground=surface, foreground=fg, bordercolor=border, relief='solid')
    style.map('TEntry', bordercolor=[('focus', accent)])

    # Combobox
    style.configure('TCombobox', padding=6, fieldbackground=surface, foreground=fg, bordercolor=border, relief='solid')
    style.map('TCombobox', bordercolor=[('focus', accent)])

    # Button
    style.configure('Accent.TButton', padding=(12, 8), background=accent, foreground='#fff', font=('Segoe UI', 10, 'bold'))
    style.map('Accent.TButton', background=[('active', '#1d4ed8')])
    style.configure('TButton', padding=(12, 8), font=('Segoe UI', 10))

    # Checkbutton
    style.configure('TCheckbutton', background=surface, foreground=fg)

    # Notebook
    style.configure('TNotebook', background=bg, tabmargins=(8, 4, 8, 0))
    style.configure('TNotebook.Tab', font=('Segoe UI', 10), padding=(12, 8))
    style.map('TNotebook.Tab', foreground=[('selected', fg)], background=[('selected', surface)])

    # Treeview
    style.configure('Treeview', background=surface, fieldbackground=surface, foreground=fg, bordercolor=border)
    style.configure('Treeview.Heading', font=('Segoe UI Semibold', 10), foreground=fg)
    style.map('Treeview', background=[('selected', '#dbeafe')], foreground=[('selected', '#0f172a')])

    # Progressbar
    style.configure('TProgressbar', troughcolor=surface, bordercolor=border, background=accent)

    # convenience color palette for logs/status
    return dict(
        bg=bg, surface=surface, border=border, fg=fg, fg_muted=fg_muted,
        accent=accent, success=success, warning=warning, error=error, info=info
    )


# ========================= Bilingual strings ========================= #
LANG = {
    'zh': {
        # App
        'app_title': "yt-dlp 图形界面（亮色主题 • EJS • 批量）",
        'banner_title': "yt-dlp 可视化下载器",
        'banner_sub': "亮色 • EJS • 批量 • Cookie • 字幕",
        'language': "语言",
        'lang_zh': "中文",
        'lang_en': "English",

        # Tabs
        'tab_basic': "基本设置",
        'tab_adv': "高级（Cookies • EJS • Runtime）",

        # Groups & Labels
        'group_url': "视频 URL",
        'label_url': "URL：",
        'btn_parse': "🔍 解析格式",

        'group_out': "输出目录",
        'btn_browse': "浏览...",

        'group_fmt': "单格式选择（表达式）",
        'label_quick': "快速选择：",
        'fmt_best': "bestvideo+bestaudio/best - 最佳质量（推荐）",
        'fmt_best_complete': "best - 最佳完整格式",
        'fmt_best_audio': "bestaudio/best - 仅音频（最佳）",
        'fmt_1080p': "bestvideo[height<=1080]+bestaudio/best - 1080p",
        'fmt_720p': "bestvideo[height<=720]+bestaudio/best - 720p",
        'fmt_custom': "custom - 自定义（弹窗选择/手写表达式）",

        'label_custom': "自定义格式表达式：",
        'tip_batch': "提示：如需批量组合，请在“解析格式”弹窗中多选视频与音频；此处仅用于单次下载。",

        'group_opts': "其他选项",
        'chk_extract_audio': "仅提取音频（MP3）",
        'chk_embed_subs': "嵌入字幕",

        'group_cookie': "Cookies",
        'label_cookie_file': "Cookie 文件：",
        'btn_select': "选择...",
        'btn_clear': "清除",
        'cookie_none': "未设置 Cookie",
        'cookie_set': "✓ 已设置 Cookie",

        'group_browser_cookie': "浏览器 Cookie（自动）",
        'label_browser': "浏览器：",
        'browser_note': "需在所选浏览器中已登录目标站点。",

        'group_ejs': "高级格式（EJS）与 JS Runtime",
        'chk_enable_ejs': "启用高级格式 (EJS)",
        'label_runtime': "Runtime：",
        'label_runtime_path': "Runtime 路径（可选）：",
        'ejs_tip': "建议安装 yt-dlp-ejs + Deno（或 Node/Bun/QuickJS），以解析 YouTube 的 4K/AV1/VP9/HDR。",

        'btn_start': "开始下载",
        'btn_cancel': "取消",
        'btn_clear_logs': "清除日志",

        'group_progress': "下载进度",
        'status_ready': "就绪",
        'group_logs': "日志",

        # Parse/log/status texts
        'warn_enter_url': "请输入视频 URL。",
        'status_parsing': "正在解析格式...",
        'log_parsing': "开始解析：{url}",
        'err_no_info': "无法获取视频信息。",
        'log_title': "标题：{title}",
        'log_fmt_count': "格式数量：{count}",
        'err_no_formats': "未解析到格式。可能需要登录或启用 EJS/Runtime。",
        'log_no_high': "未发现 1440p+ 高阶格式，可能 EJS/Runtime 未生效。",
        'status_ready_ok': "就绪",

        'log_ffmpeg_missing': "未检测到 FFmpeg：分离流合并/音频提取可能失败。请安装 ffmpeg。",
        'log_ffmpeg_detected': "已检测到 FFmpeg：{path}",
        'log_ejs_present': "检测到 yt-dlp-ejs：将使用本地 EJS 脚本。",
        'log_ejs_absent': "未检测到 yt-dlp-ejs：启用 EJS 时将使用远程脚本 (ejs:github)。",
        'log_svttk_absent': "未检测到 sv-ttk，使用内置亮色主题。安装：pip install sv-ttk",

        'status_single_start': "开始单格式下载...",
        'status_batch_start': "开始批量下载...",
        'log_single_fmt': "单格式下载：{fmt}",
        'log_batch_start': "批量开始：共 {n} 个格式组合",
        'status_done': "完成",
        'status_failed': "失败",
        'status_cancelling': "正在取消...",
        'log_cancel_req': "已请求取消（软取消，当前片段结束后停止）。",

        'log_login_needed': "可能需要登录或会员，请配置 Cookie。",
        'log_ffmpeg_error': "FFmpeg 合并/处理失败，请确认已安装 ffmpeg。",
        'log_ejs_error': "EJS/Runtime 可能未生效。请安装 yt-dlp-ejs 并配置 Deno/Node。",
        'log_download_complete': "下载完成，正在处理/合并...",

        # Dialog: Format Selector
        'dlg_title': "选择格式（支持多选）",
        'dlg_group_info': "视频信息",
        'dlg_uploader_dur': "上传者：{uploader} | 时长：{dur} | 原始格式数：{count}",
        'tab_all': "所有格式",
        'tab_video': "视频格式（仅视频，可多选）",
        'tab_audio': "音频格式（仅音频，可多选）",
        'tab_presets': "推荐组合",
        'tab_preview': "组合预览",
        'dlg_tip_all': "单击选择单格式（完整/视频/音频）。",
        'dlg_tip_video': "使用 Ctrl/Shift 多选视频流（无音频）。",
        'dlg_tip_audio': "使用 Ctrl/Shift 多选音频流（无视频）。",
        'dlg_tip_presets': "单选推荐格式（最佳/4K/...）。",
        'dlg_preview_tip': "预览：显示已选视频/音频及交叉组合。",

        'hdr_id': "ID", 'hdr_ext': "扩展名", 'hdr_resolution': "分辨率", 'hdr_fps': "帧率",
        'hdr_vcodec': "视频编码", 'hdr_acodec': "音频编码", 'hdr_vbr': "视频码率",
        'hdr_abr': "音频码率", 'hdr_size': "大小", 'hdr_note': "备注",
        'hdr_asr': "采样率", 'hdr_channels': "声道", 'hdr_quality': "质量", 'hdr_desc': "说明",

        'btn_generate': "生成组合并确定",
        'btn_confirm_one': "仅当前单选确定",
        'btn_clear_sel': "清空选择",
        'btn_cancel': "取消",
        'sel_tip': "提示：在“视频格式”与“音频格式”页多选 → 点击“生成组合并确定”。",

        'msg_no_single': "当前未单选任何格式或预设。",
        'msg_no_batch': "尚未选择用于批量的“视频或音频”格式。",
        'preview_current': "=== 当前选择概览 ===",
        'preview_v': "视频格式ID（{n}）：{list}",
        'preview_v_none': "视频格式：未选择",
        'preview_a': "音频格式ID（{n}）：{list}",
        'preview_a_none': "音频格式：未选择",
        'preview_combo': "交叉组合（最多显示前 {m} 条，共 {t}）：",
        'preview_combo_none': "尚未形成视频+音频交叉组合；若只选视频或只选音频，则将逐个下载。",

        'preset_best': "最佳质量（推荐）",
        'preset_4k': "4K 超高清",
        'preset_2k': "2K",
        'preset_1080p': "1080p",
        'preset_720p': "720p",
        'preset_mp4': "优先 MP4",
        'preset_webm': "优先 WEBM",
        'preset_audio': "仅音频",

        # runtime labels (batch item)
        'log_batch_item': "[{i}/{t}] 下载格式：{fmt}",
        'log_batch_item_ok': "[{i}/{t}] ✓ 成功：{title}",
        'log_batch_item_fail': "[{i}/{t}] ✗ 失败：{err}",
        'log_batch_done': "批量结束：成功 {ok}/{t}",
    },
    'en': {
        'app_title': "yt-dlp GUI (Light Theme • EJS • Batch)",
        'banner_title': "yt-dlp Graphical Downloader",
        'banner_sub': "Light • EJS • Batch • Cookies • Subtitles",
        'language': "Language",
        'lang_zh': "中文",
        'lang_en': "English",

        'tab_basic': "Basic Settings",
        'tab_adv': "Advanced (Cookies • EJS • Runtime)",

        'group_url': "Video URL",
        'label_url': "URL:",
        'btn_parse': "🔍 Parse Formats",

        'group_out': "Output Directory",
        'btn_browse': "Browse...",

        'group_fmt': "Single-format Selection (Expression)",
        'label_quick': "Quick:",
        'fmt_best': "bestvideo+bestaudio/best - Best Quality (Recommended)",
        'fmt_best_complete': "best - Best Complete Format",
        'fmt_best_audio': "bestaudio/best - Best Audio Only",
        'fmt_1080p': "bestvideo[height<=1080]+bestaudio/best - 1080p",
        'fmt_720p': "bestvideo[height<=720]+bestaudio/best - 720p",
        'fmt_custom': "custom - Custom (from dialog or manual expression)",

        'label_custom': "Custom Expression:",
        'tip_batch': "Tip: For batch combinations, use the Parse dialog multi-select, not this field.",

        'group_opts': "Other Options",
        'chk_extract_audio': "Extract Audio (MP3)",
        'chk_embed_subs': "Embed Subtitles",

        'group_cookie': "Cookies",
        'label_cookie_file': "Cookie File:",
        'btn_select': "Select...",
        'btn_clear': "Clear",
        'cookie_none': "No Cookie",
        'cookie_set': "Cookie Set",

        'group_browser_cookie': "Browser Cookies (Auto)",
        'label_browser': "Browser:",
        'browser_note': "Make sure you are logged into the target site in the chosen browser.",

        'group_ejs': "Advanced Formats (EJS) & JS Runtime",
        'chk_enable_ejs': "Enable Advanced Formats (EJS)",
        'label_runtime': "Runtime:",
        'label_runtime_path': "Runtime Path (Optional):",
        'ejs_tip': "Install yt-dlp-ejs + Deno (or Node/Bun/QuickJS) for best YouTube 4K/AV1/VP9/HDR parsing.",

        'btn_start': "Start Download",
        'btn_cancel': "Cancel",
        'btn_clear_logs': "Clear Logs",

        'group_progress': "Progress",
        'status_ready': "Ready",
        'group_logs': "Logs",

        'warn_enter_url': "Please enter a video URL.",
        'status_parsing': "Parsing formats...",
        'log_parsing': "Parsing: {url}",
        'err_no_info': "Cannot get video info.",
        'log_title': "Title: {title}",
        'log_fmt_count': "Format count: {count}",
        'err_no_formats': "No formats parsed. Possibly needs login or EJS/runtime.",
        'log_no_high': "No 1440p+ formats found; JS runtime/EJS may not be active.",
        'status_ready_ok': "Ready",

        'log_ffmpeg_missing': "FFmpeg not found: merging/separating tasks may fail. Install ffmpeg.",
        'log_ffmpeg_detected': "FFmpeg detected: {path}",
        'log_ejs_present': "yt-dlp-ejs detected: local EJS scripts available.",
        'log_ejs_absent': "yt-dlp-ejs not detected: will enable remote EJS (ejs:github) if EJS is on.",
        'log_svttk_absent': "sv-ttk not found. Using fallback light theme. Install: pip install sv-ttk",

        'status_single_start': "Single download started...",
        'status_batch_start': "Batch download started...",
        'log_single_fmt': "Single download: {fmt}",
        'log_batch_start': "Batch start: {n} combinations",
        'status_done': "Done",
        'status_failed': "Failed",
        'status_cancelling': "Cancelling...",
        'log_cancel_req': "Cancel requested (soft cancel; stops after current part).",

        'log_login_needed': "Login/Member may be required. Configure cookies.",
        'log_ffmpeg_error': "FFmpeg error: please install ffmpeg.",
        'log_ejs_error': "EJS/Runtime may not be active. Install yt-dlp-ejs and Deno/Node.",
        'log_download_complete': "Download complete; processing/merging...",

        'dlg_title': "Select Formats (Multi-select Supported)",
        'dlg_group_info': "Video Info",
        'dlg_uploader_dur': "Uploader: {uploader} | Duration: {dur} | Formats: {count}",
        'tab_all': "All Formats",
        'tab_video': "Video-only (Multi-select)",
        'tab_audio': "Audio-only (Multi-select)",
        'tab_presets': "Recommended Presets",
        'tab_preview': "Combination Preview",
        'dlg_tip_all': "Single-click to choose a single format (complete/video/audio).",
        'dlg_tip_video': "Use Ctrl/Shift to multi-select video-only formats (no audio).",
        'dlg_tip_audio': "Use Ctrl/Shift to multi-select audio-only formats (no video).",
        'dlg_tip_presets': "Single-select a recommended preset (best, 4K, etc).",
        'dlg_preview_tip': "Preview: Selected video/audio IDs and cross-product combinations.",

        'hdr_id': "ID", 'hdr_ext': "Ext", 'hdr_resolution': "Resolution", 'hdr_fps': "FPS",
        'hdr_vcodec': "VCodec", 'hdr_acodec': "ACodec", 'hdr_vbr': "VBR",
        'hdr_abr': "ABR", 'hdr_size': "Size", 'hdr_note': "Note",
        'hdr_asr': "ASR", 'hdr_channels': "Ch", 'hdr_quality': "Quality", 'hdr_desc': "Description",

        'btn_generate': "Generate Combinations & Confirm",
        'btn_confirm_one': "Confirm Single Selection",
        'btn_clear_sel': "Clear Selection",
        'btn_cancel': "Cancel",
        'sel_tip': "Tip: Multi-select in Video-only + Audio-only, then Generate Combinations.",

        'msg_no_single': "No single selection (format/preset) made.",
        'msg_no_batch': "No videos or audios selected for batch.",
        'preview_current': "=== Current Selection ===",
        'preview_v': "Video IDs ({n}): {list}",
        'preview_v_none': "Video formats: None",
        'preview_a': "Audio IDs ({n}): {list}",
        'preview_a_none': "Audio formats: None",
        'preview_combo': "Combinations (showing up to {m} of {t}):",
        'preview_combo_none': "No cross-product combinations yet. If only videos or audios are selected, they will be downloaded individually.",

        'preset_best': "Best Quality (Recommended)",
        'preset_4k': "4K Ultra HD",
        'preset_2k': "2K Quad HD",
        'preset_1080p': "1080p Full HD",
        'preset_720p': "720p HD",
        'preset_mp4': "Prefer MP4",
        'preset_webm': "Prefer WEBM",
        'preset_audio': "Audio Only",

        'log_batch_item': "[{i}/{t}] Downloading: {fmt}",
        'log_batch_item_ok': "[{i}/{t}] ✓ Success: {title}",
        'log_batch_item_fail': "[{i}/{t}] ✗ Failed: {err}",
        'log_batch_done': "Batch done: success {ok}/{t}",
    }
}


# ========================= Format Selector Dialog ========================= #
class FormatSelectorDialog:
    """Dialog for selecting formats (supports multi-select and batch combinations)"""

    def __init__(self, parent, formats, video_info, lang='zh'):
        self.parent = parent
        self.formats = formats or []
        self.video_info = video_info or {}
        self.lang = lang
        self.t = lambda k, **kw: LANG[self.lang].get(k, k).format(**kw)
        self.result = None  # str (single expression) or dict {'videos': [...], 'audios': [...]}

        # selection caches
        self.selected_format_code = None
        self.selected_video_ids = set()
        self.selected_audio_ids = set()

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(self.t('dlg_title'))
        self.dialog.geometry("1180x740")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # theme
        if HAS_SVTTK:
            sv_ttk.set_theme("light")

        self._build_ui()

        # center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - self.dialog.winfo_width()) // 2
        y = (self.dialog.winfo_screenheight() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

    # ---------------- UI ---------------- #
    def _build_ui(self):
        info_frame = ttk.LabelFrame(self.dialog, text=self.t('dlg_group_info'), style='Card.TLabelframe')
        info_frame.pack(fill=tk.X, padx=12, pady=12)

        title = self.video_info.get('title', 'Unknown')
        duration = self.video_info.get('duration') or 0
        uploader = self.video_info.get('uploader', 'Unknown')
        dur_str = f"{int(duration // 60)}:{int(duration % 60):02d}" if duration else "N/A"
        ttk.Label(info_frame, text=title, font=("Segoe UI", 11, "bold")).pack(anchor=tk.W, pady=(6, 2))
        ttk.Label(info_frame, text=self.t('dlg_uploader_dur', uploader=uploader, dur=dur_str, count=len(self.formats))).pack(anchor=tk.W, pady=(0, 8))

        self.notebook = ttk.Notebook(self.dialog)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        all_frame = ttk.Frame(self.notebook)
        video_frame = ttk.Frame(self.notebook)
        audio_frame = ttk.Frame(self.notebook)
        preset_frame = ttk.Frame(self.notebook)
        summary_frame = ttk.Frame(self.notebook)

        self.notebook.add(all_frame, text=self.t('tab_all'))
        self.notebook.add(video_frame, text=self.t('tab_video'))
        self.notebook.add(audio_frame, text=self.t('tab_audio'))
        self.notebook.add(preset_frame, text=self.t('tab_presets'))
        self.notebook.add(summary_frame, text=self.t('tab_preview'))

        self._build_all_tab(all_frame)
        self._build_video_tab(video_frame)
        self._build_audio_tab(audio_frame)
        self._build_preset_tab(preset_frame)
        self._build_summary_tab(summary_frame)

        # bottom actions
        bar = ttk.Frame(self.dialog)
        bar.pack(fill=tk.X, padx=12, pady=12)

        self.selection_label = ttk.Label(bar, text=self.t('sel_tip'))
        self.selection_label.pack(side=tk.LEFT, padx=(4, 12))

        ttk.Button(bar, text=self.t('btn_generate'), command=self._confirm_batch, style='Accent.TButton').pack(side=tk.RIGHT, padx=6)
        ttk.Button(bar, text=self.t('btn_confirm_one'), command=self._confirm_single).pack(side=tk.RIGHT)
        ttk.Button(bar, text=self.t('btn_clear_sel'), command=self._clear_all).pack(side=tk.LEFT, padx=6)
        ttk.Button(bar, text=self.t('btn_cancel'), command=self.on_cancel).pack(side=tk.LEFT)

    # ---------------- Tabs ---------------- #
    def _build_all_tab(self, parent):
        head = ttk.Frame(parent)
        head.pack(fill=tk.X, padx=10, pady=8)
        ttk.Label(head, text=self.t('dlg_tip_all')).pack(side=tk.LEFT)

        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', lambda *_: self._filter_all())
        ttk.Entry(head, textvariable=self.search_var, width=26).pack(side=tk.RIGHT, padx=6)

        columns = ("format_id", "ext", "resolution", "fps", "vcodec", "acodec", "vbr", "abr", "filesize", "note")
        wrap = ttk.Frame(parent)
        wrap.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        sy = ttk.Scrollbar(wrap)
        sy.pack(side=tk.RIGHT, fill=tk.Y)
        sx = ttk.Scrollbar(wrap, orient=tk.HORIZONTAL)
        sx.pack(side=tk.BOTTOM, fill=tk.X)

        self.all_tree = ttk.Treeview(wrap, columns=columns, show="headings",
                                     yscrollcommand=sy.set, xscrollcommand=sx.set, selectmode="browse")
        sy.config(command=self.all_tree.yview)
        sx.config(command=self.all_tree.xview)

        heads = {
            "format_id": self.t('hdr_id'), "ext": self.t('hdr_ext'), "resolution": self.t('hdr_resolution'), "fps": self.t('hdr_fps'),
            "vcodec": self.t('hdr_vcodec'), "acodec": self.t('hdr_acodec'), "vbr": self.t('hdr_vbr'), "abr": self.t('hdr_abr'),
            "filesize": self.t('hdr_size'), "note": self.t('hdr_note')
        }
        widths = {"format_id": 80, "ext": 80, "resolution": 120, "fps": 80,
                  "vcodec": 150, "acodec": 150, "vbr": 100, "abr": 100, "filesize": 120, "note": 260}
        for k in columns:
            self.all_tree.heading(k, text=heads[k])
            self.all_tree.column(k, width=widths[k], anchor=tk.W)

        self.all_tree.pack(fill=tk.BOTH, expand=True)
        self._all_cache = []
        for fmt in self.formats:
            vals = self._row_from_format(fmt, include_acodec=True)
            self._all_cache.append(vals)
            self.all_tree.insert("", tk.END, values=vals, tags=(vals[0],))
        self.all_tree.bind("<<TreeviewSelect>>", self._on_all_single)

    def _filter_all(self):
        key = (self.search_var.get() or "").lower()
        for it in self.all_tree.get_children():
            self.all_tree.delete(it)
        for row in self._all_cache:
            if not key or any(key in str(v).lower() for v in row):
                self.all_tree.insert("", tk.END, values=row, tags=(row[0],))

    def _build_video_tab(self, parent):
        ttk.Label(parent, text=self.t('dlg_tip_video')).pack(anchor=tk.W, padx=10, pady=8)
        columns = ("format_id", "ext", "resolution", "fps", "vcodec", "vbr", "filesize", "note")

        wrap = ttk.Frame(parent)
        wrap.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        sy = ttk.Scrollbar(wrap)
        sy.pack(side=tk.RIGHT, fill=tk.Y)
        sx = ttk.Scrollbar(wrap, orient=tk.HORIZONTAL)
        sx.pack(side=tk.BOTTOM, fill=tk.X)

        self.video_tree = ttk.Treeview(wrap, columns=columns, show="headings",
                                       yscrollcommand=sy.set, xscrollcommand=sx.set, selectmode="extended")
        sy.config(command=self.video_tree.yview)
        sx.config(command=self.video_tree.xview)

        heads = {"format_id": self.t('hdr_id'), "ext": self.t('hdr_ext'), "resolution": self.t('hdr_resolution'), "fps": self.t('hdr_fps'),
                 "vcodec": self.t('hdr_vcodec'), "vbr": self.t('hdr_vbr'), "filesize": self.t('hdr_size'), "note": self.t('hdr_note')}
        widths = {"format_id": 90, "ext": 80, "resolution": 120, "fps": 80,
                  "vcodec": 160, "vbr": 110, "filesize": 120, "note": 300}
        for k in columns:
            self.video_tree.heading(k, text=heads[k])
            self.video_tree.column(k, width=widths[k], anchor=tk.W)
        self.video_tree.pack(fill=tk.BOTH, expand=True)

        v_formats = [f for f in self.formats if f.get('vcodec', 'none') != 'none' and f.get('acodec', 'none') == 'none']
        for fmt in v_formats:
            vals = self._row_from_format(fmt, include_acodec=False)
            self.video_tree.insert("", tk.END, values=vals, tags=(vals[0],))

        self.video_tree.bind("<<TreeviewSelect>>", self._on_video_multi)
        self.video_tree.bind("<ButtonRelease-1>", self._on_video_multi)

    def _build_audio_tab(self, parent):
        ttk.Label(parent, text=self.t('dlg_tip_audio')).pack(anchor=tk.W, padx=10, pady=8)
        columns = ("format_id", "ext", "acodec", "abr", "asr", "channels", "filesize", "note")

        wrap = ttk.Frame(parent)
        wrap.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        sy = ttk.Scrollbar(wrap)
        sy.pack(side=tk.RIGHT, fill=tk.Y)
        sx = ttk.Scrollbar(wrap, orient=tk.HORIZONTAL)
        sx.pack(side=tk.BOTTOM, fill=tk.X)

        self.audio_tree = ttk.Treeview(wrap, columns=columns, show="headings",
                                       yscrollcommand=sy.set, xscrollcommand=sx.set, selectmode="extended")
        sy.config(command=self.audio_tree.yview)
        sx.config(command=self.audio_tree.xview)

        heads = {"format_id": self.t('hdr_id'), "ext": self.t('hdr_ext'), "acodec": self.t('hdr_acodec'), "abr": self.t('hdr_abr'),
                 "asr": self.t('hdr_asr'), "channels": self.t('hdr_channels'), "filesize": self.t('hdr_size'), "note": self.t('hdr_note')}
        widths = {"format_id": 90, "ext": 80, "acodec": 140, "abr": 110,
                  "asr": 110, "channels": 80, "filesize": 120, "note": 300}
        for k in columns:
            self.audio_tree.heading(k, text=heads[k])
            self.audio_tree.column(k, width=widths[k], anchor=tk.W)
        self.audio_tree.pack(fill=tk.BOTH, expand=True)

        a_formats = [f for f in self.formats if f.get('acodec', 'none') != 'none' and f.get('vcodec', 'none') == 'none']
        for fmt in a_formats:
            fid = fmt.get('format_id', 'N/A')
            ext = fmt.get('ext', 'N/A')
            acodec = self._clean_codec(fmt.get('acodec'))
            abr = self._kbps(fmt.get('abr', fmt.get('tbr')))
            asr = f"{fmt.get('asr')}Hz" if fmt.get('asr') else "-"
            ch = f"{fmt.get('audio_channels')}ch" if fmt.get('audio_channels') else "-"
            size = self._filesize(fmt)
            note = fmt.get('format_note', '-') or "-"
            self.audio_tree.insert("", tk.END, values=(fid, ext, acodec, abr, asr, ch, size, note), tags=(fid,))

        self.audio_tree.bind("<<TreeviewSelect>>", self._on_audio_multi)
        self.audio_tree.bind("<ButtonRelease-1>", self._on_audio_multi)

    def _build_preset_tab(self, parent):
        ttk.Label(parent, text=self.t('dlg_tip_presets')).pack(anchor=tk.W, padx=10, pady=8)

        columns = ("name", "format", "quality", "description")
        wrap = ttk.Frame(parent)
        wrap.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        sy = ttk.Scrollbar(wrap)
        sy.pack(side=tk.RIGHT, fill=tk.Y)

        self.preset_tree = ttk.Treeview(wrap, columns=columns, show="headings",
                                        yscrollcommand=sy.set, selectmode="browse")
        sy.config(command=self.preset_tree.yview)

        heads = {"name": self.t('hdr_desc').split()[0], "format": "Format", "quality": self.t('hdr_quality'), "description": self.t('hdr_desc')}
        widths = {"name": 220, "format": 380, "quality": 120, "description": 420}
        for k in columns:
            self.preset_tree.heading(k, text=heads[k])
            self.preset_tree.column(k, width=widths[k], anchor=tk.W)
        self.preset_tree.pack(fill=tk.BOTH, expand=True)

        presets = [
            (self.t('preset_best'), "bestvideo+bestaudio/best", "★★★★★", self.t('preset_best')),
            (self.t('preset_4k'), "bestvideo[height<=2160]+bestaudio/best", "★★★★★", self.t('preset_4k')),
            (self.t('preset_2k'), "bestvideo[height<=1440]+bestaudio/best", "★★★★", self.t('preset_2k')),
            (self.t('preset_1080p'), "bestvideo[height<=1080]+bestaudio/best", "★★★★", self.t('preset_1080p')),
            (self.t('preset_720p'), "bestvideo[height<=720]+bestaudio/best", "★★★", self.t('preset_720p')),
            (self.t('preset_mp4'), "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best", "★★★★", self.t('preset_mp4')),
            (self.t('preset_webm'), "bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]/best", "★★★", self.t('preset_webm')),
            (self.t('preset_audio'), "bestaudio/best", "★★★★★", self.t('preset_audio')),
        ]
        for p in presets:
            self.preset_tree.insert("", tk.END, values=p, tags=(p[1],))
        self.preset_tree.bind("<<TreeviewSelect>>", self._on_preset_single)

    def _build_summary_tab(self, parent):
        ttk.Label(parent, text=self.t('dlg_preview_tip')).pack(anchor=tk.W, padx=10, pady=8)
        self.summary_text = ScrolledText(parent, height=24)
        self.summary_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        ttk.Button(parent, text=self.t('btn_clear_sel'), command=self._clear_all).pack(anchor=tk.W, padx=10, pady=(0, 10))
        ttk.Button(parent, text=self.t('btn_generate'), command=self._confirm_batch, style='Accent.TButton').pack(anchor=tk.E, padx=10, pady=(0, 10))

    # ---------------- Events ---------------- #
    def _on_tab_changed(self, event):
        if self.notebook.tab(self.notebook.select(), 'text') == self.t('tab_preview'):
            self._refresh_summary()

    def _on_all_single(self, _):
        it = self.all_tree.selection()
        if not it:
            return
        vals = self.all_tree.item(it[0])['values']
        fid, ext, res, _, vcodec, acodec = vals[0], vals[1], vals[2], vals[3], vals[4], vals[5]
        if vcodec != "-" and acodec != "-":
            self.selected_format_code = str(fid)
            self.selection_label.config(text=f"{self.t('tab_all')} • {fid} ({ext} {res})")
        elif vcodec != "-":
            self.selected_format_code = str(fid)
            self.selection_label.config(text=f"{self.t('tab_video')} • {fid} ({ext} {res})")
        elif acodec != "-":
            self.selected_format_code = str(fid)
            self.selection_label.config(text=f"{self.t('tab_audio')} • {fid} ({ext})")

    def _on_preset_single(self, _):
        it = self.preset_tree.selection()
        if not it:
            return
        fmt = self.preset_tree.item(it[0])['values'][1]
        self.selected_format_code = fmt
        self.selection_label.config(text=f"{self.t('tab_presets')} • {fmt}")

    def _on_video_multi(self, _):
        self.selected_video_ids = {str(self.video_tree.item(i)['values'][0]) for i in self.video_tree.selection()}
        self._update_hint_and_preview()

    def _on_audio_multi(self, _):
        self.selected_audio_ids = {str(self.audio_tree.item(i)['values'][0]) for i in self.audio_tree.selection()}
        self._update_hint_and_preview()

    def _update_hint_and_preview(self):
        v = len(self.selected_video_ids)
        a = len(self.selected_audio_ids)
        if v and a:
            self.selection_label.config(text=f"{self.t('tab_video')}:{v} • {self.t('tab_audio')}:{a}")
        elif v:
            self.selection_label.config(text=f"{self.t('tab_video')}:{v}")
        elif a:
            self.selection_label.config(text=f"{self.t('tab_audio')}:{a}")
        else:
            self.selection_label.config(text=self.t('sel_tip'))
        self._refresh_summary()

    def _refresh_summary(self):
        self.summary_text.config(state=tk.NORMAL)
        self.summary_text.delete(1.0, tk.END)
        v_ids = sorted(self.selected_video_ids)
        a_ids = sorted(self.selected_audio_ids)

        self.summary_text.insert(tk.END, f"{self.t('preview_current')}\n")
        if v_ids:
            self.summary_text.insert(tk.END, f"{self.t('preview_v', n=len(v_ids), list=', '.join(v_ids))}\n")
        else:
            self.summary_text.insert(tk.END, f"{self.t('preview_v_none')}\n")
        if a_ids:
            self.summary_text.insert(tk.END, f"{self.t('preview_a', n=len(a_ids), list=', '.join(a_ids))}\n\n")
        else:
            self.summary_text.insert(tk.END, f"{self.t('preview_a_none')}\n\n")

        if v_ids and a_ids:
            total = len(v_ids) * len(a_ids)
            maxshow = 30
            self.summary_text.insert(tk.END, f"{self.t('preview_combo', m=maxshow, t=total)}\n")
            for idx, (vid, aid) in enumerate(product(v_ids, a_ids), 1):
                if idx > maxshow:
                    self.summary_text.insert(tk.END, "... (more not shown)\n")
                    break
                self.summary_text.insert(tk.END, f"  {vid}+{aid}\n")
        else:
            self.summary_text.insert(tk.END, f"{self.t('preview_combo_none')}\n")
        self.summary_text.config(state=tk.DISABLED)

    # ---------------- Helpers ---------------- #
    def _row_from_format(self, fmt, include_acodec):
        fid = fmt.get('format_id', 'N/A')
        ext = fmt.get('ext', 'N/A')
        w, h = fmt.get('width'), fmt.get('height')
        res = f"{w}x{h}" if w and h else (f"{h}p" if h else (fmt.get('resolution') or "-"))
        fps = f"{fmt.get('fps')}fps" if fmt.get('fps') else "-"
        vcodec = self._clean_codec(fmt.get('vcodec', 'none'))
        vbr = self._kbps(fmt.get('vbr', fmt.get('tbr')))
        size = self._filesize(fmt)
        note = fmt.get('format_note') or "-"
        if include_acodec:
            acodec = self._clean_codec(fmt.get('acodec', 'none'))
            abr = self._kbps(fmt.get('abr'))
            return (fid, ext, res, fps, vcodec, acodec, vbr, abr, size, note)
        else:
            return (fid, ext, res, fps, vcodec, vbr, size, note)

    def _kbps(self, val):
        if not val:
            return "-"
        try:
            return f"{float(val):.0f}k"
        except Exception:
            return "-"

    def _clean_codec(self, name):
        if not name or name == 'none':
            return "-"
        return str(name).split('.')[0]

    def _filesize(self, fmt):
        size = fmt.get('filesize') or fmt.get('filesize_approx')
        if not size:
            return "-"
        try:
            size = float(size)
            for u in ('B', 'KB', 'MB', 'GB', 'TB'):
                if size < 1024.0:
                    return f"{size:.2f} {u}"
                size /= 1024.0
        except Exception:
            pass
        return "-"

    def _clear_all(self):
        self.selected_format_code = None
        self.selected_video_ids.clear()
        self.selected_audio_ids.clear()
        for tree in (self.video_tree, self.audio_tree, self.all_tree, self.preset_tree):
            tree.selection_remove(*tree.selection())
        self.selection_label.config(text=self.t('sel_tip'))
        self._refresh_summary()

    # ---------------- Confirm ---------------- #
    def _confirm_single(self):
        if not self.selected_format_code:
            messagebox.showwarning(self.t('btn_confirm_one'), self.t('msg_no_single'))
            return
        self.result = self.selected_format_code
        self.dialog.destroy()

    def _confirm_batch(self):
        if self.selected_format_code and not (self.selected_video_ids or self.selected_audio_ids):
            self.result = self.selected_format_code
            self.dialog.destroy()
            return
        videos = sorted(self.selected_video_ids)
        audios = sorted(self.selected_audio_ids)
        if not videos and not audios:
            messagebox.showwarning(self.t('btn_generate'), self.t('msg_no_batch'))
            return
        self.result = {'videos': videos, 'audios': audios}
        self._refresh_summary()
        self.dialog.destroy()

    def on_cancel(self):
        self.result = None
        self.dialog.destroy()


# ============================= Main GUI ============================= #
class YtDlpGUI:
    """Main GUI (Light Themed, Bilingual, EJS, Multi-select Batch)"""

    def __init__(self, root, lang='zh'):
        self.root = root
        self.lang = lang  # 'zh' or 'en'
        self.t = lambda k, **kw: LANG[self.lang].get(k, k).format(**kw)

        self.root.title(self.t('app_title'))
        self.root.geometry("1100x820")
        self.root.minsize(980, 780)

        # theme
        if HAS_SVTTK:
            sv_ttk.set_theme("light")
        else:
            self.palette = setup_fallback_light_theme(root)

        # state
        self.is_downloading = False
        self.cancel_requested = False
        self.batch_formats = []

        # config vars
        self.cookie_file_path = tk.StringVar()
        self.browser_var = tk.StringVar(value="none")

        self.enable_ejs_var = tk.BooleanVar(value=True)
        self.runtime_choice_var = tk.StringVar(value="auto")
        self.runtime_path_var = tk.StringVar()

        self.current_video_info = None

        # UI
        self._build_ui()

        # default output dir
        self.output_path.set(str(Path.home() / "Downloads"))

        # environment checks
        self._check_environment()

    # ---------------- UI Build ---------------- #
    def _build_ui(self):
        # clear existing (for language toggle rebuild)
        for child in self.root.winfo_children():
            child.destroy()

        # Banner with language switcher
        banner = ttk.Frame(self.root)
        banner.pack(fill=tk.X, padx=12, pady=12)
        ttk.Label(banner, text=self.t('banner_title'), font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        ttk.Label(banner, text=self.t('banner_sub'), style='Muted.TLabel').pack(side=tk.LEFT, padx=(10, 0))

        lang_frame = ttk.Frame(banner)
        lang_frame.pack(side=tk.RIGHT)
        ttk.Label(lang_frame, text=self.t('language')).pack(side=tk.LEFT, padx=(0, 6))
        self.lang_choice = tk.StringVar(value=self.t('lang_zh') if self.lang == 'zh' else self.t('lang_en'))
        lang_cb = ttk.Combobox(lang_frame, textvariable=self.lang_choice, state="readonly", width=10)
        lang_cb['values'] = (self.t('lang_zh'), self.t('lang_en'))
        lang_cb.pack(side=tk.LEFT)
        lang_cb.bind("<<ComboboxSelected>>", self._on_language_change)

        nb = ttk.Notebook(self.root)
        nb.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        basic = ttk.Frame(nb)
        adv = ttk.Frame(nb)
        nb.add(basic, text=self.t('tab_basic'))
        nb.add(adv, text=self.t('tab_adv'))

        basic.columnconfigure(1, weight=1)
        adv.columnconfigure(1, weight=1)

        # Basic tab
        url_row = ttk.LabelFrame(basic, text=self.t('group_url'), style='Card.TLabelframe')
        url_row.grid(row=0, column=0, columnspan=2, sticky="ew", padx=6, pady=6)
        url_row.columnconfigure(1, weight=1)

        ttk.Label(url_row, text=self.t('label_url')).grid(row=0, column=0, sticky=tk.W, padx=8, pady=8)
        self.url_var = tk.StringVar()
        url_entry = ttk.Entry(url_row, textvariable=self.url_var)
        url_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=8)

        self.parse_btn = ttk.Button(url_row, text=self.t('btn_parse'), command=self.parse_formats, style='Accent.TButton')
        self.parse_btn.grid(row=0, column=2, padx=8, pady=8)

        # Output dir
        out_box = ttk.LabelFrame(basic, text=self.t('group_out'), style='Card.TLabelframe')
        out_box.grid(row=1, column=0, columnspan=2, sticky="ew", padx=6, pady=6)
        out_box.columnconfigure(0, weight=1)
        self.output_path = tk.StringVar()
        ttk.Entry(out_box, textvariable=self.output_path).grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        ttk.Button(out_box, text=self.t('btn_browse'), command=self.browse_folder).grid(row=0, column=1, padx=8, pady=8)

        # Format selection (single-expression)
        fmt_box = ttk.LabelFrame(basic, text=self.t('group_fmt'), style='Card.TLabelframe')
        fmt_box.grid(row=2, column=0, columnspan=2, sticky="ew", padx=6, pady=6)
        fmt_box.columnconfigure(1, weight=1)

        ttk.Label(fmt_box, text=self.t('label_quick')).grid(row=0, column=0, sticky=tk.W, padx=8, pady=(8, 6))
        self.format_var = tk.StringVar(value=self.t('fmt_best'))
        cb = ttk.Combobox(fmt_box, textvariable=self.format_var, state="readonly", width=50)
        cb['values'] = (
            self.t('fmt_best'),
            self.t('fmt_best_complete'),
            self.t('fmt_best_audio'),
            self.t('fmt_1080p'),
            self.t('fmt_720p'),
            self.t('fmt_custom'),
        )
        cb.grid(row=0, column=1, sticky=tk.W, padx=(0, 8), pady=(8, 6))

        ttk.Label(fmt_box, text=self.t('label_custom')).grid(row=1, column=0, sticky=tk.W, padx=8, pady=6)
        self.custom_format_var = tk.StringVar()
        ttk.Entry(fmt_box, textvariable=self.custom_format_var).grid(row=1, column=1, sticky=tk.W, padx=(0, 8), pady=6)

        ttk.Label(fmt_box, text=self.t('tip_batch'), style='Muted.TLabel').grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=8, pady=(0, 10))

        # Other options
        opt_box = ttk.LabelFrame(basic, text=self.t('group_opts'), style='Card.TLabelframe')
        opt_box.grid(row=3, column=0, columnspan=2, sticky="ew", padx=6, pady=6)
        self.extract_audio = tk.BooleanVar(value=False)
        self.embed_subs = tk.BooleanVar(value=False)
        ttk.Checkbutton(opt_box, text=self.t('chk_extract_audio'), variable=self.extract_audio).grid(row=0, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Checkbutton(opt_box, text=self.t('chk_embed_subs'), variable=self.embed_subs).grid(row=1, column=0, sticky=tk.W, padx=8, pady=6)

        # Advanced tab
        cookie_box = ttk.LabelFrame(adv, text=self.t('group_cookie'), style='Card.TLabelframe')
        cookie_box.grid(row=0, column=0, columnspan=2, sticky="ew", padx=6, pady=6)
        cookie_box.columnconfigure(1, weight=1)
        ttk.Label(cookie_box, text=self.t('label_cookie_file')).grid(row=0, column=0, sticky=tk.W, padx=8, pady=8)
        self.cookie_status_label = ttk.Label(cookie_box, text=self.t('cookie_none'), style='Muted.TLabel')
        self.cookie_status_label.grid(row=1, column=0, columnspan=3, sticky=tk.W, padx=8, pady=(0, 6))
        ttk.Entry(cookie_box, textvariable=self.cookie_file_path).grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=8)
        ttk.Button(cookie_box, text=self.t('btn_select'), command=self.browse_cookie_file).grid(row=0, column=2, padx=8, pady=8)
        ttk.Button(cookie_box, text=self.t('btn_clear'), command=self.clear_cookie).grid(row=0, column=3, padx=8, pady=8)

        browser_box = ttk.LabelFrame(adv, text=self.t('group_browser_cookie'), style='Card.TLabelframe')
        browser_box.grid(row=1, column=0, columnspan=2, sticky="ew", padx=6, pady=6)
        browser_box.columnconfigure(1, weight=1)
        ttk.Label(browser_box, text=self.t('label_browser')).grid(row=0, column=0, sticky=tk.W, padx=8, pady=8)
        cb2 = ttk.Combobox(browser_box, textvariable=self.browser_var, state="readonly", width=30)
        cb2['values'] = (
            'none - (Do not use browser cookies)' if self.lang == 'en' else 'none - 不使用浏览器 Cookie',
            'chrome - Google Chrome',
            'firefox - Mozilla Firefox',
            'edge - Microsoft Edge',
            'safari - Safari',
            'opera - Opera',
            'brave - Brave'
        )
        cb2.grid(row=0, column=1, sticky=tk.W, padx=(0, 8), pady=8)
        ttk.Label(browser_box, text=self.t('browser_note'), style='Muted.TLabel').grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=8, pady=(0, 8))

        ejs_box = ttk.LabelFrame(adv, text=self.t('group_ejs'), style='Card.TLabelframe')
        ejs_box.grid(row=2, column=0, columnspan=2, sticky="ew", padx=6, pady=6)
        ejs_box.columnconfigure(1, weight=1)
        ttk.Checkbutton(ejs_box, text=self.t('chk_enable_ejs'), variable=self.enable_ejs_var).grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=8, pady=6)
        ttk.Label(ejs_box, text=self.t('label_runtime')).grid(row=1, column=0, sticky=tk.W, padx=8, pady=6)
        runtime_cb = ttk.Combobox(ejs_box, textvariable=self.runtime_choice_var, state="readonly", width=18)
        runtime_cb['values'] = ('auto', 'deno', 'node', 'bun', 'quickjs')
        runtime_cb.grid(row=1, column=1, sticky=tk.W, padx=(0, 8), pady=6)
        ttk.Label(ejs_box, text=self.t('label_runtime_path')).grid(row=2, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(ejs_box, textvariable=self.runtime_path_var).grid(row=2, column=1, sticky=tk.W, padx=(0, 8), pady=6)
        ttk.Label(ejs_box, text=self.t('ejs_tip'), style='Muted.TLabel').grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=8, pady=(0, 8))

        # Bottom area (progress + logs + actions)
        bottom = ttk.Frame(self.root)
        bottom.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        actions = ttk.Frame(bottom)
        actions.pack(pady=6)
        self.download_btn = ttk.Button(actions, text=self.t('btn_start'), command=self.start_download, style='Accent.TButton')
        self.download_btn.grid(row=0, column=0, padx=6)
        self.cancel_btn = ttk.Button(actions, text=self.t('btn_cancel'), command=self.cancel_download, state=tk.DISABLED)
        self.cancel_btn.grid(row=0, column=1, padx=6)
        ttk.Button(actions, text=self.t('btn_clear_logs'), command=self.clear_log).grid(row=0, column=2, padx=6)

        progress_box = ttk.LabelFrame(bottom, text=self.t('group_progress'), style='Card.TLabelframe')
        progress_box.pack(fill=tk.X, pady=8)
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_box, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=10, pady=10)
        self.status_label = ttk.Label(progress_box, text=self.t('status_ready'))
        self.status_label.pack(anchor=tk.W, padx=10, pady=(0, 10))

        logs_box = ttk.LabelFrame(bottom, text=self.t('group_logs'), style='Card.TLabelframe')
        logs_box.pack(fill=tk.BOTH, expand=True)
        self.log_text = ScrolledText(logs_box, height=14)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        # color tags
        self.log_text.tag_config("info", foreground="#1e88e5")
        self.log_text.tag_config("success", foreground="#2e7d32")
        self.log_text.tag_config("warning", foreground="#ed6c02")
        self.log_text.tag_config("error", foreground="#d32f2f")
        self.log_text.tag_config("batch", foreground="#2563eb")
        self.log_text.tag_config("ejs", foreground="#047857")
        self.log_text.tag_config("runtime", foreground="#6b21a8")

    def _on_language_change(self, event):
        selected = self.lang_choice.get()
        # Map display label to code
        if selected == LANG['zh']['lang_zh'] or selected == LANG['en']['lang_zh']:
            self.lang = 'zh'
        else:
            self.lang = 'en'
        self.t = lambda k, **kw: LANG[self.lang].get(k, k).format(**kw)
        # Rebuild UI with new language (keep state vars)
        self._build_ui()
        # Reapply status and environment messages appropriately if needed
        self.update_status(self.t('status_ready'))
        # Optionally re-log theme and environment in the new language
        self._check_environment(relog=False)

    # ---------------- Environment ---------------- #
    def _check_environment(self, relog=True):
        ffmpeg = shutil.which("ffmpeg")
        if relog:
            if not ffmpeg:
                self.log_message(self.t('log_ffmpeg_missing'), "warning")
            else:
                self.log_message(self.t('log_ffmpeg_detected', path=ffmpeg), "success")
            if HAVE_EJS:
                self.log_message(self.t('log_ejs_present'), "ejs")
            else:
                self.log_message(self.t('log_ejs_absent'), "ejs")
            if not HAS_SVTTK:
                self.log_message(self.t('log_svttk_absent'), "warning")

    # ---------------- Utils ---------------- #
    def log_message(self, msg, tag="info"):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{ts}] {msg}\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def update_status(self, msg, color=None):
        self.status_label.config(text=msg)
        if color:
            self.status_label.config(foreground=color)

    def clear_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

    def browse_folder(self):
        folder = filedialog.askdirectory(
            title=self.t('group_out'),
            initialdir=self.output_path.get() or str(Path.home()))
        if folder:
            self.output_path.set(folder)

    def browse_cookie_file(self):
        fp = filedialog.askopenfilename(
            title=self.t('label_cookie_file'),
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if fp:
            self.cookie_file_path.set(fp)
            self._update_cookie_status(True)
            self.log_message(f"{self.t('btn_select')} OK: {os.path.basename(fp)}", "success")

    def clear_cookie(self):
        self.cookie_file_path.set("")
        self.browser_var.set("none")
        self._update_cookie_status(False)
        self.log_message(self.t('btn_clear'), "info")

    def _update_cookie_status(self, has_cookie):
        self.cookie_status_label.config(text=self.t('cookie_set') if has_cookie else self.t('cookie_none'))

    def get_browser_name(self):
        raw = (self.browser_var.get() or "none")
        return raw.split(' - ')[0] if ' - ' in raw else (None if raw.startswith('none') else raw)

    # ---------------- EJS Options ---------------- #
    def _augment_ejs_options(self, opts):
        if not self.enable_ejs_var.get():
            return opts
        if not HAVE_EJS:
            rc = opts.setdefault('remote_components', [])
            if 'ejs:github' not in rc:
                rc.append('ejs:github')
            self.log_message("EJS: ejs:github enabled", "ejs")
        runtime_choice = self.runtime_choice_var.get().lower()
        runtime_path = (self.runtime_path_var.get() or "").strip()
        if runtime_choice != "auto":
            jr = opts.setdefault('js_runtimes', {})
            jr[runtime_choice] = {'path': runtime_path} if runtime_path else {}
            self.log_message(f"Runtime: {runtime_choice} {'-> ' + runtime_path if runtime_path else '(PATH search)'}", "runtime")
        else:
            self.log_message("Runtime: auto", "runtime")
        return opts

    # ---------------- Parse Formats ---------------- #
    def parse_formats(self):
        url = (self.url_var.get() or "").strip()
        if not url:
            messagebox.showwarning(self.t('btn_parse'), self.t('warn_enter_url'))
            return
        self.parse_btn.config(state=tk.DISABLED, text=self.t('status_parsing'))
        self.update_status(self.t('status_parsing'), "#1e88e5")
        self.log_message(self.t('log_parsing', url=url), "info")
        threading.Thread(target=self._parse_worker, args=(url,), daemon=True).start()

    def _parse_worker(self, url):
        try:
            opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
            cookie_file = (self.cookie_file_path.get() or "").strip()
            browser_name = self.get_browser_name()
            if cookie_file and os.path.exists(cookie_file):
                opts['cookiefile'] = cookie_file
                self.log_message(self.t('label_cookie_file') + " OK", "info")
            elif browser_name:
                opts['cookiesfrombrowser'] = (browser_name, None, None, None)
                self.log_message(f"{self.t('group_browser_cookie')} • {browser_name}", "info")

            opts = self._augment_ejs_options(opts)

            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            if not info:
                self._ui_error(self.t('err_no_info'))
                return

            formats = info.get('formats') or []
            self.current_video_info = info
            self.log_message(self.t('log_title', title=info.get('title', 'Unknown')), "success")
            self.log_message(self.t('log_fmt_count', count=len(formats)), "success")

            if not formats:
                self._ui_error(self.t('err_no_formats'))
                return

            has_high = any((f.get('height') or 0) >= 1440 for f in formats)
            if not has_high and self.enable_ejs_var.get():
                self.log_message(self.t('log_no_high'), "warning")

            self.root.after(0, lambda: self._open_selector(formats, info))
        except Exception as e:
            import traceback
            self.log_message(f"{self.t('status_failed')}: {e}", "error")
            self.log_message(traceback.format_exc(), "error")
            self._ui_error(f"{self.t('status_failed')}: {e}")
        finally:
            self.root.after(0, lambda: self.parse_btn.config(state=tk.NORMAL, text=self.t('btn_parse')))
            self.root.after(0, lambda: self.update_status(self.t('status_ready_ok'), "#2e7d32"))

    def _open_selector(self, formats, info):
        dlg = FormatSelectorDialog(self.root, formats, info, lang=self.lang)
        self.root.wait_window(dlg.dialog)
        if dlg.result is None:
            self.log_message("Selection cancelled", "warning")
            return

        if isinstance(dlg.result, str):
            # single-expression mode
            self.custom_format_var.set(dlg.result)
            self.format_var.set(self.t('fmt_custom'))
            self.batch_formats = []
            self.log_message(f"Single ready: {dlg.result}", "success")
        else:
            videos = dlg.result.get('videos', [])
            audios = dlg.result.get('audios', [])
            self.batch_formats = self._expand_batch(videos, audios)
            if not self.batch_formats:
                single_list = videos or audios
                self.batch_formats = single_list[:]
                self.log_message(self.t('log_batch_start', n=len(self.batch_formats)), "batch")
            else:
                self.log_message(self.t('log_batch_start', n=len(self.batch_formats)), "batch")
            self.custom_format_var.set("")
            self.format_var.set(self.t('fmt_custom'))

    def _expand_batch(self, videos, audios):
        if videos and audios:
            return [f"{v}+{a}" for v, a in product(videos, audios)]
        return videos or audios or []

    # ---------------- Download ---------------- #
    def start_download(self):
        if self.is_downloading:
            return
        url = (self.url_var.get() or "").strip()
        if not url:
            messagebox.showwarning(self.t('btn_start'), self.t('warn_enter_url'))
            return
        outdir = (self.output_path.get() or "").strip()
        if not outdir or not os.path.isdir(outdir):
            messagebox.showerror(self.t('btn_start'), "Output directory invalid.")
            return

        self.is_downloading = True
        self.cancel_requested = False
        self.download_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.progress_var.set(0)

        if self.batch_formats:
            self.update_status(self.t('status_batch_start'), "#1e88e5")
            self.log_message(self.t('log_batch_start', n=len(self.batch_formats)), "batch")
            threading.Thread(target=self._batch_download_worker, args=(url, outdir), daemon=True).start()
        else:
            fmt = self._get_single_format()
            self.update_status(self.t('status_single_start'), "#1e88e5")
            self.log_message(self.t('log_single_fmt', fmt=fmt), "info")
            threading.Thread(target=self._single_download_worker, args=(url, outdir, fmt), daemon=True).start()

    def _get_single_format(self):
        custom = (self.custom_format_var.get() or "").strip()
        if custom:
            return custom
        raw = (self.format_var.get() or "").strip()
        if ' - ' in raw:
            return raw.split(' - ', 1)[0]
        return raw or 'bestvideo+bestaudio/best'

    def _common_ydl_opts(self, outdir, fmt):
        opts = {
            'outtmpl': os.path.join(outdir, '%(title)s.%(ext)s'),
            'progress_hooks': [self._progress_hook],
            'format': fmt,
            'quiet': False,
            'no_warnings': False,
        }
        cookie_file = (self.cookie_file_path.get() or "").strip()
        browser_name = self.get_browser_name()
        if cookie_file and os.path.exists(cookie_file):
            opts['cookiefile'] = cookie_file
        elif browser_name:
            opts['cookiesfrombrowser'] = (browser_name, None, None, None)

        opts = self._augment_ejs_options(opts)

        if self.extract_audio.get():
            opts['format'] = 'bestaudio/best'
            opts.setdefault('postprocessors', []).append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            })
        if self.embed_subs.get():
            opts['writesubtitles'] = True
            opts['subtitleslangs'] = ['zh-Hans', 'zh-Hant', 'en']
            opts['embedsubtitles'] = True
        return opts

    def _single_download_worker(self, url, outdir, fmt):
        try:
            opts = self._common_ydl_opts(outdir, fmt)
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
            self.log_message(f"✓ {self.t('status_done')}: {info.get('title', 'Unknown')}", "success")
            self.update_status(self.t('status_done'), "#2e7d32")
        except Exception as e:
            self._handle_download_error(e)
        finally:
            self.is_downloading = False
            self.root.after(0, self._reset_buttons)

    def _batch_download_worker(self, url, outdir):
        total = len(self.batch_formats)
        success_count = 0
        for idx, fmt in enumerate(self.batch_formats, 1):
            if self.cancel_requested:
                self.log_message(self.t('log_cancel_req'), "warning")
                break
            self.update_status(f"{self.t('status_batch_start')} {idx}/{total}", "#1e88e5")
            self.log_message(self.t('log_batch_item', i=idx, t=total, fmt=fmt), "batch")
            try:
                opts = self._common_ydl_opts(outdir, fmt)
                with YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                self.log_message(self.t('log_batch_item_ok', i=idx, t=total, title=info.get('title', 'Unknown')), "success")
                success_count += 1
            except Exception as e:
                self.log_message(self.t('log_batch_item_fail', i=idx, t=total, err=e), "error")
                self._handle_download_error(e, silent=True)
        self.log_message(self.t('log_batch_done', ok=success_count, t=total), "batch")
        self.update_status(self.t('status_done'), "#2e7d32")
        self.is_downloading = False
        self.root.after(0, self._reset_buttons)

    def _handle_download_error(self, e, silent=False):
        msg = str(e)
        if not silent:
            self.log_message(f"{self.t('status_failed')}: {msg}", "error")
            self.update_status(self.t('status_failed'), "#d32f2f")
        lower = msg.lower()
        if "login" in lower or "member" in lower or "premium" in lower:
            self.log_message(self.t('log_login_needed'), "warning")
        if "ffmpeg" in lower:
            self.log_message(self.t('log_ffmpeg_error'), "warning")
        if "challenge" in lower or "signature" in lower:
            self.log_message(self.t('log_ejs_error'), "warning")
        if "complete" in lower and "processing" in lower:
            self.log_message(self.t('log_download_complete'), "success")

    def cancel_download(self):
        if self.is_downloading:
            self.cancel_requested = True
            self.log_message(self.t('log_cancel_req'), "warning")
            self.update_status(self.t('status_cancelling'), "#ed6c02")

    def _progress_hook(self, d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            done = d.get('downloaded_bytes') or 0
            if total > 0:
                self.progress_var.set(done * 100.0 / total)
            spd = d.get('speed') or 0
            eta = d.get('eta') or 0
            spd_str = f"{spd/1024/1024:.2f} MB/s" if spd else "N/A"
            eta_str = f"{int(eta)}s" if eta else "N/A"
            self.update_status(f"{self.t('status_single_start') if not self.batch_formats else self.t('status_batch_start')} "
                               f"{self.progress_var.get():.1f}% | {spd_str} | ETA {eta_str}", "#1e88e5")
        elif d['status'] == 'finished':
            self.progress_var.set(100)
            self.update_status(self.t('log_download_complete'), "#2e7d32")
            self.log_message(self.t('log_download_complete'), "success")

    def _reset_buttons(self):
        self.download_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)
        # Keep batch_formats for re-run if desired

    def _ui_error(self, msg):
        self.root.after(0, lambda: messagebox.showerror(self.t('status_failed'), msg))


def main():
    # Default language: Simplified Chinese ('zh'); set 'en' for English default
    default_lang = 'zh'
    root = tk.Tk()
    app = YtDlpGUI(root, lang=default_lang)
    # center main window
    root.update_idletasks()
    w, h = root.winfo_width(), root.winfo_height()
    x = (root.winfo_screenwidth() - w) // 2
    y = (root.winfo_screenheight() - h) // 2
    root.geometry(f"{w}x{h}+{x}+{y}")
    root.mainloop()


if __name__ == "__main__":
    main()
