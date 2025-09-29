<template>
  <div class="data-table">
    <el-table
      :data="formattedData"
      v-loading="loading"
      stripe
      border
      style="width: 100%"
      :default-sort="{ prop: 'updated_at', order: 'descending' }"
      empty-text="暂无数据"
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
        width="170"
        sortable
        show-overflow-tooltip
      />

      <el-table-column
        prop="commit_messages"
        label="提交信息"
        min-width="200"
        show-overflow-tooltip
      >
        <template #default="{ row }">
          <el-tooltip :content="row.commit_messages" placement="top">
            <span>{{ truncateText(row.commit_messages, 50) }}</span>
          </el-tooltip>
        </template>
      </el-table-column>

      <el-table-column
        prop="delta"
        label="变更"
        width="120"
        align="center"
      >
        <template #default="{ row }">
          <span v-if="row.delta" class="delta-text">
            {{ row.delta }}
          </span>
          <span v-else>-</span>
        </template>
      </el-table-column>

      <el-table-column
        prop="score"
        label="得分"
        width="100"
        align="center"
        sortable
      >
        <template #default="{ row }">
          <el-progress
            :percentage="row.score"
            :color="getScoreColor(row.score)"
            :stroke-width="16"
            text-inside
            :format="() => row.score.toFixed(0)"
          />
        </template>
      </el-table-column>

      <el-table-column
        v-if="type === 'mr'"
        label="操作"
        width="100"
        align="center"
      >
        <template #default="{ row }">
          <el-button
            v-if="row.url"
            type="primary"
            size="small"
            @click="openUrl(row.url)"
          >
            查看详情
          </el-button>
          <span v-else>-</span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ReviewData } from '@/api/reviews'
import { formatTableData, truncateText, getScoreColor } from '@/utils/format'

interface Props {
  data: ReviewData[]
  loading: boolean
  total: number
  type: 'mr' | 'push'
}

const props = defineProps<Props>()

const formattedData = computed(() => formatTableData(props.data))

const openUrl = (url: string) => {
  if (url) {
    window.open(url, '_blank')
  }
}
</script>

<style scoped>
.data-table {
  margin-bottom: 20px;
}

.delta-text {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  font-weight: bold;
}

:deep(.el-table) {
  font-size: 14px;
}

:deep(.el-table th) {
  background-color: #fafafa;
  color: #606266;
  font-weight: 600;
}

:deep(.el-table .el-table__cell) {
  padding: 8px 0;
}

:deep(.el-progress-bar__inner) {
  transition: width 0.3s ease;
}

:deep(.el-progress__text) {
  font-size: 12px !important;
  font-weight: bold;
}
</style>