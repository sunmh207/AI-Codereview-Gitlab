<template>
  <div class="statistics-charts">
    <div v-if="loading" class="loading-container">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载中...</span>
    </div>
    <div v-else-if="!data || data.length === 0" class="empty-container">
      <el-empty description="暂无数据" />
    </div>
    <div v-else ref="chartRef" class="chart-container"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import * as echarts from 'echarts'

interface Props {
  data: any[]
  loading: boolean
  type: 'mr' | 'push'
  chartType: 'trend' | 'project' | 'author' | 'score'
}

const props = withDefaults(defineProps<Props>(), {
  data: () => [],
  loading: false,
  type: 'mr',
  chartType: 'trend'
})

const chartRef = ref<HTMLElement>()
let chartInstance: echarts.ECharts | null = null

// 初始化图表
const initChart = () => {
  if (!chartRef.value) return
  
  chartInstance = echarts.init(chartRef.value)
  updateChart()
}

// 更新图表
const updateChart = () => {
  if (!chartInstance || !props.data || props.data.length === 0) return

  let option: any = {}

  switch (props.chartType) {
    case 'trend':
      option = getTrendOption()
      break
    case 'project':
      option = getProjectOption()
      break
    case 'author':
      option = getAuthorOption()
      break
    case 'score':
      option = getScoreOption()
      break
  }

  chartInstance.setOption(option, true)
}

// 趋势图配置
const getTrendOption = () => {
  // 按日期分组统计
  const dateMap = new Map()
  props.data.forEach(item => {
    const date = item.updated_at?.split('T')[0] || item.created_at?.split('T')[0]
    if (date) {
      dateMap.set(date, (dateMap.get(date) || 0) + 1)
    }
  })

  const dates = Array.from(dateMap.keys()).sort()
  const counts = dates.map(date => dateMap.get(date))

  return {
    title: {
      text: `${props.type === 'mr' ? '合并请求' : '代码推送'}趋势`,
      left: 'center',
      textStyle: { fontSize: 14 }
    },
    tooltip: {
      trigger: 'axis',
      formatter: '{b}: {c} 条'
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: {
        formatter: (value: string) => {
          return value.split('-').slice(1).join('-')
        }
      }
    },
    yAxis: {
      type: 'value',
      name: '数量'
    },
    series: [{
      data: counts,
      type: 'line',
      smooth: true,
      itemStyle: {
        color: '#409EFF'
      },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
            { offset: 1, color: 'rgba(64, 158, 255, 0.1)' }
          ]
        }
      }
    }]
  }
}

// 项目分布配置
const getProjectOption = () => {
  const projectMap = new Map()
  props.data.forEach(item => {
    const project = item.project_name
    if (project) {
      projectMap.set(project, (projectMap.get(project) || 0) + 1)
    }
  })

  const projects = Array.from(projectMap.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10) // 取前10个

  return {
    title: {
      text: '项目分布',
      left: 'center',
      textStyle: { fontSize: 14 }
    },
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c} ({d}%)'
    },
    series: [{
      name: '项目分布',
      type: 'pie',
      radius: ['40%', '70%'],
      data: projects.map(([name, value]) => ({ name, value })),
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      }
    }]
  }
}

// 开发者排行配置
const getAuthorOption = () => {
  const authorMap = new Map()
  props.data.forEach(item => {
    const author = item.author
    if (author) {
      authorMap.set(author, (authorMap.get(author) || 0) + 1)
    }
  })

  const authors = Array.from(authorMap.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10) // 取前10个

  return {
    title: {
      text: '开发者排行',
      left: 'center',
      textStyle: { fontSize: 14 }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    xAxis: {
      type: 'value',
      name: '数量'
    },
    yAxis: {
      type: 'category',
      data: authors.map(([name]) => name),
      axisLabel: {
        interval: 0
      }
    },
    series: [{
      data: authors.map(([, value]) => value),
      type: 'bar',
      itemStyle: {
        color: '#67C23A'
      }
    }]
  }
}

// 得分分布配置
const getScoreOption = () => {
  const scoreRanges = [
    { name: '0-20', min: 0, max: 20 },
    { name: '21-40', min: 21, max: 40 },
    { name: '41-60', min: 41, max: 60 },
    { name: '61-80', min: 61, max: 80 },
    { name: '81-100', min: 81, max: 100 }
  ]

  const scoreCounts = scoreRanges.map(range => {
    const count = props.data.filter(item => 
      item.score >= range.min && item.score <= range.max
    ).length
    return { name: range.name, value: count }
  })

  return {
    title: {
      text: '得分分布',
      left: 'center',
      textStyle: { fontSize: 14 }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    xAxis: {
      type: 'category',
      data: scoreCounts.map(item => item.name),
      name: '得分区间'
    },
    yAxis: {
      type: 'value',
      name: '数量'
    },
    series: [{
      data: scoreCounts.map(item => item.value),
      type: 'bar',
      itemStyle: {
        color: (params: any) => {
          const colors = ['#F56C6C', '#E6A23C', '#F7BA2A', '#67C23A', '#409EFF']
          return colors[params.dataIndex] || '#409EFF'
        }
      }
    }]
  }
}

// 监听数据变化
watch(() => [props.data, props.chartType], () => {
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
.statistics-charts {
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