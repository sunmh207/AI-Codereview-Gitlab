<template>
  <div class="dashboard">
    <div class="header">
      <h2>审查日志</h2>
      <div class="header-buttons">
        <button class="chat-button" @click="goToChat">
          <span class="chat-icon">💬</span>
          CHAT
        </button>
        <button class="prompt-button" @click="goToPrompt">
          <span class="prompt-icon">📜</span>
          提示词
        </button>
        <button class="config-button" @click="goToConfig">
          <span class="config-icon">⚙️</span>
          环境配置
        </button>
      </div>
    </div>
    
    <!-- 标签页 -->
    <div class="tabs">
      <button 
        :class="['tab-button', { active: activeTab === 'mr' }]"
        @click="activeTab = 'mr'"
      >
        Merge Request
      </button>
      <button 
        :class="['tab-button', { active: activeTab === 'push' }]"
        @click="activeTab = 'push'"
      >
        Push
      </button>
    </div>

    <!-- 筛选器 -->
    <div class="filters">
      <div class="filter-group">
        <label>开始日期：</label>
        <input type="date" v-model="startDate" />
      </div>
      <div class="filter-group">
        <label>结束日期：</label>
        <input type="date" v-model="endDate" />
      </div>
      <div class="filter-group">
        <label>用户名：</label>
        <select v-model="selectedAuthors" multiple>
          <option v-for="author in uniqueAuthors" :key="author" :value="author">
            {{ author }}
          </option>
        </select>
      </div>
      <div class="filter-group">
        <label>项目名：</label>
        <select v-model="selectedProjects" multiple>
          <option v-for="project in uniqueProjects" :key="project" :value="project">
            {{ project }}
          </option>
        </select>
      </div>
    </div>

    <!-- 数据表格 -->
    <div class="table-container">
      <table>
        <thead>
          <tr>
            <th v-for="column in columns" :key="column.key">{{ column.label }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, index) in filteredData" :key="index">
            <td v-for="column in columns" :key="column.key">
              <template v-if="column.key === 'score'">
                <div class="progress-bar" @click="showDetail(row)">
                  <div 
                    class="progress" 
                    :style="{ width: `${row[column.key]}%` }"
                  >
                    <span class="score-text">{{ row[column.key] }}</span>
                  </div>
                </div>
              </template>
              <template v-else-if="column.key === 'url'">
                <a :href="row[column.key]" target="_blank">查看</a>
              </template>
              <template v-else>
                {{ row[column.key] }}
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 统计信息 -->
    <div class="stats">
      <p>总记录数: {{ totalRecords }}</p>
      <p>平均分: {{ averageScore.toFixed(2) }}</p>
    </div>

    <!-- 图表区域 -->
    <div class="charts">
      <div class="chart-container">
        <h3>项目提交次数</h3>
        <canvas ref="projectCountChart"></canvas>
      </div>
      <div class="chart-container">
        <h3>项目平均分数</h3>
        <canvas ref="projectScoreChart"></canvas>
      </div>
      <div class="chart-container">
        <h3>人员提交次数</h3>
        <canvas ref="authorCountChart"></canvas>
      </div>
      <div class="chart-container">
        <h3>人员平均分数</h3>
        <canvas ref="authorScoreChart"></canvas>
      </div>
    </div>

    <!-- 详情模态框 -->
    <DetailModal 
      v-if="showModal"
      :mrData="selectedData"
      @close="closeModal"
    />
  </div>
</template>

<script>
import Chart from 'chart.js/auto'
import DetailModal from './DetailModal.vue'

