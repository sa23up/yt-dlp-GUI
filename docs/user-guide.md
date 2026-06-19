# yt-dlp-gui 用户手册 / User Guide

本指南帮助你充分利用 yt-dlp-gui 的所有功能。/ This guide helps you make full use of yt-dlp-gui's features.

---

## 快速开始 / Quick Start

### 1. 基本下载 / Basic Download

1. 启动应用，粘贴 YouTube URL 到输入框
2. 按 `Enter` 或点击「获取格式」
3. 选择「最佳质量」或手动选择视频+音频格式
4. 点击「开始下载」

下载进度会实时显示，完成后会收到系统通知。

### 2. 批量下载 / Batch Download

粘贴多个 URL（每行一个）：
```
https://www.youtube.com/watch?v=abc123
https://www.youtube.com/watch?v=def456
https://www.youtube.com/watch?v=ghi789
```

应用会自动去重并加入队列，按设置的并发数同时下载。

### 3. 播放列表下载 / Playlist Download

粘贴播放列表 URL（包含 `/playlist` 或 `list=`）：
```
https://www.youtube.com/playlist?list=PLxxxxxx
```

应用会自动展开所有视频并加入队列（最多 200 个）。

---

## Cookie 认证 / Cookie Authentication

部分视频需要登录才能下载（年龄限制、私人视频、会员专属）。yt-dlp-gui 提供三种 Cookie 认证方式：

### 方式 1：Firefox 自动读取（推荐）

**状态**：✅ 最可靠，无需额外操作

1. 在设置页选择「Cookie 来源」→「Firefox」
2. 应用会自动从 Firefox 的 Cookie 数据库读取
3. Firefox 可以保持打开状态

**要求**：
- 已安装 Firefox 浏览器
- 已在 Firefox 中登录 YouTube

---

### 方式 2：Chrome / Edge 自动读取（实验性）

**状态**：⚠️ 需要关闭浏览器

1. **完全关闭** Chrome 或 Edge（包括后台进程）
   - Windows: 任务管理器确认无 `chrome.exe` / `msedge.exe`
   - Linux: `pkill chrome` 或 `pkill msedge`
2. 在设置页选择「Cookie 来源」→「Chrome」或「Edge」
3. 下载完成后可重新打开浏览器

**为什么需要关闭浏览器？**
Chromium 内核浏览器运行时会锁定 Cookie 数据库文件，yt-dlp 无法读取。Firefox 使用不同的锁机制，因此不受影响。

---

### 方式 3：手动导入 cookies.txt（终极兜底）

**状态**：✅ 适用于所有浏览器，包括 Safari / 移动浏览器

#### 步骤 1：导出 Cookie 文件

使用浏览器扩展导出 Cookie（**推荐纯本地扩展，不上传数据**）：

