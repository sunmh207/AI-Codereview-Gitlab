<template>
  <div class="dashboard-container">
    <!-- 头部 -->
    <el-header class="dashboard-header">
      <div class="header-content">
        <h2 class="header-title">📊 代码审查统计</h2>
        <div class="header-actions">
          <span class="welcome-text">欢迎，{{ authStore.user?.username }}</span>
          <el-button type="danger" @click="handleLogout">
            退出登录
          </el-button>
        </div>
      </div>
    </el-header>

    <!-- 主内容 -->
    <el-main class="dashboard-main">
      <!-- 筛选条件 -->
      <el-card class="filter-card" shadow="never">
        <el-row :gutter="20">
          <el-col :span="6">
            <el-date-picker
              v-model="filters.startDate"
              type="date"
              placeholder="开始日期"
              style="width: 100%"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
            />
          </el-col>
          <el-col :span="6">
            <el-date-picker
              v-model="filters.endDate"
              type="date"
              placeholder="结束日期"
              style="width: 100%"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
            />
          </el-col>
          <el-col :span="6">
            <el-select
              v-model="filters.authors"
              multiple
              placeholder="选择开发者"
              style="width: 100%"
              clearable
            >
              <el-option
                v-for="author in availableAuthors"
                :key="author"
                :label="author"
                :value="author"
              />
            </el-select>
          </el-col>
          <el-col :span="6">
            <el-select
              v-model="filters.projectNames"
              multiple
              placeholder="选择项目"
              style="width: 100%"
              clearable
            >
              <el-option
                v-for="project in availableProjects"
                :key="project"
                :label="project"
                :value="project"
              />
            </el-select>
          </el-col>
        </el-row>
      </el-card>

      <!-- 标签页 -->
      <el-tabs v-model="activeTab" class="data-tabs">
        <el-tab-pane label="合并请求" name="mr">
          <DataTable
            :data="mrData"
            type="mr"
            :loading="mrLoading"
            :total="mrPagination.total"
            :current-page="mrPagination.currentPage"
            :page-size="mrPagination.pageSize"
            @page-change="handleMrPageChange"
            @size-change="handleMrSizeChange"
          />
        </el-tab-pane>

        <el-tab-pane v-if="showPushTab" label="代码推送" name="push">
          <DataTable
            :data="pushData"
            type="push"
            :loading="pushLoading"
            :total="pushPagination.total"
            :current-page="pushPagination.currentPage"
            :page-size="pushPagination.pageSize"
            @show-commit-details="handleShowCommitDetails"
            @page-change="handlePushPageChange"
            @size-change="handlePushSizeChange"
          />
        </el-tab-pane>

        <el-tab-pane label="未审查用户" name="users-without-review">
          <UsersWithoutReview />
        </el-tab-pane>
      </el-tabs>

      <!-- 图表 -->
      <Charts
        v-if="activeTab !== 'users-without-review'"
        :data="currentTabChartData"
        :loading="chartLoading"
      />
    </el-main>

    <!-- Commit详情模态框 -->
    <CommitModal
      v-model="commitModalVisible"
      :row-data="selectedCommitRow"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import { useAuthStore } from '@/stores/auth'
import { reviewApi } from '@/api'
import DataTable from '@/components/DataTable.vue'
import Charts from '@/components/Charts.vue'
import CommitModal from '@/components/CommitModal.vue'
import UsersWithoutReview from '@/components/UsersWithoutReview.vue'
import type { MergeRequestLog, PushLog, FilterParams } from '@/types'

const router = useRouter()
const authStore = useAuthStore()

// 响应式数据
const activeTab = ref('mr')

// 表格数据（分页）
const mrData = ref<MergeRequestLog[]>([])
const pushData = ref<PushLog[]>([])
const mrLoading = ref(false)
const pushLoading = ref(false)

// 图表数据（全量）
const mrChartData = ref<MergeRequestLog[]>([])
const pushChartData = ref<PushLog[]>([])
const chartLoading = ref(false)

const availableAuthors = ref<string[]>([])
const availableProjects = ref<string[]>([])
const commitModalVisible = ref(false)
const selectedCommitRow = ref<PushLog | null>(null)

// 分页相关数据
const mrPagination = ref({
  currentPage: 1,
  pageSize: 10,
  total: 0
})

const pushPagination = ref({
  currentPage: 1,
  pageSize: 10,
  total: 0
})

// 环境配置
const showPushTab = ref(false)
const showSecurityWarning = ref(false)

