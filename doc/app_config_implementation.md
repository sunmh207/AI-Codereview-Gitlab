# 应用专属配置功能实现总结

## 功能概述

本次改造实现了按应用名（GitLab/GitHub URL slug）独立配置 `.env` 和 `prompt_templates.yml` 的功能，使得不同的代码仓库可以使用不同的配置参数和 Prompt 模板，实现更灵活的多项目管理。

## 改造内容

### 1. 新增核心模块

#### 1.1 配置加载器 (`biz/utils/config_loader.py`)

创建了 `ConfigLoader` 类，实现以下功能：

- **单例模式**：全局唯一的配置加载器实例
- **配置优先级**：应用专属配置 > 默认配置
- **环境变量加载**：`load_env(app_name)` 方法支持按应用名加载 `.env`
- **Prompt模板加载**：`load_prompt_template(prompt_key, app_name)` 方法支持按应用名加载 `prompt_templates.yml`
- **路径解析**：自动查找应用专属配置文件，不存在时降级到默认配置
- **目录创建**：提供 `create_app_config_dir(app_name)` 方法快速创建应用配置目录

**关键方法：**
```python
# 设置应用名称
config_loader.set_app_name(app_name)

# 加载环境变量（支持覆盖）
config_loader.load_env(app_name, override=True)

# 加载Prompt模板
prompts = config_loader.load_prompt_template(prompt_key, app_name)

# 获取配置文件路径
env_path = config_loader.get_env_file_path(app_name)
template_path = config_loader.get_prompt_template_file_path(app_name)
```

### 2. 修改现有模块

#### 2.1 代码审查器 (`biz/utils/code_reviewer.py`)

**修改内容：**
- `BaseReviewer.__init__()` 新增 `app_name` 参数
- `_load_prompts()` 方法改用 `config_loader.load_prompt_template()` 加载配置
- `CodeReviewer.__init__()` 新增 `app_name` 参数并传递给父类

**改动前：**
```python
class CodeReviewer(BaseReviewer):
    def __init__(self):
        super().__init__("code_review_prompt")
```

**改动后：**
```python
class CodeReviewer(BaseReviewer):
    def __init__(self, app_name: Optional[str] = None):
        super().__init__("code_review_prompt", app_name)
```

#### 2.2 Worker处理函数 (`biz/queue/worker.py`)

**修改内容：**
- 在所有 webhook 事件处理函数中添加配置加载逻辑
- 调用 `CodeReviewer` 时传递 `app_name` 参数

**修改的函数：**
1. `handle_push_event()` - GitLab Push 事件处理
2. `handle_merge_request_event()` - GitLab MR 事件处理
3. `handle_github_push_event()` - GitHub Push 事件处理
4. `handle_github_pull_request_event()` - GitHub PR 事件处理

**改动示例：**
```python
def handle_merge_request_event(webhook_data: dict, gitlab_token: str, gitlab_url: str, gitlab_url_slug: str):
    try:
        # 加载应用专属配置
        config_loader.load_env(gitlab_url_slug, override=True)
        
        # ... 其他处理逻辑 ...
        
        # 使用应用专属配置进行 Review
        review_result = CodeReviewer(app_name=gitlab_url_slug).review_and_strip_code(str(changes), commits_text)
```

### 3. 配置文件示例

#### 3.1 示例应用配置 (`conf/example_app/`)

创建了完整的示例配置供参考：
- `conf/example_app/.env` - 示例环境变量配置
- `conf/example_app/prompt_templates.yml` - 示例 Prompt 模板配置

#### 3.2 配置文件结构

```
conf/
├── .env                          # 默认环境变量配置
├── prompt_templates.yml          # 默认 Prompt 模板
├── example_app/                  # 示例应用配置
│   ├── .env
│   └── prompt_templates.yml
├── {app_name_1}/                 # 应用1的专属配置
│   ├── .env
│   └── prompt_templates.yml
└── {app_name_2}/                 # 应用2的专属配置
    └── .env
```

### 4. 文档

#### 4.1 应用专属配置指南 (`doc/app_config_guide.md`)

详细说明文档，包含：
- 功能概述
- 配置优先级
- URL Slug 生成规则
- 配置步骤（创建目录、配置文件）
- 使用场景示例（不同 LLM、不同风格、不同消息群等）
- 配置文件结构示例
- 技术实现原理
- 注意事项和常见问题

#### 4.2 README 更新

在 README.md 的功能介绍部分增加了应用专属配置功能的说明。

### 5. 单元测试

#### 5.1 配置加载器测试 (`biz/utils/test_config_loader.py`)

创建了全面的单元测试，覆盖以下场景：
- 单例模式验证
- 默认配置文件路径获取
- 应用专属配置文件路径获取
- 配置文件降级（应用配置不存在时使用默认配置）
- Prompt 模板加载（默认和应用专属）
- 应用配置目录创建

