<template>
  <div class="modal fade show" 
       tabindex="-1" 
       style="display: block;"
       @click.self="$emit('close')">
    <div class="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">提交详情</h5>
          <button type="button" 
                  class="btn-close" 
                  @click="$emit('close')" 
                  aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <div class="row">
            <div class="col-md-6">
              <p><strong>项目：</strong> {{ mrData.project_name }}</p>
              <p><strong>开发者：</strong> {{ mrData.author }}</p>
              <p><strong>源分支：</strong> {{ mrData.branch }}</p>
              <p><strong>目标分支：</strong> {{ mrData.target_branch }}</p>
              <p><strong>更新时间：</strong> {{ formatDate(mrData.updated_at) }}</p>
            </div>
            <div class="col-md-6">
              <p><strong>提交信息：</strong> {{ mrData.commit_messages }}</p>
              <p><strong>评分：</strong></p>
              <div class="progress">
                <div class="progress-bar"
                     role="progressbar"
                     :style="{ width: `${mrData.score || 0}%` }"
                     :aria-valuenow="mrData.score || 0"
                     aria-valuemin="0"
                     aria-valuemax="100">
                  {{ mrData.score || 0 }}
                </div>
              </div>
            </div>
          </div>
          <div>
            <p><strong>审查结果：</strong></p>
            <div class="markdown-content" v-html="renderMarkdown(mrData.review_result)"></div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" 
                  class="btn btn-secondary" 
                  @click="$emit('close')">退出</button>
        </div>
      </div>
    </div>
  </div>
  <div class="modal-backdrop fade show"></div>
</template>

<script>
import { marked } from 'marked';

export default {
  name: 'DetailModal',
  props: {
    mrData: {
      type: Object,
      required: true
    }
  },
  methods: {
    formatDate(timestamp) {
      return new Date(timestamp * 1000).toLocaleString()
    },
    renderMarkdown(content) {
      return marked(content || '');
    }
  }
}
</script>

<style scoped>
.modal-body :deep(.markdown-content) {
  max-height: 600px;
  overflow-y: auto;
}

.modal-body :deep(.markdown-content) h1,
.modal-body :deep(.markdown-content) h2,
.modal-body :deep(.markdown-content) h3,
.modal-body :deep(.markdown-content) h4,
.modal-body :deep(.markdown-content) h5,
.modal-body :deep(.markdown-content) h6 {
  margin-top: 1rem;
  margin-bottom: 0.5rem;
}

.modal-body :deep(.markdown-content) p {
  margin-bottom: 1rem;
}

.modal-body :deep(.markdown-content) code {
  background-color: #f8f9fa;
  padding: 0.2rem 0.4rem;
  border-radius: 0.25rem;
}

.modal-body :deep(.markdown-content) pre {
  background-color: #f8f9fa;
  padding: 1rem;
  border-radius: 0.25rem;
  overflow-x: auto;
}

.modal-body :deep(.markdown-content) table {
  width: 100%;
  margin-bottom: 1rem;
  border-collapse: collapse;
  border: 1px solid #dee2e6;
}

.modal-body :deep(.markdown-content) th,
.modal-body :deep(.markdown-content) td {
  padding: 0.75rem;
  border: 1px solid #dee2e6;
  text-align: left;
}

.modal-body :deep(.markdown-content) th {
  background-color: #f8f9fa;
  font-weight: 600;
}

.modal-body :deep(.markdown-content) tr:nth-child(even) {
  background-color: #f8f9fa;
}

.modal-body :deep(.markdown-content) tr:hover {
  background-color: #f2f2f2;
}

.modal-xl {
  max-width: 90vw;
}

.modal-dialog-scrollable .modal-body {
  max-height: 75vh;
  overflow-y: auto;
}

@media (max-width: 768px) {
  .modal-xl {
    max-width: 95vw;
  }
  .modal-body :deep(.markdown-content) {
    font-size: 0.9rem;
  }
}
</style> 