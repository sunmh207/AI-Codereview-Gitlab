<template>
  <div class="dashboard-container">
    <!-- Header -->
    <div class="dashboard-header">
      <div class="dashboard-title">
        <el-icon><Monitor /></el-icon>
        📊 代码审查统计
      </div>
      <div class="dashboard-actions">
        <span style="margin-right: 16px; color: #606266;">
          欢迎，{{ authStore.username }}
        </span>
        <el-button type="primary" @click="handleLogout">
          退出登录
        </el-button>
      </div>
    </div>

    <!-- Content -->
    <div class="dashboard-content">
      <!-- Filters -->
      <div class="dashboard-filters">
        <el-row :gutter="16">
          <el-col :span="6">
            <el-date-picker
              v-model="filters.startDate"
              type="date"
              placeholder="开始日期"
              style="width: 100%"
              @change="onDateChange"
            />
          </el-col>
          <el-col :span="6">
            <el-date-picker
              v-model="filters.endDate"
              type="date"
              placeholder="结束日期"
              style="width: 100%"
              @change="onDateChange"
            />
          </el-col>
          <el-col :span="6">
            <el-select
              v-model="filters.selectedAuthors"
              multiple
              placeholder="开发者"
              style="width: 100%"
              clearable
              @change="onFiltersChange"
            >
              <el-option
                v-for="author in metadata.authors"
                :key="author"
                :label="author"
                :value="author"
              />
            </el-select>
          </el-col>
          <el-col :span="6">
            <el-select
              v-model="filters.selectedProjects"
              multiple
              placeholder="项目名称"
              style="width: 100%"
              clearable
              @change="onFiltersChange"
            >
              <el-option
                v-for="project in metadata.project_names"
                :key="project"
                :label="project"
                :value="project"
              />
            </el-select>
          </el-col>
        </el-row>
      </div>

      <!-- Tabs -->
      <div class="dashboard-tabs">
        <el-tabs v-model="activeTab" @tab-change="onTabChange">
          <!-- Merge Request Tab -->
          <el-tab-pane label="合并请求" name="mr">
            <ReviewDataTable
              :data="mrData"
              :loading="mrLoading"
              :total="mrTotal"
              type="mr"
            />
            <div class="table-summary">
              <span><strong>总记录数:</strong> {{ mrTotal }}</span>
              <span><strong>平均得分:</strong> {{ formatScore(mrAverageScore) }}</span>
            </div>
          </el-tab-pane>

          <!-- Push Tab (if enabled) -->
          <el-tab-pane v-if="metadata.push_review_enabled" label="代码推送" name="push">
            <ReviewDataTable
              :data="pushData"
              :loading="pushLoading"
              :total="pushTotal"
              type="push"
            />
            <div class="table-summary">
              <span><strong>总记录数:</strong> {{ pushTotal }}</span>
              <span><strong>平均得分:</strong> {{ formatScore(pushAverageScore) }}</span>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>

      <!-- Statistics Charts -->
      <StatisticsCharts
        :data="currentTabData"
        :loading="currentTabLoading"
        :type="activeTab as 'mr' | 'push'"
        :filters="chartFilters"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import { Monitor } from '@element-plus/icons-vue'
import {
  getMRReviews,
  getPushReviews,
  getMetadata,
  type ReviewData,
  type MetadataResponse,
  type ReviewFilters
} from '@/api/reviews'
import { getDefaultDateRange, formatDateForAPI } from '@/utils/date'
import { formatScore } from '@/utils/format'
import ReviewDataTable from '@/components/ReviewDataTable.vue'
import StatisticsCharts from '@/components/StatisticsCharts.vue'

const router = useRouter()
const authStore = useAuthStore()

// Data states
const activeTab = ref<'mr' | 'push'>('mr')
const mrData = ref<ReviewData[]>([])
const pushData = ref<ReviewData[]>([])
const mrLoading = ref(false)
const pushLoading = ref(false)
const mrTotal = ref(0)
const pushTotal = ref(0)

// Metadata
const metadata = ref<MetadataResponse>({
  authors: [],
  project_names: [],
  push_review_enabled: false
})

// Filters
const filters = reactive({
  startDate: '',
  endDate: '',
  selectedAuthors: [] as string[],
  selectedProjects: [] as string[]
})