**测试结果：**
```
Ran 9 tests in 0.100s
OK
```

## URL Slug 生成规则

应用名称由 `slugify_url()` 函数生成，规则如下：

1. 移除 URL 的协议前缀（`http://`、`https://`）
2. 将非字母数字字符替换为下划线
3. 移除末尾的下划线

**示例：**
```
http://gitlab.example.com/          => gitlab_example_com
https://github.com/user/repo.git    => github_com_user_repo_git
http://git.test.cn:8080/project     => git_test_cn_8080_project
```

## 配置优先级

系统采用以下配置加载优先级：

1. **应用专属配置** > **默认配置**
   - `.env`: `conf/{app_name}/.env` > `conf/.env`
   - `prompt_templates.yml`: `conf/{app_name}/prompt_templates.yml` > `conf/prompt_templates.yml`

2. 如果应用专属配置文件不存在，则自动降级使用默认配置

## 使用场景

### 场景一：不同项目使用不同的 LLM

```
项目 A (gitlab.company.com) - 使用 DeepSeek
项目 B (github.com) - 使用 ZhipuAI
```

### 场景二：不同项目使用不同的 Review 风格

```
严肃项目 (git.product.com) - professional 风格
内部项目 (git.internal.com) - humorous 风格
```

### 场景三：不同项目发送到不同的消息群

```
团队 A - 发送到团队 A 的企微群
团队 B - 发送到团队 B 的企微群
```

### 场景四：不同项目使用不同的 Prompt 模板

```
前端项目 - 专注于 Vue/React 代码审查
后端项目 - 专注于 Java/Python 代码审查
```

## 技术实现亮点

1. **单例模式**：`ConfigLoader` 采用单例模式，确保全局唯一实例
2. **灵活降级**：配置文件不存在时自动降级到默认配置，保证系统稳定性
3. **配置覆盖**：使用 `load_dotenv(override=True)` 确保应用专属配置能覆盖默认配置
4. **日志可追踪**：关键操作都有详细日志输出，便于调试和问题排查
5. **完善测试**：提供完整的单元测试，保证功能可靠性

## 兼容性说明

1. **向后兼容**：如果不创建应用专属配置，系统会自动使用默认配置，与之前行为一致
2. **可选参数**：所有新增的 `app_name` 参数都是可选的，默认为 `None`
3. **渐进式升级**：可以逐步为不同项目添加专属配置，无需一次性全部配置

## 注意事项

1. **配置文件编码**：所有配置文件必须使用 UTF-8 编码
2. **目录命名**：应用配置目录名必须与 URL Slug 完全一致
3. **配置热更新**：
   - Docker 部署：修改配置后需要重启容器
   - 本地运行：修改配置后需要重启服务
4. **完整性**：应用专属的 `.env` 文件需要包含所有必要的配置项（建议从默认配置复制后修改）

## 验证方法

### 1. 查看日志

系统会输出配置加载的日志：
```
[INFO] ConfigLoader设置应用名称: gitlab_example_com
[INFO] 使用应用专属配置: conf/gitlab_example_com/.env
[INFO] 成功加载Prompt模板 code_review_prompt from conf/gitlab_example_com/prompt_templates.yml
```

### 2. 运行单元测试

```bash
python -m unittest biz.utils.test_config_loader -v
```

### 3. 实际测试

1. 创建应用专属配置目录：`conf/test_app/`
2. 复制并修改 `.env` 和 `prompt_templates.yml`
3. 使用对应的 GitLab URL 触发 webhook
4. 观察日志确认使用了正确的配置

## 相关文件清单

### 新增文件
- `biz/utils/config_loader.py` - 配置加载器核心实现
- `biz/utils/test_config_loader.py` - 单元测试
- `conf/example_app/.env` - 示例环境变量配置
- `conf/example_app/prompt_templates.yml` - 示例 Prompt 模板
- `doc/app_config_guide.md` - 详细使用指南

### 修改文件
- `biz/utils/code_reviewer.py` - 支持应用名参数
- `biz/queue/worker.py` - 在 webhook 处理中加载应用配置
- `README.md` - 功能介绍更新

## 后续优化建议

1. **配置管理界面**：可以考虑在 Dashboard 中增加配置管理界面，支持在线编辑应用配置
2. **配置模板**：提供更多场景的配置模板供用户选择
3. **配置校验**：增加配置文件的合法性校验，提前发现配置错误
4. **热加载**：支持配置文件的热加载，修改配置后无需重启服务
5. **配置继承**：支持应用配置继承默认配置，只需配置差异部分

## 总结

本次改造实现了应用专属配置功能，使得系统能够支持多项目、多团队的差异化配置需求。通过合理的设计和完善的测试，保证了功能的可靠性和向后兼容性。配合详细的文档和示例，用户可以轻松上手使用该功能。
