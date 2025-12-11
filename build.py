#!/usr/bin/env python3
"""
Nuitka 构建脚本（适用于本地与 GitHub Actions）
- 入口文件：yt_dlp_gui.py
- 模式：standalone（非 onefile）
- 优化：LTO + -OO + 排除不必要模块
"""

import subprocess
import sys
import shutil
from pathlib import Path
import os

APP_NAME = "yt-dlp-gui"
ENTRY = "yt_dlp_gui.py"
VERSION = "0.1.0"  # 可按需同步 pyproject.toml

# 排除不需要的标准库模块（减小体积）
EXCLUDED_MODULES = [
    # 测试/开发相关
    "unittest",
    "pydoc",
    "doctest",
    "tkinter.test",
    "idlelib",
    "lib2to3",
    "test",
    "distutils",
    "setuptools",
    "pip",
    "ensurepip",
    "venv",
    # 网络/协议相关（yt-dlp 自带处理）
    "xmlrpc",
    "ftplib",
    "poplib",
    "imaplib",
    "smtplib",
    "nntplib",
    "telnetlib",
    "cgi",
    "cgitb",
    # 数据库相关（未使用）
    "sqlite3",
    "dbm",
    # 多进程相关（只用 threading）
    "multiprocessing",
    "concurrent",
    # 调试/分析相关
    "pdb",
    "profile",
    "cProfile",
    "pstats",
    "timeit",
    "trace",
    # 其他未使用的模块
    "curses",
    "turtle",
    "turtledemo",
    "antigravity",
    "this",
    "pty",
    "tty",
    "mailbox",
    "mimetypes",
    "audioop",
    "aifc",
    "sunau",
    "wave",
    "chunk",
    "sndhdr",
    "ossaudiodev",
    "crypt",
    "spwd",
    "grp",
    "termios",
    "readline",
    "rlcompleter",
    "xdrlib",
    "pipes",
    "mailcap",
]

# 排除 yt_dlp 中不需要的大型依赖
EXCLUDED_YTDLP = [
    "yt_dlp.extractor.lazy_extractors",
]

# 编译时内存占用过大的模块，不跟踪导入（保持运行时动态导入）
NOFOLLOW_HEAVY = [
    "customtkinter.windows",
]


def run(cmd: list[str], env: dict | None = None) -> bool:
    print(">>>", " ".join(cmd))
    return subprocess.run(cmd, env=env).returncode == 0


def ensure_clean() -> None:
    for p in ("build", f"{APP_NAME}.dist", f"{APP_NAME}.build"):
        path = Path(p)
        if path.exists():
            print(f"[clean] removing {path}")
            shutil.rmtree(path, ignore_errors=True)


def build() -> bool:
    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--enable-plugin=tk-inter",
        "--lto=yes",
        "--python-flag=-OO",
        "--assume-yes-for-downloads",
        "--remove-output",
        "--output-dir=build",
        "--output-filename=yt-dlp-gui.exe",
        "--windows-console-mode=disable",
        f"--company-name={APP_NAME}",
        f"--product-name={APP_NAME}",
        f"--product-version={VERSION}",
        f"--file-version={VERSION}",
        "--include-package=yt_dlp",
        # 使用 MSVC 编译器（比 MinGW 内存管理更好）
        "--clang",
        "--msvc=latest",
    ]

    # 排除不需要的模块以减小体积
    for mod in EXCLUDED_MODULES:
        cmd.append(f"--nofollow-import-to={mod}")
    for mod in EXCLUDED_YTDLP:
        cmd.append(f"--nofollow-import-to={mod}")
    # 不编译内存占用过大的模块（保持运行时动态导入）
    for mod in NOFOLLOW_HEAVY:
        cmd.append(f"--nofollow-import-to={mod}")

    icon_path = Path("asset/icon/icon.ico")
    if icon_path.exists():
        cmd.append(f"--windows-icon-from-ico={icon_path}")

    # 入口文件必须放最后
    cmd.append(ENTRY)

    env = os.environ.copy()
    # 跳过编译体积巨大的 yt_dlp.extractor.lazy_extractors，改用非 lazy 提取器路径
    env.setdefault("YTDLP_NO_LAZY_EXTRACTORS", "1")

    return run(cmd, env=env)


def main() -> int:
    print("=" * 60)
    print("Building yt-dlp GUI with Nuitka (LTO + -OO, standalone)")
    print("=" * 60)
    ensure_clean()
    ok = build()
    if ok:
        print("\n[OK] Build finished.")
        print("  可执行文件: build/yt-dlp-gui.dist/yt-dlp-gui.exe")
    else:
        print("\n[ERROR] Build failed.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