// Computed properties
const currentTabData = computed(() => activeTab.value === 'mr' ? mrData.value : pushData.value)
const currentTabLoading = computed(() => activeTab.value === 'mr' ? mrLoading.value : pushLoading.value)

const mrAverageScore = computed(() => {
  if (mrData.value.length === 0) return 0
  return mrData.value.reduce((sum, item) => sum + item.score, 0) / mrData.value.length
})

const pushAverageScore = computed(() => {
  if (pushData.value.length === 0) return 0
  return pushData.value.reduce((sum, item) => sum + item.score, 0) / pushData.value.length
})

const chartFilters = computed((): ReviewFilters => ({
  start_date: filters.startDate ? formatDateForAPI(filters.startDate) : undefined,
  end_date: filters.endDate ? formatDateForAPI(filters.endDate) : undefined,
  authors: filters.selectedAuthors.length > 0 ? filters.selectedAuthors : undefined,
  project_names: filters.selectedProjects.length > 0 ? filters.selectedProjects : undefined
}))

// Methods
const handleLogout = async () => {
  try {
    await authStore.logout()
    ElMessage.success('已退出登录')
    router.push('/login')
  } catch (error: any) {
    ElMessage.error('退出登录失败')
  }
}

const loadMetadata = async () => {
  try {
    const result = await getMetadata({
      start_date: filters.startDate ? formatDateForAPI(filters.startDate) : undefined,
      end_date: filters.endDate ? formatDateForAPI(filters.endDate) : undefined,
      type: activeTab.value
    })
    metadata.value = result
  } catch (error: any) {
    ElMessage.error('获取元数据失败')
  }
}

const loadMRData = async () => {
  if (activeTab.value !== 'mr') return

  mrLoading.value = true
  try {
    const result = await getMRReviews(chartFilters.value)
    mrData.value = result.data
    mrTotal.value = result.total
  } catch (error: any) {
    ElMessage.error('获取合并请求数据失败')
  } finally {
    mrLoading.value = false
  }
}

const loadPushData = async () => {
  if (activeTab.value !== 'push' || !metadata.value.push_review_enabled) return

  pushLoading.value = true
  try {
    const result = await getPushReviews(chartFilters.value)
    pushData.value = result.data
    pushTotal.value = result.total
  } catch (error: any) {
    ElMessage.error('获取推送数据失败')
  } finally {
    pushLoading.value = false
  }
}

const loadCurrentTabData = async () => {
  if (activeTab.value === 'mr') {
    await loadMRData()
  } else {
    await loadPushData()
  }
}

const initializeFilters = () => {
  const [startDate, endDate] = getDefaultDateRange()
  filters.startDate = startDate
  filters.endDate = endDate
}

// Event handlers
const onDateChange = () => {
  loadMetadata()
  loadCurrentTabData()
}

const onFiltersChange = () => {
  loadCurrentTabData()
}

const onTabChange = () => {
  loadMetadata()
  loadCurrentTabData()
}

// Watchers
watch(() => activeTab.value, () => {
  // Reset filters when switching tabs
  filters.selectedAuthors = []
  filters.selectedProjects = []
})

// Lifecycle
onMounted(async () => {
  initializeFilters()
  await loadMetadata()
  await loadCurrentTabData()
})
</script>

<style scoped>
.dashboard-container {
  min-height: 100vh;
  background-color: #f0f2f5;
}

.dashboard-header {
  background: white;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  padding: 0 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
}

.dashboard-title {
  font-size: 20px;
  font-weight: bold;
  color: #2E4053;
  display: flex;
  align-items: center;
  gap: 10px;
}

.dashboard-actions {
  display: flex;
  align-items: center;
}

.dashboard-content {
  padding: 20px;
}

.dashboard-filters {
  background: white;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.dashboard-tabs {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  overflow: hidden;
  margin-bottom: 20px;
}

.table-summary {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 16px 20px;
  background: #f8f9fa;
  border-top: 1px solid #ebeef5;
  font-size: 14px;
  color: #606266;
}

@media (max-width: 768px) {
  .dashboard-header {
    padding: 0 16px;
    flex-direction: column;
    height: auto;
    padding: 16px;
    gap: 10px;
  }

  .dashboard-content {
    padding: 16px;
  }

  .dashboard-filters .el-row .el-col {
    margin-bottom: 12px;
  }
}
</style>