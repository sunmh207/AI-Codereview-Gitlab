<template>
  <div class="chart-wrapper">
    <v-chart
      v-loading="loading"
      :option="chartOption"
      style="height: 300px;"
      autoresize
    />
    <div v-if="!loading && data.length === 0" class="empty-state">
      暂无数据
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
} from 'echarts/components'
import type { AuthorStatistics } from '@/api/reviews'

use([
  CanvasRenderer,
  BarChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
])

interface Props {
  data: AuthorStatistics[]
  loading: boolean
}

const props = defineProps<Props>()

const chartOption = computed(() => {
  if (!props.data || props.data.length === 0) {
    return {}
  }

  const authors = props.data.map(item => item.author)
  const scores = props.data.map(item => item.average_score || 0)

  // Generate pastel colors
  const colors = [
    '#ffb3ba', '#ffdfba', '#ffffba', '#baffc9', '#bae1ff',
    '#c9baff', '#ffbaf0', '#d4baff', '#badfff', '#ffbacc'
  ]

  // Get score color based on value
  const getScoreColor = (score: number) => {
    if (score >= 80) return '#67C23A' // Green
    if (score >= 60) return '#E6A23C' // Orange
    return '#F56C6C' // Red
  }

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: (params: any) => {
        const data = params[0]
        return `${data.name}<br/>平均得分: ${data.value.toFixed(2)}`
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: authors,
      axisLabel: {
        rotate: 45,
        fontSize: 12
      }
    },
    yAxis: {
      type: 'value',
      max: 100,
      min: 0,
      axisLabel: {
        formatter: '{value}'
      }
    },
    series: [
      {
        name: '平均得分',
        type: 'bar',
        data: scores.map((value) => ({
          value,
          itemStyle: {
            color: getScoreColor(value)
          }
        })),
        barWidth: '60%',
        label: {
          show: true,
          position: 'top',
          fontSize: 12,
          formatter: '{c}'
        }
      }
    ]
  }
})
</script>

<style scoped>
.chart-wrapper {
  position: relative;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: #909399;
  font-size: 14px;
}
</style>