# 批量代码审查功能实现说明

## 概述
本次更新实现了按文件批次进行代码审查的功能，解决了一次性将所有修改代码发送给AI导致上下文不够、AI忘记提示词模板要求的问题。

## 主要改动

### 1. code_reviewer.py 新增功能

#### 新增方法：`review_changes_in_batches`
- **功能**：按文件批次审查代码变更，然后汇总所有审查结果
- **参数**：
  - `changes`: 代码变更列表，每个元素是一个包含文件信息的字典
  - `commits_text`: 提交信息
- **返回值**：汇总后的审查结果

**工作流程**：
1. 遍历每个文件的变更
2. 对每个文件单独调用 `review_code` 方法进行审查
3. 如果单个文件的tokens超过 `REVIEW_MAX_TOKENS`，会自动截断
4. 收集所有文件的审查结果
5. 如果只有一个文件，直接返回该文件的审查结果
6. 如果有多个文件，调用 `_summarize_reviews` 方法汇总结果

#### 新增方法：`_summarize_reviews`
- **功能**：使用 `summary_merge_review_prompt` 提示词汇总多个审查结果
- **参数**：
  - `partial_reviews`: 各批次的审查结果列表
- **返回值**：汇总后的总审查报告

**工作流程**：
1. 加载 `summary_merge_review_prompt` 提示词配置
2. 将所有分批审查结果用分隔符拼接
3. 调用LLM进行汇总
4. 返回格式化后的汇总结果

### 2. worker.py 修改

#### `handle_merge_request_event` 函数
**修改前**：
```python
review_result = CodeReviewer().review_and_strip_code(str(changes), commits_text)
```

**修改后**：
```python
code_reviewer = CodeReviewer()
review_result = code_reviewer.review_changes_in_batches(changes, commits_text)
```

**变化**：不再将所有changes转换为字符串一次性审查，而是将changes列表传递给批量审查方法。

#### `handle_push_event` 函数
与 `handle_merge_request_event` 相同的修改方式。

#### `handle_github_push_event` 函数
与GitLab push事件处理相同的修改方式。

#### `handle_github_pull_request_event` 函数
与GitLab merge request处理相同的修改方式。

## 环境变量配置

项目提供了灵活的环境变量来控制批量审查行为：

### BATCH_REVIEW_ENABLED
- **说明**：是否启用批量审查功能
- **可选值**：
  - `1`：启用批量审查（默认）
  - `0`：禁用批量审查，使用传统的一次性审查方式
- **默认值**：`1`
- **使用场景**：
  - 启用时：代码变更会按批次分组审查，然后汇总
  - 禁用时：所有代码变更一次性发送给AI审查（可能遇到上下文限制问题）

### BATCH_REVIEW_FILES_PER_BATCH
- **说明**：每批次审查的文件数量
- **可选值**：整数，建议范围 `1-5`
- **默认值**：`1`（每个文件单独审查）
- **配置建议**：
  - `1`：每个文件独立审查，精确度最高，但LLM调用次数最多
  - `2-3`：适合中等规模的变更，平衡精确度和性能
  - `4-5`：适合大量小文件变更，减少LLM调用次数
  - 更大值：可能导致单次审查上下文过长，不推荐

### REVIEW_MAX_TOKENS
- **说明**：每批次审查的最大token限制
- **默认值**：`10000`
- **作用**：防止单批次内容过长，超出部分会自动截断

### 配置示例

在 `conf/.env` 文件中添加：

```bash
# 启用批量审查 0-否 1-是
BATCH_REVIEW_ENABLED=1

# 每批次审查文件数（建议1-5）
BATCH_REVIEW_FILES_PER_BATCH=2

```

## 性能对比

| 配置 | 10个文件变更的LLM调用次数 | 精确度 | 适用场景 |
|------|-------------------------|--------|----------|
| `BATCH_REVIEW_ENABLED=0` | 1次 | 低 | 小规模变更 |
| `FILES_PER_BATCH=1` | 11次（10+1汇总） | 最高 | 追求最高质量 |
| `FILES_PER_BATCH=3` | 5次（4批次+1汇总） | 高 | **推荐配置** |
| `FILES_PER_BATCH=5` | 3次（2批次+1汇总） | 中 | 大量小文件 |

## 提示词配置

已使用项目中新增的 `summary_merge_review_prompt` 提示词，该提示词专门用于：
- 整合多个分批审查报告
- 去除重复问题
- 重新计算整体评分
- 生成结构化的总审查报告
