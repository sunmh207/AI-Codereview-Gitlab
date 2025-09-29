<template>
  <div class="trend-chart">
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
  
  if (!hasData.value) return

  const option = getTrendOption()
  chartInstance.setOption(option, true)
}

// 获取最近30天的日期数组
const getLast30Days = () => {
  const dates = []
  for (let i = 29; i >= 0; i--) {
    const date = new Date()
    date.setDate(date.getDate() - i)
    dates.push(date.toISOString().split('T')[0])
  }
  return dates
}

// 按日期分组统计数据
const groupDataByDate = (data: any[]) => {
  const dateMap = new Map()
  const scoreMap = new Map()
  const countMap = new Map()
  
  data.forEach(item => {
    const date = item.updated_at?.split('T')[0] || item.created_at?.split('T')[0]
    if (date) {
      const count = dateMap.get(date) || 0
      const totalScore = scoreMap.get(date) || 0
      const itemCount = countMap.get(date) || 0
      
      dateMap.set(date, count + 1)
      scoreMap.set(date, totalScore + (item.score || 0))
      countMap.set(date, itemCount + 1)
    }
  })

  return { dateMap, scoreMap, countMap }
}

// 趋势图配置
const getTrendOption = () => {
  const dates = getLast30Days()
  
  // 处理MR数据
  const { dateMap: mrDateMap, scoreMap: mrScoreMap, countMap: mrCountMap } = groupDataByDate(props.mrData || [])
  
  // 处理Push数据
  const { dateMap: pushDateMap, scoreMap: pushScoreMap, countMap: pushCountMap } = groupDataByDate(props.pushData || [])
  
  // 生成数据数组
  const mrCounts = dates.map((date: string) => mrDateMap.get(date) || 0)
  const pushCounts = dates.map((date: string) => pushDateMap.get(date) || 0)
  
  // 计算平均分
  const mrAvgScores = dates.map((date: string) => {
    const count = mrCountMap.get(date) || 0
    const totalScore = mrScoreMap.get(date) || 0
    return count > 0 ? Math.round(totalScore / count) : 0
  })
  
  const pushAvgScores = dates.map((date: string) => {
    const count = pushCountMap.get(date) || 0
    const totalScore = pushScoreMap.get(date) || 0
    return count > 0 ? Math.round(totalScore / count) : 0
  })

  return {
    title: {
      text: '最近一月审查趋势',
      left: 'center',
      textStyle: { fontSize: 14 }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
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
      data: ['合并请求数量', '代码推送数量', '合并请求平均分', '代码推送平均分'],
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
      data: dates.map((date: string) => {
        const [year, month, day] = date.split('-')
        return `${month}-${day}`
      }),
      boundaryGap: false
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
        name: '合并请求数量',
        type: 'line',
        yAxisIndex: 0,
        data: mrCounts,
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
      },
      {
        name: '代码推送数量',
        type: 'line',
        yAxisIndex: 0,
        data: pushCounts,
        smooth: true,
        itemStyle: {
          color: '#67C23A'
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(103, 194, 58, 0.3)' },
              { offset: 1, color: 'rgba(103, 194, 58, 0.1)' }
            ]
          }
        }
      },
      {
        name: '合并请求平均分',
        type: 'line',
        yAxisIndex: 1,
        data: mrAvgScores,
        smooth: true,
        itemStyle: {
          color: '#E6A23C'
        },
        lineStyle: {
          type: 'dashed'
        }
      },
      {
        name: '代码推送平均分',
        type: 'line',
        yAxisIndex: 1,
        data: pushAvgScores,
        smooth: true,
        itemStyle: {
          color: '#F56C6C'
        },
        lineStyle: {
          type: 'dashed'
        }
      }
    ]
  }
}

// 监听数据变化
watch(() => [props.mrData, props.pushData], () => {
  nextTick(() => {
    updateChart()
  })
}, { deep: true, immediate: true })

// 监听hasData变化
watch(hasData, (newVal) => {
  if (newVal) {
    nextTick(() => {
      updateChart()
    })
  }
})

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
.trend-chart {
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