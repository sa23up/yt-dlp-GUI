# Repository build script (Nuitka)
# - 默认 Release：最高优化 + 清理调试符号
# - 编译模式：standalone / onefile

#requires -Version 5.1

[CmdletBinding()]
param(
    [ValidateSet('Release', 'Debug')]
    [string]$Configuration = 'Release',

    [string]$Entry = 'yt_dlp_gui.py',
    [string]$AppName = 'yt-dlp-gui',
    [string]$Version = '0.1.0',

	    [string]$OutputDir = 'build',
	    [string]$OutputFilename = 'yt-dlp-gui.exe',

	    [ValidateSet('standalone', 'onefile')]
	    [string]$Mode = 'standalone',

	    [ValidateSet('auto', 'msvc', 'clang')]
	    [string]$Toolchain = 'auto',

    [switch]$NoClean,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Command
    )

    Write-Host ("`n>>> {0}" -f ($Command -join ' '))
    if ($DryRun) {
        return
    }

    if ($Command.Count -lt 2) {
        & $Command[0]
    } else {
        & $Command[0] @($Command[1..($Command.Count - 1)])
    }

    if ($LASTEXITCODE -ne 0) {
        throw ("命令执行失败，退出码: {0}" -f $LASTEXITCODE)
    }
}

$repoRoot = $PSScriptRoot
Push-Location $repoRoot
try {
    if (-not (Test-Path -Path $Entry -PathType Leaf)) {
        throw ("入口文件不存在: {0}" -f $Entry)
    }

	    $entryBase = [System.IO.Path]::GetFileNameWithoutExtension($Entry)

	    if (-not $NoClean) {
	        $modeArtifacts = @()
	        if ($Mode -eq 'onefile') {
	            $modeArtifacts = @(
	                "$entryBase.onefile-build",
	                "$entryBase.onefile-dist",
	                "$AppName.onefile-build",
	                "$AppName.onefile-dist"
	            )
	        }

	        $cleanTargets = @(
	            $OutputDir,
	            "$entryBase.build",
	            "$entryBase.dist",
	            "$AppName.build",
	            "$AppName.dist"
	        ) + $modeArtifacts
	        $cleanTargets = $cleanTargets | Where-Object { $_ -and (Test-Path -Path $_) } | Sort-Object -Unique

	        foreach ($t in $cleanTargets) {
	            Write-Host "[clean] removing $t"
	            Remove-Item -Path $t -Recurse -Force
	        }
	    }

    # 排除不需要的标准库模块（减小体积）
    # 注意：对标准库做 --nofollow-import-to 过于激进会导致运行时缺模块（例如 yt_dlp 依赖 urllib.request -> mimetypes）。
    $excludedModules = @(
        'unittest', 'pydoc', 'doctest', 'tkinter.test', 'idlelib', 'lib2to3', 'test',
        'distutils', 'pip', 'ensurepip', 'venv'
    )

    # 排除 yt_dlp 中不需要的大型依赖
    $excludedYtDlp = @(
        'yt_dlp.extractor.lazy_extractors'
    )

	    # 预留：编译时内存占用过大的模块可在此加入 nofollow 列表
	    # 注意：对 GUI 依赖（如 customtkinter）使用 nofollow 可能导致运行时报缺模块
	    $noFollowHeavy = @()

	    $modeArg = if ($Mode -eq 'onefile') { '--mode=onefile' } else { '--standalone' }

	    $nuitkaArgs = @(
	        $modeArg,
	        '--enable-plugins=tk-inter',
	        '--assume-yes-for-downloads',
	        '--remove-output',
        "--output-dir=$OutputDir",
        "--output-filename=$OutputFilename",
        '--windows-console-mode=disable',
        "--company-name=$AppName",
        "--product-name=$AppName",
        "--product-version=$Version",
        "--file-version=$Version",
        '--include-package=yt_dlp',
        '--include-package=customtkinter',
        # 优先使用 MSVC 工具链；如安装了 VS Clang 组件可用 clang 加速/降内存
        '--msvc=latest'
    )

    if ($Configuration -eq 'Release') {
        # 最高优化：LTO + -OO（去 docstring + 去 assert）
        $nuitkaArgs += @('--lto=yes', '--python-flag=-OO')
    } else {
        # Debug：保留调试信息（更利于调试器交互）
        $nuitkaArgs += @('--unstripped')
    }

    foreach ($m in $excludedModules) { $nuitkaArgs += "--nofollow-import-to=$m" }
    foreach ($m in $excludedYtDlp) { $nuitkaArgs += "--nofollow-import-to=$m" }
    foreach ($m in $noFollowHeavy) { $nuitkaArgs += "--nofollow-import-to=$m" }

    $clangCl = $null
    $clangFromPath = Get-Command clang-cl -ErrorAction SilentlyContinue
	    if ($clangFromPath) {
	        $clangCl = $clangFromPath.Source
	    } else {
	        $vsLlvmDirs = @(
	            (Join-Path $env:ProgramFiles 'Microsoft Visual Studio\2022\Community\VC\Tools\Llvm\x64\bin')
	            (Join-Path $env:ProgramFiles 'Microsoft Visual Studio\2022\Professional\VC\Tools\Llvm\x64\bin')
	            (Join-Path $env:ProgramFiles 'Microsoft Visual Studio\2022\Enterprise\VC\Tools\Llvm\x64\bin')
	            (Join-Path $env:ProgramFiles 'Microsoft Visual Studio\2022\BuildTools\VC\Tools\Llvm\x64\bin')
	            (Join-Path $env:ProgramFiles 'LLVM\bin')
	        ) | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Container) }

	        foreach ($dir in $vsLlvmDirs) {
	            $candidate = Join-Path $dir 'clang-cl.exe'
            if (Test-Path -LiteralPath $candidate -PathType Leaf) {
                $clangCl = $candidate
                break
            }
        }
    }

    if ($Toolchain -eq 'clang') {
        if (-not $clangCl) {
            throw '已指定 -Toolchain clang，但未检测到 clang-cl.exe。请在 Visual Studio Installer 中安装 "C++ Clang tools for Windows/LLVM (clang-cl)" 组件，或改用 -Toolchain msvc。'
        }
        $nuitkaArgs += '--clang'
    } elseif ($Toolchain -eq 'auto') {
        if ($clangCl) {
            $nuitkaArgs += '--clang'
        } else {
            Write-Warning "未检测到 Visual Studio Clang 组件，将使用 MSVC (cl.exe) 编译。若仍失败，请在 VS Installer 安装 Windows SDK（Windows 10/11 SDK）。"
        }
    }

    $programFilesX86 = ${env:ProgramFiles(x86)}
    $hasWindowsSdk = $false
    if ($programFilesX86) {
        $hasWindowsSdk = (Test-Path -LiteralPath (Join-Path $programFilesX86 'Windows Kits\10\Include') -PathType Container) -or
                         (Test-Path -LiteralPath (Join-Path $programFilesX86 'Windows Kits\11\Include') -PathType Container)
    }
    if (-not $hasWindowsSdk) {
        Write-Warning "未检测到 Windows SDK（Windows Kits）。如果编译报错找不到 Windows 头文件/库，请在 VS Installer 安装 Windows 10/11 SDK。"
    }

    $iconPath = Join-Path $repoRoot 'asset/icon/icon.ico'
    if (Test-Path -Path $iconPath -PathType Leaf) {
        $nuitkaArgs += "--windows-icon-from-ico=$iconPath"
    }

    # 优先使用 uv（与 uv.lock/pyproject.toml 对齐）；没有 uv 则回退到 python
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        $runner = @('uv', 'run', 'python')
    } else {
        $runner = @('python')
    }

    $cmd = $runner + @('-m', 'nuitka') + $nuitkaArgs + @($Entry)

    $oldYtdlp = $env:YTDLP_NO_LAZY_EXTRACTORS
    $oldNoPyc = $env:PYTHONDONTWRITEBYTECODE
    $env:YTDLP_NO_LAZY_EXTRACTORS = '1'
    $env:PYTHONDONTWRITEBYTECODE = '1'
    try {
        Invoke-Checked -Command $cmd
    } finally {
        if ($null -eq $oldYtdlp) { Remove-Item env:YTDLP_NO_LAZY_EXTRACTORS -ErrorAction SilentlyContinue } else { $env:YTDLP_NO_LAZY_EXTRACTORS = $oldYtdlp }
        if ($null -eq $oldNoPyc) { Remove-Item env:PYTHONDONTWRITEBYTECODE -ErrorAction SilentlyContinue } else { $env:PYTHONDONTWRITEBYTECODE = $oldNoPyc }
    }

    if ($DryRun) {
        return
    }

    $exe = Get-ChildItem -Path $OutputDir -Recurse -File -Filter $OutputFilename -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $exe) {
        Write-Warning "未找到输出文件: $OutputDir/**/$OutputFilename（请查看 Nuitka 输出）"
    } else {
        Write-Host "[OK] Output: $($exe.FullName)"
    }

    if ($Configuration -eq 'Release') {
        # Release：删除调试符号相关产物（PDB/ILK），并尽力 strip（如果工具存在）
        Get-ChildItem -Path $OutputDir -Recurse -File -Filter '*.pdb' -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
        Get-ChildItem -Path $OutputDir -Recurse -File -Filter '*.ilk' -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

        $strip = Get-Command llvm-strip -ErrorAction SilentlyContinue
        if ($null -eq $strip) {
            $strip = Get-Command strip -ErrorAction SilentlyContinue
        }

        if ($strip -and $exe) {
            try {
                & $strip.Path '--strip-all' $exe.FullName | Out-Null
                Write-Host "[strip] $($strip.Name) --strip-all $($exe.Name)"
            } catch {
                Write-Warning "strip 失败（可忽略）: $($_.Exception.Message)"
            }
        }
    }
} finally {
    Pop-Location
}
