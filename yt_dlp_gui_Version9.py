#!/usr/bin/env python3
"""
yt-dlp GUI - 支持：
  - 多选视频 / 音频格式批量组合下载
  - 高级格式(EJS) + JS Runtime
  - 自动刷新“组合预览”标签内容
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import os
import sys
import shutil
from pathlib import Path
from itertools import product

try:
    from yt_dlp import YoutubeDL
except ImportError:
    print("错误: 未安装 yt-dlp，请执行: pip install -U yt-dlp")
    sys.exit(1)

try:
    import yt_dlp_ejs  # noqa
    HAVE_EJS = True
except Exception:
    HAVE_EJS = False


class FormatSelectorDialog:
    """格式选择对话框（修复组合预览不刷新问题）"""

    def __init__(self, parent, formats, video_info):
        self.parent = parent
        self.result = None
        self.formats = formats or []
        self.video_info = video_info or {}

        self.selected_format_code = None          # 单格式 / 预设
        self.selected_video_ids = set()
        self.selected_audio_ids = set()

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("选择视频与音频格式（支持多选）")
        self.dialog.geometry("1150x700")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 用于 Notebook 切换自动刷新
        self.notebook = None

        self._build_ui()

        # 居中
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - self.dialog.winfo_width()) // 2
        y = (self.dialog.winfo_screenheight() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

    # ---------------- 构建界面 ----------------
    def _build_ui(self):
        info_frame = ttk.LabelFrame(self.dialog, text="视频信息", padding=10)
        info_frame.pack(fill=tk.X, padx=10, pady=6)

        title = self.video_info.get('title', 'Unknown')
        duration = self.video_info.get('duration') or 0
        uploader = self.video_info.get('uploader', 'Unknown')
        duration_str = f"{int(duration // 60)}:{int(duration % 60):02d}" if duration else "N/A"
        head = f"标题: {title}\n上传者: {uploader} | 时长: {duration_str} | 原始格式总数: {len(self.formats)}"
        ttk.Label(info_frame, text=head, wraplength=1100).pack(anchor=tk.W)

        self.notebook = ttk.Notebook(self.dialog)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        all_frame = ttk.Frame(self.notebook)
        video_frame = ttk.Frame(self.notebook)
        audio_frame = ttk.Frame(self.notebook)
        preset_frame = ttk.Frame(self.notebook)
        summary_frame = ttk.Frame(self.notebook)

        self.notebook.add(all_frame, text="所有格式")
        self.notebook.add(video_frame, text="视频格式（仅视频, 可多选）")
        self.notebook.add(audio_frame, text="音频格式（仅音频, 可多选）")
        self.notebook.add(preset_frame, text="推荐组合（单选）")
        self.notebook.add(summary_frame, text="组合预览")

        self._build_all_formats_tab(all_frame)
        self._build_video_tab(video_frame)
        self._build_audio_tab(audio_frame)
        self._build_preset_tab(preset_frame)
        self._build_summary_tab(summary_frame)

        btn_bar = ttk.Frame(self.dialog)
        btn_bar.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(btn_bar, text="生成组合并确定", command=self._confirm_batch, width=16).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_bar, text="仅当前单选确定", command=self._confirm_single, width=14).pack(side=tk.RIGHT)
        ttk.Button(btn_bar, text="取消", command=self.on_cancel, width=10).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_bar, text="清空选择", command=self._clear_all).pack(side=tk.LEFT)

        self.selection_label = ttk.Label(
            btn_bar,
            text="提示：可在“视频格式”与“音频格式”标签页多选 → 再点击“生成组合并确定”",
            foreground="blue"
        )
        self.selection_label.pack(side=tk.LEFT, padx=12)

    # -------------- 标签页构造 --------------
    def _build_all_formats_tab(self, parent):
        bar = ttk.Frame(parent)
        bar.pack(fill=tk.X, pady=5, padx=5)
        ttk.Label(bar, text="所有格式（完整/仅视频/仅音频）单击即单格式选择", foreground="gray").pack(side=tk.LEFT)

        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', lambda *_: self._filter_all())
        ttk.Entry(bar, textvariable=self.search_var, width=28).pack(side=tk.RIGHT)

        columns = ("format_id", "ext", "resolution", "fps", "vcodec", "acodec",
                   "vbr", "abr", "filesize", "note")
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        sy = ttk.Scrollbar(frame)
        sy.pack(side=tk.RIGHT, fill=tk.Y)
        sx = ttk.Scrollbar(frame, orient=tk.HORIZONTAL)
        sx.pack(side=tk.BOTTOM, fill=tk.X)

        self.all_tree = ttk.Treeview(
            frame, columns=columns, show="headings",
            yscrollcommand=sy.set, xscrollcommand=sx.set, selectmode="browse"
        )
        sy.config(command=self.all_tree.yview)
        sx.config(command=self.all_tree.xview)

        heads = {
            "format_id": "格式ID", "ext": "扩展名", "resolution": "分辨率", "fps": "帧率",
            "vcodec": "视频编码", "acodec": "音频编码", "vbr": "视频码率", "abr": "音频码率",
            "filesize": "大小", "note": "备注"
        }
        widths = {"format_id": 80, "ext": 70, "resolution": 100, "fps": 60,
                  "vcodec": 120, "acodec": 120, "vbr": 90, "abr": 90, "filesize": 100, "note": 280}
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
        ttk.Label(
            parent,
            text="可 Ctrl/Shift 多选视频流；切换到“音频格式”后继续多选音频流。",
            foreground="gray"
        ).pack(anchor=tk.W, pady=5, padx=5)

        cols = ("format_id", "ext", "resolution", "fps", "vcodec", "vbr", "filesize", "note")
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        sy = ttk.Scrollbar(frame)
        sy.pack(side=tk.RIGHT, fill=tk.Y)
        sx = ttk.Scrollbar(frame, orient=tk.HORIZONTAL)
        sx.pack(side=tk.BOTTOM, fill=tk.X)

        self.video_tree = ttk.Treeview(
            frame, columns=cols, show="headings",
            yscrollcommand=sy.set, xscrollcommand=sx.set, selectmode="extended"
        )
        sy.config(command=self.video_tree.yview)
        sx.config(command=self.video_tree.xview)

        heads = {"format_id": "格式ID", "ext": "扩展名", "resolution": "分辨率",
                 "fps": "帧率", "vcodec": "视频编码", "vbr": "码率", "filesize": "大小", "note": "备注"}
        widths = {"format_id": 90, "ext": 70, "resolution": 110, "fps": 60,
                  "vcodec": 140, "vbr": 90, "filesize": 110, "note": 300}
        for k in cols:
            self.video_tree.heading(k, text=heads[k])
            self.video_tree.column(k, width=widths[k], anchor=tk.W)
        self.video_tree.pack(fill=tk.BOTH, expand=True)

        v_formats = [f for f in self.formats if f.get('vcodec', 'none') != 'none' and f.get('acodec', 'none') == 'none']
        for fmt in v_formats:
            vals = self._row_from_format(fmt, include_acodec=False)
            self.video_tree.insert("", tk.END, values=vals, tags=(vals[0],))

        # 多选事件增强：Select + 鼠标释放都刷新
        self.video_tree.bind("<<TreeviewSelect>>", self._on_video_multi)
        self.video_tree.bind("<ButtonRelease-1>", self._on_video_multi)

    def _build_audio_tab(self, parent):
        ttk.Label(
            parent,
            text="可 Ctrl/Shift 多选音频流；与已选视频交叉组合。",
            foreground="gray"
        ).pack(anchor=tk.W, pady=5, padx=5)

        cols = ("format_id", "ext", "acodec", "abr", "asr", "channels", "filesize", "note")
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        sy = ttk.Scrollbar(frame)
        sy.pack(side=tk.RIGHT, fill=tk.Y)
        sx = ttk.Scrollbar(frame, orient=tk.HORIZONTAL)
        sx.pack(side=tk.BOTTOM, fill=tk.X)

        self.audio_tree = ttk.Treeview(
            frame, columns=cols, show="headings",
            yscrollcommand=sy.set, xscrollcommand=sx.set, selectmode="extended"
        )
        sy.config(command=self.audio_tree.yview)
        sx.config(command=self.audio_tree.xview)

        heads = {"format_id": "格式ID", "ext": "扩展名", "acodec": "音频编码",
                 "abr": "比特率", "asr": "采样率", "channels": "声道",
                 "filesize": "大小", "note": "备注"}
        widths = {"format_id": 90, "ext": 70, "acodec": 130, "abr": 90,
                  "asr": 90, "channels": 70, "filesize": 110, "note": 300}
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
        ttk.Label(
            parent,
            text="推荐组合（单选）。若要多选批量，请用“视频格式”、“音频格式”页。",
            foreground="gray"
        ).pack(anchor=tk.W, pady=5, padx=5)

        cols = ("name", "format", "quality", "description")
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        sy = ttk.Scrollbar(frame)
        sy.pack(side=tk.RIGHT, fill=tk.Y)

        self.preset_tree = ttk.Treeview(
            frame, columns=cols, show="headings",
            yscrollcommand=sy.set, selectmode="browse"
        )
        sy.config(command=self.preset_tree.yview)

        heads = {"name": "名称", "format": "格式代码", "quality": "质量", "description": "说明"}
        widths = {"name": 180, "format": 380, "quality": 90, "description": 470}
        for k in cols:
            self.preset_tree.heading(k, text=heads[k])
            self.preset_tree.column(k, width=widths[k], anchor=tk.W)
        self.preset_tree.pack(fill=tk.BOTH, expand=True)

        presets = [
            ("最佳质量（推荐）", "bestvideo+bestaudio/best", "⭐⭐⭐⭐⭐", "最佳视频+最佳音频"),
            ("4K 超高清", "bestvideo[height<=2160]+bestaudio/best", "⭐⭐⭐⭐⭐", "2160p 视频+最佳音频"),
            ("2K", "bestvideo[height<=1440]+bestaudio/best", "⭐⭐⭐⭐", "1440p 视频+最佳音频"),
            ("1080p", "bestvideo[height<=1080]+bestaudio/best", "⭐⭐⭐⭐", "1080p 视频+最佳音频"),
            ("720p", "bestvideo[height<=720]+bestaudio/best", "⭐⭐⭐", "720p 视频+最佳音频"),
            ("优先 MP4", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best", "⭐⭐⭐⭐", "兼容性好"),
            ("优先 WEBM", "bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]/best", "⭐⭐⭐", "体积较小"),
            ("仅音频", "bestaudio/best", "⭐⭐⭐⭐⭐", "只下载音频"),
        ]
        for p in presets:
            self.preset_tree.insert("", tk.END, values=p, tags=(p[1],))
        self.preset_tree.bind("<<TreeviewSelect>>", self._on_preset_single)

    def _build_summary_tab(self, parent):
        ttk.Label(
            parent,
            text="组合预览：显示当前多选的视频与音频及其交叉组合（自动刷新）。",
            foreground="gray"
        ).pack(anchor=tk.W, pady=5, padx=5)

        self.summary_text = scrolledtext.ScrolledText(parent, height=22, wrap=tk.WORD, state=tk.DISABLED)
        self.summary_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        ttk.Button(parent, text="手动刷新", command=self._refresh_summary).pack(anchor=tk.E, padx=5, pady=5)

    # -------------- 事件与刷新 --------------
    def _on_tab_changed(self, event):
        current_tab = self.notebook.tab(self.notebook.select(), 'text')
        if "组合预览" in current_tab:
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

    # --- 单选（所有格式 / 预设） ---
    def _on_all_single(self, _):
        it = self.all_tree.selection()
        if not it:
            return
        vals = self.all_tree.item(it[0])['values']
        fid, ext, res, _, vcodec, acodec = vals[0], vals[1], vals[2], vals[3], vals[4], vals[5]
        if vcodec != "-" and acodec != "-":
            self.selected_format_code = str(fid)
            self.selection_label.config(text=f"单选完整格式: {fid} ({ext} {res})", foreground="green")
        elif vcodec != "-":
            self.selected_format_code = str(fid)
            self.selection_label.config(text=f"单选视频格式: {fid} ({ext} {res})", foreground="orange")
        elif acodec != "-":
            self.selected_format_code = str(fid)
            self.selection_label.config(text=f"单选音频格式: {fid} ({ext})", foreground="orange")

    def _on_preset_single(self, _):
        it = self.preset_tree.selection()
        if not it:
            return
        fmt_code = self.preset_tree.item(it[0])['values'][1]
        self.selected_format_code = fmt_code
        self.selection_label.config(text=f"预设单选: {fmt_code}", foreground="green")

    # --- 多选（视频 / 音频） ---
    def _on_video_multi(self, _):
        self.selected_video_ids = {
            str(self.video_tree.item(i)['values'][0]) for i in self.video_tree.selection()
        }
        self._update_combination_hint()

    def _on_audio_multi(self, _):
        self.selected_audio_ids = {
            str(self.audio_tree.item(i)['values'][0]) for i in self.audio_tree.selection()
        }
        self._update_combination_hint()

    def _update_combination_hint(self):
        v = len(self.selected_video_ids)
        a = len(self.selected_audio_ids)
        if v and a:
            self.selection_label.config(
                text=f"已多选 视频:{v} 音频:{a} → 组合数 {v * a}，可在“组合预览”查看或直接生成下载。",
                foreground="blue"
            )
        elif v:
            self.selection_label.config(text=f"已多选 视频:{v}（未选音频，将仅下载视频流）", foreground="orange")
        elif a:
            self.selection_label.config(text=f"已多选 音频:{a}（未选视频，将仅下载音频）", foreground="orange")
        else:
            self.selection_label.config(text="提示：可多选视频与音频生成组合", foreground="blue")
        # 自动刷新预览（即便当前不在该标签页）
        self._refresh_summary()

    def _refresh_summary(self):
        if not hasattr(self, 'summary_text'):
            return
        self.summary_text.config(state=tk.NORMAL)
        self.summary_text.delete(1.0, tk.END)
        v_ids = sorted(self.selected_video_ids)
        a_ids = sorted(self.selected_audio_ids)
        self.summary_text.insert(tk.END, "=== 当前选择概览 ===\n")
        if v_ids:
            self.summary_text.insert(tk.END, f"视频格式ID ({len(v_ids)}): {', '.join(v_ids)}\n")
        else:
            self.summary_text.insert(tk.END, "视频格式: 尚未选择\n")
        if a_ids:
            self.summary_text.insert(tk.END, f"音频格式ID ({len(a_ids)}): {', '.join(a_ids)}\n")
        else:
            self.summary_text.insert(tk.END, "音频格式: 尚未选择\n")

        if v_ids and a_ids:
            total = len(v_ids) * len(a_ids)
            self.summary_text.insert(tk.END, f"\n交叉组合（总 {total}）：(最多显示前 25 条)\n")
            for idx, (vid, aid) in enumerate(product(v_ids, a_ids), 1):
                if idx > 25:
                    self.summary_text.insert(tk.END, "... (更多组合未列出)\n")
                    break
                self.summary_text.insert(tk.END, f"  {vid}+{aid}\n")
        else:
            self.summary_text.insert(tk.END, "\n尚未形成视频+音频交叉组合。\n"
                                             "如果只选了视频或只选了音频，将逐个单独下载。\n")
        self.summary_text.config(state=tk.DISABLED)

    def _clear_all(self):
        self.selected_format_code = None
        self.selected_video_ids.clear()
        self.selected_audio_ids.clear()
        for tree in (self.video_tree, self.audio_tree, self.all_tree, self.preset_tree):
            tree.selection_remove(*tree.selection())
        self.selection_label.config(text="已清空选择。", foreground="blue")
        self._refresh_summary()

    # -------------- 确认返回 --------------
    def _confirm_single(self):
        if not self.selected_format_code:
            messagebox.showwarning("提示", "当前未单选任何格式或预设")
            return
        self.result = self.selected_format_code
        self.dialog.destroy()

    def _confirm_batch(self):
        if self.selected_format_code and not (self.selected_video_ids or self.selected_audio_ids):
            # 单格式优先
            self.result = self.selected_format_code
            self.dialog.destroy()
            return
        videos = sorted(self.selected_video_ids)
        audios = sorted(self.selected_audio_ids)
        if not videos and not audios:
            messagebox.showwarning("提示", "还没有选择任何视频或音频用于批量下载")
            return
        self.result = {'videos': videos, 'audios': audios}
        # 确认前最后刷新一次，方便用户看到最终组合
        self._refresh_summary()
        self.dialog.destroy()

    def on_cancel(self):
        self.result = None
        self.dialog.destroy()


# ---------------- 下面保持之前的主 GUI（只加对多选结果的处理） ----------------
class YtDlpGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("yt-dlp 视频下载器 (多选批量 & EJS 支持)")
        self.root.geometry("940x760")
        self.root.resizable(True, True)

        self.is_downloading = False
        self.cancel_requested = False

        self.cookie_file_path = tk.StringVar()
        self.browser_var = tk.StringVar(value="none")

        self.enable_ejs_var = tk.BooleanVar(value=True)
        self.runtime_choice_var = tk.StringVar(value="auto")
        self.runtime_path_var = tk.StringVar()

        self.current_video_info = None
        self.batch_formats = []

        self._build_ui()
        self.output_path.set(str(Path.home() / "Downloads"))
        self._check_environment()

    def _build_ui(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        basic = ttk.Frame(notebook, padding=10)
        adv = ttk.Frame(notebook, padding=10)
        notebook.add(basic, text="基本设置")
        notebook.add(adv, text="高级设置（Cookie / EJS / Runtime）")
        basic.columnconfigure(1, weight=1)
        adv.columnconfigure(1, weight=1)
        self._build_basic_tab(basic)
        self._build_adv_tab(adv)
        self._build_bottom()

    def _build_basic_tab(self, parent):
        url_row = ttk.Frame(parent)
        url_row.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)
        url_row.columnconfigure(1, weight=1)
        ttk.Label(url_row, text="视频 URL:", font=("", 10, "bold")).grid(row=0, column=0, sticky=tk.W)
        self.url_var = tk.StringVar()
        ttk.Entry(url_row, textvariable=self.url_var).grid(row=0, column=1, sticky="ew", padx=6)
        self.parse_btn = ttk.Button(url_row, text="🔍 解析格式", command=self.parse_formats, width=14)
        self.parse_btn.grid(row=0, column=2, padx=6)

        ttk.Label(parent, text="输出目录:", font=("", 10, "bold")).grid(row=1, column=0, sticky=tk.W, pady=6)
        path_row = ttk.Frame(parent)
        path_row.grid(row=1, column=1, sticky="ew")
        path_row.columnconfigure(0, weight=1)
        self.output_path = tk.StringVar()
        ttk.Entry(path_row, textvariable=self.output_path).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(path_row, text="浏览...", command=self.browse_folder).grid(row=0, column=1)

        fmt_box = ttk.LabelFrame(parent, text="单格式（非批量）表达式", padding=10)
        fmt_box.grid(row=2, column=0, columnspan=2, sticky="ew", pady=10)
        fmt_box.columnconfigure(1, weight=1)
        ttk.Label(fmt_box, text="快速选择:").grid(row=0, column=0, sticky=tk.W)
        self.format_var = tk.StringVar(value="bestvideo+bestaudio/best - 最佳质量（推荐）")
        cb = ttk.Combobox(fmt_box, textvariable=self.format_var, state="readonly", width=42)
        cb['values'] = (
            'bestvideo+bestaudio/best - 最佳质量（推荐）',
            'best - 最佳完整格式',
            'bestaudio/best - 仅音频（最佳）',
            'bestvideo[height<=1080]+bestaudio/best - 1080p',
            'bestvideo[height<=720]+bestaudio/best - 720p',
            'custom - 自定义（解析选择/手写表达式）'
        )
        cb.grid(row=0, column=1, sticky=tk.W, padx=6)
        ttk.Label(fmt_box, text="自定义格式:").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.custom_format_var = tk.StringVar()
        ttk.Entry(fmt_box, textvariable=self.custom_format_var, width=45).grid(row=1, column=1, sticky=tk.W, padx=6)
        ttk.Label(fmt_box,
                  text="如果使用多选批量，请在解析对话框选择；这里的表达式仅用于单次下载。",
                  foreground="blue").grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=4)

        opt = ttk.LabelFrame(parent, text="其他选项", padding=10)
        opt.grid(row=3, column=0, columnspan=2, sticky="ew", pady=10)
        self.extract_audio = tk.BooleanVar(value=False)
        ttk.Checkbutton(opt, text="仅提取音频（MP3）", variable=self.extract_audio).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.embed_subs = tk.BooleanVar(value=False)
        ttk.Checkbutton(opt, text="嵌入字幕", variable=self.embed_subs).grid(row=1, column=0, sticky=tk.W, pady=2)

        info = ttk.LabelFrame(parent, text="使用说明", padding=10)
        info.grid(row=4, column=0, columnspan=2, sticky="ew", pady=10)
        text = (
            "1. 输入 URL → “解析格式”\n"
            "2. 弹窗中多选视频与音频 → 生成批量组合，或单选预设 / 完整格式\n"
            "3. 返回后点击“开始下载”\n"
            "4. 批量时将逐个组合下载\n"
        )
        ttk.Label(info, text=text, justify=tk.LEFT, foreground="gray").pack(anchor=tk.W)

    def _build_adv_tab(self, parent):
        cookie_box = ttk.LabelFrame(parent, text="Cookie 设置", padding=10)
        cookie_box.grid(row=0, column=0, columnspan=2, sticky="ew", pady=6)
        cookie_box.columnconfigure(1, weight=1)
        ttk.Label(cookie_box, text="Cookie 文件:").grid(row=0, column=0, sticky=tk.W)
        row = ttk.Frame(cookie_box)
        row.grid(row=0, column=1, sticky="ew", pady=3)
        row.columnconfigure(0, weight=1)
        ttk.Entry(row, textvariable=self.cookie_file_path).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(row, text="选择文件...", command=self.browse_cookie_file).grid(row=0, column=1)
        ttk.Button(row, text="清除", command=self.clear_cookie).grid(row=0, column=2, padx=(6, 0))
        self.cookie_status_label = ttk.Label(cookie_box, text="未设置 Cookie", foreground="gray")
        self.cookie_status_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(4, 0))

        browser_box = ttk.LabelFrame(parent, text="浏览器 Cookie（自动）", padding=10)
        browser_box.grid(row=1, column=0, columnspan=2, sticky="ew", pady=6)
        browser_box.columnconfigure(1, weight=1)
        ttk.Label(browser_box, text="浏览器:").grid(row=0, column=0, sticky=tk.W)
        cb = ttk.Combobox(browser_box, textvariable=self.browser_var, state="readonly", width=30)
        cb['values'] = (
            'none - 不使用浏览器 Cookie',
            'chrome - Google Chrome',
            'firefox - Mozilla Firefox',
            'edge - Microsoft Edge',
            'safari - Safari',
            'opera - Opera',
            'brave - Brave'
        )
        cb.grid(row=0, column=1, sticky=tk.W, padx=6)

        ejs_box = ttk.LabelFrame(parent, text="高级格式(EJS)与 JS Runtime", padding=10)
        ejs_box.grid(row=2, column=0, columnspan=2, sticky="ew", pady=6)
        ejs_box.columnconfigure(1, weight=1)
        ttk.Checkbutton(ejs_box, text="启用高级格式 (EJS)", variable=self.enable_ejs_var).grid(row=0, column=0, columnspan=2, sticky=tk.W)
        ttk.Label(ejs_box, text="Runtime:").grid(row=1, column=0, sticky=tk.W)
        runtime_cb = ttk.Combobox(ejs_box, textvariable=self.runtime_choice_var, state="readonly", width=18)
        runtime_cb['values'] = ('auto', 'deno', 'node', 'bun', 'quickjs')
        runtime_cb.grid(row=1, column=1, sticky=tk.W, padx=6)
        ttk.Label(ejs_box, text="Runtime 路径（留空自动）:").grid(row=2, column=0, sticky=tk.W)
        ttk.Entry(ejs_box, textvariable=self.runtime_path_var, width=40).grid(row=2, column=1, sticky=tk.W, padx=6)

    def _build_bottom(self):
        area = ttk.Frame(self.root)
        area.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        btns = ttk.Frame(area)
        btns.pack(pady=6)
        self.download_btn = ttk.Button(btns, text="开始下载", command=self.start_download, width=16)
        self.download_btn.grid(row=0, column=0, padx=6)
        self.cancel_btn = ttk.Button(btns, text="取消", command=self.cancel_download, state=tk.DISABLED, width=16)
        self.cancel_btn.grid(row=0, column=1, padx=6)
        ttk.Button(btns, text="清除日志", command=self.clear_log, width=16).grid(row=0, column=2, padx=6)

        pbox = ttk.LabelFrame(area, text="下载进度", padding=8)
        pbox.pack(fill=tk.X, pady=6)
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(pbox, variable=self.progress_var, maximum=100, mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=6)
        self.status_label = ttk.Label(pbox, text="就绪", foreground="green")
        self.status_label.pack(anchor=tk.W)

        lbox = ttk.LabelFrame(area, text="日志", padding=6)
        lbox.pack(fill=tk.BOTH, expand=True, pady=6)
        self.log_text = scrolledtext.ScrolledText(lbox, height=14, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        for tag, color in {
            "info": "blue",
            "warning": "orange",
            "error": "red",
            "success": "green",
            "runtime": "#8844cc",
            "ejs": "#00695c",
            "batch": "#795548",
        }.items():
            self.log_text.tag_config(tag, foreground=color)

    # ---------- 环境 ----------
    def _check_environment(self):
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            self.log_message("未检测到 ffmpeg：分离流合并/音频提取可能失败。", "warning")
        else:
            self.log_message(f"检测到 ffmpeg: {ffmpeg}", "success")
        if HAVE_EJS:
            self.log_message("检测到 yt-dlp-ejs：可解析高阶格式。", "ejs")
        else:
            self.log_message("未检测到 yt-dlp-ejs：将使用远程脚本 (ejs:github)（若启用）。", "ejs")

    # ---------- 基本工具 ----------
    def log_message(self, msg, tag="info"):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{msg}\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def update_status(self, msg, color="black"):
        self.status_label.config(text=msg, foreground=color)

    def clear_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

    def browse_folder(self):
        folder = filedialog.askdirectory(title="选择输出目录", initialdir=self.output_path.get() or str(Path.home()))
        if folder:
            self.output_path.set(folder)

    def browse_cookie_file(self):
        fp = filedialog.askopenfilename(title="选择 Cookie 文件", filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")])
        if fp:
            self.cookie_file_path.set(fp)
            self._update_cookie_status(True)
            self.log_message(f"✓ 已加载 Cookie 文件: {os.path.basename(fp)}", "success")

    def clear_cookie(self):
        self.cookie_file_path.set("")
        self.browser_var.set("none")
        self._update_cookie_status(False)
        self.log_message("已清除 Cookie 设置", "info")

    def _update_cookie_status(self, has_cookie):
        if has_cookie:
            self.cookie_status_label.config(text="✓ Cookie 已设置", foreground="green")
        else:
            self.cookie_status_label.config(text="未设置 Cookie", foreground="gray")

    def get_browser_name(self):
        raw = (self.browser_var.get() or "none")
        name = raw.split(' - ')[0] if ' - ' in raw else raw
        return None if name == "none" else name

    # ---------- EJS ----------
    def _augment_ejs_options(self, opts):
        if not self.enable_ejs_var.get():
            return opts
        if not HAVE_EJS:
            rc = opts.setdefault('remote_components', [])
            if 'ejs:github' not in rc:
                rc.append('ejs:github')
            self.log_message("EJS: 启用远程组件 ejs:github", "ejs")
        runtime_choice = self.runtime_choice_var.get().lower()
        runtime_path = (self.runtime_path_var.get() or "").strip()
        if runtime_choice != "auto":
            jr = opts.setdefault('js_runtimes', {})
            jr[runtime_choice] = {'path': runtime_path} if runtime_path else {}
            self.log_message(f"Runtime: {runtime_choice} {'-> ' + runtime_path if runtime_path else '(PATH 查找)'}", "runtime")
        else:
            self.log_message("Runtime: auto", "runtime")
        return opts

    # ---------- 解析 ----------
    def parse_formats(self):
        url = (self.url_var.get() or "").strip()
        if not url:
            messagebox.showwarning("警告", "请输入 URL")
            return
        self.parse_btn.config(state=tk.DISABLED, text="解析中...")
        self.update_status("解析中...", "blue")
        self.log_message(f"开始解析: {url}", "info")
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
                self._ui_error("无法获取视频信息")
                return
            formats = info.get('formats') or []
            self.current_video_info = info
            self.log_message(f"✓ 标题: {info.get('title', 'Unknown')}", "success")
            self.log_message(f"✓ 格式数: {len(formats)}", "success")
            if not formats:
                self._ui_error("未解析到格式。可能需要登录或启用 EJS/Runtime。")
                return
            has_high = any((f.get('height') or 0) >= 1440 for f in formats)
            if not has_high and self.enable_ejs_var.get():
                self.log_message("⚠ 未出现 1440p+，可能 JS Runtime 未正常运行。", "warning")
            self.root.after(0, lambda: self._open_selector(formats, info))
        except Exception as e:
            import traceback
            self.log_message(f"解析失败: {e}", "error")
            self.log_message(traceback.format_exc(), "error")
            self._ui_error(f"解析失败：{e}")
        finally:
            self.root.after(0, lambda: self.parse_btn.config(state=tk.NORMAL, text="🔍 解析格式"))
            self.root.after(0, lambda: self.update_status("就绪", "green"))

    def _open_selector(self, formats, info):
        dlg = FormatSelectorDialog(self.root, formats, info)
        self.root.wait_window(dlg.dialog)
        if dlg.result is None:
            self.log_message("取消选择", "warning")
            return
        if isinstance(dlg.result, str):
            self.custom_format_var.set(dlg.result)
            self.format_var.set("custom - 单格式")
            self.batch_formats = []
            self.log_message(f"单格式准备下载: {dlg.result}", "success")
        else:
            videos = dlg.result.get('videos', [])
            audios = dlg.result.get('audios', [])
            self.batch_formats = self._expand_batch(videos, audios)
            if not self.batch_formats:
                single_list = videos or audios
                self.batch_formats = single_list[:]
                self.log_message(f"批量选择为单类，共 {len(self.batch_formats)} 条", "batch")
            else:
                self.log_message(f"批量组合数: {len(self.batch_formats)}", "batch")
            self.custom_format_var.set("")
            self.format_var.set("custom - 批量模式")

    def _expand_batch(self, videos, audios):
        if videos and audios:
            return [f"{v}+{a}" for v, a in product(videos, audios)]
        return videos or audios or []

    # ---------- 下载 ----------
    def start_download(self):
        if self.is_downloading:
            return
        url = (self.url_var.get() or "").strip()
        if not url:
            messagebox.showwarning("警告", "请输入 URL")
            return
        outdir = (self.output_path.get() or "").strip()
        if not outdir or not os.path.isdir(outdir):
            messagebox.showerror("错误", "输出目录无效")
            return

        self.is_downloading = True
        self.cancel_requested = False
        self.download_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.progress_var.set(0)

        if self.batch_formats:
            self.update_status("批量下载开始...", "blue")
            self.log_message(f"开始批量下载，共 {len(self.batch_formats)} 组格式", "batch")
            threading.Thread(target=self._batch_download_worker, args=(url, outdir), daemon=True).start()
        else:
            fmt = self._get_single_format()
            self.update_status("单格式下载开始...", "blue")
            self.log_message(f"单格式下载: {fmt}", "info")
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
            self.log_message(f"✓ 下载完成: {info.get('title', 'Unknown')}", "success")
            self.update_status("下载完成", "green")
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
                self.log_message("用户取消批量下载，停止。", "warning")
                break
            self.update_status(f"批量 {idx}/{total}: {fmt}", "blue")
            self.log_message(f"[{idx}/{total}] 下载格式: {fmt}", "batch")
            try:
                opts = self._common_ydl_opts(outdir, fmt)
                with YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                self.log_message(f"[{idx}/{total}] ✓ 成功: {info.get('title', 'Unknown')}", "success")
                success_count += 1
            except Exception as e:
                self.log_message(f"[{idx}/{total}] ✗ 失败: {e}", "error")
                self._handle_download_error(e, silent=True)
        self.log_message(f"批量结束：成功 {success_count}/{total}", "batch")
        self.update_status("批量结束", "green")
        self.is_downloading = False
        self.root.after(0, self._reset_buttons)

    def _handle_download_error(self, e, silent=False):
        msg = str(e)
        if not silent:
            self.log_message(f"下载失败: {msg}", "error")
            self.update_status("下载失败", "red")
        lower = msg.lower()
        if "login" in lower or "member" in lower or "premium" in lower:
            self.log_message("⚠ 可能需要登录或会员，请配置 Cookie。", "warning")
        if "ffmpeg" in lower:
            self.log_message("⚠ 合并失败：请确认已安装 ffmpeg。", "warning")
        if "challenge" in lower or "signature" in lower:
            self.log_message("⚠ EJS 解析可能失败：请确认 yt-dlp-ejs 或 Runtime 设置。", "warning")

    def cancel_download(self):
        if self.is_downloading:
            self.cancel_requested = True
            self.log_message("已请求取消（当前项完成后停止）", "warning")
            self.update_status("取消中...", "orange")

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
            self.update_status(f"下载中... {self.progress_var.get():.1f}% | 速度: {spd_str} | 剩余: {eta_str}", "blue")
        elif d['status'] == 'finished':
            self.progress_var.set(100)
            self.update_status("已下载，后处理...", "green")

    def _reset_buttons(self):
        self.download_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)
        # 不自动清空 batch_formats，方便用户重复下载；如需清空可自行选择：
        # self.batch_formats = []

    def _ui_error(self, msg):
        self.root.after(0, lambda: messagebox.showerror("错误", msg))


def main():
    root = tk.Tk()
    app = YtDlpGUI(root)
    root.update_idletasks()
    w, h = root.winfo_width(), root.winfo_height()
    x = (root.winfo_screenwidth() - w) // 2
    y = (root.winfo_screenheight() - h) // 2
    root.geometry(f"{w}x{h}+{x}+{y}")
    root.mainloop()


if __name__ == "__main__":
    main()