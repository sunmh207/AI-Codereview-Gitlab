<template>
  <div class="charts-container" v-loading="loading">
    <!-- 第一行：项目相关图表 -->
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <div class="chart-title">项目提交统计</div>
          </template>
          <v-chart
            class="chart"
            :option="projectCountOption"
            autoresize
          />
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <div class="chart-title">项目平均得分</div>
          </template>
          <v-chart
            class="chart"
            :option="projectScoreOption"
            autoresize
          />
        </el-card>
      </el-col>
    </el-row>

    <!-- 第二行：开发者相关图表 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <div class="chart-title">开发者提交统计</div>
          </template>
          <v-chart
            class="chart"
            :option="authorCountOption"
            autoresize
          />
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <div class="chart-title">开发者平均得分</div>
          </template>
          <v-chart
            class="chart"
            :option="authorScoreOption"
            autoresize
          />
        </el-card>
      </el-col>
    </el-row>

    <!-- 第三行：代码变更行数图表 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <div class="chart-title">人员代码变更行数</div>
          </template>
          <v-chart
            class="chart"
            :option="codeLineOption"
            autoresize
          />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
} from 'echarts/components'
import VChart from 'vue-echarts'
import type { MergeRequestLog, PushLog } from '@/types'

use([
  CanvasRenderer,
  BarChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
])

interface Props {
  data: (MergeRequestLog | PushLog)[]
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
})

// 计算项目提交统计
const projectCountData = computed(() => {
  const counts = new Map<string, number>()
  props.data.forEach(item => {
    const count = counts.get(item.project_name) || 0
    counts.set(item.project_name, count + 1)
  })
  return Array.from(counts.entries()).map(([name, value]) => ({ name, value }))
})

// 计算项目平均得分
const projectScoreData = computed(() => {
  const scores = new Map<string, number[]>()
  props.data.forEach(item => {
    const projectScores = scores.get(item.project_name) || []
    projectScores.push(item.score)
    scores.set(item.project_name, projectScores)
  })
  
  return Array.from(scores.entries()).map(([name, scoreList]) => ({
    name,
    value: Math.round(scoreList.reduce((sum, score) => sum + score, 0) / scoreList.length)
  }))
})

// 计算开发者提交统计
const authorCountData = computed(() => {
  const counts = new Map<string, number>()
  props.data.forEach(item => {
    const count = counts.get(item.author) || 0
    counts.set(item.author, count + 1)
  })
  return Array.from(counts.entries()).map(([name, value]) => ({ name, value }))
})

// 计算开发者平均得分
const authorScoreData = computed(() => {
  const scores = new Map<string, number[]>()
  props.data.forEach(item => {
    const authorScores = scores.get(item.author) || []
    authorScores.push(item.score)
    scores.set(item.author, authorScores)
  })
  
  return Array.from(scores.entries()).map(([name, scoreList]) => ({
    name,
    value: Math.round(scoreList.reduce((sum, score) => sum + score, 0) / scoreList.length)
  }))
})

// 计算代码变更行数
const codeLineData = computed(() => {
  const additions = new Map<string, number>()
  const deletions = new Map<string, number>()
  
  props.data.forEach(item => {
    const addCount = additions.get(item.author) || 0
    const delCount = deletions.get(item.author) || 0
    additions.set(item.author, addCount + (item.additions || 0))
    deletions.set(item.author, delCount + (item.deletions || 0))
  })
  
  return {
    authors: Array.from(additions.keys()),
    additions: Array.from(additions.values()),
    deletions: Array.from(deletions.values())
  }
})

// 图表配置
const createBarOption = (data: { name: string; value: number }[], colors: string[]) => ({
  tooltip: {
    trigger: 'axis',
    axisPointer: {
      type: 'shadow'
    }
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    containLabel: true
  },
  xAxis: {
    type: 'category',
    data: data.map(item => item.name),
    axisLabel: {
      rotate: 45,
      fontSize: 12
    }
  },
  yAxis: {
    type: 'value',
    minInterval: 1
  },
  series: [{
    type: 'bar',
    data: data.map((item, index) => ({
      value: item.value,
      itemStyle: {
        color: colors[index % colors.length]
      }
    }))
  }]
})

const projectCountOption = computed(() => 
  createBarOption(projectCountData.value, ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de'])
)

const projectScoreOption = computed(() => 
  createBarOption(projectScoreData.value, ['#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#5470c6'])
)

const authorCountOption = computed(() => 
  createBarOption(authorCountData.value, ['#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272'])
)

const authorScoreOption = computed(() => 
  createBarOption(authorScoreData.value, ['#fc8452', '#9a60b4', '#ea7ccc', '#5470c6', '#91cc75'])
)

const codeLineOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    axisPointer: {
      type: 'shadow'
    }
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    containLabel: true
  },
  xAxis: {
    type: 'category',
    data: codeLineData.value.authors,
    axisLabel: {
      rotate: 45,
      fontSize: 12
    }
  },
  yAxis: {
    type: 'value'
  },
  series: [
    {
      name: '新增',
      type: 'bar',
      data: codeLineData.value.additions,
      itemStyle: {
        color: 'rgba(114, 204, 114, 0.8)'
      }
    },
    {
      name: '删除',
      type: 'bar',
      data: codeLineData.value.deletions.map(val => -val),
      itemStyle: {
        color: 'rgba(255, 114, 114, 0.8)'
      }
    }
  ]
}))
</script>

<style scoped>
.charts-container {
  padding: 20px;
}

.chart-card {
  height: 400px;
}

.chart-title {
  text-align: center;
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}

.chart {
  height: 320px;
  width: 100%;
}
</style>