// 筛选条件
const filters = reactive<FilterParams>({
  startDate: dayjs().subtract(7, 'day').format('YYYY-MM-DD'),
  endDate: dayjs().format('YYYY-MM-DD'),
  authors: [],
  projectNames: []
})

// 计算属性
const currentTabChartData = computed(() => {
  return activeTab.value === 'mr' ? mrChartData.value : pushChartData.value
})

// 方法
const loadMrData = async (page = 1, pageSize = 10) => {
  try {
    mrLoading.value = true
    const params = {
      ...filters,
      page,
      page_size: pageSize
    }
    const response = await reviewApi.getMergeRequestLogs(params)
    mrData.value = response.data
    mrPagination.value = {
      currentPage: response.page,
      pageSize: response.page_size,
      total: response.total
    }
  } catch (error) {
    console.error('Failed to load MR data:', error)
    ElMessage.error('加载合并请求数据失败')
  } finally {
    mrLoading.value = false
  }
}

const loadPushData = async (page = 1, pageSize = 10) => {
  try {
    pushLoading.value = true
    const params = {
      ...filters,
      page,
      page_size: pageSize
    }
    const response = await reviewApi.getPushLogs(params)
    pushData.value = response.data
    pushPagination.value = {
      currentPage: response.page,
      pageSize: response.page_size,
      total: response.total
    }
  } catch (error) {
    console.error('Failed to load Push data:', error)
    ElMessage.error('加载推送数据失败')
  } finally {
    pushLoading.value = false
  }
}

// 加载图表数据（全量数据）
const loadChartData = async () => {
  try {
    chartLoading.value = true
    const chartFilters = {
      startDate: filters.startDate,
      endDate: filters.endDate,
      authors: filters.authors,
      projectNames: filters.projectNames
    }

    const [mrChart, pushChart] = await Promise.all([
      reviewApi.getAllMergeRequestLogs(chartFilters),
      showPushTab.value ? reviewApi.getAllPushLogs(chartFilters) : Promise.resolve([])
    ])

    mrChartData.value = mrChart
    pushChartData.value = pushChart
  } catch (error) {
    console.error('Failed to load chart data:', error)
    ElMessage.error('加载图表数据失败')
  } finally {
    chartLoading.value = false
  }
}

const loadMetadata = async () => {
  try {
    const [authors, projects, config] = await Promise.all([
      reviewApi.getAuthors(),
      reviewApi.getProjects(),
      reviewApi.getConfig()
    ])
    availableAuthors.value = authors
    availableProjects.value = projects
    showPushTab.value = config.push_review_enabled
    showSecurityWarning.value = config.show_security_warning
  } catch (error) {
    console.error('Failed to load metadata:', error)
    ElMessage.error('加载元数据失败')
  }
}

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
  ElMessage.success('已退出登录')
}

const handleShowCommitDetails = (row: PushLog) => {
  selectedCommitRow.value = row
  commitModalVisible.value = true
}

// 分页处理函数
const handleMrPageChange = (page: number) => {
  loadMrData(page, mrPagination.value.pageSize)
}

const handleMrSizeChange = (size: number) => {
  loadMrData(1, size)
}

const handlePushPageChange = (page: number) => {
  loadPushData(page, pushPagination.value.pageSize)
}

const handlePushSizeChange = (size: number) => {
  loadPushData(1, size)
}

// 监听筛选条件变化
watch(filters, () => {
  // 重置分页并重新加载数据
  mrPagination.value.currentPage = 1
  pushPagination.value.currentPage = 1
  loadMrData()
  if (showPushTab.value) {
    loadPushData()
  }
  // 重新加载图表数据
  loadChartData()
}, { deep: true })

// 组件挂载
onMounted(async () => {
  await loadMetadata()
  await loadMrData()
  if (showPushTab.value) {
    await loadPushData()
  }
  // 加载图表数据
  await loadChartData()
})
</script>

<style scoped>
.dashboard-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.dashboard-header {
  background: white;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 20px;
  height: 60px !important;
  display: flex;
  align-items: center;
}

.header-content {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  margin: 0;
  color: #303133;
  font-size: 20px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.welcome-text {
  color: #606266;
  font-size: 14px;
}

.dashboard-main {
  flex: 1;
  padding: 20px;
  background-color: #f0f2f6;
  overflow-y: auto;
}

.filter-card {
  margin-bottom: 20px;
}

.data-tabs {
  background: white;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}

:deep(.el-tabs__header) {
  margin-bottom: 20px;
}

:deep(.el-tabs__item) {
  font-size: 16px;
  font-weight: 500;
}
</style>
