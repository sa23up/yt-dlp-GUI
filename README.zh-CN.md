# yt-dlp-gui

[English](README.md) | **简体中文**

[yt-dlp](https://github.com/yt-dlp/yt-dlp) 的跨平台桌面图形界面,基于 Tauri 2 + Vue 3。内置打包 `yt-dlp`、`ffmpeg`、`deno`——装好即用,无需终端。

> 技术栈:Tauri 2 (Rust) · Vue 3 · Pinia · vue-i18n · naive-ui · tauri-specta

## 功能

- 一键 **最佳画质**,或手动挑选视频 + 音频格式
- 批量与播放列表下载(每行一个链接;播放列表页经 `--flat-playlist` 展开)
- 实时进度(速度 / 剩余时间 / 百分比),可取消
- 拖拽链接到窗口即可添加
- Cookie 认证(Firefox / Chrome / Edge,或手动 `cookies.txt`)
- 支持代理与限速
- 中英双语界面,明暗主题
- 队列重启后保留
- 内置 yt-dlp 更新器(SHA-256 校验),应用自身亦可自动更新

## 安装

从 [Releases](https://github.com/sa23up/yt-dlp-GUI/releases) 下载最新安装包:

- **Linux** —— `.deb` 或 `.AppImage`
- **Windows** —— `.msi` 或 `.exe`

不提供 macOS 版本(需要 Apple 开发者签名)。

## 开发

```bash
npm install
npm run tauri dev
```

`cargo test` 会经 tauri-specta 重新生成 `src/bindings.ts`——请提交生成结果。

## 构建

```bash
npm run tauri build
```

外部二进制(`yt-dlp`、`ffmpeg`、`deno`)的版本与 SHA-256 锁定在 `src-tauri/deps.json`,打包前需放在 `src-tauri/binaries/` 下(CI 会自动下载并校验)。

## 文档

- [`CONTEXT.md`](CONTEXT.md) —— 领域术语表
- [`docs/adr/`](docs/adr/) —— 架构决策记录
- [`SECURITY.md`](SECURITY.md) —— 安全策略

## 许可

[MIT](LICENSE)
