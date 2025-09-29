<template>
  <div class="statistics-view">
    <div class="page-header">
      <h1 class="page-title">统计分析</h1>
      <p class="page-description">代码审查数据统计和趋势分析</p>
    </div>

    <!-- 筛选条件 -->
    <el-card class="filter-card">
      <el-form :model="filters" :inline="true" class="filter-form">
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            @change="onDateRangeChange"
          />
        </el-form-item>
        
        <el-form-item label="审查类型">
          <el-select
            v-model="filters.type"
            placeholder="选择类型"
            style="width: 150px"
            @change="onFiltersChange"
          >
            <el-option label="合并请求" value="mr" />
            <el-option label="代码推送" value="push" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="项目">
          <el-select
            v-model="filters.project_names"
            multiple
            placeholder="选择项目"
            style="width: 200px"
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
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="loadData">
            <el-icon><Search /></el-icon>
            刷新
          </el-button>
          <el-button @click="resetFilters">
            <el-icon><Refresh /></el-icon>
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 统计图表 -->
    <el-row :gutter="20">
      <!-- 趋势图 -->
      <el-col :xs="24" :lg="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>{{ filters.type === 'mr' ? '合并请求' : '代码推送' }}趋势</span>
            </div>
          </template>
          <div class="chart-container">
            <StatisticsCharts
              :data="chartData"
              :loading="loading"
              :type="filters.type"
              chart-type="trend"
            />
          </div>
        </el-card>
      </el-col>
      
      <!-- 项目分布 -->
      <el-col :xs="24" :lg="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>项目分布</span>
            </div>
          </template>
          <div class="chart-container">
            <StatisticsCharts
              :data="chartData"
              :loading="loading"
              :type="filters.type"
              chart-type="project"
            />
          </div>
        </el-card>
      </el-col>
      
      <!-- 开发者排行 -->
      <el-col :xs="24" :lg="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>开发者排行</span>
            </div>
          </template>
          <div class="chart-container">
            <StatisticsCharts
              :data="chartData"
              :loading="loading"
              :type="filters.type"
              chart-type="author"
            />
          </div>
        </el-card>
      </el-col>
      
      <!-- 得分分布 -->
      <el-col :xs="24" :lg="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>得分分布</span>
            </div>
          </template>
          <div class="chart-container">
            <StatisticsCharts
              :data="chartData"
              :loading="loading"
              :type="filters.type"
              chart-type="score"
            />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 统计表格 -->
    <el-card class="table-card">
      <template #header>
        <div class="card-header">
          <span>项目统计详情</span>
          <el-button size="small" @click="exportData">
            <el-icon><Download /></el-icon>
            导出
          </el-button>
        </div>
      </template>
      
      <el-table :data="projectStats" :loading="loading" stripe>
        <el-table-column prop="project_name" label="项目名称" />
        <el-table-column prop="total_count" label="总数量" width="100" />
        <el-table-column prop="avg_score" label="平均得分" width="100">
          <template #default="{ row }">
            <el-tag :type="getScoreType(row.avg_score)">{{ row.avg_score }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total_additions" label="总新增行数" width="120" />
        <el-table-column prop="total_deletions" label="总删除行数" width="120" />
        <el-table-column prop="active_authors" label="活跃开发者" width="120" />
        <el-table-column prop="last_activity" label="最后活动" width="160">
          <template #default="{ row }">
            {{ formatDate(row.last_activity) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh, Download } from '@element-plus/icons-vue'
import { getProjectStatistics, getMetadata, type ReviewFilters } from '@/api/reviews'
import StatisticsCharts from '@/components/StatisticsCharts.vue'
import { formatDate, getDefaultDateRange } from '@/utils/date'

// 数据状态
const loading = ref(false)
const chartData = ref([])
const projectStats = ref([])
const metadata = ref({ authors: [], project_names: [] })

// 筛选条件
const dateRange = ref<[string, string]>(['', ''])
const filters = reactive<ReviewFilters & { type: string }>({
  type: 'mr',
  project_names: []
})

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    const params: any = {
      type: filters.type
    }

    // 添加筛选条件
    if (dateRange.value[0]) params.start_date = dateRange.value[0]
    if (dateRange.value[1]) params.end_date = dateRange.value[1]
    if (filters.project_names?.length) params.project_names = filters.project_names

    const result = await getProjectStatistics(params)
    chartData.value = result.chart_data || []
    projectStats.value = result.project_stats || []
  } catch (error: any) {
    ElMessage.error('获取统计数据失败')
  } finally {
    loading.value = false
  }
}

// 加载元数据
const loadMetadata = async () => {
  try {
    const result = await getMetadata({ type: filters.type })
    metadata.value = result
  } catch (error: any) {
    ElMessage.error('获取元数据失败')
  }
}

// 事件处理
const onDateRangeChange = () => {
  loadData()
}

const onFiltersChange = () => {
  loadMetadata()
  loadData()
}

const resetFilters = () => {
  const [startDate, endDate] = getDefaultDateRange()
  dateRange.value = [startDate, endDate]
  filters.type = 'mr'
  filters.project_names = []
  loadMetadata()
  loadData()
}

const exportData = () => {
  ElMessage.info('导出功能开发中...')
}

const getScoreType = (score: number) => {
  if (score >= 80) return 'success'
  if (score >= 60) return 'warning'
  return 'danger'
}

// 初始化
onMounted(async () => {
  const [startDate, endDate] = getDefaultDateRange()
  dateRange.value = [startDate, endDate]
  
  await loadMetadata()
  await loadData()
})
</script>

<style scoped>
.statistics-view {
  padding: 0;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 8px 0;
}

.page-description {
  color: #6b7280;
  margin: 0;
}

.filter-card {
  margin-bottom: 20px;
}

.filter-form {
  margin: 0;
}

.chart-card,
.table-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}

.chart-container {
  height: 300px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .filter-form {
    display: block;
  }
  
  .filter-form .el-form-item {
    display: block;
    margin-bottom: 16px;
  }
  
  .chart-container {
    height: 250px;
  }
}
</style>