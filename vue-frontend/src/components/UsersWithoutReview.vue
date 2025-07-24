<template>
  <div class="users-without-review-container">
    <!-- 筛选条件 -->
    <el-card class="filter-card" shadow="never">
      <el-row :gutter="20" align="middle">
        <el-col :span="6">
          <el-select
            v-model="selectedTimeRange"
            placeholder="选择时间范围"
            style="width: 100%"
            @change="handleTimeRangeChange"
          >
            <el-option
              v-for="option in timeRangeOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-col>

        <el-col :span="6">
          <el-date-picker
            v-model="customStartDate"
            type="date"
            placeholder="自定义开始日期"
            style="width: 100%"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            :disabled="selectedTimeRange !== 'custom'"
            @change="handleCustomDateChange"
          />
        </el-col>

        <el-col :span="6">
          <el-date-picker
            v-model="customEndDate"
            type="date"
            placeholder="自定义结束日期"
            style="width: 100%"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            :disabled="selectedTimeRange !== 'custom'"
            @change="handleCustomDateChange"
          />
        </el-col>

        <el-col :span="6">
          <el-button
            type="primary"
            :loading="loading"
            @click="loadData"
          >
            <el-icon><Refresh /></el-icon>
            刷新数据
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 统计信息 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-number">{{ data.total_developers }}</div>
            <div class="stat-label">总开发者数</div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-number unreviewed">{{ data.total_unreviewed_users }}</div>
            <div class="stat-label">未审查用户数</div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-number coverage">{{ data.review_coverage_rate }}%</div>
            <div class="stat-label">审查覆盖率</div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-label time-range">{{ data.time_range }}</div>
            <div class="stat-sublabel">统计时间范围</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 未审查用户列表 -->
    <el-card class="users-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span class="card-title">
            <el-icon><UserFilled /></el-icon>
            未审查用户列表
          </span>
          <el-button
            type="primary"
            size="small"
            @click="exportData"
            :disabled="data.users_without_review.length === 0"
          >
            <el-icon><Download /></el-icon>
            导出列表
          </el-button>
        </div>
      </template>

      <div v-loading="loading">
        <el-empty
          v-if="data.users_without_review.length === 0 && !loading"
          description="暂无未审查用户"
          :image-size="100"
        />

        <el-table
          v-else
          :data="paginatedUsers"
          stripe
          border
          style="width: 100%"
        >
          <el-table-column
            prop="name"
            label="姓名"
            width="200"
            show-overflow-tooltip
          />

          <el-table-column
            prop="group"
            label="分组"
            width="120"
            show-overflow-tooltip
          />

          <el-table-column
            prop="gitlab_username"
            label="GitLab用户名"
            show-overflow-tooltip
          />

          <el-table-column
            label="操作"
            width="120"
            align="center"
          >
            <template #default="{ row }">
              <el-button
                type="primary"
                size="small"
                @click="viewUserProfile(row)"
              >
                查看详情
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="pagination-container" v-if="data.users_without_review.length > 0">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :small="false"
            :disabled="loading"
            :background="true"
            layout="total, sizes, prev, pager, next, jumper"
            :total="data.users_without_review.length"
          />
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, UserFilled, Download } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { reviewApi } from '@/api'
import type { UsersWithoutReviewData, TimeRangeOption, Developer } from '@/types'

// 响应式数据
const loading = ref(false)
const selectedTimeRange = ref('week')
const customStartDate = ref('')
const customEndDate = ref('')
const currentPage = ref(1)
const pageSize = ref(20)

const data = reactive<UsersWithoutReviewData>({
  users_without_review: [],
  total_developers: 0,
  total_unreviewed_users: 0,
  review_coverage_rate: 0,
  time_range: ''
})

// 时间范围选项
const timeRangeOptions: TimeRangeOption[] = [
  { label: '近一周', value: 'week' },
  { label: '当天', value: 'today' },
  { label: '历史所有', value: 'all' },
  { label: '自定义时间', value: 'custom' }
]

// 计算属性
const paginatedUsers = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return data.users_without_review.slice(start, end)
})

// 方法
const loadData = async () => {
  try {
    loading.value = true

    let params: any = {}

    if (selectedTimeRange.value === 'custom') {
      if (!customStartDate.value || !customEndDate.value) {
        ElMessage.warning('请选择自定义时间范围')
        return
      }
      params.start_time = dayjs(customStartDate.value).unix()
      params.end_time = dayjs(customEndDate.value).endOf('day').unix()
    } else {
      params.time_range = selectedTimeRange.value
    }

    const response = await reviewApi.getUsersWithoutReview(params)

    // 更新数据
    Object.assign(data, response)

    // 重置分页
    currentPage.value = 1

    ElMessage.success('数据加载成功')
  } catch (error) {
    console.error('Failed to load users without review:', error)
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

const handleTimeRangeChange = () => {
  if (selectedTimeRange.value !== 'custom') {
    customStartDate.value = ''
    customEndDate.value = ''
    loadData()
  }
}

const handleCustomDateChange = () => {
  if (selectedTimeRange.value === 'custom' && customStartDate.value && customEndDate.value) {
    loadData()
  }
}

const viewUserProfile = (user: Developer) => {
  ElMessageBox.alert(
    `姓名: ${user.name}\nGitLab用户名: ${user.gitlab_username}`,
    '用户详情',
    {
      confirmButtonText: '确定',
      type: 'info'
    }
  )
}

const exportData = () => {
  try {
    const csvContent = [
      ['姓名', '分组', 'GitLab用户名'],
      ...data.users_without_review.map(user => [user.name, user.group || '', user.gitlab_username])
    ].map(row => row.join(',')).join('\n')

    const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', `未审查用户列表_${dayjs().format('YYYY-MM-DD')}.csv`)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    ElMessage.success('导出成功')
  } catch (error) {
    console.error('Export failed:', error)
    ElMessage.error('导出失败')
  }
}

// 组件挂载
onMounted(() => {
  loadData()
})
</script>

<style scoped>
.users-without-review-container {
  padding: 20px;
}

.filter-card {
  margin-bottom: 20px;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
}

.stat-content {
  padding: 10px;
}

.stat-number {
  font-size: 2.5rem;
  font-weight: bold;
  color: #409eff;
  margin-bottom: 8px;
}

.stat-number.unreviewed {
  color: #f56c6c;
}

.stat-number.coverage {
  color: #67c23a;
}

.stat-label {
  font-size: 1rem;
  color: #606266;
  font-weight: 500;
}

.stat-label.time-range {
  font-size: 1.1rem;
  color: #409eff;
  font-weight: 600;
}

.stat-sublabel {
  font-size: 0.9rem;
  color: #909399;
  margin-top: 4px;
}

.users-card {
  background: white;
  border-radius: 8px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.pagination-container {
  display: flex;
  justify-content: center;
  padding: 20px 0;
  border-top: 1px solid #e9ecef;
  margin-top: 20px;
}

:deep(.el-table th) {
  background-color: #fafafa;
  color: #606266;
  font-weight: 600;
}

:deep(.el-table td) {
  padding: 12px 0;
}
</style>
