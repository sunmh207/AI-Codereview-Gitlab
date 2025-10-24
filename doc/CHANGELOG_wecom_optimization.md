# 企微消息提示优化 - 更新日志

## 版本：v1.1.0
**发布日期**：2025-10-24

---

## 🎉 新功能

### 1. 支持企业微信 Text 消息类型（可 @commit 者）

**背景**：  
之前的企业微信消息推送使用 **markdown** 格式，虽然展示效果好，但无法 @指定用户。为了更好地提醒代码提交者关注 AI Review 结果，现已支持 **text** 消息类型。

**功能说明**：
- 通过环境变量 `PUSH_WECOM_USE_TEXT_MSG=1` 启用 text 消息
- 自动提取所有 commit 作者，使用企业微信的 `mentioned_list` 参数 @相关人员
- 提高代码审查的响应速度和关注度

**配置方式**：
```bash
# .env 文件
PUSH_WECOM_USE_TEXT_MSG=1  # 启用 text 消息，支持@人
```

---

### 2. AI Review 结果增强（包含评分和详情链接）

**背景**：  
之前的 Push 消息通知中只显示 AI Review 的文字结果，缺少评分和详情链接，用户需要手动查找对应的 commit。

**功能说明**：
- 新增 **AI Review 评分**显示（如：85.0/100）
- 新增 **查看详情链接**，直接跳转到 GitLab/GitHub 的 commit 评论页面
- 方便用户快速查看完整的 AI Review 结果

**效果展示**：

**Text 消息示例**：
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

[@zhangsan @lisi]  # 企业微信会@这些用户
```

**说明**：
- 提交信息保持详细格式（包含时间、作者、链接）
- AI Review 结果仅显示评分和查看详情链接，不包含详细内容
- 点击链接查看完整的 AI Review 结果

**Markdown 消息示例**：
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
```

---

## 🔧 技术实现

### 修改的文件

| 文件路径 | 修改内容 |
|---------|---------|
| `biz/utils/im/wecom.py` | `send_message()` 和 `_build_text_message()` 新增 `mentioned_list` 参数支持 |
| `biz/utils/im/notifier.py` | `send_notification()` 新增 `mentioned_list` 参数传递 |
| `biz/entity/review_entity.py` | `PushReviewEntity` 新增 `note_url` 字段，保存 AI Review 结果的 URL |
| `biz/gitlab/webhook_handler.py` | `add_push_notes()` 方法返回 commit URL |
| `biz/github/webhook_handler.py` | `add_push_notes()` 方法返回 commit URL |
| `biz/queue/worker.py` | `handle_push_event()` 和 `handle_github_push_event()` 接收并传递 `note_url` |
| `biz/event/event_manager.py` | `on_push_reviewed()` 根据配置选择消息类型，提取 commit 作者用于 `mentioned_list` |

### 新增的文件

| 文件路径 | 说明 |
|---------|------|
| `doc/wecom_text_message_guide.md` | 企微消息优化功能使用指南 |
| `doc/CHANGELOG_wecom_optimization.md` | 本更新日志 |

### 数据流

```
Push Event 触发
    ↓
worker.py 处理
    ↓
handler.add_push_notes() → 返回 commit URL
    ↓
创建 PushReviewEntity (包含 note_url 和 score)
    ↓
触发 on_push_reviewed 事件
    ↓
根据 PUSH_WECOM_USE_TEXT_MSG 决定消息类型
    ↓
Text 类型：提取所有 commit 作者 → mentioned_list
    ↓
send_notification() → WeComNotifier
    ↓
企业微信 @相关人员
```

---

## 📋 配置说明

### 新增环境变量

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `PUSH_WECOM_USE_TEXT_MSG` | Boolean | `0` | Push 事件是否使用 text 消息类型：<br>`1` = 启用（会@commit者）<br>`0` = 使用 markdown（默认） |

### 完整配置示例

```bash
# .env 文件

# 企业微信配置
WECOM_ENABLED=1
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY

# Push Review 配置
PUSH_REVIEW_ENABLED=1
PUSH_WECOM_USE_TEXT_MSG=1  # 新增：启用 text 消息

# Commit Message 检查（可选）
PUSH_COMMIT_MESSAGE_CHECK_ENABLED=1
PUSH_COMMIT_MESSAGE_CHECK_PATTERN=review
```

---

## ⚠️ 注意事项

### 1. @人功能的限制

- 企业微信 @人需要用户名**完全匹配**
- GitLab/GitHub 的 commit author name 需要与企业微信用户名一致
- 如果匹配不上，用户不会被@到（但消息仍会发送）

**解决方案**：
- 确保开发者在 Git 中配置的用户名与企业微信一致
- 未来可考虑增加用户名映射功能

### 2. 消息长度限制

| 消息类型 | 最大长度 |
|---------|---------|
| Text | 2048 字节 |
| Markdown | 4096 字节 |

超过限制会自动分割发送。

### 3. AI Review URL 生成条件

- 需要 `PUSH_REVIEW_ENABLED=1`
- 代码变更需要满足 `SUPPORTED_EXTENSIONS` 配置
- `add_push_notes()` API 调用成功

---

## 🚀 使用场景建议

### 适合使用 Text 消息的场景

✅ 需要及时提醒代码提交者关注 AI Review 结果  
✅ 团队规模较小，@人不会造成打扰  
✅ 希望提高代码审查的响应速度  

### 适合使用 Markdown 消息的场景

✅ 仅作为信息通知，不需要强制提醒  
✅ 团队规模较大，减少@人带来的打扰  
✅ 需要更丰富的消息格式展示  

---

## 📚 相关文档

- [企微消息优化使用指南](wecom_text_message_guide.md)
- [常见问题 FAQ](faq.md)
- [Push Commit Check 指南](push_commit_check_guide.md)

---

## 🙏 致谢

感谢所有提出需求和建议的用户！如果您有任何问题或改进建议，欢迎提交 Issue 或 PR。

---

**更新时间**：2025-10-24  
**版本**：v1.1.0  
**作者**：AI-Codereview-Gitlab Team
