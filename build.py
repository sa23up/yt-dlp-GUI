#!/usr/bin/env python3
"""
Nuitka 构建脚本（适用于本地与 GitHub Actions）
- 入口文件：yt_dlp_gui.py
- 模式：standalone（非 onefile）
- 优化：LTO + -OO + 排除不必要模块
- 输出：build/yt-dlp-gui.exe 与 build/yt-dlp-gui.msi（需 Nuitka 支持 --msi）
"""

import subprocess
import sys
import shutil
from pathlib import Path
import os

APP_NAME = "yt-dlp-gui"
ENTRY = "yt_dlp_gui.py"
VERSION = "0.1.0"  # 可按需同步 pyproject.toml
UPGRADE_GUID = "{8F8E4E14-3A7E-4D59-9C49-7F2E1F2C0A10}"

# 排除不需要的标准库模块（减小体积）
EXCLUDED_MODULES = [
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
]

# 排除 yt_dlp 中不需要的大型依赖
EXCLUDED_YTDLP = [
    "yt_dlp.extractor.lazy_extractors",
]


def run(cmd: list[str], env: dict | None = None) -> bool:
    print(">>>", " ".join(cmd))
    return subprocess.run(cmd, env=env).returncode == 0


def nuitka_supports_msi() -> bool:
    """检测当前 Nuitka 是否支持 --msi 参数。"""
    try:
        help_out = subprocess.check_output(
            [sys.executable, "-m", "nuitka", "--help"],
            text=True,
            errors="ignore",
        )
        return "--msi" in help_out
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] 无法检测 Nuitka 功能：{exc}")
        return False


def ensure_clean() -> None:
    for p in ("build", f"{APP_NAME}.dist", f"{APP_NAME}.build"):
        path = Path(p)
        if path.exists():
            print(f"[clean] removing {path}")
            shutil.rmtree(path, ignore_errors=True)


def build() -> bool:
    support_msi = nuitka_supports_msi()
    force_msi = os.getenv("FORCE_MSI", "").lower() in ("1", "true", "yes")
    if force_msi and not support_msi:
        print("[error] 当前 Nuitka 不支持 --msi；请升级 Nuitka 或取消 FORCE_MSI。")
        return False

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
        "--include-module=sv_ttk",
    ]

    # 排除不需要的模块以减小体积
    for mod in EXCLUDED_MODULES:
        cmd.append(f"--nofollow-import-to={mod}")
    for mod in EXCLUDED_YTDLP:
        cmd.append(f"--nofollow-import-to={mod}")

    # 可选：生成 MSI 安装包（仅当支持 --msi）
    if support_msi:
        cmd.append(f"--msi-upgrade-guid={UPGRADE_GUID}")
        cmd.append(f"--msi-version={VERSION}")
        cmd.append("--msi-display-name=yt-dlp GUI")
        cmd.append(f"--msi-name={APP_NAME}")
        cmd.append("--msi")
    else:
        print("[info] 当前 Nuitka 版本未提供 --msi，已跳过 MSI 打包。")

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
    print("Building yt-dlp GUI with Nuitka (LTO + -OO, standalone, MSI)")
    print("=" * 60)
    ensure_clean()
    ok = build()
    if ok:
        print("\n[OK] Build finished.")
        print("  可执行文件: build/yt-dlp-gui.exe")
        print("  安装包:     build/yt-dlp-gui.msi（需 Nuitka 支持 --msi）")
    else:
        print("\n[ERROR] Build failed.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
