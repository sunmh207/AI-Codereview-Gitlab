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
      <!-- 项目数量统计 -->
      <el-col :xs="24" :lg="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>项目审查数量</span>
            </div>
          </template>
          <div class="chart-container">
            <SimpleChart
              :data="projectCounts"
              :loading="loading"
              chart-type="project-counts"
            />
          </div>
        </el-card>
      </el-col>
      
      <!-- 项目得分统计 -->
      <el-col :xs="24" :lg="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>项目平均得分</span>
            </div>
          </template>
          <div class="chart-container">
            <SimpleChart
              :data="projectScores"
              :loading="loading"
              chart-type="project-scores"
            />
          </div>
        </el-card>
      </el-col>
      
      <!-- 开发者审查数量 -->
      <el-col :xs="24" :lg="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>开发者审查数量</span>
            </div>
          </template>
          <div class="chart-container">
            <SimpleChart
              :data="authorCounts"
              :loading="loading"
              chart-type="author-counts"
            />
          </div>
        </el-card>
      </el-col>
      
      <!-- 开发者平均得分 -->
      <el-col :xs="24" :lg="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>开发者平均得分</span>
            </div>
          </template>
          <div class="chart-container">
            <SimpleChart
              :data="authorScores"
              :loading="loading"
              chart-type="author-scores"
            />
          </div>
        </el-card>
      </el-col>

      <!-- 开发者代码行数 -->
      <el-col :xs="24" :lg="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>开发者代码行数</span>
            </div>
          </template>
          <div class="chart-container">
            <SimpleChart
              :data="authorCodeLines"
              :loading="loading"
              chart-type="author-code-lines"
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
        <el-table-column prop="count" label="审查数量" width="100" />
        <el-table-column prop="average_score" label="平均得分" width="100">
          <template #default="{ row }">
            <el-tag :type="getScoreType(row.average_score)">{{ row.average_score?.toFixed(1) || 'N/A' }}</el-tag>
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
import { ref, reactive, onMounted, toRaw } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh, Download } from '@element-plus/icons-vue'
import { getStatistics, getMetadata, type ReviewFilters } from '@/api/reviews'
import SimpleChart from '@/components/charts/SimpleChart.vue'
import { formatDate, getDefaultDateRange } from '@/utils/date'

// 定义数据接口
interface ProjectStatistics {
  project_name: string
  count?: number
  average_score?: number
  total_additions?: number
  total_deletions?: number
  active_authors?: number
  last_activity?: string
}

interface AuthorStatistics {
  author: string
  count?: number
  average_score?: number
  additions?: number
  deletions?: number
}

interface MetadataType {
  authors: string[]
  project_names: string[]
}

// 数据状态
const loading = ref(false)
const projectCounts = ref<ProjectStatistics[]>([])
const projectScores = ref<ProjectStatistics[]>([])
const authorCounts = ref<AuthorStatistics[]>([])
const authorScores = ref<AuthorStatistics[]>([])
const authorCodeLines = ref<AuthorStatistics[]>([])
const projectStats = ref<ProjectStatistics[]>([])
const metadata = ref<MetadataType>({ authors: [], project_names: [] })

// 筛选条件
const dateRange = ref<[string, string]>(['', ''])
const filters = reactive<ReviewFilters & { type: 'mr' | 'push' }>({
  type: 'push',
  project_names: []
})

// 加载统计数据
const loadStatisticsData = async () => {
  try {
    loading.value = true
    
    // 并行获取所有统计数据，传递当前的筛选条件
    const [
      projectCountsRes,
      projectScoresRes,
      authorCountsRes,
      authorScoresRes,
      authorCodeLinesRes
    ] = await Promise.all([
      getStatistics('project_counts', { 
        type: filters.type,
        start_date: dateRange.value[0],
        end_date: dateRange.value[1],
        project_names: filters.project_names
      }),
      getStatistics('project_scores', { 
        type: filters.type,
        start_date: dateRange.value[0],
        end_date: dateRange.value[1],
        project_names: filters.project_names
      }),
      getStatistics('author_counts', { 
        type: filters.type,
        start_date: dateRange.value[0],
        end_date: dateRange.value[1],
        project_names: filters.project_names
      }),
      getStatistics('author_scores', { 
        type: filters.type,
        start_date: dateRange.value[0],
        end_date: dateRange.value[1],
        project_names: filters.project_names
      }),
      getStatistics('author_code_lines', { 
        type: filters.type,
        start_date: dateRange.value[0],
        end_date: dateRange.value[1],
        project_names: filters.project_names
      })
    ])
    
    // API返回的是 {data: [...]} 格式，直接取 .data
    const rawProjectCounts = projectCountsRes.data || []
    const rawProjectScores = projectScoresRes.data || []
    const rawAuthorCounts = authorCountsRes.data || []
    const rawAuthorScores = authorScoresRes.data || []
    const rawAuthorCodeLines = authorCodeLinesRes.data || []
    
    // 使用展开语法确保数据是原始数组
    projectCounts.value = [...rawProjectCounts]
    projectScores.value = [...rawProjectScores]
    authorCounts.value = [...rawAuthorCounts]
    authorScores.value = [...rawAuthorScores]
    authorCodeLines.value = [...rawAuthorCodeLines]
    
    // 合并项目统计数据用于表格显示
    const projectMap = new Map<string, ProjectStatistics>()
    
    projectCounts.value.forEach(item => {
      if (!projectMap.has(item.project_name)) {
        projectMap.set(item.project_name, { project_name: item.project_name })
      }
      const project = projectMap.get(item.project_name)!
      project.count = item.count
    })
    
    projectScores.value.forEach(item => {
      if (!projectMap.has(item.project_name)) {
        projectMap.set(item.project_name, { project_name: item.project_name })
      }
      const project = projectMap.get(item.project_name)!
      project.average_score = item.average_score
    })
    
    projectStats.value = Array.from(projectMap.values())
    
    ElMessage.success('统计数据加载成功')
  } catch (error) {
    console.error('获取统计数据失败:', error)
    ElMessage.error('获取统计数据失败')
  } finally {
    loading.value = false
  }
}

// 加载数据（保持兼容性）
const loadData = () => {
  loadStatisticsData()
}

// 加载元数据
const loadMetadata = async () => {
  try {
    const result = await getMetadata({ type: filters.type })
    metadata.value = {
      authors: result.authors || [],
      project_names: result.project_names || []
    }
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
  filters.type = 'push'
  filters.project_names = []
  loadMetadata()
  loadData()
}

const exportData = () => {
  ElMessage.info('导出功能开发中...')
}

const getScoreType = (score: number | undefined) => {
  if (!score) return 'info'
  if (score >= 80) return 'success'
  if (score >= 60) return 'warning'
  return 'danger'
}

// 初始化
onMounted(async () => {
  const [startDate, endDate] = getDefaultDateRange()
  dateRange.value = [startDate, endDate]
  
  await loadMetadata()
  await loadStatisticsData()
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