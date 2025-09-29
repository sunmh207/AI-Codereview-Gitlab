<template>
  <div class="push-reviews-view">
    <div class="page-header">
      <h1 class="page-title">推送审查</h1>
      <p class="page-description">查看和管理所有代码推送的审查记录</p>
    </div>

    <!-- 搜索和筛选 -->
    <el-card class="filter-card">
      <el-form :model="filters" :inline="true" class="filter-form">
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            @change="onDateRangeChange"
          />
        </el-form-item>
        
        <el-form-item label="开发者">
          <el-select
            v-model="filters.authors"
            multiple
            placeholder="选择开发者"
            style="width: 200px"
            clearable
            @change="onFiltersChange"
          >
            <el-option
              v-for="author in metadata.authors"
              :key="author"
              :label="author"
              :value="author"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="项目">
          <el-select
            v-model="filters.project_names"
            multiple
            placeholder="选择项目"
            style="width: 200px"
            clearable
            @change="onFiltersChange"
          >
            <el-option
              v-for="project in metadata.project_names"
              :key="project"
              :label="project"
              :value="project"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="得分范围">
          <el-select
            v-model="filters.scoreRange"
            placeholder="选择得分范围"
            style="width: 150px"
            clearable
            @change="onFiltersChange"
          >
            <el-option label="优秀 (80-100)" value="80-100" />
            <el-option label="良好 (60-79)" value="60-79" />
            <el-option label="需改进 (0-59)" value="0-59" />
          </el-select>
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="loadData">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button @click="resetFilters">
            <el-icon><Refresh /></el-icon>
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 数据表格 -->
    <el-card class="table-card">
      <template #header>
        <div class="table-header">
          <span>审查记录 (共 {{ pagination.total }} 条)</span>
          <div class="table-actions">
            <el-button size="small" @click="exportData">
              <el-icon><Download /></el-icon>
              导出
            </el-button>
          </div>
        </div>
      </template>
      
      <el-table
        :data="tableData"
        :loading="loading"
        stripe
        @sort-change="onSortChange"
      >
        <el-table-column prop="project_name" label="项目" width="150" />
        <el-table-column prop="author" label="开发者" width="120" />
        <el-table-column prop="commit_messages" label="提交信息" min-width="200">
          <template #default="{ row }">
            <div class="commit-message-cell" :title="row.commit_messages">
              {{ getFirstLine(row.commit_messages) }}
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="score" label="得分" width="80" sortable="custom">
          <template #default="{ row }">
            <el-tag :type="getScoreType(row.score)">{{ row.score }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="additions" label="新增行数" width="100" sortable="custom" />
        <el-table-column prop="deletions" label="删除行数" width="100" sortable="custom" />
        <el-table-column prop="updated_at" label="审查时间" width="160" sortable="custom">
          <template #default="{ row }">
            {{ formatDate(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="viewDetail(row)">
              查看详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="onPageSizeChange"
          @current-change="onPageChange"
        />
      </div>
    </el-card>

    <!-- 详情弹窗 -->
    <el-dialog
      v-model="detailVisible"
      title="审查详情"
      width="80%"
      :before-close="closeDetail"
    >
      <div v-if="currentDetail" class="detail-content">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="项目名称">{{ currentDetail.project_name }}</el-descriptions-item>
          <el-descriptions-item label="开发者">{{ currentDetail.author }}</el-descriptions-item>
          <el-descriptions-item label="提交信息" :span="2">
            <pre class="commit-message-detail">{{ currentDetail.commit_messages }}</pre>
          </el-descriptions-item>
          <el-descriptions-item label="得分">
            <el-tag :type="getScoreType(currentDetail.score)">{{ currentDetail.score }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="审查时间">{{ formatDate(currentDetail.updated_at) }}</el-descriptions-item>
          <el-descriptions-item label="新增行数">{{ currentDetail.additions }}</el-descriptions-item>
          <el-descriptions-item label="删除行数">{{ currentDetail.deletions }}</el-descriptions-item>
        </el-descriptions>
        
        <div class="review-content">
          <h4>审查内容</h4>
          <MarkdownRenderer :content="currentDetail.review_result || ''" />
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh, Download } from '@element-plus/icons-vue'
import { getPushReviews, getMetadata, type ReviewData, type ReviewFilters } from '@/api/reviews'
import { formatDate, getDefaultDateRange } from '@/utils/date'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'

// 数据状态
const loading = ref(false)
const tableData = ref<ReviewData[]>([])
const metadata = ref<{ authors: string[], project_names: string[] }>({ authors: [], project_names: [] })
const detailVisible = ref(false)
const currentDetail = ref<ReviewData | null>(null)

// 筛选条件
const dateRange = ref<[string, string]>(['', ''])
const filters = reactive<ReviewFilters & { scoreRange?: string }>({
  authors: [],
  project_names: [],
  scoreRange: undefined
})

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 20,  // 调整默认页面大小，在用户体验与性能之间找到平衡点
  total: 0
})

// 排序
const sortConfig = ref({
  prop: '',
  order: ''
})

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      page_size: pagination.pageSize
    }

    // 添加筛选条件
    if (dateRange.value[0]) params.start_date = dateRange.value[0]
    if (dateRange.value[1]) params.end_date = dateRange.value[1]
    if (filters.authors?.length) params.authors = filters.authors
    if (filters.project_names?.length) params.project_names = filters.project_names
    
    // 得分范围筛选
    if (filters.scoreRange) {
      const [min, max] = filters.scoreRange.split('-').map(Number)
      params.score_min = min
      params.score_max = max
    }

    // 排序
    if (sortConfig.value.prop) {
      params.sort_by = sortConfig.value.prop
      params.sort_order = sortConfig.value.order === 'ascending' ? 'asc' : 'desc'
    }

    const result = await getPushReviews(params)
    tableData.value = result.data
    pagination.total = result.total
  } catch (error: any) {
    ElMessage.error('获取数据失败')
  } finally {
    loading.value = false
  }
}

