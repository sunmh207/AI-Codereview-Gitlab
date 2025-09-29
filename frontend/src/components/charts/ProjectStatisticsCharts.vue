<template>
  <div class="project-statistics-charts">
    <!-- 项目提交统计 -->
    <el-row :gutter="20">
      <el-col :xs="24" :lg="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>项目提交统计</span>
            </div>
          </template>
          <div ref="projectCountChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      
      <!-- 项目平均得分 -->
      <el-col :xs="24" :lg="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>项目平均得分</span>
            </div>
          </template>
          <div ref="projectScoreChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 开发者统计 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :xs="24" :lg="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>开发者提交统计</span>
            </div>
          </template>
          <div ref="authorCountChartRef" class="chart-container"></div>
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
          <div ref="authorScoreChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 代码变更行数 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :xs="24" :lg="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>人员代码变更行数</span>
            </div>
          </template>
          <div ref="codeLineChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'

interface ProjectStatistics {
  project_name: string
  count?: number
  average_score?: number
}

interface AuthorStatistics {
  author: string
  count?: number
  average_score?: number
  additions?: number
  deletions?: number
}

interface Props {
  projectCounts: ProjectStatistics[]
  projectScores: ProjectStatistics[]
  authorCounts: AuthorStatistics[]
  authorScores: AuthorStatistics[]
  authorCodeLines: AuthorStatistics[]
  loading: boolean
}

const props = withDefaults(defineProps<Props>(), {
  projectCounts: () => [],
  projectScores: () => [],
  authorCounts: () => [],
  authorScores: () => [],
  authorCodeLines: () => [],
  loading: false
})

// Chart refs
const projectCountChartRef = ref<HTMLElement>()
const projectScoreChartRef = ref<HTMLElement>()
const authorCountChartRef = ref<HTMLElement>()
const authorScoreChartRef = ref<HTMLElement>()
const codeLineChartRef = ref<HTMLElement>()

// Chart instances
let projectCountChart: echarts.ECharts | null = null
let projectScoreChart: echarts.ECharts | null = null
let authorCountChart: echarts.ECharts | null = null
let authorScoreChart: echarts.ECharts | null = null
let codeLineChart: echarts.ECharts | null = null

// 生成颜色
const generateColors = (count: number, colorMap: string) => {
  const colors = echarts.color.getColors(colorMap, count)
  return colors
}

// 项目提交数量图表
const initProjectCountChart = () => {
  if (!projectCountChartRef.value || props.projectCounts.length === 0) return
  
  projectCountChart = echarts.init(projectCountChartRef.value)
  
  const data = props.projectCounts.slice(0, 10) // 取前10个
  const colors = generateColors(data.length, 'tab20')
  
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    xAxis: {
      type: 'category',
      data: data.map(item => item.project_name),
      axisLabel: {
        rotate: 45,
        fontSize: 12
      }
    },
    yAxis: {
      type: 'value',
      name: '提交数量'
    },
    series: [{
      data: data.map((item, index) => ({
        value: item.count,
        itemStyle: { color: colors[index] }
      })),
      type: 'bar'
    }]
  }
  
  projectCountChart.setOption(option)
}

// 项目平均分数图表
const initProjectScoreChart = () => {
  if (!projectScoreChartRef.value || props.projectScores.length === 0) return
  
  projectScoreChart = echarts.init(projectScoreChartRef.value)
  
  const data = props.projectScores.slice(0, 10)
  const colors = generateColors(data.length, 'Accent')
  
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    xAxis: {
      type: 'category',
      data: data.map(item => item.project_name),
      axisLabel: {
        rotate: 45,
        fontSize: 12
      }
    },
    yAxis: {
      type: 'value',
      name: '平均得分',
      min: 0,
      max: 100
    },
    series: [{
      data: data.map((item, index) => ({
        value: item.average_score?.toFixed(1),
        itemStyle: { color: colors[index] }
      })),
      type: 'bar'
    }]
  }
  
  projectScoreChart.setOption(option)
}

