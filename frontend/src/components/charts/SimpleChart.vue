<template>
  <div class="simple-chart">
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
import { ref, onMounted, watch, nextTick, onBeforeUnmount, computed } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import * as echarts from 'echarts'

interface Props {
  data: any[]
  loading: boolean
  chartType: 'project-counts' | 'project-scores' | 'author-counts' | 'author-scores' | 'author-code-lines'
}

const props = withDefaults(defineProps<Props>(), {
  data: () => [],
  loading: false,
  chartType: 'project-counts'
})

const chartRef = ref<HTMLElement>()
let chartInstance: echarts.ECharts | null = null

// 检查是否有数据
const hasData = computed(() => {
  const dataArray = Array.isArray(props.data) ? props.data : []
  return dataArray.length > 0
})

// 初始化图表
const initChart = () => {
  if (!chartRef.value || !hasData.value) return
  
  if (chartInstance) {
    chartInstance.dispose()
  }
  
  chartInstance = echarts.init(chartRef.value)
  updateChart()
}

// 更新图表
const updateChart = () => {
  if (!chartInstance || !hasData.value) return

  let option: any = {}

  switch (props.chartType) {
    case 'project-counts':
      option = getProjectCountsOption()
      break
    case 'project-scores':
      option = getProjectScoresOption()
      break
    case 'author-counts':
      option = getAuthorCountsOption()
      break
    case 'author-scores':
      option = getAuthorScoresOption()
      break
    case 'author-code-lines':
      option = getAuthorCodeLinesOption()
      break
  }

  chartInstance.setOption(option, true)
}

// 项目数量统计图表配置
const getProjectCountsOption = () => {
  const data = props.data.slice(0, 10) // 取前10个
  
  return {
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
      name: '审查数量'
    },
    series: [{
      data: data.map(item => item.count),
      type: 'bar',
      itemStyle: {
        color: '#409EFF'
      }
    }]
  }
}

// 项目得分统计图表配置
const getProjectScoresOption = () => {
  const data = props.data.slice(0, 10)
  
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: (params: any) => {
        const item = params[0]
        return `${item.name}<br/>平均得分: ${item.value?.toFixed(1) || 'N/A'}`
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
      data: data.map(item => item.average_score),
      type: 'bar',
      itemStyle: {
        color: '#67C23A'
      }
    }]
  }
}

// 开发者数量统计图表配置
const getAuthorCountsOption = () => {
  const data = props.data.slice(0, 10)
  
  return {
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
      name: '审查数量'
    },
    series: [{
      data: data.map(item => item.count),
      type: 'bar',
      itemStyle: {
        color: '#E6A23C'
      }
    }]
  }
}

// 开发者得分统计图表配置
const getAuthorScoresOption = () => {
  const data = props.data.slice(0, 10)
  
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: (params: any) => {
        const item = params[0]
        return `${item.name}<br/>平均得分: ${item.value?.toFixed(1) || 'N/A'}`
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
      data: data.map(item => item.average_score),
      type: 'bar',
      itemStyle: {
        color: '#F56C6C'
      }
    }]
  }
}

// 开发者代码行数统计图表配置
const getAuthorCodeLinesOption = () => {
  const data = props.data.slice(0, 10)
  
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: (params: any) => {
        let result = params[0].name + '<br/>'
        params.forEach((param: any) => {
          const value = Math.abs(param.value)
          const type = param.seriesName
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
        stack: 'total',
        data: data.map(item => item.additions || 0),
        itemStyle: {
          color: '#67C23A'
        }
      },
      {
        name: '删除行数',
        type: 'bar',
        stack: 'total',
        data: data.map(item => item.deletions || 0),
        itemStyle: {
          color: '#F56C6C'
        }
      }
    ]
  }
}

// 监听数据变化
watch(() => [props.data, props.chartType], () => {
  nextTick(() => {
    if (!props.loading && hasData.value) {
      if (!chartInstance) {
        initChart()
      } else {
        updateChart()
      }
    }
  })
}, { deep: true })

// 监听loading状态变化
watch(() => props.loading, (newLoading) => {
  if (!newLoading && hasData.value) {
    nextTick(() => {
      initChart()
    })
  }
})

// 窗口大小变化处理
const handleResize = () => {
  if (chartInstance) {
    chartInstance.resize()
  }
}

onMounted(() => {
  nextTick(() => {
    if (!props.loading && hasData.value) {
      initChart()
    }
    window.addEventListener('resize', handleResize)
  })
})

onBeforeUnmount(() => {
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.simple-chart {
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