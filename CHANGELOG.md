# 更新日志

## v1.1.0 - 2025-09-29

### 新增功能
- ✨ **Markdown渲染支持**: 审查结果(`review_result`)现在支持完整的Markdown格式显示
  - 新增 `MarkdownRenderer.vue` 组件，使用 `marked` 库进行渲染
  - 支持代码高亮、表格、列表等Markdown语法
  - 自定义样式，与系统主题保持一致

- 📜 **审查详情滚动优化**: 改进审查详情对话框的滚动体验
  - 添加自定义滚动条样式
  - 解决双滚动条问题，提供流畅的单一滚动体验
  - 响应式高度设置，适配不同屏幕尺寸

### 界面改进
- 🎨 **图标修复**: 修复前端缺失的Element Plus图标
  - 将不存在的 `PullRequest` 图标替换为 `FolderOpened`
  - 将不存在的 `Robot` 图标替换为 `Service`

- 💻 **用户体验优化**: 
  - 审查详情对话框最大高度设置为80vh
  - 优化内容区域的内边距和间距
  - 改进滚动条视觉效果

### 技术改进
- 🔧 **类型定义完善**: 更新TypeScript接口定义
  - 在 `ReviewData` 接口中添加 `review_result` 和 `title` 字段
  - 修复字段名称不匹配问题 (`commit_message` → `commit_messages`)

- 📦 **依赖更新**: 
  - 新增 `marked` 库用于Markdown渲染
  - 新增 `@vueuse/integrations` 用于Vue集成

### 修复问题
- 🐛 **服务连接**: 修复后端服务连接中断问题
- 🐛 **前端空白页**: 解决因缺失图标导致的前端空白页问题
- 🐛 **字段映射**: 修复前后端字段名称不一致问题

### 文件变更
#### 前端文件
- `frontend/src/components/MarkdownRenderer.vue` - 新增Markdown渲染组件
- `frontend/src/layouts/AdminLayout.vue` - 修复图标引用
- `frontend/src/api/reviews.ts` - 更新接口类型定义
- `frontend/src/views/admin/MRReviewsView.vue` - 集成Markdown渲染和滚动优化
- `frontend/src/views/admin/PushReviewsView.vue` - 集成Markdown渲染和滚动优化
- `frontend/package.json` - 添加新依赖

#### 配置文件
- `.gitignore` - 确保敏感配置文件不被提交

### 部署说明
1. 前端需要重新安装依赖: `npm install`
2. 后端无需额外配置
3. 确保 `.env` 文件配置正确但不提交到版本控制

---

## 开发者注意事项
- 本次更新主要集中在前端用户体验改进
- 新增的Markdown渲染组件可复用于其他需要显示Markdown内容的地方
- 滚动条样式已统一，后续开发请保持一致性