# 企业微信 @人功能说明

## 重要发现 🎉

根据企业微信官方文档 [https://developer.work.weixin.qq.com/document/path/99110](https://developer.work.weixin.qq.com/document/path/99110)，我们发现：

> **text 和 markdown 类型消息都支持在 content 中使用 `<@userid>` 扩展语法来 @群成员！**

这意味着：
- ✅ **Text 消息**：同时支持 `mentioned_list` 参数和 `<@userid>` 语法
- ✅ **Markdown 消息**：支持 `<@userid>` 语法

## 实现方式

### 1. Text 消息

```json
{
  "msgtype": "text",
  "text": {
    "content": "🚀 ProjectName: Push\n\n提交记录:\n...\n\n<@zhangsan> <@lisi>",
    "mentioned_list": ["zhangsan", "lisi"]
  }
}
```

**特点**：
- 双重保障：`mentioned_list` + `<@userid>` 语法
- 企业微信会根据两者综合处理 @人逻辑

### 2. Markdown 消息

```json
{
  "msgtype": "markdown",
  "markdown": {
    "content": "### 🚀 ProjectName: Push\n\n#### 提交记录:\n...\n\n<@zhangsan> <@lisi>"
  }
}
```

**特点**：
- 仅使用 `<@userid>` 语法
- 不支持 `mentioned_list` 参数

## 代码实现

### wecom.py 核心代码

```python
def _build_text_message(self, content, is_at_all, mentioned_list=None):
    """ 构造纯文本消息 """
    # 如果提供了明确的mentioned_list，使用它；否则根据is_at_all决定
    if mentioned_list is not None:
        mentions = mentioned_list if isinstance(mentioned_list, list) else [mentioned_list]
    else:
        mentions = ["@all"] if is_at_all else []
    
    # 如果有mentioned_list，在content末尾添加<@userid>语法
    if mentioned_list:
        mention_tags = ' '.join([f'<@{user}>' for user in (mentioned_list if isinstance(mentioned_list, list) else [mentioned_list])])
        content = f"{content}\n\n{mention_tags}"
    
    return {
        "msgtype": "text",
        "text": {
            "content": content,
            "mentioned_list": mentions
        }
    }

def _build_markdown_message(self, content, title, mentioned_list=None):
    """ 构造 Markdown 消息 """
    formatted_content = self.format_markdown_content(content, title)
    
    # 如果有mentioned_list，在content末尾添加<@userid>语法
    if mentioned_list:
        mention_tags = ' '.join([f'<@{user}>' for user in (mentioned_list if isinstance(mentioned_list, list) else [mentioned_list])])
        formatted_content = f"{formatted_content}\n\n{mention_tags}"
    
    return {
        "msgtype": "markdown",
        "markdown": {
            "content": formatted_content
        }
    }
```

### event_manager.py 核心代码

```python
def on_push_reviewed(entity: PushReviewEntity):
    # 获取配置：是否使用text消息类型
    import os
    use_text_msg = os.environ.get('PUSH_WECOM_USE_TEXT_MSG', '0') == '1'
    msg_type = 'text' if use_text_msg else 'markdown'
    
    # 提取commit者用于@（text和markdown都支持）
    mentioned_list = None
    authors = set()
    for commit in entity.commits:
        author = commit.get('author', '')
        if author:
            authors.add(author)
    mentioned_list = list(authors) if authors else None
    
    # 发送消息（text或markdown都会传递mentioned_list）
    notifier.send_notification(
        content=im_msg, 
        msg_type=msg_type,
        title=f"{entity.project_name} Push Event",
        project_name=entity.project_name, 
        url_slug=entity.url_slug,
        webhook_data=entity.webhook_data,
        mentioned_list=mentioned_list  # 传递给所有消息类型
    )
```

## 效果展示

### Text 消息效果

```
🚀 ProjectName: Push

提交记录:
- 提交信息: feat: add new feature
  提交者: zhangsan
  时间: 2025-10-24T10:30:00
  查看详情: https://gitlab.com/project/commit/abc123

AI Review 结果:
评分: 85.0/100
查看详情: https://gitlab.com/project/commit/abc123

<@zhangsan> <@lisi>
```

### Markdown 消息效果

```markdown
### 🚀 ProjectName: Push

#### 提交记录:
- **提交信息**: feat: add new feature
- **提交者**: zhangsan
- **时间**: 2025-10-24T10:30:00
- [查看提交详情](https://gitlab.com/project/commit/abc123)

#### AI Review 结果:
- **评分**: 85.0/100
- [查看详情](https://gitlab.com/project/commit/abc123)

代码质量评分：85/100
主要问题：
1. 建议添加单元测试...

<@zhangsan> <@lisi>
```

## 优势对比

| 特性 | 之前 | 现在 |
|------|------|------|
| Text 消息 @人 | ✅ 支持（`mentioned_list`） | ✅ 支持（双重保障） |
| Markdown 消息 @人 | ❌ 不支持 | ✅ 支持（`<@userid>`） |
| 消息格式丰富度 | Markdown 更丰富 | Markdown 更丰富 |
| 功能完整性 | Text 独有 @人 | **两者都支持 @人** |

## 配置说明

### 环境变量

```bash
# Push 事件消息类型选择
# 0 = markdown 消息（默认，支持@人 + 完整内容）
# 1 = text 消息（支持@人 + 简洁内容）
PUSH_WECOM_USE_TEXT_MSG=0
```

### 选择建议

#### 推荐使用 Markdown 消息（默认）

现在 Markdown 消息也支持 @人了，建议大多数场景使用 Markdown：

✅ **优势**：
- 支持 @commit 者
- 格式丰富，阅读体验好
- 显示完整的 AI Review 结果
- 消息长度限制更大（4096 字节 vs 2048 字节）

✅ **适用场景**：
- 希望在消息中查看完整的审查结果
- 需要格式化显示（标题、加粗、链接等）
- 需要 @人提醒

#### 使用 Text 消息的场景

⚠️ **仅在以下情况使用**：
- 希望消息极简，只显示关键信息
- Review 详情通过链接查看
- 移动端为主，希望快速浏览

## 注意事项

### 1. userid 匹配规则

- `<@userid>` 中的 `userid` 需要与企业微信成员的 userid **完全一致**
- 如果使用 GitLab/GitHub 的用户名，需要确保与企微 userid 匹配
- 不匹配的 userid 不会触发 @提醒，但不会报错

### 2. @all 的处理

```python
# 如果需要@所有人
mentioned_list = ["@all"]

# 生成的内容会包含
content += "\n\n<@all>"
```

### 3. 多人 @的格式

```python
# 多个用户
mentioned_list = ["zhangsan", "lisi", "wangwu"]

# 生成的内容
content += "\n\n<@zhangsan> <@lisi> <@wangwu>"
```

## 技术细节

### 为什么同时使用两种方式？

对于 Text 消息，我们同时使用了：
1. `mentioned_list` 参数
2. `<@userid>` 语法

**原因**：
- `mentioned_list` 是官方推荐的标准方式
- `<@userid>` 是扩展语法，提供额外的展示效果
- 双重保障，提高兼容性

### Markdown 消息只能用扩展语法

Markdown 消息类型**不支持** `mentioned_list` 参数，只能通过在 content 中添加 `<@userid>` 实现 @人。

## 测试建议

### 1. 测试 Markdown 消息 @人

```bash
# .env 配置
WECOM_ENABLED=1
PUSH_WECOM_USE_TEXT_MSG=0  # 使用 markdown

# 提交代码，查看企业微信消息
# 应该能看到 @提醒
```

### 2. 测试 Text 消息 @人

```bash
# .env 配置
WECOM_ENABLED=1
PUSH_WECOM_USE_TEXT_MSG=1  # 使用 text

# 提交代码，查看企业微信消息
# 应该能看到 @提醒
```

### 3. 验证点

- [ ] 消息中能看到 `<@username>` 标记
- [ ] 被 @的用户收到提醒
- [ ] 消息格式正确
- [ ] 评分和链接正常显示

## 总结

通过发现并使用企业微信的 `<@userid>` 扩展语法，我们实现了：

✅ **Text 和 Markdown 消息都支持 @人**  
✅ **用户可以自由选择消息格式**  
✅ **功能完整性大幅提升**  

建议默认使用 **Markdown 消息**，兼顾格式丰富和 @人功能！

---

**参考文档**：
- [企业微信机器人 API 文档](https://developer.work.weixin.qq.com/document/path/99110)
- [企微消息优化使用指南](wecom_text_message_guide.md)
- [消息格式对比说明](message_format_comparison.md)

**更新时间**：2025-10-24
