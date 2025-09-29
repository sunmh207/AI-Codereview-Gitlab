<template>
  <div class="dashboard-view">
    <div class="page-header">
      <h1 class="page-title">仪表盘</h1>
      <p class="page-description">代码审查系统概览</p>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-cards">
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon mr">
              <el-icon><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.totalMR }}</div>
              <div class="stat-label">合并请求</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon push">
              <el-icon><Upload /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.totalPush }}</div>
              <div class="stat-label">代码推送</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon score">
              <el-icon><TrendCharts /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.avgScore }}</div>
              <div class="stat-label">平均得分</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon projects">
              <el-icon><FolderOpened /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.totalProjects }}</div>
              <div class="stat-label">活跃项目</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <div class="charts-section">
      <!-- 趋势图 - 独占一行 -->
      <el-row :gutter="20" class="trend-row">
        <el-col :span="24">
          <el-card class="chart-card">
            <template #header>
              <div class="card-header">
                <span>最近一月审查趋势</span>
              </div>
            </template>
            <div class="chart-container large">
              <TrendChart
                :mr-data="mrDataForChart"
                :push-data="pushDataForChart"
                :loading="loading"
              />
            </div>
          </el-card>
        </el-col>
      </el-row>
      
      <!-- 项目分布图 - 独占一行 -->
      <el-row :gutter="20" class="project-row">
        <el-col :span="24">
          <el-card class="chart-card">
            <template #header>
              <div class="card-header">
                <span>项目分布统计</span>
              </div>
            </template>
            <div class="chart-container large">
              <ProjectChart
                :mr-data="mrDataForChart"
                :push-data="pushDataForChart"
                :loading="loading"
              />
            </div>
          </el-card>
        </el-col>
      </el-row>
      
      <!-- 人员排行榜和最近审查记录 - 同一行 -->
      <el-row :gutter="20" class="bottom-row">
        <el-col :xs="24" :lg="12">
          <el-card class="chart-card">
            <template #header>
              <div class="card-header">
                <span>人员排行榜</span>
                <el-tooltip content="根据推送数量(30%)、合并数量(40%)、平均得分(30%)综合计算排名" placement="top">
                  <el-icon><QuestionFilled /></el-icon>
                </el-tooltip>
              </div>
            </template>
            <div class="ranking-container">
              <RankingChart
                :mr-data="mrDataForChart"
                :push-data="pushDataForChart"
                :loading="loading"
              />
            </div>
          </el-card>
        </el-col>
        
        <el-col :xs="24" :lg="12">
          <el-card class="chart-card">
            <template #header>
              <div class="card-header">
                <span>最近审查记录</span>
                <el-button type="primary" size="small" @click="$router.push('/admin/reviews/mr')">
                  查看全部
                </el-button>
              </div>
            </template>
            
            <div class="table-container">
              <el-table :data="recentReviews" :loading="loading" stripe size="small">
                <el-table-column prop="project_name" label="项目" width="100" />
                <el-table-column prop="author" label="开发者" width="80" />
                <el-table-column prop="score" label="得分" width="70">
                  <template #default="{ row }">
                    <el-tag :type="getScoreType(row.score)" size="small">{{ row.score }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="updated_at" label="时间" width="120">
                  <template #default="{ row }">
                    <span class="time-text">{{ formatDate(row.updated_at) }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="commit_messages" label="提交信息" min-width="150" show-overflow-tooltip>
                  <template #default="{ row }">
                    <div class="commit-message" :title="row.commit_messages">
                      {{ getFirstLine(row.commit_messages) }}
                    </div>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Document, Upload, TrendCharts, FolderOpened, QuestionFilled
} from '@element-plus/icons-vue'
import { getMRReviews, getPushReviews, getMetadata, type ReviewData } from '@/api/reviews'
import StatisticsCharts from '@/components/StatisticsCharts.vue'
import TrendChart from '@/components/charts/TrendChart.vue'
import ProjectChart from '@/components/charts/ProjectChart.vue'
import RankingChart from '@/components/charts/RankingChart.vue'
import { formatDate } from '@/utils/date'

// 数据状态
const loading = ref(false)
const stats = ref({
  totalMR: 0,
  totalPush: 0,
  avgScore: 0,
  totalProjects: 0
})

const recentData = ref<ReviewData[]>([])
const projectData = ref<ReviewData[]>([])
const recentReviews = ref<ReviewData[]>([])
const mrDataForChart = ref<ReviewData[]>([])
const pushDataForChart = ref<ReviewData[]>([])

// 获取统计数据
const loadStats = async () => {
  loading.value = true
  try {
    // 先不使用时间过滤，获取所有数据
    const filters = {}

    // 并行获取数据
    const [mrResult, pushResult, metadata] = await Promise.all([
      getMRReviews(filters),
      getPushReviews(filters),
      getMetadata({ type: 'push' })
    ])

    // 使用Push数据，因为MR表为空
    const mainData = pushResult.data && pushResult.data.length > 0 ? pushResult : mrResult
    
    stats.value = {
      totalMR: mrResult.total || 0,
      totalPush: pushResult.total || 0,
      avgScore: mainData.data && mainData.data.length > 0 
        ? Math.round(mainData.data.reduce((sum, item) => sum + (item.score || 0), 0) / mainData.data.length)
        : 0,
      totalProjects: metadata.project_names ? metadata.project_names.length : 0
    }

    // 最近审查记录（取前5条）- 优先使用有数据的
    recentReviews.value = mainData.data ? mainData.data.slice(0, 5) : []
    
    // 图表数据 - 分别保存MR和Push数据
    mrDataForChart.value = mrResult.data || []
    pushDataForChart.value = pushResult.data || []
    
    // 为了兼容现有组件，recentData使用主要数据
    recentData.value = pushResult.data || [] // Push数据用于趋势图
    projectData.value = mainData.data || [] // 项目分布图使用有数据的



  } catch (error: any) {
    console.error('Dashboard load error:', error)
    ElMessage.error('获取统计数据失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

// 获取得分类型
const getScoreType = (score: number) => {
  if (score >= 80) return 'success'
  if (score >= 60) return 'warning'
  return 'danger'
}

// 获取提交信息的第一行
const getFirstLine = (message: string) => {
  if (!message) return '-'
  // 使用字符编码避免语法错误
  const CR = String.fromCharCode(13) // 

  const LF = String.fromCharCode(10) // 

  
  const crIndex = message.indexOf(CR)
  const lfIndex = message.indexOf(LF)
  
  let firstNewlineIndex = -1
  if (crIndex !== -1 && lfIndex !== -1) {
    firstNewlineIndex = Math.min(crIndex, lfIndex)
  } else if (crIndex !== -1) {
    firstNewlineIndex = crIndex
  } else if (lfIndex !== -1) {
    firstNewlineIndex = lfIndex
  }
  
  if (firstNewlineIndex === -1) {
    return message
  }
  return message.substring(0, firstNewlineIndex)
}

onMounted(() => {
  loadStats()
})
</script>

<style scoped>
.dashboard-view {
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

.stats-cards {
  margin-bottom: 24px;
}

.stat-card {
  margin-bottom: 16px;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: white;
}

.stat-icon.mr {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.stat-icon.push {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.stat-icon.score {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.stat-icon.projects {
  background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #1f2937;
  line-height: 1;
}

.stat-label {
  font-size: 14px;
  color: #6b7280;
  margin-top: 4px;
}

.charts-section {
  margin-bottom: 24px;
}

.chart-card,
.recent-reviews {
  margin-bottom: 16px;
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

.chart-container.large {
  height: 400px;
}

.trend-row,
.project-row,
.bottom-row {
  margin-bottom: 20px;
}

.ranking-container {
  height: 400px;
  overflow-y: auto;
}

.table-container {
  height: 400px;
  overflow-y: auto;
}

.time-text {
  font-size: 12px;
  color: #606266;
}

.commit-message {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.4;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .stats-cards .el-col {
    margin-bottom: 16px;
  }
  
  .charts-section .el-col {
    margin-bottom: 16px;
  }
  
  .chart-container {
    height: 250px;
  }
}
</style>