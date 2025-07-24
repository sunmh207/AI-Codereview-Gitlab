<template>
  <div class="data-table-container">
    <div class="table-header">
      <span class="table-stats">
        <strong>总记录数:</strong> {{ total }}，
        <strong>平均得分:</strong> {{ averageScore.toFixed(2) }}
      </span>
    </div>

    <el-table
      :data="data"
      style="width: 100%"
      stripe
      border
      :default-sort="{ prop: 'updated_at', order: 'descending' }"
      v-loading="loading"
    >
      <el-table-column
        prop="project_name"
        label="项目名称"
        width="150"
        show-overflow-tooltip
      />
      
      <el-table-column
        prop="author"
        label="开发者"
        width="120"
        show-overflow-tooltip
      />
      
      <el-table-column
        v-if="type === 'mr'"
        prop="source_branch"
        label="源分支"
        width="120"
        show-overflow-tooltip
      />
      
      <el-table-column
        v-if="type === 'mr'"
        prop="target_branch"
        label="目标分支"
        width="120"
        show-overflow-tooltip
      />
      
      <el-table-column
        v-if="type === 'push'"
        prop="branch"
        label="分支"
        width="120"
        show-overflow-tooltip
      />
      
      <el-table-column
        prop="updated_at"
        label="更新时间"
        width="160"
        sortable
      />
      
      <el-table-column
        prop="commit_messages"
        label="提交信息"
        min-width="200"
        show-overflow-tooltip
      />
      
      <el-table-column
        prop="delta"
        label="变更"
        width="120"
        align="center"
      >
        <template #default="{ row }">
          <span class="delta-text">{{ row.delta }}</span>
        </template>
      </el-table-column>
      
      <el-table-column
        prop="score"
        label="得分"
        width="120"
        align="center"
      >
        <template #default="{ row }">
          <div class="score-progress">
            <el-progress
              :percentage="row.score"
              :color="getScoreColor(row.score)"
              :stroke-width="6"
              :text-inside="true"
              :format="(percentage) => `${percentage}%`"
            />
          </div>
        </template>
      </el-table-column>
      
      <el-table-column
        v-if="type === 'mr'"
        label="操作"
        width="100"
        align="center"
      >
        <template #default="{ row }">
          <el-link
            :href="row.url"
            target="_blank"
            type="primary"
          >
            查看详情
          </el-link>
        </template>
      </el-table-column>
      
      <el-table-column
        v-if="type === 'push'"
        label="查看详情"
        width="100"
        align="center"
      >
        <template #default="{ row }">
          <el-button
            type="primary"
            size="small"
            @click="handleShowCommitDetails(row)"
          >
            查看详情
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页组件 -->
    <div class="pagination-container">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :small="false"
        :disabled="loading"
        :background="true"
        layout="total, sizes, prev, pager, next, jumper"
        :total="total"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { MergeRequestLog, PushLog } from '@/types'

interface Props {
  data: (MergeRequestLog | PushLog)[]
  type: 'mr' | 'push'
  loading?: boolean
  total?: number
  currentPage?: number
  pageSize?: number
}

interface Emits {
  (e: 'show-commit-details', row: PushLog): void
  (e: 'page-change', page: number): void
  (e: 'size-change', size: number): void
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  total: 0,
  currentPage: 1,
  pageSize: 10
})

const emit = defineEmits<Emits>()

const currentPage = ref(props.currentPage)
const pageSize = ref(props.pageSize)

const averageScore = computed(() => {
  if (props.data.length === 0) return 0
  const total = props.data.reduce((sum, item) => sum + item.score, 0)
  return total / props.data.length
})

const getScoreColor = (score: number) => {
  if (score >= 90) return '#67c23a'
  if (score >= 80) return '#e6a23c'
  if (score >= 70) return '#f56c6c'
  return '#909399'
}

const handleShowCommitDetails = (row: PushLog) => {
  emit('show-commit-details', row)
}

const handleCurrentChange = (page: number) => {
  currentPage.value = page
  emit('page-change', page)
}

const handleSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  emit('size-change', size)
}
</script>

<style scoped>
.data-table-container {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.table-header {
  padding: 16px 20px;
  background-color: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.table-stats {
  font-size: 14px;
  color: #606266;
}

.delta-text {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #606266;
}

:deep(.el-table) {
  border-radius: 0;
}

:deep(.el-table th) {
  background-color: #fafafa;
  color: #606266;
  font-weight: 600;
}

:deep(.el-table td) {
  padding: 12px 0;
}

:deep(.el-progress-bar__outer) {
  border-radius: 4px;
}

:deep(.el-progress-bar__inner) {
  border-radius: 4px;
}

.score-progress {
  width: 100%;
  padding: 0 8px;
}

.score-progress :deep(.el-progress) {
  width: 100%;
}

.score-progress :deep(.el-progress-bar) {
  padding-right: 0;
  margin-right: 0;
}

.score-progress :deep(.el-progress-bar__outer) {
  height: 18px !important;
}

.score-progress :deep(.el-progress__text) {
  font-size: 12px;
  color: #606266;
  margin-left: 4px;
}

.pagination-container {
  display: flex;
  justify-content: center;
  padding: 20px 0;
  background-color: #fafafa;
  border-top: 1px solid #e9ecef;
}
</style>