| 浏览器 | 扩展名称 | 链接 |
|--------|---------|------|
| Chrome / Edge | "Get cookies.txt LOCALLY" | [Chrome Web Store](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) |
| Firefox | "cookies.txt" | [Firefox Add-ons](https://addons.mozilla.org/firefox/addon/cookies-txt/) |

#### 步骤 2：导出 YouTube Cookie

1. 访问 https://www.youtube.com 并登录
2. 点击扩展图标，选择「Export」
3. 保存为 `youtube-cookies.txt`（文件名任意）

#### 步骤 3：在应用中导入

1. 在设置页选择「Cookie 来源」→「手动导入文件」
2. 点击「选择文件」，选择刚才导出的 `.txt` 文件
3. 应用会读取该文件路径，传递给 yt-dlp

**注意事项**：
- Cookie 有效期通常 30-90 天，过期后需重新导出
- 不要分享你的 Cookie 文件，它等同于登录凭证
- 应用不会上传或存储 Cookie，只传递文件路径给 yt-dlp

---

## 代理配置 / Proxy Configuration

在「设置」→「网络」中配置代理，支持以下格式：

### HTTP / HTTPS 代理
```
http://127.0.0.1:7890
https://proxy.example.com:8080
```

### SOCKS5 代理
```
socks5://127.0.0.1:1080
socks5h://proxy.example.com:1080
```

**`socks5` vs `socks5h`**：
- `socks5`: 本地解析域名
- `socks5h`: 代理服务器解析域名（推荐，防止 DNS 泄露）

### 带认证的代理
```
http://username:password@proxy.example.com:8080
socks5://user:pass@127.0.0.1:1080
```

**注意**：
- 代理格式必须包含 scheme 前缀（`http://`、`socks5://` 等）
- 无效格式会直接拒绝，不会回退到直连（避免意外泄露真实 IP）

---

## 文件名模板 / Filename Template

在「设置」→「通用」中自定义下载文件的命名规则，默认为：
```
%(title)s.%(ext)s
```

### 常用模板变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `%(title)s` | 视频标题 | `My Video Title.mp4` |
| `%(id)s` | 视频 ID | `abc123XYZ.mp4` |
| `%(uploader)s` | 上传者名称 | `Channel Name - My Video.mp4` |
| `%(upload_date)s` | 上传日期 (YYYYMMDD) | `20260531 - My Video.mp4` |
| `%(ext)s` | 文件扩展名 | 自动（`.mp4` / `.webm` 等） |
| `%(resolution)s` | 分辨率 | `1080p.mp4` |
| `%(format_id)s` | 格式 ID | `137+140.mp4` |

### 示例模板

**按上传者分组**：
```
%(uploader)s/%(title)s.%(ext)s
```
结果：`Channel Name/My Video.mp4`

**包含日期和分辨率**：
```
%(upload_date)s - %(title)s [%(resolution)s].%(ext)s
```
结果：`20260531 - My Video [1080p].mp4`

**完整目录结构**：
```
%(uploader)s/%(upload_date)s/%(title)s.%(ext)s
```
结果：`Channel Name/20260531/My Video.mp4`

**注意**：
- 应用会自动启用 `--restrict-filenames`，特殊字符会被替换为安全字符
- 路径分隔符 `/` 会自动创建子目录
- 完整变量列表：https://github.com/yt-dlp/yt-dlp#output-template

---

## 格式选择 / Format Selection

### 最佳质量（默认）

点击「最佳质量」相当于 yt-dlp 参数：
```bash
-f bestvideo+bestaudio
```

会自动选择最高质量的视频和音频轨道，然后用 ffmpeg 合并。

### 手动选择格式

**视频格式**包含：
- 分辨率（如 1080p、4K）
- 编码（H.264、VP9、AV1）
- 帧率（30fps、60fps）
- 文件大小

**音频格式**包含：
- 编码（AAC、Opus）
- 比特率（128kbps、256kbps）

选择一个视频格式 + 一个音频格式，应用会调用 ffmpeg 合并为单个文件。

### 编码偏好

在「设置」→「格式偏好」中设置：

**首选视频编码**（仅对「最佳质量」生效）：
- `any`: 不限制，优先最高质量
- `h264`: 优先 H.264（兼容性最好）
- `vp9`: 优先 VP9（相同质量下文件更小）
- `av1`: 优先 AV1（最新编码，最小文件，解码性能要求高）

**最大分辨率限制**：
- `无限制`: 允许 4K / 8K
- `1080p`: 最高 1920×1080
- `720p`: 最高 1280×720

适用于批量下载时避免意外下载超大文件。

---

## 并发下载 / Concurrent Downloads

在「设置」→「通用」中设置并发数（1-5），默认 2。

**推荐设置**：
- **家庭网络**：2-3（YouTube 对同 IP 并发敏感）
- **数据中心 IP**：1（避免触发限流）
- **慢速网络**：1（避免每个任务都很慢）

过高的并发可能触发 YouTube 的 `403 Forbidden`，此时需降低并发或使用 Cookie。

---

## 限速 / Rate Limiting

在「设置」→「网络」中设置下载速度上限，格式：
```
500K    # 500 KB/s
1.5M    # 1.5 MB/s
10M     # 10 MB/s
```

**何时使用**：
- 避免占满带宽影响其他设备
- 数据流量有限的移动网络
- 避免触发 ISP 限速

留空表示不限速。

---

## 更新管理 / Update Management

### 应用自身更新

应用启动时会自动检查 GitHub Release，发现新版本会在设置页显示「有新版本可用」。

点击「检查更新」会弹出更新对话框，下载安装包后自动重启。

**手动更新**：
1. 访问 https://github.com/sa23up/yt-dlp-GUI/releases/latest
2. 下载对应平台的安装包
3. 安装覆盖旧版本

### yt-dlp 更新

YouTube 频繁更新反爬机制，yt-dlp 每 1-3 周发布新版本。

在「设置」→「更新」中：
1. 查看当前 yt-dlp 版本
2. 点击「检查最新版本」
3. 如果有更新，点击「立即更新」

更新过程：
1. 从 GitHub Release 下载最新 yt-dlp 二进制
2. 验证 SHA-256 哈希（防止篡改）
3. 替换 `~/.yt-dlp-gui/bin/yt-dlp`
4. 验证失败自动回滚

**注意**：ffmpeg 和 deno 不支持应用内更新，跟随 UI 版本一起发布。

---

## 故障排查 / Troubleshooting

### 问题 1：下载失败，提示「请求被拒绝 / Request Blocked」

**原因**：YouTube 的反爬机制或 IP 限流。

**解决方案**：
1. 使用 Cookie 认证（见上文「Cookie 认证」章节）
2. 降低并发数至 1-2
3. 使用代理
4. 等待一段时间后重试（可能是临时限流）

---

### 问题 2：下载失败，提示「Cookie 已过期 / Login Expired」

**原因**：手动导入的 Cookie 文件已过期。

**解决方案**：
1. 重新登录 YouTube
2. 重新导出 Cookie 文件
3. 在设置中更新文件路径

**预防**：使用 Firefox 自动读取，Cookie 会实时同步。

---

### 问题 3：Chrome Cookie 读取失败

**原因**：浏览器未完全关闭。

**解决方案**：
1. 关闭所有 Chrome 窗口
2. 确认任务管理器中无 `chrome.exe` 进程
3. 关闭 Chrome 后台应用（系统托盘图标）
4. 重试下载

或改用 Firefox 自动读取 / 手动导入方式。

---

### 问题 4：下载速度很慢

**可能原因**：
1. ISP 限速 YouTube
2. 并发数过高导致每个任务分配带宽不足
3. 代理速度慢

**解决方案**：
1. 降低并发数至 1
2. 更换代理或直连
3. 避开高峰时段

---

### 问题 5：视频和音频不同步

**原因**：ffmpeg 合并时出现问题（极少见）。

**解决方案**：
1. 检查 `~/.yt-dlp-gui/app.log` 查看详细错误
2. 尝试不同的格式组合（避免高帧率视频）
3. 更新 yt-dlp 到最新版本

---

### 问题 6：应用崩溃或无法启动

**排查步骤**：

1. **查看日志**：
   ```bash
   # Linux
   cat ~/.yt-dlp-gui/app.log
   
   # Windows
   type %USERPROFILE%\.yt-dlp-gui\app.log
   ```

2. **清空配置**（谨慎，会丢失设置）：
   ```bash
   # Linux
   rm -rf ~/.yt-dlp-gui/
   
   # Windows
   rmdir /s %USERPROFILE%\.yt-dlp-gui
   ```

3. **重新安装**：
   - 卸载应用
   - 下载最新版本
   - 重新安装

---

### 问题 7：播放列表只下载了部分视频

**原因**：
1. 队列深度上限（200 个任务）
2. 播放列表中部分视频不可用
3. 解析超时（单个播放列表 60 秒，总计 180 秒）

**解决方案**：
1. 分批粘贴播放列表 URL
2. 手动复制视频 URL 逐个下载
3. 检查日志查看哪些视频跳过了

---

### 获取帮助 / Get Help

如果以上方法无法解决问题：

1. **搜索 Issues**：https://github.com/sa23up/yt-dlp-GUI/issues
2. **提交 Bug 报告**：使用 Bug Report 模板，附带日志文件
3. **讨论区提问**：https://github.com/sa23up/yt-dlp-GUI/discussions

提供以下信息可加快诊断：
- 应用版本（设置页查看）
- 操作系统（Windows 10/11、Linux 发行版）
- 复现步骤
- `app.log` 相关部分（隐藏 Cookie / 路径等敏感信息）
- 截图

---

## 数据存储位置 / Data Storage Locations

```
~/.yt-dlp-gui/
├── settings.json      — 应用设置
├── queue.json         — 下载队列（持久化）
├── app.log            — 应用日志（1 MB 滚动）
├── app.log.1          — 上次日志备份
└── bin/
    └── yt-dlp         — 自更新后的 yt-dlp 二进制
```

**Windows 路径**：`%USERPROFILE%\.yt-dlp-gui\`

下载的文件保存在「设置」中指定的目录，默认为用户的「下载」文件夹。

---

## 快捷键 / Keyboard Shortcuts

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+V` / `Cmd+V` | 粘贴 URL 到输入框 |
| `Enter` | 提交 URL 获取格式 |
| `Esc` | 取消格式选择对话框 |

更多快捷键待后续版本添加。

---

## 隐私声明 / Privacy Statement

- 应用不收集任何用户数据
- Cookie 文件仅传递给本地 yt-dlp 进程，不上传或存储
- 不包含遥测或分析代码
- 网络连接仅用于：
  - 下载视频（youtube.com）
  - 检查应用更新（github.com）
  - 更新 yt-dlp（github.com）

---

## 技术限制 / Technical Limitations

- **无暂停功能**：yt-dlp 和 YouTube 均不支持断点续传，只能取消后重新下载
- **无历史记录**：完成/失败的任务仅通过系统通知告知，不保留应用内历史
- **macOS 不支持**：需要 Apple Developer 签名，暂未计划
- **播放列表上限**：单次最多 200 个视频，避免内存溢出

---

## 常见问题 / FAQ

**Q: 为什么没有 macOS 版本？**  
A: macOS 要求应用签名（需付费 Apple Developer 账号）。如有需求可自行编译。

**Q: 支持 Bilibili / Twitter 等其他网站吗？**  
A: yt-dlp 本身支持 1000+ 网站，但本应用 UI 针对 YouTube 优化。其他网站可能部分功能不可用。

**Q: 可以下载 YouTube Music 吗？**  
A: 可以，粘贴 `music.youtube.com` 链接即可。

**Q: 下载的文件在哪里？**  
A: 「设置」→「下载目录」中查看和修改。

**Q: 如何卸载应用？**  
A: 
- Windows: 控制面板 → 卸载程序
- Linux: `sudo apt remove yt-dlp-gui` 或删除 AppImage 文件
- 数据目录 `~/.yt-dlp-gui/` 不会自动删除，需手动清理

---

## 贡献和反馈 / Contributions & Feedback

- **Bug 报告**：https://github.com/sa23up/yt-dlp-GUI/issues
- **功能请求**：https://github.com/sa23up/yt-dlp-GUI/issues
- **贡献代码**：请阅读 [CONTRIBUTING.md](../CONTRIBUTING.md)
- **讨论交流**：https://github.com/sa23up/yt-dlp-GUI/discussions

感谢使用 yt-dlp-gui！
