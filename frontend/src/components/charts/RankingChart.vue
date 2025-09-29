<template>
  <div class="ranking-chart">
    <!-- 时间筛选器 -->
    <div class="filter-bar">
      <el-radio-group v-model="timeFilter" size="small" @change="handleTimeFilterChange">
        <el-radio-button label="all">全部</el-radio-button>
        <el-radio-button label="today">今天</el-radio-button>
        <el-radio-button label="week">近一周</el-radio-button>
        <el-radio-button label="month">近一月</el-radio-button>
      </el-radio-group>
    </div>
    
    <div v-if="loading" class="loading-container">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载中...</span>
    </div>
    <div v-else-if="!hasData" class="empty-container">
      <el-empty description="暂无数据" />
    </div>
    <div v-else class="ranking-content">
      <!-- 排行榜表格 -->
      <el-table :data="rankingData" stripe class="ranking-table">
        <el-table-column type="index" label="排名" width="80" align="center">
          <template #default="{ $index }">
            <div class="rank-cell">
              <el-icon v-if="$index === 0" class="rank-icon gold"><Trophy /></el-icon>
              <el-icon v-else-if="$index === 1" class="rank-icon silver"><Medal /></el-icon>
              <el-icon v-else-if="$index === 2" class="rank-icon bronze"><Medal /></el-icon>
              <span v-else class="rank-number">{{ $index + 1 }}</span>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="author" label="开发者" width="120" />
        
        <el-table-column prop="pushCount" label="推送数" width="100" align="center">
          <template #default="{ row }">
            <div class="count-cell">
              <span>{{ row.pushCount }}</span>
              <el-icon v-if="row.isMaxPush" class="achievement-icon max"><Star /></el-icon>
              <el-icon v-if="row.isMinPush" class="achievement-icon min"><Warning /></el-icon>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="mrCount" label="合并数" width="100" align="center">
          <template #default="{ row }">
            <div class="count-cell">
              <span>{{ row.mrCount }}</span>
              <el-icon v-if="row.isMaxMR" class="achievement-icon max"><Star /></el-icon>
              <el-icon v-if="row.isMinMR" class="achievement-icon min"><Warning /></el-icon>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="avgScore" label="平均分" width="100" align="center">
          <template #default="{ row }">
            <div class="score-cell">
              <el-tag :type="getScoreType(row.avgScore)">{{ row.avgScore }}</el-tag>
              <el-icon v-if="row.isMaxScore" class="achievement-icon max"><Star /></el-icon>
              <el-icon v-if="row.isMinScore" class="achievement-icon min"><Warning /></el-icon>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="totalScore" label="综合得分" width="120" align="center">
          <template #default="{ row }">
            <div class="total-score">
              <strong>{{ row.totalScore }}</strong>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column label="成就" min-width="150">
          <template #default="{ row }">
            <div class="achievements">
              <el-tag v-for="achievement in row.achievements" :key="achievement.type" 
                      :type="achievement.color" size="small" class="achievement-tag">
                {{ achievement.text }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { Loading, Trophy, Medal, Star, Warning } from '@element-plus/icons-vue'

interface Props {
  mrData: any[]
  pushData: any[]
  loading: boolean
}

const props = withDefaults(defineProps<Props>(), {
  mrData: () => [],
  pushData: () => [],
  loading: false
})

// 时间筛选
const timeFilter = ref('all')

// 处理时间筛选变化
const handleTimeFilterChange = () => {
  // 触发重新计算
}

// 根据时间筛选过滤数据
const getFilteredData = (data: any[]) => {
  if (!data || data.length === 0) return []
  
  const now = new Date()
  let startDate: Date
  
  switch (timeFilter.value) {
    case 'today':
      startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate())
      break
    case 'week':
      startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
      break
    case 'month':
      startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)
      break
    default:
      return data // 全部数据
  }
  
  return data.filter(item => {
    const itemDate = new Date(item.updated_at || item.created_at)
    return itemDate >= startDate
  })
}

const hasData = computed(() => {
  const filteredMR = getFilteredData(props.mrData)
  const filteredPush = getFilteredData(props.pushData)
  return (filteredMR && filteredMR.length > 0) || (filteredPush && filteredPush.length > 0)
})

