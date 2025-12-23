#!/usr/bin/env python3
"""
yt-dlp GUI (CustomTkinter)
- 多选视频/音频格式批量下载
- EJS + JS Runtime 支持
- 一键中英文切换
- 全局字体：Microsoft YaHei
"""

import os
import sys
import shutil
import threading
from itertools import product
from pathlib import Path
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import tkinter.font as tkfont

try:
    from yt_dlp import YoutubeDL
except ImportError:
    print("未安装 yt-dlp，请执行: pip install -U yt-dlp")
    sys.exit(1)

try:
    import yt_dlp_ejs  # noqa
    HAVE_EJS = True
except Exception:
    HAVE_EJS = False

# ---------- 语言字典 ----------
LANG = {
    "zh": {
        "app_title": "yt-dlp 视频下载器 (多选批量 & EJS 支持)",
        "lang_zh": "中文",
        "lang_en": "English",
        "tab_basic": "基本设置",
        "tab_adv": "高级设置（Cookie / EJS / Runtime）",
        "video_url": "视频 URL:",
        "parse_formats": "🔍 解析格式",
        "output_dir": "输出目录:",
        "browse": "浏览...",
        "single_format": "单格式（非批量）表达式",
        "quick_select": "快速选择:",
        "custom_format": "自定义格式:",
        "custom_hint": "如果使用多选批量，请在解析对话框选择；这里的表达式仅用于单次下载。",
        "audio_only": "仅提取音频（MP3）",
        "embed_subs": "嵌入字幕",
        "instruction": "1. 输入 URL → “解析格式”\n2. 弹窗中多选视频与音频 → 生成批量组合，或单选预设 / 完整格式\n3. 返回后点击“开始下载”\n4. 批量时将逐个组合下载\n",
        "cookie_settings": "Cookie 设置",
        "cookie_file": "Cookie 文件:",
        "choose_file": "选择文件...",
        "clear": "清除",
        "cookie_status_none": "未设置 Cookie",
        "cookie_status_set": "✓ Cookie 已设置",
        "browser_cookie": "浏览器 Cookie（自动）",
        "browser_none": "none - 不使用浏览器 Cookie",
        "browser_chrome": "chrome - Google Chrome",
        "browser_firefox": "firefox - Mozilla Firefox",
        "browser_edge": "edge - Microsoft Edge",
        "browser_safari": "safari - Safari",
        "browser_opera": "opera - Opera",
        "browser_brave": "brave - Brave",
        "ejs_runtime": "高级格式(EJS)与 JS Runtime",
        "ejs_enable": "启用高级格式 (EJS)",
        "runtime": "Runtime:",
        "runtime_path": "Runtime 路径（留空自动）:",
        "start_download": "开始下载",
        "cancel": "取消",
        "clear_log": "清除日志",
        "download_progress": "下载进度",
        "logs": "日志",
        "ready": "就绪",
        "parse_title": "选择视频与音频格式（支持多选）",
        "all_formats": "所有格式",
        "videos_only": "视频格式（仅视频, 可多选）",
        "audios_only": "音频格式（仅音频, 可多选）",
        "presets": "推荐组合（单选）",
        "summary": "组合预览",
        "search": "搜索...",
        "all_formats_tip": "所有格式（完整/仅视频/仅音频）单击即单格式选择",
        "video_tip": "可 Ctrl/Shift 多选视频流；切换到“音频格式”后继续多选音频流。",
        "audio_tip": "可 Ctrl/Shift 多选音频流；与已选视频交叉组合。",
        "preset_tip": "推荐组合（单选）。若要多选批量，请用“视频格式”、“音频格式”页。",
        "summary_tip": "组合预览：显示当前多选的视频与音频及其交叉组合（自动刷新）。",
        "manual_refresh": "手动刷新",
        "gen_batch_confirm": "生成组合并确定",
        "confirm_current": "仅当前单选确定",
        "cancel_btn": "取消",
        "clear_selection": "清空选择",
        "hint_select": "提示：可在“视频格式”与“音频格式”标签页多选 → 再点击“生成组合并确定”",
        "ok_parsed": "开始解析:",
        "no_url": "请输入 URL",
        "no_output": "输出目录无效",
        "parse_failed": "解析失败",
        "select_none": "当前未单选任何格式或预设",
        "no_batch_choose": "还没有选择任何视频或音频用于批量下载",
        "cancel_choose": "取消选择",
        "batch_log": "批量组合数",
        "batch_done": "批量结束",
    },
    "en": {
        "app_title": "yt-dlp Video Downloader (Multi-select & EJS)",
        "lang_zh": "中文",
        "lang_en": "English",
        "tab_basic": "Basic Settings",
        "tab_adv": "Advanced (Cookie / EJS / Runtime)",
        "video_url": "Video URL:",
        "parse_formats": "🔍 Parse Formats",
        "output_dir": "Output Folder:",
        "browse": "Browse...",
        "single_format": "Single Format (non-batch)",
        "quick_select": "Quick Select:",
        "custom_format": "Custom Format:",
        "custom_hint": "For batch/multi-select, please use the parse dialog; this expression is only for single download.",
        "audio_only": "Audio Only (MP3)",
        "embed_subs": "Embed Subtitles",
        "instruction": "1. Enter URL → Parse Formats\n2. In dialog, multi-select video/audio → build batch, or single preset/full format\n3. Click “Start Download”\n4. In batch mode, each combination will download in turn\n",
        "cookie_settings": "Cookie Settings",
        "cookie_file": "Cookie File:",
        "choose_file": "Choose File...",
        "clear": "Clear",
        "cookie_status_none": "No Cookie set",
        "cookie_status_set": "✓ Cookie loaded",
        "browser_cookie": "Browser Cookie (auto)",
        "browser_none": "none - No browser cookie",
        "browser_chrome": "chrome - Google Chrome",
        "browser_firefox": "firefox - Mozilla Firefox",
        "browser_edge": "edge - Microsoft Edge",
        "browser_safari": "safari - Safari",
        "browser_opera": "opera - Opera",
        "browser_brave": "brave - Brave",
        "ejs_runtime": "Advanced Format (EJS) & JS Runtime",
        "ejs_enable": "Enable Advanced Format (EJS)",
        "runtime": "Runtime:",
        "runtime_path": "Runtime Path (empty = auto):",
        "start_download": "Start",
        "cancel": "Cancel",
        "clear_log": "Clear Log",
        "download_progress": "Download Progress",
        "logs": "Logs",
        "ready": "Ready",
        "parse_title": "Select Video/Audio Formats (multi-select supported)",
        "all_formats": "All Formats",
        "videos_only": "Video only (multi-select)",
        "audios_only": "Audio only (multi-select)",
        "presets": "Presets (single choice)",
        "summary": "Preview",
        "search": "Search...",
        "all_formats_tip": "All formats (full/video/audio), click to pick single format",
        "video_tip": "Ctrl/Shift to multi-select video; then go to Audio tab to multi-select audio.",
        "audio_tip": "Ctrl/Shift to multi-select audio; will be crossed with selected videos.",
        "preset_tip": "Presets (single). For batch multi-select, use Video/Audio tabs.",
        "summary_tip": "Preview: current selections and cross combinations (auto refresh).",
        "manual_refresh": "Refresh",
        "gen_batch_confirm": "Generate Combos & OK",
        "confirm_current": "OK (current single)",
        "cancel_btn": "Cancel",
        "clear_selection": "Clear Selection",
        "hint_select": "Tip: multi-select in Video/Audio tabs → click “Generate Combos & OK”.",
        "ok_parsed": "Start parsing:",
        "no_url": "Please input URL",
        "no_output": "Invalid output folder",
        "parse_failed": "Parse failed",
        "select_none": "No single preset or format selected",
        "no_batch_choose": "No video/audio selected for batch",
        "cancel_choose": "Selection canceled",
        "batch_log": "Batch combos",
        "batch_done": "Batch finished",
    }
}

