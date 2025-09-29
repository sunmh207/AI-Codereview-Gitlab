import { defineStore } from 'pinia'
import { ref, readonly } from 'vue'
import { apiClient } from '@/api/client'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(null)
  const username = ref<string | null>(null)
  const isAuthenticated = ref(false)
  const isInitialized = ref(false)

  const login = async (loginUsername: string, password: string) => {
    try {
      const response = await apiClient.post('/api/auth/login', {
        username: loginUsername,
        password
      })

      token.value = response.data.access_token
      username.value = response.data.username
      isAuthenticated.value = true

      // Save to localStorage
      if (token.value) localStorage.setItem('access_token', token.value)
      if (username.value) localStorage.setItem('username', username.value)

      // Set axios default header
      if (token.value) {
        apiClient.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
      }

      return response.data
    } catch (error: any) {
      throw new Error(error.response?.data?.message || 'Login failed')
    }
  }

  const logout = async () => {
    try {
      if (token.value) {
        await apiClient.post('/api/auth/logout')
      }
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      // Clear state regardless of API call result
      token.value = null
      username.value = null
      isAuthenticated.value = false

      // Clear localStorage
      localStorage.removeItem('access_token')
      localStorage.removeItem('username')

      // Clear axios default header
      delete apiClient.defaults.headers.common['Authorization']
    }
  }

  const restoreAuth = async () => {
    const storedToken = localStorage.getItem('access_token')
    const storedUsername = localStorage.getItem('username')

    if (storedToken && storedUsername) {
      token.value = storedToken
      username.value = storedUsername

      // Set axios default header
      if (storedToken) {
        apiClient.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`
      }

      try {
        // Verify token with backend
        await apiClient.get('/api/auth/verify')
        isAuthenticated.value = true
      } catch (error) {
        // Token is invalid, clear auth
        await logout()
      }
    }
    
    isInitialized.value = true
  }

  const verifyToken = async () => {
    try {
      const response = await apiClient.get('/api/auth/verify')
      return response.data
    } catch (error) {
      await logout()
      throw error
    }
  }

  return {
    token: readonly(token),
    username: readonly(username),
    isAuthenticated: readonly(isAuthenticated),
    isInitialized: readonly(isInitialized),
    login,
    logout,
    restoreAuth,
    verifyToken
  }
})