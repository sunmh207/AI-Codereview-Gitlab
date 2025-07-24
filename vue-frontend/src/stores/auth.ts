import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { User, LoginForm } from '@/types'
import { setToken, getToken, removeToken, setUser, getUser, isAuthenticated } from '@/utils/auth'
import { authApi } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const isLoggedIn = ref(false)
  const authInitialized = ref(false)

  function initAuth() {
    try {
      // 直接从localStorage读取状态
      const token = getToken()
      const userData = getUser()

      if (token && userData) {
        user.value = userData
        isLoggedIn.value = true
        console.log('Auth initialized from localStorage:', userData)
      } else {
        user.value = null
        isLoggedIn.value = false
        removeToken() // 清理不完整的数据
      }
    } catch (error) {
      console.error('Auth initialization failed:', error)
      user.value = null
      isLoggedIn.value = false
      removeToken()
    } finally {
      authInitialized.value = true
    }
  }

  async function login(loginForm: LoginForm): Promise<{ success: boolean; message?: string }> {
    try {
      const response = await authApi.login(loginForm)

      if (response.success && response.user) {
        user.value = response.user
        isLoggedIn.value = true

        // 保存用户信息到localStorage
        setUser(response.user)

        if (loginForm.remember && response.token) {
          setToken(response.token)
        }

        console.log('Login successful, user saved to localStorage:', response.user)
        return { success: true, message: response.message }
      } else {
        return { success: false, message: response.message || '登录失败' }
      }
    } catch (error: any) {
      console.error('Login failed:', error)
      const message = error.response?.data?.message || '登录失败'
      return { success: false, message }
    }
  }

  function logout() {
    user.value = null
    isLoggedIn.value = false
    removeToken() // 这会同时清除token和user数据
    console.log('User logged out, localStorage cleared')
  }

  return {
    user,
    isLoggedIn,
    authInitialized,
    initAuth,
    login,
    logout
  }
})
