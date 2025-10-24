# Push事件Commit Message检查配置指南

## 功能说明

本功能允许你在处理Push事件时，根据commit message的内容决定是否触发代码审查。只有当commit message匹配指定的规则时，才会执行AI代码审查。

## 配置参数

在 `conf/.env` 文件中，有以下两个配置项：

### 1. PUSH_COMMIT_MESSAGE_CHECK_ENABLED

**说明：** 是否启用commit message检查开关

**可选值：**
- `0`：关闭检查（默认）- Push事件会正常触发代码审查
- `1`：开启检查 - 只有当commit message匹配指定规则时才触发代码审查

**示例：**
```bash
PUSH_COMMIT_MESSAGE_CHECK_ENABLED=1
```

### 2. PUSH_COMMIT_MESSAGE_CHECK_PATTERN

**说明：** Commit message检查规则，支持正则表达式（不区分大小写）

**默认值：** `review`

**示例：**

1. **简单关键字匹配**
   ```bash
   PUSH_COMMIT_MESSAGE_CHECK_PATTERN=review
   ```
   匹配包含 "review" 或 "Review" 或 "REVIEW" 的commit message

2. **多个关键字（任意一个）**
   ```bash
   PUSH_COMMIT_MESSAGE_CHECK_PATTERN=(review|codereview|code-review)
   ```
   匹配包含 "review"、"codereview" 或 "code-review" 的commit message

3. **特定格式标签**
   ```bash
   PUSH_COMMIT_MESSAGE_CHECK_PATTERN=\[review\]
   ```
   匹配包含 "[review]" 标签的commit message

4. **特定前缀**
   ```bash
   PUSH_COMMIT_MESSAGE_CHECK_PATTERN=^(feat|fix|review):
   ```
   匹配以 "feat:"、"fix:" 或 "review:" 开头的commit message

5. **复杂规则组合**
   ```bash
   PUSH_COMMIT_MESSAGE_CHECK_PATTERN=(\[review\]|^review:|需要审查)
   ```
   匹配以下任意情况：
   - 包含 "[review]" 标签
   - 以 "review:" 开头
   - 包含 "需要审查" 文字

## 使用场景

### 场景1：只对标记的commit进行审查

```bash
PUSH_COMMIT_MESSAGE_CHECK_ENABLED=1
PUSH_COMMIT_MESSAGE_CHECK_PATTERN=\[review\]
```

开发者在commit message中添加 `[review]` 标签时才触发审查：
```bash
git commit -m "[review] 实现用户登录功能"
```

### 场景2：特定类型的commit才审查

```bash
PUSH_COMMIT_MESSAGE_CHECK_ENABLED=1
PUSH_COMMIT_MESSAGE_CHECK_PATTERN=^(feat|fix):
```

只对功能开发(feat)和bug修复(fix)类型的commit进行审查：
```bash
git commit -m "feat: 添加用户管理模块"
git commit -m "fix: 修复登录超时问题"
```

### 场景3：关键词触发

```bash
PUSH_COMMIT_MESSAGE_CHECK_ENABLED=1
PUSH_COMMIT_MESSAGE_CHECK_PATTERN=(review|审查|code-review)
```

commit message中包含任意关键词即触发审查：
```bash
git commit -m "请帮忙review一下这个功能"
git commit -m "需要进行代码审查的重要更新"
```

## 工作流程

1. **检查开关状态**
   - 如果 `PUSH_COMMIT_MESSAGE_CHECK_ENABLED=0`，跳过检查，正常执行审查
   - 如果 `PUSH_COMMIT_MESSAGE_CHECK_ENABLED=1`，继续执行检查

2. **匹配规则检查**
   - 遍历所有commit的message
   - 使用配置的正则表达式进行匹配（不区分大小写）
   - 只要有一个commit message匹配成功，就继续执行审查

3. **执行结果**
   - **匹配成功**：记录日志 `Commits message匹配规则 "{pattern}"，继续执行审查。`，继续执行代码审查
   - **匹配失败**：记录日志 `Commits message中未匹配到指定规则 "{pattern}"，跳过本次审查。`，结束流程
   - **正则表达式错误**：记录错误日志，跳过检查继续执行审查

## 注意事项

1. **正则表达式语法**
   - 使用Python正则表达式语法
   - 特殊字符需要转义，如 `[` 需要写成 `\[`
   - 匹配模式不区分大小写（自动使用 `re.IGNORECASE` 标志）

2. **多commit处理**
   - 一次push可能包含多个commit
   - 只要任意一个commit message匹配规则即可触发审查
   - 不需要所有commit都匹配

3. **错误处理**
   - 如果正则表达式格式错误，系统会记录错误日志并跳过检查，继续执行审查
   - 确保配置的正则表达式语法正确

4. **性能影响**
   - 检查逻辑在代码审查之前执行
   - 不匹配的commit会立即返回，不会调用AI模型，节省资源

## 测试建议

修改配置后，建议按以下步骤测试：

1. 设置测试配置
   ```bash
   PUSH_COMMIT_MESSAGE_CHECK_ENABLED=1
   PUSH_COMMIT_MESSAGE_CHECK_PATTERN=test-review
   ```

2. 创建测试commit（不应触发审查）
   ```bash
   git commit -m "普通的提交"
   git push
   ```

3. 创建匹配的commit（应该触发审查）
   ```bash
   git commit -m "test-review 需要审查的提交"
   git push
   ```

4. 查看日志确认
   - 检查应用日志文件 `log/app.log`
   - 确认看到相应的匹配或未匹配日志

## 常见问题

**Q: 配置修改后需要重启服务吗？**
A: 是的，需要重启服务使配置生效。

**Q: 如何临时禁用检查？**
A: 将 `PUSH_COMMIT_MESSAGE_CHECK_ENABLED` 设置为 `0` 并重启服务。

**Q: 支持中文关键字吗？**
A: 支持，可以直接使用中文，如 `PUSH_COMMIT_MESSAGE_CHECK_PATTERN=(review|审查|检视)`

**Q: 如何确认正则表达式是否正确？**
A: 可以使用Python在线正则测试工具，或者查看日志中的错误信息。