// 开发者提交数量图表
const initAuthorCountChart = () => {
  if (!authorCountChartRef.value || props.authorCounts.length === 0) return
  
  authorCountChart = echarts.init(authorCountChartRef.value)
  
  const data = props.authorCounts.slice(0, 10)
  const colors = generateColors(data.length, 'Paired')
  
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    xAxis: {
      type: 'category',
      data: data.map(item => item.author),
      axisLabel: {
        rotate: 45,
        fontSize: 12
      }
    },
    yAxis: {
      type: 'value',
      name: '提交数量'
    },
    series: [{
      data: data.map((item, index) => ({
        value: item.count,
        itemStyle: { color: colors[index] }
      })),
      type: 'bar'
    }]
  }
  
  authorCountChart.setOption(option)
}

// 开发者平均分数图表
const initAuthorScoreChart = () => {
  if (!authorScoreChartRef.value || props.authorScores.length === 0) return
  
  authorScoreChart = echarts.init(authorScoreChartRef.value)
  
  const data = props.authorScores.slice(0, 10)
  const colors = generateColors(data.length, 'Pastel1')
  
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    xAxis: {
      type: 'category',
      data: data.map(item => item.author),
      axisLabel: {
        rotate: 45,
        fontSize: 12
      }
    },
    yAxis: {
      type: 'value',
      name: '平均得分',
      min: 0,
      max: 100
    },
    series: [{
      data: data.map((item, index) => ({
        value: item.average_score?.toFixed(1),
        itemStyle: { color: colors[index] }
      })),
      type: 'bar'
    }]
  }
  
  authorScoreChart.setOption(option)
}

// 代码变更行数图表
const initCodeLineChart = () => {
  if (!codeLineChartRef.value || props.authorCodeLines.length === 0) return
  
  codeLineChart = echarts.init(codeLineChartRef.value)
  
  const data = props.authorCodeLines.slice(0, 10)
  
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: (params: any) => {
        let result = params[0].name + '<br/>'
        params.forEach((param: any) => {
          const value = Math.abs(param.value)
          const type = param.value >= 0 ? '新增' : '删除'
          result += `${param.marker} ${type}: ${value} 行<br/>`
        })
        return result
      }
    },
    legend: {
      data: ['新增行数', '删除行数']
    },
    xAxis: {
      type: 'category',
      data: data.map(item => item.author),
      axisLabel: {
        rotate: 45,
        fontSize: 12
      }
    },
    yAxis: {
      type: 'value',
      name: '代码行数'
    },
    series: [
      {
        name: '新增行数',
        type: 'bar',
        data: data.map(item => item.additions || 0),
        itemStyle: {
          color: 'rgba(114, 204, 114, 0.8)'
        }
      },
      {
        name: '删除行数',
        type: 'bar',
        data: data.map(item => -(item.deletions || 0)),
        itemStyle: {
          color: 'rgba(255, 114, 114, 0.8)'
        }
      }
    ]
  }
  
  codeLineChart.setOption(option)
}

// 初始化所有图表
const initAllCharts = () => {
  nextTick(() => {
    initProjectCountChart()
    initProjectScoreChart()
    initAuthorCountChart()
    initAuthorScoreChart()
    initCodeLineChart()
  })
}

// 窗口大小变化处理
const handleResize = () => {
  projectCountChart?.resize()
  projectScoreChart?.resize()
  authorCountChart?.resize()
  authorScoreChart?.resize()
  codeLineChart?.resize()
}

// 监听数据变化
watch(() => [
  props.projectCounts,
  props.projectScores,
  props.authorCounts,
  props.authorScores,
  props.authorCodeLines
], () => {
  if (!props.loading) {
    initAllCharts()
  }
}, { deep: true })

onMounted(() => {
  initAllCharts()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  projectCountChart?.dispose()
  projectScoreChart?.dispose()
  authorCountChart?.dispose()
  authorScoreChart?.dispose()
  codeLineChart?.dispose()
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.project-statistics-charts {
  width: 100%;
}

.chart-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  font-size: 16px;
}

.chart-container {
  height: 300px;
  width: 100%;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .chart-container {
    height: 250px;
  }
}
</style>