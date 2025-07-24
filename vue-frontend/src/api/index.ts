import axios from 'axios'
import dayjs from 'dayjs'
import type {
  MergeRequestLog,
  PushLog,
  FilterParams,
  LoginForm,
  User,
  PaginationResponse,
  UsersWithoutReviewData
} from '@/types'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// 将日期字符串转换为时间戳
const dateToTimestamp = (dateStr: string): number => {
  return dayjs(dateStr).unix()
}

// 认证相关 API
export const authApi = {
  // 用户登录
  async login(loginForm: LoginForm): Promise<{ success: boolean; user?: User; token?: string; message?: string }> {
    const response = await api.post('/auth/login', loginForm)
    return response
  },

  // 验证token
  async verifyToken(token: string): Promise<{ success: boolean; user?: User; message?: string }> {
    const response = await api.post('/auth/verify', { token })
    return response
  }
}

// 数据相关 API
export const reviewApi = {
  // 获取合并请求审查日志
  async getMergeRequestLogs(params: FilterParams): Promise<PaginationResponse<MergeRequestLog>> {
    const queryParams = new URLSearchParams()

    if (params.startDate) {
      queryParams.append('updated_at_gte', dateToTimestamp(params.startDate).toString())
    }
    if (params.endDate) {
      queryParams.append('updated_at_lte', dateToTimestamp(params.endDate + ' 23:59:59').toString())
    }
    if (params.authors.length > 0) {
      params.authors.forEach(author => queryParams.append('authors', author))
    }
    if (params.projectNames.length > 0) {
      params.projectNames.forEach(project => queryParams.append('project_names', project))
    }
    if (params.page) {
      queryParams.append('page', params.page.toString())
    }
    if (params.page_size) {
      queryParams.append('page_size', params.page_size.toString())
    }

    const response = await api.get(`/mr-logs?${queryParams.toString()}`)
    return response
  },

  // 获取推送审查日志
  async getPushLogs(params: FilterParams): Promise<PaginationResponse<PushLog>> {
    const queryParams = new URLSearchParams()

    if (params.startDate) {
      queryParams.append('updated_at_gte', dateToTimestamp(params.startDate).toString())
    }
    if (params.endDate) {
      queryParams.append('updated_at_lte', dateToTimestamp(params.endDate + ' 23:59:59').toString())
    }
    if (params.authors.length > 0) {
      params.authors.forEach(author => queryParams.append('authors', author))
    }
    if (params.projectNames.length > 0) {
      params.projectNames.forEach(project => queryParams.append('project_names', project))
    }
    if (params.page) {
      queryParams.append('page', params.page.toString())
    }
    if (params.page_size) {
      queryParams.append('page_size', params.page_size.toString())
    }

    const response = await api.get(`/push-logs?${queryParams.toString()}`)
    return response
  },

  // 获取项目列表
  async getProjects(): Promise<string[]> {
    const response = await api.get('/projects')
    return response.data || []
  },

  // 获取开发者列表
  async getAuthors(): Promise<string[]> {
    const response = await api.get('/authors')
    return response.data || []
  },

  // 获取所有合并请求审查日志（用于图表）
  async getAllMergeRequestLogs(params: Omit<FilterParams, 'page' | 'page_size'>): Promise<MergeRequestLog[]> {
    const queryParams = new URLSearchParams()

    if (params.startDate) {
      queryParams.append('updated_at_gte', dateToTimestamp(params.startDate).toString())
    }
    if (params.endDate) {
      queryParams.append('updated_at_lte', dateToTimestamp(params.endDate + ' 23:59:59').toString())
    }
    if (params.authors.length > 0) {
      params.authors.forEach(author => queryParams.append('authors', author))
    }
    if (params.projectNames.length > 0) {
      params.projectNames.forEach(project => queryParams.append('project_names', project))
    }

    const response = await api.get(`/mr-logs/all?${queryParams.toString()}`)
    return response.data || []
  },

  // 获取所有推送审查日志（用于图表）
  async getAllPushLogs(params: Omit<FilterParams, 'page' | 'page_size'>): Promise<PushLog[]> {
    const queryParams = new URLSearchParams()

    if (params.startDate) {
      queryParams.append('updated_at_gte', dateToTimestamp(params.startDate).toString())
    }
    if (params.endDate) {
      queryParams.append('updated_at_lte', dateToTimestamp(params.endDate + ' 23:59:59').toString())
    }
    if (params.authors.length > 0) {
      params.authors.forEach(author => queryParams.append('authors', author))
    }
    if (params.projectNames.length > 0) {
      params.projectNames.forEach(project => queryParams.append('project_names', project))
    }

    const response = await api.get(`/push-logs/all?${queryParams.toString()}`)
    return response.data || []
  },

  // 获取配置信息
  async getConfig(): Promise<{ push_review_enabled: boolean; dashboard_user: string; show_security_warning: boolean }> {
    const response = await api.get('/config')
    return response.data || { push_review_enabled: false, dashboard_user: 'admin', show_security_warning: false }
  },

  // 获取未审查用户列表
  async getUsersWithoutReview(params: {
    time_range?: string
    start_time?: number
    end_time?: number
  }): Promise<UsersWithoutReviewData> {
    const queryParams = new URLSearchParams()

    if (params.time_range) {
      queryParams.append('time_range', params.time_range)
    }
    if (params.start_time) {
      queryParams.append('start_time', params.start_time.toString())
    }
    if (params.end_time) {
      queryParams.append('end_time', params.end_time.toString())
    }

    const response = await api.get(`/review/users_without_review?${queryParams.toString()}`)
    return response.data || {
      users_without_review: [],
      total_developers: 0,
      total_unreviewed_users: 0,
      review_coverage_rate: 0,
      time_range: ''
    }
  }
}

export default api