DEFAULT_FONT = None
DEFAULT_FONT_BOLD = None
LOG_FONT = None

def set_global_tk_font():
    for name in (
        "TkDefaultFont", "TkTextFont", "TkFixedFont",
        "TkMenuFont", "TkHeadingFont", "TkCaptionFont",
        "TkSmallCaptionFont", "TkTooltipFont", "TkIconFont"
    ):
        try:
            tkfont.nametofont(name).config(family="Microsoft YaHei", size=11)
        except Exception:
            pass

def init_fonts():
    global DEFAULT_FONT, DEFAULT_FONT_BOLD, LOG_FONT
    try:
        ctk.FontManager.load_font("C:/Windows/Fonts/msyh.ttc")
    except Exception:
        pass
    DEFAULT_FONT = ctk.CTkFont(family="Microsoft YaHei", size=12)
    DEFAULT_FONT_BOLD = ctk.CTkFont(family="Microsoft YaHei", size=12, weight="bold")
    LOG_FONT = ("Microsoft YaHei", 11)

# ========== 格式选择对话框 ==========
class FormatSelectorDialog:
    def __init__(self, parent, formats, video_info, lang="zh"):
        self.lang = lang
        self.t = lambda k: LANG[self.lang].get(k, k)
        self.parent = parent
        self.result = None
        self.formats = formats or []
        self.video_info = video_info or {}
        self.selected_format_code = None
        self.selected_video_ids = set()
        self.selected_audio_ids = set()

        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title(self.t("parse_title"))
        self.dialog.geometry("1150x700")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 样式：放大 Notebook 标签字体 & Treeview 字体/行高/表头
        self.nb_style_name = "TabFont.TNotebook"
        style = ttk.Style(self.dialog)
        style.configure(f"{self.nb_style_name}.Tab", font=("Microsoft YaHei", 13, "bold"))
        # Treeview 大号字体样式（字体14，行高28，表头14 bold）
        self.tv_style_name = "Large.Treeview"
        style.configure(self.tv_style_name, font=("Microsoft YaHei", 14), rowheight=28)
        style.configure(f"{self.tv_style_name}.Heading", font=("Microsoft YaHei", 14, "bold"))

        self._build_ui()

        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - self.dialog.winfo_width()) // 2
        y = (self.dialog.winfo_screenheight() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

    def _build_ui(self):
        info_frame = ctk.CTkFrame(self.dialog, corner_radius=8)
        info_frame.pack(fill=tk.X, padx=10, pady=8)
        title = self.video_info.get('title', 'Unknown')
        duration = self.video_info.get('duration') or 0
        uploader = self.video_info.get('uploader', 'Unknown')
        duration_str = f"{int(duration // 60)}:{int(duration % 60):02d}" if duration else "N/A"
        head = f"Title: {title}\nUploader: {uploader} | Duration: {duration_str} | Formats: {len(self.formats)}"
        ctk.CTkLabel(info_frame, text=head, wraplength=1100, anchor="w", justify="left", font=DEFAULT_FONT).pack(anchor=tk.W, padx=8, pady=8)

        self.notebook = ttk.Notebook(self.dialog, style=self.nb_style_name)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        all_frame = ctk.CTkFrame(self.notebook)
        video_frame = ctk.CTkFrame(self.notebook)
        audio_frame = ctk.CTkFrame(self.notebook)
        preset_frame = ctk.CTkFrame(self.notebook)
        summary_frame = ctk.CTkFrame(self.notebook)

        self.notebook.add(all_frame, text=self.t("all_formats"))
        self.notebook.add(video_frame, text=self.t("videos_only"))
        self.notebook.add(audio_frame, text=self.t("audios_only"))
        self.notebook.add(preset_frame, text=self.t("presets"))
        self.notebook.add(summary_frame, text=self.t("summary"))

        self._build_all_formats_tab(all_frame)
        self._build_video_tab(video_frame)
        self._build_audio_tab(audio_frame)
        self._build_preset_tab(preset_frame)
        self._build_summary_tab(summary_frame)

        btn_bar = ctk.CTkFrame(self.dialog, corner_radius=8)
        btn_bar.pack(fill=tk.X, padx=10, pady=10)

        ctk.CTkButton(btn_bar, text=self.t("gen_batch_confirm"), command=self._confirm_batch, width=150, font=DEFAULT_FONT).pack(side=tk.RIGHT, padx=5)
        ctk.CTkButton(btn_bar, text=self.t("confirm_current"), command=self._confirm_single, width=150, font=DEFAULT_FONT).pack(side=tk.RIGHT)
        ctk.CTkButton(btn_bar, text=self.t("cancel_btn"), command=self.on_cancel, width=100, font=DEFAULT_FONT).pack(side=tk.RIGHT, padx=5)
        ctk.CTkButton(btn_bar, text=self.t("clear_selection"), command=self._clear_all, width=120, font=DEFAULT_FONT).pack(side=tk.LEFT)

        self.selection_label = ctk.CTkLabel(btn_bar, text=self.t("hint_select"), text_color="blue", anchor="w", justify="left", font=DEFAULT_FONT)
        self.selection_label.pack(side=tk.LEFT, padx=12)

    def _build_all_formats_tab(self, parent):
        bar = ctk.CTkFrame(parent)
        bar.pack(fill=tk.X, pady=6, padx=8)
        ctk.CTkLabel(bar, text=self.t("all_formats_tip"), text_color="gray", font=DEFAULT_FONT).pack(side=tk.LEFT)

        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', lambda *_: self._filter_all())
        ctk.CTkEntry(bar, textvariable=self.search_var, width=200, placeholder_text=self.t("search"), font=DEFAULT_FONT).pack(side=tk.RIGHT)

        columns = ("format_id", "ext", "resolution", "fps", "vcodec", "acodec", "vbr", "abr", "filesize", "note")
        frame = ctk.CTkFrame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        sy = ttk.Scrollbar(frame)
        sy.pack(side=tk.RIGHT, fill=tk.Y)
        sx = ttk.Scrollbar(frame, orient=tk.HORIZONTAL)
        sx.pack(side=tk.BOTTOM, fill=tk.X)

        self.all_tree = ttk.Treeview(
            frame, columns=columns, show="headings",
            yscrollcommand=sy.set, xscrollcommand=sx.set,
            selectmode="browse", style=self.tv_style_name
        )
        sy.config(command=self.all_tree.yview)
        sx.config(command=self.all_tree.xview)

        heads = {"format_id": "FormatID", "ext": "Ext", "resolution": "Resolution", "fps": "FPS", "vcodec": "VCodec", "acodec": "ACodec", "vbr": "VBR", "abr": "ABR", "filesize": "Size", "note": "Note"}
        widths = {"format_id": 80, "ext": 70, "resolution": 100, "fps": 60, "vcodec": 120, "acodec": 120, "vbr": 90, "abr": 90, "filesize": 100, "note": 280}
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
        ctk.CTkLabel(parent, text=self.t("video_tip"), text_color="gray", anchor="w", justify="left", font=DEFAULT_FONT).pack(anchor=tk.W, pady=5, padx=8)

        cols = ("format_id", "ext", "resolution", "fps", "vcodec", "vbr", "filesize", "note")
        frame = ctk.CTkFrame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        sy = ttk.Scrollbar(frame)
        sy.pack(side=tk.RIGHT, fill=tk.Y)
        sx = ttk.Scrollbar(frame, orient=tk.HORIZONTAL)
        sx.pack(side=tk.BOTTOM, fill=tk.X)

        self.video_tree = ttk.Treeview(
            frame, columns=cols, show="headings",
            yscrollcommand=sy.set, xscrollcommand=sx.set,
            selectmode="extended", style=self.tv_style_name
        )
        sy.config(command=self.video_tree.yview)
        sx.config(command=self.video_tree.xview)

        heads = {"format_id": "FormatID", "ext": "Ext", "resolution": "Resolution", "fps": "FPS", "vcodec": "VCodec", "vbr": "VBR", "filesize": "Size", "note": "Note"}
        widths = {"format_id": 90, "ext": 70, "resolution": 110, "fps": 60, "vcodec": 140, "vbr": 90, "filesize": 110, "note": 300}
        for k in cols:
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
        ctk.CTkLabel(parent, text=self.t("audio_tip"), text_color="gray", anchor="w", justify="left", font=DEFAULT_FONT).pack(anchor=tk.W, pady=5, padx=8)

        cols = ("format_id", "ext", "acodec", "abr", "asr", "channels", "filesize", "note")
        frame = ctk.CTkFrame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        sy = ttk.Scrollbar(frame)
        sy.pack(side=tk.RIGHT, fill=tk.Y)
        sx = ttk.Scrollbar(frame, orient=tk.HORIZONTAL)
        sx.pack(side=tk.BOTTOM, fill=tk.X)

        self.audio_tree = ttk.Treeview(
            frame, columns=cols, show="headings",
            yscrollcommand=sy.set, xscrollcommand=sx.set,
            selectmode="extended", style=self.tv_style_name
        )
        sy.config(command=self.audio_tree.yview)
        sx.config(command=self.audio_tree.xview)

        heads = {"format_id": "FormatID", "ext": "Ext", "acodec": "ACodec", "abr": "ABR", "asr": "ASR", "channels": "Ch", "filesize": "Size", "note": "Note"}
        widths = {"format_id": 90, "ext": 70, "acodec": 130, "abr": 90, "asr": 90, "channels": 70, "filesize": 110, "note": 300}
        for k in cols:
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
        ctk.CTkLabel(parent, text=self.t("preset_tip"), text_color="gray", anchor="w", justify="left", font=DEFAULT_FONT).pack(anchor=tk.W, pady=5, padx=8)

        cols = ("name", "format", "quality", "description")
        frame = ctk.CTkFrame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        sy = ttk.Scrollbar(frame)
        sy.pack(side=tk.RIGHT, fill=tk.Y)

        self.preset_tree = ttk.Treeview(
            frame, columns=cols, show="headings",
            yscrollcommand=sy.set, selectmode="browse",
            style=self.tv_style_name
        )
        sy.config(command=self.preset_tree.yview)

        heads = {"name": "Name", "format": "Format", "quality": "Q", "description": "Desc"}
        widths = {"name": 180, "format": 380, "quality": 90, "description": 470}
        for k in cols:
            self.preset_tree.heading(k, text=heads[k])
            self.preset_tree.column(k, width=widths[k], anchor=tk.W)
        self.preset_tree.pack(fill=tk.BOTH, expand=True)

        presets = [
            ("Best Quality", "bestvideo+bestaudio/best", "⭐⭐⭐⭐⭐", "Best video+audio"),
            ("4K", "bestvideo[height<=2160]+bestaudio/best", "⭐⭐⭐⭐⭐", "2160p + best audio"),
            ("2K", "bestvideo[height<=1440]+bestaudio/best", "⭐⭐⭐⭐", "1440p + best audio"),
            ("1080p", "bestvideo[height<=1080]+bestaudio/best", "⭐⭐⭐⭐", "1080p + best audio"),
            ("720p", "bestvideo[height<=720]+bestaudio/best", "⭐⭐⭐", "720p + best audio"),
            ("MP4 First", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best", "⭐⭐⭐⭐", "Good compatibility"),
            ("WEBM First", "bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]/best", "⭐⭐⭐", "Smaller size"),
            ("Audio Only", "bestaudio/best", "⭐⭐⭐⭐⭐", "Audio only"),
        ]
        self.preset_tree.tag_configure("preset", background="#f0f0f0")
        for p in presets:
            self.preset_tree.insert("", tk.END, values=p, tags=("preset", p[1]))
        self.preset_tree.bind("<<TreeviewSelect>>", self._on_preset_single)

    def _build_summary_tab(self, parent):
        ctk.CTkLabel(parent, text=self.t("summary_tip"), text_color="gray", anchor="w", justify="left", font=DEFAULT_FONT).pack(anchor=tk.W, pady=5, padx=8)
        self.summary_text = scrolledtext.ScrolledText(parent, height=22, wrap=tk.WORD, state=tk.DISABLED, font=LOG_FONT)
        self.summary_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        ctk.CTkButton(parent, text=self.t("manual_refresh"), command=self._refresh_summary, width=120, font=DEFAULT_FONT).pack(anchor=tk.E, padx=8, pady=6)

    def _on_tab_changed(self, event):
        current_tab = self.notebook.tab(self.notebook.select(), 'text')
        if self.t("summary") in current_tab:
            self._refresh_summary()

    def _row_from_format(self, fmt, include_acodec):
        fid = fmt.get('format_id', 'N/A')
        ext = fmt.get('ext', 'N/A')
        width, height = fmt.get('width'), fmt.get('height')
        if width and height:
            res = f"{width}x{height}"
        elif height:
            res = f"{height}p"
        else:
            res = fmt.get('resolution') or "-"
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

    def _on_all_single(self, _):
        it = self.all_tree.selection()
        if not it:
            return
        vals = self.all_tree.item(it[0])['values']
        fid = vals[0]
        self.selected_format_code = str(fid)

    def _on_preset_single(self, _):
        it = self.preset_tree.selection()
        if not it:
            return
        fmt_code = self.preset_tree.item(it[0])['values'][1]
        self.selected_format_code = fmt_code

    def _on_video_multi(self, _):
        self.selected_video_ids = {str(self.video_tree.item(i)['values'][0]) for i in self.video_tree.selection()}
        self._refresh_summary()

    def _on_audio_multi(self, _):
        self.selected_audio_ids = {str(self.audio_tree.item(i)['values'][0]) for i in self.audio_tree.selection()}
        self._refresh_summary()

    def _refresh_summary(self):
        if not hasattr(self, 'summary_text'):
            return
        self.summary_text.config(state=tk.NORMAL)
        self.summary_text.delete(1.0, tk.END)
        v_ids = sorted(self.selected_video_ids)
        a_ids = sorted(self.selected_audio_ids)
        self.summary_text.insert(tk.END, "=== Summary ===\n")
        if v_ids:
            self.summary_text.insert(tk.END, f"Video IDs ({len(v_ids)}): {', '.join(v_ids)}\n")
        else:
            self.summary_text.insert(tk.END, "Video: None\n")
        if a_ids:
            self.summary_text.insert(tk.END, f"Audio IDs ({len(a_ids)}): {', '.join(a_ids)}\n")
        else:
            self.summary_text.insert(tk.END, "Audio: None\n")

        if v_ids and a_ids:
            total = len(v_ids) * len(a_ids)
            self.summary_text.insert(tk.END, f"\nCross combos (total {total}): (show first 25)\n")
            for idx, (vid, aid) in enumerate(product(v_ids, a_ids), 1):
                if idx > 25:
                    self.summary_text.insert(tk.END, "... more ...\n")
                    break
                self.summary_text.insert(tk.END, f"  {vid}+{aid}\n")
        else:
            self.summary_text.insert(tk.END, "\nNo cross combos yet.\n")
        self.summary_text.config(state=tk.DISABLED)

    def _clear_all(self):
        self.selected_format_code = None
        self.selected_video_ids.clear()
        self.selected_audio_ids.clear()
        for tree in (self.video_tree, self.audio_tree, self.all_tree, self.preset_tree):
            tree.selection_remove(*tree.selection())
        self._refresh_summary()

    def _confirm_single(self):
        if not self.selected_format_code:
            messagebox.showwarning(self.t("parse_title"), self.t("select_none"))
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
            messagebox.showwarning(self.t("parse_title"), self.t("no_batch_choose"))
            return
        self.result = {'videos': videos, 'audios': audios}
        self._refresh_summary()
        self.dialog.destroy()

    def on_cancel(self):
        self.result = None
        self.dialog.destroy()

# ========== 主界面 ==========
class YtDlpGUI:
    def __init__(self, root):
        self.root = root
        self.lang_var = tk.StringVar(value="zh")
        self.lang = self.lang_var.get()

        self.is_downloading = False
        self.cancel_requested = False

        self.cookie_file_path = tk.StringVar()
        self.browser_var = tk.StringVar(value="none")

        self.enable_ejs_var = tk.BooleanVar(value=True)
        self.runtime_choice_var = tk.StringVar(value="auto")
        self.runtime_path_var = tk.StringVar()

        self.current_video_info = None
        self.batch_formats = []

        self.output_path = tk.StringVar()

        self.url_var = tk.StringVar()
        self.format_var = tk.StringVar(value="bestvideo+bestaudio/best - 最佳质量（推荐）")
        self.custom_format_var = tk.StringVar()
        self.extract_audio = tk.BooleanVar(value=False)
        self.embed_subs = tk.BooleanVar(value=False)

        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=0)
        self.root.grid_columnconfigure(0, weight=1)

        self._build_ui()
        self.output_path.set(str(Path.home() / "Downloads"))
        self._check_environment()

    def t(self, key):
        return LANG[self.lang].get(key, key)

    def _build_ui(self):
        self.root.title(self.t("app_title"))

        topbar = ctk.CTkFrame(self.root, corner_radius=0)
        topbar.grid(row=0, column=0, sticky="ew")
        topbar.grid_columnconfigure(0, weight=1)
        topbar.grid_columnconfigure(1, weight=0)
        topbar.grid_columnconfigure(2, weight=0)

        ctk.CTkLabel(topbar, text="Languages", font=DEFAULT_FONT_BOLD).grid(row=0, column=1, padx=(0, 6), pady=6, sticky="e")
        lang_button = ctk.CTkSegmentedButton(
            topbar,
            values=[LANG["zh"]["lang_zh"], LANG["en"]["lang_en"]],
            variable=self.lang_var,
            font=DEFAULT_FONT,
            width=200,
            command=self._on_language_changed
        )
        lang_button.set(LANG["zh"]["lang_zh"] if self.lang == "zh" else LANG["en"]["lang_en"])
        lang_button.grid(row=0, column=2, padx=10, pady=6, sticky="e")

        self.tabview = ctk.CTkTabview(self.root, width=940, height=540)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        self.basic_tab = self.tabview.add(self.t("tab_basic"))
        self.adv_tab = self.tabview.add(self.t("tab_adv"))
        for tab in (self.basic_tab, self.adv_tab):
            tab.grid_columnconfigure(0, weight=0)
            tab.grid_columnconfigure(1, weight=1)

        self._build_basic_tab(self.basic_tab)
        self._build_adv_tab(self.adv_tab)
        self._build_bottom()

    def _on_language_changed(self, _val=None):
        new_lang_label = self.lang_var.get()
        if new_lang_label == LANG["zh"]["lang_zh"]:
            self.lang = "zh"
        elif new_lang_label == LANG["en"]["lang_en"]:
            self.lang = "en"
        else:
            self.lang = "zh"
        for child in self.root.winfo_children():
            child.destroy()
        self._build_ui()

    def _build_basic_tab(self, parent):
        url_row = ctk.CTkFrame(parent, corner_radius=8)
        url_row.grid(row=0, column=0, columnspan=2, sticky="ew", pady=6, padx=4)
        url_row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(url_row, text=self.t("video_url"), font=DEFAULT_FONT_BOLD).grid(row=0, column=0, sticky=tk.W, padx=6, pady=8)
        ctk.CTkEntry(url_row, textvariable=self.url_var, font=DEFAULT_FONT).grid(row=0, column=1, sticky="ew", padx=6, pady=8)
        self.parse_btn = ctk.CTkButton(url_row, text=self.t("parse_formats"), command=self.parse_formats, width=140, font=DEFAULT_FONT)
        self.parse_btn.grid(row=0, column=2, padx=6, pady=8)

        out_box = ctk.CTkFrame(parent, corner_radius=8)
        out_box.grid(row=1, column=0, columnspan=2, sticky="ew", pady=6, padx=4)
        out_box.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(out_box, text=self.t("output_dir"), font=DEFAULT_FONT_BOLD).grid(row=0, column=0, sticky=tk.W, padx=6, pady=8)
        path_row = ctk.CTkFrame(out_box)
        path_row.grid(row=0, column=1, sticky="ew", padx=6, pady=8)
        path_row.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(path_row, textvariable=self.output_path, font=DEFAULT_FONT).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(path_row, text=self.t("browse"), command=self.browse_folder, width=90, font=DEFAULT_FONT).grid(row=0, column=1)

        fmt_box = ctk.CTkFrame(parent, corner_radius=8)
        fmt_box.grid(row=2, column=0, columnspan=2, sticky="ew", pady=8, padx=4)
        fmt_box.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(fmt_box, text=self.t("single_format"), font=DEFAULT_FONT_BOLD).grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(10, 4))
        ctk.CTkLabel(fmt_box, text=self.t("quick_select"), font=DEFAULT_FONT).grid(row=1, column=0, sticky=tk.W, padx=8)
        ctk.CTkComboBox(fmt_box, variable=self.format_var, width=420, font=DEFAULT_FONT, values=[
            'bestvideo+bestaudio/best - Best Quality',
            'best - Best single',
            'bestaudio/best - Audio Only',
            'bestvideo[height<=1080]+bestaudio/best - 1080p',
            'bestvideo[height<=720]+bestaudio/best - 720p',
            'custom - custom (select in dialog)'
        ]).grid(row=1, column=1, sticky=tk.W, padx=8, pady=4)

        ctk.CTkLabel(fmt_box, text=self.t("custom_format"), font=DEFAULT_FONT).grid(row=2, column=0, sticky=tk.W, padx=8, pady=6)
        ctk.CTkEntry(fmt_box, textvariable=self.custom_format_var, width=320, font=DEFAULT_FONT).grid(row=2, column=1, sticky=tk.W, padx=8, pady=6)
        ctk.CTkLabel(fmt_box, text=self.t("custom_hint"), text_color="blue", anchor="w", justify="left", font=DEFAULT_FONT).grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=8, pady=(0, 10))

        opt = ctk.CTkFrame(parent, corner_radius=8)
        opt.grid(row=3, column=0, columnspan=2, sticky="ew", pady=8, padx=4)
        ctk.CTkCheckBox(opt, text=self.t("audio_only"), variable=self.extract_audio, font=DEFAULT_FONT).grid(row=0, column=0, sticky=tk.W, pady=6, padx=8)
        ctk.CTkCheckBox(opt, text=self.t("embed_subs"), variable=self.embed_subs, font=DEFAULT_FONT).grid(row=1, column=0, sticky=tk.W, pady=6, padx=8)

        info = ctk.CTkFrame(parent, corner_radius=8)
        info.grid(row=4, column=0, columnspan=2, sticky="ew", pady=8, padx=4)
        ctk.CTkLabel(info, text=self.t("instruction"), justify=tk.LEFT, text_color="gray", font=DEFAULT_FONT).pack(anchor=tk.W, padx=8, pady=10)

    def _build_adv_tab(self, parent):
        cookie_box = ctk.CTkFrame(parent, corner_radius=8)
        cookie_box.grid(row=0, column=0, columnspan=2, sticky="ew", pady=8, padx=4)
        cookie_box.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(cookie_box, text=self.t("cookie_settings"), font=DEFAULT_FONT_BOLD).grid(row=0, column=0, sticky="w", padx=8, pady=(8, 2))
        ctk.CTkLabel(cookie_box, text=self.t("cookie_file"), font=DEFAULT_FONT).grid(row=1, column=0, sticky=tk.W, padx=8, pady=6)
        row = ctk.CTkFrame(cookie_box)
        row.grid(row=1, column=1, sticky="ew", pady=6, padx=8)
        row.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(row, textvariable=self.cookie_file_path, font=DEFAULT_FONT).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(row, text=self.t("choose_file"), command=self.browse_cookie_file, width=110, font=DEFAULT_FONT).grid(row=0, column=1)
        ctk.CTkButton(row, text=self.t("clear"), command=self.clear_cookie, width=80, font=DEFAULT_FONT).grid(row=0, column=2, padx=(6, 0))
        self.cookie_status_label = ctk.CTkLabel(cookie_box, text=self.t("cookie_status_none"), text_color="gray", font=DEFAULT_FONT)
        self.cookie_status_label.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(0, 8), padx=8)

        browser_box = ctk.CTkFrame(parent, corner_radius=8)
        browser_box.grid(row=1, column=0, columnspan=2, sticky="ew", pady=8, padx=4)
        browser_box.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(browser_box, text=self.t("browser_cookie"), font=DEFAULT_FONT_BOLD).grid(row=0, column=0, sticky="w", padx=8, pady=(8, 2))
        ctk.CTkLabel(browser_box, text=self.t("browser_cookie"), font=DEFAULT_FONT).grid(row=1, column=0, sticky=tk.W, padx=8, pady=6)
        ctk.CTkComboBox(browser_box, variable=self.browser_var, width=260, font=DEFAULT_FONT, values=[
            self.t("browser_none"),
            self.t("browser_chrome"),
            self.t("browser_firefox"),
            self.t("browser_edge"),
            self.t("browser_safari"),
            self.t("browser_opera"),
            self.t("browser_brave")
        ]).grid(row=1, column=1, sticky=tk.W, padx=8, pady=6)

        ejs_box = ctk.CTkFrame(parent, corner_radius=8)
        ejs_box.grid(row=2, column=0, columnspan=2, sticky="ew", pady=8, padx=4)
        ejs_box.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(ejs_box, text=self.t("ejs_runtime"), font=DEFAULT_FONT_BOLD).grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 2))
        ctk.CTkCheckBox(ejs_box, text=self.t("ejs_enable"), variable=self.enable_ejs_var, font=DEFAULT_FONT).grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=8, pady=6)
        ctk.CTkLabel(ejs_box, text=self.t("runtime"), font=DEFAULT_FONT).grid(row=2, column=0, sticky=tk.W, padx=8, pady=6)
        ctk.CTkComboBox(ejs_box, variable=self.runtime_choice_var, width=160, font=DEFAULT_FONT, values=('auto', 'deno', 'node', 'bun', 'quickjs')).grid(row=2, column=1, sticky=tk.W, padx=8, pady=6)
        ctk.CTkLabel(ejs_box, text=self.t("runtime_path"), font=DEFAULT_FONT).grid(row=3, column=0, sticky=tk.W, padx=8, pady=6)
        ctk.CTkEntry(ejs_box, textvariable=self.runtime_path_var, width=280, font=DEFAULT_FONT).grid(row=3, column=1, sticky=tk.W, padx=8, pady=6)

    def _build_bottom(self):
        area = ctk.CTkFrame(self.root, corner_radius=8)
        area.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        area.grid_columnconfigure(0, weight=1)

        btns = ctk.CTkFrame(area)
        btns.grid(row=0, column=0, sticky="ew", pady=6, padx=4)
        btns.grid_columnconfigure((0, 1, 2), weight=1)
        self.download_btn = ctk.CTkButton(btns, text=self.t("start_download"), command=self.start_download, width=140, font=DEFAULT_FONT)
        self.download_btn.grid(row=0, column=0, padx=6)
        self.cancel_btn = ctk.CTkButton(btns, text=self.t("cancel"), command=self.cancel_download, state=tk.DISABLED, width=140, font=DEFAULT_FONT)
        self.cancel_btn.grid(row=0, column=1, padx=6)
        ctk.CTkButton(btns, text=self.t("clear_log"), command=self.clear_log, width=140, font=DEFAULT_FONT).grid(row=0, column=2, padx=6)

        pbox = ctk.CTkFrame(area, corner_radius=8)
        pbox.grid(row=1, column=0, sticky="ew", pady=6, padx=4)
        ctk.CTkLabel(pbox, text=self.t("download_progress"), font=DEFAULT_FONT_BOLD).pack(anchor="w", padx=8, pady=(8, 2))
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_bar = ctk.CTkProgressBar(pbox, variable=self.progress_var)
        self.progress_bar.set(0.0)
        self.progress_bar.pack(fill=tk.X, pady=8, padx=8)
        self.status_label = ctk.CTkLabel(pbox, text=self.t("ready"), text_color="green", font=DEFAULT_FONT)
        self.status_label.pack(anchor=tk.W, padx=8, pady=(0, 8))

        lbox = ctk.CTkFrame(area, corner_radius=8)
        lbox.grid(row=2, column=0, sticky="nsew", pady=6, padx=4)
        lbox.grid_rowconfigure(1, weight=1)
        lbox.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(lbox, text=self.t("logs"), font=DEFAULT_FONT_BOLD).grid(row=0, column=0, sticky="w", padx=8, pady=(8, 2))
        self.log_text = scrolledtext.ScrolledText(lbox, height=10, wrap=tk.WORD, state=tk.DISABLED, font=LOG_FONT)
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        for tag, color in {"info": "blue", "warning": "orange", "error": "red", "success": "green", "runtime": "#8844cc", "ejs": "#00695c", "batch": "#795548"}.items():
            self.log_text.tag_config(tag, foreground=color)

    def log_message(self, msg, tag="info"):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{msg}\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def update_status(self, msg, color="black"):
        self.status_label.configure(text=msg, text_color=color)

    def clear_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

    def browse_folder(self):
        folder = filedialog.askdirectory(title=self.t("browse"), initialdir=self.output_path.get() or str(Path.home()))
        if folder:
            self.output_path.set(folder)

    def browse_cookie_file(self):
        fp = filedialog.askopenfilename(title=self.t("choose_file"), filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")])
        if fp:
            self.cookie_file_path.set(fp)
            self._update_cookie_status(True)
            self.log_message(f"✓ Cookie: {os.path.basename(fp)}", "success")

    def clear_cookie(self):
        self.cookie_file_path.set("")
        self.browser_var.set("none")
        self._update_cookie_status(False)
        self.log_message("Cookie cleared", "info")

    def _update_cookie_status(self, has_cookie):
        if has_cookie:
            self.cookie_status_label.configure(text=self.t("cookie_status_set"), text_color="green")
        else:
            self.cookie_status_label.configure(text=self.t("cookie_status_none"), text_color="gray")

    def get_browser_name(self):
        raw = (self.browser_var.get() or "none")
        name = raw.split(' - ')[0] if ' - ' in raw else raw
        return None if name == "none" else name

    def _check_environment(self):
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            self.log_message("ffmpeg not found (merge may fail).", "warning")
        else:
            self.log_message(f"ffmpeg: {ffmpeg}", "success")
        if HAVE_EJS:
            self.log_message("yt-dlp-ejs detected.", "ejs")
        else:
            self.log_message("yt-dlp-ejs not found, will use remote ejs:github (if enabled).", "ejs")

    def parse_formats(self):
        url = (self.url_var.get() or "").strip()  # 修正为 strip()
        if not url:
            messagebox.showwarning(self.t("app_title"), self.t("no_url"))
            return
        self.parse_btn.configure(state=tk.DISABLED, text=self.t("parse_formats"))
        self.update_status("Parsing...", "blue")
        self.log_message(f"{self.t('ok_parsed')} {url}", "info")
        threading.Thread(target=self._parse_worker, args=(url,), daemon=True).start()

    def _parse_worker(self, url):
        try:
            opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
            cookie_file = (self.cookie_file_path.get() or "").strip()
            browser_name = self.get_browser_name()
            if cookie_file and os.path.exists(cookie_file):
                opts['cookiefile'] = cookie_file
            elif browser_name:
                opts['cookiesfrombrowser'] = (browser_name, None, None, None)
            opts = self._augment_ejs_options(opts)
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            if not info:
                self._ui_error(self.t("parse_failed"))
                return
            formats = info.get('formats') or []
            self.current_video_info = info
            self.log_message(f"Title: {info.get('title', 'Unknown')}", "success")
            self.log_message(f"Formats: {len(formats)}", "success")
            self.root.after(0, lambda: self._open_selector(formats, info))
        except Exception as e:
            import traceback
            self.log_message(f"Parse failed: {e}", "error")
            self.log_message(traceback.format_exc(), "error")
            self._ui_error(f"{self.t('parse_failed')}: {e}")
        finally:
            self.root.after(0, lambda: self.parse_btn.configure(state=tk.NORMAL, text=self.t("parse_formats")))
            self.root.after(0, lambda: self.update_status(self.t("ready"), "green"))

    def _open_selector(self, formats, info):
        dlg = FormatSelectorDialog(self.root, formats, info, lang=self.lang)
        self.root.wait_window(dlg.dialog)
        if dlg.result is None:
            self.log_message(self.t("cancel_choose"), "warning")
            return
        if isinstance(dlg.result, str):
            self.custom_format_var.set(dlg.result)
            self.format_var.set("custom - 单格式")
            self.batch_formats = []
            self.log_message(f"Single format: {dlg.result}", "success")
        else:
            videos = dlg.result.get('videos', [])
            audios = dlg.result.get('audios', [])
            self.batch_formats = self._expand_batch(videos, audios)
            if not self.batch_formats:
                single_list = videos or audios
                self.batch_formats = single_list[:]
                self.log_message(f"Batch single type: {len(self.batch_formats)}", "batch")
            else:
                self.log_message(f"{self.t('batch_log')}: {len(self.batch_formats)}", "batch")
            self.custom_format_var.set("")
            self.format_var.set("custom - batch")

    def _expand_batch(self, videos, audios):
        if videos and audios:
            return [f"{v}+{a}" for v, a in product(videos, audios)]
        return videos or audios or []

    def _augment_ejs_options(self, opts):
        if not self.enable_ejs_var.get():
            return opts
        if not HAVE_EJS:
            rc = opts.setdefault('remote_components', [])
            if 'ejs:github' not in rc:
                rc.append('ejs:github')
            self.log_message("EJS remote: ejs:github", "ejs")
        runtime_choice = self.runtime_choice_var.get().lower()
        runtime_path = (self.runtime_path_var.get() or "").strip()
        if runtime_choice != "auto":
            jr = opts.setdefault('js_runtimes', {})
            jr[runtime_choice] = {'path': runtime_path} if runtime_path else {}
            self.log_message(f"Runtime: {runtime_choice} {'-> ' + runtime_path if runtime_path else '(PATH)'}", "runtime")
        else:
            self.log_message("Runtime: auto", "runtime")
        return opts

    def start_download(self):
        if self.is_downloading:
            return
        url = (self.url_var.get() or "").strip()
        if not url:
            messagebox.showwarning(self.t("app_title"), self.t("no_url"))
            return
        outdir = (self.output_path.get() or "").strip()
        if not outdir or not os.path.isdir(outdir):
            messagebox.showerror(self.t("app_title"), self.t("no_output"))
            return

        self.is_downloading = True
        self.cancel_requested = False
        self.download_btn.configure(state=tk.DISABLED)
        self.cancel_btn.configure(state=tk.NORMAL)
        self.progress_var.set(0.0)
        self.progress_bar.set(0.0)

        if self.batch_formats:
            self.update_status("Batch downloading...", "blue")
            self.log_message(f"Batch start: {len(self.batch_formats)}", "batch")
            threading.Thread(target=self._batch_download_worker, args=(url, outdir), daemon=True).start()
        else:
            fmt = self._get_single_format()
            self.update_status("Single download...", "blue")
            self.log_message(f"Single format: {fmt}", "info")
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
            opts.setdefault('postprocessors', []).append({'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'})
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
            self.log_message(f"✓ Done: {info.get('title', 'Unknown')}", "success")
            self.update_status("Done", "green")
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
                self.log_message("User canceled.", "warning")
                break
            self.update_status(f"Batch {idx}/{total}: {fmt}", "blue")
            self.log_message(f"[{idx}/{total}] {fmt}", "batch")
            try:
                opts = self._common_ydl_opts(outdir, fmt)
                with YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                self.log_message(f"[{idx}/{total}] ✓ {info.get('title', 'Unknown')}", "success")
                success_count += 1
            except Exception as e:
                self.log_message(f"[{idx}/{total}] ✗ {e}", "error")
                self._handle_download_error(e, silent=True)
        self.log_message(f"{self.t('batch_done')}: {success_count}/{total}", "batch")
        self.update_status(self.t("batch_done"), "green")
        self.is_downloading = False
        self.root.after(0, self._reset_buttons)

    def _handle_download_error(self, e, silent=False):
        msg = str(e)
        if not silent:
            self.log_message(f"Error: {msg}", "error")
            self.update_status("Error", "red")
        lower = msg.lower()
        if "login" in lower or "member" in lower or "premium" in lower:
            self.log_message("Maybe need login / cookie.", "warning")
        if "ffmpeg" in lower:
            self.log_message("ffmpeg missing or merge failed.", "warning")
        if "challenge" in lower or "signature" in lower:
            self.log_message("EJS / runtime may be required.", "warning")

    def cancel_download(self):
        if self.is_downloading:
            self.cancel_requested = True
            self.log_message("Cancel requested", "warning")
            self.update_status("Canceling...", "orange")

    def _progress_hook(self, d):
        def update_ui():
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                done = d.get('downloaded_bytes') or 0
                progress = (done / total) if total else 0.0  # 0~1
                self.progress_var.set(progress)
                percent = progress * 100
                spd = d.get('speed') or 0
                eta = d.get('eta') or 0
                spd_str = f"{spd/1024/1024:.2f} MB/s" if spd else "N/A"
                eta_str = f"{int(eta)}s" if eta else "N/A"
                self.update_status(f"Downloading... {percent:.1f}% | {spd_str} | ETA {eta_str}", "blue")
            elif d['status'] == 'finished':
                self.progress_var.set(1.0)
                self.update_status("Post-processing...", "green")
        self.root.after(0, update_ui)

    def _reset_buttons(self):
        self.download_btn.configure(state=tk.NORMAL)
        self.cancel_btn.configure(state=tk.DISABLED)

    def _ui_error(self, msg):
        self.root.after(0, lambda: messagebox.showerror(self.t("app_title"), msg))

def main():
    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")
    desired_w, desired_h = 1150, 850

    root = ctk.CTk()
    root.minsize(1000, 720)
    set_global_tk_font()
    init_fonts()

    app = YtDlpGUI(root)
    x = (root.winfo_screenwidth() - desired_w) // 2
    y = (root.winfo_screenheight() - desired_h) // 2
    root.geometry(f"{desired_w}x{desired_h}+{x}+{y}")
    root.mainloop()

if __name__ == "__main__":
    main()