// 计算排行榜数据
const rankingData = computed(() => {
  if (!hasData.value) return []
  
  // 获取筛选后的数据
  const filteredPushData = getFilteredData(props.pushData)
  const filteredMRData = getFilteredData(props.mrData)
  
  const authorStats = new Map()
  
  // 处理Push数据
  if (filteredPushData && filteredPushData.length > 0) {
    filteredPushData.forEach(item => {
      const author = item.author || '未知用户'
      const stats = authorStats.get(author) || {
        author,
        pushCount: 0,
        mrCount: 0,
        totalScore: 0,
        scoreCount: 0,
        avgScore: 0
      }
      
      stats.pushCount += 1
      if (item.score) {
        stats.totalScore += item.score
        stats.scoreCount += 1
      }
      
      authorStats.set(author, stats)
    })
  }
  
  // 处理MR数据
  if (filteredMRData && filteredMRData.length > 0) {
    filteredMRData.forEach(item => {
      const author = item.author || '未知用户'
      const stats = authorStats.get(author) || {
        author,
        pushCount: 0,
        mrCount: 0,
        totalScore: 0,
        scoreCount: 0,
        avgScore: 0
      }
      
      stats.mrCount += 1
      if (item.score) {
        stats.totalScore += item.score
        stats.scoreCount += 1
      }
      
      authorStats.set(author, stats)
    })
  }
  
  // 计算平均分和综合得分
  const authors = Array.from(authorStats.values()).map(stats => {
    stats.avgScore = stats.scoreCount > 0 ? Math.round(stats.totalScore / stats.scoreCount) : 0
    
    // 综合得分计算：推送数 * 0.3 + 合并数 * 0.2 + 平均分 * 0.5
    const normalizedPush = stats.pushCount * 0.3
    const normalizedMR = stats.mrCount * 0.2
    const normalizedScore = stats.avgScore * 0.5
    stats.totalScore = Math.round(normalizedPush + normalizedMR + normalizedScore)
    
    return stats
  })
  
  // 找出最值
  const pushCounts = authors.map(a => a.pushCount).filter(c => c > 0)
  const mrCounts = authors.map(a => a.mrCount).filter(c => c > 0)
  const avgScores = authors.map(a => a.avgScore).filter(s => s > 0)
  
  const maxPush = Math.max(...pushCounts, 0)
  const minPush = Math.min(...pushCounts, Infinity)
  const maxMR = Math.max(...mrCounts, 0)
  const minMR = Math.min(...mrCounts, Infinity)
  const maxScore = Math.max(...avgScores, 0)
  const minScore = Math.min(...avgScores, Infinity)
  
  // 标记最值和成就
  authors.forEach(author => {
    author.isMaxPush = author.pushCount === maxPush && maxPush > 0
    author.isMinPush = author.pushCount === minPush && minPush < Infinity && pushCounts.length > 1
    author.isMaxMR = author.mrCount === maxMR && maxMR > 0
    author.isMinMR = author.mrCount === minMR && minMR < Infinity && mrCounts.length > 1
    author.isMaxScore = author.avgScore === maxScore && maxScore > 0
    author.isMinScore = author.avgScore === minScore && minScore < Infinity && avgScores.length > 1
    
    // 生成成就标签
    author.achievements = []
    if (author.isMaxPush) {
      author.achievements.push({ type: 'maxPush', text: '推送王', color: 'success' })
    }
    if (author.isMinPush) {
      author.achievements.push({ type: 'minPush', text: '需努力', color: 'warning' })
    }
    if (author.isMaxMR) {
      author.achievements.push({ type: 'maxMR', text: '合并王', color: 'success' })
    }
    if (author.isMinMR) {
      author.achievements.push({ type: 'minMR', text: '需努力', color: 'warning' })
    }
    if (author.isMaxScore) {
      author.achievements.push({ type: 'maxScore', text: '质量王', color: 'success' })
    }
    if (author.isMinScore) {
      author.achievements.push({ type: 'minScore', text: '需改进', color: 'danger' })
    }
  })
  
  // 按综合得分排序
  return authors.sort((a, b) => b.totalScore - a.totalScore)
})

// 获取得分类型
const getScoreType = (score: number) => {
  if (score >= 80) return 'success'
  if (score >= 60) return 'warning'
  return 'danger'
}
</script>

<style scoped>
.ranking-chart {
  width: 100%;
  height: 100%;
  position: relative;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #909399;
}

.loading-container .el-icon {
  font-size: 24px;
  margin-bottom: 8px;
}

.empty-container {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
}

.ranking-content {
  width: 100%;
}

.ranking-table {
  width: 100%;
}

.rank-cell {
  display: flex;
  align-items: center;
  justify-content: center;
}

.rank-icon {
  font-size: 20px;
}

.rank-icon.gold {
  color: #FFD700;
}

.rank-icon.silver {
  color: #C0C0C0;
}

.rank-icon.bronze {
  color: #CD7F32;
}

.rank-number {
  font-weight: 600;
  color: #606266;
}

.count-cell,
.score-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.achievement-icon {
  font-size: 14px;
}

.achievement-icon.max {
  color: #F56C6C;
}

.achievement-icon.min {
  color: #E6A23C;
}

.total-score {
  font-size: 16px;
  color: #409EFF;
}

.achievements {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.achievement-tag {
  font-size: 12px;
}
</style>