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
# 注意：对标准库做 --nofollow-import-to 过于激进会导致运行时缺模块（例如 yt_dlp 依赖 urllib.request -> mimetypes）。
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
    "pip",
    "ensurepip",
    "venv",
]

# 排除 yt_dlp 中不需要的大型依赖
EXCLUDED_YTDLP = [
    "yt_dlp.extractor.lazy_extractors",
]

# 编译时内存占用过大的模块，不跟踪导入（保持运行时动态导入）
NOFOLLOW_HEAVY = [
]

def find_clang_cl() -> str | None:
    clang_from_path = shutil.which("clang-cl")
    if clang_from_path:
        return clang_from_path

    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    candidates = [
        Path(program_files)
        / r"Microsoft Visual Studio\2022\Community\VC\Tools\Llvm\x64\bin\clang-cl.exe",
        Path(program_files)
        / r"Microsoft Visual Studio\2022\Professional\VC\Tools\Llvm\x64\bin\clang-cl.exe",
        Path(program_files)
        / r"Microsoft Visual Studio\2022\Enterprise\VC\Tools\Llvm\x64\bin\clang-cl.exe",
        Path(program_files)
        / r"Microsoft Visual Studio\2022\BuildTools\VC\Tools\Llvm\x64\bin\clang-cl.exe",
        Path(program_files) / r"LLVM\bin\clang-cl.exe",
    ]

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)

    return None


def has_windows_sdk() -> bool:
    program_files_x86 = os.environ.get("ProgramFiles(x86)")
    if not program_files_x86:
        return False

    return (Path(program_files_x86) / r"Windows Kits\10\Include").is_dir() or (
        Path(program_files_x86) / r"Windows Kits\11\Include"
    ).is_dir()


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
        "--enable-plugins=tk-inter",
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
        "--include-package=customtkinter",
        # 使用 MSVC 编译器（可选：安装 VS Clang 组件后可启用 clang-cl）
        "--msvc=latest",
    ]

    if find_clang_cl():
        cmd.append("--clang")
    else:
        print("[WARN] 未检测到 Visual Studio Clang 组件，将使用 MSVC (cl.exe) 编译。若失败，请在 VS Installer 安装 Windows SDK（Windows 10/11 SDK）。")
    if not has_windows_sdk():
        print("[WARN] 未检测到 Windows SDK（Windows Kits）。如果编译报错找不到 Windows 头文件/库，请在 VS Installer 安装 Windows 10/11 SDK。")

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
