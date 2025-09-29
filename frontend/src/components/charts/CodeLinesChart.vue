<template>
  <div class="chart-wrapper">
    <v-chart
      v-loading="loading"
      :option="chartOption"
      style="height: 400px;"
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
  const additions = props.data.map(item => item.additions || 0)
  const deletions = props.data.map(item => -(item.deletions || 0)) // Negative for deletions

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: (params: any) => {
        const authorName = params[0].name
        const additionsValue = params.find((p: any) => p.seriesName === '新增')?.value || 0
        const deletionsValue = Math.abs(params.find((p: any) => p.seriesName === '删除')?.value || 0)

        return `${authorName}<br/>
          <span style="color: #67C23A;">● 新增: +${additionsValue}</span><br/>
          <span style="color: #F56C6C;">● 删除: -${deletionsValue}</span><br/>
          <strong>净变更: ${additionsValue - deletionsValue}</strong>`
      }
    },
    legend: {
      data: ['新增', '删除'],
      bottom: 0
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
      axisLabel: {
        formatter: (value: number) => {
          return Math.abs(value).toString()
        }
      },
      axisLine: {
        show: true,
        lineStyle: {
          color: '#333'
        }
      },
      splitLine: {
        show: true,
        lineStyle: {
          type: 'dashed'
        }
      }
    },
    series: [
      {
        name: '新增',
        type: 'bar',
        stack: 'total',
        data: additions,
        itemStyle: {
          color: '#67C23A' // Green for additions
        },
        label: {
          show: false
        }
      },
      {
        name: '删除',
        type: 'bar',
        stack: 'total',
        data: deletions,
        itemStyle: {
          color: '#F56C6C' // Red for deletions
        },
        label: {
          show: false
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
  height: 400px;
  color: #909399;
  font-size: 14px;
}
</style>