export default {
  name: 'DashboardComponent',
  components: {
    DetailModal
  },
  data() {
    return {
      activeTab: 'mr',
      startDate: this.getDefaultStartDate(),
      endDate: new Date().toISOString().split('T')[0],
      selectedAuthors: [],
      selectedProjects: [],
      data: [],
      uniqueAuthors: [],
      uniqueProjects: [],
      charts: {
        projectCount: null,
        projectScore: null,
        authorCount: null,
        authorScore: null
      },
      showModal: false,
      selectedData: null
    }
  },
  computed: {
    columns() {
      return this.activeTab === 'mr' 
        ? [
            { key: 'project_name', label: '项目名' },
            { key: 'author', label: '作者' },
            { key: 'source_branch', label: '源分支' },
            { key: 'target_branch', label: '目标分支' },
            { key: 'updated_at', label: '更新时间' },
            { key: 'commit_messages', label: '提交信息' },
            { key: 'score', label: '分数' },
            { key: 'url', label: '链接' }
          ]
        : [
            { key: 'project_name', label: '项目名' },
            { key: 'author', label: '作者' },
            { key: 'branch', label: '分支' },
            { key: 'updated_at', label: '更新时间' },
            { key: 'commit_messages', label: '提交信息' },
            { key: 'score', label: '分数' }
          ]
    },
    filteredData() {
      return this.data.filter(row => {
        const date = new Date(row.updated_at)
        const start = new Date(this.startDate)
        const end = new Date(this.endDate)
        end.setHours(23, 59, 59, 999)
        
        const dateMatch = date >= start && date <= end
        const authorMatch = this.selectedAuthors.length === 0 || this.selectedAuthors.includes(row.author)
        const projectMatch = this.selectedProjects.length === 0 || this.selectedProjects.includes(row.project_name)
        
        return dateMatch && authorMatch && projectMatch
      })
    },
    totalRecords() {
      return this.filteredData.length
    },
    averageScore() {
      if (this.filteredData.length === 0) return 0
      return this.filteredData.reduce((sum, row) => sum + row.score, 0) / this.filteredData.length
    }
  },
  methods: {
    goToChat() {
      this.$router.push({
        path: '/chat',
        replace: true
      })
    },
    goToConfig() {
      this.$router.push({
        path: '/config',
        replace: true
      })
    },
    goToPrompt() {
      this.$router.push({
        path: '/prompt',
        replace: true
      })
    },
    getDefaultStartDate() {
      const date = new Date()
      date.setDate(date.getDate() - 7)
      return date.toISOString().split('T')[0]
    },
    async fetchData() {
      try {
        const endpoint = this.activeTab === 'mr' ? '/api/mr-logs' : '/api/push-logs'
        const params = new URLSearchParams({
          start_date: this.startDate,
          end_date: this.endDate
        })
        
        if (this.selectedAuthors.length > 0) {
          this.selectedAuthors.forEach(author => {
            params.append('authors[]', author)
          })
        }
        
        if (this.selectedProjects.length > 0) {
          this.selectedProjects.forEach(project => {
            params.append('projects[]', project)
          })
        }
        
        const response = await fetch(`${endpoint}?${params.toString()}`)
        if (response.ok) {
          const rawData = await response.json()
          // 处理时间戳和格式化数据
          this.data = rawData.map(item => ({
            ...item,
            updated_at: new Date(item.updated_at * 1000).toLocaleString(),
            score: parseFloat(item.score) || 0,
            commit_messages: item.commit_messages || '',
            branch: item.branch || item.target_branch || '',
            source_branch: item.source_branch || '',
            target_branch: item.target_branch || '',
            url: item.url || ''
          }))
          this.updateUniqueValues()
          this.updateCharts()
        } else {
          console.error('获取数据失败:', await response.text())
        }
      } catch (error) {
        console.error('获取数据失败:', error)
      }
    },
    updateUniqueValues() {
      this.uniqueAuthors = [...new Set(this.data.map(row => row.author))]
      this.uniqueProjects = [...new Set(this.data.map(row => row.project_name))]
    },
    updateCharts() {
      // 项目提交次数图表
      const projectCounts = this.getProjectCounts()
      this.updateChart('projectCount', '项目提交次数', projectCounts)

      // 项目平均分数图表
      const projectScores = this.getProjectScores()
      this.updateChart('projectScore', '项目平均分数', projectScores)

      // 人员提交次数图表
      const authorCounts = this.getAuthorCounts()
      this.updateChart('authorCount', '人员提交次数', authorCounts)

      // 人员平均分数图表
      const authorScores = this.getAuthorScores()
      this.updateChart('authorScore', '人员平均分数', authorScores)
    },
    updateChart(chartKey, label, data) {
      if (this.charts[chartKey]) {
        this.charts[chartKey].destroy()
      }

      const ctx = this.$refs[`${chartKey}Chart`].getContext('2d')
      this.charts[chartKey] = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: data.labels,
          datasets: [{
            label: label,
            data: data.values,
            backgroundColor: this.generateColors(data.labels.length, label)
          }]
        },
        options: {
          responsive: true,
          scales: {
            y: {
              beginAtZero: true
            }
          }
        }
      })
    },
    generateColors(count, label) {
      // 为不同类型的图表设置不同的颜色方案
      const colorSchemes = {
        projectCount: [
          '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEEAD',
          '#D4A5A5', '#9B59B6', '#3498DB', '#E67E22', '#2ECC71'
        ],
        projectScore: [
          '#2ECC71', '#E74C3C', '#F1C40F', '#9B59B6', '#3498DB',
          '#1ABC9C', '#E67E22', '#34495E', '#7F8C8D', '#16A085'
        ],
        authorCount: [
          '#3498DB', '#E74C3C', '#2ECC71', '#F1C40F', '#9B59B6',
          '#1ABC9C', '#E67E22', '#34495E', '#7F8C8D', '#16A085'
        ],
        authorScore: [
          '#9B59B6', '#3498DB', '#E74C3C', '#2ECC71', '#F1C40F',
          '#1ABC9C', '#E67E22', '#34495E', '#7F8C8D', '#16A085'
        ]
      }

      // 获取当前图表的类型
      const chartType = Object.keys(this.charts).find(key => 
        this.charts[key] && this.charts[key].data.datasets[0].label === label
      )

      // 如果找不到对应的图表类型，使用默认颜色方案
      if (!chartType || !colorSchemes[chartType]) {
        return Array(count).fill().map((_, i) => 
          `hsl(${(i * 360) / count}, 70%, 50%)`
        )
      }

      // 如果数据点数量超过预定义的颜色数量，循环使用颜色
      const colors = colorSchemes[chartType]
      return Array(count).fill().map((_, i) => colors[i % colors.length])
    },
    getProjectCounts() {
      const counts = {}
      this.filteredData.forEach(row => {
        counts[row.project_name] = (counts[row.project_name] || 0) + 1
      })
      return {
        labels: Object.keys(counts),
        values: Object.values(counts)
      }
    },
    getProjectScores() {
      const scores = {}
      const counts = {}
      this.filteredData.forEach(row => {
        scores[row.project_name] = (scores[row.project_name] || 0) + row.score
        counts[row.project_name] = (counts[row.project_name] || 0) + 1
      })
      return {
        labels: Object.keys(scores),
        values: Object.keys(scores).map(key => scores[key] / counts[key])
      }
    },
    getAuthorCounts() {
      const counts = {}
      this.filteredData.forEach(row => {
        counts[row.author] = (counts[row.author] || 0) + 1
      })
      return {
        labels: Object.keys(counts),
        values: Object.values(counts)
      }
    },
    getAuthorScores() {
      const scores = {}
      const counts = {}
      this.filteredData.forEach(row => {
        scores[row.author] = (scores[row.author] || 0) + row.score
        counts[row.author] = (counts[row.author] || 0) + 1
      })
      return {
        labels: Object.keys(scores),
        values: Object.keys(scores).map(key => scores[key] / counts[key])
      }
    },
    showDetail(row) {
      this.selectedData = row
      this.showModal = true
    },
    closeModal() {
      this.showModal = false
      this.selectedData = null
    }
  },
  watch: {
    activeTab() {
      this.fetchData()
    },
    startDate() {
      this.updateCharts()
    },
    endDate() {
      this.updateCharts()
    },
    selectedAuthors() {
      this.updateCharts()
    },
    selectedProjects() {
      this.updateCharts()
    }
  },
  mounted() {
    this.fetchData()
  }
}
</script>

