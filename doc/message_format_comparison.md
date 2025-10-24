# 企微消息格式对比说明

## Text 消息 vs Markdown 消息

### Text 消息（PUSH_WECOM_USE_TEXT_MSG=1）

**特点**：
- ✅ **支持 @人**：通过 `mentioned_list` 和 `<@userid>` 语法
- ✅ **详细提交信息**：包含时间、作者、链接
- ✅ **Review 结果简洁**：仅显示评分和链接
- ⚠️ **需点击链接**：查看完整 AI Review 需跳转到 GitLab/GitHub

**适用场景**：
- 需要及时提醒开发者关注代码审查结果
- 团队规模小，@人不会过度打扰
- 希望消息简洁，减少信息过载
- 开发者习惯点击链接查看详情

**消息示例**：
```
🚀 AI-CodeReview: Push

提交记录:
- 提交信息: feat: add new feature
  提交者: zhangsan
  时间: 2025-10-24T10:30:00
  查看详情: https://gitlab.com/project/commit/abc123

- 提交信息: fix: resolve login bug
  提交者: lisi
  时间: 2025-10-24T11:00:00
  查看详情: https://gitlab.com/project/commit/def456

AI Review 结果:
评分: 85.0/100
查看详情: https://gitlab.com/project/commit/abc123

[@zhangsan @lisi]
```

---

### Markdown 消息（PUSH_WECOM_USE_TEXT_MSG=0，默认）

**特点**：
- ✅ **支持 @人**：通过 `<@userid>` 语法
- ✅ **格式丰富**：支持标题、加粗、链接等 Markdown 格式
- ✅ **信息完整**：在消息中直接显示完整的 AI Review 结果
- ✅ **无需跳转**：直接在企微中阅读所有内容

**适用场景**：
- 仅作为信息通知，不需要强制提醒
- 团队规模大，避免频繁@人
- 希望在消息中查看完整内容
- 适合归档和回顾

**消息示例**：
```markdown
### 🚀 AI-CodeReview: Push

#### 提交记录:
- **提交信息**: feat: add new feature
- **提交者**: zhangsan
- **时间**: 2025-10-24T10:30:00
- [查看提交详情](https://gitlab.com/project/commit/abc123)

- **提交信息**: fix: resolve login bug
- **提交者**: lisi
- **时间**: 2025-10-24T11:00:00
- [查看提交详情](https://gitlab.com/project/commit/def456)

#### AI Review 结果:
- **评分**: 85.0/100
- [查看详情](https://gitlab.com/project/commit/abc123)

代码质量评分：85/100

主要问题：
1. 建议为新增功能添加单元测试
2. login bug 修复后需要验证边界情况

优点：
1. 代码逻辑清晰
2. 注释完整

建议：
1. 增加错误处理
2. 优化性能
```

---

## 配置对比

| 配置项 | Text 消息 | Markdown 消息 |
|--------|-----------|--------------|
| `PUSH_WECOM_USE_TEXT_MSG` | `1` | `0`（默认） |
| **支持 @人** | ✅ 是 | ❌ 否 |
| **显示完整 Review** | ❌ 否（需点链接） | ✅ 是 |
| **消息长度** | 短（约 10-15 行） | 长（可能 30+ 行） |
| **最大字节数** | 2048 字节 | 4096 字节 |
| **格式化** | 纯文本 | Markdown |
| **查看详情** | 必须点击链接 | 可直接查看或点击链接 |

---

## 选择建议

### 推荐使用 Text 消息的情况

✅ **强提醒场景**
- 希望开发者第一时间注意到代码审查结果
- 代码质量要求高，需要及时响应

✅ **小团队场景**
- 团队成员少于 10 人
- @人不会造成过度打扰

✅ **移动优先场景**
- 团队成员主要通过手机查看消息
- 希望消息简洁，快速阅读

✅ **点击习惯场景**
- 团队习惯点击链接查看详情
- GitLab/GitHub 访问速度快

---

### 推荐使用 Markdown 消息的情况

✅ **信息展示场景**
- 希望在消息中看到完整的审查结果
- 不需要强制提醒特定人员

✅ **大团队场景**
- 团队成员超过 10 人
- 避免频繁@人造成打扰

✅ **桌面优先场景**
- 团队成员主要通过电脑查看消息
- 需要详细的格式化内容

✅ **归档需求场景**
- 需要在企微中保留完整的审查记录
- 方便后续回顾和查找

---

## 快速切换

### 启用 Text 消息（@人 + 简洁）

```bash
# .env 文件
PUSH_WECOM_USE_TEXT_MSG=1
```

### 使用 Markdown 消息（完整内容）

```bash
# .env 文件
PUSH_WECOM_USE_TEXT_MSG=0
# 或删除/注释该配置项
```

---

## 常见问题

### Q1: 可以让 Markdown 消息也支持 @人吗？

**A**: 可以！根据企业微信官方文档，**markdown 消息现在也支持 @人**：
- **text 消息类型**：支持 `mentioned_list` 参数和 `<@userid>` 语法
- **markdown 消息类型**：支持 `<@userid>` 语法

参考文档：[https://developer.work.weixin.qq.com/document/path/99110](https://developer.work.weixin.qq.com/document/path/99110)

本项目已经实现了该功能，**text 和 markdown 两种消息类型都支持 @commit 者**！

### Q2: Text 消息可以显示完整的 Review 内容吗？

**A**: 不推荐。原因：
1. Text 消息有 2048 字节限制，完整内容容易超限
2. Text 消息不支持格式化，阅读体验差
3. 设计理念是"简洁提醒 + 链接跳转"

如果需要在消息中查看完整内容，建议使用 Markdown 消息。

### Q3: 可以只在某些项目使用 Text 消息吗？

**A**: 目前不支持。`PUSH_WECOM_USE_TEXT_MSG` 是全局配置，作用于所有项目。

如有需求，可以考虑：
- 不同项目使用不同的企微 Webhook（通过 `WECOM_WEBHOOK_URL_{PROJECT_NAME}` 配置）
- 为不同 Webhook 部署不同的服务实例，使用不同的配置

### Q4: @人不生效怎么办？

**A**: 检查以下几点：
1. 确认 `PUSH_WECOM_USE_TEXT_MSG=1`
2. 确认 GitLab/GitHub 的 commit author name 与企业微信用户名完全一致
3. 查看日志确认 `mentioned_list` 内容正确
4. 测试企微机器人是否有 @人权限

---

## 总结

| 维度 | Text 消息 | Markdown 消息 |
|------|-----------|--------------|
| **核心优势** | @人提醒 | 完整展示 |
| **使用建议** | 强提醒场景 | 信息展示场景 |
| **配置难度** | 简单 | 简单（默认） |
| **学习成本** | 低 | 低 |

根据团队实际需求选择合适的消息类型，也可以先试用 Text 消息，如果@人过度打扰，再切换回 Markdown 消息。

---

**相关文档**：
- [企微消息优化使用指南](wecom_text_message_guide.md)
- [更新日志](CHANGELOG_wecom_optimization.md)
- [常见问题 FAQ](faq.md)