// 加载元数据
const loadMetadata = async () => {
  try {
    const result = await getMetadata({ type: 'push' })
    metadata.value = result
  } catch (error: any) {
    ElMessage.error('获取元数据失败')
  }
}

// 事件处理
const onDateRangeChange = () => {
  loadData()
}

const onFiltersChange = () => {
  pagination.page = 1 // 重置到第一页
  loadData()
}

const onPageChange = () => {
  loadData()
}

const onPageSizeChange = () => {
  pagination.page = 1
  loadData()
}

const onSortChange = ({ prop, order }: any) => {
  sortConfig.value = { prop, order }
  loadData()
}

const resetFilters = () => {
  const [startDate, endDate] = getDefaultDateRange()
  dateRange.value = [startDate, endDate]
  filters.authors = []
  filters.project_names = []
  filters.scoreRange = undefined
  pagination.page = 1
  sortConfig.value = { prop: '', order: '' }
  loadData()
}

const viewDetail = (row: ReviewData) => {
  currentDetail.value = row
  detailVisible.value = true
}

const closeDetail = () => {
  detailVisible.value = false
  currentDetail.value = null
}

const exportData = () => {
  ElMessage.info('导出功能开发中...')
}

const getScoreType = (score: number) => {
  if (score >= 80) return 'success'
  if (score >= 60) return 'warning'
  return 'danger'
}

// 获取提交信息的第一行
const getFirstLine = (message: string) => {
  if (!message) return ''
  const newlineChar = String.fromCharCode(10)
  const newlineIndex = message.indexOf(newlineChar)
  return newlineIndex === -1 ? message : message.substring(0, newlineIndex)
}

// 初始化
onMounted(async () => {
  const [startDate, endDate] = getDefaultDateRange()
  dateRange.value = [startDate, endDate]
  
  await loadMetadata()
  await loadData()
})
</script>

<style scoped>
.push-reviews-view {
  padding: 0;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 8px 0;
}

.page-description {
  color: #6b7280;
  margin: 0;
}

.filter-card {
  margin-bottom: 20px;
}

.filter-form {
  margin: 0;
}

.table-card {
  margin-bottom: 20px;
}

.table-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}

.table-actions {
  display: flex;
  gap: 8px;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.detail-content {
  padding: 0;
  max-height: 70vh;
  overflow-y: auto;
}

.review-content {
  margin-top: 20px;
  padding: 16px;
  background-color: var(--el-fill-color-extra-light);
  border-radius: 6px;
}

.review-content h4 {
  margin: 0 0 12px 0;
  color: #1f2937;
}

/* 提交信息样式 */
.commit-message-cell {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}

.commit-message-detail {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 4px;
  padding: 12px;
  margin: 0;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
  color: #495057;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 200px;
  overflow-y: auto;
}

.review-text {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 16px;
  white-space: pre-wrap;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 14px;
  line-height: 1.5;
  color: #374151;
}

/* 自定义滚动条样式 */
.detail-content::-webkit-scrollbar,
.review-content::-webkit-scrollbar {
  width: 6px;
}

.detail-content::-webkit-scrollbar-track,
.review-content::-webkit-scrollbar-track {
  background: var(--el-fill-color-light);
  border-radius: 3px;
}

.detail-content::-webkit-scrollbar-thumb,
.review-content::-webkit-scrollbar-thumb {
  background: var(--el-border-color);
  border-radius: 3px;
}

.detail-content::-webkit-scrollbar-thumb:hover,
.review-content::-webkit-scrollbar-thumb:hover {
  background: var(--el-border-color-dark);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .filter-form {
    display: block;
  }
  
  .filter-form .el-form-item {
    display: block;
    margin-bottom: 16px;
  }
  
  .table-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
}
</style>