# 企微消息提示优化指南

## 概述

本文档介绍企业微信消息推送的优化功能，支持使用 **text 消息类型**，以便在 Push 事件通知中 **@提交者**，并在消息中包含 **AI Review 结果的 URL 和评分**。

## 功能特性

### 1. 支持 text 消息类型（可@人）

企业微信的 **text 消息类型**支持 `mentioned_list` 参数和 `<@userid>` 语法，可以 @指定用户。

### 2. 支持 markdown 消息类型（也可@人）

根据企业微信官方文档，**markdown 消息**也支持在 content 中使用 `<@userid>` 语法来 @群成员！

👉 **参考文档**: [https://developer.work.weixin.qq.com/document/path/99110](https://developer.work.weixin.qq.com/document/path/99110)

### 3. AI Review 结果增强

Push 事件的通知消息中现在包含：
- **AI Review 评分**：显示代码质量评分
- **查看详情链接**：直接跳转到 GitLab/GitHub 的 commit 评论，查看完整的 AI Review 结果

## 配置说明

### 环境变量配置

在 `.env` 文件中添加以下配置：

```bash
# 企业微信推送启用
WECOM_ENABLED=1
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY

# Push 事件是否使用 text 消息类型（支持@人）
# 1: 使用 text 类型，会@所有commit者
# 0: 使用 markdown 类型（默认）
PUSH_WECOM_USE_TEXT_MSG=1
```

### 配置项说明

| 配置项 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `WECOM_ENABLED` | 否 | `0` | 是否启用企业微信推送：`1` 启用，`0` 禁用 |
| `WECOM_WEBHOOK_URL` | 是 | 无 | 企业微信机器人 Webhook URL |
| `PUSH_WECOM_USE_TEXT_MSG` | 否 | `0` | Push 事件是否使用 text 消息类型：`1` 启用（会@commit者），`0` 使用 markdown |

## 消息格式对比

### Text 消息格式（PUSH_WECOM_USE_TEXT_MSG=1）

```
🚀 ProjectName: Push

提交记录:
- 提交信息: feat: add new feature
  提交者: zhangsan
  时间: 2025-10-24T10:30:00
  查看详情: https://gitlab.com/project/commit/abc123

- 提交信息: fix: resolve bug
  提交者: lisi
  时间: 2025-10-24T11:00:00
  查看详情: https://gitlab.com/project/commit/def456

AI Review 结果:
评分: 85.0/100
查看详情: https://gitlab.com/project/commit/abc123

[@zhangsan @lisi]  # 会@所有commit的作者
```

**说明**：
- 提交信息保持详细格式（包含时间、作者、链接）
- AI Review 结果仅显示评分和查看详情链接，不包含详细内容
- 可以 @commit 者，提醒他们点击链接查看完整结果

### Markdown 消息格式（PUSH_WECOM_USE_TEXT_MSG=0，默认）

```markdown
### 🚀 ProjectName: Push

#### 提交记录:
- **提交信息**: feat: add new feature
- **提交者**: zhangsan
- **时间**: 2025-10-24T10:30:00
- [查看提交详情](https://gitlab.com/project/commit/abc123)

#### AI Review 结果:
- **评分**: 85.0
- [查看详情](https://gitlab.com/project/commit/abc123)

代码质量评分：85/100
主要问题：
1. 建议添加单元测试...

<@zhangsan> <@lisi>  # 使用<@userid>语法@用户
```

**说明**：
- 支持丰富的 Markdown 格式
- 显示完整的 AI Review 结果
- 现在也支持使用 `<@userid>` 语法 @用户！

## 使用场景建议

### 使用 Text 消息（PUSH_WECOM_USE_TEXT_MSG=1）

适用于以下场景：
- ✅ 需要及时提醒代码提交者关注 AI Review 结果
- ✅ 团队规模较小，@人不会造成打扰
- ✅ 希望提高代码审查的响应速度
- ✅ 需要查看详细的提交信息（时间、作者、链接）

### 使用 Markdown 消息（PUSH_WECOM_USE_TEXT_MSG=0）

适用于以下场景：
- ✅ 仅作为信息通知，不需要强制提醒
- ✅ 团队规模较大，减少@人带来的打扰
- ✅ 需要更丰富的消息格式展示

## 注意事项

1. **企业微信 @人的实现方式**
   - **Text 消息**：同时支持 `mentioned_list` 参数和 `<@userid>` 语法
   - **Markdown 消息**：仅支持 `<@userid>` 语法
   - 用户需要在企业微信中的名称需要与 GitLab/GitHub 的用户名**完全匹配**才能被 @到
   - 如果匹配不上，可以考虑配置用户映射关系（未来功能）

2. **消息长度限制**
   - Text 消息最大 2048 字节
   - Markdown 消息最大 4096 字节
   - 超过限制会自动分割发送

3. **AI Review 结果 URL**
   - 仅在 PUSH_REVIEW_ENABLED=1 时才会有评分和 URL
   - URL 指向最后一个 commit 的评论
   - Text 消息不显示详细内容，需要点击链接查看

## 完整配置示例

```bash
# .env 文件示例

# 企业微信配置
WECOM_ENABLED=1
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY

# Push Review 配置
PUSH_REVIEW_ENABLED=1
PUSH_WECOM_USE_TEXT_MSG=1

# Commit Message 检查（可选）
PUSH_COMMIT_MESSAGE_CHECK_ENABLED=1
PUSH_COMMIT_MESSAGE_CHECK_PATTERN=review
```

## 技术实现说明

### 关键代码文件

- `biz/utils/im/wecom.py`: 企业微信通知器，支持 mentioned_list 参数
- `biz/utils/im/notifier.py`: 通知分发器，支持传递 mentioned_list
- `biz/event/event_manager.py`: 事件处理器，根据配置选择消息类型和提取 commit 作者
- `biz/entity/review_entity.py`: PushReviewEntity 增加 note_url 字段
- `biz/gitlab/webhook_handler.py`: add_push_notes 返回 commit URL
- `biz/github/webhook_handler.py`: add_push_notes 返回 commit URL

### 数据流

1. Push 事件触发 → `worker.py` 处理
2. 调用 `handler.add_push_notes()` 添加评论并获取 URL
3. 创建 `PushReviewEntity`，包含 `note_url` 和 `score`
4. 触发 `on_push_reviewed` 事件
5. 根据 `PUSH_WECOM_USE_TEXT_MSG` 配置决定消息类型
6. Text 类型：提取所有 commit 作者作为 `mentioned_list`
7. 调用 `send_notification` 发送消息，企业微信会 @相关人员

## 故障排查

### @人不生效

**可能原因**：
1. GitLab/GitHub 用户名与企业微信用户名不匹配
2. `PUSH_WECOM_USE_TEXT_MSG` 未设置为 `1`
3. 使用了 markdown 消息类型（不支持@人）

**解决方案**：
1. 检查企业微信用户名与 Git 提交者名称是否一致
2. 确认环境变量配置正确
3. 查看日志确认消息类型和 mentioned_list 内容

### 没有评分和详情链接

**可能原因**：
1. `PUSH_REVIEW_ENABLED` 未设置为 `1`
2. 代码变更未触发 Review（文件类型不在支持范围）
3. add_push_notes 失败

**解决方案**：
1. 确认 `PUSH_REVIEW_ENABLED=1`
2. 检查 `SUPPORTED_EXTENSIONS` 配置
3. 查看日志确认 API 调用状态

## 更新日志

**v1.1.0** (2025-10-24)
- ✨ 新增：支持 text 消息类型，可@commit者
- ✨ 新增：AI Review 结果包含评分和详情链接
- 🔧 优化：mentioned_list 自动从 commits 中提取作者
- 📝 文档：新增企微消息优化使用指南
