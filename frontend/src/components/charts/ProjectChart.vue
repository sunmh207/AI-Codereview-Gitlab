<template>
  <div class="project-chart">
    <div v-if="loading" class="loading-container">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载中...</span>
    </div>
    <div v-else-if="!hasData" class="empty-container">
      <el-empty description="暂无数据" />
    </div>
    <div v-else ref="chartRef" class="chart-container"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick, computed } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import * as echarts from 'echarts'

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

const chartRef = ref<HTMLElement>()
let chartInstance: echarts.ECharts | null = null

const hasData = computed(() => {
  return (props.mrData && props.mrData.length > 0) || (props.pushData && props.pushData.length > 0)
})

// 初始化图表
const initChart = () => {
  if (!chartRef.value) return
  
  chartInstance = echarts.init(chartRef.value)
  updateChart()
}

// 更新图表
const updateChart = () => {
  if (!chartInstance) {
    if (chartRef.value) {
      initChart()
    }
    return
  }
  
  if (!hasData.value) {
    console.log('ProjectChart: No data available')
    return
  }

  console.log('ProjectChart updateChart:', {
    mrLength: props.mrData?.length || 0,
    pushLength: props.pushData?.length || 0,
    hasData: hasData.value
  })

  const option = getProjectOption()
  chartInstance.setOption(option, true)
}

// 按项目分组统计数据
const groupDataByProject = () => {
  const projectStats = new Map()
  
  // 处理Push数据
  if (props.pushData && props.pushData.length > 0) {
    props.pushData.forEach(item => {
      const projectName = item.project_name || '未知项目'
      const stats = projectStats.get(projectName) || {
        pushCount: 0,
        mrCount: 0,
        totalScore: 0,
        scoreCount: 0
      }
      
      stats.pushCount += 1
      if (item.score) {
        stats.totalScore += item.score
        stats.scoreCount += 1
      }
      
      projectStats.set(projectName, stats)
    })
  }
  
  // 处理MR数据
  if (props.mrData && props.mrData.length > 0) {
    props.mrData.forEach(item => {
      const projectName = item.project_name || '未知项目'
      const stats = projectStats.get(projectName) || {
        pushCount: 0,
        mrCount: 0,
        totalScore: 0,
        scoreCount: 0
      }
      
      stats.mrCount += 1
      if (item.score) {
        stats.totalScore += item.score
        stats.scoreCount += 1
      }
      
      projectStats.set(projectName, stats)
    })
  }
  
  return projectStats
}

// 项目分布图配置
const getProjectOption = () => {
  const projectStats = groupDataByProject()
  
  const projects = Array.from(projectStats.keys())
  const pushCounts = projects.map(project => projectStats.get(project)?.pushCount || 0)
  const mrCounts = projects.map(project => projectStats.get(project)?.mrCount || 0)
  const avgScores = projects.map(project => {
    const stats = projectStats.get(project)
    return stats && stats.scoreCount > 0 
      ? Math.round(stats.totalScore / stats.scoreCount) 
      : 0
  })

  console.log('ProjectChart data:', {
    projects,
    pushCounts,
    mrCounts,
    avgScores
  })

  return {
    title: {
      text: '项目分布统计',
      left: 'center',
      textStyle: { fontSize: 14 }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: function(params: any) {
        let result = `${params[0].axisValue}<br/>`
        params.forEach((param: any) => {
          const unit = param.seriesName.includes('平均分') ? '分' : '条'
          result += `${param.marker}${param.seriesName}: ${param.value}${unit}<br/>`
        })
        return result
      }
    },
    legend: {
      data: ['代码推送', '合并请求', '平均分'],
      top: 30
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: projects,
      axisLabel: {
        rotate: 45,
        interval: 0
      }
    },
    yAxis: [
      {
        type: 'value',
        name: '数量',
        position: 'left',
        axisLabel: {
          formatter: '{value} 条'
        }
      },
      {
        type: 'value',
        name: '平均分',
        position: 'right',
        axisLabel: {
          formatter: '{value} 分'
        },
        min: 0,
        max: 100
      }
    ],
    series: [
      {
        name: '代码推送',
        type: 'bar',
        yAxisIndex: 0,
        data: pushCounts,
        itemStyle: {
          color: '#67C23A'
        },
        stack: 'count'
      },
      {
        name: '合并请求',
        type: 'bar',
        yAxisIndex: 0,
        data: mrCounts,
        itemStyle: {
          color: '#409EFF'
        },
        stack: 'count'
      },
      {
        name: '平均分',
        type: 'line',
        yAxisIndex: 1,
        data: avgScores,
        itemStyle: {
          color: '#E6A23C'
        },
        lineStyle: {
          width: 3
        },
        symbol: 'circle',
        symbolSize: 6
      }
    ]
  }
}

// 监听数据变化
watch(() => [props.mrData, props.pushData], () => {
  nextTick(() => {
    updateChart()
  })
}, { deep: true })

// 监听窗口大小变化
const handleResize = () => {
  if (chartInstance) {
    chartInstance.resize()
  }
}

onMounted(() => {
  nextTick(() => {
    initChart()
    window.addEventListener('resize', handleResize)
  })
})

// 清理
const cleanup = () => {
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
  window.removeEventListener('resize', handleResize)
}

// 组件卸载时清理
import { onBeforeUnmount } from 'vue'
onBeforeUnmount(() => {
  cleanup()
})
</script>

<style scoped>
.project-chart {
  width: 100%;
  height: 100%;
  position: relative;
}

.chart-container {
  width: 100%;
  height: 100%;
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
</style>