<template>
  <el-dialog
    v-model="visible"
    title="📋 Commit详情"
    width="90%"
    :before-close="handleClose"
  >
    <div v-if="rowData">
      <el-row :gutter="20" class="info-row">
        <el-col :span="6">
          <strong>项目:</strong> {{ rowData.project_name || 'N/A' }}
        </el-col>
        <el-col :span="6">
          <strong>开发者:</strong> {{ rowData.author || 'N/A' }}
        </el-col>
        <el-col :span="6">
          <strong>分支:</strong> {{ rowData.branch || 'N/A' }}
        </el-col>
        <el-col :span="6">
          <strong>更新时间:</strong> {{ rowData.updated_at || 'N/A' }}
        </el-col>
      </el-row>

      <el-divider />

      <div v-if="commits.length > 0">
        <h3>共 {{ commits.length }} 个提交:</h3>
        
        <div v-for="(commit, index) in commits" :key="commit.id" class="commit-item">
          <el-card shadow="hover" class="commit-card">
            <el-row :gutter="20">
              <el-col :span="18">
                <h4 class="commit-title">
                  #{{ index + 1 }} {{ truncateMessage(commit.message) }}
                </h4>
                <div class="commit-meta">
                  👤 {{ commit.author || 'Unknown' }} | 🕒 {{ commit.timestamp || 'Unknown' }}
                </div>
                <el-collapse v-if="commit.message" class="commit-collapse">
                  <el-collapse-item title="查看完整提交信息" name="1">
                    <pre class="commit-message">{{ commit.message }}</pre>
                  </el-collapse-item>
                </el-collapse>
              </el-col>
              <el-col :span="6" class="commit-actions">
                <el-link
                  v-if="commit.url"
                  :href="commit.url"
                  target="_blank"
                  type="primary"
                  class="commit-link"
                >
                  🔗 查看
                </el-link>
                <div class="commit-id">
                  <strong>ID:</strong> <code>{{ commit.id.substring(0, 8) }}...</code>
                </div>
              </el-col>
            </el-row>
          </el-card>
        </div>
      </div>
      
      <div v-else>
        <el-empty description="该记录没有commit详情数据" />
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { Commit, PushLog } from '@/types'

interface Props {
  modelValue: boolean
  rowData: PushLog | null
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const commits = ref<Commit[]>([])

watch(() => props.rowData, (newData) => {
  if (newData && newData.commits_json) {
    try {
      commits.value = JSON.parse(newData.commits_json)
    } catch (error) {
      console.error('无法解析commit数据:', error)
      commits.value = []
    }
  } else {
    commits.value = []
  }
}, { immediate: true })

const truncateMessage = (message: string): string => {
  if (!message) return 'No message'
  return message.length > 80 ? message.substring(0, 80) + '...' : message
}

const handleClose = () => {
  visible.value = false
}
</script>

<style scoped>
.info-row {
  margin-bottom: 20px;
}

.commit-item {
  margin-bottom: 16px;
}

.commit-card {
  border-left: 4px solid #409eff;
}

.commit-title {
  margin: 0 0 8px 0;
  color: #303133;
  font-size: 16px;
  font-weight: 600;
}

.commit-meta {
  color: #909399;
  font-size: 14px;
  margin-bottom: 12px;
}

.commit-collapse {
  margin-top: 8px;
}

.commit-message {
  background-color: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.4;
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
}

.commit-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
}

.commit-link {
  font-size: 14px;
}

.commit-id {
  font-size: 12px;
  color: #909399;
}

.commit-id code {
  background-color: #f1f2f3;
  padding: 2px 4px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
}
</style>
