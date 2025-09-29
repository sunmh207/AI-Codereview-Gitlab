import axios from 'axios'
import { ElMessage } from 'element-plus'

// Create axios instance
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    const message = error.response?.data?.message || error.message || 'Request failed'

    if (error.response?.status === 401) {
      // Unauthorized - redirect to login
      localStorage.removeItem('access_token')
      localStorage.removeItem('username')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    } else if (error.response?.status >= 500) {
      ElMessage.error('Server error, please try again later')
    } else {
      ElMessage.error(message)
    }

    return Promise.reject(error)
  }
)