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
    <el-row :gutter="20" class="charts-section">
      <el-col :xs="24" :lg="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>最近7天审查趋势</span>
            </div>
          </template>
          <div class="chart-container">
            <StatisticsCharts
              :data="recentData"
              :loading="loading"
              type="mr"
              chart-type="trend"
            />
          </div>
        </el-card>
      </el-col>
      
      <el-col :xs="24" :lg="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>项目分布</span>
            </div>
          </template>
          <div class="chart-container">
            <StatisticsCharts
              :data="projectData"
              :loading="loading"
              type="mr"
              chart-type="project"
            />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近审查记录 -->
    <el-card class="recent-reviews">
      <template #header>
        <div class="card-header">
          <span>最近审查记录</span>
          <el-button type="primary" size="small" @click="$router.push('/admin/reviews/mr')">
            查看全部
          </el-button>
        </div>
      </template>
      
      <el-table :data="recentReviews" :loading="loading" stripe>
        <el-table-column prop="project_name" label="项目" width="150" />
        <el-table-column prop="author" label="开发者" width="120" />
        <el-table-column prop="title" label="标题" show-overflow-tooltip />
        <el-table-column prop="score" label="得分" width="80">
          <template #default="{ row }">
            <el-tag :type="getScoreType(row.score)">{{ row.score }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.updated_at) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Document, Upload, TrendCharts, FolderOpened
} from '@element-plus/icons-vue'
import { getMRReviews, getPushReviews, getMetadata } from '@/api/reviews'
import StatisticsCharts from '@/components/StatisticsCharts.vue'
import { formatDate } from '@/utils/date'

// 数据状态
const loading = ref(false)
const stats = ref({
  totalMR: 0,
  totalPush: 0,
  avgScore: 0,
  totalProjects: 0
})

const recentData = ref([])
const projectData = ref([])
const recentReviews = ref([])

// 获取统计数据
const loadStats = async () => {
  loading.value = true
  try {
    // 获取最近7天的数据
    const endDate = new Date()
    const startDate = new Date()
    startDate.setDate(startDate.getDate() - 7)
    
    const filters = {
      start_date: startDate.toISOString(),
      end_date: endDate.toISOString()
    }

    // 并行获取数据
    const [mrResult, pushResult, metadata] = await Promise.all([
      getMRReviews(filters),
      getPushReviews(filters),
      getMetadata({ type: 'mr' })
    ])

    stats.value = {
      totalMR: mrResult.total,
      totalPush: pushResult.total,
      avgScore: mrResult.data.length > 0 
        ? Math.round(mrResult.data.reduce((sum, item) => sum + item.score, 0) / mrResult.data.length)
        : 0,
      totalProjects: metadata.project_names.length
    }

    // 最近审查记录（取前5条）
    recentReviews.value = mrResult.data.slice(0, 5)
    
    // 图表数据
    recentData.value = mrResult.data
    projectData.value = mrResult.data

  } catch (error: any) {
    ElMessage.error('获取统计数据失败')
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