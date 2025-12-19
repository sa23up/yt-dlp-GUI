; Inno Setup Script for yt-dlp-gui (Nuitka standalone dist)
; 说明：
; - 该脚本默认打包 `build\yt_dlp_gui.dist\` 目录
; - 在 GitHub Actions 中通过 /DMyAppVersion=... 传入版本号

#ifndef MyAppName
#define MyAppName "yt-dlp-gui"
#endif

#ifndef MyAppExeName
#define MyAppExeName "yt-dlp-gui.exe"
#endif

#ifndef MyAppPublisher
; 与 build.ps1 中的 company-name/product-name 保持一致（默认使用 MyAppName）
#define MyAppPublisher MyAppName
#endif

#ifndef MyAppURL
#define MyAppURL "https://github.com/un4gt/yt-dlp-GUI"
#endif

#ifndef MyAppVersion
#define MyAppVersion "0.1.0"
#endif

; dist 目录路径（相对本 .iss 文件）
#ifndef MyDistDir
#define MyDistDir "..\\build\\yt_dlp_gui.dist"
#endif

; 安装包输出目录（相对本 .iss 文件）
#ifndef MyOutputDir
#define MyOutputDir "..\\build"
#endif

; 安装包图标（可选）：与 build.ps1 的默认图标路径保持一致
#ifndef MySetupIconFile
#define MySetupIconFile "..\\asset\\icon\\icon.ico"
#endif

[Setup]
AppId={{A3F22D4A-21D0-4E8E-9E1A-0F7D39F7C7A3}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

OutputDir={#MyOutputDir}
OutputBaseFilename={#MyAppName}-{#MyAppVersion}-windows-setup

Compression=lzma2
SolidCompression=yes
WizardStyle=modern

#if FileExists(MySetupIconFile)
SetupIconFile={#MySetupIconFile}
#endif

PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
; 将 Nuitka 生成的整个 dist 目录打包进安装目录
Source: "{#MyDistDir}\\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
