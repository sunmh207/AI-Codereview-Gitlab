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
  const counts = props.data.map(item => item.count || 0)

  // Generate colors from a predefined palette
  const colors = [
    '#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeaa7',
    '#dda0dd', '#98d8c8', '#74b9ff', '#fd79a8', '#fdcb6e'
  ]

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: (params: any) => {
        const data = params[0]
        return `${data.name}<br/>提交数量: ${data.value}`
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
      minInterval: 1
    },
    series: [
      {
        name: '提交数量',
        type: 'bar',
        data: counts.map((value, index) => ({
          value,
          itemStyle: {
            color: colors[index % colors.length]
          }
        })),
        barWidth: '60%',
        label: {
          show: true,
          position: 'top',
          fontSize: 12
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