<style scoped>
.dashboard {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chat-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s;
}

.chat-button:hover {
  background-color: #45a049;
}

.chat-icon {
  font-size: 16px;
}

.config-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s;
}

.config-button:hover {
  background-color: #45a049;
}

.config-icon {
  font-size: 16px;
}

.tabs {
  margin-bottom: 20px;
}

.tab-button {
  padding: 10px 20px;
  margin-right: 10px;
  border: none;
  background: #f0f0f0;
  cursor: pointer;
  border-radius: 4px;
}

.tab-button.active {
  background: #4CAF50;
  color: white;
}

.filters {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.filter-group label {
  font-weight: bold;
}

.filter-group input,
.filter-group select {
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.table-container {
  overflow-x: auto;
  margin-bottom: 20px;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

th {
  background-color: #f5f5f5;
  font-weight: bold;
}

.progress-bar {
  width: 100%;
  height: 20px;
  background-color: #f0f0f0;
  border-radius: 10px;
  overflow: hidden;
  cursor: pointer;
}

.progress {
  height: 100%;
  background-color: #4CAF50;
  transition: width 0.3s ease;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.progress:hover {
  background-color: #45a049;
}

.score-text {
  color: white;
  font-size: 12px;
  font-weight: bold;
  text-shadow: 0 0 2px rgba(0, 0, 0, 0.5);
}

.stats {
  margin: 20px 0;
  font-weight: bold;
}

.charts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

.chart-container {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.chart-container h3 {
  margin-top: 0;
  text-align: center;
}
.prompt-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s;
}

.prompt-button:hover {
  background-color: #45a049;
}
</style>