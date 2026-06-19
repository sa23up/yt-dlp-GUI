# 安全最佳实践 / Security Best Practices

## 🔒 敏感信息保护

本项目通过 `.gitignore` 保护以下敏感信息不被提交到 Git：

### 🚨 绝对不能提交的文件（CRITICAL）

#### 1. 更新器签名密钥
```
*.privkey
*_updater-key
*.key
*.pem
```
**风险**: 泄露后攻击者可伪造应用更新，分发恶意软件。

#### 2. 环境变量文件
```
.env
.env.local
.env.production
```
**风险**: 可能包含 API 密钥、数据库连接字符串等。

#### 3. Cookie 文件
```
cookies.txt
*.cookies
*.cookie
```
**风险**: 包含用户的 YouTube 登录凭证，等同于账号密码。

#### 4. API 密钥和令牌
```
*_token
*_key.json
*_key.txt
*.token
```
**风险**: 泄露后第三方可冒用身份访问服务。

#### 5. 用户运行时数据
```
~/.yt-dlp-gui/
├── settings.json      # 用户设置（可能含 Cookie 路径）
├── queue.json         # 下载队列（含 URL 历史）
├── app.log            # 日志（可能含文件路径）
└── bin/yt-dlp         # 自更新后的二进制
```
**风险**: 包含用户隐私信息和使用习惯。

---

## ✅ 已实施的保护措施

### 1. `.gitignore` 全面覆盖
项目的 `.gitignore` 已配置以下规则：
- 🔴 签名密钥和证书（`*.privkey`, `*.pem`）
- 🔴 环境变量（`.env*`）
- 🔴 Cookie 文件（`cookies.txt`, `*.cookies`）
- 🔴 用户数据目录（`.yt-dlp-gui/`）
- 🟡 构建产物（`dist/`, `target/`）
- 🟡 依赖（`node_modules/`, `binaries/`）

### 2. Cookie 仅读取不存储
应用的 Cookie 处理策略：
- ✅ Firefox/Chrome 自动读取：直接传递浏览器标识符给 yt-dlp
- ✅ 手动导入：仅传递文件路径给 yt-dlp
- ✅ **不会** 复制、存储或上传 Cookie 内容
- ✅ 设置页面明确标注"不会上传或存储"

### 3. 日志脱敏
`app.log` 写入规则：
- ✅ 仅记录首行 stderr（错误类型）
- ✅ 不记录完整命令行参数（避免泄露 Cookie 路径、代理凭证）
- ✅ 大小限制 1 MB，自动滚动覆盖旧日志

### 4. 二进制完整性校验
外部二进制（yt-dlp/ffmpeg/deno）：
- ✅ CI 下载时强制 SHA-256 验证
- ✅ 自更新时强制 SHA-256 验证
- ✅ 校验失败自动回滚

---

## 🛡️ 开发者注意事项

### 提交前检查清单

在 `git commit` 之前，务必确认：

```bash
# 1. 检查是否意外暂存了敏感文件
git status

# 2. 查看即将提交的文件差异
git diff --cached

# 3. 确认没有包含以下内容：
#    - Cookie 文件内容
#    - API 密钥或令牌
#    - 真实的文件路径（如 /home/username/）
#    - 签名私钥
#    - .env 文件

# 4. 如果意外暂存了敏感文件，取消暂存：
git restore --staged <文件>
```

### 如果意外提交了敏感信息

**🚨 立即执行以下步骤：**

1. **停止推送** - 如果还未 push 到远程
   ```bash
   # 撤销最后一次提交（保留更改）
   git reset --soft HEAD~1
   # 移除敏感文件
   git restore --staged <敏感文件>
   # 重新提交
   git commit -m "..."
   ```

2. **已推送到远程** - 必须重写历史
   ```bash
   # 使用 BFG Repo-Cleaner 或 git-filter-repo
   # 警告：会改变所有提交的 SHA-1
   git filter-repo --path <敏感文件> --invert-paths
   git push --force
   ```

3. **立即轮换密钥**
   - 吊销泄露的 API 密钥
   - 重新生成 Tauri 更新器密钥对
   - 修改所有使用该密钥的地方

4. **通知用户**
   - 如果是签名密钥泄露，发布安全公告
   - 建议用户重新下载并验证新版本

---

## 🔐 CI/CD 密钥管理

### GitHub Secrets（推荐）

敏感信息应存储在 GitHub Secrets 中：

| Secret Name | 用途 | 格式 |
|-------------|------|------|
| `TAURI_PRIVATE_KEY` | 更新器签名私钥 | PEM 格式 |
| `TAURI_KEY_PASSWORD` | 私钥密码 | 字符串 |

**配置方法**：
1. GitHub 仓库 → Settings → Secrets and variables → Actions
2. 点击 "New repository secret"
3. 粘贴密钥内容（**不要加引号**）
4. 在 workflow 中通过 `${{ secrets.SECRET_NAME }}` 引用

**安全要求**：
- ✅ 使用 RSA 4096 位或更高
- ✅ 私钥加密码保护
- ✅ 定期轮换（建议每年一次）
- ✅ 限制访问权限（仅发布管理员）

---

## 📚 相关文档

- [SECURITY.md](../SECURITY.md) - 安全漏洞报告流程
- [CONTRIBUTING.md](../CONTRIBUTING.md) - 贡献指南（包含提交规范）
- [Tauri Security](https://tauri.app/v1/guides/development/security) - Tauri 安全最佳实践

---

## ⚠️ 免责声明

本项目不收集、存储或上传用户数据。所有敏感信息（Cookie、下载历史、设置）
仅存储在用户本地设备的 `~/.yt-dlp-gui/` 目录中。

**用户责任**：
- 保护好自己的 Cookie 文件，不要分享给他人
- 定期更新 yt-dlp 以获取最新安全修复
- 使用强密码保护 YouTube 账号

**开发者责任**：
- 绝不在代码中硬编码任何密钥
- 审查所有 PR，确保无敏感信息泄露
- 定期运行 `git secrets` 或类似工具扫描历史

---

**最后更新**: 2026-06-14  
**维护者**: yt-dlp-gui 团队
