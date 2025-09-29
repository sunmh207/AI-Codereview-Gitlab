<template>
  <div class="markdown-renderer" v-html="renderedMarkdown"></div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'

interface Props {
  content: string
}

const props = withDefaults(defineProps<Props>(), {
  content: ''
})

// 配置 marked 选项
marked.setOptions({
  breaks: true,
  gfm: true,
  headerIds: false,
  mangle: false
})

const renderedMarkdown = computed(() => {
  if (!props.content) {
    return '<p>暂无审查内容</p>'
  }
  
  try {
    return marked(props.content)
  } catch (error) {
    console.error('Markdown rendering error:', error)
    return `<pre>${props.content}</pre>`
  }
})
</script>

<style scoped>
.markdown-renderer {
  line-height: 1.6;
  color: var(--el-text-color-primary);
}

.markdown-renderer :deep(h1),
.markdown-renderer :deep(h2),
.markdown-renderer :deep(h3),
.markdown-renderer :deep(h4),
.markdown-renderer :deep(h5),
.markdown-renderer :deep(h6) {
  margin: 16px 0 8px 0;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.markdown-renderer :deep(h1) {
  font-size: 1.5em;
  border-bottom: 1px solid var(--el-border-color);
  padding-bottom: 8px;
}

.markdown-renderer :deep(h2) {
  font-size: 1.3em;
}

.markdown-renderer :deep(h3) {
  font-size: 1.1em;
}

.markdown-renderer :deep(p) {
  margin: 8px 0;
}

.markdown-renderer :deep(ul),
.markdown-renderer :deep(ol) {
  margin: 8px 0;
  padding-left: 20px;
}

.markdown-renderer :deep(li) {
  margin: 4px 0;
}

.markdown-renderer :deep(code) {
  background-color: var(--el-fill-color-light);
  padding: 2px 4px;
  border-radius: 3px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 0.9em;
}

.markdown-renderer :deep(pre) {
  background-color: var(--el-fill-color-light);
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 12px 0;
}

.markdown-renderer :deep(pre code) {
  background-color: transparent;
  padding: 0;
}

.markdown-renderer :deep(blockquote) {
  border-left: 4px solid var(--el-color-primary);
  padding-left: 12px;
  margin: 12px 0;
  color: var(--el-text-color-regular);
  background-color: var(--el-fill-color-extra-light);
  padding: 8px 12px;
  border-radius: 0 4px 4px 0;
}

.markdown-renderer :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 12px 0;
}

.markdown-renderer :deep(th),
.markdown-renderer :deep(td) {
  border: 1px solid var(--el-border-color);
  padding: 8px 12px;
  text-align: left;
}

.markdown-renderer :deep(th) {
  background-color: var(--el-fill-color-light);
  font-weight: 600;
}

.markdown-renderer :deep(a) {
  color: var(--el-color-primary);
  text-decoration: none;
}

.markdown-renderer :deep(a:hover) {
  text-decoration: underline;
}

.markdown-renderer :deep(strong) {
  font-weight: 600;
}

.markdown-renderer :deep(em) {
  font-style: italic;
}

.markdown-renderer :deep(hr) {
  border: none;
  border-top: 1px solid var(--el-border-color);
  margin: 16px 0;
}
</style>