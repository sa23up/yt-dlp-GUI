## 变更类型 / Change Type

<!-- 请勾选适用的类型 / Please check applicable types -->

- [ ] 🐛 Bug 修复 / Bug fix
- [ ] ✨ 新功能 / New feature
- [ ] 📝 文档更新 / Documentation
- [ ] ♻️ 重构 / Refactoring
- [ ] 🎨 UI/样式改进 / UI/Style improvement
- [ ] ⚡️ 性能优化 / Performance improvement
- [ ] ✅ 测试 / Tests
- [ ] 🔧 构建/配置 / Build/Config

## 变更说明 / Description

<!-- 清晰描述本次变更的内容和原因 / Clearly describe what changed and why -->



## 关联 Issue / Related Issue

<!-- 关闭哪个 Issue？使用 "Closes #123" / Which issue does this close? Use "Closes #123" -->

Closes #

## 测试 / Testing

<!-- 如何验证这个变更？/ How was this change tested? -->

- [ ] 已通过所有单元测试 / All unit tests pass
- [ ] 已手动测试关键路径 / Key paths manually tested
- [ ] 已在以下环境测试 / Tested on:
  - [ ] Windows
  - [ ] Linux

## 截图 / Screenshots

<!-- 如果是 UI 变更，请提供前后对比 / If UI change, provide before/after -->



## 检查清单 / Checklist

- [ ] 代码通过 `cargo clippy -D warnings` 和 `cargo fmt --check`
- [ ] 前端通过 `npm run build`（包含类型检查）
- [ ] 更新了相关文档（如果需要）
- [ ] 更新了 `CONTEXT.md`（如果引入新术语）
- [ ] 添加/更新了测试
- [ ] `src/bindings.ts` 已同步（如果修改了 Rust IPC）

## 破坏性变更 / Breaking Changes

<!-- 是否有不兼容的 API 变更？/ Are there any incompatible API changes? -->

- [ ] 无破坏性变更 / No breaking changes
- [ ] 有破坏性变更（请在下方说明）/ Has breaking changes (explain below)

<!-- 如有破坏性变更，说明迁移路径 / If breaking, explain migration path -->



## 附加信息 / Additional Notes

<!-- 任何其他需要审查者注意的信息 / Any other info for reviewers -->


